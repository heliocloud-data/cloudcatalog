"""Unit tests for fetch_S3orURL().

These tests exercise each branch of the fetch cascade without contacting AWS
or the network. The local-file test creates its own JSON fixture via pytest's
built-in tmp_path fixture.

Run from the repository root, assuming the source module is importable as
``main`` (for example, when src/ is on PYTHONPATH):

    pytest -q test_fetch_s3orurl.py
"""

import json

import cloudcatalog.main as cc

S3_URL = "s3://test-bucket/test/catalog.json"
EXPECTED = {"status": {"code": 0}, "catalog": [{"id": "TEST"}]}
REGION = "us-west-2"


def _successful_s3_response(catalog=EXPECTED):
    """Return the (status, catalog) tuple expected from fetch_S3()."""
    return 200, catalog


def _failed_s3_response():
    """Return the unavailable result expected from fetch_S3()."""
    return None, None


def test_fetch_s3orurl_s3_unsigned(monkeypatch):
    """Case 1: the first S3 attempt succeeds with unsigned=True."""
    calls = []

    def fake_fetch_s3(s3url, *, unsigned=True, **kwargs):
        calls.append((s3url, unsigned, kwargs))
        return _successful_s3_response()

    monkeypatch.setattr(cc, "fetch_S3", fake_fetch_s3)

    def fail_url(*args, **kwargs):
        raise AssertionError("fetch_url() should not be reached")

    monkeypatch.setattr(cc, "fetch_url", fail_url)

    result = cc.fetch_S3orURL(S3_URL)

    assert result == EXPECTED
    assert calls == [(S3_URL, True, {"rawbytes": False, "max_lines": None})]


def test_fetch_s3orurl_s3_signed(monkeypatch):
    """Case 2: unsigned S3 fails, then signed S3 (unsigned=False) succeeds."""
    calls = []

    def fake_fetch_s3(s3url, *, unsigned=True, **kwargs):
        calls.append((s3url, unsigned, kwargs))
        if unsigned:
            return _failed_s3_response()
        return _successful_s3_response()

    monkeypatch.setattr(cc, "fetch_S3", fake_fetch_s3)

    def fail_url(*args, **kwargs):
        raise AssertionError("fetch_url() should not be reached")

    monkeypatch.setattr(cc, "fetch_url", fail_url)

    result = cc.fetch_S3orURL(S3_URL)

    assert result == EXPECTED
    assert calls == [
        (S3_URL, True, {"rawbytes": False, "max_lines": None}),
        (S3_URL, False, {"rawbytes": False, "max_lines": None}),
    ]


def test_fetch_s3orurl_s3_unsigned_with_region(monkeypatch):
    """Case 3: first two S3 attempts fail, then unsigned=True with region succeeds."""
    calls = []

    def fake_fetch_s3(s3url, *, unsigned=True, region=None, **kwargs):
        calls.append((s3url, unsigned, region, kwargs))
        if unsigned and region == REGION:
            return _successful_s3_response()
        return _failed_s3_response()

    monkeypatch.setattr(cc, "fetch_S3", fake_fetch_s3)

    def fail_url(*args, **kwargs):
        raise AssertionError("fetch_url() should not be reached")

    monkeypatch.setattr(cc, "fetch_url", fail_url)

    result = cc.fetch_S3orURL(S3_URL, region=REGION)

    assert result == EXPECTED
    assert calls == [
        (S3_URL, True, None, {"rawbytes": False, "max_lines": None}),
        (S3_URL, False, None, {"rawbytes": False, "max_lines": None}),
        (S3_URL, True, REGION, {"rawbytes": False, "max_lines": None}),
    ]


def test_fetch_s3orurl_via_fetch_url(monkeypatch):
    """Case 4: all S3 attempts fail, then fetch_url() succeeds."""
    s3_calls = []
    url_calls = []

    def fake_fetch_s3(s3url, **kwargs):
        s3_calls.append((s3url, kwargs))
        return _failed_s3_response()

    def fake_fetch_url(s3url, rawbytes=False):
        url_calls.append((s3url, rawbytes))
        return 200, EXPECTED

    monkeypatch.setattr(cc, "fetch_S3", fake_fetch_s3)
    monkeypatch.setattr(cc, "fetch_url", fake_fetch_url)

    result = cc.fetch_S3orURL(S3_URL)

    assert result == EXPECTED
    assert len(s3_calls) == 3
    assert url_calls == [(S3_URL, False)]


def test_fetch_s3orurl_via_local_json_load(monkeypatch, tmp_path):
    """Case 5: S3 and URL fail, then a locally-created JSON file is loaded."""
    local_file = tmp_path / "catalog.json"
    local_file.write_text(json.dumps(EXPECTED), encoding="utf-8")

    def fake_fetch_s3(*args, **kwargs):
        return _failed_s3_response()

    def fake_fetch_url(*args, **kwargs):
        return None, None

    # Spy on json.load while still using the real implementation.
    real_json_load = json.load
    load_calls = []

    def spy_json_load(fp, *args, **kwargs):
        load_calls.append(fp.name)
        return real_json_load(fp, *args, **kwargs)

    monkeypatch.setattr(cc, "fetch_S3", fake_fetch_s3)
    monkeypatch.setattr(cc, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(cc.json, "load", spy_json_load)

    result = cc.fetch_S3orURL(str(local_file))

    assert result == EXPECTED
    assert load_calls == [str(local_file)]
