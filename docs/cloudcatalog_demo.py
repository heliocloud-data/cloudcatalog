import cloudcatalog

"""
The cloud catalog API is just "import cloudcatalog". It defaults to the global catalog of all known storage buckets (AWS S3 buckets)-- this is an index catalog that points to, basically, all known HelioClouds.
"""

print("\n*** We start with the main usage: a HAPI-like query to get a list of files for a given dataset id, over a given time range")
dataset = "mms1_feeps_brst_electron"
start = "2020-02-01T00:00:00Z"
stop = "2020-02-02T00:00:00Z"
cr = cloudcatalog.CatalogRegistry()
endpoint = cr.get_endpoint("GSFC HelioCloud Public Temp")
fr = cloudcatalog.CloudCatalog(endpoint, cache=True)
filekeys = fr.request_cloud_catalog(dataset,start_date=start,stop_date=stop)
print("filekeys for ",dataset,start,stop,":",filekeys)

pause=input("(hit any key to continue)")
print("*** Simple metadata for (arbitrarily chosen) 3rd file in that Pandas DataFrame")
print("All info on item 3:",filekeys.iloc[2])
print("Just the S3 key:",filekeys.iloc[2]['datakey'])

pause=input("(hit any key to continue)")
print("\n*** Now we step back to explore the catalogs that are available, to work up to that example.")

print("\n*** Getting the actual catalog list of filenames")

print("\n*** Exploring catalogs")
cr = cloudcatalog.CatalogRegistry()
cat = cr.get_catalog()
print("get_catalog:",cat)
reg = cr.get_registry()
print("get registry:",reg)
url = cr.get_endpoint("HelioCloud, including SDO")
print("get_endpoint:", url)

"""
Searching for data with EntireCatalogSearch
This initial search accesses each HelioCloud's specific data holdings to create what you probably want, which is a list of all datasets available within the entire HelioCloud ecosystem.
We include an example of a down or de-registered catalog to emphasize this index catalog points to HelioClouds, but doesn't manage them.
"""
pause=input("(hit any key to continue)")
print("\n*** Sample searches (requires an AWS account currently)")
search = cloudcatalog.EntireCatalogSearch()
feeps = search.search_by_id('mms1_feeps')
print("Found mms1_feeps:",feeps)
fpi = search.search_by_title('mms1/fpi/b')
print("Found data in mms1/fpi/b:",fpi)
mixed = search.search_by_keywords(['mms2','brst','apples'])[:3]
print("Searched keywords mmm2, brst, and apples, found:",mixed)

pause=input("(hit any key to continue)")
print("\n*** Listing holdings available on a specific S3 'disk'")
cr = cloudcatalog.CatalogRegistry() # repeating this from earlier, no reason
endpoint = cr.get_endpoint("GSFC HelioCloud Public Temp")
fr = cloudcatalog.CloudCatalog(endpoint, cache=True)
cat = fr.get_catalog()
print("catalog is:",cat)

pause=input("(hit any key to continue)")
print("\n*** Finding the metadata for a data set")
meta = fr.get_entry("mms1_feeps_brst_electron")
print("metadata for mms1_feeps_brst_electron", meta)

print("\n\n... and once you have the dataset, you can go to the start of this where we showed you how to fetch the filekeys for that entire set over a given time range.")
print("\n\nThus ends this demo.")
