from itertools import groupby
import cloudcatalog

def cattree(catalog=None, spider=False, noisy=False):

    if catalog == None:
        catalog = "http://heliocloud.org/catalog/HelioDataRegistry.json"

    search = cloudcatalog.EntireCatalogSearch(catalog)

    search.search_by_keywords(["mms2", "brst", "apples"])[:3]
    cr = cloudcatalog.CatalogRegistry(catalog)
    # for s3disk in cr.get_registry():
    fullset = []
    collection = "CDAWeb"  # None
    for s3disk in cr.catalog["registry"]:
        print(f"{s3disk['endpoint']},{s3disk['region']}")
        try:
            fr = cloudcatalog.CloudCatalog(s3disk["endpoint"], cache=False)
            items = fr.get_catalog()["catalog"]
            if collection != None:
                items = [
                    item
                    for item in items
                    if "collections" in item.keys() and collection in item["collections"]
                ]
            if len(items) > 0:
                labels = [ele["id"] + ": " + ele["title"] for ele in items]
                spiderset = [[ele["id"], ele["start"], ele["stop"]] for ele in items]
                fullset += labels
        except:
            print(f"{s3disk['endpoint']} not accessible or has no catalogs")
    # print(fullset)
    fullset.sort(key=str.casefold)

    res = [list(i) for j, i in groupby(fullset, lambda a: a.split("_")[0].lower())]
    print(len(res))
    for ele in res:
        groupid = ele[0].split("_")[0]
        print(f"*{groupid} has {len(ele)} datasets")

    if spider: spiderme(spiderset, fr, noisy)
    
def spiderme(spiderset, fr, noisy=True):

    icount = 0
    spiderset.sort()
    totcount = len(spiderset)
    with open("spiderout.txt", "w") as fout:
        for trio in spiderset:
            icount += 1
            #print(trio)
            # now handles year skips
            year1 = int(trio[1][:4])
            year2 = int(trio[2][:4])
            for iyear in range(year1, year2 + 1):
                start = str(iyear) + "-01-01T00:00:00"
                end = str(iyear) + "-12-31T23:59:59"
                if iyear == year1:
                    start = trio[1]
                if iyear == year2 + 1:
                    end = trio[2]
                try:
                    flist = fr.request_cloud_catalog(
                        trio[0], start_date=start, stop_date=end
                    )
                    mystr = f"{trio[0]}, {iyear}: {len(flist)} entries."
                except:
                    mystr = f"Error accessing {trio[0]}, {iyear}"

                fout.writelines(mystr+'\n')
                if noisy: print(mystr)
                # fkeys = [item['datakey'] for item in flist]
                # fout.writelines(fkeys)
            if icount % 3 == 1: print(f"   (checked {icount} of {totcount})")
    print(f"Done, checked {icount} of {totcount}")
                
if __name__ == "__main__":
    cattree(spider=True)
    
