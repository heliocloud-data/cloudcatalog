import os
import json
import boto3
import pandas as pd
import pytest
from unittest.mock import MagicMock
from io import BytesIO
from cloudcatalog import CloudCatalog, FailedS3Get, UnavailableData


@pytest.fixture
def test_catalog():
    return {
        "status": {"code": 1200, "message": "OK"},
        "catalog": [
            {
                "id": "test_dataset",
                "index": "s3://test-bucket/test_dataset/",
                "title": "Test Dataset",
                "start": "2020-01-01T00:00:00Z",
                "stop": "2021-12-31T23:59:59Z",
            }
        ],
    }


@pytest.fixture
def mock_s3_client(test_catalog):
    s3_client = MagicMock()
    s3_client.get_object.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "Body": MagicMock(read=lambda: json.dumps(test_catalog).encode("utf-8")),
    }
    return s3_client


@pytest.fixture
def mock_boto3_client(monkeypatch, mock_s3_client):
    def mock_client(service, **kwargs):
        if service == "s3":
            return mock_s3_client
        raise ValueError("Unexpected service in mock_boto3_client")

    monkeypatch.setattr(boto3, "client", mock_client)


def test_cloud_catalog_init(mock_boto3_client, test_catalog):
    fr = CloudCatalog("test-bucket", cache=False)

    assert fr.bucket_name == "test-bucket"
    assert fr.catalog == test_catalog
    assert fr.cache_folder is None


def test_cloud_catalog_init_unavailable_data(mock_s3_client, mock_boto3_client):
    mock_s3_client.get_object.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "Body": MagicMock(
            read=lambda: json.dumps(
                {"status": {"code": 1400, "message": "temporarily unavailable"}, "catalog": {}}
            ).encode("utf-8")
        ),
    }

    with pytest.raises(UnavailableData):
        CloudCatalog("test-bucket", cache=False)


def test_cloud_catalog_init_failed_s3_get(mock_s3_client, mock_boto3_client):
    mock_s3_client.get_object.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 404},
    }

    with pytest.raises(FailedS3Get):
        CloudCatalog("test-bucket", cache=False)


def test_cloud_catalog_get_catalog(mock_boto3_client, test_catalog):
    fr = CloudCatalog("test-bucket", cache=False)
    assert fr.get_catalog() == test_catalog


def test_cloud_catalog_get_entries_id_title(mock_boto3_client):
    fr = CloudCatalog("test-bucket", cache=False)
    assert fr.get_entries_id_title() == [("test_dataset", "Test Dataset")]


def test_cloud_catalog_get_entries_dict(mock_boto3_client):
    fr = CloudCatalog("test-bucket", cache=False)
    assert fr.get_entries_dict() == [
        {
            "id": "test_dataset",
            "index": "s3://test-bucket/test_dataset/",
            "title": "Test Dataset",
            "start": "2020-01-01T00:00:00Z",
            "stop": "2021-12-31T23:59:59Z",
        }
    ]


def test_cloud_catalog_get_entry(mock_boto3_client, test_catalog):
    fr = CloudCatalog("test-bucket", cache=False)
    entry = fr.get_entry("test_dataset")
    assert entry == test_catalog["catalog"][0]

    with pytest.raises(KeyError):
        fr.get_entry("nonexistent")


def test_cloud_catalog_request_cloud_catalog(mock_boto3_client, mock_s3_client):
    fr = CloudCatalog("test-bucket", cache=False)

    # Create the test FR data
    test_data = {
        "start": [
            "2020-01-01T00:00:00Z",
            "2020-01-02T00:00:00Z",
            "2020-12-31T23:59:59Z",
            "2021-12-30T23:59:59Z",
        ],
        "enddate": [
            "2020-01-01T23:59:59Z",
            "2020-01-02T23:59:59Z",
            "2020-12-31T23:59:59Z",
            "2021-12-30T23:59:59Z",
        ],
        "metadata": ["a", "b", "c", "d"],
    }
    test_df = pd.DataFrame(test_data)

    def mock_get_object(Bucket, Key):
        if Key.endswith(".csv"):
            buf = BytesIO()
            test_df.to_csv(buf, index=False)
            buf.seek(0)
            return {"ResponseMetadata": {"HTTPStatusCode": 200}, "Body": buf}
        else:
            return {"ResponseMetadata": {"HTTPStatusCode": 404}}

    mock_s3_client.get_object.side_effect = mock_get_object

    # Test request_cloud_catalog
    result = fr.request_cloud_catalog(
        catalog_id="test_dataset",
        start_date="2020-01-01T00:00:00Z",
        stop_date="2021-12-31T23:59:59Z",
    )

    assert isinstance(result, pd.DataFrame)
    assert "start" in result.columns


def test_cloud_catalog_request_cloud_catalog_invalid_dates(mock_boto3_client):
    fr = CloudCatalog("test-bucket", cache=False)

    with pytest.raises(ValueError):
        fr.request_cloud_catalog(
            catalog_id="test_dataset",
            start_date="2022-01-01T00:00:00Z",
            stop_date="2021-12-31T23:59:59Z",
        )


def test_cloud_catalog_request_cloud_catalog_unknown_catalog_id(mock_boto3_client):
    fr = CloudCatalog("test-bucket", cache=False)

    with pytest.raises(KeyError):
        fr.request_cloud_catalog(
            catalog_id="unknown",
            start_date="2020-01-01T00:00:00Z",
            stop_date="2021-12-31T23:59:59Z",
        )
