"""
Validation log for the cloudcatalog library
"""


import json
import logging
import os
from datetime import datetime
from math import ceil
from typing import Dict, Optional, Any

import boto3
import dateutil
import requests


class FailedS3Get(Exception):
    pass


class UnavailableData(Exception):
    pass


class Validator:
    def __init__(self, catalog_url: Optional[str] = None, **client_kwargs) -> None:
        self.combined_catalog = []
        self.global_catalog = None
        self.s3_client = boto3.client("s3", **client_kwargs)
        self._fetch_and_combine_catalogs(catalog_url)

    def _fetch_and_combine_catalogs(self, catalog_url: Optional[str] = None) -> None:
        """
        Fetches the global catalog and combines it with local catalogs.

        Parameters:
            catalog_url: URL of the global catalog. If not provided, it is read from the environment
             variable ROOT_CATALOG_REGISTRY_URL.
        """
        # Load the global catalog
        if catalog_url is None:
            catalog_url = os.getenv("ROOT_CATALOG_REGISTRY_URL")
            if catalog_url is None:
                raise ValueError(
                    "No environment variable ROOT_CATALOG_REGISTRY_URL nor was an explicit "
                    "catalog_url passed in."
                )

        response = requests.get(catalog_url)
        if response.status_code != 200:
            raise requests.ConnectionError(
                f"Get Request for Global Catalog Failed. Catalog url: {catalog_url}"
            )

        self.global_catalog = response.json()
        # Key Error if missing registry (invalid catalog)
        entries = self.global_catalog["registry"]

        failed_entries = []
        for entry in entries:
            # Key Error if missing endpoint (invalid catalog)
            bucket_name = entry["endpoint"]
            if bucket_name.startswith("s3://"):
                bucket_name = bucket_name[5:]
            bucket_name = bucket_name.rstrip("/")

            try:
                response = self.s3_client.get_object(Bucket=bucket_name, Key="catalog.json")
                status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                if "Body" not in response and status != 200:
                    raise FailedS3Get(
                        f"Failed to Get Catalog from Bucket. Status: {status}. Response: {response}"
                    )

                catalog_bytes = response["Body"].read()
                local_catalog = json.loads(catalog_bytes)

                if local_catalog["status"] == "1400/temporarily unavailable":
                    raise UnavailableData(self.catalog["status"])

                self.combined_catalog.append(local_catalog)

            except Exception as e:
                # Key Error if missing name or region (invalid catalog)
                logging.warning(
                    f"Failed to fetch local catalog for entry {entry['name']} ({entry['region']}): {e}\n"
                )
                failed_entries.append((entry["name"], entry["region"]))

        if len(failed_entries) > 0:
            msg = f"Failed Local Catalog Fetches ({len(failed_entries)}/{len(entries)}): \n[\n"
            for entry in failed_entries:
                msg += f"    {entry[0]} ({entry[1]})\n"
            msg += "]"
            logging.error(msg)

    def validate_global_uniqueness(self) -> None:
        """
        Validates the uniqueness of name and region combinations the the global catalog entries.
        """
        success = True
        unique_identifiers = set()
        dups = 0

        for catalog_entry in self.global_catalog["registry"]:
            identifier = f"{catalog_entry['name']} ({catalog_entry['region']})"
            if identifier in unique_identifiers:
                logging.warning(f"{identifier} is not a unique entry.")
                dups += 1
            else:
                unique_identifiers.add(identifier)

        if dups == 0:
            logging.info("Catalog name + region uniqueness passed.")
        else:
            logging.warning(f"Catalog name + region uniqueness failed. Duplicates: {dups}")
            success = False
        return success

    def validate_local_uniqueness(self) -> None:
        """
        Validates the uniqueness of ID across all catalogs.
        """
        success = True
        unique_identifiers = {}
        dups = 0
        for catalog in self.combined_catalog:
            for entry in catalog["catalog"]:
                identifier = entry["id"]
                if identifier in unique_identifiers:
                    logging.warning(
                        f"{identifier} is not a unique entry. Conflicts in "
                        f"{unique_identifiers[identifier]} and {catalog['name']}"
                    )
                    dups += 1
                else:
                    unique_identifiers[identifier] = catalog["name"]

        if dups == 0:
            logging.info("Local catalog IDs are unique across all catalogs. Passed.")
        else:
            logging.warning(
                f"Local catalog IDs are not unique across all catalogs. Failed. Duplicates: {dups}"
            )
            success = False
        return success

    def validate_local_catalog_schema(self, local_catalog: Dict[str, Any]) -> None:
        """
        Validates the schema of a local catalog.

        Parameters:
            local_catalog: The local catalog to be validated.
        """
        success = True
        schema = {
            "type": "object",
            "properties": {
                "Cloudy": {"type": "string"},
                "endpoint": {"type": "string", "pattern": "s3://\S+/"},
                "name": {"type": "string"},
                "region": {"type": "string"},
                "egressPolicy": {"type": "string"},
                "contact": {"type": "string"},
                "description": {"type": "string"},
                "citation": {"type": "string"},
                "catalog": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "pattern": "^[a-zA-Z0-9-_]+$"},
                            "loc": {"type": "string", "pattern": "s3://\S+/.*"},  # support https?
                            "title": {"type": "string"},
                            "start": {
                                "type": "string",
                                "pattern": "\d{4}-\d{2}-\d{2}T\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?Z",
                            },
                            "stop": {
                                "type": "string",
                                "pattern": "\d{4}-\d{2}-\d{2}T\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?Z",
                            },
                            "modification": {
                                "type": "string",
                                "pattern": "\d{4}-\d{2}-\d{2}T\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?Z",
                            },
                            "indexFormat": {
                                "type": "string",
                                "enum": ["csv", "csv-zip", "parquet"],
                            },
                            "fileFormat": {"type": "string"},
                            "description": {"type": "string"},
                            "resource": {"type": "string"},
                            "creation": {
                                "type": "string",
                                "pattern": "\d{4}-\d{2}-\d{2}T\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?Z",
                            },
                            "citation": {"type": "string"},
                            "contact": {"type": "string"},
                            "contactID": {"type": "string"},
                            "aboutURL": {"type": "string"},
                        },
                        "required": [
                            "id",
                            "loc",
                            "title",
                            "start",
                            "stop",
                            "modification",
                            "indexFormat",
                            "fileFormat",
                        ],
                        "additionalProperties": False,
                    },
                },
                "status": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "integer"},
                        "message": {"type": "string"},
                    },
                    "required": ["code", "message"],
                    "additionalProperties": False,
                },
            },
            "required": [
                "Cloudy",
                "endpoint",
                "name",
                "region",
                "egressPolicy",
                "catalog",
                "status",
            ],
            "additionalProperties": False,
        }

        try:
            jsonschema.validate(instance=local_catalog, schema=schema)
            logging.info("Local catalog schema validation passed.")
        except jsonschema.exceptions.ValidationError as e:
            logging.error(f"Local catalog schema validation failed: {e.message}")
            success = False
        return success

    def validate_all_local_catalog_schemas(self) -> None:
        """
        Validates the schema of all local catalogs in the combined catalog.
        """
        success = True
        for index, local_catalog in enumerate(self.combined_catalog):
            logging.info(f"Validating local catalog {index} {local_catalog['name']}:")
            success = success and self.validate_local_catalog_schema(local_catalog)
        return success

    def validate_global_catalog_schema(self) -> None:
        """
        Validates the schema of the global catalog.
        """
        success = True
        schema = {
            "type": "object",
            "properties": {
                "CloudCatalog": {"type": "string"},
                "modification": {
                    "type": "string",
                    "pattern": "\d{4}-\d{2}-\d{2}T\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?Z",
                },
                "registry": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "endpoint": {"type": "string", "pattern": "s3://\S+/"},
                            "name": {"type": "string"},
                            "provider": {"type": "string"},
                            "region": {"type": "string"},
                        },
                        "required": ["endpoint", "name", "region"],  # make provider required?
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["CloudCatalog", "modification", "registry"],
            "additionalProperties": False,
        }

        try:
            jsonschema.validate(instance=self.global_catalog, schema=schema)
            logging.info("Global catalog schema validation passed.")
        except jsonschema.exceptions.ValidationError as e:
            logging.error(f"Global catalog schema validation failed: {e.message}")
            success = False
        return success

    def validate_local_catalog_file_registries(self, local_catalog: Dict[str, Any]) -> None:
        """
        Validates local file registries in the provided local catalog.

        Parameters:
            local_catalog: The local catalog containing file registries to be validated.
        """
        success = True
        failed_reg_files = 0
        for entry in local_catalog["catalog"]:
            try:
                eid, loc, catalog_start_date, catalog_stop_date = (
                    entry["id"],
                    entry["loc"],
                    entry["start"],
                    entry["stop"],
                )
                ndxformat = "csv"

                year_start_date = dateutil.parser.parse(catalog_start_date[:-1]).year

                def ceil_year(date):
                    return ceil(
                        date.year + (date - datetime(date.year, 1, 1)).total_seconds() * 3.17098e-8
                    )

                year_stop_date = ceil_year(dateutil.parser.parse(catalog_stop_date[:-1]))

                bucket_name = loc[5:].split("/", 1)[0]
                loc = loc[len(bucket_name) + 6 :]

                for year in range(year_start_date, year_stop_date):
                    filename = f"{eid}_{year}.{ndxformat}"

                    response = self.s3_client.get_object(Bucket=bucket_name, Key=loc + filename)
                    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                    if "Body" not in response or status != 200:
                        raise FailedS3Get(
                            f"Failed to get a cloud catalog object. Status: {status}. Response: {response}"
                        )
            except Exception as e:
                failed_reg_files += 1
                logging.warning(
                    f"Failed to fetch local cloud catalog files for entry {entry['id']}: {e}\n"
                )
        if failed_reg_files == 0:
            logging.info("Loading Local Catalog File Registries Passed.")
        else:
            logging.error(
                f"Loading Local Catalog File Registries Failed. Failures: {failed_reg_files}"
            )
            success = False
        return success

    def validate_all_local_catalog_file_registries(self) -> None:
        """
        Validates the file registries for all local catalogs in the combined catalog.
        """
        success = True
        for index, local_catalog in enumerate(self.combined_catalog):
            logging.info(
                f"Validating local catalog file registries {index} {local_catalog['name']}:"
            )
            success = success and self.validate_local_catalog_file_registries(local_catalog)
        return success

    def validate(self) -> None:
        """
        Performs a complete validation of the catalogs.
        Validates the global catalog schema, local catalog schemas, uniqueness of entries, and local catalog file registries.
        """
        success = self.validate_global_catalog_schema()
        success = self.validate_all_local_catalog_schemas() and success
        success = self.validate_global_uniqueness() and success
        sucesss = self.validate_local_uniqueness() and success
        success = self.validate_all_local_catalog_file_registries() and success
        return success

    def get_global_catalog(self) -> Dict[str, Any]:
        return self.global_catalog

    def get_local_catalogs(self) -> Dict[str, Any]:
        return self.combined_catalog
