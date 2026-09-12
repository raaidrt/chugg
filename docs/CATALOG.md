# Chugg's offline opening catalog

Chugg ships 45 drills across 13 opening families as static application data. Every drill has one complete, fixed UCI move sequence and the exact name of its endpoint. The catalog introduces named positions; it does not claim to teach every continuation of an opening. Both colors train the same sequence.

No explorer, game archive, account, or server is contacted while using the trainer. Catalog preparation happens on a maintainer's computer or in CI, then the resulting catalog is bundled with the app and cached for offline use.

## Opening names and moves

`scripts/catalog-selection.json` contains the selected ECO codes, names, and PGN sequences from [Lichess chess-openings](https://github.com/lichess-org/chess-openings/tree/4b8622759e7ae6f93f011cc6c83a3823401ab45e), pinned to commit `4b8622759e7ae6f93f011cc6c83a3823401ab45e`. That dataset is CC0. We selected the shortest upstream sequence for each chosen name; where lengths tie, PGN text determines the choice. There is no invented extension of a named line.

`uv run chugg catalog-build` uses python-chess to validate the PGNs and convert them to UCI moves. It generates `src/chugg/data/catalog.json`, including source metadata and a content-derived catalog version. Stable line IDs are independent of popularity counts. Preserve an ID when only its metadata changes; use a new ID if the actual training sequence changes, so existing progress is not attached to a different drill.

## What “popularity” means in this release

The counts are measured from the public tournament games in [The Week in Chess](https://theweekinchess.com/) issues **1600–1603**, covering July 2025 releases. Source game date tags range from April 24 through July 28, 2025; issue publication dates are not a game-date filter. The files were retrieved September 11, 2026 UTC.

| Reference metric                    |  Count |
| ----------------------------------- | -----: |
| PGN game records                    | 34,669 |
| Classified into one supported drill |  8,910 |
| Unclassified                        | 25,594 |
| Nonstandard/setup games skipped     |    165 |

The initial goal was an online rapid reference population. Both public Lichess explorer endpoints returned HTTP 401 during preparation, so this release uses accessible tournament games instead. **These weights are not estimates of what a particular online rating group plays.** The app discloses the tournament source in its catalog information.

Classification follows exact PGN mainline move orders from the standard starting position. Each game contributes to its longest matching supported drill, once. A game reaching the Italian Game and then the deeper Giuoco Piano contributes only to the deeper match. Equal-length duplicate matches are resolved by ascending stable ID. Comments, alternative variations, numeric annotation glyphs, and check/annotation punctuation are ignored. Games without a supported prefix remain unclassified; nonstandard start positions and variants are skipped.

This is deliberately an **exclusive count within the supported catalog**, not a sum of overlapping position-reach counts. Its limitations matter:

- Different move orders leading to the same position are not merged. They can remain unclassified or match a shallower drill.
- Only 25.7% of these game records match a supported line; this is a small curated opening catalog.
- The data reflects the events covered in these four TWIC issues. There is no rating or time-control filter, and no attempt to deduplicate repeated game records across source files.
- Adding a more specific drill redistributes some counts away from its ancestor. Adding coverage can change family totals; merely duplicating an entry must not increase counts.
- A zero count means “unobserved under this classification,” not “never played.”

Only aggregate counts and source identifiers/checksums are checked in. The source games and player names are not distributed to phones. `scripts/catalog-sources.json` records fixed download URLs, SHA-256 checksums of the uncompressed source files, and observed date-tag ranges. `scripts/catalog-counts.json` records the cohort description, game totals, file hashes, and per-drill counts.

## Sampling on the device

`src/chugg/sampling.py` filters the eligible catalog, applies a recent-drill cooldown, samples a family, then samples a complete line within that family. It commits to that line before its name is displayed.

At both stages, with candidate counts `c`:

```text
w(i) = max(c(i), 0)^0.7
P(i) = 0.95 × w(i) / sum(w) + 0.05 / candidateCount
```

If all candidate counts are zero, sampling is uniform. The 5% exploration component gives unobserved lines a chance. The exponent softens the gap between common and rare openings. Family counts are sums of the exclusive per-drill counts, so adding an unobserved line cannot inflate the family's frequency.

Recent IDs are excluded when at least one eligible alternative exists. If every eligible drill is recent, the sampler uses the full filtered pool. Within a still-eligible family, cooldown does not temporarily reduce the family's full reference count. An unknown family or empty input returns no result. The optional random-number source supports deterministic tests; production uses Python’s `random.random()`.

## Reproduce the current catalog

With the project's dependencies installed, this uses only checked-in inputs and performs **no network requests**:

```sh
uv run chugg catalog-build
uv run pytest
```

The script resolves its input/output paths relative to the project package, so it can run from any working directory. Regenerating from the same selection and counts produces byte-identical catalog output.

To independently retrieve and verify the original source records, the uv-managed project environment and curl are sufficient:

```sh
uv run scripts/catalog-fetch.py --directory /tmp/chugg-reference --download
uv run scripts/catalog-fetch.py --directory /tmp/chugg-reference --rebuild
```

The first command downloads public source files, checks their fixed SHA-256 checksums, and verifies that every selected name/ECO/PGN row is present in the pinned upstream tables. It fails on changed inputs. The second verifies already downloaded inputs and rebuilds the original measured counts and catalog without network access. `--rebuild` intentionally replaces any later custom counts with the reference snapshot.

## Replace the cohort with your own PGNs

Use standard SAN PGN files containing an `Event` header for each game. The paths are local files, and the command makes no network calls:

```sh
CATALOG_SOURCE='My rapid reference sample' \
CATALOG_DESCRIPTION='Standard rapid games; describe the date/rating filters used to produce these files.' \
CATALOG_DATE='2026-09-11' \
uv run chugg catalog-build /absolute/path/sample-a.pgn /absolute/path/sample-b.pgn
```

The command replaces `scripts/catalog-counts.json` and regenerates the catalog. Record the actual input cohort in the environment fields; the script does not enforce rating or time-control filters. It hashes each file and reports classified coverage. Source files are read into memory one at a time, so preprocess very large archives into manageable PGN files first. Keep your original source files to reproduce a custom cohort. The checked-in source manifest continues to describe the original TWIC reference snapshot.

After adding or changing a selected line, rerun classification on the source PGNs rather than copying counts: exclusive assignments depend on the supported catalog. Then run the tests and review the resulting count/coverage changes before shipping a new static build.

For a later rating-specific reference, prepare an appropriately filtered Lichess game sample offline and run it through this same pipeline. Position-based transposition matching or a broader catalog would be a separate classifier improvement; neither requires an application server.
