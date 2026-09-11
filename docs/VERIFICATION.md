# First-release verification

Verified locally on September 11, 2026:

- TypeScript strict compilation and production builds at both `/` and `/chugg/`.
- 37 automated tests covering catalog legality, count conservation, weighted sampling/cooldown, chess move validation, castling/captures/en passant/promotion, per-side storage, concurrent result recording, invalid backups, idempotent imports, and atomic rollback.
- All 45 lines replayed successfully with chess.js.
- Browser: completed Giuoco Piano as White with two rejected moves and one hint; result displayed 3 moves, 2 retries, 1 hint.
- Browser: completed the same variation cleanly as Black; progress displayed distinct White and Black records and accurate clean recall totals.
- Browser: stopped the HTTP preview server, reloaded the app successfully from the service-worker cache, and verified saved progress remained visible.
- Browser, server still stopped: completed Giuoco Pianissimo as Black, including the final automatic White move `4. d3`, entirely offline.
- Browser: updated a cached release through the update prompt between drills.
- Browser: checked Safari and Android installation instructions and the `/chugg/` manifest/piece image paths.
- At a 390px mobile viewport, document width matched viewport width with no horizontal overflow; every observed piece image loaded.
- GitHub Actions test/build and initial Pages deployment both succeeded for release commit `31894c8`. The live HTTPS site at `https://raaidrt.com/chugg/` loaded its piece assets and reached “Ready for offline practice.”

Physical iPhone/Android home-screen installation has not been exercised in this desktop environment. Follow the in-app guides on a real phone for a final platform check. Browser storage eviction and cross-device migration depend on the browser and device; export/import tests verify the app's backup logic.
