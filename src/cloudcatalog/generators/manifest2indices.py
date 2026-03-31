"""***** REQUIRES MANIFEST.csv is in sorted order by first id, then timestamp

 Works but needs better exception handling, run it to see what I mean

Streams a sorted MANIFEST.csv into its indices, also creates a versioned
    'updates.csv' to update the catalog.json with.
    (usually the case when just alphabetically sorting it)
   Also, that only .nc/.cdf files exist

   ***** REQUIRES MANIFEST.csv is in sorted order by first id, then filesize

(Catalog updater does the 'update if exists, otherwise use XML to create)

    tbd: updating existing indices, updating catalog.json with partials
"""

import os
import pathlib
import re
import shutil
import time
from . import cdaweb_xml_checker as cxc

DEBUG = False

# if --filter_filetypes, then only indexes these filename end stems
endpattern = re.compile(r"\.(?:cdf|nc|fits|fts)$")


def set_presets(
    manifest="manifest_sorted.csv",
    coutfile="updates.csv",
    errorsfile="errors.lst",
    ignorefile="ignore.lst",
    newidsfile="newids.csv",
    metadata_file="./all.xml",
    filter_filetypes=True,
    strip_me="pub/data/",
    ensure_prefix="spdf/cdaweb/data/",
    add_prefix="s3://gov-nasa-hdrl-data1/",
    quiet=False,
):
    """shorthand to store many user-specified values into a passable dict"""
    presets = {
        "manifest": manifest,
        "coutfile": coutfile,
        "errorsfile": errorsfile,
        "ignorefile": ignorefile,
        "newidsfile": newidsfile,
        "metadata_file": metadata_file,
        "filter_filetypes": filter_filetypes,
        "strip_me": strip_me,
        "ensure_prefix": ensure_prefix,
        "add_prefix": add_prefix,
        "quiet": quiet,
    }
    return presets


def check_presets(presets):
    """verifies all presets are set"""
    safety = True
    for mykey in presets.keys():
        if presets["quiet"] is False:
            print(f"\t{mykey}: {presets[mykey]}")
        if mykey == "manifest" and not os.path.exists(presets[mykey]):
            print(f"Warning, {mykey}: {presets[mykey]} does not exist")
            safety = False
        if (
            mykey == "metadata_file"
            and presets[mykey] is not None
            and not os.path.exists(presets[mykey])
        ):
            print(f"Warning, {mykey}: {presets[mykey]} does not exist")
            safety = False
    return safety


def dumpline(fout, cache):
    """tries to write cache"""
    try:
        fout.write(
            f"{cache['start']},{cache['stop']},{cache['s3key']},{cache['fsize']}\n"
        )
    except:
        pass
        # fake print(f"Error writing line for {cache['s3key']}, continuing with errors")
    # print("\t\t",cache)


def parseline(line):
    """simple name/size parser"""
    line = line.rstrip()
    items = line.split(",")
    fsize = items[-1]
    fname = items[-2]
    return fname, fsize


def version_file(filepath):
    """simple version numbering"""
    if filepath.startswith("s3://"):
        print("Warning, cannot version files in S3 yet.")
        return

    if not os.path.exists(filepath):
        # print("File does not exist. No need to version.")
        return

    dirname, filename = os.path.split(filepath)
    name, ext = os.path.splitext(filename)

    version = 1
    while True:
        new_filename = f"{name}_v{version}{ext}"
        new_filepath = os.path.join(dirname, new_filename)
        if not os.path.exists(new_filepath):
            break
        version += 1

    shutil.move(filepath, new_filepath)
    # print(f"File versioned as: {new_filepath}")


def tracker_cleanup(trackerfile):
    """format is  list of lists ['id','index','start','end']
    reconciles multiple entries
    """
    with open(trackerfile) as fin:
        trackerdata = fin.readlines()
    trackerhash = {}
    for line in trackerdata:
        try:
            dataid, index, start, end = line.split(",")
        except:
            print("Could not parse ", line)
            continue
        if dataid in trackerhash.keys():
            trackerhash[dataid] = {
                "index": index,
                "start": min(start, trackerhash[dataid]["start"]),
                "end": max(end, trackerhash[dataid]["end"]),
            }
        else:
            trackerhash[dataid] = {"index": index, "start": start, "end": end}
    newtracker = []
    for dataid in sorted(trackerhash.keys()):
        newtracker.append(
            [
                dataid,
                trackerhash[dataid]["index"],
                trackerhash[dataid]["start"],
                trackerhash[dataid]["end"],
            ]
        )
    return newtracker


def manifest2indices(presets=None):
    """main"""
    if presets is None:
        presets = set_presets()
    if check_presets(presets) is False:
        print("Error, some presets not valid, exiting.")
        return

    now = time.time()
    idcount, ncount, ierrors = 0, 0, 0
    version_file(presets["coutfile"])
    version_file(presets["errorsfile"])
    version_file(presets["ignorefile"])
    version_file(presets["newidsfile"])
    use_regex = True
    regex_matchme = None
    if presets["metadata_file"] is None:
        regex_base, regex_pattern = {}, {}
        use_regex = False
        """
        when no regexes then grab the 1st 3 in path to make before /indices!!!
        e.g. contrib/jhuapl/supermag -> indices
             sdac/hinode/sot/
        """
    elif presets["metadata_file"].endswith(".xml"):
        regex_base, regex_pattern = cxc.load_fromxml(
            presets["metadata_file"],
            strip_me=presets["strip_me"],
            ensure_prefix=presets["ensure_prefix"],
        )
    elif presets["metadata_file"].endswith(".json"):
        regex_base, regex_pattern = cxc.load_fromjson(
            presets["metadata_file"], ensure_prefix=presets["ensure_prefix"]
        )
    elif presets["metadata_file"].endswith(".csv"):
        regex_base, regex_pattern, regex_matchme = cxc.load_fromcsv(
            presets["metadata_file"], ensure_prefix=presets["ensure_prefix"]
        )
    else:
        regex_base, regex_pattern = {}, {}
    fin = open(presets["manifest"], "r")
    cout = open(presets["coutfile"], "w")
    ferr = open(presets["errorsfile"], "w")
    fignore = open(presets["ignorefile"], "w")
    fnewids = open(presets["newidsfile"], "w")

    # init setup to trigger first rounds
    currid = "junk"
    tracker = ["id", "index", "start"]
    ztime = "stop"
    cache = {"start": "", "s3key": "", "fsize": ""}
    fout = open("junk.ignore", "w")

    for line in fin:
        ncount += 1
        if ncount % 100000 == 0:
            print(f"\t up to file {ncount}")
        fname, fsize = parseline(line)
        if presets["filter_filetypes"] and not endpattern.search(fname):
            fignore.write(f"{fname} ignored, no whitelisted filestem\n")
            continue
        try:
            dataid, filename = cxc.extract_matchme(fname, regex_matchme)
        except:
            dataid, filename = cxc.extract_just_dataid(fname)
        if dataid is None:
            ferr.write(f"{fname}, dataid not found\n")
            ierrors += 1
            continue
        if dataid != currid:
            cache["stop"] = ztime
            try:
                dumpline(fout, cache)
                fout.close()
            except:
                pass
            try:
                tracker.append(ztime)
                cout.write(",".join(tracker) + "\n")
            except:
                tracker.pop()  # no valid new id yet so remove that last bad field
                pass
            if use_regex is False:
                indexbase = cxc.trio_indexdir(fname, add_prefix=presets["add_prefix"])
            else:
                try:
                    indexbase = regex_base[dataid]
                except:
                    indexbase = cxc.best_indexdir(
                        fname,
                        short_prefix=presets["ensure_prefix"],
                        add_prefix=presets["add_prefix"],
                    )
            try:
                x_regex = regex_pattern[dataid]
                # fake, probably just rewrite below to be more robust?
            except:
                dataid_ignore, indexbase_ignore, x_regex = cxc.extract_regex(
                    regex_base, regex_pattern, fname
                )
            if dataid not in regex_pattern.keys():
                fnewids.write(f"{dataid},{fname}\n")
                # print(f"fake new ids, {dataid},{fname}\n")
                regex_pattern[dataid] = x_regex
                regex_base[dataid] = indexbase
            if x_regex != regex_pattern[dataid]:
                regex_pattern[dataid] = x_regex  # update
            ztime = cxc.extract_datetime(fname, x_regex, form="str")
            if ztime is None:
                ferr.write(f"{fname},{x_regex}, date not found\n")
                ierrors += 1
                continue
            year = ztime[0:4]
            os.makedirs(indexbase, exist_ok=True)
            tracker = [dataid, indexbase, ztime]
            foutname = indexbase + "/" + dataid + "_" + year + ".csv"
            fout = open(foutname, "a+")
            if os.path.getsize(foutname) == 0:
                fout.write("#start,stop,s3key,filesize\n")
            if DEBUG:
                print(f"Writing {dataid} {year} index {foutname}")
            if presets["add_prefix"] is not None:
                fname = presets["add_prefix"] + fname
            cache = {"start": ztime, "s3key": fname, "fsize": fsize}
            curryear = year
            currid = dataid
            idcount += 1
        else:
            ztime = cxc.extract_datetime(fname, x_regex, form="str")
            if ztime is None:
                ferr.write(f"{fname}, date not found with regex {x_regex}\n")
                ierrors += 1
                continue
            cache["stop"] = ztime
            dumpline(fout, cache)
            if presets["add_prefix"] is not None:
                fname = presets["add_prefix"] + fname
            cache = {"start": ztime, "s3key": fname, "fsize": fsize}
            year = ztime[0:4]
            if year != curryear:
                fout.close()
                foutname = indexbase + "/" + dataid + "_" + year + ".csv"
                fout = open(foutname, "a+")
                if os.path.getsize(foutname) == 0:
                    fout.write("#start,stop,s3key,filesize\n")
                if DEBUG:
                    print(f"\tYearskip {dataid} {year} index {foutname}")
                curryear = year

    cache["stop"] = ztime
    dumpline(fout, cache)
    tracker.append(ztime)
    # tracker = tracker_cleanup(tracker) # joins multiple entries
    cout.write(",".join(tracker) + "\n")
    fout.close()
    ferr.close()
    fignore.close()
    fnewids.close()
    cout.close()
    pathlib.Path("junk.ignore").unlink(missing_ok=True)

    print(
        "Total runtime %.2f min, %d dataIDs, %d files, %d errors"
        % ((time.time() - now) / 60, idcount, ncount, ierrors)
    )


def m2i_main(argv=None):
    """callable routine"""
    import argparse

    parser = argparse.ArgumentParser(
        prog="manifest2indices",
        description="Merge cloudcatalog JSON files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("manifest", help="manifest.csv or similar input file")
    parser.add_argument(
        "add_prefix",
        help="Required start to add on all index & file paths, e.g. s3://gov-nasa-hdrl-data1/",
    )

    # toggle off for speed or if files exist other than .cdf/.nc/.fits/.fts
    parser.add_argument(
        "--filter_filetypes",
        dest="filter_filetypes",
        action="store_true",
        help="toggle on whether to whitelist filetypes",
    )

    # useful per-repository definitions
    parser.add_argument(
        "--ensure_prefix",
        dest="ensure_prefix",
        default=None,
        help="Required prefix to enforce on paths, e.g. spdf/cdaweb/data/",
    )
    parser.add_argument(
        "--metadata_file",
        dest="metadata_file",
        default=None,
        help="Full name of metadata file (XML or JSON)",
    )
    parser.add_argument(
        "--strip_me",
        dest="strip_me",
        default="pub/data/",
        help="Prefix to strip from paths",
    )

    # defaults that probably don't need changing
    parser.add_argument(
        "--coutfile",
        dest="coutfile",
        default="updates.csv",
        help="Output CSV for updates",
    )
    parser.add_argument(
        "--errorsfile",
        dest="errorsfile",
        default="errors.lst",
        help="Output file for errors",
    )
    parser.add_argument(
        "--ignorefile",
        dest="ignorefile",
        default="ignore.lst",
        help="Output file for files with wrong filestems (only if --filker_filetypes is set)",
    )
    parser.add_argument(
        "--newidsfile",
        dest="newidsfile",
        default="newids.csv",
        help="Outputs IDs that were not in the metadata file",
    )

    parser.add_argument("--quiet", dest="quiet", action="store_true", help="quiet")

    args = parser.parse_args(argv)

    presets = set_presets(
        manifest=args.manifest,
        coutfile=args.coutfile,
        errorsfile=args.errorsfile,
        ignorefile=args.ignorefile,
        newidsfile=args.newidsfile,
        metadata_file=args.metadata_file,
        filter_filetypes=args.filter_filetypes,
        strip_me=args.strip_me,
        ensure_prefix=args.ensure_prefix,
        add_prefix=args.add_prefix,
        quiet=args.quiet,
    )

    manifest2indices(presets=presets)


if __name__ == "__main__":
    m2i_main()
