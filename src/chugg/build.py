"""Reproducible static distribution with a checksum-pinned, locally served CPython runtime."""

import hashlib
import json
import os
import shutil
import urllib.request
from pathlib import Path
from typing import TypedDict, cast
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import chess

PACKAGE = Path(__file__).parent
ROOT = PACKAGE.parents[1]


class Runtime(TypedDict):
    version: str
    files: dict[str, str]


def base_path(value: str) -> str:
    if (
        not value.startswith("/")
        or any(char in value for char in ("?", "#", "\\"))
        or ".." in value.split("/")
    ):
        raise ValueError("BASE_PATH must be an absolute URL path, such as / or /chugg/.")
    return value.rstrip("/") + "/"


def runtime_files(cache: Path) -> Path:
    manifest = cast(Runtime, json.loads((PACKAGE / "data/runtime.json").read_text()))
    cache.mkdir(parents=True, exist_ok=True)
    for name, expected in manifest["files"].items():
        target = cache / name
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            url = f"https://cdn.jsdelivr.net/pyodide/v{manifest['version']}/full/{name}"
            with urllib.request.urlopen(url, timeout=120) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f"Runtime checksum mismatch: {name}")
            target.write_bytes(data)
    return cache


def archive(destination: Path) -> None:
    with ZipFile(destination, "w", ZIP_DEFLATED, compresslevel=9) as bundle:
        for directory, prefix in [(PACKAGE, "chugg"), (Path(chess.__file__).parent, "chess")]:
            for source in sorted(directory.rglob("*")):
                if (
                    source.is_file()
                    and source.suffix in (".py", ".json")
                    and "__pycache__" not in source.parts
                ):
                    info = ZipInfo(
                        f"{prefix}/{source.relative_to(directory).as_posix()}",
                        (2026, 1, 1, 0, 0, 0),
                    )
                    info.compress_type = ZIP_DEFLATED
                    info.external_attr = 0o644 << 16
                    bundle.writestr(info, source.read_bytes())


def build(*, base: str = "/", output: Path | None = None) -> Path:
    base = base_path(base)
    output = output or ROOT / "dist"
    runtime = runtime_files(ROOT / ".cache/pyodide")
    # Replace generated output only after dependencies have been verified.
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(ROOT / "public", output)
    shutil.copytree(runtime, output / "runtime")
    for source in (PACKAGE / "web").iterdir():
        if source.is_file():
            shutil.copy2(source, output / source.name)
    archive(output / "app.zip")
    html = (ROOT / "index.html").read_text().replace("%BASE_URL%", base)
    (output / "index.html").write_text(html)
    manifest = {
        "id": base,
        "name": "Chugg — Chess Opening Trainer",
        "short_name": "Chugg",
        "description": "Practice chess openings, one line at a time.",
        "start_url": base,
        "scope": base,
        "display": "standalone",
        "background_color": "#faf8f2",
        "theme_color": "#244a36",
        "lang": "en",
        "icons": [
            {
                "src": "icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "icons/icon-maskable-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }
    (output / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2) + "\n")
    files = sorted(
        path
        for path in output.rglob("*")
        if path.is_file() and path.name not in ("_headers", "sw.js")
    )
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(output).as_posix().encode())
        digest.update(path.read_bytes())
    version = digest.hexdigest()[:16]
    prefix = "chugg-python-" + hashlib.sha256(base.encode()).hexdigest()[:8] + "-"
    urls = [base + path.relative_to(output).as_posix() for path in files]
    worker = (
        (PACKAGE / "web/sw.js")
        .read_text()
        .replace("__CACHE__", json.dumps(prefix + version))
        .replace("__PREFIX__", json.dumps(prefix))
        .replace("__ASSETS__", json.dumps(urls))
        .replace("__BASE__", json.dumps(base))
    )
    (output / "sw.js").write_text(worker)
    print(
        f"Built {output} for {base} ({sum(path.stat().st_size for path in files) / 1024 / 1024:.1f} MiB, locally bundled Python 3.14)."
    )
    return output


def configured_base() -> str:
    return base_path(os.environ.get("BASE_PATH") or "/")
