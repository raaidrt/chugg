"""Serve real IndexedDB contracts on a dedicated, disposable browser test origin."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from chugg.build import ROOT, build
from chugg.cli import serve

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--port", type=int, default=4182)
args = parser.parse_args()
with TemporaryDirectory(prefix="chugg-browser-tests-") as directory:
    output = build(output=Path(directory))
    (output / "app.html").write_bytes((output / "index.html").read_bytes())
    bootstrap = output / "bootstrap.js"
    bootstrap.write_text(bootstrap.read_text().replace("await registerOffline();", ""))
    (output / "mobile.html").write_bytes((ROOT / "tests/mobile-preview.html").read_bytes())
    (output / "index.html").write_bytes((ROOT / "tests/browser-contract.html").read_bytes())
    (output / "browser-contract.js").write_bytes((ROOT / "tests/browser-contract.js").read_bytes())
    with ZipFile(output / "app.zip", "a") as archive:
        archive.write(ROOT / "tests/browser_contract.py", "browser_contract.py")
        archive.write(ROOT / "tests/fixtures/legacy-backup.json", "legacy-backup.json")
    serve(output, "/", "127.0.0.1", args.port)
