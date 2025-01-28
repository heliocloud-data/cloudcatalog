"""
Validator for new entries to the CloudCatalog. Returns an error for catalog metadata that doesn't match the spec.

Find the spec here: https://gitlab.smce.nasa.gov/heliocloud/scregistry/-/blob/develop/docs/cloudcatalog-spec.md?ref_type=heads

Contact Lisa Knowles lisa.knowles@jhuapl.edu
"""

import json
from smart_open import open
import re


def valid_endpoint(collectionendpoint):
    if not re.search("^[s3://|https://].*/$", collectionendpoint):
        return False
    else:
        return True


def valid_id(datasetid):
    if not re.search(r"^[a-zA-Z0-9_-]*$", datasetid):
        return False
    else:
        return True


def valid_index(filepath):
    if not re.search("^[s3://|https://].*/.*/$", filepath):
        return False
    else:
        return True


def valid_start(startstr):
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?Z", startstr
    ):
        return False
    else:
        return True


def valid_stop(stopstr):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?Z", stopstr):
        return False
    else:
        return True


def valid_modification(modstr):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?Z", modstr):
        return False
    else:
        return True


def valid_indextype(indextype):
    if not re.search("^(csv|csv-zip|parquet)$", indextype, re.IGNORECASE):
        return False
    else:
        return True


def valid_filetype(filetype):
    if not re.search(
        "^(fits|csv|cdf|netcdf3|netcdf4|hdf5|datamap|txt|binary|other)$",
        filetype,
        re.IGNORECASE,
    ):
        return False
    else:
        return True


def valid_creation(creationstr):
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?Z", creationstr
    ):
        return False
    else:
        return True


def valid_expiration(expstr):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?Z", expstr):
        return False
    else:
        return True


def valid_verified(verifstr):
    if not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?Z", verifstr):
        return False
    else:
        return True


def valid_multiyear(multiyearboo):
    if not re.search("^(True|False)$", multiyearboo, re.IGNORECASE):
        return False
    else:
        return True


def validator(catalogname):
    with open(catalogname, "r") as fin:
        topcatalog = json.load(fin)

    if "name" not in topcatalog:
        print(
            'No entry for "name" provided! Collection name is a required entry! Name should be a descriptive '
            "title for the collection of datasets. Should be the same as provided to GlobalDataRegistry.json."
        )

    if "endpoint" not in topcatalog:
        print(
            'No entry for "endpoint" provided! Collection endpoint is a required entry!'
        )
    else:
        if not valid_endpoint(topcatalog["endpoint"]):
            print(
                "Invalid endpoint. Endpoint must be a an accessible S3 (or equivalent) bucket link. It must start "
                'with "s3://" or "https://" and end in a terminating "/".'
            )

    if "egress" not in topcatalog:
        print(
            'No entry for "egress" provided! Egress should be a set of keywords defining permissions. Currently '
            "optional but will be required in the near future."
        )

    if "status" not in topcatalog:
        print(
            'No entry for "status" provided! Status is a return code and should communicate if a dataset is '
            'temporarily down or has other constraints. Default is "code: 1200, message: OK".'
        )

    if "contact" not in topcatalog:
        print(
            'No entry for "contact" provided! Contact should be the name and email address of the person to contact '
            "with issues with the collection."
        )

    datasetcatalog = topcatalog["catalog"]

    datalength = str(len(datasetcatalog))

    for idx, catalog in enumerate(datasetcatalog):
        print("Validating dataset #" + str(idx + 1) + " of " + datalength)

        if "id" not in catalog:
            print('No entry for "id" provided! Dataset ID is a required catalog entry!')
        else:
            if not valid_id(catalog["id"]):
                print(
                    "Invalid dataset ID. ID can only contain alphanumeric characters, dashes, or underscores. No"
                    "spaces or any other characters."
                )

        if "index" not in catalog:
            print(
                'No entry for "index" provided! Dataset index is a required catalog entry!'
            )
        else:
            if not valid_index(catalog["index"]):
                print(
                    "Invalid index. Index must be a pointed to the object directory and contain the dataset name. It "
                    'must start with "s3://" or "https://" and end in a terminating "/".'
                )

        if "start" not in catalog:
            print(
                'No entry for "start" provided! Start date is a required catalog entry!'
            )
        else:
            if not valid_start(catalog["start"]):
                print(
                    "Invalid start date. Start date must be a date/time string in Restricted ISO 8601 format: "
                    "XXXX-XX-XXTXXZ with at least the year, month, day, and hour specified."
                )

        if "stop" not in catalog:
            print(
                'No entry for "stop" provided! Stop date is a required catalog entry!'
            )
        else:
            if not valid_stop(catalog["stop"]):
                print(
                    "Invalid stop date. Stop date must be a date/time string in Restricted ISO 8601 format: "
                    "XXXX-XX-XXTXXZ with at least the year, month, day, and hour specified."
                )

        if "modification" not in catalog:
            print(
                'No entry for "modification" provided! Modification date is a required catalog entry!'
            )
        else:
            if not valid_modification(catalog["modification"]):
                print(
                    "Invalid modification date. Modification date must be a date/time string in Restricted ISO 8601 "
                    "format: XXXX-XX-XXTXXZ with at least the year, month, day, and hour specified."
                )

        if "title" not in catalog:
            print(
                'No entry for "title" provided! Dataset title is a required catalog entry!'
            )

        if "indextype" not in catalog:
            print(
                'No entry for "indextype" provided! Index type is a required catalog entry!'
            )
        else:
            if not valid_indextype(catalog["indextype"]):
                print(
                    'Invalid entry for "indextype." Index type can be either csv, csv-zip, or parquet.'
                )

        if "filetype" not in catalog:
            print(
                'No entry for "filetype" provided! File type is a required catalog entry!'
            )
        else:
            if not valid_filetype(catalog["filetype"]):
                print(
                    'Invalid entry for "filetype." Current permitted types are fits, csv, cdf, netcdf3, netcdf4, '
                    "hdf5, datamap, txt, binary, and other."
                )

        if "creation" not in catalog:
            pass
        elif catalog["creation"] and not valid_creation(catalog["creation"]):
            print(
                'Invalid entry for "creation." Creation date must be a date/time string in ISO 8601 format.'
            )

        if "expiration" not in catalog:
            pass
        elif catalog["expiration"] and not valid_expiration(catalog["expiration"]):
            print(
                'Invalid entry for "expiration." Expiration date must be a date/time string in ISO 8601 format: '
                "XXXX-XX-XXTXXZ with at least the year, month, day, and hour specified."
            )

        if "verified" not in catalog:
            pass
        elif catalog["verified"] and not valid_verified(catalog["verified"]):
            print(
                'Invalid entry for "verified." Verified date must be a date/time string in ISO 8601 format: '
                "XXXX-XX-XXTXXZ with at least the year, month, day, and hour specified."
            )

        if "multiyear" not in catalog:
            pass
        elif catalog["multiyear"] and not valid_multiyear(catalog["multiyear"]):
            print(
                'Invalid entry for "multiyear." Multiyear entry must either be "True" or "False."'
            )


# if __name__ == 'main':
#    validator(catalogname)
