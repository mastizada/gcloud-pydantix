from enum import Enum

from gcloud.base.utils import BaseModel


class TokenType(Enum):
    AUTHORIZED_USER = "authorized_user"
    GCE_METADATA = "gce_metadata"
    SERVICE_ACCOUNT = "service_account"


class TokenResponse(BaseModel):
    access_token: str
    expires_in: int
