import asyncio
import os
import unittest
import unittest.mock
from io import StringIO
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import respx
import stamina
from httpx import AsyncClient, Response, TimeoutException
from pydantic import ValidationError

from gcloud.auth.client import AnonymousGCPToken, GCPToken
from gcloud.bigquery.constants import DEFAULT_SCOPES as BIGQUERY_SCOPES

SERVICE_FILE_CONTENT = """
{
    "type": "service_account",
    "project_id": "not-my-project",
    "private_key_id": "abc123",
    "private_key": "fake-key",
    "client_email": "fake@appspot.gserviceaccount.com",
    "client_secret": "fake",
    "refresh_token": null,
    "client_id": "123456",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://example.com/cert"
}
"""


@pytest.mark.asyncio()
async def test_anonym_auth(http_client: AsyncClient):
    client = AnonymousGCPToken(http_client)
    assert await client.get_token() == "fake"


@pytest.mark.asyncio()
async def test_metadata_auth(http_client: AsyncClient):
    auth_mock = respx.get(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token?recursive=true"
    )
    auth_mock.side_effect = [
        Response(status_code=200, json={"access_token": "ABC", "expires_in": 3600}),
        Response(status_code=200, json={"access_token": "CBA", "expires_in": 3600}),
    ]

    client = GCPToken(http_client=http_client)
    client.token_ttl_leeway = 3601  # always expired
    assert await client.get_token() == "ABC"
    # should re-fetch the token
    assert await client.get_token() == "CBA"
    client.token_ttl_leeway = 500  # there is enough time before expire
    assert await client.get_token() == "CBA"


@pytest.mark.asyncio()
async def test_google_auth_with_service_file(http_client: AsyncClient):
    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=Response(status_code=200, json={"access_token": "ABC", "expires_in": 3600})
    )
    with unittest.mock.patch.object(
        Path, "open", new=unittest.mock.mock_open(read_data=SERVICE_FILE_CONTENT), create=True
    ):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
        with unittest.mock.patch("jwt.encode") as jwt_encode_mock:
            jwt_encode_mock.return_value = "fake-token-str"
            with pytest.raises(RuntimeError) as err:
                GCPToken(http_client=http_client)
            assert (
                err.value.args[0]
                == "Scopes must be provided when token type is service account or using target_principal"
            )
            client = GCPToken(http_client=http_client, scopes=BIGQUERY_SCOPES)
            assert await client.get_token() == "ABC"


@pytest.mark.asyncio()
async def test_google_auth_with_service_io(http_client: AsyncClient):
    service_file = StringIO(SERVICE_FILE_CONTENT)
    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=Response(status_code=200, json={"access_token": "ABC", "expires_in": 3600})
    )
    with unittest.mock.patch("jwt.encode") as jwt_encode_mock:
        jwt_encode_mock.return_value = "fake-token-str"
        client = GCPToken(http_client=http_client, service_file=service_file, scopes=BIGQUERY_SCOPES)
        assert await client.get_token() == "ABC"


@pytest.mark.asyncio()
async def test_google_auth_with_service_file_issues(http_client: AsyncClient):
    respx.get(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token?recursive=true"
    ).mock(return_value=Response(status_code=200, json={"access_token": "ABC", "expires_in": 3600}))
    # file not found
    with pytest.raises(FileNotFoundError):
        GCPToken(http_client=http_client, service_file=f"/tmp/{uuid4}.blank", scopes=BIGQUERY_SCOPES)  # noqa: S108
    # file reading issues
    with unittest.mock.patch.object(Path, "open", side_effect=OSError()):
        # should fall back to GCE_METADATA
        client = GCPToken(http_client=http_client, service_file="credentials.json", scopes=BIGQUERY_SCOPES)
        assert await client.get_token() == "ABC"


@pytest.mark.asyncio()
async def test_google_auth_with_cloud_sdk_path(http_client: AsyncClient):
    respx.get(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token?recursive=true"
    ).mock(return_value=Response(status_code=200, json={"access_token": "ABC", "expires_in": 3600}))
    # custom cloud sdk path
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    os.environ["CLOUDSDK_CONFIG"] = "/tmp/"  # noqa: S108
    with pytest.raises(FileNotFoundError) as err:
        GCPToken(http_client=http_client, scopes=BIGQUERY_SCOPES)
    assert err.value.filename == "/tmp/application_default_credentials.json"  # noqa: S108
    assert err.value.strerror == "No such file or directory"
    # default Windows sdk path
    del os.environ["CLOUDSDK_CONFIG"]
    os.environ["APPDATA"] = "/tmp/app_data/"  # noqa: S108
    with unittest.mock.patch("gcloud.auth.client.os_name") as os_name:
        os_name.return_value = "nt"
        client = GCPToken(http_client=http_client, scopes=BIGQUERY_SCOPES)
        # not explicitly set, will fall back to GCE_METADATA
        assert await client.get_token() == "ABC"
        # without APPDATA, will use SystemDrive
        del os.environ["APPDATA"]
        client = GCPToken(http_client=http_client, scopes=BIGQUERY_SCOPES)
        # not explicitly set, will fall back to GCE_METADATA
        assert await client.get_token() == "ABC"


@pytest.mark.asyncio()
async def test_google_auth_multiple_calls_lock(http_client: AsyncClient):
    auth_mock = respx.get(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token?recursive=true"
    )
    # the first task should acquire the token and cache it
    # second task should use the token from the cache and avoid fetching again
    auth_mock.side_effect = [
        Response(status_code=200, json={"access_token": "ABC", "expires_in": 3600}),
        Response(status_code=400, json={}),
    ]

    client = GCPToken(http_client=http_client)
    tasks = [asyncio.create_task(client.get_token()), asyncio.create_task(client.get_token())]
    await asyncio.gather(*tasks)
    assert all(token.result() == "ABC" for token in tasks), tasks


@pytest.mark.asyncio()
async def test_google_auth_retry_decorator(http_client: AsyncClient):
    auth_mock = respx.get(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token?recursive=true"
    )
    # the first task should acquire the token and cache it
    # second task should use the token from the cache and avoid fetching again
    auth_mock.side_effect = [
        TimeoutException(message="Request timed out"),
        Response(status_code=400, json={}),
        Response(status_code=200, json={"access_token": "ABC", "expires_in": 3600}),
    ]
    retry_decorator = stamina.retry(on=(httpx.HTTPError, ValidationError), attempts=3, wait_max=0.01)
    client = GCPToken(http_client=http_client, retry_decorator=retry_decorator)
    assert await client.get_token() == "ABC"


@pytest.mark.asyncio()
async def test_google_auth_user_auth(http_client: AsyncClient):
    service_file = StringIO(SERVICE_FILE_CONTENT.replace("service_account", "authorized_user"))
    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=Response(status_code=200, json={"access_token": "ABC", "expires_in": 3600})
    )
    client = GCPToken(http_client=http_client, service_file=service_file, scopes=BIGQUERY_SCOPES)
    assert await client.get_token() == "ABC"


@pytest.mark.asyncio()
async def test_google_auth_unsupported_type(http_client: AsyncClient):
    service_file = StringIO(SERVICE_FILE_CONTENT.replace("service_account", "new_type"))
    with pytest.raises(ValueError) as err:  # noqa: PT011
        GCPToken(http_client=http_client, service_file=service_file, scopes=BIGQUERY_SCOPES)
    assert err.value.args[0] == "'new_type' is not a valid TokenType"
