"""Popularity-weighted sampling with exploration, cooldown, and per-side draw history."""

from collections.abc import Callable, Mapping, Sequence
from math import isfinite
from random import Random

from chugg.models import OpeningLine, Side
from chugg.progress import MAX_COUNT, integer, mapping, valid_id

POPULARITY_EXPONENT = 0.7
# The exploration share blends popularity weights with a uniform pick:
# (1 - alpha) * w / total + alpha / n. The home screen slider spans Popular..Random.
EXPLORATION_MIN = 0.05
EXPLORATION_MAX = 1.0
# Rejection sampling retires an opening from one side once it has been drawn this often.
SAMPLE_LIMIT = 2
SIDES: tuple[Side, ...] = ("w", "b")


def sample_key(line_id: str, side: Side) -> str:
    # White and Black are separate drills, and the tally keeps them apart the way
    # progress records already do with their compound [lineId, side] key.
    return f"{line_id}:{side}"


def valid_sample_key(key: str) -> bool:
    line_id, _, side = key.rpartition(":")
    return bool(line_id) and side in SIDES and valid_id(key)


def validate_samples(value: object) -> dict[str, int]:
    """Sanitize the device's tally; unreadable entries are simply forgotten."""
    if not mapping(value):
        return {}
    return {
        key: int(count)
        for key, count in value.items()
        if valid_sample_key(key) and integer(count) and count > 0
    }


def count_sample(line_id: str, side: Side, counts: dict[str, int]) -> dict[str, int]:
    key = sample_key(line_id, side)
    if not valid_sample_key(key):
        raise ValueError("Invalid sampled line.")
    return {**counts, key: min(MAX_COUNT, counts.get(key, 0) + 1)}


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


def available_sides(line_id: str, sampled: Mapping[str, int] | None = None) -> list[Side]:
    """Sides this opening can still be drawn for: fewer than SAMPLE_LIMIT draws so far."""
    counts = sampled or {}
    return [side for side in SIDES if counts.get(sample_key(line_id, side), 0) < SAMPLE_LIMIT]


def available_lines(
    lines: Sequence[OpeningLine], sampled: Mapping[str, int] | None = None
) -> list[OpeningLine]:
    """Lines rejection sampling still accepts: at least one side left to draw."""
    return [line for line in lines if available_sides(line["id"], sampled)]


def remaining_draws(lines: Sequence[OpeningLine], sampled: Mapping[str, int] | None = None) -> int:
    """How many opening-and-side drills the sampler can still produce."""
    return sum(len(available_sides(line["id"], sampled)) for line in lines)


def sample_available_side(
    line_id: str,
    sampled: Mapping[str, int] | None = None,
    rng: Callable[[], float] | None = None,
) -> Side:
    """Pick a side the opening can still be drawn for; random while both remain."""
    sides = available_sides(line_id, sampled)
    return sides[0] if len(sides) == 1 else sample_side(rng)


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
    # accepted, without the unbounded retries; exhausting every line and side yields no
    # pick at all.
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
