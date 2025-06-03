## Developer's Guide

To build this, first install build tools (if not yet done), then build, then test the wheel.  Updated Sept 2024.

* python -m build

Test the wheel
* pip install cloudcatalog-*-py3-none-any.whl

Do a test package upload then install with:

* twine upload -r testpypi dist/*
* pip install --index-url https://test.pypi.org/simple/ cloudcatalog

Commit with

* twine upload dist/*
