GCE_METADATA_BASE = "http://metadata.google.internal/computeMetadata/v1"
GCE_ENDPOINT_TOKEN = f"{GCE_METADATA_BASE}/instance/service-accounts/default/token?recursive=true"

REFRESH_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}
GCE_METADATA_HEADERS = {"metadata-flavor": "Google"}
