import json
import csv
import os
import shutil
from datetime import datetime


def update_catalog_json(json_path, csv_path, output_path):
    if not os.path.exists(json_path) or not os.path.exists(csv_path):
        return False

    with open(json_path, "r") as f:
        json_data = json.load(f)

    catalog = json_data.setdefault("catalog", [])
    catalog_map = {entry["id"]: entry for entry in catalog}

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record_id = row.get("id")
            if not record_id:
                continue

            if record_id in catalog_map:
                target = catalog_map[record_id]
            else:
                target = {"id": record_id, "title": record_id, "indextype": "csv"}
                catalog.append(target)
                catalog_map[record_id] = target

            for key, value in row.items():
                if key == "id" or value is None or value.strip() == "":
                    continue

                if key == "collections":
                    new_collection = value.strip()
                    target_collections = target.setdefault("collections", [])
                    if new_collection not in target_collections:
                        target_collections.append(new_collection)
                else:
                    target[key] = infer_type(value)

    with open(output_path, "w") as f:
        json.dump(json_data, f, indent=2)

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


def perform_cleanup(json_path, csv_path, output_path):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    versioned_path = f"{json_path}.{timestamp}.bak"
    shutil.move(json_path, versioned_path)
    shutil.move(output_path, json_path)
    os.remove(csv_path)


if __name__ == "__main__":
    jfile = "test/catalog_stub.json"
    ofile = "test/catalog_updated.json"
    cfile = "test/cat.csv"
    success = update_catalog_json(jfile, cfile, ofile)
    if success:
        perform_cleanup(jfile, cfile, ofile)
    print("Update succeeded." if success else "Update failed: missing input file(s).")
