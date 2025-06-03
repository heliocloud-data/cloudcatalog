"""
CloudCatalog. 'import cloudcatalog'.

This tool is designed for retrieving file catalog (index) files from a
specific ID entry in a catalog within a bucket. It also includes
search functionality for searching through all data index catalogs
found in the bucket list.

# Find all available catalogs
cr = cloudcatalog.CatalogRegistry()
print(cr.get_catalog())
print(cr.get_entries())

# Request a specific data item from the NASA TOPS bucket
fr = cloudcatalog.CloudCatalog("s3://gov-nasa-hdrl-data1/")
fr_id = 'a_dataset_id_from_the_catalog'
start_date = '2007-02-01T00:00:00Z'
stop_date = '2007-03-01T00:00:00Z'
myfiles = fr.request_cloud_catalog(
              fr_id, start_date=start_date, end_date=end_date
          )
"""

from io import BytesIO
from datetime import datetime
from math import ceil
from typing import List, Dict, Tuple, Union, Optional, Callable
import os
import json
import requests
import logging
import dateutil
import re
import pandas as pd
import boto3
from botocore import UNSIGNED
from botocore.client import Config

"""
To support other clouds, add code to fetch_S3 and s3url_to_https, and
modify the variable bucket_prefix in class CloudCatalog.
"""


# Added handler that first tries S3 anonymous, then tries https/egreess
def s3url_to_https(s3url):
    """Formula is  s3://BUCKET/KEY -> https://BUCKET.s3.amazonaws.com/KEY"""
    # allowing https addition
    if s3url.startswith("http"):
        return s3url
    mybucket, mykey = s3url_to_bucketkey(s3url)
    url = "https://" + mybucket + ".s3.amazonaws.com/" + mykey
    return url


def s3url_to_bucketkey(s3url, bucket_prefix="s3://"):
    """
    Extracts the S3 bucket name and file key from an S3 URL.

    S3 paths are weird, bucket + everything else, e.g.
    s3://b1/b2/b3/t.txt would be bucket b1, file b2/b3/t.txt

    :param s3url: The S3 URL to extract the bucket name and file key from.

    :returns: A tuple containing the S3 bucket name and file key.
    """
    # S3 paths are weird, bucket + everything else, e.g.
    # s3://b1/b2/b3/t.txt would be bucket b1, file b2/b3/t.txt
    name2 = re.sub(rf"{bucket_prefix}", "", s3url)
    s = name2.split("/", 1)
    mybucket = s[0]
    myfilekey = s[1] if len(s) > 1 else ""  # Want None if no key?
    return mybucket, myfilekey


def fetch_S3(s3url, unsigned=True, region=None, rawbytes=False, **client_kwargs):
    # default is JSON, but can return raw bytes
    # print("Trying S3, unsigned=",unsigned,"region=",region)
    bucket_prefix = "s3://"
    mybucket, mykey = s3url_to_bucketkey(s3url, bucket_prefix=bucket_prefix)
    # print("Looking for: ",mybucket,mykey)
    if unsigned:
        if region != None:
            s3_client = boto3.client(
                "s3",
                config=Config(signature_version=UNSIGNED),
                region=region,
                **client_kwargs,
            )
        else:
            s3_client = boto3.client(
                "s3", config=Config(signature_version=UNSIGNED), **client_kwargs
            )
    else:
        if region != None:
            s3_client = boto3.client("s3", region=region, **client_kwargs)
        else:
            s3_client = boto3.client("s3", **client_kwargs)

    response = s3_client.get_object(Bucket=mybucket, Key=mykey)
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    # print("  Success S3 unsigned",status)
    if "Body" in response and status == 200:
        catalog_bytes = response["Body"].read()
        if rawbytes:
            catalog = catalog_bytes
        else:
            catalog = json.loads(catalog_bytes)
    elif status != 200:
        print("Error, status = ", status)
    return status, catalog


def fetch_url(s3url, rawbytes=False):
    # default is JSON, but can return raw bytes
    httpurl = s3url_to_https(s3url)
    response = requests.get(httpurl)
    status = response.status_code
    if rawbytes:
        catalog = response.content
    else:
        catalog = response.json()
    return status, catalog


def fetch_S3orURL(s3url, region="us-east-1", rawbytes=False, **client_kwargs):
    """To get around vagualities of S3 access, this tries a cascade of:
    straight fetch of S3 using your existing permissions
    fetch S3 unsigned/anonymous
    fetch S3 for a specified region only, defaulting to us-east-1
    fetch the S3 contents via the AWS-equivalent URL
    """

    try:
        # print("Calling unsigned")
        status, catalog = fetch_S3(
            s3url, unsigned=True, rawbytes=rawbytes, **client_kwargs
        )
    except:
        try:
            # print("Calling signed")
            status, catalog = fetch_S3(
                s3url, unsigned=False, rawbytes=rawbytes, **client_kwargs
            )
        except:
            try:
                # print("Calling region")
                status, catalog = fetch_S3(
                    s3url,
                    unsigned=True,
                    region=region,
                    rawbytes=rawbytes,
                    **client_kwargs,
                )
            except:
                try:
                    # print("Calling url")
                    status, catalog = fetch_url(s3url, rawbytes=rawbytes)
                    if status == 404:
                        return None
                except:
                    # print("Cannot fetch catalog, exiting.")
                    return None
    if rawbytes:
        fr_bytes_file = BytesIO()
        fr_bytes_file.write(catalog)
        fr_bytes_file.seek(0)
        return fr_bytes_file
    else:
        return catalog


class CatalogRegistry:
    """Use to work with the the global catalog (catalog of catalogs)."""

    def __init__(self, catalog_url: Optional[str] = None) -> None:
        """
        Parameters:
            catalog_url: either the environment variable
                         `ROOT_CATALOG_REGISTRY_URL` if it exists
                         or the smce heliocloud global catalog by default,
                         otherwise the explicitly passed in url.
        """
        # Set the catalog URL (env variable or default if not manually provided)
        if catalog_url is None:
            catalog_url = os.getenv("ROOT_CATALOG_REGISTRY_URL")
            if catalog_url is None:
                catalog_url = "http://heliocloud.org/catalog/HelioDataRegistry.json"
        self.catalog_url = catalog_url

        # Load the content from json
        response = requests.get(self.catalog_url)
        if response.status_code == 200:
            self.catalog = response.json()
        else:
            raise requests.ConnectionError(
                f"Get Request for Global Catalog Failed. Catalog url: {self.catalog_url}"
            )

        # Check global catalog format assumptions
        if "registry" not in self.catalog:
            raise KeyError("Invalid catalog. Missing registry key.")
        for reg_entry in self.catalog["registry"]:
            if (
                "endpoint" not in reg_entry
                or "name" not in reg_entry
                or "region" not in reg_entry
            ):
                raise KeyError(
                    f"Invalid registry entry in catalog. Missing endpoint or name or region key. Registry entry: {reg_entry}"
                )

    def get_catalog(self) -> Dict:
        """
        Get the global catalog with all metadata and registry entries.

        Returns:
            The global catalog dict
        """
        return self.catalog

    def get_registry(self) -> List[Dict]:
        """
        Get the registry values in the global catalog.

        Returns:
            A list of catalog dicts, which are each entry in the registry.
        """
        return self.catalog["registry"]

    def get_entries_name_region(self) -> List[Tuple[str, str]]:
        """
        Get the entry names and region of each entry in the registry.

        Returns:
            A list of tuples with the name and region from the
            global catalog registry.
        """
        # Get the name and region of each entry in the catalog
        return [(x["name"], x["region"]) for x in self.catalog["registry"]]

    def get_entries(self):
        """
        Get all data for a given registry

        Returns:
            A dictionary for that entry
        """
        # Get the name and region of each entry in the catalog
        myjson = [x for x in self.catalog["registry"]]
        if myjson is not None:
            myjson = myjson[0]
        return myjson

    def get_endpoint(
        self, name: str, region_prefix: str = "", force_first: bool = False
    ) -> str:
        """
        Get the s3 endpoint given the name and region.

        Parameters:
            name: Name of the endpoint.
            region_prefix (optional, str,): Prefix for a region.
            force_first (optional, defaults to False, bool): If True,
                  returns the first entry regardless of name+region uniqueness.

        Returns:
            The URI of the endpoint.
        """
        # Find registries that match the specified name and region prefix
        registries = [
            x
            for x in self.catalog["registry"]
            if x["name"] == name and x["region"].startswith(region_prefix)
        ]
        # Check to make sure all entries have unique names + prefixed region
        if not force_first and len(registries) > 1:
            if len(set(x["region"] for x in registries)) == 1:
                raise ValueError(
                    "Entries do not all have unique names. You may enable force_first to choose first option."
                )
            else:
                raise ValueError(
                    "Entries do not all have unique names but have different regions, please further specify region_prefix."
                )
        elif len(registries) == 0:
            raise KeyError("No endpoint found with given name and region_prefix.")
        return registries[0]["endpoint"]


class FailedS3Get(Exception):
    """
    A custom exception for any errors relating to s3 that are not already
    thrown by boto.
    """

    pass


class UnavailableData(Exception):
    """
    A custom exception for when the catalog indicates the dataset is
    unavailable.
    """

    pass


class CloudCatalog:
    """
    Use to work with a specific bucket (obtained from the global catalog) and
    the associated catalog in the bucket.
    """

    def __init__(
        self,
        bucket_name: str,
        cache_folder: Optional[str] = None,
        cache: bool = False,
        **client_kwargs,
    ) -> None:
        """
        Parameters:
            bucket_name (str): The name of the s3 bucket.
            cache_folder (str): Folder to store the file catalog cache,
                                defaults to bucket_name + '_cache'.
            cache (optional, defaults to False, bool): Determines if any files
                  should be cached so that S3 pulling
                  is not unnecessarily done. If a cache_folder is provided,
                  this is forced to false because some archives
                  e.g. CDAWeb updates frequently.
            client_kwargs: parameters for boto3.client:
                   region_name, aws_acces_key_id, aws_secret_access_key, etc.
        """
        # Remove s3 uri info if provided
        bucket_prefix = "s3://"
        if bucket_name.startswith(bucket_prefix):
            bucket_name = bucket_name[5:]
        bucket_name = bucket_name.rstrip("/")

        # Store the bucket name for future use
        self.bucket_name = bucket_name

        self.cache = cache

        self.catalog = fetch_S3orURL(bucket_name + "/catalog.json", **client_kwargs)

        if self.catalog == None:
            raise KeyError(f"Invalid catalog, does not Exist. Catalog: {self.catalog}")

        # Check catalog format assumptions
        if any([key not in self.catalog for key in ["status", "catalog"]]):
            raise KeyError(
                f"Invalid catalog. Missing either status or catalog key. Catalog: {self.catalog}"
            )

        # Check status and rasie exception
        if self.catalog["status"]["code"] == 1400:
            raise UnavailableData(self.catalog["status"])

        # Check catalog entries format assumptions
        for entry in self.catalog["catalog"]:
            missing_keys = [
                key
                for key in ["id", "index", "title", "start", "stop"]
                if key not in entry
            ]
            if len(missing_keys) > 0:
                raise KeyError(
                    f"Invalid catalog entry. Missing keys ({missing_keys}) in entry: {entry}"
                )
            loc = entry["index"]

            # allowing https addition
            if not (
                (loc.startswith(bucket_prefix) or loc.startswith("http"))
                and loc[-1] == "/"
            ):
                raise ValueError(f"Invalid index in catalog entry. index: {loc}")
            # could check if start is less than stop here

        # Set and create the folder for caching
        self.cache_folder = None
        if cache:
            if cache_folder is None:
                cache_folder = self.bucket_name + "_cache"
            self.cache_folder = cache_folder
            if self.cache_folder is not None and not os.path.exists(self.cache_folder):
                os.mkdir(self.cache_folder)

            # Copy the content of the catalog to this file (overwrites)
            with open(os.path.join(cache_folder, "catalog.json"), "w") as file:
                json.dump(self.catalog, file, indent=4, ensure_ascii=False)

    def get_catalog(self) -> Dict:
        """
        Gets the raw catalog downloaded from the bucket.

        Returns:
            The catalog dict.
        """
        return self.catalog

    def get_entries_id_title(self) -> List[Tuple[str, str]]:
        """
        Get just the entry id and title of each entry in the catalog.

        Returns:
            A list of tuples with the id and title from the
            global catalog registry.
        """
        # Get the name and region of each entry in the catalog
        return [(x["id"], x["title"]) for x in self.catalog["catalog"]]

    def get_entries_dict(self) -> List[Dict]:
        """
        Get all the items of each entry in the catalog.

        Returns:
            The json items from the catalog
        """
        return self.catalog["catalog"]

    def get_entry(self, entry_id: str) -> Dict:
        """
        Get the entry (with full info) using the given entry_id.

        Returns:
            A list of tuples with the id and title from the
            global catalog registry.
        """
        entries = [x for x in self.catalog["catalog"] if x["id"] == entry_id]
        if len(entries) == 0:
            raise KeyError(f"No entries found with entry_id ({entry_id}).")
        elif len(entries) > 1:
            raise ValueError(
                f"Invalid catalog with multiple entries with the same ID. ID: {entry_id}"
            )
        return entries[0]

    def date2datetime(self, start_date):
        # Make dates conform with Restricted ISO 8601 standard
        if start_date[-1] != "Z":
            start_date += "Z"
        # Convert dates to datetime object
        if not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?Z", start_date
        ):
            raise ValueError(
                "start_date must follow the format XXXX-XX-XXTXXZ with at least the year, month, day, and hour specified."
            )
        start_date = dateutil.parser.parse(start_date[:-1])
        return start_date

    def ceil_year(self, date):
        return ceil(
            date.year + (date - datetime(date.year, 1, 1)).total_seconds() * 3.17098e-8
        )

    def year_range(self, catalog_start_date, start_date, direction="max"):
        # assuming Z ends date
        catalog_year_start_date = dateutil.parser.parse(catalog_start_date[:-1]).year
        if start_date is None:
            year_start_date = catalog_year_start_date
        else:
            if direction == "max":
                year_start_date = max(catalog_year_start_date, start_date.year)
            else:
                year_start_date = min(catalog_year_start_date, start_date.year)
        return year_start_date

    def request_cloud_catalog(
        self,
        catalog_id: str,
        start_date: Optional[str] = None,
        stop_date: Optional[str] = None,
        overwrite: bool = False,
    ) -> pd.DataFrame:
        """
        Request the files in the dataset catalog within the provided times
        from the s3 bucket.

        Parameters:
            catalog_id (str): The id of the catalog entry in the s3 bucket.
            start_date (str): Start date for which files are needed
                              (default None). ISO 8601 standard.
            stop_date (str): End date for which files are needed
                              (default None). ISO 8601 standard.
            overwrite (bool): Overwrite files already cached if within request
                              cache in initilization must have been true.

        Returns:
            A pandas Dataframe containing the requested dataset catalog.
        """

        # everything else assumes typical time series data

        start_date = self.date2datetime(start_date)
        stop_date = self.date2datetime(stop_date)

        # Check if start date is less or equal than end date
        if stop_date < start_date:
            raise ValueError(
                f"start_date ({start_date}) must be equal or less than stop_date ({stop_date})."
            )

        # Get the entry with given catalog id from the list of catalogs
        entry = [
            catalog_entry
            for catalog_entry in self.catalog["catalog"]
            if catalog_entry["id"] == catalog_id
        ]

        # Raises error if no matching entry is found
        if len(entry) == 0:
            raise KeyError(f"No catalog entry found with id: {catalog_id}")
        elif len(entry) > 1:
            raise ValueError(f"No unique catalog entry found with id: {catalog_id}")
        else:
            entry = entry[0]

        # Get some necessary variables
        eid, loc, catalog_start_date, catalog_stop_date = (
            entry["id"],
            entry["index"],
            entry["start"],
            entry["stop"],
        )
        ndxformat = "csv"  # entry['ndxformat']

        # If caching
        if self.cache_folder is None:
            path = None
        else:
            # Create the path for storing cached files and folder if not exist
            path = os.path.join(self.cache_folder, catalog_id)
            if not os.path.exists(path):
                os.mkdir(path)

        # Compute minimum and maximum year from start and end date respectively
        year_start_date = self.year_range(
            catalog_start_date, start_date, direction="max"
        )
        year_stop_date = self.year_range(catalog_stop_date, stop_date, direction="min")

        # Local or different: Could be same bucket or different bucket
        # not enforcing being same bucket
        # allowing https addition
        if not loc.startswith("http"):
            bucket_name = loc[5:].split("/", 1)[0]
            loc = loc[len(bucket_name) + 6 :]

        # Define empty array for storing data frames
        frs = []

        # Loop through all the years

        for year in range(year_start_date, year_stop_date + 1):
            filename = f"{eid}_{year}.{ndxformat}"

            if path is None:
                filepath = None
            else:
                filepath = os.path.join(path, filename)

            # If file does not exist download it from s3
            # And save it to the given path
            if (
                not self.cache
                or overwrite
                or (filepath is not None and not os.path.exists(filepath))
            ):
                # If have ListBucket perms, no such key error will be raised
                # instead of client error
                # allowing https addition
                if loc.startswith("http"):
                    fr_bytes_file = fetch_S3orURL(loc + filename, rawbytes=True)
                else:
                    fr_bytes_file = fetch_S3orURL(
                        self.bucket_name + "/" + loc + filename, rawbytes=True
                    )

                if fr_bytes_file == None:
                    continue

                if filepath is not None:
                    with open(filepath, "wb") as file:
                        file.write(fr_bytes_file.read())
                    fr_bytes_file.seek(0)
                fr = pd.read_csv(fr_bytes_file)

            # If file exists, read from given path
            else:
                fr = pd.read_csv(filepath)

            # print("Debug, version is ",self.catalog["Cloudy"])
            try:
                version = float(self.catalog["Cloudy"])
            except:
                version = float(self.catalog["version"])
            if version < 0.5:
                # spec before 0.5 was start/key/filesize
                # generate a 'maybe' stop using start time of prior entry
                col0 = fr.columns[0]
                try:
                    fr.insert(1, "stop", fr[col0].shift(-1))
                except:
                    pass  # usually because 'stop' already exists in metadata

            # Handle # if used for the header
            if fr.columns.values[0][:2] == "# ":
                fr.columns.values[0] = fr.columns.values[0][2:]

            # Make column names consistent since not enforcing this spec
            fr.rename(
                columns={
                    "start": "start",
                    "stop": "stop",
                    "modification": "modification",
                },
                inplace=True,
            )

            """ assume first column is start, second is stop, third is key,
                and fourth is filesize
                only assuming if not found in column names
                no error will be thrown if one of these missing,
                but per spec they are required """
            if "start" not in fr.columns.values:
                fr.columns.values[0] = "start"
            if "stop" not in fr.columns.values:
                fr.columns.values[1] = "stop"
            if "datakey" not in fr.columns.values:
                fr.columns.values[2] = "datakey"
            if "filesize" not in fr.columns.values:
                fr.columns.values[3] = "filesize"

            frs.append(fr)

        frs = pd.concat(frs)

        # Filter catalog dataframe to exact requested dates
        try:
            frs["start"] = pd.to_datetime(
                frs["start"], format="%Y-%m-%dT%H:%M:%S.%fZ", exact=False
            )
        except:
            try:
                frs["start"] = pd.to_datetime(
                    frs["start"], format="%Y-%m-%dT%H:%M:%SZ", exact=False
                )
            except:
                frs["start"] = pd.to_datetime(
                    frs["start"], format="%Y-%m-%dT%H:%MZ", exact=False
                )
        try:
            frs["stop"] = pd.to_datetime(
                frs["stop"], format="%Y-%m-%dT%H:%M:%S.%fZ", exact=False
            )
        except:
            try:
                frs["stop"] = pd.to_datetime(
                    frs["stop"], format="%Y-%m-%dT%H:%M:%SZ", exact=False
                )
            except:
                frs["stop"] = pd.to_datetime(
                    frs["stop"], format="%Y-%m-%dT%H:%MZ", exact=False
                )
        # frs["start"] = pd.to_datetime(frs["start"], format='ISO8601',exact=False)
        # frs["stop"] = pd.to_datetime(frs["stop"], format='ISO8601',exact=False)
        frs = frs[(frs["stop"] >= start_date) & (frs["start"] < stop_date)]

        return frs

    @staticmethod
    def stream(
        cloud_catalog: pd.DataFrame,
        process_func: Callable[[BytesIO, str, str, int], None],
        ignore_faileds3get: bool = False,
    ) -> None:
        """
        Downloads files from S3 and passes them to a processing function.

        Parameters:
            cloud_catalog (pd.DataFrame): A pandas DataFrame containing
                                          the dataset catalog information.
            process_func (Callable): A function that takes a BytesIO object,
                         a string representing the start date of the file,
                         a string representing the stop date of the file, and
                         an integer representing the file size as arguments.
            ignore_faileds3get (bool): A boolean that determines if
                         the FailedS3Get is not thrown.
        """

        # original version, added https mod
        # s3_client = boto3.client("s3")

        fr_bytes_file = None
        for _, row in cloud_catalog.iterrows():
            # Get the S3 URL from the key in the dataframe
            s3_url = row["datakey"]
            fr_bytes_file = fetch_S3orURL(s3_url, rawbytes=True)
            """ Pass the BytesIO object, start date, and file size to
                the processing function
                start may be a date object so making a string just in case
                for consistency"""
            process_func(
                fr_bytes_file, str(row["start"]), str(row["stop"]), row["filesize"]
            )

    @staticmethod
    def stream_uri(
        cloud_catalog: pd.DataFrame, process_func: Callable[[str, str, str, int], None]
    ) -> None:
        """
        Sends S3 URLs to a processing function.

        Parameters:
            cloud_catalog (pd.DataFrame): A pandas DataFrame containing
                         the dataset catalog information.
            process_func (Callable): A function that takes
                         a string representing the S3 URL,
                         a string representing the start date of the file,
                         a string representing the stop date of the file, and
                         an integer representing the file size as arguments.
        """
        for _, row in cloud_catalog.iterrows():
            # Get the S3 URL from the key in the dataframe
            s3_url = row["datakey"]

            """ Pass the S3 URL, start date, and file size to
                the processing function
                start may be a date object so making a string
                just in case for consistency"""
            process_func(s3_url, str(row["start"]), str(row["stop"]), row["filesize"])


class EntireCatalogSearch:
    """Use to search through all the catalogs by using the global catalog
    to get all the local catalogs."""

    def __init__(self, catalog_url: Optional[str] = None, **client_kwargs):
        """
        Parameters:
            catalog_url (str, optional): URL of the global catalog,
                        default is None.
            client_kwargs: Keyword arguments passed to the CloudCatalog object.
        """

        # Get the global catalog
        self.global_catalog = CatalogRegistry(catalog_url=catalog_url)

        # Combine the global catalog with local catalogs from each entry
        self.combined_catalog = []
        failed_entries = []
        entries = self.global_catalog.get_registry()
        for entry in entries:
            endpoint = self.global_catalog.get_endpoint(entry["name"], entry["region"])
            try:
                cloud_catalog = CloudCatalog(endpoint, cache=False, **client_kwargs)
                local_catalog = cloud_catalog.get_catalog()
                self.combined_catalog.append(local_catalog)
            except Exception as e:
                logging.debug(
                    f"Failed to fetch local catalog for entry {entry['name']} (Region: {entry['region']}; Endpoint: {entry['endpoint']}): {e}\n"
                )
                failed_entries.append((entry["name"], entry["region"]))
        if len(failed_entries) > 0:
            msg = f"Failed Local Catalog Fetches ({len(failed_entries)}/{len(entries)}): \n[\n"
            for entry in failed_entries:
                msg += f"    {entry[0]} ({entry[1]})\n"
            msg += "]"
            logging.warning(msg)

    def search_by_id(self, catalog_id_substr: str):
        """
        Search the combined catalog by ID.

        Parameters:
            catalog_id_substr (str): The catalog ID to search for.
                                     Can be an ID prefix.

        Returns:
            A list of matching catalog entries.
        """
        results = []
        catalog_id_substr = catalog_id_substr.lower()
        for catalog in self.combined_catalog:
            for entry in catalog["catalog"]:
                if catalog_id_substr in entry["id"].lower():
                    results.append(entry)
        return results

    def search_by_title(self, title_substr: str):
        """
        Search the combined catalog by title substring.

        Parameters:
            title_substr (str): The substring to search for in catalog titles.

        Returns:
            A list of matching catalog entries.
        """
        results = []
        title_substr = title_substr.lower()
        for catalog in self.combined_catalog:
            for entry in catalog["catalog"]:
                if title_substr in entry["title"].lower():
                    results.append(entry)
        return results

    def search_by_keywords(self, keywords: List[str]):
        """
        Search the combined catalog for keywords in ID, location, and title.

        Parameters:
            keywords (List[str]): A list of keywords to search for.

        Returns:
            A list of matching catalog entries,
            sorted by the most matching keywords.
        """
        entry_counts = []
        for catalog in self.combined_catalog:
            for entry in catalog["catalog"]:
                count = 0
                for keyword in keywords:
                    keyword = keyword.lower()
                    count += entry["id"].lower().count(keyword)
                    count += entry["index"].lower().count(keyword)
                    count += entry["title"].lower().count(keyword)
                    if "tags" in entry:
                        count += sum([keyword in tag.lower() for tag in entry["tags"]])
                if count > 0:
                    entry_counts.append((entry, count))

        # Sort results by the most matching keywords
        sorted_results = sorted(entry_counts, key=lambda x: x[1], reverse=True)
        return [entry for entry, count in sorted_results if count > 0]
