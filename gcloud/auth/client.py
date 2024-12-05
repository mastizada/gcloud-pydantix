import asyncio
import os
from datetime import datetime, timezone
from io import StringIO
from json.decoder import JSONDecodeError
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any

import jwt
import orjson
from httpx import AsyncClient as AsyncHttpClient
from httpx import HTTPError
from pydantic import ValidationError

from gcloud.auth.constants import (
    GCE_ENDPOINT_TOKEN,
    GCE_METADATA_HEADERS,
    REFRESH_HEADERS,
)
from gcloud.auth.schemas import TokenResponse, TokenType
from gcloud.base.utils import DecoratorType

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

RETRY_EXCEPTIONS = (HTTPError, JSONDecodeError, ValidationError, TypeError, ValueError)


def os_name():
    """Mock-able os.name resolution."""
    return os.name


def get_service_data(service: str | StringIO | None) -> dict[str, Any]:
    """
    Get service auth data for one of the available methods.

    It tries to find and read application credentials file and return its contents.

    This method is based on the official ``google.auth.default()`` method.
    """
    # get service file from environment variable
    service = service or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if not service:
        # _get_gcloud_sdk_credentials() replacement
        cloudsdk_config = os.environ.get("CLOUDSDK_CONFIG")
        if cloudsdk_config is not None:
            sdk_path = Path(cloudsdk_config)
        elif os_name() != "nt":
            sdk_path = Path.home() / ".config" / "gcloud"
        else:
            try:
                sdk_path = Path(os.environ["APPDATA"]) / "gcloud"
            except KeyError:
                sdk_path = Path(os.environ.get("SystemDrive", "C:")) / "\\" / "gcloud"  # noqa: SIM112
        service = str(sdk_path / "application_default_credentials.json")
        set_explicitly = bool(cloudsdk_config)
    else:
        set_explicitly = True

    # skip _get_gae_credentials(): not supported

    # noinspection PyBroadException
    try:
        if isinstance(service, str):
            with Path.open(Path(service), encoding="utf-8") as f:
                return orjson.loads(f.read())
        # read from in-memory file (io.StringIO)
        return orjson.loads(service.read())
    except FileNotFoundError:
        if set_explicitly:
            # only warn users if they have explicitly set the service_file
            # path, otherwise this is an expected code flow
            raise

        # _get_gce_credentials(): when we return {} here, the Token class falls
        # back to using the metadata service
        return {}
    except Exception:  # noqa: BLE001
        return {}


class GCPToken:
    """
    GCP OAuth 2.0 access token.

    Based on https://developers.google.com/identity/protocols/oauth2.
    It is using an HTTPX session, closing the session will be enough for the cleanup.
    """

    def __init__(
        self,
        http_client: AsyncHttpClient,
        service_file: str | StringIO | None = None,
        scopes: list[str] | None = None,
        retry_decorator: DecoratorType | None = None,
        # client defaults
        default_token_ttl: int = 3600,
        token_ttl_leeway: int = 40,
    ) -> None:
        """
        Initialize the Google Authentication for Oauth 2.0.

        :param http_client: Shared httpx client session.
        :param service_file: Path or content (StringIO) for the GCP credentials file.
        :param scopes: Access scopes. Merge scopes for GCP clients that you are going to use with this Auth session.
        :param retry_decorator: A retry decorator of your choice. Make sure it is async compatible.
        :param default_token_ttl: Token TTL in seconds, limited to 65 minutes in GCP, default value is 3600 seconds.
        :param token_ttl_leeway: Update the token x seconds before it will expire, default value is 40.
        """
        self.default_token_ttl = default_token_ttl
        self.token_ttl_leeway = token_ttl_leeway
        self.http_client = http_client
        # get auth details
        self.service_data = get_service_data(service_file)
        if self.service_data:
            self.token_type = TokenType(self.service_data["type"])
            self.token_uri = self.service_data.get("token_uri", "https://oauth2.googleapis.com/token")
        else:
            # At this point, all we can do is assume we're running somewhere
            # with default credentials, for example, GCE.
            self.token_type = TokenType.GCE_METADATA
            self.token_uri = GCE_ENDPOINT_TOKEN

        # scopes are required for service account
        self.scopes = " ".join(scopes or [])
        if self.token_type == TokenType.SERVICE_ACCOUNT and not self.scopes:
            raise RuntimeError("Scopes must be provided when token type is service account or using target_principal")

        # store access token data for refresh
        self.access_token: str | None = None
        self.access_token_duration: int = 0
        self.access_token_acquired_at: datetime = datetime(1970, 1, 1)

        # define token update function based on the Token Type
        refresh_method: Callable[[int], Awaitable[TokenResponse]]
        if self.token_type == TokenType.AUTHORIZED_USER:
            refresh_method = self._refresh_authorized_user
        elif self.token_type == TokenType.GCE_METADATA:
            refresh_method = self._refresh_gce_metadata
        else:
            refresh_method = self._refresh_service_account

        # apply the retry decorator if it is supplied
        self.refresh_method: Callable[[int], Awaitable[TokenResponse]]
        if retry_decorator is None:
            self.refresh_method = refresh_method
        else:
            self.refresh_method = retry_decorator(refresh_method)

        # lock for acquiring a new token
        self.acquire_task: asyncio.Task[None] | None = None

    async def get_token(self) -> str | None:
        # get the GCP token, main function to use in clients.
        await self.ensure_token()
        return self.access_token

    async def ensure_token(self) -> None:
        """Make sure the token is available and up to date."""
        if self.acquire_task and not self.acquire_task.done():
            # another coroutine is updating the token, wait for it
            await self.acquire_task
            return

        if self.access_token:
            # check token age
            token_age = (datetime.now(timezone.utc) - self.access_token_acquired_at).total_seconds()
            if token_age <= (self.access_token_duration - self.token_ttl_leeway):
                return

        # update the token
        self.acquire_task = asyncio.create_task(self.acquire_access_token())
        await self.acquire_task

    async def acquire_access_token(self, timeout: int = 10) -> None:
        # refresh the token based on token type
        result = await self.refresh_method(timeout)

        self.access_token = result.access_token
        self.access_token_duration = result.expires_in
        self.access_token_acquired_at = datetime.now(timezone.utc)
        self.acquire_task = None

    async def _refresh_authorized_user(self, timeout: int) -> TokenResponse:
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.service_data["client_id"],
            "client_secret": self.service_data["client_secret"],
            "refresh_token": self.service_data["refresh_token"],
        }

        response = await self.http_client.post(
            url=self.token_uri,
            data=payload,
            headers=REFRESH_HEADERS,
            timeout=timeout,
        )
        return TokenResponse.model_validate_json(response.text)

    async def _refresh_gce_metadata(self, timeout: int) -> TokenResponse:
        response = await self.http_client.get(
            url=self.token_uri,
            headers=GCE_METADATA_HEADERS,
            timeout=timeout,
        )
        return TokenResponse.model_validate_json(response.text)

    async def _refresh_service_account(self, timeout: int) -> TokenResponse:
        now = int(time())
        assertion_payload = {
            "aud": self.token_uri,
            "exp": now + self.default_token_ttl,
            "iat": now,
            "iss": self.service_data["client_email"],
            "scope": self.scopes,
        }

        assertion = jwt.encode(
            assertion_payload,
            self.service_data["private_key"],
            algorithm="RS256",
        )
        payload = {
            "assertion": assertion,
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        }

        response = await self.http_client.post(
            self.token_uri,
            data=payload,
            headers=REFRESH_HEADERS,
            timeout=timeout,
        )
        return TokenResponse.model_validate_json(response.text)


class AnonymousGCPToken(GCPToken):
    """Fake token generator."""

    # noinspection PyMissingConstructor
    def __init__(self, http_client: AsyncHttpClient, scopes: list[str] | None = None, **__: dict) -> None:
        self.http_client = http_client
        self.scopes = " ".join(scopes or [])

    async def get_token(self) -> str | None:
        return "fake"
