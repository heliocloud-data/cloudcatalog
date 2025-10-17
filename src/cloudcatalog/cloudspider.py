"""
tree(catalog=None, noisy=False, returnvars=False, printme=True)
      catalog defaults to http://heliocloud.org/catalog/HelioDataRegistry.json
      returnvars is whether to return a python list of dict (id,start,stop)
      printme is whether to echo to screen or not, default is True

tree() prints and/or returns a list of l top-level IDs plus
 # of datasets per ID


spider(spiderset = None, fr = None, noisy=True, create_manifest=False)
      pass it spiderset and fr if tree() was called earlier, otherwise
         it will do a call to tree() to generate these
      noisy is whether to echo to screen or not, default is True
      create_manifest is whether to do a deeper spider to list all files,
           default is False. This takes a lot of time because it has to
           call cloudcatalog() for each ID/year item, and can generate
           GB-sized manifests.]
           Note default manifest date form is 'YYYY-MM-DD HH:MM:SS'

  spider always generates a 'spiderout.txt' of how many files per ID/year exist
  optionally, it can do an entire 'manifest_spider.txt', but that takes longer

Available as CLI versions:
   cloudcatalog-tree
      [--catalog_url http://heliocloud.org/catalog/HelioDataRegistry.json]

   cloudcatalog-spider
      [--catalog_url http://heliocloud.org/catalog/HelioDataRegistry.json]
      [--create_manifest False]

"""


from itertools import groupby
import cloudcatalog

def tree(catalog=None, returnvars=False, printme=True):

    if catalog == None:
        catalog = "http://heliocloud.org/catalog/HelioDataRegistry.json"

    search = cloudcatalog.EntireCatalogSearch(catalog)

    search.search_by_keywords(["mms2", "brst", "apples"])[:3]
    cr = cloudcatalog.CatalogRegistry(catalog)
    # for s3disk in cr.get_registry():
    fullset = []
    collection = "CDAWeb"  # None
    for s3disk in cr.catalog["registry"]:
        if printme: print(f"{s3disk['endpoint']},{s3disk['region']}")
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
            if printme: print(f"{s3disk['endpoint']} not accessible or has no catalogs")
    # print(fullset)
    fullset.sort(key=str.casefold)

    res = [list(i) for j, i in groupby(fullset, lambda a: a.split("_")[0].lower())]
    if printme: print(len(res))
    for ele in res:
        groupid = ele[0].split("_")[0]
        if printme: print(f"*{groupid} has {len(ele)} datasets")

    if returnvars:
        return spiderset, fr
    
def spider(spiderset = None, fr = None, noisy=True, create_manifest=False):

    if spiderset == None or fr == None:
        spiderset, fr = tree(returnvars=True,printme=False)
    if noisy: print(f"Fetched {len(spiderset)} entries, now spidering.")
    icount = 0
    spiderset.sort()
    totcount = len(spiderset)
    if create_manifest:
        mout = open("manifest_spider.txt","w")
    fout = open("spiderout.txt", "w")
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
                if create_manifest:
                    flist.to_csv(mout,index=False)
            except:
                mystr = f"Error accessing {trio[0]}, {iyear}"

            fout.writelines(mystr+'\n')
            if noisy: print(mystr)
            # fkeys = [item['datakey'] for item in flist]
            # fout.writelines(fkeys)
        if icount % 3 == 1: print(f"   (checked {icount} of {totcount})")
    fout.close()
    if create_manifest:
        mout.close()
    print(f"Done, checked {icount} of {totcount}")

def spider_main():
    import argparse
    p = argparse.ArgumentParser(prog="cloudcatalog-spider", description="Run the cloudcatalog spider")
    p.add_argument("--catalog_url", default=None, help="(optional) catalog loc")
    p.add_argument("--create_manifest", dest="create_manifest", default=False, help="(optional) dump entire catalog to manifest_spider.csv")
    args = p.parse_args()
    spider(tree(catalog=args.catalog_url),create_manifest=args.create_manifest)

def tree_main(catalog=None):
    import argparse
    p = argparse.ArgumentParser(prog="cloudcatalog-tree", description="Print the cloudcatalog tree")
    p.add_argument("--catalog_url", default=None, help="(optional) catalog loc")
    args = p.parse_args()
    tree(catalog=args.catalog_url,returnvars=False,printme=True)

if __name__ == "__main__":
    spiderset, fr = tree(returnvars=True,printme=True)
    yn = input("Spider all datasets to validate (lengthy)? y/n: ")
    if yn.lower().startswith('y'):
        spider(spiderset, fr)
