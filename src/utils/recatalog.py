"""
Given a shift in data from A to B, updates the individual indices plus
'catalog.json' with the new location using regex.

Updates actual indices in place (saving old ones as a backup),
generates a temporary 'catalog.json.tmp', validates, then
moves 'catalog.json.tmp' to 'catalog.json'

Backs up the old 'catalog.json' and indices as well.

Two modes:
Mode A: Update indices before data is moved
    1) read in catalog.json, follow to indices, update *.csv
    2) update catalog.json with new loc
Mode B: Data was moved already so catalog.json, *.csv are out of date
    1) update catalog.json with new loc
    2) read in catalog.json, follow to indices, update *.csv

tbd: auto-gen of test script and run tests
     'fixindices' that can do index repairs or mods
     maybe does this accept actual regexes or just do string replacements?
     make an 'addcollection' tool

Potential problem/edge case:
 right now  spdf/cdaweb/data/mms is correct but spdf/cdaweb/* is not (including an 'mms' directory)
      so we'd need to first rename/move spdf/cdaweb/data/mms away (which we know)
      but the cdaweb migration means changing '/spdf/cdaweb/' to '/spdf/cdaweb/data/' but this
      would make existing /spdf/cdaweb/data/mms become /spdf/cdaweb/data/data/mms, hmm...
      Need to add 'regex to exclude'



"""

import json
import os
import shutil
import re
import pandas
from smart_open import open


def get_inputs():
    dryrun = input("Is this a test dryrun, or a production run? (test/prod): ")
    if dryrun.lower()[0] == "p":
        dryrun = False
        print("\tOkay, doing the actual production writes.")
    else:
        dryrun = True
        print("\tTest dryrun, no actual files will be changed.")
    bucket = input("Which S3 bucket is this (e.g. 'helio-public'): ")
    catname = "s3://" + bucket + "/catalog.json"
    try:
        catalog = fetch_catalog(catname)
    except:
        print(f"Error, unable to fetch a valid catalog at {catalog}, exiting")

    yn = input("Is the data going to the same bucket? y/n: ")
    if yn.lower() == "n":
        newbucket = input(
            "What is the new S3 destination bucket name (e.g. 'gov-nasa-hdrl-data1'): "
        )
    else:
        newbucket = bucket

    oldloc = input(
        "Enter old location string you want to replace, e.g. '/contrib/euvml/': "
    )
    newloc = input("Enter new location string, e.g. '/contrib/jhuapl/euvml/': ")
    exclude = input(
        "Any words/strings to exclude i.e. not change or overwrite? (e.g. for CDAWeb move, exclude 'mms') Enter string or leave blank if none: "
    )
    if len(exclude) < 1:
        exclude = None
    mode = None
    while mode not in ["A", "B"]:
        mode = input(
            "Enter mode.\nA = data still in old loc so update indices and catalog.json in preparation for move,\nB = data was already moved to new loc but not re-indexed so both catalog.json and indices need to be updated.\n(A/B): "
        )
        mode = mode.upper()
    inputs = {
        "mode": mode,
        "bucket": bucket,
        "newbucket": newbucket,
        "oldloc": oldloc,
        "newloc": newloc,
        "exclude": exclude,
        "catname": catname,
        "dryrun": dryrun,
    }

    yn = input(
        f"Is this correct? Mode {mode}, updating indices to change {oldloc} to {newloc}, dryrun={dryrun}  (y/n): "
    )
    if yn.lower() != "y":
        print("Exiting, feel free to start again.")
        exit()
    imatch = update_catalog(inputs, catalog, force_dryrun=True)
    yn = input(f"There are {imatch} entries that will be updated, continue? (y/n): ")
    if yn.lower() != "y":
        print("Exiting, feel free to start again.")
        exit()

    return inputs


def fetch_catalog(catname):
    with open(catname) as fin:
        catalog = json.load(fin)
    return catalog


def update_catalog(inputs, catalog, force_dryrun=None):
    imatch = 0
    if force_dryrun == None:
        dryrun = inputs["dryrun"]
    else:
        dryrun = True
    for jj in catalog["catalog"]:
        indexbase = jj["index"]
        if inputs["oldloc"] in indexbase and (
            inputs["exclude"] is None or inputs["exclude"] not in indexbase
        ):
            imatch += 1
            jj["index"] = re.sub(inputs["oldloc"], inputs["newloc"], jj["index"])
            if inputs["bucket"] != inputs["newbucket"]:
                jj["index"] = re.sub(inputs["bucket"], inputs["newbucket"], jj["index"])
            # note this does replace-in-place, altering 'catalog' itself
    if not dryrun:
        backup_index(inputs["catname"])
        with open(inputs["catname"], "w") as fout:
            json.dump(catalog, fout, indent=4)
            print(f"Success, new {inputs['catname']} created.")
    return imatch


def update_indices(inputs, catalog):
    numfiles = 0
    numsuccesses = 0
    for jj in catalog["catalog"]:
        indexbase = jj["index"]
        if inputs["oldloc"] in indexbase and (
            inputs["exclude"] is None or inputs["exclude"] not in indexbase
        ):
            dataid = jj["id"]
            startyear = jj["start"][0:4]
            stopyear = jj["stop"][0:4]
            for i in range(int(startyear), int(stopyear)):
                fcsv = dataid + "_" + str(i) + ".csv"
                findex = indexbase + fcsv
                status = update_index(findex, inputs)
                numfiles += 1
                if status == True:
                    numsuccesses += 1
    if numfiles != numsuccesses:
        print(
            f"Warning, only processed {numsuccesses} indices out of {numfiles} matches. Continuing"
        )
        status = False
    else:
        status = True
    return status


def backup_index(findex):
    # using 'open' instead of os/shutils because of need for S3 writes
    fbck = findex + ".bck"
    with open(findex, "r") as fin:
        with open(fbck, "w") as fout:
            fout.writelines(fin.readlines())
    return


def update_index(findex, inputs):
    if not inputs["dryrun"]:
        backup_index(findex)
    try:
        with open(findex, "r") as fin:
            lines = fin.readlines()
            lines = [re.sub(inputs["oldloc"], inputs["newloc"], l) for l in lines]
            if inputs["bucket"] != inputs["newbucket"]:
                lines = [
                    re.sub(inputs["bucket"], inputs["newbucket"], l) for l in lines
                ]
    except:
        print(f"Warning, {findex} not found, continuing")
        return False
    try:
        if not inputs["dryrun"]:
            with open(findex, "w") as fout:
                fout.writelines(lines)
        return True
    except:
        print(f"Error, could not write to {findex}, exiting")
        return False


# os.makedirs(destdir,exist_ok=True)

inputs = get_inputs()
catalog = fetch_catalog(inputs["catname"])
if inputs["mode"] == "A":
    status = update_indices(inputs, catalog)
    imatch = update_catalog(inputs, catalog)
else:
    imatch = update_catalog(inputs, catalog)
    status = update_indices(inputs, catalog)

print(f"Completed, {imatch} entries updated")
