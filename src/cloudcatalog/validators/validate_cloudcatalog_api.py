#!/usr/bin/env python3
"""Validate Heliocloud cloudcatalog data IDs.

Usage:
  python validate_cloudcatalog_api.py dataids.txt  (dataids, 1 per line)
  python validate_cloudcatalog_api.py all.xml   (cdaweb-formated xml)
  python validate_cloudcatalog_api.py dataids.txt --workers 64 --failed-out failed_ids.txt


Given a list of dataids from an XML file or TXT file, Python validation script
that checks that each ID returns a valid page from
https://api.heliocloud.org/cloudcatalog?id=[ID]

An invalid response is either (a) a zero-sized response or (b) a
response that starts with:
<html> <head><title>404 Not Found</title></head> <body> <h1>404 Not Found</h1>

While a valid response is an HTML page that starts with (ignoring the
text in [ignore] and looking for the field [dataid] to ensure it
matches the provided ID):

<!doctype html> <html lang="en"> <head> <meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>[ignore]</title>
<style>[ignore style]</style>
</head>
<body>
<h1>[ignore]</h1>
<div class="meta"> <div><strong>id:</strong> <code>[dataid]</code></div>
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from urllib.parse import quote

import aiohttp

BASE_URL = "https://api.heliocloud.org/cloudcatalog?id="

NOT_FOUND_PREFIX = """<html>
<head><title>404 Not Found</title></head>
<body>
<h1>404 Not Found</h1>"""

VALID_PREFIX = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />"""


def load_ids(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def is_valid_response(dataid: str, text: str) -> bool:
    if not text:
        return False

    stripped = text.lstrip()

    if stripped.startswith(NOT_FOUND_PREFIX):
        return False

    if not stripped.startswith(VALID_PREFIX):
        return False

    expected_id_line = f"<div><strong>id:</strong> <code>{dataid}</code></div>"
    return expected_id_line in stripped


async def fetch_one(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    dataid: str,
    retries: int,
) -> tuple[str, bool]:
    url = BASE_URL + quote(dataid, safe="")

    async with sem:
        for attempt in range(retries + 1):
            try:
                async with session.get(url) as resp:
                    text = await resp.text()
                    return dataid, is_valid_response(dataid, text)

            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt == retries:
                    return dataid, False
                await asyncio.sleep(0.25 * (attempt + 1))

    return dataid, False


async def validate_ids(
    dataids: list[str],
    workers: int,
    retries: int,
    timeout_seconds: float,
) -> tuple[list[str], list[str]]:
    sem = asyncio.Semaphore(workers)
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    passed: list[str] = []
    failed: list[str] = []

    total = len(dataids)
    next_progress = 5

    connector = aiohttp.TCPConnector(limit=workers, ttl_dns_cache=300)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        tasks = [
            asyncio.create_task(fetch_one(session, sem, dataid, retries))
            for dataid in dataids
        ]

        completed = 0

        for task in asyncio.as_completed(tasks):
            dataid, ok = await task
            completed += 1

            if ok:
                passed.append(dataid)
            else:
                failed.append(dataid)

            pct = int((completed / total) * 100)
            if pct >= next_progress:
                print(f"Progress: {completed}/{total} ({pct}%)")
                next_progress += 5

    return passed, failed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--failed-out", type=Path, default=Path("failed_ids.txt"))
    parser.add_argument("--workers", type=int, default=64)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    print(str(args.input_file))
    # if str(args.input_file).endswith(".xml"):
    #    dataids = cdawebxml2txt(args.input_file, writefile=False)
    # else:
    dataids = load_ids(args.input_file)

    if not dataids:
        print("Worked: 0")
        print("Failed: 0")
        args.failed_out.write_text("", encoding="utf-8")
        return 0

    passed, failed = asyncio.run(
        validate_ids(
            dataids=dataids,
            workers=args.workers,
            retries=args.retries,
            timeout_seconds=args.timeout,
        )
    )

    args.failed_out.write_text(
        "\n".join(failed) + ("\n" if failed else ""), encoding="utf-8"
    )

    print(f"Worked: {len(passed)}")
    print(f"Failed: {len(failed)}")
    print(f"Failed ID file: {args.failed_out}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
