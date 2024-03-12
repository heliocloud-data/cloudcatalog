# Cloud Catalog (cloudcatalog) Tool
This tool is designed for retrieving file catalog (index) files from a specific ID entry in a catalog within a bucket. It also includes search functionality for searching through all data index catalogs found in the bucket list.

## Use Case
Suppose there is a mission on S3 that follows the HelioCloud 'Cloud Catalog' specification, and you want to obtain specific files from this mission.

### Initial Setup and Global Catalog
First, install the tool if it has not been already installed. Then, import the tool into a script or shell. You will likely want to search the global catalog to find the specific bucket/catalog containing the data catalog files.

```python
import cloudcatalog

# Create CatalogRegistry object which will by default pull from the Heliocloud global catalog
# or if an environment variable has been set for another global catalog, it will pull from there
cr = cloudcatalog.CatalogRegistry()

# Print out the entire global catalog
print(cr.get_catalog())

# Print out name + region of all global catalog entries
# If we know roughly what the name of the overarching bucket would be,
# this will help us find the exact name we need for the mission we want.
# Otherwise, other methods must be used to search for the bucket of interests.
print(cr.get_entries())
```

### Finding and Requesting the File Catalog
At this point, you should have found the bucket containing the data of interest. Next, you will want to search the bucket-specific catalog (data catalog) for the ID representing the mission you want to obtain data for.

```python
# With the bucket name we have obtained (possibly by using cr.get_endpoint(name, region_prefix=''))
bucket_name = 'a-bucket-name'
# If this is not a public bucket, you may need to pass access_key or other boto S3 client specific params to get the data
# cache_folder is only used if cache is True and defaults to `bucket_name + '_cache'`
fr = cloudcatalog.CloudCatalog(bucket_name, cache_folder=None, cache=True)  

# Print out the entire local catalog (datasets)
print(fr.get_catalog())

# To find the specific ID we can also get the ID + Title by
print(fr.get_entries())

# Now with the ID we can request the catalog index files
# This if successful, will get us a Pandas dataframe of the file index
# and if we previously had set cache to True in initialization, it will
# also save the downloaded file index
fr_id = 'a_dataset_id_from_the_catalog'
start_date = '2007-02-01T00:00:00Z'  # A ISO 8601 standard time and a valid time witin the mission/file-index
stop_date = None  # A ISO 8601 standard time or None if want all the file indices after start_date
myfiles = fr.request_cloud_catalog(fr_id, start_date=start_date, end_date=end_date, overwrite=False)
```

### Streaming Data from the File Catalog
You now have a pandas DataFrame with startdate, stopdate, key, and filesize for all the files of the mission within your specified start and end dates. From here, you can use the key to stream some of the data through EC2, a Lambda, or other processing methods.

This tool also offers a simple function for streaming the data once the file catalog is obtained:

```python
cloudcatalog.CloudCatalog.stream(cloud_catalog, lambda bfile, startdate, stopdate, filesize: print(len(bo.read()), filesize))
```

### Searching the Entire Catalog
As an alternative to manually searching, you can use the EntireCatalogSearch class to find a catalog entry:

```python
search = cloudcatalog.EntireCatalogSearch()
top_search_result = search.search_by_keywords(['vector', 'mission', 'useful'])[0]
# Prints out the top result with all the catalog info, including id, loc, startdate, etc.
print(top_search_result)
```

### Terse example for an SDO fetch of the filelist for all the 94A EUV images (1,624,900 files)
```
import cloudcatalog
dataid = "aia_0094"
s3bucket="s3://gov-nasa-hdrl-data1/"
fr = cloudcatalog.CloudCatalog(s3bucket)
mySDOlist = fr.request_cloud_catalog(dataid,
	    start_date=fr.get_entry(dataid)['start'],
	    stop_date=fr.get_entry(dataid)['stop'])
```

### Terse example for an MMS fetch of the filelist for all of a specific MMS item (64,383 files)
```
import cloudcatalog
dataid = "mms1_feeps_brst_electron"
s3bucket="s3://helio-public/"
fr = cloudcatalog.CloudCatalog(s3bucket)
myMMSlist = fr.request_cloud_catalog(dataid,
	    start_date=fr.get_entry(dataid)['start'],
	    stop_date=fr.get_entry(dataid)['stop'])
```