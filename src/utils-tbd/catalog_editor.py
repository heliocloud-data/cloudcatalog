"""
Tool for manually updating catalog files
"""

import argparse
import json
from filelock import FileLock, Timeout


def lock_close(lock):
    """
    Close the lock on a file.
    """
    lock.release()


def lock_open(file_name: str):
    """
    Open a lock file for the named file.
    """
    lockfile = file_name + ".lock"
    lock_status = False

    lock = FileLock(lockfile, timeout=4)
    try:
        lock.acquire()
        lock_status = True
    except Timeout:
        print("File locked by other program, failing.")

    return lock_status, lock


def ingest_catalog(file_name):
    """
    Opens and returns the content of a catalog file
    """
    with open(file_name, "r", encoding="UTF-8") as fs_stream:
        data = json.load(fs_stream)
    return data


def show_catalog(catalog_data):
    """
    Shows the contents of a Catalog
    """
    for item in catalog_data["catalog"]:
        print("\n", item["id"])
        for key in item.keys():
            print("    ", key, ":", item[key])


def query_form():
    """
    Form for taking input to add to catalog
    """
    keys = [
        "id",
        "loc",
        "title",
        "startdate",
        "enddate",
        "modificationdate",
        "indexformat",
        "fileformat",
    ]

    dataset = {}
    for key in keys:
        data = input(key + ": ")
        dataset[key] = data

    return dataset


def add_entry(data, dataset):
    """
    Add an entry into the catalog data
    """
    data["catalog"].append(dataset)


def write_catalog(file_name, data):
    """
    Write the catalog back out.
    """
    lock_status, lock = lock_open(file_name)

    if lock_status:
        with open(file_name, "w", encoding="UTF-8") as c_file:
            json.dump(data, c_file, indent=4)
        lock_close(lock)

    return lock_status


def check_unique(data, dataset):
    """
    Returns True if the dataset already exists in the catalog data, else False.
    """
    id_set = [dataset["id"] for dataset in data["catalog"]]
    if dataset["id"] in id_set:
        return False
    return True


if __name__ == "__main__":
    print("Running the catalog editor")
    parser = argparse.ArgumentParser(
        prog="HelioCloud Catalog file editor",
        description="Allows for direct editing of catalog.json files on local disk.",
    )
    parser.add_argument(
        "-f", "--file", type=str, required=True, help="Name of the catalog file to load."
    )
    args = parser.parse_args()

    # Load the catalog file
    catalog_file = args.file
    print(f"Loading {catalog_file}.")
    catalog = ingest_catalog(catalog_file)
    show_catalog(catalog)

    # Prompt user to make an entry in the catalog
    new_entry = query_form()  # {"id":"test","loc":"s3://whatever","title":"Hi"}
    print(check_unique(catalog, new_entry))

    if check_unique(catalog, new_entry):
        add_entry(catalog, new_entry)
        show_catalog(catalog)
        STATUS = write_catalog(catalog_file, catalog)
        print("New file written: ", STATUS)

    print(check_unique(catalog, new_entry))
