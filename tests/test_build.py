import hashlib
import json
from pathlib import Path
from typing import cast
from zipfile import ZipFile

import pytest

from chugg.build import ROOT, Runtime, base_path, build


@pytest.mark.parametrize("base", ["/", "/chugg/"])
def test_static_distribution_is_complete_and_scoped(tmp_path: Path, base: str) -> None:
    output = build(base=base, output=tmp_path / "dist")
    manifest = cast(dict[str, object], json.loads((output / "manifest.webmanifest").read_text()))
    assert manifest["id"] == manifest["scope"] == manifest["start_url"] == base
    html = (output / "index.html").read_text()
    assert f'src="{base}bootstrap.js"' in html
    assert "%BASE_URL%" not in html
    worker = (output / "sw.js").read_text()
    assert "__CACHE__" not in worker and "__PREFIX__" not in worker
    for filename in [
        "runtime/pyodide.asm.wasm",
        "runtime/python_stdlib.zip",
        "app.zip",
        "piece/maestro/wN.svg",
        "credits.html",
        "manifest.webmanifest",
    ]:
        assert (output / filename).is_file()
        assert base + filename in worker
    with ZipFile(output / "app.zip") as archive:
        assert "chugg/app.py" in archive.namelist()
        assert "chess/__init__.py" in archive.namelist()
        assert "chugg/data/catalog.json" in archive.namelist()
        assert "browser_contract.py" not in archive.namelist()
    pinned = cast(Runtime, json.loads((ROOT / "src/chugg/data/runtime.json").read_text()))
    for name, digest in pinned["files"].items():
        assert hashlib.sha256((output / "runtime" / name).read_bytes()).hexdigest() == digest
    # Rebuilding identical sources produces identical archive bytes and worker cache identity.
    before = (output / "app.zip").read_bytes(), worker
    build(base=base, output=output)
    assert before == ((output / "app.zip").read_bytes(), (output / "sw.js").read_text())


@pytest.mark.parametrize(
    "value", ["relative", "/../bad/", "/path?query", "/path#hash", "/path\\bad"]
)
def test_invalid_base_paths(value: str) -> None:
    with pytest.raises(ValueError):
        base_path(value)
