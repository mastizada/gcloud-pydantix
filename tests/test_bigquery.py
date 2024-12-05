import pytest
import respx
from httpx import AsyncClient, Response

from gcloud.auth.client import AnonymousGCPToken
from gcloud.base.exceptions import ErrorResponse, RequestError
from gcloud.bigquery.client import BigQueryClient
from gcloud.bigquery.constants import BIGQUERY_SCOPES
from gcloud.bigquery.schemas import Dataset, DatasetReference, DatasetResponse
from tests.mocks.bigquery import (
    DATASET_CREATE_ALREADY_EXISTS,
    DATASET_CREATE_SUCCESS,
    DATASET_GET_RESPONSE,
    DATASET_LIST_RESPONSE,
    DATASET_PATCH_RESPONSE,
)


@pytest.mark.asyncio()
async def test_bigquery_client_scope_check(http_client: AsyncClient):
    token_session = AnonymousGCPToken(http_client)
    with pytest.raises(RuntimeError) as err:
        BigQueryClient(project="test-project", token_session=token_session, http_client=http_client)

    assert err.value.args
    assert err.value.args[0] == "Current token session doesn't contain any BigQuery scopes!"


@pytest.mark.asyncio()
async def test_bigquery_client_create_dataset(http_client: AsyncClient):
    token_session = AnonymousGCPToken(http_client, scopes=BIGQUERY_SCOPES)
    client = BigQueryClient(project="test-project", token_session=token_session, http_client=http_client)

    respx.post("https://bigquery.googleapis.com/bigquery/v2/projects/test-project/datasets").mock(
        return_value=Response(status_code=200, json=DATASET_CREATE_SUCCESS)
    )
    payload = Dataset(
        dataset_reference=DatasetReference(project_id="test-project", dataset_id="test-dataset"),
        description="Test dataset",
        location="EU",
    )
    result = await client.create_dataset(payload, timeout=10)
    assert result
    assert result.id == "test-project:test-dataset"


@pytest.mark.asyncio()
async def test_bigquery_client_create_dataset_duplicate(http_client: AsyncClient):
    token_session = AnonymousGCPToken(http_client, scopes=BIGQUERY_SCOPES)
    client = BigQueryClient(project="test-project", token_session=token_session, http_client=http_client)

    respx.post("https://bigquery.googleapis.com/bigquery/v2/projects/test-project/datasets").mock(
        return_value=Response(status_code=409, json=DATASET_CREATE_ALREADY_EXISTS)
    )
    payload = Dataset(
        dataset_reference=DatasetReference(project_id="test-project", dataset_id="test-dataset"),
        description="Test dataset",
        location="EU",
    )
    with pytest.raises(RequestError) as err:
        await client.create_dataset(payload)
    assert isinstance(err.value.error, ErrorResponse)
    assert err.value.status_code == 409
    assert err.value.error.message == "Already Exists: Dataset test-project:test-dataset"


@pytest.mark.asyncio()
async def test_bigquery_client_list_dataset(http_client: AsyncClient):
    token_session = AnonymousGCPToken(http_client, scopes=BIGQUERY_SCOPES)
    client = BigQueryClient(project="test-project", token_session=token_session, http_client=http_client)

    respx.get("https://bigquery.googleapis.com/bigquery/v2/projects/test-project/datasets").mock(
        return_value=Response(status_code=200, json=DATASET_LIST_RESPONSE)
    )
    datasets = await client.list_datasets()
    assert datasets
    assert datasets.kind == "bigquery#datasetList"
    assert datasets.datasets
    assert datasets.datasets[0].dataset_reference.dataset_id == "test-dataset"


@pytest.mark.asyncio()
async def test_bigquery_client_get_dataset(http_client: AsyncClient):
    token_session = AnonymousGCPToken(http_client, scopes=BIGQUERY_SCOPES)
    client = BigQueryClient(project="test-project", token_session=token_session, http_client=http_client)

    respx.get("https://bigquery.googleapis.com/bigquery/v2/projects/test-project/datasets/test-dataset").mock(
        return_value=Response(status_code=200, json=DATASET_GET_RESPONSE)
    )
    dataset_result = await client.get_dataset("test-dataset")
    assert isinstance(dataset_result, DatasetResponse)
    assert dataset_result.id == "test-project:test-dataset"
    dataset = dataset_result.to_dataset()
    assert isinstance(dataset, Dataset)
    assert dataset.dataset_reference.dataset_id == "test-dataset"


@pytest.mark.asyncio()
async def test_bigquery_client_patch_dataset(http_client: AsyncClient):
    token_session = AnonymousGCPToken(http_client, scopes=BIGQUERY_SCOPES)
    client = BigQueryClient(project="test-project", token_session=token_session, http_client=http_client)

    respx.patch("https://bigquery.googleapis.com/bigquery/v2/projects/test-project/datasets/test-dataset").mock(
        return_value=Response(status_code=200, json=DATASET_PATCH_RESPONSE)
    )
    payload = Dataset(
        dataset_reference=DatasetReference(project_id="test-project", dataset_id="test-dataset"),
        description="Test description 2",
        location="EU",
    )
    result = await client.patch_dataset("test-dataset", payload)
    assert result
    assert result.description == "Test description 2"
