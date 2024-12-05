from collections.abc import Callable
from uuid import uuid4

import orjson
from httpx import AsyncClient as AsyncHttpClient

from gcloud.auth.client import GCPToken
from gcloud.base.client import GCPBaseClient
from gcloud.base.constants import RequestMethod
from gcloud.base.utils import BaseModel, DecoratorType
from gcloud.bigquery.constants import BIGQUERY_API_ROOT, BIGQUERY_SCOPES
from gcloud.bigquery.schemas import (
    Dataset,
    DatasetListResponse,
    DatasetResponse,
    Table,
    TableInsertError,
    TableInsertResponse,
    TableResponse,
)


class BigQueryClient(GCPBaseClient):
    """
    Basic operations for BigQuery.

    Depends on Pydantic models, httpx session and GCPToken.
    In URLs, prettyPrint=false prevents backend json prettifier.
    """

    def __init__(
        self,
        project: str,
        token_session: GCPToken,
        http_client: AsyncHttpClient,
        api_root: str = BIGQUERY_API_ROOT,
        default_dataset: str | None = None,
        retry_decorator: DecoratorType | None = None,
    ):
        """
        RestAPI Client for BigQuery API.

        :param project: GCP Project ID.
        Sometimes assigned to BIGQUERY_PROJECT_ID or GOOGLE_CLOUD_PROJECT environment variables.

        :param token_session: Initialized GCPToken session instance.
        It should include 'https://www.googleapis.com/auth/bigquery.insertdata' and
        'https://www.googleapis.com/auth/bigquery' scopes.

        :param http_client: httpx client instance.

        :param api_root: GCP API Root, defaults to https://www.googleapis.com.
        Useful for changing to emulator URL. Should be a valid HTTP URL.

        :param default_dataset: Default dataset name to use when working with tables.
        :param retry_decorator: A retry decorator of your choice. Make sure it is async compatible.
        """
        if not any(scope in token_session.scopes for scope in BIGQUERY_SCOPES):
            raise RuntimeError("Current token session doesn't contain any BigQuery scopes!")

        super().__init__(
            token_session=token_session,
            http_client=http_client,
            api_root=f"{api_root}/bigquery/v2",
            retry_decorator=retry_decorator,
        )
        self.project = project
        self.default_dataset = default_dataset

    async def list_datasets(self, timeout: int | None = None) -> DatasetListResponse:
        """
        List datasets.

        Based on https://cloud.google.com/bigquery/docs/reference/rest/v2/datasets/list
        """
        url = f"{self.api_root}/projects/{self.project}/datasets?prettyPrint=false"
        return await self.get_request(
            url=url,
            timeout=timeout,
            response_model=DatasetListResponse,
        )

    async def get_dataset(self, dataset_name: str, timeout: int | None = None) -> DatasetResponse:
        """
        Get dataset.

        Based on https://cloud.google.com/bigquery/docs/reference/rest/v2/datasets/get
        """
        url = f"{self.api_root}/projects/{self.project}/datasets/{dataset_name}?prettyPrint=false"
        return await self.get_request(
            url=url,
            timeout=timeout,
            response_model=DatasetResponse,
        )

    async def create_dataset(self, dataset: Dataset, timeout: int | None = None) -> DatasetResponse:
        """
        Create a dataset.

        Based on https://cloud.google.com/bigquery/docs/reference/rest/v2/datasets/insert
        """
        url = f"{self.api_root}/projects/{self.project}/datasets?prettyPrint=false"
        return await self.send_request(
            url=url,
            payload=dataset.model_dump_json(by_alias=True).encode("utf-8"),
            timeout=timeout,
            response_model=DatasetResponse,
        )

    async def patch_dataset(self, dataset_name: str, dataset: Dataset, timeout: int | None = None) -> DatasetResponse:
        """
        Update dataset fields.

        Based on https://cloud.google.com/bigquery/docs/reference/rest/v2/datasets/patch
        """
        url = f"{self.api_root}/projects/{self.project}/datasets/{dataset_name}?prettyPrint=false"
        return await self.send_request(
            url=url,
            payload=dataset.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8"),
            timeout=timeout,
            response_model=DatasetResponse,
            method=RequestMethod.PATCH,
        )

    async def get_table(
        self, table_name: str, dataset_name: str | None = None, timeout: int | None = None
    ) -> TableResponse:
        """
        Get table information.

        Based on https://cloud.google.com/bigquery/docs/reference/rest/v2/tables/get
        """
        if dataset_name is None:
            if self.default_dataset is None:
                raise ValueError("Dataset name is required when default name is not provided")
            dataset_name = self.default_dataset

        url = f"{self.api_root}/projects/{self.project}/datasets/{dataset_name}/tables/{table_name}?prettyPrint=false"
        return await self.get_request(url=url, timeout=timeout, response_model=TableResponse)

    async def create_table(
        self, table: Table, dataset_name: str | None = None, timeout: int | None = None
    ) -> TableResponse:
        """
        Create a new table.

        Based on https://cloud.google.com/bigquery/docs/reference/rest/v2/tables/insert
        """
        if dataset_name is None:
            if self.default_dataset is None:
                raise ValueError("Dataset name is required when default name is not provided")
            dataset_name = self.default_dataset

        url = f"{self.api_root}/projects/{self.project}/datasets/{dataset_name}/tables?prettyPrint=false"
        return await self.send_request(
            url=url,
            payload=table.model_dump_json(by_alias=True).encode("utf-8"),
            timeout=timeout,
            response_model=TableResponse,
        )

    async def insert_all(
        self,
        rows: list[BaseModel],
        table_name: str,
        dataset_name: str | None = None,
        *,
        skip_invalid: bool = False,
        ignore_unknown: bool = True,
        template_suffix: str | None = None,
        timeout: int | None = None,
        insert_id_fn: Callable[[BaseModel], str] | None = None,
    ) -> list[TableInsertError]:
        """
        Streams data into BigQuery Table.

        Please check the result, it will contain list of errors and will not raise an exception.

        Based on https://cloud.google.com/bigquery/docs/reference/rest/v2/tabledata/insertAll

        By default, each row is assigned a unique insertId. This can be
        customized by supplying an `insert_id_fn` which takes a row and
        returns an insertId.

        In cases where at least one row has successfully been inserted and at
        least one row has failed to be inserted, the Google API will return a
        2xx (successful) response along with an `insertErrors` key in the
        response JSON containing details on the failing rows.
        """
        if dataset_name is None:
            if self.default_dataset is None:
                raise ValueError("Dataset name is required when default name is not provided")
            dataset_name = self.default_dataset

        if not rows:
            return []

        url = (
            f"{self.api_root}/projects/{self.project}/datasets/{dataset_name}"
            f"/tables/{table_name}/insertAll?prettyPrint=false"
        )

        payload = self._make_table_insert_body(
            rows,
            skip_invalid=skip_invalid,
            ignore_unknown=ignore_unknown,
            template_suffix=template_suffix,
            insert_id_fn=insert_id_fn or self._mk_unique_insert_id,
        )
        result = await self.send_request(url=url, payload=payload, timeout=timeout, response_model=TableInsertResponse)
        return result.insert_errors

    # noinspection PyUnusedLocal
    @staticmethod
    def _mk_unique_insert_id(__: BaseModel) -> str:
        """
        Unique id generator for each row.

        Defaults to value used by Google's BigQuery client for Python.
        """
        return str(uuid4())

    @staticmethod
    def _make_table_insert_body(
        rows: list[BaseModel],
        *,
        skip_invalid: bool,
        ignore_unknown: bool,
        template_suffix: str | None,
        insert_id_fn: Callable[[BaseModel], str],
    ) -> bytes:
        body = {
            "kind": "bigquery#tableDataInsertAllRequest",
            "skipInvalidRows": skip_invalid,
            "ignoreUnknownValues": ignore_unknown,
            "rows": [
                {
                    "insertId": insert_id_fn(row),
                    "json": row.model_dump(mode="json", by_alias=True),
                }
                for row in rows
            ],
        }

        if template_suffix is not None:
            body["templateSuffix"] = template_suffix

        return orjson.dumps(body)
