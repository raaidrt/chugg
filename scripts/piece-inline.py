#!/usr/bin/env python3
"""Regenerate the inlined Maestro piece markup from the pinned upstream SVG files.

Downloads the twelve piece SVGs from the pinned Lichess commit, verifies each
SHA-256 digest against the original distribution, prefixes every internal SVG
id with the piece code so the markup stays valid when embedded many times in
one document, and writes src/chugg/data/pieces.json.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMIT = "423f2aa1e92cf10b3344aeab0b4755dbe5a435d4"
SOURCE = f"https://raw.githubusercontent.com/lichess-org/lila/{COMMIT}/public/piece/maestro"
DIGESTS = {
    "bB": "bf12b64284bef27ce1d33e40230e4b568e1697f4b3ca48cf12a36a31ba67af8d",
    "bK": "978b8af181130b2a83178822ee3d8d71a1c5dff32f8e26740eb8cb76f44da36e",
    "bN": "7cd77e4db972390ec0009a6399b5434d65a3ad5c71f83918b2281367bad65b7f",
    "bP": "437072d99abcef4108ad9f7b95d3c0f7278515d21d058ccc79db86913718b759",
    "bQ": "e96a48ba19ddd63776f26ce3b678233080a3f6d1eb1c2545282e2d22c67b8045",
    "bR": "89ef27465e24d158580209879f4fce69697f0b9867ba361a63c7f6a34b985ea9",
    "wB": "9bdd9174c076ead85fc0a2ffdbad5d0cc4a50bf6986b0a18ecf004bf67a9e54f",
    "wK": "dfa6be81e7009ca941100bf02b748178046a183d2b10ad9cd045718c0715e4be",
    "wN": "bd7f1be185744ddb26a1c8cf391d83e509b23b808f016b70600e07e8f2800d2a",
    "wP": "5bedc78160724cc1b548807253bbf0837c73b36c91af018df258606a66d144b2",
    "wQ": "16a297d607a1febf77d8c34adcc552defe570ac1c5e09ca991705b8c969eb9fb",
    "wR": "a62b1dd1e960df3753c9f56165a92ae8cb2e194ec4368d8e32e550089841d413",
}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--directory", type=Path, required=True, help="Local directory for the downloaded SVG files"
)
args = parser.parse_args()
args.directory.mkdir(parents=True, exist_ok=True)


def namespaced(code: str, markup: str) -> str:
    markup = re.sub(r'\bid="(\w+)"', rf'id="{code}-\1"', markup)
    markup = re.sub(r"url\(#(\w+)\)", rf"url(#{code}-\1)", markup)
    markup = re.sub(r'href="#(\w+)"', rf'href="#{code}-\1"', markup)
    return markup.replace("<svg ", '<svg class="piece" aria-hidden="true" ', 1)


pieces: dict[str, str] = {}
for code, expected in DIGESTS.items():
    target = args.directory / f"{code}.svg"
    if not target.exists():
        data = subprocess.check_output(
            ["curl", "--fail", "--location", "--silent", "--show-error", f"{SOURCE}/{code}.svg"]
        )
        target.write_bytes(data)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if digest != expected:
        raise SystemExit(f"{code}.svg digest {digest} does not match the pinned original.")
    markup = namespaced(code, target.read_text().strip())
    for reference in re.findall(r"url\(#(\w+)\)|href=\"#(\w+)\"", markup):
        name = reference[0] or reference[1]
        if f'id="{name}"' not in markup:
            raise SystemExit(f"{code}.svg references #{name} but defines no such id.")
    pieces[code] = markup
(ROOT / "src/chugg/data/pieces.json").write_text(
    json.dumps(pieces, indent=2, sort_keys=True) + "\n"
)
print(f"Wrote {len(pieces)} verified pieces to src/chugg/data/pieces.json.")
