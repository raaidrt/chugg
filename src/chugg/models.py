"""Typed domain objects; camel-case keys deliberately preserve the version 1 wire format."""

from typing import Literal, TypedDict

Side = Literal["w", "b"]


class OpeningLine(TypedDict):
    id: str
    familyId: str
    family: str
    name: str
    eco: str
    moves: list[str]
    popularity: float
    description: str


class DrillResult(TypedDict):
    lineId: str
    side: Side
    mistakes: int
    hints: int
    completedAt: int


class LineProgress(TypedDict):
    lineId: str
    side: Side
    completions: int
    cleanCompletions: int
    lastCompletedAt: int
    lastMistakes: int
    lastHints: int


class Preferences(TypedDict):
    side: Side
    familyId: str


class Backup(TypedDict):
    app: Literal["chugg"]
    version: Literal[1]
    exportedAt: int
    preferences: Preferences
    progress: list[LineProgress]


class CatalogMetadata(TypedDict):
    version: str
    date: str
    source: str
    description: str
    sourceCommit: str
    sourceUrl: str
    popularityMethod: str
    totalGames: int
    classifiedGames: int
    unclassifiedGames: int
    skippedGames: int
    lineCount: int
    familyCount: int


class Catalog(TypedDict):
    metadata: CatalogMetadata
    openings: list[OpeningLine]
