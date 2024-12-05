# CloudCatalog (cloudcatalog) API

CloudCatalog is a generalized indexing specification for large cloud datasets.
The push to open science means many more published datasets, and finding and accessing is important to solve. CloudCatalog is an indexing method for sharing big datasets in cloud systems. It is scientist-friendly and it is easy to generate a set of indices. It uses static index files in time-ordered CSV format that are easy to fetch, easy to access via an API, and very low cost in both money and bandwidth needed to support. Metadata is kept in a simple JSON schema. We also provide a Python client toolset for scientists to access datasets that use CloudCatalog. 

The CloudCatalog specification and tools are open source, created by the HelioCloud project, and already used for 2 Petabytes of publicly available NASA and scientist-contributed data. We hope the community continues to adopt this CloudCatalog standard (in github, linked off heliocloud.org).

* For sharing datasets across cloud frameworks
* Decentralized: data owners control their own data and access
* RESTful & serverless (indices are flat files alongside their datasets)
* Removes need for doing slow/expensive disk ‘ls’ on large holdings
* Global registry JSON points to owner-controlled ‘buckets’
* Uses minimal JSON to list metadata, CSV files for indices
* Searchable
* Public specification here on GitHub.

[The Specification](docs/cloudcatalog-spec.md) enables anyone to index a public dataset such that other users can find it and retrieve file listings in a cost-effective serverless fashion.

The API is designed for retrieving file catalog (index) files from a specific ID entry in a catalog within a bucket. It also includes search functionality for searching through all data index catalogs found in the bucket list.

## Use Case
Suppose there is a mission on S3 that follows the HelioCloud 'CloudCatalog' specification, and you want to obtain specific files from this mission.

### Initial Setup and Global Catalog
First, install the tool if it has not been already installed. Then, import the tool into a script or shell. You will likely want to search the global catalog to find the specific bucket/catalog containing the data catalog files. You first create a CatalogRegistry object to pull from the default global catalog. This lists buckets not datasets; each bucket owner retains direct ownership over which of their datasets they wish to expose to the public.

```python
import cloudcatalog

cr = cloudcatalog.CatalogRegistry()
print(cr.get_catalog())

print(cr.get_entries())
```

### Finding and Requesting the File Catalog
At this point, you should have found the bucket containing the data of interest. Next, you will want to search the bucket-specific catalog (data catalog) for the ID representing the mission you want to obtain data for.

```python
bucket_name = cr.get_endpoint('e.g. Bucket Mnemonic') # or hard-code, e.g. 's3://mybucket'
# If not a public bucket, pass access_key or boto S3 client params to access it
fr = cloudcatalog.CloudCatalog(bucket_name)  

# Print out the entire local catalog (datasets)
print(fr.get_catalog())

# To find the specific ID we can also get the ID + Title by
print(fr.get_entries())

# Now with the ID we can request the catalog index files as a Pandas dataframe
fr_id = 'a_dataset_id_from_the_catalog'
start_date = '2007-02-01T00:00:00Z'  # A ISO 8601 standard time
stop_date = None  # A ISO 8601 standard time or None for everything after start_date
myfiles = fr.request_cloud_catalog(fr_id, start_date=start_date, end_date=end_date, overwrite=False)
```

### Searching the Entire Catalog
You can use the EntireCatalogSearch class to find a catalog entry:

```python
search = cloudcatalog.EntireCatalogSearch()
top_search_result = search.search_by_keywords(['vector', 'mission', 'useful'])[0]
print(top_search_result)
```

### Specific example for an SDO fetch of the filelist for all the 94A EUV images (1,624,900 files)
``` python
import cloudcatalog
fr = cloudcatalog.CloudCatalog("s3://gov-nasa-hdrl-data1/")
dataid = "aia_0094"
start, stop = fr.get_entry(dataid)['start'], fr.get_entry(dataid)['stop']
mySDOlist = fr.request_cloud_catalog(dataid, start, stop)
```

### Add-on example for an MMS fetch of the filelist for all of a specific MMS item (64,383 files)
``` python
dataid = "mms1_feeps_brst_electron"
start, stop = fr.get_entry(dataid)['start'], fr.get_entry(dataid)['stop']
myMMSlist = fr.request_cloud_catalog(dataid, start, stop)
```

### Streaming Data from the File Catalog
You now have a pandas DataFrame with startdate, stopdate, key, and filesize for all the files of the mission within your specified start and end dates. From here, you can use the key to stream some of the data through EC2, a Lambda, or other processing methods.

This tool also offers a simple function for streaming the data once the file catalog is obtained:

```python
cloudcatalog.CloudCatalog.stream(cloud_catalog, lambda bfile, startdate, stopdate, filesize: print(len(bo.read()), filesize))
```

## Full Notebook Tutorial

For an in-depth walkthrough using the CloudCatalog on NASA datasets, see [CloudCatalog-Demo.ipynb](https://github.com/heliocloud-data/science-tutorials/blob/main/CloudCatalog-Demo.ipynb)