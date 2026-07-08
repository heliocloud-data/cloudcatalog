import cloudcatalog

"""
Just a stub for now
"""


def CloudCatalogToHAPIConverter(df):
    return df


def test_real_cloudcatalog_to_hapi():
    mmsid = "MMS1_FEEPS_BRST_L2_ELECTRON"
    mmsstart = "2020-02-01T00:00:00Z"
    mmsstop = "2020-02-02T00:00:00Z"

    fr = cloudcatalog.CloudCatalog("s3://gov-nasa-hdrl-data1/", cache=False)

    df = fr.request_cloud_catalog(mmsid, start_date=mmsstart, stop_date=mmsstop)

    assert len(df) > 0

    converter = CloudCatalogToHAPIConverter(df)
    """

    # ---- JSON ----
    hapi_json = converter.to_json()

    assert "filelist" in hapi_json
    assert len(hapi_json["filelist"]) == len(df)

    first = hapi_json["filelist"][0]

    assert "url" in first
    assert "start" in first
    assert "stop" in first

    # Ensure mapping correctness
    assert first["start"] == df.iloc[0]["Starttime"]
    assert first["stop"] == df.iloc[0]["Endtime"]

    # ---- CSV ----
    csv_output = converter.to_csv()
    lines = csv_output.splitlines()

    assert len(lines) > 1

    header = lines[0].split(",")

    # HAPI requirement: Time first, key second
    assert header[0] == "Time"
    assert header[1] == "key"

    first_row = lines[1].split(",")

    assert first_row[0] == df.iloc[0]["Starttime"]
    assert first_row[1] == df.iloc[0]["key"]
    """
