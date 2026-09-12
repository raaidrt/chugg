"""Family-first popularity sampling with exploration and recent-line cooldown."""

from collections.abc import Callable, Sequence
from math import isfinite
from random import random

from chugg.models import OpeningLine, Side

POPULARITY_EXPONENT = 0.7
# The exploration share blends popularity weights with a uniform pick:
# (1 - alpha) * w / total + alpha / n. The home screen slider spans Popular..Random.
EXPLORATION_MIN = 0.05
EXPLORATION_MAX = 0.95


def sample_side(rng: Callable[[], float] = random) -> Side:
    return "w" if rng() < 0.5 else "b"


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


def sample_opening(
    lines: Sequence[OpeningLine],
    *,
    family_id: str = "all",
    recent_ids: Sequence[str] = (),
    exploration: float = EXPLORATION_MIN,
    rng: Callable[[], float] = random,
) -> OpeningLine | None:
    filtered = [
        line
        for line in lines
        if not family_id or family_id == "all" or line["familyId"] == family_id
    ]
    if not filtered:
        return None
    recent = set(recent_ids)
    pool = [line for line in filtered if line["id"] not in recent] or filtered
    families: dict[str, list[OpeningLine]] = {}
    counts: dict[str, float] = {}
    for line in pool:
        families.setdefault(line["familyId"], []).append(line)
    for line in filtered:
        key = line["familyId"]
        counts[key] = counts.get(key, 0) + valid_count(line["popularity"])
    family = weighted_pick(list(families), lambda key: counts[key], rng, exploration)
    return weighted_pick(families[family], lambda line: line["popularity"], rng, exploration)
