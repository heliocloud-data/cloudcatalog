# Contributing to HelioCloud and CloudCatalog

HelioCloud originated at NASA/GSFC from the Heliophysics Data Research Library, and is open source software accepting contributions from the community. To get an overview of the project, read both the [README](../README.md) file for this Python client and the actual definition of the [CloudCatalog specification](cloudcatalog-spec.md).

There is over a Petabyte of data already indexed and accessible via CloudCatalog.  It is very important that any suggested changes or enhancements to the specification be backwards compatible with all existing data holdings. In particular, feature enhancements must not break earlier indices, as scientists are using the cloudcatalog indices to do their existing research.  Likewise, any client modifications must remain backward capable (easily done as indices include the version number in their catalog JSON metadata.)

Currently contributions are best handled by creating an Issue and discussing the Issue.  If you wish to create additional software or CloudCatalog client capabilities, create an Issue, fork the repo, commit your changes, and tie it to the Issue in your Pull request.  The maintainers will use the Issues to discuss adoption.
