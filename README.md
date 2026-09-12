# Chugg

A client-only chess opening trainer written in **Python 3.14**, managed with **uv**, and checked with **basedpyright**. See the exact variation, play one side from memory, and let Chugg play the other.

**[Open Chugg](https://raaidrt.com/chugg/)** — hosted on GitHub Pages at the existing origin. Deployment is manual; a local commit does not update the hosted app.

## Run locally

Install [uv](https://docs.astral.sh/uv/), then:

```sh
uv sync --locked
uv run chugg dev
# http://localhost:5173/
```

uv provisions Python 3.14 when needed. No npm installation, Node project, backend, account, or database server is required. basedpyright manages its own JavaScript runtime as a uv dependency.

```sh
uv run basedpyright
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run chugg build
uv run chugg preview
# http://localhost:4173/
```

`dev` builds and serves a development snapshot without registering a service worker; rerun it after source edits. Use a fresh port if another installed development build already controls that origin. Use `build` followed by `preview` to test offline behavior. The first build downloads the pinned Pyodide runtime, checks every SHA-256 digest, and caches it in `.cache/pyodide/`. Later builds can run offline.

## Runtime and code organization

[Pyodide 314.0.6](https://pyodide.org/en/stable/usage/downloading-and-deploying.html) runs CPython 3.14 directly in the browser. The static distribution bundles the interpreter, standard library, application source, python-chess, catalog, icons, and original CSS. All practice and progress processing happens on the device. There are no runtime third-party requests.

- `src/chugg/models.py`: typed domain and version 1 backup schemas.
- `trainer.py`, `sampling.py`, `progress.py`: chess/drill state, weighted selection, and backup validation/merging; independent of browser APIs.
- `app.py`, `views.py`, `dialogs.py`: Python controller and HTML presentation using the existing design and copy.
- `browser.py`, `storage.py`: typed browser boundary and atomic IndexedDB repository.
- `web/host.js`: browser primitives for DOM events, transactions, downloads, and service-worker registration. `web/bootstrap.js` loads Python; `web/sw.js` implements the browser-required service worker. These small platform adapters contain no chess, sampling, backup-validation, or UI-rendering rules.
- `build.py`, `cli.py`, `catalog_build.py`, `classifier.py`, `icons.py`: Python build, preview, and asset tools.

The service worker precaches the entire distribution, including Python and its source archive. Initial assets total approximately **13.2 MiB before HTTP compression**, larger than the former JavaScript app. Subsequent cached loads and drills work without a network. Installation alone does not confirm that caching finished.

## What is included

- The same 45 exact named opening lines across 13 families, with stable IDs and curated Lichess CC0 names/move orders.
- Popularity-weighted family-then-variation selection, exponent 0.7, 5% exploration, and recent-line cooldown.
- TWIC tournament issues 1600–1603 reference counts; tournament-sample frequencies, not online rapid population estimates.
- Random White/Black assignment for each new drill, one-second name reveal, legal moves, 650 ms opponent replies, hints, move history, replay with the same side, and library browsing.
- Device-only per-side progress, version 1 JSON export/import, persistent-storage requests, and Safari/Android installation guidance.
- Original Maestro pieces, interface icons, colors, responsive styling, dialogs, and install icons.

The IndexedDB database remains `chugg`, version 1, with the same compound keys. Existing progress and old backups remain compatible at the same origin. Import uses snapshot maxima and never double-counts repeated imports. Updates wait for **Update Chugg** outside a drill. See [storage details](docs/STORAGE.md).

## Verification

`uv run pytest` includes golden fixtures captured from the former TypeScript app: every FEN, legal move set, and SAN recap across all 45 lines, 500 deterministic selections, and an original exported backup. It also exercises both sides, special chess moves, malformed backups, classifier behavior, and build contracts.

For real IndexedDB transaction checks, run:

```sh
uv run scripts/browser-tests.py
# Open http://127.0.0.1:4182/
```

This dedicated test origin is disposable: the harness resets its `chugg` database. It verifies concurrent writes, original backups, idempotent merging, atomic rollback, and unavailable storage. Keep it separate from a personal practice origin. See [verification results](docs/VERIFICATION.md).

## Deploy to GitHub Pages

The check workflow runs Python typing, linting, tests, and static builds on pushes and pull requests. The manually triggered Pages workflow builds and uploads `dist/`.

1. Under **Settings → Pages → Build and deployment**, choose **GitHub Actions**.
2. Under **Actions → Deploy to GitHub Pages**, select **Run workflow** on the desired branch.
3. The action obtains the Pages base path and publishes the resulting static files.

Test a subpath locally:

```sh
BASE_PATH=/chugg/ uv run chugg build
BASE_PATH=/chugg/ uv run chugg preview
# http://localhost:4173/chugg/
```

Keep the production origin stable to retain browser storage. For other static hosts, install uv, run `uv sync --locked && uv run chugg build`, and publish `dist/`. Leave `BASE_PATH` unset for a domain root. No server-side Python runtime is required. `public/_headers` supplies Cloudflare cache headers; GitHub Pages ignores it.

## Catalog and assets

```sh
uv run chugg catalog-build
uv run chugg icons-build
uv run ruff format .
```

Catalog regeneration uses pinned checked-in inputs and makes no network requests. See [catalog sources and regeneration](docs/CATALOG.md). Icon regeneration uses resvg-py and Pillow; normal builds use the checked-in icons.

Maestro is by **sadsnake1**, under **CC BY-NC-SA 4.0**, included unmodified. The migration uses python-chess under **GPL-3.0-or-later**; Pyodide, CPython, and Lucide notices and license texts are also bundled. See [third-party notices](THIRD_PARTY_NOTICES.md) and the in-app Credits page.
