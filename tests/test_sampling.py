from collections import Counter
from collections.abc import Callable
from random import Random

import pytest

from chugg.catalog import openings
from chugg.models import OpeningLine
from chugg.progress import MAX_COUNT
from chugg.sampling import (
    EXPLORATION_MAX,
    EXPLORATION_MIN,
    SAMPLE_LIMIT,
    SIDES,
    available_lines,
    available_sides,
    count_sample,
    remaining_draws,
    sample_available_side,
    sample_key,
    sample_opening,
    sample_side,
    validate_samples,
)


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


def spent(*line_ids: str) -> dict[str, int]:
    """A tally with both sides of each line drawn to the limit."""
    return {sample_key(row, side): SAMPLE_LIMIT for row in line_ids for side in SIDES}


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


def test_sampled_lines_are_rejected_until_reset() -> None:
    lines = [line("a", "x", 100), line("b", "x", 1)]
    # "a" is retired from both sides, so every draw returns "b" wherever the RNG lands.
    for draw in (0.0, 0.5, 0.999):
        assert sample_opening(lines, sampled=spent("a"), rng=lambda: draw) == lines[1]
    # Partial draws still leave a line in the pool.
    partial = {sample_key("a", side): SAMPLE_LIMIT - 1 for side in SIDES}
    assert sample_opening(lines, sampled=partial, rng=lambda: 0) == lines[0]
    # Counts above the limit (a shrunken catalog, a tampered store) retire the side too.
    over = {sample_key("a", side): SAMPLE_LIMIT + 5 for side in SIDES}
    assert sample_opening(lines, sampled=over, rng=lambda: 0) == lines[1]
    # Exhausting the pool yields no pick at all rather than repeating a line.
    assert sample_opening(lines, sampled=spent("a", "b")) is None
    assert sample_opening(lines, sampled={}) is not None


def test_exhaustion_outranks_the_cooldown() -> None:
    lines = [line("a", "x", 100), line("b", "x", 100), line("c", "x", 100)]
    retired = spent("a")
    # The cooldown yields when it would empty the pool; it never revives a retired line.
    cooled = ["a", "b", "c"]
    assert sample_opening(lines, recent_ids=cooled, rng=lambda: 0) == lines[0]
    assert sample_opening(lines, recent_ids=cooled, sampled=retired, rng=lambda: 0) == lines[1]
    # With "a" retired and "b" on cooldown, only "c" is left to draw.
    assert sample_opening(lines, recent_ids=["b"], sampled=retired, rng=lambda: 0.9) == lines[2]


def test_family_filter_applies_before_exhaustion() -> None:
    lines = [line("a", "x", 5), line("b", "y", 5)]
    assert sample_opening(lines, family_id="x", sampled=spent("a")) is None
    assert sample_opening(lines, family_id="y", sampled=spent("a")) == lines[1]


def test_available_lines_counts_what_can_still_be_drawn() -> None:
    lines = [line("a", "x", 5), line("b", "x", 5), line("c", "x", 5)]
    assert available_lines(lines) == lines
    assert available_lines(lines, {}) == lines
    assert available_lines(lines, {sample_key("a", "w"): SAMPLE_LIMIT - 1}) == lines
    # One spent side is not enough to drop a line from the pool.
    assert available_lines(lines, {sample_key("a", "w"): SAMPLE_LIMIT}) == lines
    assert available_lines(lines, spent("a", "c")) == [lines[1]]
    assert available_lines(lines, spent("a", "b", "c")) == []
    # Unknown ids belong to other catalogs and must not retire anything.
    assert available_lines(lines, spent("gone")) == lines


def test_rejection_preserves_the_weighting_of_the_rest() -> None:
    lines = [line("common", "a", 1000), line("rare", "a", 10), line("retired", "a", 500)]
    rng = seeded()
    counts: Counter[str] = Counter()
    for _ in range(40000):
        result = sample_opening(lines, sampled=spent("retired"), rng=rng)
        assert result
        counts[result["id"]] += 1
    total = 1000**0.7 + 10**0.7
    assert counts["retired"] == 0
    assert counts["common"] / 40000 == pytest.approx(0.95 * 1000**0.7 / total + 0.05 / 2, abs=0.005)


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


def test_tally_counts_each_side_separately() -> None:
    first = count_sample("italian-main", "w", {})
    assert first == {"italian-main:w": 1}
    assert count_sample("italian-main", "w", first) == {"italian-main:w": 2}
    # The same opening from the other side is a different drill with its own count.
    both = count_sample("italian-main", "b", first)
    assert both == {"italian-main:w": 1, "italian-main:b": 1}
    # The source dictionary is never mutated in place; callers hold their own snapshot.
    assert first == {"italian-main:w": 1}
    assert count_sample("italian-main", "w", {"italian-main:w": MAX_COUNT}) == {
        "italian-main:w": MAX_COUNT
    }
    with pytest.raises(ValueError, match="Invalid sampled line"):
        count_sample("not a line id", "w", {})


def test_tally_survives_unreadable_storage() -> None:
    assert validate_samples({"italian-main:w": 2, "italian-main:b": 1.0}) == {
        "italian-main:w": 2,
        "italian-main:b": 1,
    }
    assert type(validate_samples({"a:w": 2.0})["a:w"]) is int
    # Anything the sampler could not act on is dropped rather than failing the read.
    assert validate_samples({"bad id:w": 3, "a:w": -1, "b:w": "2", "c:w": 0}) == {}
    assert validate_samples({"a:w": MAX_COUNT + 1, "b:w": True}) == {}
    # Keys without a side predate per-side history and no longer mean anything.
    assert validate_samples({"italian-main": 2, ":w": 1, "a:x": 1}) == {}
    unusable: list[object] = [None, [], "sampled", 7]
    for value in unusable:
        assert validate_samples(value) == {}


def test_a_line_stays_available_until_both_sides_are_spent() -> None:
    lines = [line("a", "x", 100), line("b", "x", 1)]
    half = {sample_key("a", "w"): SAMPLE_LIMIT}
    # White is spent, so "a" can still be drawn — but only as Black.
    assert available_sides("a", half) == ["b"]
    assert available_lines(lines, half) == lines
    assert sample_available_side("a", half) == "b"
    assert sample_opening(lines, sampled=half, rng=lambda: 0) == lines[0]
    # Once both sides are spent the line itself drops out of the pool.
    assert available_sides("a", spent("a")) == []
    assert available_lines(lines, spent("a")) == [lines[1]]
    assert sample_opening(lines, sampled=spent("a"), rng=lambda: 0) == lines[1]
    assert sample_opening(lines, sampled=spent("a", "b")) is None


def test_both_sides_stay_random_while_both_remain() -> None:
    rng = seeded()
    drawn = [sample_available_side("a", {}, rng) for _ in range(10000)]
    assert 0.48 < drawn.count("w") / 10000 < 0.52
    # With one side left there is nothing to randomize.
    assert {
        sample_available_side("a", {sample_key("a", "b"): SAMPLE_LIMIT}) for _ in range(20)
    } == ({"w"})


def test_remaining_draws_counts_openings_and_sides() -> None:
    lines = [line("a", "x", 5), line("b", "x", 5)]
    assert remaining_draws(lines) == remaining_draws(lines, {}) == 4
    assert remaining_draws(lines, {sample_key("a", "w"): SAMPLE_LIMIT}) == 3
    assert remaining_draws(lines, {sample_key("a", "w"): SAMPLE_LIMIT - 1}) == 4
    assert remaining_draws(lines, spent("a")) == 2
    assert remaining_draws(lines, spent("a", "b")) == 0
    # Unknown ids belong to other catalogs and must not retire anything.
    assert remaining_draws(lines, spent("gone")) == 4
