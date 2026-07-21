"""Given a catalog.json, returns list of ids for all items that
  match a given COLLECTION

 usage:
    idlist = find_ids_by_collection(json_path,collection_name)

e.g. idlist = find_ids_by_collection('catalog.json','CDAWeb')

"""

import json


def find_ids_by_collection(json_path="catalog.json", collection_name=None):

    if collection_name == None:
        print("Please give it a collection to search for. Exiting.")
        return None

    with open(json_path, "r") as f:
        data = json.load(f)

    results = []
    for item in data.get("catalog", []):
        collections = item.get("collections", [])
        if "CDAWeb" in collections:
            results.append((item.get("id"), item.get("index")))
    return results


# Example usage
if __name__ == "__main__":
    ids = find_ids_by_collection("catalog.json", "CDAWeb")
    print(ids)
