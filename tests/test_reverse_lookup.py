import pytest
import cloudcatalog
import os


def test_reverse_lookup():

    fr = cloudcatalog.CloudCatalog("s3://gov-nasa-hdrl-data1/")
    id = fr.reverse_lookup_ids("genesis/gim/3dl2_gim")[0]
    print("reverse lookup", id)
    # id="mms_hmi"
    # id = "GENESIS_3DL2_GIM"
    test = fr.get_entry(id)
    print("fetched", test)
    sample = fr.sample_file(id)
    print(id, sample)
    print("files reside in", os.path.dirname(sample))


# problem, for this test case the 2001 files are in .../2001/, but
# the 2002 files are in .../2002/, etc
# FIX for reverse-index-matching, or otherwise tweak...
#    if pattern is always 'sometimes there is a year end' we are in good
#    shape, but if it does e.g.  2001/fgm/l2  then we are screwed.
#    Is there a cdaweb pattern?  Make a scanner to check!!
#
