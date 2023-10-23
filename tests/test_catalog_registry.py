import pytest
from cloudcatalog import CatalogRegistry


@pytest.fixture
def catalog_registry():
    # Actually try to load a real catalog, but then overwrites contents just in case of changes
    cr = CatalogRegistry()
    cr.catalog = {
        "CloudCatalog": "0.1",
        "modificationDate": "2022-01-01T00:00Z",
        "registry": [
            {
                "endpoint": "s3://helio-public/",
                "name": "GSFC HelioCloud Public Temp",
                "region": "us-east-1",
            },
            {
                "endpoint": "s3://helio-public2/",
                "name": "GSFC HelioCloud Public Temp",
                "region": "us-east-2",
            },
            {
                "endpoint": "s3://helio-public/MMS/",
                "name": "GSFC HC MMS bucket",
                "region": "us-east-1",
            },
            {
                "endpoint": "s3://gov-nasa-hdrl-data2/",
                "name": "GSFC HelioCloud Set 2",
                "region": "us-east-1",
            },
            {
                "endpoint": "s3://edu-apl-helio-public/",
                "name": "APL HelioCLoud",
                "region": "us-west-1",
            },
        ],
    }
    return cr


def test_get_catalog(catalog_registry):
    catalog = catalog_registry.get_catalog()
    assert isinstance(catalog, dict)
    assert len(catalog) > 0


def test_get_registry(catalog_registry):
    registry = catalog_registry.get_registry()
    assert isinstance(registry, list)
    assert len(registry) > 0
    for item in registry:
        assert isinstance(item, dict)


def test_get_entries_name_region(catalog_registry):
    entries = catalog_registry.get_entries_name_region()
    assert isinstance(entries, list)
    assert len(entries) > 0
    for entry in entries:
        assert isinstance(entry, tuple)
        assert len(entry) == 2


@pytest.mark.parametrize(
    "name, region_prefix, force_first",
    [
        ("APL Heliocloud", "", False),
        ("GSFC HelioCloud Public Temp", "us-east-1", False),
        ("GSFC HelioCloud Public Temp", "us-east", True),
    ],
)
def test_get_endpoint(catalog_registry, name, region_prefix, force_first):
    endpoint = catalog_registry.get_endpoint(name, region_prefix, force_first)
    assert isinstance(endpoint, str)
    assert len(endpoint) > 0


@pytest.mark.parametrize(
    "name, region_prefix, force_first",
    [("GSFC HelioCloud Public Temp", "", False), ("GSFC HelioCloud Public Temp", "us-east", False)],
)
def test_get_endpoint(catalog_registry, name, region_prefix, force_first):
    with pytest.raises(ValueError):
        endpoint = catalog_registry.get_endpoint(name, region_prefix, force_first)
