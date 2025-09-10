This includes a tool to convert a sorted S3 MANIFEST.csv into a set of per-dataid catalog indexes and main catalog.json index.

Currently works for CDAWeb, presumes the following:

An XML or CSV file containing dataid descriptions and regexes to extract dates from filenames.  Currently a CDAWeb example 'sample_data/smallall.xml' is provided.

An S3 CSV manifest, arbitrary fields so long as the last two files in a line are the full filename, then the filesize in bytes.  This file must be sorted in (a) dataid order and (b) time order for a given dataid.  In most cases this is just a straight alphabetic sort of the filename, as generally files are in some form of '*<dataid>*<year-leading date>*'.  Currently a CDAWeb example 'sample_data/smallsorted.csv' is provided.
