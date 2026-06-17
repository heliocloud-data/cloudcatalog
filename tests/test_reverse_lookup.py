"""tests reverse lookup aka give file path for a dataid"""

import os
import pytest
import cloudcatalog


def test_reverse_lookup():
    """core test"""
    fr = cloudcatalog.CloudCatalog("s3://gov-nasa-hdrl-data1/")
    dataid = fr.reverse_lookup_ids("mms/indices/")[0]
    # print("reverse lookup", dataid)
    # dataid="mms_hmi"
    # dataid = "GENESIS_3DL2_GIM"
    test = fr.get_entry(dataid)
    print("fetched", test)
    # sample = fr.sample_file(dataid)
    # print(dataid, sample)
    # print("files reside in", os.path.dirname(sample))
    assert True


# problem, for this test case the 2001 files are in .../2001/, but
# the 2002 files are in .../2002/, etc
# FIX for reverse-index-matching, or otherwise tweak...
#    if pattern is always 'sometimes there is a year end' we are in good
#    shape, but if it does e.g.  2001/fgm/l2  then we are screwed.
#    Is there a cdaweb pattern?  Make a scanner to check!!
#
