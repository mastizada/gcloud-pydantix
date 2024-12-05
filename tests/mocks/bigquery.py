DATASET_LIST_RESPONSE = {
    "kind": "bigquery#datasetList",
    "etag": "apoDlfAOQy/5u5Qe8gTrmQ==",
    "datasets": [
        {
            "kind": "bigquery#dataset",
            "id": "test-project:test-dataset",
            "datasetReference": {"datasetId": "test-dataset", "projectId": "test-project"},
            "location": "EU",
        }
    ],
}

DATASET_GET_RESPONSE = {
    "kind": "bigquery#dataset",
    "etag": "L2dDdTFpl4uQPXv1a4g84Q==",
    "id": "test-project:test-dataset",
    "selfLink": "https://content-bigquery.googleapis.com/bigquery/v2/projects/test-project/datasets/test-dataset",
    "datasetReference": {"datasetId": "test-dataset", "projectId": "test-project"},
    "description": "Test description 2",
    "access": [
        {"role": "WRITER", "specialGroup": "projectWriters"},
        {"role": "OWNER", "specialGroup": "projectOwners"},
        {"role": "OWNER", "userByEmail": "emin@example.com"},
        {"role": "READER", "specialGroup": "projectReaders"},
    ],
    "creationTime": "1733435860474",
    "lastModifiedTime": "1733438476416",
    "location": "EU",
    "type": "DEFAULT",
    "maxTimeTravelHours": "168",
}

DATASET_PROJECT_NOT_FOUND = {
    "error": {
        "code": 404,
        "message": "Not found: Project incorrect-project",
        "errors": [{"message": "Not found: Project incorrect-project", "domain": "global", "reason": "notFound"}],
        "status": "NOT_FOUND",
    }
}

DATASET_GET_FULL_RESPONSE = {
    "kind": "bigquery#dataset",
    "etag": "oj9wg6Iv4wyU5A/9GamknA==",
    "id": "test-project:test-dataset",
    "selfLink": "https://content-bigquery.googleapis.com/bigquery/v2/projects/test-project/datasets/test-dataset",
    "datasetReference": {"datasetId": "test-dataset", "projectId": "test-project"},
    "access": [
        {"role": "WRITER", "specialGroup": "projectWriters"},
        {"role": "OWNER", "specialGroup": "projectOwners"},
        {"role": "OWNER", "userByEmail": "testing@test-project.iam.gserviceaccount.com"},
        {"role": "READER", "specialGroup": "projectReaders"},
    ],
    "creationTime": "1587403431739",
    "lastModifiedTime": "1587403431739",
    "location": "EU",
    "type": "DEFAULT",
    "maxTimeTravelHours": "168",
}

DATASET_CREATE_ALREADY_EXISTS = {
    "error": {
        "code": 409,
        "message": "Already Exists: Dataset test-project:test-dataset",
        "errors": [
            {"message": "Already Exists: Dataset test-project:test-dataset", "domain": "global", "reason": "duplicate"}
        ],
        "status": "ALREADY_EXISTS",
    }
}

DATASET_CREATE_SUCCESS = {
    "kind": "bigquery#dataset",
    "etag": "LeFM++F+81NrklybaAX1bA==",
    "id": "test-project:test-dataset",
    "selfLink": "https://content-bigquery.googleapis.com/bigquery/v2/projects/test-project/datasets/test-dataset",
    "datasetReference": {"datasetId": "test-dataset", "projectId": "test-project"},
    "description": "Test dataset",
    "access": [
        {"role": "WRITER", "specialGroup": "projectWriters"},
        {"role": "OWNER", "specialGroup": "projectOwners"},
        {"role": "OWNER", "userByEmail": "emin@example.com"},
        {"role": "READER", "specialGroup": "projectReaders"},
    ],
    "creationTime": "1733435860474",
    "lastModifiedTime": "1733435860474",
    "location": "EU",
    "type": "DEFAULT",
}

DATASET_PATCH_RESPONSE = {
    "kind": "bigquery#dataset",
    "etag": "L2dDdTFpl4uQPXv1a4g84Q==",
    "id": "test-project:test-dataset",
    "selfLink": "https://content-bigquery.googleapis.com/bigquery/v2/projects/test-project/datasets/test-dataset",
    "datasetReference": {"datasetId": "test-dataset", "projectId": "test-project"},
    "description": "Test description 2",
    "access": [
        {"role": "WRITER", "specialGroup": "projectWriters"},
        {"role": "OWNER", "specialGroup": "projectOwners"},
        {"role": "OWNER", "userByEmail": "emin@example.com"},
        {"role": "READER", "specialGroup": "projectReaders"},
    ],
    "creationTime": "1733435860474",
    "lastModifiedTime": "1733438476416",
    "location": "EU",
    "type": "DEFAULT",
    "maxTimeTravelHours": "168",
}
