# Python migration verification

Verified locally on September 11, 2026, using native CPython 3.14 and browser CPython 3.14 through Pyodide 314.0.6:

- The original 38 TypeScript tests passed before migration.
- 103 Python tests pass. basedpyright strict reports zero errors and warnings; Ruff lint and formatting checks pass.
- Golden comparisons match every FEN, complete legal move set, and SAN recap at every ply of all 45 original lines. Sampling now weights individual lines rather than family-then-variation, so the former sampler's 500 seeded selections are kept only as a fixture record and are no longer asserted. Catalog regeneration preserves every field, all stable IDs, and version `1-b8f3863f076d`.
- Every catalog line completes for both White and Black in the Python drill state. Rules tests include castling, captures, en passant, exact promotions, checks, mate notation, illegal alternatives, hints, and odd-length endings.
- Nine real-browser IndexedDB contracts pass: fresh defaults/preferences, twelve concurrent increments, per-side records, backup roundtrip/idempotence, newer-local-data preservation, importing an original TypeScript backup, validation before writes, forced-write rollback, and unavailable storage. Run `uv run scripts/browser-tests.py` on its dedicated disposable origin.
- Browser: completed Giuoco Piano as White with two rejected moves and one hint. Completion and progress showed one session, zero clean recalls, and correct move history. Replay retained White and reset drill counters.
- Browser: the full app reloaded from the service worker with its HTTP server stopped, preserving progress and allowing library search. Giuoco Pianissimo then completed cleanly as White entirely offline, including its fourth player move.
- Browser: a rebuilt release displayed **Update Chugg** outside a drill and **Update ready after your drill** during practice; accepting the update reloaded successfully.
- Root and `/chugg/` builds pass deterministic archive, manifest, scope, runtime checksum, and complete-precache tests. The subpath build loads successfully in the browser.
- At a 390-pixel iframe viewport, document width and scroll width both measured 390 pixels; every board image loaded. Both stylesheets are byte-identical to the original. The fixed-width preview is available at `/mobile.html` on the browser-contract test server.
- Python icon regeneration produces the original 180/192/512-pixel sizes and padded maskable mark, without a system Cairo dependency. Checked-in production icons remain unchanged.
- JavaScript bootstrap, browser-host, and service-worker syntax checks pass. Python business rules and presentation are type-checked; JavaScript is confined to browser primitives and interpreter startup.

The initial static payload is approximately 13.2 MiB before HTTP compression because the Python interpreter and standard library are now local app assets. Runtime assets are checksum-pinned and included in offline caching. python-chess introduces a GPL-3.0-or-later dependency; its source and license accompany the app.

Physical iPhone/Android installation and storage eviction have not been exercised in this desktop environment. The existing platform instructions and manifest behavior are preserved. Deployment remains manual and was not triggered by this migration.

## Previous release

The former React/TypeScript release was verified and deployed on September 11, 2026. Its original source, test suite, and verification record remain in Git history. This migration is a separate commit and does not overwrite that release.
