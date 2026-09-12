#!/usr/bin/env python3
"""Verify pinned catalog sources, optionally download and reproduce the bundled counts."""

import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = json.loads((ROOT / "scripts/catalog-sources.json").read_text())
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--directory", type=Path, required=True, help="Local directory for source TSV and PGN files"
)
parser.add_argument(
    "--download", action="store_true", help="Download public sources into the directory"
)
parser.add_argument(
    "--rebuild",
    action="store_true",
    help="Replace the catalog and counts with the original reference snapshot",
)
args = parser.parse_args()
args.directory.mkdir(parents=True, exist_ok=True)
for source in SOURCES["openingTables"] + SOURCES["gameArchives"]:
    target = args.directory / source["filename"]
    if args.download:
        data = subprocess.check_output(
            [
                "curl",
                "--fail",
                "--location",
                "--silent",
                "--show-error",
                "--max-time",
                "120",
                source["url"],
            ]
        )
        if source["url"].endswith(".zip"):
            # Read only the expected member: no archive path extraction.
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                data = archive.read(source["filename"])
        if hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise SystemExit(f"Source changed; refusing to overwrite {target}")
        target.write_bytes(data)
    if hashlib.sha256(target.read_bytes()).hexdigest() != source["sha256"]:
        raise SystemExit(f"Checksum mismatch: {target}")

upstream_rows: set[tuple[str, str, str]] = set()
for source in SOURCES["openingTables"]:
    with (args.directory / source["filename"]).open() as file:
        upstream_rows.update(
            (row["eco"], row["name"], row["pgn"]) for row in csv.DictReader(file, delimiter="\t")
        )
selection = json.loads((ROOT / "scripts/catalog-selection.json").read_text())
for row in selection:
    if (row["eco"], row["name"], row["pgn"]) not in upstream_rows:
        raise SystemExit(f"Selection does not match pinned upstream: {row['id']}")
print(f"Verified all nine source files and {len(selection)} selected opening rows.")
if args.rebuild:
    env = dict(
        os.environ,
        CATALOG_SOURCE=SOURCES["popularitySource"],
        CATALOG_DESCRIPTION=SOURCES["popularityDescription"],
        CATALOG_DATE=SOURCES["retrievedAt"],
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "chugg",
            "catalog-build",
            *[str(args.directory / source["filename"]) for source in SOURCES["gameArchives"]],
        ],
        env=env,
        check=True,
    )
