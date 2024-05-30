import pytest
import respx
from httpx import AsyncClient, Response

from gcloud.auth.client import AnonymousGCPToken, GCPToken


@pytest.mark.asyncio()
async def test_anonym_auth(http_client: AsyncClient):
    client = AnonymousGCPToken(http_client)
    assert await client.get_token() == "fake"


@pytest.mark.asyncio()
async def test_metadata_auth(http_client: AsyncClient):
    respx.get(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/" "default/token?recursive=true"
    ).mock(return_value=Response(status_code=200, json={"access_token": "ABC", "expires_in": 3600}))

    client = GCPToken(http_client=http_client)
    assert await client.get_token() == "ABC"
