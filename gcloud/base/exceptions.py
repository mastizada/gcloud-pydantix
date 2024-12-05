"""Shared error handling for Google Cloud Services."""

from pydantic import Field

from gcloud.base.utils import BaseModel


class ErrorProto(BaseModel):
    """
    Generic error message used in GCP.

    It might make sense to move it to shared module.
    https://cloud.google.com/bigquery/docs/reference/rest/v2/tables#errorproto
    """

    reason: str
    location: str | None = None
    message: str | None = None


class ErrorDetail(BaseModel):
    errors: list[ErrorProto]


class ErrorResponse(BaseModel):
    code: int | None = None
    message: str | None = None
    error: ErrorDetail | None = None
    # status enum: https://github.com/googleapis/googleapis/blob/master/google/rpc/code.proto
    status: str | None = None


class RequestError(Exception):
    """
    Request to GCP failed.

    https://google.aip.dev/193#http11json-representation
    """

    status_code: int = Field(..., description="HTTP status code from GCP")
    error: ErrorResponse

    def __init__(self, status_code: int, error: ErrorResponse):
        super().__init__(error.message)
        self.status_code = status_code
        self.error = error


class ServiceUnavailableError(Exception):
    """
    Request to GCP failed, but it can be retried.

    https://cloud.google.com/bigquery/docs/error-messages
    """

    status_code: int = Field(..., description="HTTP status code from GCP")
    error: ErrorResponse

    def __init__(self, status_code: int, error: ErrorResponse):
        super().__init__(error.message)
        self.status_code = status_code
        self.error = error
