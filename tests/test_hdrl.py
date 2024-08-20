"""
Tests CloudCatalog against the ODR/TOPS bucket (gov-nasa-hdrl-data1).
Failure means either a bug in CloudCatalog, an error in the index files,
or access issues, any of which need to be investigated and fixed.

"""

import cloudcatalog
mmsid = 'mms1_feeps_brst_electron'
mmsstart = '2020-02-01T00:00:00Z'
mmsstop =   '2020-02-02T00:00:00Z'
aiaid = "aia_0094"
aiastart="2010-05-13T00:00:00Z"
aiastop="2010-06-30T23:56:00Z"
euvid = "euvml_stereoa_171"
euvstart="2018-05-13T00:00:00Z"
euvstop="2018-12-31T23:56:00Z"

fr=cloudcatalog.CloudCatalog("s3://gov-nasa-hdrl-data1/",cache=False)

filekeys_mms = fr.request_cloud_catalog(mmsid,start_date=mmsstart,stop_date=mmsstop)
#print(len(filekeys_mms))
assert len(filekeys_mms) == 15

filekeys_aia = fr.request_cloud_catalog(aiaid,start_date=aiastart,stop_date=aiastop)
#print(len(filekeys_aia))
assert len(filekeys_aia) == 16783

filekeys_euv = fr.request_cloud_catalog(euvid,start_date=euvstart,stop_date=euvstop)
#print(len(filekeys_euv))
assert len(filekeys_euv) == 780

mysearch = cloudcatalog.EntireCatalogSearch()
ss = mysearch.search_by_id('srvy_ion')
assert len(ss) == 8

