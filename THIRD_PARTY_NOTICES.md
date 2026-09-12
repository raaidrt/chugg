# Third-party materials

## Maestro chess pieces

Author: **sadsnake1**. Distributed by Lichess.

Source: https://github.com/lichess-org/lila/tree/423f2aa1e92cf10b3344aeab0b4755dbe5a435d4/public/piece/maestro

License: **CC BY-NC-SA 4.0** — https://creativecommons.org/licenses/by-nc-sa/4.0/

The SVG files are bundled without modification. Lichess identifies this license in its [COPYING.md](https://github.com/lichess-org/lila/blob/423f2aa1e92cf10b3344aeab0b4755dbe5a435d4/COPYING.md). The noncommercial restriction applies to these assets; commercial distribution requires suitable permission or a different piece set.

## Opening data

Lichess chess-openings: CC0. Source, pinned revision, reference sample, and generation instructions are recorded in `docs/CATALOG.md` and catalog metadata.

## Libraries

- python-chess (`chess` 1.11.2): GPL-3.0-or-later. Copyright Niklas Fiekas and contributors. Full license: `public/licenses/python-chess.txt`. Unmodified Python sources are distributed in `app.zip` alongside the application sources.
- Pyodide 314.0.6: MPL-2.0, with CPython 3.14 under the Python Software Foundation license. Runtime files are pinned by SHA-256 in `src/chugg/data/runtime.json`; upstream source: https://github.com/pyodide/pyodide/tree/314.0.6. Bundled license texts are under `public/licenses/`.
- Lucide 0.468.0: ISC. The original SVG interface icons are preserved in `src/chugg/data/icons.json`; full license: `public/licenses/lucide.txt`.

The former React, chess.js, and idb runtime dependencies are no longer shipped. Golden test fixtures record behavior from the original chess.js implementation.
