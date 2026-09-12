"""Exact-mainline classifier, preserving the original tournament-counting algorithm."""

import re
from dataclasses import dataclass, field
from typing import TypedDict


class PgnLine(TypedDict):
    id: str
    pgn: str


class Classification(TypedDict):
    counts: dict[str, int]
    totalGames: int
    classifiedGames: int
    skippedGames: int
    unclassifiedGames: int


def mainline_tokens(pgn: str) -> list[str]:
    text: list[str] = []
    depth = 0
    brace = semicolon = header = False
    for char in pgn:
        if semicolon:
            if char == "\n":
                semicolon = False
                text.append(" ")
            continue
        if brace:
            if char == "}":
                brace = False
                text.append(" ")
            continue
        if header:
            if char == "]":
                header = False
                text.append(" ")
            continue
        if char == "{":
            brace = True
            continue
        if char == ";":
            semicolon = True
            continue
        if char == "[":
            header = True
            continue
        if char == "(":
            depth += 1
            text.append(" ")
            continue
        if char == ")":
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            text.append(char)
    clean = re.sub(r"\d+\.(?:\.\.)?", " ", re.sub(r"\$\d+", " ", "".join(text)))
    tokens = [re.sub(r"[+#!?]", "", token).replace("0", "O") for token in clean.split()]
    return [
        token for token in tokens if token and token not in ("1-O", "O-1", "1/2-1/2", "*", "...")
    ]


@dataclass
class Node:
    children: dict[str, Node] = field(default_factory=dict)
    identifier: str | None = None


def classify_pgn(pgn: str, lines: list[PgnLine]) -> Classification:
    root = Node()
    for line in sorted(lines, key=lambda line: line["id"]):
        node = root
        for move in mainline_tokens(line["pgn"]):
            node = node.children.setdefault(move, Node())
        if node.identifier is None:
            node.identifier = line["id"]
    counts = {line["id"]: 0 for line in lines}
    total = classified = skipped = 0
    for game in re.split(r"(?=^\[Event\s)", pgn.removeprefix("\ufeff"), flags=re.MULTILINE):
        if not game.strip():
            continue
        if not re.search(r"^\[Event\s", game, re.MULTILINE):
            raise ValueError("PGN games must have an Event header.")
        total += 1
        if re.search(
            r'^\[(?:SetUp\s+"1"|FEN\s+"|Variant\s+"(?!Standard"|Chess"))', game, re.MULTILINE
        ):
            skipped += 1
            continue
        node = root
        match: str | None = None
        for token in mainline_tokens(game):
            child = node.children.get(token)
            if child is None:
                break
            node = child
            if node.identifier:
                match = node.identifier
        if match:
            counts[match] += 1
            classified += 1
    return {
        "counts": counts,
        "totalGames": total,
        "classifiedGames": classified,
        "skippedGames": skipped,
        "unclassifiedGames": total - classified - skipped,
    }
