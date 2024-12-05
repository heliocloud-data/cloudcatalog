import cloudcatalog

search = cloudcatalog.EntireCatalogSearch()

search.search_by_keywords(["mms2", "brst", "apples"])[:3]
cr = cloudcatalog.CatalogRegistry()
# for s3disk in cr.get_registry():
fullset = []
for s3disk in cr.catalog["registry"]:
    print(f"{s3disk['endpoint']},{s3disk['region']}")
    try:
        fr = cloudcatalog.CloudCatalog(s3disk["endpoint"], cache=False)
        items = fr.get_catalog()["catalog"]
        labels = [ele["id"] + ": " + ele["title"] for ele in items]
        fullset += labels
    except:
        print(f"{s3disk['endpoint']} not accessible or has no catalogs")
# print(fullset)
fullset.sort(key=str.casefold)
from itertools import groupby

res = [list(i) for j, i in groupby(fullset, lambda a: a.split("_")[0].lower())]
print(len(res))
for ele in res:
    groupid = ele[0].split("_")[0]
    print(f"*{groupid} has {len(ele)} datasets")
