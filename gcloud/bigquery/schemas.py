from enum import Enum
from typing import Literal

from pydantic import Field, field_validator

from gcloud.base.exceptions import ErrorProto
from gcloud.base.utils import BaseModel


class TableInsertError(BaseModel):
    index: int
    errors: list[ErrorProto]


class TableReference(BaseModel):
    """
    Reference to the BigQuery table.

    Based on https://cloud.google.com/bigquery/docs/reference/rest/v2/TableReference
    """

    project_id: str = Field(..., alias="projectId")
    dataset_id: str = Field(..., alias="datasetId")
    table_id: str = Field(..., alias="tableId")


class TableFieldType(Enum):
    STRING = "STRING"
    BYTES = "BYTES"
    INTEGER = "INTEGER"
    INT64 = "INT64"
    FLOAT = "FLOAT"
    FLOAT64 = "FLOAT64"
    BOOLEAN = "BOOLEAN"
    TIMESTAMP = "TIMESTAMP"
    DATE = "DATE"
    TIME = "TIME"
    DATETIME = "DATETIME"
    GEOGRAPHY = "GEOGRAPHY"
    NUMERIC = "NUMERIC"
    BIGNUMERIC = "BIGNUMERIC"
    JSON = "JSON"
    RANGE = "RANGE"
    # for nested fields
    RECORD = "RECORD"
    STRUCT = "STRUCT"


class TableFieldMode(Enum):
    NULLABLE = "NULLABLE"
    REQUIRED = "REQUIRED"
    REPEATED = "REPEATED"


class TimePartitioningType(Enum):
    DAY = "DAY"
    HOUR = "HOUR"
    MONTH = "MONTH"
    YEAR = "YEAR"


class TableFieldSchema(BaseModel):
    """
    BigQuery table schema.

    Based on https://cloud.google.com/bigquery/docs/reference/rest/v2/tables#TableFieldSchema
    """

    name: str
    field_type: TableFieldType = Field(..., alias="type")
    mode: TableFieldMode = TableFieldMode.NULLABLE
    # fields for nested record types
    fields: list["TableFieldSchema"] | None = None
    description: str | None = None

    @field_validator("mode", mode="before")
    @classmethod
    def default_mode_as_nullable(cls: type["TableFieldSchema"], v: TableFieldMode | str | None) -> TableFieldMode:
        if v is None:
            return TableFieldMode.NULLABLE
        if isinstance(v, str):
            return TableFieldMode(v)
        return v


class TableSchema(BaseModel):
    """
    Main schema of the table.

    Based on https://cloud.google.com/bigquery/docs/reference/rest/v2/tables#TableSchema
    """

    fields: list[TableFieldSchema]


class TableTimePartitioning(BaseModel):
    """
    Time based partitioning for the table.

    Based on https://cloud.google.com/bigquery/docs/reference/rest/v2/tables#TimePartitioning
    """

    type: TimePartitioningType
    expiration_ms: str | None = Field(None, alias="expirationMs")
    field: str | None = None


class TableInsertResponse(BaseModel):
    kind: Literal["bigquery#tableDataInsertAllResponse"] = "bigquery#tableDataInsertAllResponse"
    insert_errors: list[TableInsertError] = Field(default_factory=list, alias="insertErrors")


class Table(BaseModel):
    """Schema for representing a BigQuery Table."""

    table_reference: TableReference = Field(..., alias="tableReference")
    description: str | None = None
    table_schema: TableSchema | None = Field(None, alias="schema")
    time_partitioning: TableTimePartitioning | None = Field(None, alias="timePartitioning")


class TableResponse(Table):
    """Get table response schema. Based on BigQueryTable schema."""

    kind: str
    id: str


class DatasetReference(BaseModel):
    dataset_id: str = Field(..., alias="datasetId")
    project_id: str | None = Field(None, alias="projectId")


class Dataset(BaseModel):
    """
    Create a new dataset in Bigquery.

    Based on https://cloud.google.com/bigquery/docs/reference/rest/v2/datasets#Dataset

    Only the dataset_reference is required for creating a new dataset.
    """

    dataset_reference: DatasetReference = Field(..., alias="datasetReference")
    friendly_name: str | None = Field(None, alias="friendlyName")
    description: str | None = None
    # GCP region
    location: str | None = None


class DatasetResponse(Dataset):
    kind: str | None = None
    id: str | None = None
    self_link: str | None = Field(None, alias="selfLink")
    creation_time: int | None = Field(None, alias="creationTime", description="Unix timestamp")
    last_modified_time: int | None = Field(None, alias="lastModifiedTime", description="Unix timestamp")

    def to_dataset(self) -> Dataset:
        return Dataset.model_validate(self.model_dump())


class DatasetListResponse(BaseModel):
    kind: str | None = None
    etag: str | None = None
    datasets: list[DatasetResponse] = Field(default_factory=list)
