# gcloud-pydantic

AsyncIO Google Cloud Client Library using Pydantic and HTTPX

---

## About & Usage

This library was heavily inspired by [gcloud-aio](https://github.com/talkiq/gcloud-aio/), it relies on Google's REST Resource documentations. It is using Pydantic for request and response schemas, httpx for managing the network sessions, and orjson for parsing responses.

Recommended usage is to create a google token on application startup with all access scopes that you are going to use, and then initialize all clients for those tools (pubsub, bigquery and etc.).
After that, use the instance of that client wherever you need to interact with that resource.

### Starlette/FastAPI Example:

This example shows how to use it in FastAPI project, but steps can be adjusted to all other use cases and frameworks that use asyncio.

```python
from httpx import AsyncClient
from fastapi import Depends
from gcloud.auth import GCPToken
from gcloud.bigquery import BigQueryClient

@asynccontextmanager
async def lifespan(app):
    app.state.http = AsyncClient(http2=True, timeout=10)
    gcp_session = GCPToken(app.state.http, scopes=(...))
    app.state.bigquery = BigQueryClient(
        project="GCP_PROJECT", token_session=gcp_session, http_client=app.state.http
    )
    # initial authentication and token caching
    await gcp_session.get()

    yield
    # closing the httpx session will be enough for cleanup
    await state.http.aclose()

async def get_bigquery_client(request):
    # Dependency injection for the client
    return request.app.state.bigquery

@route.get("/")
async def get_info(bigquery_client=Depends(get_bigquery_client)):
    # Use the client in an API route
    ...
```
---

&copy; 2024 Emin Mastizada. MIT Licenced.
