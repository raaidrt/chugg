"""Version 1 backup validation and pure, conservative progress transformations."""

import json
import re
from time import time
from typing import NoReturn, TypeGuard, cast

from chugg.models import Backup, DrillResult, LineProgress, Preferences

MAX_BACKUP_BYTES = 2 * 1024 * 1024
MAX_RECORDS = 10_000
MAX_COUNT = 1_000_000_000
DEFAULT_PREFERENCES: Preferences = {"side": "w", "familyId": "all"}


def now_ms() -> int:
    return int(time() * 1000)


def valid_id(value: object) -> TypeGuard[str]:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{0,159}", value) is not None
    )


def integer(value: object, maximum: int = MAX_COUNT) -> TypeGuard[int]:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= value <= maximum
        and value == int(value)
    )


def timestamp(value: object) -> TypeGuard[int]:
    return integer(value, now_ms() + 86_400_000)


def mapping(value: object) -> TypeGuard[dict[str, object]]:
    return isinstance(value, dict) and all(
        isinstance(key, str) for key in cast(dict[object, object], value)
    )


def validate_preferences(value: object) -> Preferences:
    if (
        not mapping(value)
        or set(value) != {"side", "familyId"}
        or value["side"] not in ("w", "b")
        or not valid_id(value["familyId"])
    ):
        raise ValueError("Invalid backup preferences.")
    return cast(Preferences, value)


def validate_progress(value: object) -> LineProgress:
    keys = {
        "lineId",
        "side",
        "completions",
        "cleanCompletions",
        "lastCompletedAt",
        "lastMistakes",
        "lastHints",
    }
    if not mapping(value) or set(value) != keys:
        raise ValueError("Invalid progress record in backup.")
    if (
        not valid_id(value["lineId"])
        or value["side"] not in ("w", "b")
        or not integer(value["completions"])
        or value["completions"] < 1
        or not integer(value["cleanCompletions"])
        or value["cleanCompletions"] > value["completions"]
        or not timestamp(value["lastCompletedAt"])
        or not integer(value["lastMistakes"])
        or not integer(value["lastHints"])
    ):
        raise ValueError("Invalid progress record in backup.")
    record = cast(LineProgress, value)
    # JavaScript treats 1 and 1.0 identically; normalize integral JSON numbers for Python UI text.
    return {
        **record,
        "completions": int(record["completions"]),
        "cleanCompletions": int(record["cleanCompletions"]),
        "lastCompletedAt": int(record["lastCompletedAt"]),
        "lastMistakes": int(record["lastMistakes"]),
        "lastHints": int(record["lastHints"]),
    }


def reject_constant(value: str) -> NoReturn:
    raise ValueError(value)


def parse_backup(text: str) -> Backup:
    if len(text.encode("utf-8")) > MAX_BACKUP_BYTES:
        raise ValueError("This backup is too large. Choose a file smaller than 2 MB.")
    try:
        parsed: object = json.loads(text, parse_constant=reject_constant)
    except ValueError:
        raise ValueError("This file is not valid JSON. Choose a Chugg backup.") from None
    if (
        not mapping(parsed)
        or set(parsed) != {"app", "version", "exportedAt", "preferences", "progress"}
        or parsed["app"] != "chugg"
        or isinstance(parsed["version"], bool)
        or parsed["version"] != 1
        or not timestamp(parsed["exportedAt"])
        or not isinstance(parsed["progress"], list)
        or len(cast(list[object], parsed["progress"])) > MAX_RECORDS
    ):
        raise ValueError("This is not a supported Chugg backup (version 1).")
    prefs = validate_preferences(parsed["preferences"])
    records = [validate_progress(row) for row in cast(list[object], parsed["progress"])]
    seen: set[tuple[str, str]] = set()
    for row in records:
        key = row["lineId"], row["side"]
        if key in seen:
            raise ValueError(
                "This backup contains duplicate progress records. Nothing was imported."
            )
        seen.add(key)
    return {
        "app": "chugg",
        "version": 1,
        "exportedAt": int(parsed["exportedAt"]),
        "preferences": prefs,
        "progress": records,
    }


def record_result(result: DrillResult, previous: LineProgress | None) -> LineProgress:
    if (
        not valid_id(result["lineId"])
        or result["side"] not in ("w", "b")
        or not integer(result["mistakes"])
        or not integer(result["hints"])
        or not timestamp(result["completedAt"])
    ):
        raise ValueError("Invalid drill result.")
    latest = not previous or result["completedAt"] >= previous["lastCompletedAt"]
    return {
        "lineId": result["lineId"],
        "side": result["side"],
        "completions": min(MAX_COUNT, (previous["completions"] if previous else 0) + 1),
        "cleanCompletions": min(
            MAX_COUNT,
            (previous["cleanCompletions"] if previous else 0)
            + int(result["mistakes"] == 0 and result["hints"] == 0),
        ),
        "lastCompletedAt": result["completedAt"]
        if latest
        else cast(LineProgress, previous)["lastCompletedAt"],
        "lastMistakes": result["mistakes"]
        if latest
        else cast(LineProgress, previous)["lastMistakes"],
        "lastHints": result["hints"] if latest else cast(LineProgress, previous)["lastHints"],
    }


def validate_samples(value: object) -> dict[str, int]:
    """Sanitize the device's sampling tally; unreadable entries are simply forgotten."""
    if not mapping(value):
        return {}
    return {
        key: int(count)
        for key, count in value.items()
        if valid_id(key) and integer(count) and count > 0
    }


def count_sample(line_id: str, counts: dict[str, int]) -> dict[str, int]:
    if not valid_id(line_id):
        raise ValueError("Invalid sampled line.")
    return {**counts, line_id: min(MAX_COUNT, counts.get(line_id, 0) + 1)}


def merge_progress(local: LineProgress | None, incoming: LineProgress) -> LineProgress:
    latest = (
        local if local and local["lastCompletedAt"] >= incoming["lastCompletedAt"] else incoming
    )
    return {
        **latest,
        "completions": max(local["completions"] if local else 0, incoming["completions"]),
        "cleanCompletions": max(
            local["cleanCompletions"] if local else 0, incoming["cleanCompletions"]
        ),
    }
