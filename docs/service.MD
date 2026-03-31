## CloudCatalog web service

A simple, secure Python webserver.

It returns either the JSON metadata for a given ID, or an HTML landing page.

The default is the landing page.

Usage:
https://heliocloud.org/cloudcatalog?id=[DATAID]&format=json&source=[S3 bucket]

Arguments:
   id (required): a dataset ID
   format (optional): 'html' or 'json'. If not provided, defaults to 'html'
   source (optional): an S3 bucket name, defaults to 'gov-nasa-hdrl-data1'

The code to generate its results are:

(assuming incoming variables DataID, Format and Source)



import cloudcatalog

def parse_query(????):
    """ get and sanitize URL args 'id', 'format', 'source'
        throw an error if format 'exists' but is not 'html' or 'json'
	throw an error is 'source' exists but is not a viable S3 bucket name:
	   must be between 3-63 char long
	   only lowercase letters, numbers, periods and hyphens
	   must begin and end with a letter or number
	   cannot have 2 adjascent periods
    """

    return DataID, Format, Source


def get_metadata(DataID, Format, Source):
    """ Given a sanitized DataID, Format, and Source, returns the results """
    fr = cloudcatalog.CloudCatalog(f"s3://{Source}")
    metadata = fr.get_entry(DataID)
    status = 0
    if metadata is None:
         return 0, metadata
    elif Format == "html":
        metadata = render_index_html(metadata)
	return 1, metadata
    elif Format == "json":
        metadata = fr.get_entry(DataID)
	return 2, metadata
    else:
        # throw an HTML error code for system/unknown error
	return -1, metadata

""" web code goes here """


# on query, call this:
metadata, status = get_metadata(DataID, Format, Source)

""" return metadata as html, json or error to the server,
    based on status code:
    -1 = unknown system error
    0 = DataID not found
    1 = valid HTML
    2 = valid JSON
"""
