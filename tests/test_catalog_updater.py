import pytest
from pathlib import Path
import shutil

from cloudcatalog.updater import update_catalog_from_json
from cloudcatalog.updater import update_catalog_from_csv

def test_catalog_updater():
    # define file names to run on
    jfile = str(Path(__file__).parent / "catdata/catalog.json")
    ofile = str(Path(__file__).parent / "catdata/catalog_stub.json")
    cfile = str(Path(__file__).parent / "catdata/cat.csv")
    # first copy the canonicals over
    jtest = str(Path(__file__).parent / "catdata/catalog.json-test")
    otest = str(Path(__file__).parent / "catdata/catalog_stub.json-test")
    ctest = str(Path(__file__).parent / "catdata/cat.csv-test")
    try:
        shutil.copy(jtest,jfile)
    except shutil.SameFileError:
        pass
    try:
        shutil.copy(otest,ofile)
    except shutil.SameFileError:
        pass
    try:
        shutil.copy(ctest,cfile)
    except shutil.SameFileError:
        pass
    # run the test
    success = update_catalog_from_json(jfile,ofile)
    assert success == True
    #print("JSON pdate succeeded." if success else "Update failed: missing input file(s).")
    success = update_catalog_from_csv(jfile,cfile)
    assert success == True
    #print("CSV update succeeded." if success else "Update failed: missing input file(s).")
    # clean up?
