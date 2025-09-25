"""
JSON manipulation tools for the cloudcatalog 'catalog.json' file.

1) If file (def) 'catalog_stub.json' exists, adds new entries to (def)
   'catalog.json' if they do not exist.
   If they do exist, updates any changed metadata only.
   Can optionally specify a 'collection', in which case it only updates
   items in 'catalog_stub' that match that collection.
   (If for some reason now 'catalog.json' exists, simply renames input stub
    with no processing needed.)
   Always versions the 'catalog.json' before overwriting
2) def update_catalog_from_csv(json_path = 'catalog.json',
                            csv_path = 'cat.csv',
                            collections = None):
If file (def) 'cat.csv' exists, updates metadata of (def) 'catalog.json'
   for those id (form of CSV file is: id,start,stop,index,modification)
   If the id in (def) 'cat.csv' is not in (def) 'catalog.json',
   warns but does nothing.
   Can optionally specify a 'collection', in which case it only updates
   items in 'catalog_stub' that match that collection.
   Always versions the 'catalog.json' before overwriting

Sample usage: having taken an AWS manifest to generate a new
   'catalog_stub.json' the owner can now update the global 'catalog.json'
   safely.
Sample usage: having generated a set of updated times in 'cat.csv',
   the owner can now update the global 'catalog.json' safely.

"""

import json
import csv
import os
from cloudcatalog.updater import version_file as vf

def jloadme(jsonfile):
    with open(jsonfile, "r") as f:
        json_data = json.load(f)
    #cat_data = json_data.setdefault("catalog", [])
    cat_ids = [entry["id"] for entry in json_data["catalog"]]
    cat_data = {entry["id"] : entry for entry in json_data["catalog"]}
    return cat_ids, cat_data, json_data

def bestdate(date1,date2,earlier=True):
    itis = date1 < date2
    if earlier == itis:
        return date1
    else:
        return date2

def update_catalog_from_json(json_path = 'catalog.json',
                             json_updates = 'catalog_stub.json',
                             collections_filter = None,
                             debug = True):
    if not os.path.exists(json_path) or not os.path.exists(json_updates):
        return False
    cat_ids, cat_data, json_data = jloadme(json_path)
    cat_updates_ids, cat_updates, ignore = jloadme(json_updates)

    num_orig, num_new = len(cat_ids), len(cat_updates_ids)
    num_modded, num_added, num_tot = 0, 0, 0
    
    # filter if we only need items in a collection
    if collections_filter != None:
        cat_updates_ids = [myid for myid in cat_updates_ids if collections_filter in cat_updates[id]["collections"]]

    for rec_id in cat_updates_ids:
        if rec_id in cat_ids:
            num_modded += 1
            for field in cat_updates[rec_id]:
                if field == "start":
                    cat_data[rec_id][field] = bestdate(cat_data[rec_id][field],
                                                       cat_updates[rec_id][field],
                                                       True)
                elif field == "stop":
                    cat_data[rec_id][field] = bestdate(cat_data[rec_id][field],
                                                       cat_updates[rec_id][field],
                                                       False)
                else:
                    cat_data[rec_id][field] = cat_updates[rec_id][field]
        else:
            num_added += 1
            cat_data[rec_id] = cat_updates[rec_id]

    num_tot = len(cat_data.keys())
    cat_data = [cat_data[key] for key in sorted(cat_data.keys())]
    json_data["catalog"] = cat_data
    vf.version_file_timestamp(json_path)
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=4)

    if debug: print(f"Orig catalog had {num_orig}, update had {num_new}: added {num_added}, modded {num_modded}, final total {num_tot}")
    
    return True

def update_catalog_from_csv(json_path = 'catalog.json',
                            csv_path = 'cat.csv',
                            collections_filter = None):
    if not os.path.exists(json_path) or not os.path.exists(csv_path):
        return False
    cat_ids, cat_data, json_data = jloadme(json_path)

    # Now update with any data from CSV file, if it exists
    with open(csv_path, "r", newline="", encoding="utf-8-sig") as fin:
        reader = csv.DictReader(fin)
        for row in reader:
            rec_id = row.get("id")
            if not rec_id:
                continue

            if rec_id in cat_ids:
                target = cat_data[rec_id]
            else:
                target = {"id": rec_id, "title": rec_id, "indextype": "csv"}
                cat_ids.append(rec_id)
                cat_data[rec_id] = target

            has_collections = False
            for key, value in row.items():
                if key == "id" or value is None or value.strip() == "":
                    continue

                if key == "start" and "start" in cat_data:
                    # do not overwrite start times due to bug
                    continue
                
                if key == "collections":
                    has_collections = True
                    new_collection = value.strip()
                    target_collections = target.setdefault("collections", [])
                    if new_collection not in target_collections:
                        target_collections.append(new_collection)
                else:
                    target[key] = infer_type(value)
                    
            if collections_filter != None and has_collections == False:
                target["collections"] = collections_filter

    cat_data = [cat_data[key] for key in sorted(cat_data.keys())]
    json_data["catalog"] = cat_data
    vf.version_file_timestamp(json_path)
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=4)

    return True


def infer_type(value):
    value = value.strip()
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    for cast in (int, float):
        try:
            return cast(value)
        except (ValueError, TypeError):
            continue
    return value

# CLI entry points
def update_json_main():
    # parse args and call update_catalog_from_json
    import argparse
    parser = argparse.ArgumentParser(description="Update catalog from JSON.")
    parser.add_argument("json_path")
    parser.add_argument("json_updates")
    parser.add_argument("--collections_filter", dest="collections_filter", default=None)
    parser.add_argument("--debug", dest="debug", action="store_true")
    args = parser.parse_args()

    update_catalog_from_json(
        json_path=args.json_path,
        json_updates=args.json_updates,
        collections_filter=args.collections_filter,
        debug=args.debug,
    )

def update_csv_main():
    # parse args and call update_catalog_from_csv
    import argparse
    parser = argparse.ArgumentParser(description="Update catalog from CSV.")
    parser.add_argument("json_path")
    parser.add_argument("csv_path")
    parser.add_argument("--collections_filter", dest="collections_filter", default=None)
    args = parser.parse_args()

    update_catalog_from_csv(
        json_path=args.json_path,
        csv_path=args.csv_path,
        collections_filter=args.collections_filter,
    )

