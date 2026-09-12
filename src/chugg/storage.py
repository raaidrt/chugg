"""Browser repository: validation precedes one synchronous atomic IDB mutation."""

import json
from collections.abc import Callable
from typing import TypedDict, cast

from chugg.browser import Host, ProxyFactory
from chugg.models import Backup, DrillResult, LineProgress, Preferences
from chugg.progress import (
    DEFAULT_PREFERENCES,
    merge_progress,
    now_ms,
    parse_backup,
    record_result,
    validate_preferences,
)


class Snapshot(TypedDict):
    progress: list[LineProgress]
    preferences: Preferences | None


class Repository:
    def __init__(self, host: Host, proxy: ProxyFactory) -> None:
        self.host = host
        self.proxy = proxy

    async def snapshot(self) -> Snapshot:
        return cast(Snapshot, json.loads(await self.host.snapshot()))

    async def mutate(self, operation: Callable[[Snapshot], Snapshot]) -> Snapshot:
        def apply(text: str) -> str:
            return json.dumps(operation(cast(Snapshot, json.loads(text))))

        callback = self.proxy(apply)
        try:
            return cast(Snapshot, json.loads(await self.host.transact(callback)))
        finally:
            callback.destroy()

    async def record(self, result: DrillResult) -> Snapshot:
        def apply(snapshot: Snapshot) -> Snapshot:
            key = result["lineId"], result["side"]
            previous = next(
                (row for row in snapshot["progress"] if (row["lineId"], row["side"]) == key), None
            )
            saved = record_result(result, previous)
            return {
                **snapshot,
                "progress": [
                    row for row in snapshot["progress"] if (row["lineId"], row["side"]) != key
                ]
                + [saved],
            }

        return await self.mutate(apply)

    async def save_preferences(self, preferences: Preferences) -> None:
        validated = validate_preferences(preferences)
        await self.mutate(lambda snapshot: {**snapshot, "preferences": validated})

    async def export(self) -> str:
        snapshot = await self.snapshot()
        backup: Backup = {
            "app": "chugg",
            "version": 1,
            "exportedAt": now_ms(),
            "preferences": snapshot["preferences"] or DEFAULT_PREFERENCES.copy(),
            "progress": snapshot["progress"],
        }
        return json.dumps(backup, indent=2, ensure_ascii=False)

    async def import_text(self, text: str) -> Snapshot:
        backup = parse_backup(text)

        def apply(snapshot: Snapshot) -> Snapshot:
            rows = {(row["lineId"], row["side"]): row for row in snapshot["progress"]}
            for incoming in backup["progress"]:
                key = incoming["lineId"], incoming["side"]
                rows[key] = merge_progress(rows.get(key), incoming)
            return {
                "progress": list(rows.values()),
                "preferences": snapshot["preferences"] or backup["preferences"],
            }

        return await self.mutate(apply)
