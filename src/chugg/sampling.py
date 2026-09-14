"""Popularity-weighted opening sampling with exploration and recent-line cooldown."""

from collections.abc import Callable, Mapping, Sequence
from math import isfinite
from random import Random

from chugg.models import OpeningLine, Side

POPULARITY_EXPONENT = 0.7
# The exploration share blends popularity weights with a uniform pick:
# (1 - alpha) * w / total + alpha / n. The home screen slider spans Popular..Random.
EXPLORATION_MIN = 0.05
EXPLORATION_MAX = 1.0
# Rejection sampling retires a line once it has been drawn this many times.
SAMPLE_LIMIT = 2


def sample_side(rng: Callable[[], float] | None = None) -> Side:
    # A freshly seeded generator per pick: browser runtimes can start the module-level
    # random sequence from a fixed startup seed, which would replay the same draws.
    return "w" if (rng or Random().random)() < 0.5 else "b"


def valid_count(value: float) -> float:
    return value if isfinite(value) and value > 0 else 0


def weighted_pick[T](
    items: Sequence[T],
    get_count: Callable[[T], float],
    rng: Callable[[], float],
    exploration: float = EXPLORATION_MIN,
) -> T:
    weights = [valid_count(get_count(item)) ** POPULARITY_EXPONENT for item in items]
    total = sum(weights)
    remaining = rng()
    if not isfinite(remaining) or not 0 <= remaining < 1:
        raise ValueError("Sampling RNG must return a number in [0, 1).")
    for item, weight in zip(items, weights, strict=True):
        remaining -= (
            ((1 - exploration) * weight / total + exploration / len(items))
            if total > 0
            else 1 / len(items)
        )
        if remaining < 0:
            return item
    return items[-1]


def available_lines(
    lines: Sequence[OpeningLine], sampled: Mapping[str, int] | None = None
) -> list[OpeningLine]:
    """Lines rejection sampling still accepts: drawn fewer than SAMPLE_LIMIT times."""
    counts = sampled or {}
    return [line for line in lines if counts.get(line["id"], 0) < SAMPLE_LIMIT]


def sample_opening(
    lines: Sequence[OpeningLine],
    *,
    family_id: str = "all",
    recent_ids: Sequence[str] = (),
    sampled: Mapping[str, int] | None = None,
    exploration: float = EXPLORATION_MIN,
    rng: Callable[[], float] | None = None,
) -> OpeningLine | None:
    filtered = [
        line
        for line in lines
        if not family_id or family_id == "all" or line["familyId"] == family_id
    ]
    # Rejecting up front draws from the same distribution as redrawing until a line is
    # accepted, without the unbounded retries; exhausting every line yields no pick at all.
    remaining = available_lines(filtered, sampled)
    if not remaining:
        return None
    recent = set(recent_ids)
    # Unlike the sampling limit, the cooldown yields rather than run out of openings.
    pool = [line for line in remaining if line["id"] not in recent] or remaining
    return weighted_pick(
        pool,
        lambda line: line["popularity"],
        rng or Random().random,
        exploration,
    )
