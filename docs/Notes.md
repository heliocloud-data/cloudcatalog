## Developer's Guide

To build this, first install build tools (if not yet done), then build, then test the wheel

* python -m build

Test the wheel
* pip install scregistry-*-py3-none-any.whl

Do a test package upload then install with:

* twine upload -repository testpypi dist/*
* pip install -i https://test.pypi.org/simple/scregistry==0.3

Commit with

* twine upload dist/*
