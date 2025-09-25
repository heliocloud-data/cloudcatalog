#***** REQUIRES MANIFEST.csv is in sorted order by first id, then timestamp

# Works but needs better exception handling, run it to see what I mean

""" Streams a sorted MANIFEST.csv into its indices, also creates a versioned
    'updates.csv' to update the catalog.json with.
    (usually the case when just alphabetically sorting it)
   Also, that only .nc/.cdf files exist

   ***** REQUIRES MANIFEST.csv is in sorted order by first id, then timestamp

(Catalog updater does the 'update if exists, otherwise use XML to create)

    tbd: updating existing indices, updating catalog.json with partials
"""

import os
import pathlib
import re
import shutil
import time
import cdaweb_xml_checker as cxc

DEBUG = False

def set_presets(manifest='manifest_sorted.csv',
                coutfile='updates.csv',
                errorsfile='errors.lst',
                xml_path='./all.xml',
                strip_me='pub/data/',
                ensure_prefix='spdf/cdaweb/data/',
                add_prefix='s3://gov-nasa-hdrl-data1/'):
    presets = {
        "manifest" : manifest,
        "coutfile" : coutfile,
        "errorsfile" : errorsfile,
        "xml_path" : xml_path,
        "strip_me" : strip_me,
        "ensure_prefix" : ensure_prefix,
        "add_prefix" : add_prefix
        }
    return presets

def check_presets(presets):
    safety = True
    for mykey in presets.keys():
        print(f"{mykey}: {presets[mykey]}")
        if (mykey == 'manifest' or mykey == 'xml_path') and not os.path.exists(presets[mykey]):
            print(f"Warning, {mykey}: {presets[mykey]} does not exist")
            safety = False
    return safety

def dumpline(fout,cache):
    fout.write(f"{cache['start']},{cache['stop']},{cache['s3key']},{cache['fsize']}\n")
    #print("\t\t",cache)

def parseline(line):
    line=line.rstrip()
    items=line.split(',')
    fsize = items[-1]
    fname = items[-2]
    return fname, fsize

def version_file(filepath):
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

def manifest2indices(presets=None):
    if presets == None: presets = set_presets()
    if check_presets(presets) == False:
        return
    
    now = time.time()
    idcount, ncount, ierrors = 0, 0, 0
    version_file(presets["coutfile"])
    version_file(presets["errorsfile"])
    regex_base, regex_pattern = cxc.load_fromxml(presets["xml_path"],
                                strip_me=presets["strip_me"],
                                ensure_prefix=presets["ensure_prefix"])
    fin = open(presets["manifest"],"r")
    cout = open(presets["coutfile"],"w")
    ferr = open(presets["errorsfile"],"w")

    # init setup to trigger first rounds
    currid = 'junk'
    tracker = ['id','s3key','start']
    ztime = 'stop'
    cache = {'start':'','s3key':'','fsize':''}
    fout = open('junk.ignore','w')

    endpattern = re.compile(r'\.(?:cdf|nc)$')

    for line in fin:
        ncount += 1
        if ncount % 100000 == 0: print(f"\t up to file {ncount}")
        fname, fsize = parseline(line)
        if not endpattern.search(fname):
            continue
        dataid, filename = cxc.extract_just_dataid(fname,shortprefix=presets["ensure_prefix"])
        if dataid == None:
            ferr.write(f"{fname}, dataid not found\n")
            ierrors += 1
            continue
        if dataid != currid:
            cache['stop']=ztime
            try:
                dumpline(fout,cache)
                fout.close()
            except:
                pass
            try:
                tracker.append(ztime)
                cout.write(','.join(tracker)+'\n')
            except:
                tracker.pop() # no valid new id yet so remove that last bad field
                pass
            dataid, indexbase, x_regex = cxc.extract_regex(regex_base, regex_pattern, fname)
            indexbase = cxc.best_indexdir(fname, short_prefix=presets["ensure_prefix"],add_prefix=presets["add_prefix"])
            ztime = cxc.extract_datetime(fname, x_regex, form="str")
            if ztime == None:
                ferr.write(f"{fname},{x_regex}, date not found\n")
                ierrors += 1
                continue
            year = ztime[0:4]
            os.makedirs(indexbase,exist_ok=True)
            tracker = [dataid,indexbase,ztime]
            foutname = indexbase + '/' + dataid + '_' + year + '.csv'
            if DEBUG: print(f"Initiating {dataid} {year} index {foutname}")
            fout = open(foutname,"w")
            fout.write('#start,stop,s3key,filesize\n')
            if presets["add_prefix"] != None:
                fname = presets["add_prefix"] + fname
            cache = {'start':ztime,'s3key':fname,'fsize':fsize}
            curryear = year
            currid = dataid
            idcount += 1
        else:
            ztime = cxc.extract_datetime(fname, x_regex, form="str")
            if ztime == None:
                ferr.write(f"{fname}, date not found with regex {x_regex}\n")
                ierrors += 1
                continue
            cache['stop']=ztime
            dumpline(fout,cache)
            if presets["add_prefix"] != None:
                fname = presets["add_prefix"] + fname
            cache = {'start':ztime,'s3key':fname,'fsize':fsize}
            year = ztime[0:4]
            if year != curryear:
                fout.close()
                foutname = indexbase + '/' + dataid + '_' + year + '.csv'
                fout = open(foutname,"w")
                fout.write('#start,stop,s3key,filesize\n')
                if DEBUG: print(f"\tYearskip {dataid} {year} index {foutname}")
                curryear = year
        
    cache['stop']=ztime
    dumpline(fout,cache)
    tracker.append(ztime)
    cout.write(','.join(tracker)+'\n')
    fout.close()
    cout.close()
    pathlib.Path('junk.ignore').unlink(missing_ok=True)

    print("Total runtime %.2f min, %d dataIDs, %d files, %d errors" %
          ((time.time() - now) / 60, idcount, ncount, ierrors))

def m2i_main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        prog="manifest2indices",
        description="Merge cloudcatalog JSON files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--manifest", default="manifest_sorted.csv",
                        help="Path to the manifest CSV")
    parser.add_argument("--coutfile", default="updates.csv",
                        help="Output CSV for updates")
    parser.add_argument("--errorsfile", default="errors.lst",
                        help="Output file for errors")
    parser.add_argument("--xml-path", dest="xml_path", default="./all.xml",
                        help="Full name of XML files")
    parser.add_argument("--strip-me", dest="strip_me", default="pub/data/",
                        help="Prefix to strip from paths")
    parser.add_argument("--ensure-prefix", dest="ensure_prefix",
                        default="spdf/cdaweb/data/",
                        help="Required prefix to enforce on paths")
    parser.add_argument("--add-prefix", dest="add_prefix",
                        default="s3://gov-nasa-hdrl-data1/",
                        help="Required start to add on all index & file paths")

    args = parser.parse_args(argv)

    presets = set_presets(
        manifest=args.manifest,
        coutfile=args.coutfile,
        errorsfile=args.errorsfile,
        xml_path=args.xml_path,
        strip_me=args.strip_me,
        ensure_prefix=args.ensure_prefix,
        add_prefix=args.add_prefix,
    )

    manifest2indices(presets=presets)

    
if __name__ == "__main__":
    m2i_main()
