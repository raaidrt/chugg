#!/usr/bin/env python3
"""Measure observed sampling probabilities against the sampler's intent.

Local diagnostics only; nothing here ships in the app bundle. Examples:

  uv run scripts/sampling-debug.py --exploration 1.0 --draws 200000
  uv run scripts/sampling-debug.py --seeds 1,2,3 --debug   # also log every draw
"""

import argparse
import logging
from collections import Counter
from math import isfinite, sqrt
from random import Random

from chugg.catalog import openings
from chugg.sampling import POPULARITY_EXPONENT, sample_opening

log = logging.getLogger("sampling-debug")


def expected_probabilities(exploration: float) -> dict[str, float]:
    """What weighted_pick intends per line, ignoring the cooldown interaction."""
    n = len(openings)
    weights = [max(row["popularity"], 0) ** POPULARITY_EXPONENT for row in openings]
    total = sum(weights)
    if total <= 0:
        return {row["id"]: 1 / n for row in openings}
    return {
        row["id"]: (1 - exploration) * w / total + exploration / n
        for row, w in zip(openings, weights)
    }


def run(seed: int, exploration: float, draws: int, cooldown: bool) -> tuple[Counter[str], int]:
    """Draw `draws` picks the way the app does; return counts and cooldown violations."""
    rng = Random(seed).random
    recent: list[str] = []
    counts: Counter[str] = Counter()
    violations = 0
    for i in range(draws):
        selected = sample_opening(openings, recent_ids=recent, exploration=exploration, rng=rng)
        assert selected
        counts[selected["id"]] += 1
        if selected["id"] in recent:
            violations += 1
        if cooldown:
            recent = [selected["id"], *recent][:5]
        log.debug("draw %6d -> %s", i, selected["name"])
    return counts, violations


def report(counts: Counter[str], expected: dict[str, float], draws: int, violations: int) -> None:
    chi2 = 0.0
    worst = 0.0
    never = 0
    log.info("%-58s %8s %8s %9s %7s", "line", "pop", "exp%", "obs%", "z")
    for row in sorted(openings, key=lambda r: expected[r["id"]]):
        p = expected[row["id"]]
        obs = counts[row["id"]] / draws
        var = p * (1 - p) / draws
        z = (obs - p) / sqrt(var) if var > 0 else 0.0
        chi2 += (counts[row["id"]] - draws * p) ** 2 / (draws * p)
        worst = max(worst, abs(z))
        never += counts[row["id"]] == 0
        log.info(
            "%-58s %8g %8.4f %9.4f %+7.2f", row["name"], row["popularity"], p * 100, obs * 100, z
        )
    df = len(openings) - 1
    log.info("-" * 92)
    log.info(
        "draws=%d  lines=%d  never-sampled=%d  cooldown-violations=%d  max|z|=%.2f",
        draws,
        len(openings),
        never,
        violations,
        worst,
    )
    log.info("chi2=%.1f  df=%d  (95%% critical ~%.1f)", chi2, df, df + 1.645 * sqrt(2 * df))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="2025", help="Comma-separated Random() seeds")
    parser.add_argument("--draws", type=int, default=100_000)
    parser.add_argument("--exploration", type=float, default=1.0)
    parser.add_argument("--no-cooldown", action="store_true", help="isolate the raw pick")
    parser.add_argument("--debug", action="store_true", help="log every draw")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)-5s %(message)s" if args.debug else "%(message)s",
    )
    if not isfinite(args.exploration) or not 0 <= args.exploration <= 1:
        parser.error("--exploration must be in [0, 1]")
    expected = expected_probabilities(args.exploration)
    for seed in (int(part) for part in args.seeds.split(",")):
        counts, violations = run(seed, args.exploration, args.draws, not args.no_cooldown)
        log.info("=== seed %d ===", seed)
        report(counts, expected, args.draws, violations)


if __name__ == "__main__":
    main()
