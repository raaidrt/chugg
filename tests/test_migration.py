"""Golden contracts captured from the pre-migration TypeScript/chess.js implementation."""

import json
from pathlib import Path
from typing import TypedDict, cast

import pytest

from chugg.catalog import catalog, openings
from chugg.catalog_build import Reference, Selection, generate
from chugg.sampling import sample_opening
from chugg.trainer import notation, position_at

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).parents[1]


class Position(TypedDict):
    fen: str
    san: str
    legal: list[str]


class LinePositions(TypedDict):
    id: str
    plies: list[Position]


POSITIONS = cast(list[LinePositions], json.loads((FIXTURES / "legacy-positions.json").read_text()))


@pytest.mark.parametrize("reference", POSITIONS, ids=[row["id"] for row in POSITIONS])
def test_every_position_notation_and_legal_move_matches_chess_js(reference: LinePositions) -> None:
    line = next(row for row in openings if row["id"] == reference["id"])
    for ply, expected in enumerate(reference["plies"]):
        board = position_at(line["moves"], ply)
        assert board.fen() == expected["fen"]
        assert notation(line["moves"][:ply]) == expected["san"]
        assert sorted(move.uci() for move in board.legal_moves) == expected["legal"]


def test_sampling_matches_500_legacy_draws_with_cooldown() -> None:
    seed = 2025

    def rng() -> float:
        nonlocal seed
        seed = (1664525 * seed + 1013904223) & 0xFFFFFFFF
        return seed / 4294967296

    recent: list[str] = []
    for expected in cast(list[str], json.loads((FIXTURES / "legacy-sampling.json").read_text())):
        selected = sample_opening(openings, recent_ids=recent, rng=rng)
        assert selected and selected["id"] == expected
        recent = [selected["id"], *recent][:5]


def test_catalog_regeneration_preserves_every_field_and_version() -> None:
    selection = cast(
        list[Selection], json.loads((ROOT / "scripts/catalog-selection.json").read_text())
    )
    reference = cast(Reference, json.loads((ROOT / "scripts/catalog-counts.json").read_text()))
    assert generate(selection, reference) == catalog
    assert catalog["metadata"]["version"] == "1-b8f3863f076d"
    assert len(openings) == len({row["id"] for row in openings}) == 45
    assert len({row["familyId"] for row in openings}) == 13
    assert sum(row["popularity"] for row in openings) == reference["classifiedGames"] == 8910
    assert (
        reference["classifiedGames"] + reference["unclassifiedGames"] + reference["skippedGames"]
        == reference["totalGames"]
        == 34669
    )
    assert sum(file["games"] for file in reference["files"]) == reference["totalGames"]
