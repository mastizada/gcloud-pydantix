from enum import Enum
from typing import TypeVar

from gcloud.base.utils import BaseModel

GCP_GENERIC_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class RequestMethod(Enum):
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
