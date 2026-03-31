#!/usr/bin/env python3
"""
CloudCatalog web service

Behavior:
- Default: return an HTML landing page
- If ?id=<DATAID> is provided:
    - ?format=html   -> HTML rendering of metadata
    - ?format=json   -> JSON rendering of metadata
    - format omitted -> HTML rendering of metadata
- Optional ?source=<bucket> defaults to gov-nasa-hdrl-data1

Example:
https://heliocloud.org/cloudcatalog?id=[DATAID]&format=json&source=[S3 bucket]
"""

from __future__ import annotations

import html
import json
import os
import re
from typing import Any, Tuple

from flask import Flask, Response, jsonify, make_response, request

import cloudcatalog
from cloudcatalog.generators.cloudcat_indexer import render_index_html

DEFAULT_SOURCE = "gov-nasa-hdrl-data1"

# Conservative dataset-id validation. Adjust if your IDs require more characters.
DATAID_RE = re.compile(r"^[A-Za-z0-9._:/+=@-]{1,256}$")

# S3 bucket constraints from the design doc:
# - 3 to 63 chars
# - lowercase letters, numbers, periods, hyphens
# - begins/ends with letter or number
# - no adjacent periods
BUCKET_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{1,61})[a-z0-9]$")

app = Flask(__name__)


class QueryError(ValueError):
    """Raised when query parameters are invalid."""


def is_valid_bucket_name(bucket: str) -> bool:
    """Validate S3 bucket name using the rules in the design doc."""
    if not isinstance(bucket, str):
        return False
    if not (3 <= len(bucket) <= 63):
        return False
    if not BUCKET_RE.fullmatch(bucket):
        return False
    if ".." in bucket:
        return False
    return True


def is_valid_dataid(dataid: str) -> bool:
    """
    Conservative validation for incoming dataset IDs.

    The design doc does not define DATAID syntax, so this rejects obvious junk
    while allowing common catalog-style identifiers.
    """
    return bool(DATAID_RE.fullmatch(dataid))


def parse_query(req) -> Tuple[str | None, str, str]:
    """
    Get and sanitize URL args: 'id', 'format', 'source'.

    Rules:
    - id is optional overall because the default route is the landing page.
    - if format exists, it must be 'html' or 'json'
    - if source exists, it must be a viable S3 bucket name
    """
    raw_id = req.args.get("id", default=None, type=str)
    raw_format = req.args.get("format", default=None, type=str)
    raw_source = req.args.get("source", default=None, type=str)

    dataid = raw_id.strip() if raw_id is not None else None
    fmt = raw_format.strip().lower() if raw_format is not None else "html"
    source = raw_source.strip() if raw_source is not None else DEFAULT_SOURCE

    if raw_format is not None and fmt not in {"html", "json"}:
        raise QueryError("Invalid format. Allowed values are 'html' or 'json'.")

    if raw_source is not None and not is_valid_bucket_name(source):
        raise QueryError("Invalid source. Must be a valid S3 bucket name.")

    # If id is omitted or blank, treat as landing-page request.
    if dataid == "":
        dataid = None

    if dataid is not None and not is_valid_dataid(dataid):
        raise QueryError("Invalid id.")

    return dataid, fmt, source


def render_error_html(title: str, message: str, http_code: int) -> str:
    """Render a simple HTML error page."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      font-family: system-ui, sans-serif;
      max-width: 800px;
      margin: 3rem auto;
      padding: 0 1rem;
      line-height: 1.5;
      color: #222;
    }}
    .error {{
      border: 1px solid #ccc;
      border-radius: 8px;
      padding: 1rem 1.25rem;
      background: #fafafa;
    }}
    code {{
      background: #f0f0f0;
      padding: 0.1rem 0.3rem;
      border-radius: 4px;
    }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <div class="error">
    <p>{html.escape(message)}</p>
    <p>HTTP status: {http_code}</p>
  </div>
</body>
</html>
"""


def render_landing_page() -> str:
    """Render the default landing page."""
    example = "/cloudcatalog?id=DATASET123&format=json" f"&source={DEFAULT_SOURCE}"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CloudCatalog</title>
  <style>
    body {{
      font-family: system-ui, sans-serif;
      max-width: 900px;
      margin: 3rem auto;
      padding: 0 1rem;
      line-height: 1.55;
      color: #222;
    }}
    code {{
      background: #f4f4f4;
      padding: 0.12rem 0.3rem;
      border-radius: 4px;
    }}
    pre {{
      background: #f6f8fa;
      padding: 1rem;
      border-radius: 8px;
      overflow-x: auto;
    }}
  </style>
</head>
<body>
  <h1>CloudCatalog web service</h1>
  <p>A simple, secure Python web service for CloudCatalog metadata lookup.</p>

  <h2>Usage</h2>
  <pre>{html.escape(example)}</pre>

  <h2>Parameters</h2>
  <ul>
    <li><code>id</code>: dataset ID</li>
    <li><code>format</code>: <code>html</code> or <code>json</code>, defaults to <code>html</code></li>
    <li><code>source</code>: S3 bucket name, defaults to <code>{html.escape(DEFAULT_SOURCE)}</code></li>
  </ul>

  <h2>Notes</h2>
  <ul>
    <li>If <code>id</code> is omitted, this landing page is returned.</li>
    <li>If metadata is found and <code>format=html</code>, metadata is rendered as an HTML page.</li>
    <li>If metadata is found and <code>format=json</code>, metadata is returned as JSON.</li>
  </ul>
</body>
</html>
"""


def get_metadata(dataid: str, fmt: str, source: str) -> Tuple[int, Any]:
    """
    Given sanitized DataID, Format, and Source, return (status, metadata).

    Status meanings:
    -1 = unknown system error
     0 = DataID not found
     1 = valid HTML
     2 = valid JSON
    """
    try:
        fr = cloudcatalog.CloudCatalog(f"s3://{source}")
        try:
            metadata = fr.get_entry(dataid)
        except Exception as e:
            # older cloudcatalog throws errors instead of returning None
            return -1, e

        if metadata is None:
            return 0, None
        elif fmt == "html":
            return 1, render_index_html(metadata)
        elif fmt == "json":
            return 2, metadata
        else:
            return -1, None
    except Exception:
        return -2, None


@app.after_request
def add_security_headers(resp: Response) -> Response:
    """Add a few basic security headers."""
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )
    return resp


@app.route("/cloudcatalog", methods=["GET"])
def cloudcatalog_handler():
    """
    Main endpoint.

    Flow:
    - Parse and validate query parameters
    - No id -> landing page
    - With id -> get metadata
    - Return HTML, JSON, or an error page based on status code
    """
    try:
        dataid, fmt, source = parse_query(request)
    except QueryError as exc:
        return make_response(
            render_error_html("Bad Request", str(exc), 400),
            400,
            {"Content-Type": "text/html; charset=utf-8"},
        )

    if dataid is None:
        return make_response(
            render_landing_page(),
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )

    status, metadata = get_metadata(dataid, fmt, source)

    if status == -2:
        return make_response(
            render_error_html(
                "Internal Server Error",
                "An unknown system error occurred.",
                500,
            ),
            500,
            {"Content-Type": "text/html; charset=utf-8"},
        )

    if status == -1:
        return make_response(
            render_error_html(
                "Server Error",
                str(metadata),
                500,
            ),
            500,
            {"Content-Type": "text/html; charset=utf-8"},
        )

    if status == 0:
        return make_response(
            render_error_html(
                "Not Found",
                f"Dataset ID '{dataid}' was not found.",
                404,
            ),
            404,
            {"Content-Type": "text/html; charset=utf-8"},
        )

    if status == 1:
        return make_response(
            metadata,
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )

    if status == 2:
        return jsonify(metadata)

    return make_response(
        render_error_html(
            "Internal Server Error",
            "Unexpected response state.",
            500,
        ),
        500,
        {"Content-Type": "text/html; charset=utf-8"},
    )


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    debug = os.environ.get("DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)
