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

manifest = 'sortedmanifest.csv' #'smallmanifest.csv' # 'sortedmanifest.csv'
coutfile = 'updates.csv'
errorsfile = 'errors.lst'
xml_path = '.'
strip_me = 'pub/data/'
ensure_prefix = 'spdf/cdaweb/data/'

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

now = time.time()
idcount = 0
ncount = 0
ierrors = 0

version_file(coutfile)
version_file(errorsfile)

regex_base, regex_pattern = cxc.load_fromxml(xml_path, strip_me=strip_me,
                                             ensure_prefix=ensure_prefix)

fin = open(manifest,"r")
cout = open(coutfile,"w")
ferr = open(errorsfile,"w")

# init setup to trigger first rounds
currid = 'junk'
tracker = ['junk','0','.']
ztime = '0000'
cache = {'start':'','s3key':'','fsize':''}
fout = open('junk.ignore','w')

endpattern = re.compile(r'\.(?:cdf|nc)$')

for line in fin:
    ncount += 1
    if ncount % 100000 == 0: print(f"\t up to file {ncount}")
    fname, fsize = parseline(line)
    if not endpattern.search(fname):
        continue
    dataid, filename = cxc.extract_just_dataid(fname,shortprefix=ensure_prefix)
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
        indexbase = cxc.best_indexdir(fname, short_prefix=ensure_prefix)
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
