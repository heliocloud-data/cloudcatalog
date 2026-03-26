import pytest
import sys

import cloudcatalog


def test_minimms(dataset="MMS1_ASPOC_SRVY_L2", printme=False):

    # import cc as cloudcatalog
    fr = cloudcatalog.CloudCatalog("s3://gov-nasa-hdrl-data1", cache=False)
    # dataset = "MMS1_MEC_SRVY_L2_EPHT89D"
    start, stop = "2020-02-01T00:00:00Z", "2020-02-02T00:00:00Z"
    filekeys_mms = fr.request_cloud_catalog(dataset, start_date=start, stop_date=stop)
    if printme:
        print(dataset, filekeys_mms)
    assert len(dataset) == 18


if __name__ == "__main__":
    try:
        dataset = sys.argv[1]
    except:
        dataset = "MMS1_ASPOC_SRVY_L2"
    test_minimms(dataset, printme=True)

# import pip
# pip.main(['install','smart_open[s3]'])
