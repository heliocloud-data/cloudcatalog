"""
Tests ls-like * wildcard matching
"""

import pytest
import cloudcatalog


def test_ls_wildcard():
    """tests that function"""
    pattern_short = "tha_l2_fft_202501*_v*.cdf"
    pattern_long = "*" + pattern_short
    dataid, start, stop = "THA_L2_FFT", "2025-01-01T00:00:00Z", "2025-02-02T00:00:00Z"
    fr = cloudcatalog.CloudCatalog("s3://gov-nasa-hdrl-data1/")  # CDAWeb cloud home
    df = fr.request_cloud_catalog(dataid, start, stop)

    # will find 0 because regex is too rigid, does not match full path
    filekeys = fr.ls_wildcard(df, pattern_short)
    assert len(filekeys) == 0
    # tests using just the basename, should return 5
    filekeys = fr.ls_wildcard(df, pattern_short, use_basename=True)
    assert len(filekeys) >= 2
    # tests using just the basename via extra *, should return 5
    filekeys = fr.ls_wildcard(df, pattern_long)
    assert len(filekeys) >= 2
