"""Base Client for Google Cloud Resources."""

import orjson
from httpx import AsyncClient as AsyncHttpClient

from gcloud.auth.client import GCPToken
from gcloud.base.constants import RequestMethod, ResponseModel
from gcloud.base.exceptions import ErrorResponse, RequestError, ServiceUnavailableError
from gcloud.base.utils import DecoratorType


class GCPBaseClient:
    def __init__(
        self,
        token_session: GCPToken,
        http_client: AsyncHttpClient,
        api_root: str,
        retry_decorator: DecoratorType | None = None,
    ):
        self.token_session = token_session
        self.http_client = http_client
        self.api_root = api_root

        if retry_decorator is None:
            self.send_request = self._send_request
            self.get_request = self._get_request
        else:
            self.send_request = retry_decorator(self._send_request)
            self.get_request = retry_decorator(self._get_request)

    async def get_headers(self) -> dict[str, str]:
        token = await self.token_session.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def _send_request(
        self,
        url: str,
        payload: bytes,
        timeout: int | None,
        response_model: type[ResponseModel],
        method: RequestMethod = RequestMethod.POST,
    ) -> ResponseModel:
        """
        Send request to GCP, parse and return the response according to the response_model.

        Raises RequestError if the response is not 2xx.
        """
        headers = await self.get_headers()

        extras = {}
        if timeout is not None:
            # will use default httpx timeout if it is not specified
            extras["timeout"] = timeout

        match method:
            case RequestMethod.POST:
                handler = self.http_client.post
            case RequestMethod.PUT:
                handler = self.http_client.put
            case RequestMethod.PATCH:
                handler = self.http_client.patch
            case RequestMethod.DELETE:
                handler = self.http_client.delete
            case _:
                handler = self.http_client.post

        response = await handler(url, content=payload, headers=headers, **extras)
        if response.is_success:
            return response_model.model_validate_json(response.text)

        # error handling according to https://cloud.google.com/bigquery/docs/error-messages
        if response.status_code in [500, 502, 503, 504]:
            # retry-safe issues
            raise ServiceUnavailableError(
                status_code=response.status_code,
                error=ErrorResponse(
                    code=response.status_code,
                    message="Request to Google Cloud failed",
                    status="INTERNAL" if response.status_code == 500 else "UNAVAILABLE",
                ),
            )
        # retry-unsafe issues
        try:
            response_data = orjson.loads(response.text)
            if error_details := response_data.get("error"):
                error = ErrorResponse.model_validate(error_details)
            else:
                error = ErrorResponse(
                    code=response.status_code, message="Bad response from Google Cloud", status="UNKNOWN"
                )
            raise RequestError(error=error, status_code=response.status_code)
        except orjson.JSONDecodeError as e:
            error = ErrorResponse(code=response.status_code, message="Bad response from Google Cloud", status="UNKNOWN")
            raise RequestError(status_code=response.status_code, error=error) from e

    async def _get_request(self, url: str, timeout: int | None, response_model: type[ResponseModel]) -> ResponseModel:
        """
        Get resource from GCP, parse and return the response according to the response_model.

        Raises RequestError if the response is not 2xx.
        """
        headers = await self.get_headers()

        extras = {}
        if timeout is not None:
            # use default httpx timeout if it is not specified
            extras["timeout"] = timeout

        response = await self.http_client.get(url, headers=headers, **extras)
        if response.is_success:
            return response_model.model_validate_json(response.text)

        if response.status_code in [500, 502, 503, 504]:
            raise ServiceUnavailableError(
                status_code=response.status_code,
                error=ErrorResponse(
                    code=response.status_code,
                    message="Request to Google Cloud failed",
                    status="INTERNAL" if response.status_code == 500 else "UNAVAILABLE",
                ),
            )

        try:
            response_data = orjson.loads(response.text)
            if error_details := response_data.get("error"):
                error = ErrorResponse.model_validate(error_details)
            else:
                error = ErrorResponse(
                    code=response.status_code, message="Bad response from Google Cloud", status="UNKNOWN"
                )
            raise RequestError(error=error, status_code=response.status_code)
        except orjson.JSONDecodeError as e:
            error = ErrorResponse(code=response.status_code, message="Bad response from Google Cloud", status="UNKNOWN")
            raise RequestError(status_code=response.status_code, error=error) from e
