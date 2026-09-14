from collections import Counter
from collections.abc import Callable
from random import Random

import pytest

from chugg.catalog import openings
from chugg.models import OpeningLine
from chugg.sampling import EXPLORATION_MAX, EXPLORATION_MIN, sample_opening, sample_side


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


def catalog_sequence(seed: int, exploration: float, draws: int) -> list[str]:
    # Mirror the app: one seeded generator across picks, five-item line cooldown.
    rng = Random(seed).random
    recent: list[str] = []
    names: list[str] = []
    for _ in range(draws):
        selected = sample_opening(openings, recent_ids=recent, exploration=exploration, rng=rng)
        assert selected
        names.append(selected["name"])
        recent = [selected["id"], *recent][:5]
    return names


def test_seeded_catalog_draws_popular() -> None:
    assert catalog_sequence(42, EXPLORATION_MIN, 25) == [
        "Caro-Kann Defense: Advance Variation",
        "Italian Game: Giuoco Piano",
        "Sicilian Defense: Najdorf Variation",
        "Sicilian Defense: Dragon Variation",
        "Queen's Gambit Declined: Tarrasch Defense",
        "Scandinavian Defense: Main Line",
        "Nimzo-Indian Defense: Rubinstein System",
        "Italian Game: Two Knights Defense",
        "Sicilian Defense: Nyezhmetdinov-Rossolimo Attack",
        "Italian Game: Giuoco Piano",
        "Sicilian Defense: Najdorf Variation",
        "French Defense: Tarrasch Variation",
        "Ruy Lopez: Berlin Defense",
        "Ruy Lopez: Marshall Attack",
        "Caro-Kann Defense: Exchange Variation",
        "French Defense: Winawer Variation",
        "Sicilian Defense: Najdorf Variation",
        "Caro-Kann Defense: Advance Variation",
        "King's Indian Defense: Orthodox Variation",
        "Italian Game: Giuoco Piano",
        "Slav Defense: Three Knights Variation",
        "Scandinavian Defense: Main Line",
        "Sicilian Defense: Alapin Variation",
        "Ruy Lopez: Morphy Defense",
        "Scotch Game: Schmidt Variation",
    ]


def test_seeded_catalog_draws_max_exploration() -> None:
    assert catalog_sequence(2025, EXPLORATION_MAX, 25) == [
        "Queen's Gambit Declined: Exchange Variation",
        "Slav Defense: Exchange Variation",
        "Caro-Kann Defense: Panov Attack",
        "Ruy Lopez: Marshall Attack",
        "Italian Game: Giuoco Piano",
        "Scotch Game: Göring Gambit",
        "Queen's Gambit Declined: Exchange Variation",
        "Italian Game: Two Knights Defense",
        "Caro-Kann Defense: Classical Variation",
        "Italian Game: Giuoco Piano, Greco's Attack",
        "King's Indian Defense: Four Pawns Attack",
        "London System",
        "Ruy Lopez: Exchange Variation",
        "Italian Game: Giuoco Pianissimo",
        "Italian Game: Two Knights Defense",
        "Scandinavian Defense: Modern Variation",
        "Nimzo-Indian Defense: Classical Variation",
        "Sicilian Defense: Alapin Variation",
        "Sicilian Defense: Dragon Variation",
        "King's Indian Defense: Orthodox Variation",
        "London System",
        "Scotch Game: Classical Variation",
        "Queen's Gambit Declined: Tarrasch Defense",
        "English Opening: Symmetrical Variation, Four Knights Variation",
        "French Defense: Advance Variation",
    ]


def test_seeded_catalog_draws_mixed_exploration() -> None:
    assert catalog_sequence(7, 0.5, 25) == [
        "Sicilian Defense: Closed",
        "Ruy Lopez: Morphy Defense",
        "Queen's Gambit Declined: Exchange Variation",
        "Italian Game: Two Knights Defense",
        "Caro-Kann Defense: Panov Attack",
        "French Defense: Advance Variation",
        "Italian Game: Giuoco Piano, Greco's Attack",
        "Caro-Kann Defense: Advance Variation",
        "Italian Game: Giuoco Pianissimo",
        "French Defense: Exchange Variation",
        "Italian Game: Two Knights Defense",
        "Ruy Lopez: Morphy Defense",
        "French Defense: Winawer Variation",
        "Nimzo-Indian Defense: Rubinstein System",
        "Ruy Lopez: Marshall Attack",
        "Sicilian Defense: Alapin Variation",
        "Scandinavian Defense: Gubinsky-Melts Defense",
        "Scotch Game: Schmidt Variation",
        "Caro-Kann Defense: Classical Variation",
        "French Defense: Advance Variation",
        "Scotch Game: Göring Gambit",
        "Italian Game: Giuoco Pianissimo",
        "Nimzo-Indian Defense: Classical Variation",
        "Sicilian Defense: Alapin Variation",
        "Ruy Lopez: Morphy Defense",
    ]
