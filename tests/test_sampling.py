from collections import Counter
from collections.abc import Callable

import pytest

from chugg.models import OpeningLine
from chugg.sampling import sample_opening, sample_side


def line(identifier: str, family: str, count: float) -> OpeningLine:
    return {
        "id": identifier,
        "familyId": family,
        "family": family,
        "popularity": count,
        "name": identifier,
        "eco": "A00",
        "moves": ["e2e4"],
        "description": "",
    }


def seeded() -> Callable[[], float]:
    seed = 2025

    def rng() -> float:
        nonlocal seed
        seed = (1664525 * seed + 1013904223) & 0xFFFFFFFF
        return seed / 4294967296

    return rng


def frequencies(lines: list[OpeningLine], exploration: float = 0.05) -> dict[str, float]:
    rng = seeded()
    counts: Counter[str] = Counter()
    for _ in range(40000):
        result = sample_opening(lines, exploration=exploration, rng=rng)
        assert result
        counts[result["id"]] += 1
    return {key: value / 40000 for key, value in counts.items()}


def test_equal_sides() -> None:
    rng = seeded()
    assert 0.48 < sum(sample_side(rng) == "w" for _ in range(10000)) / 10000 < 0.52


def test_softened_frequency_and_exploration() -> None:
    observed = frequencies(
        [line("common", "a", 1000), line("rare", "a", 10), line("unseen", "a", 0)]
    )
    total = 1000**0.7 + 10**0.7
    assert observed["common"] == pytest.approx(0.95 * 1000**0.7 / total + 0.05 / 3, abs=0.005)
    assert observed["rare"] == pytest.approx(0.95 * 10**0.7 / total + 0.05 / 3, abs=0.005)
    assert observed["unseen"] > 0.01


def test_full_exploration_is_uniform() -> None:
    observed = frequencies(
        [line("common", "a", 1000), line("rare", "a", 10), line("unseen", "a", 0)],
        exploration=1.0,
    )
    assert observed["common"] == pytest.approx(1 / 3, abs=0.01)
    assert observed["rare"] == pytest.approx(1 / 3, abs=0.01)
    assert observed["unseen"] == pytest.approx(1 / 3, abs=0.01)


def test_max_exploration_is_uniform_per_opening() -> None:
    # Family size must not matter: at maximum exploration every opening — not every
    # family — is equally likely.
    lines = [
        line("a-one", "a", 100),
        line("b-one", "b", 100),
        *[line(f"b-{i}", "b", 0) for i in range(12)],
    ]
    observed = frequencies(lines, exploration=1.0)
    for row in lines:
        assert observed[row["id"]] == pytest.approx(1 / len(lines), abs=0.005)


def test_popularity_weights_apply_per_opening() -> None:
    lines = [
        line("a-one", "a", 100),
        line("b-one", "b", 100),
        *[line(f"b-{i}", "b", 0) for i in range(12)],
    ]
    observed = frequencies(lines)
    share = 0.95 * 100**0.7 / (2 * 100**0.7) + 0.05 / 14
    assert observed["a-one"] == pytest.approx(share, abs=0.005)
    assert observed["b-one"] == pytest.approx(share, abs=0.005)


def test_filter_cooldown_and_empty_pools() -> None:
    lines = [line("a", "x", 5), line("b", "x", 0), line("c", "y", 9999)]
    assert sample_opening(lines, family_id="x", recent_ids=["a"], rng=lambda: 0) == lines[1]
    assert sample_opening(lines, family_id="unknown") is None
    assert sample_opening([]) is None
    assert sample_opening(lines, family_id="x", recent_ids=["a", "b"], rng=lambda: 0) == lines[0]
    # Cooldown removes the recent line's own weight from the pick.
    candidates = [line("a-old", "a", 100), line("a-new", "a", 0), line("b", "b", 100)]
    assert sample_opening(candidates, recent_ids=["a-old"], rng=lambda: 0.4) == candidates[2]


def test_uniform_fallback_and_invalid_counts() -> None:
    observed = frequencies([line("a", "x", float("nan")), line("b", "x", -2)])
    assert observed["a"] == pytest.approx(0.5, abs=0.005)


@pytest.mark.parametrize("draw", [1, -0.1, float("nan"), float("inf")])
def test_invalid_rng(draw: float) -> None:
    with pytest.raises(ValueError):
        sample_opening([line("a", "x", 1)], rng=lambda: draw)


def test_each_pick_seeds_a_fresh_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[object] = []

    class FakeRandom:
        def __init__(self) -> None:
            created.append(self)

        def random(self) -> float:
            return 0.5

    monkeypatch.setattr("chugg.sampling.Random", FakeRandom)
    sample_opening([line("a", "x", 1)])
    sample_side()
    assert len(created) == 2
