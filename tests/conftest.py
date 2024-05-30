import httpx
import pytest
import pytest_asyncio
from httpx import AsyncHTTPTransport
from respx.router import MockRouter


@pytest.fixture(autouse=True)
def _patch_httpx_library(respx_mock: MockRouter):
    """
    Do not allow httpx making any external calls.

    The fixture respx_mock is provided by `respx.plugin.py` for pytest context.
    """
    with respx_mock():
        yield


@pytest_asyncio.fixture(scope="session")
async def http_client():
    client = httpx.AsyncClient(
        timeout=30,
        transport=AsyncHTTPTransport(retries=1),
        headers={"user-agent": "gcloud-pydantix unit tests"},
        http2=True,
    )
    yield client
    await client.aclose()
