import pytest

from chugg.classifier import PgnLine, classify_pgn, mainline_tokens

LINES: list[PgnLine] = [
    {"id": "italian", "pgn": "1. e4 e5 2. Nf3 Nc6 3. Bc4"},
    {"id": "piano", "pgn": "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5"},
]


def test_longest_match_only() -> None:
    result = classify_pgn('[Event "Test"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 *', LINES)
    assert result["counts"] == {"italian": 0, "piano": 1}
    assert result["classifiedGames"] == 1


def test_comments_variations_setup_and_unclassified() -> None:
    pgn = '[Event "A"]\n\n1.e4 {e5} e5 2.Nf3 (2.Bc4 (2.d4)) Nc6 $1 3.Bc4!? Nf6 *\n\n[Event "B"]\n\n1.d4 d5 *\n\n[Event "C"]\n[SetUp "1"]\n\n1.e4 e5 *'
    result = classify_pgn(pgn, LINES)
    assert result == {
        "counts": {"italian": 1, "piano": 0},
        "totalGames": 3,
        "classifiedGames": 1,
        "unclassifiedGames": 1,
        "skippedGames": 1,
    }
    assert mainline_tokens("1. e4 ; e5\n c5 2. Nf3 1-0") == ["e4", "c5", "Nf3"]


def test_duplicate_ties_independent_of_order() -> None:
    rows: list[PgnLine] = [{"id": "z", "pgn": "1. e4"}, {"id": "a", "pgn": "1. e4"}]
    assert classify_pgn('[Event "Test"]\n\n1.e4 *', rows)["counts"] == {"z": 0, "a": 1}


def test_nonstandard_variants_and_missing_headers() -> None:
    assert classify_pgn('[Event "A"]\n[Variant "Chess960"]\n1.e4 *', LINES)["skippedGames"] == 1
    with pytest.raises(ValueError, match="Event header"):
        classify_pgn("1.e4 *", LINES)
