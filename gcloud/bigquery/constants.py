from gcloud.base.constants import GCP_GENERIC_SCOPE

BIGQUERY_API_ROOT = "https://bigquery.googleapis.com"

# Access Scopes
BIGQUERY_MANAGE_SCOPE = "https://www.googleapis.com/auth/bigquery"
BIGQUERY_INSERT_DATA_SCOPE = "https://www.googleapis.com/auth/bigquery.insertdata"
BIGQUERY_SCOPES = [BIGQUERY_MANAGE_SCOPE, BIGQUERY_INSERT_DATA_SCOPE, GCP_GENERIC_SCOPE]
