import json
from smart_open import open
import re

catalogname = "s3://gov-nasa-hdrl-data1/catalog.json"


def valid_id(datasetid):
    if not re.search(r'^[a-zA-Z0-9_-]*$', datasetid):
        return False
    else:
        return True

def valid_index(filepath):
    if not re.search('^[s3://|https://].*/$', filepath): # <----- SPEC SAYS https:// OR EQUIVALENT????
        return False
    else:
        return True

def valid_start(startstr):
    if not re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\.\d{2}Z', startstr):
        return False
    else:
        return True

def valid_stop(stopstr):
    if not re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\.\d{2}Z', stopstr):
        return False
    else:
        return True

def valid_modification(modstr):
    if not re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\.\d{2}Z', modstr):
        return False
    else:
        return True

# SHOULD I ADD SOMETHING HERE FOR THE TITLE ENTRY????

def valid_indextype(indextype):
    if not re.search('^(csv|csv-zip|parquet)$', indextype):
        return False
    else:
        return True

def valid_filetype(filetype):
    if not re.search('^(fits|csv|cdf|netcdf3|netcdf4|hdf5|datamap|txt|binary|other)$', filetype):
        return False
    else:
        return True

# OPTIONAL DESCRIPTION

# OPTIONAL RESOURCE IDENTIFIER

def valid_creation(creationstr):
    if not re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\.\d{2}Z', creationstr):
        return False
    else:
        return True

def valid_expiration(expstr):
    if not re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\.\d{2}Z', expstr):
        return False
    else:
        return True

def valid_verified(verifstr):
    if not re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\.\d{2}Z', verifstr):
        return False
    else:
        return True

# OPTIONAL CITATION

# OPTIONAL CONTACT NAME

# OPTIONAL ABOUT

def valid_multiyear(multiyearboo):
    if not re.search('^(True|False)$', multiyearboo): # DOES CAPITALIZATION MATTER????
        return False
    else:
        return True

def validator(catalogname):
    with open(catalogname, "r") as fin:
        catalog = json.load(fin)

    if not catalog['id']:
        print('No entry for "id" provided! Dataset ID is a required catalog entry!')
    else:
        if not valid_id(catalog['id']):
            print('Invalid dataset ID. ID can only contain alphanumeric characters, dashes, or underscores. No spaces'
                  ' or any other characters.')

    if not catalog['index']:
        print('No entry for "index" provided! Dataset index is a required catalog entry!')
    else:
        if not valid_index(catalog['index']):
            print('Invalid index. Index must start with "s3://" or "https://" and end in a terminating "/".')

    if not catalog['start']:
        print('No entry for "start" provided! Start date is a required catalog entry!')
    else:
        if not valid_start(catalog['start']):
            print('Invalid start date. Start date must be a date/time string in Restricted ISO 8601 format.')
            # INCLUDE EXAMPLE OF DATE FORMAT? I.E. YYYY-MM-DDTHH:MM.SSZ?

    if not catalog['stop']:
        print('No entry for "stop" provided! Stop date is a required catalog entry!')
    else:
        if not valid_stop(catalog['stop']):
            print('Invalid stop date. Stop date must be a date/time string in Restricted ISO 8601 format.')

    if not catalog['modification']:
        print('No entry for "modification" provided! Modification date is a required catalog entry!')
    else:
        if not valid_modification(catalog['modification']):
            print('Invalid modification date. Modification date must be a date/time string in Restricted ISO 8601 '
                  'format.')

    if not catalog['title']:
        print('No entry for "title" provided! Dataset title is a required catalog entry!')
    # SHOULD I ADD SOMETHING HERE FOR THE TITLE ENTRY????

    if not catalog['indextype']:
        print('No entry for "indextype" provided! Index type is a required catalog entry!')
    else:
        if not valid_indextype(catalog['indextype']):
            print('Invalid entry for "indextype." Index type can be either csv, csv-zip, or parquet.')

    if not catalog['filetype']:
        print('No entry for "filetype" provided! File type is a required catalog entry!')
    else:
        if not valid_filetype(catalog['filetype']):
            print('Invalid entry for "filetype." Current permitted types are fits, csv, cdf, netcdf3, netcdf4, hdf5, '
                  'datamap, txt, binary, and other.')

    # OPTIONAL DESCRIPTION

    # OPTIONAL RESOURCE

    if catalog['creation'] and not valid_creation(catalog['creation']):
        print('Invalid entry for "creation." Creation date must be a date/time string in ISO 8601 format.')

    if catalog['expiration'] and not valid_expiration(catalog['expiration']):
        print('Invalid entry for "expiration." Expiration date must be a date/time string in ISO 8601 format.')

    if catalog['verified'] and not valid_verified(catalog['verified']):
        print('Invalid entry for "verified." Verified date must be a date/time string in ISO 8601 format.')

    # OPTIONAL CITATION

    # OPTIONAL CONTACT NAME

    # OPTIONAL ABOUT

    if catalog['multiyear'] and not valid_multiyear(catalog['multiyear']):
        print('Invalid entry for "multiyear." Multiyear entry must either be "True" or "False."')


validator(catalogname)


if __name__ == 'main':
    validator(catalogname)



