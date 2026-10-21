import cloudcatalog

"""
Test of the new HAPI-style returns
"""


def test_real_cloudcatalog_to_hapi():
    server = "s3://gov-nasa-hdrl-data1/"
    dataid = "MMS1_FEEPS_BRST_L2_ELECTRON"
    start = "2020-02-01T00:00:00Z"
    stop = "2020-02-02T00:00:00Z"

    df2, meta = cloudcatalog.hapi_cloudcatalog(server, dataid, start, stop)

    assert len(df2) > 1
    assert meta["status"]["message"] == "OK"
