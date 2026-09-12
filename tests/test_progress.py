import json
from pathlib import Path
from typing import cast

import pytest

from chugg.models import DrillResult, LineProgress
from chugg.progress import (
    MAX_BACKUP_BYTES,
    MAX_COUNT,
    merge_progress,
    parse_backup,
    record_result,
    validate_preferences,
)

LEGACY = (Path(__file__).parent / "fixtures/legacy-backup.json").read_text()


def result(**changes: object) -> DrillResult:
    return cast(
        DrillResult,
        {
            "lineId": "italian-main",
            "side": "w",
            "mistakes": 0,
            "hints": 0,
            "completedAt": 1700000000000,
            **changes,
        },
    )


def backup(**changes: object) -> str:
    parsed = cast(dict[str, object], json.loads(LEGACY))
    return json.dumps({**parsed, **changes})


def test_legacy_backup_roundtrip_and_idempotent_merge() -> None:
    parsed = parse_backup(LEGACY)
    assert parsed["preferences"] == {"side": "b", "familyId": "sicilian"}
    for row in parsed["progress"]:
        assert merge_progress(None, row) == row
        assert merge_progress(row, row) == row
    assert parse_backup(json.dumps(parsed)) == parsed


def test_counters_clean_recalls_and_latest_details() -> None:
    previous = record_result(result(), None)
    current = record_result(result(hints=1, completedAt=1700000000100), previous)
    assert (current["completions"], current["cleanCompletions"], current["lastHints"]) == (2, 1, 1)
    older = record_result(result(), current)
    assert older["lastHints"] == 1 and older["lastCompletedAt"] == 1700000000100
    capped = record_result(
        result(), {**previous, "completions": MAX_COUNT, "cleanCompletions": MAX_COUNT}
    )
    assert capped["completions"] == capped["cleanCompletions"] == MAX_COUNT


def test_merge_maxima_and_local_wins_ties() -> None:
    local = record_result(result(mistakes=2, completedAt=1700000001000), None)
    incoming: LineProgress = {
        **local,
        "completions": 8,
        "cleanCompletions": 5,
        "lastCompletedAt": 1700000000000,
        "lastMistakes": 0,
    }
    merged = merge_progress(local, incoming)
    assert merged == {**local, "completions": 8, "cleanCompletions": 5}
    assert (
        merge_progress(local, {**incoming, "lastCompletedAt": local["lastCompletedAt"]})[
            "lastMistakes"
        ]
        == 2
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"side": "x"},
        {"lineId": "../evil"},
        {"cleanCompletions": 3},
        {"lastHints": 0.5},
        {"lastMistakes": 2**53 - 1},
        {"lastCompletedAt": 99999999999999},
        {"extra": True},
        {"completions": True},
        {"completions": 0},
        {"completions": -1},
    ],
)
def test_invalid_record_rejected(changes: dict[str, object]) -> None:
    row = parse_backup(LEGACY)["progress"][0]
    with pytest.raises(ValueError, match="Invalid progress"):
        parse_backup(backup(progress=[{**row, **changes}]))


@pytest.mark.parametrize(
    "text, message",
    [
        (backup(version=2), "supported"),
        (backup(version=True), "supported"),
        ("{", "valid JSON"),
        (backup(preferences={"side": "w", "familyId": ""}), "preferences"),
        (" " * (MAX_BACKUP_BYTES + 1), "too large"),
        (backup(progress=[{"invalid": 1}] * 10001), "supported"),
        (backup(exportedAt=float("nan")), "valid JSON"),
    ],
)
def test_invalid_backup_rejected(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_backup(text)


def test_duplicate_keys_and_whole_document_validation() -> None:
    row = parse_backup(LEGACY)["progress"][0]
    with pytest.raises(ValueError, match="duplicate"):
        parse_backup(backup(progress=[row, row]))
    with pytest.raises(ValueError, match="Invalid progress"):
        parse_backup(backup(progress=[row, {**row, "lineId": "new", "completions": -1}]))
    assert validate_preferences({"side": "w", "familyId": "all"}) == {
        "side": "w",
        "familyId": "all",
    }
    unknown = {**row, "lineId": "future.line:42"}
    assert parse_backup(backup(progress=[unknown]))["progress"][0]["lineId"] == unknown["lineId"]


def test_integral_json_floats_keep_javascript_integer_display() -> None:
    row = parse_backup(LEGACY)["progress"][0]
    parsed = parse_backup(
        backup(progress=[{**row, "completions": 2.0, "lastHints": 0.0}], exportedAt=1700000000000.0)
    )
    assert type(parsed["progress"][0]["completions"]) is int
    assert type(parsed["progress"][0]["lastHints"]) is int
    assert type(parsed["exportedAt"]) is int
