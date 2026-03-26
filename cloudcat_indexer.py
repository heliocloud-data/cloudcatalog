#!/usr/bin/env python3
"""
Generate per-id HTML index pages from catalog.json.

Each page includes:
- A list of yearly files with fully formed HTTPS + S3 links
- A verbatim Python code template block for fetching/streaming the dataset,
  with dataset_id/start/stop/base_s3 substituted from JSON.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Allowed formats:
#   YYYY-MM-DDTHHZ
#   YYYY-MM-DDTHH:MMZ
#   YYYY-MM-DDTHH:MM:SSZ
#   YYYY-MM-DDTHH:MM:SS.SSSZ
VALID_TS_RE = re.compile(
    r"""
    ^
    (?P<Y>\d{4})-
    (?P<M>\d{2})-
    (?P<D>\d{2})
    T
    (?P<H>\d{2})
    (?:
        :
        (?P<m>\d{2})
        (?:
            :
            (?P<s>\d{2})
            (?:\.(?P<frac>\d+))?
        )?
    )?
    Z
    $
    """,
    re.VERBOSE,
)


def validate_and_fix_timestamp(ts: str, *, field_name: str, dataset_id: str) -> str:
    """
    Check if ts matches required formats.
    If not, warn and attempt a safe, minimal normalization.

    Returns a valid timestamp string.
    """

    if VALID_TS_RE.match(ts):
        return ts  # Already OK

    # ---------- warn ----------
    print(
        f"WARNING: {field_name} for dataset {dataset_id!r} is not in valid format: {ts!r}",
        file=sys.stderr,
    )

    # ---------- attempt minimal salvage ----------
    # Extract digits for YYYYMMDDHH
    nums = re.findall(r"\d+", ts)
    combined = "".join(nums)

    if len(combined) < 10:
        # hopeless case
        print(
            f"WARNING: {field_name} for dataset {dataset_id!r} cannot be salvaged. (is {ts!r})"
            f"Leaving unchanged.",
            file=sys.stderr,
        )
        return ts

    # Example: YYYYMMDDHH...
    Y = combined[0:4]
    M = combined[4:6]
    D = combined[6:8]
    H = combined[8:10]

    # Construct a safe canonical timestamp
    repaired = f"{Y}-{M}-{D}T{H}:00:00Z"

    print(
        f"WARNING: Rewriting {field_name} from {ts!r} for dataset {dataset_id!r} "
        f"to canonical form {repaired}",
        file=sys.stderr,
    )

    return repaired


def extract_year(iso8601: str) -> int:
    if not isinstance(iso8601, str) or len(iso8601) < 4:
        raise ValueError(f"Invalid ISO timestamp: {iso8601!r}")
    return int(iso8601[:4])


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def parse_s3_prefix(s3_prefix: str) -> tuple[str, str]:
    """
    Parse s3://bucket/prefix/ -> (bucket, key_prefix_with_trailing_slash_or_empty)
    """
    if not isinstance(s3_prefix, str) or not s3_prefix.startswith("s3://"):
        raise ValueError(f"Not an s3:// prefix: {s3_prefix!r}")

    rest = s3_prefix[len("s3://") :]  # bucket/prefix...
    parts = rest.split("/", 1)
    bucket = parts[0].strip()
    key_prefix = parts[1] if len(parts) == 2 else ""

    key_prefix = key_prefix.lstrip("/")
    if key_prefix and not key_prefix.endswith("/"):
        key_prefix += "/"

    if not bucket:
        raise ValueError(f"Missing bucket in prefix: {s3_prefix!r}")

    return bucket, key_prefix


def s3_object_url(bucket: str, key: str) -> str:
    # Virtual-hosted–style. Change hostname here if you need a regional/GovCloud endpoint.
    return f"https://{bucket}.s3.amazonaws.com/{key.lstrip('/')}"


def s3_uri(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key.lstrip('/')}"


def base_s3_from_index_prefix(index_prefix: str) -> str:
    """
    Derive s3://bucket/ from an index prefix s3://bucket/some/prefix/
    """
    bucket, _ = parse_s3_prefix(index_prefix)
    return f"s3://{bucket}/"


def load_catalog(path: str | os.PathLike[str]) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        return raw

    if isinstance(raw, dict):
        for v in raw.values():
            if isinstance(v, list):
                return v

    raise ValueError("catalog.json does not contain a list of entries")

def render_fetch_template(
    *, dataset_id: str, start: str, stop: str, base_s3: str
) -> str:
    """
    Keep the user's template verbatim except for the substituted values.
    """
    return (
        "import cloudcatalog" + "\n"
        "dataset_id = "
        + repr(dataset_id)
        + "\n"
        + "start = "
        + repr(start)
        + "\n"
        + "stop =   "
        + repr(stop)
        + "\n"
        + "fr=cloudcatalog.CloudCatalog("
        + repr(base_s3)
        + ")"
        + "\n"
        + "filelist = fr.request_cloud_catalog(dataset_id, start_date=start, stop_date=stop)"
        + "\n\n#example usage:\n"
        + "fr.stream_uri(filelist, lambda s3_uri, start, stop, filesize: MYCODE(s3_uri, start, stop, filesize))"
    )

def fetch_code(entry):
    # wrapper for render_fetch_template
    base_s3 = base_s3_from_index_prefix(entry["index"])
    codelet = render_fetch_template(
        dataset_id=entry["id"],
        start=entry["start"],
        stop=entry["stop"],
        base_s3=base_s3)
    return codelet

def render_index_html(entry: dict, *, ext: str = "csv") -> str:
    id_ = str(entry["id"])
    title = str(entry.get("title", id_))
    index_prefix = str(entry["index"])
    start = str(entry["start"])
    stop = str(entry["stop"])

    start = validate_and_fix_timestamp(start, field_name="start", dataset_id=id_)
    stop = validate_and_fix_timestamp(stop, field_name="stop", dataset_id=id_)

    start_year = extract_year(start)
    stop_year = extract_year(stop)

    bucket, key_prefix = parse_s3_prefix(index_prefix)
    base_s3 = base_s3_from_index_prefix(index_prefix)

    codelet = fetch_code(entry)

    lines = [
        "<!doctype html>",
        '<html lang="en">',
        "  <head>",
        '    <meta charset="utf-8" />',
        '    <meta name="viewport" content="width=device-width, initial-scale=1" />',
        f"    <title>{html_escape(title)} index</title>",
        "    <style>",
        "      body { font-family: system-ui, sans-serif; margin: 2rem; }",
        "      code { background: #f3f3f3; padding: 0.2rem 0.4rem; border-radius: 0.25rem; }",
        "      pre { background: #f8f8f8; padding: 1rem; border-radius: 0.75rem; overflow-x: auto; }",
        "      ul { line-height: 1.7; }",
        "      li { margin: 0.25rem 0; }",
        "      .meta { color: #444; margin-bottom: 1rem; }",
        "      .links a { margin-right: 0.75rem; }",
        "    </style>",
        "  </head>",
        "  <body>",
        f"    <h1>{html_escape(title)}</h1>",
        '    <div class="meta">',
        f"      <div><strong>id:</strong> <code>{html_escape(id_)}</code></div>",
        f"      <div><strong>index prefix:</strong> <code>{html_escape(index_prefix)}</code></div>",
        f"      <div><strong>start:</strong> <code>{html_escape(start)}</code></div>",
        f"      <div><strong>stop:</strong> <code>{html_escape(stop)}</code></div>",
        f"      <div><strong>year range:</strong> {start_year}–{stop_year}</div>",
        "    </div>",
        "    <h2>Fetch the full dataset (template)</h2>",
        "    <pre><code>",
        html_escape(codelet),
        "    </code></pre>",
        "    <h2>Yearly index files</h2>",
        "    <ul>",
    ]

    for y in range(start_year, stop_year + 1):
        fname = f"{id_}_{y}.{ext}"
        key = f"{key_prefix}{fname}"

        https = s3_object_url(bucket, key)
        s3 = s3_uri(bucket, key)

        lines.append("      <li>")
        lines.append(f"        <code>{html_escape(fname)}</code> &nbsp;")
        lines.append('        <span class="links">')
        lines.append(f'          <a href="{html_escape(https)}">https</a>')
        lines.append(f'          <a href="{html_escape(s3)}">s3</a>')
        lines.append("        </span>")
        lines.append("      </li>")

    lines.extend(
        [
            "    </ul>",
            "  </body>",
            "</html>",
            "",
        ]
    )

    return "\n".join(lines)


def write_indexes(
    catalog_path: str | os.PathLike[str],
    out_dir: str | os.PathLike[str],
    *,
    ext: str = "csv",
) -> None:
    if out_dir == None:
        out_dir = ""

    entries = load_catalog(catalog_path)

    count = 0
    for e in entries:
        if not isinstance(e, dict):
            continue
        if not all(k in e for k in ("id", "index", "start", "stop")):
            continue

        html = render_index_html(e, ext=ext)
        key_prefix = re.sub("s3://", "", str(e["index"]))
        out = out_dir + key_prefix
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        out.joinpath(f"{e['id']}_index.html").write_text(html, encoding="utf-8")
        count += 1

    print(f"Wrote {count} index pages to {out_dir}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Generate per-id HTML index pages from catalog.json"
    )
    ap.add_argument("catalog", help="Path to catalog.json")
    ap.add_argument(
        "--out", default="indexes/", help="Output directory (default: indexes/)"
    )
    ap.add_argument("--ext", default="csv", help="Index file extension (default: csv)")
    args = ap.parse_args()

    write_indexes(args.catalog, args.out, ext=args.ext)
