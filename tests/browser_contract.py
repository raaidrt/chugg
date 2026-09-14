"""Run inside real browser CPython/IndexedDB on a dedicated test origin."""

import asyncio
import json
from collections.abc import Awaitable
from pathlib import Path
from typing import Protocol

from chugg.models import DrillResult
from chugg.storage import Repository


class Controls(Protocol):
    def reset(self) -> Awaitable[None]: ...
    def failWrites(self, enabled: bool) -> None: ...
    def unavailable(self, enabled: bool) -> None: ...


async def run(repository: Repository, controls: Controls) -> str:
    checks: list[str] = []

    def result(index: int = 0) -> DrillResult:
        return {
            "lineId": "italian-main",
            "side": "w",
            "mistakes": 0,
            "hints": 0,
            "completedAt": 1700000000000 + index,
        }

    await controls.reset()
    assert await repository.snapshot() == {"progress": [], "preferences": None, "sampled": {}}
    await repository.save_preferences({"side": "b", "familyId": "sicilian"})
    assert (await repository.snapshot())["preferences"] == {"side": "b", "familyId": "sicilian"}
    checks.append("Fresh defaults and preferences persist in IndexedDB")
    await asyncio.gather(*(repository.record(result(index)) for index in range(12)))
    saved = (await repository.snapshot())["progress"][0]
    assert saved["completions"] == saved["cleanCompletions"] == 12
    assert saved["lastCompletedAt"] == 1700000000011
    checks.append("Twelve concurrent completions preserve every increment")
    await repository.record({**result(), "side": "b", "mistakes": 2})
    await repository.record({**result(), "lineId": "sicilian-main", "hints": 1})
    assert len((await repository.snapshot())["progress"]) == 3
    checks.append("Line and side records remain separate; mistakes and hints prevent clean recalls")
    text = await repository.export()
    original = await repository.snapshot()
    await controls.reset()
    await repository.import_text(text)
    await repository.import_text(text)
    assert await repository.snapshot() == original
    checks.append("Export/import roundtrip restores preferences; repeat import is idempotent")
    await repository.record({**result(1000), "mistakes": 3})
    await repository.save_preferences({"side": "w", "familyId": "all"})
    await repository.import_text(text)
    after = await repository.snapshot()
    white = next(
        row for row in after["progress"] if row["lineId"] == "italian-main" and row["side"] == "w"
    )
    assert white["completions"] == 13 and white["lastMistakes"] == 3
    assert after["preferences"] == {"side": "w", "familyId": "all"}
    checks.append("Older snapshots preserve newer local attempts and device preferences")
    await controls.reset()
    legacy = Path("/app/legacy-backup.json").read_text()
    await repository.import_text(legacy)
    assert len((await repository.snapshot())["progress"]) == 2
    checks.append("Backups exported by the original TypeScript app import unchanged")
    before = await repository.snapshot()
    try:
        await repository.import_text(legacy.replace('"lastHints": 0', '"lastHints": -1'))
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid backup accepted")
    assert await repository.snapshot() == before
    checks.append("Invalid later records leave the entire database unchanged")
    await controls.reset()
    controls.failWrites(True)
    try:
        try:
            await repository.import_text(legacy)
        except Exception:
            pass
        else:
            raise AssertionError("Expected settings write failure")
    finally:
        controls.failWrites(False)
    assert (await repository.snapshot())["progress"] == []
    checks.append("A settings write failure rolls back progress writes in the same transaction")
    await controls.reset()
    await asyncio.gather(*(repository.record_sample("italian-main") for _ in range(6)))
    await repository.record_sample("sicilian-main")
    assert (await repository.snapshot())["sampled"] == {"italian-main": 6, "sicilian-main": 1}
    await repository.record(result())
    await repository.import_text(await repository.export())
    assert (await repository.snapshot())["sampled"] == {"italian-main": 6, "sicilian-main": 1}
    checks.append("Concurrent draws are tallied; progress writes and backups leave them intact")
    assert (await repository.reset_samples())["sampled"] == {}
    assert (await repository.snapshot())["sampled"] == {}
    assert len((await repository.snapshot())["progress"]) == 1
    checks.append("Reset clears the sampling history without touching practice progress")
    controls.unavailable(True)
    try:
        for operation in (repository.snapshot(), repository.record(result())):
            try:
                await operation
            except Exception:
                pass
            else:
                raise AssertionError("Unavailable storage silently accepted")
    finally:
        controls.unavailable(False)
    checks.append("Unavailable storage rejects reads and writes")
    return json.dumps(checks)
