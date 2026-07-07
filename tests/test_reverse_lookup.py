"""
tests reverse lookup aka give file path for a dataid
Works like a regex, e.g. if looking for path/path/2002/file it will
likely miss because indices are in path/path
Also does useful work for cdaweb because all indices are in top level,
not data-specific areas.
"""

import os
import pytest
import cloudcatalog


def test_reverse_lookup():
    """core test"""
    fr = cloudcatalog.CloudCatalog("s3://gov-nasa-hdrl-data1/")

    items = [
        [
            "PARKERSOLARPROBE_WISPR_FITS_LEVEL2_PT30M",
            "psp_wispr/indices",
            "# an sdac example",
        ],
        ["A1_K0_MPA", "spdf/cdaweb/data/indices", "# an spdf/cdaweb example"],
    ]
    for trio in items:
        dataid = trio[0]
        datapath = trio[1]
        test = fr.get_entry(dataid)
        dataids = fr.reverse_lookup_ids(datapath)
        dataid = dataids[0]
        sample = fr.sample_file(dataid)
        # print(dataid, sample)
        assert len(dataids) > 1 and len(sample) > 0


if __name__ == "__main__":
    test_reverse_lookup()
