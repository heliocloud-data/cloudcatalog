import cloudcatalog as cc

fr = cc.CloudCatalog("s3://gov-nasa-hdrl-data1/", altcatalog="catalog-20260428v2.json")

for dataid in open("dataids_small.txt"):
    dataid = dataid.rstrip()
    try:
        meta = fr.get_entry(dataid)
        print(f"\tMetadata {dataid}: {meta['id']},\n\t{meta['index']}")
    except:
        print(f"No catalog metadata found for {dataid}")
    test = fr.sample_file(dataid)
    try:
        test = fr.sample_file(dataid)
        print(f"\tSample file {dataid}: {test}")
    except:
        print(f"No file index found for {dataid}")
