import re
import time
import catalog_updater as cu
import reorder_csv_columns as rcc
import spdf_to_db as spdf

"""
Note our S3 manifest typically includes index files, so we have to be sure
we only extract filenames of '.cdf' and '.nc' to avoid recursive messiness!
"""

def splitter(fname='MANIFEST.csv',justmms='justmms.csv',notmms='notmms.csv'):
    pattern = re.compile(r'spdf/cdaweb/data/mms/')
    filepattern = re.compile(r'\.cdf|\.nc')
    with open(fname,'r',encoding='utf-8') as infile, \
    open(justmms,'w',encoding='utf-8') as mms_out, \
    open(notmms,'w',encoding='utf-8') as not_out:
        for line in infile:
            if filepattern.search(line):
                (mms_out if pattern.search(line) else not_out).write(line)
    return justmms, notmms

start = time.time()
now = time.time()
source = "manifest.csv"
print(f"Splitting {source} into MMS and non-MMS halves")
justmms_infile, notmms_infile = splitter(source)
justmms_r, notmms_r = "justmms_r.csv", "notmms_r.csv"
#reorder=[3,0,4,5,6,7,8,2,1]
reorder=[1,0]
resub=(r"^spdf/cdaweb/", r"pub/")
print(f"Done split, took {time.time()-now} seconds")

now = time.time()
print("Re-ordering the 2 CSV files")
rcc.reorder_csv_columns(justmms_infile, justmms_r, reorder, resub)
rcc.reorder_csv_columns(notmms_infile, notmms_r, reorder, resub)
print(f"Done re-order, took {time.time()-now} seconds")

now=time.time()
print("Doing the full ingest cycle for both, this takes time.")
spdf.ingest_s3_inventory(db_name="justmms.db",infile=justmms_r,
                         staging_prefix="s3/")
spdf.ingest_s3_inventory(db_name="notmms.db",infile=notmms_r,
                         staging_prefix="s3/")
print(f"Done ingest and indices, took {time.time()-now} seconds")

now=time.time()
print("Updating catalog.json (quick)")
catnot = 'catalog_updates2.csv'
catmms = 'catalog_updates2_v1.csv'
jfile = 'catalog_jul10.json'
ofile = 'catalog_interim.json'
ffile = 'catalog_final.json'
success  = cu.update_catalog_json(jfile, catnot, ofile, collections=["CDAWeb","MMS"])
success  = cu.update_catalog_json(ofile, catmms, ffile, collections=["CDAWeb"])
print(f"Done catalog update, took {time.time()-now} seconds")

print("See catalog_final.json, all indices (JUSTMMS and NOTMMS) are in s3/")
print(f"Total elapsed time: {time.time()-start} seconds")

print("Copy things to s3://scratch-data-ops")

