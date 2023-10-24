import pytest
from cloudcatalog import EntireCatalogSearch


@pytest.fixture
def search():
    # won't actually use this catalog, but need a working json file to just do tests
    return EntireCatalogSearch()


@pytest.fixture
def mock_catalog():
    return {
        "catalog": [
            {"id": "file1", "index": "s3://helio-public/MMS", "title": "File 1"},
            {"id": "file2", "index": "s3://helio-public/MMS", "title": "File 2"},
            {"id": "file3", "index": "s3://helio-public/MMS", "title": "Another file"},
            {"id": "file4", "index": "s3://helio-public/MMS", "title": "File 4"},
            {"id": "file5", "index": "s3://helio-public/SDO", "title": "File 5"},
        ]
    }


def test_search_by_id(search, mock_catalog):
    # Test searching for an ID that exists in one catalog
    search.combined_catalog = [mock_catalog]
    results = search.search_by_id("file1")
    assert len(results) == 1
    assert results[0]["id"] == "file1"

    # Test searching for an ID that exists in multiple catalogs
    search.combined_catalog = [mock_catalog, mock_catalog]
    results = search.search_by_id("file2")
    assert len(results) == 2
    assert results[0]["id"] == "file2"
    assert results[1]["id"] == "file2"

    # Test searching for an ID that doesn't exist
    search.combined_catalog = [mock_catalog]
    results = search.search_by_id("file6")
    assert len(results) == 0


def test_search_by_title(search, mock_catalog):
    # Test searching for a substring that exists in one catalog
    search.combined_catalog = [mock_catalog]
    results = search.search_by_title("file")
    assert len(results) == 5
    assert set(entry["id"] for entry in results) == {"file1", "file2", "file3", "file4", "file5"}

    # Test searching for a substring that exists in multiple catalogs
    # (per docs, ids are unique, but for testing..)
    search.combined_catalog = [mock_catalog, mock_catalog]
    results = search.search_by_title("file")
    assert len(results) == 10
    assert set(entry["id"] for entry in results) == {"file1", "file2", "file3", "file4", "file5"}

    # Test searching for a substring that doesn't exist
    search.combined_catalog = [mock_catalog]
    results = search.search_by_title("xyz")
    assert len(results) == 0


def test_search_by_keywords(search, mock_catalog):
    # Test searching for keywords that exist in one catalog
    search.combined_catalog = [mock_catalog]
    results = search.search_by_keywords(["file", "s3://helio-public/MMS"])
    assert len(results) == 5
    assert results[0]["id"] == "file1"

    search.combined_catalog = [mock_catalog]
    results = search.search_by_keywords(["file1", "s3://helio-public/MMS"])
    assert len(results) == 4
    assert results[0]["id"] == "file1"

    # Test searching for keywords that exist in multiple catalogs
    search.combined_catalog = [mock_catalog, mock_catalog]
    results = search.search_by_keywords(["file", "s3://helio-public/MMS"])
    assert len(results) == 10
    assert results[0]["id"] in {"file1", "file2", "file3", "file4"}
    assert results[1]["id"] in {"file1", "file2", "file3", "file4"}

    # Test searching for keywords that don't exist
    search.combined_catalog = [mock_catalog]
    results = search.search_by_keywords(["filea", "s3://helio-pWQublic/MMS"])
    assert len(results) == 0
