import pytest
import sys

import cloudcatalog

try:
    dataset = sys.argv[1]
except:
    dataset = "MMS1_ASPOC_SRVY_L2"

# import cc as cloudcatalog
fr = cloudcatalog.CloudCatalog("s3://gov-nasa-hdrl-data1", cache=False)
# dataset = "MMS1_MEC_SRVY_L2_EPHT89D"
start, stop = "2020-02-01T00:00:00Z", "2020-02-02T00:00:00Z"
filekeys_mms = fr.request_cloud_catalog(dataset, start_date=start, stop_date=stop)
print(dataset,filekeys_mms)


# import pip
# pip.main(['install','smart_open[s3]'])
