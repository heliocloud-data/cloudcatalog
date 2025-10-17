import json

def find_ids_with_cdaweb(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    results = []
    for item in data.get("catalog", []):
        collections = item.get("collections", [])
        if "CDAWeb" in collections:
            results.append((item.get("id"),item.get("index")))
    return results

# Example usage
if __name__ == "__main__":
    ids = find_ids_with_cdaweb("catalog.json")
    print(ids)
