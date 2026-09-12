"""Regenerate the catalog from checked-in selections and measured PGN counts."""

import hashlib
import io
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict, cast

import chess.pgn

from chugg.build import PACKAGE, ROOT
from chugg.classifier import PgnLine, classify_pgn
from chugg.models import Catalog, CatalogMetadata, OpeningLine
from chugg.progress import integer


class Selection(PgnLine):
    familyId: str
    family: str
    name: str
    eco: str


class SourceFile(TypedDict):
    filename: str
    sha256: str
    games: int


class Reference(TypedDict):
    source: str
    description: str
    date: str
    method: str
    totalGames: int
    classifiedGames: int
    skippedGames: int
    unclassifiedGames: int
    files: list[SourceFile]
    counts: dict[str, int]


def generate(selection: list[Selection], reference: Reference) -> Catalog:
    lines: list[OpeningLine] = []
    for row in selection:
        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
        if game is None or game.errors:
            raise ValueError(f"Invalid PGN: {row['id']}")
        moves = [move.uci() for move in game.mainline_moves()]
        count = reference["counts"][row["id"]]
        if not integer(count, 2**53 - 1):
            raise ValueError(f"Invalid count: {row['id']}")
        lines.append(
            {
                "id": row["id"],
                "familyId": row["familyId"],
                "family": row["family"],
                "name": row["name"],
                "eco": row["eco"],
                "moves": moves,
                "popularity": count,
                "description": f"Learn the {len(moves)}-ply sequence to this named position.",
            }
        )
    digest = hashlib.sha256(
        json.dumps(
            {"selection": selection, "reference": reference},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()[:12]
    metadata: CatalogMetadata = {
        "version": "1-" + digest,
        "date": reference["date"],
        "source": reference["source"],
        "description": reference["description"],
        "sourceCommit": "4b8622759e7ae6f93f011cc6c83a3823401ab45e",
        "sourceUrl": "https://github.com/lichess-org/chess-openings/tree/4b8622759e7ae6f93f011cc6c83a3823401ab45e",
        "popularityMethod": reference["method"],
        "totalGames": reference["totalGames"],
        "classifiedGames": reference["classifiedGames"],
        "unclassifiedGames": reference["unclassifiedGames"],
        "skippedGames": reference["skippedGames"],
        "lineCount": len(lines),
        "familyCount": len({line["familyId"] for line in lines}),
    }
    return {"metadata": metadata, "openings": lines}


def build_catalog(paths: list[Path]) -> None:
    selection = cast(
        list[Selection], json.loads((ROOT / "scripts/catalog-selection.json").read_text())
    )
    counts_path = ROOT / "scripts/catalog-counts.json"
    if paths:
        reference: Reference = {
            "source": os.environ.get("CATALOG_SOURCE") or "User-supplied PGN sample",
            "description": os.environ.get("CATALOG_DESCRIPTION")
            or "Exact move-order counts from supplied PGN games; not a population estimate.",
            "date": os.environ.get("CATALOG_DATE") or datetime.now(UTC).date().isoformat(),
            "method": "longest-exact-mainline-prefix",
            "totalGames": 0,
            "classifiedGames": 0,
            "skippedGames": 0,
            "unclassifiedGames": 0,
            "files": [],
            "counts": {line["id"]: 0 for line in selection},
        }
        for path in paths:
            data = path.read_bytes()
            result = classify_pgn(
                data.decode(), [PgnLine(id=row["id"], pgn=row["pgn"]) for row in selection]
            )
            reference["totalGames"] += result["totalGames"]
            reference["classifiedGames"] += result["classifiedGames"]
            reference["skippedGames"] += result["skippedGames"]
            reference["unclassifiedGames"] += result["unclassifiedGames"]
            for identifier, count in result["counts"].items():
                reference["counts"][identifier] += count
            reference["files"].append(
                {
                    "filename": path.name,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "games": result["totalGames"],
                }
            )
        counts_path.write_text(json.dumps(reference, indent=2, ensure_ascii=False) + "\n")
    else:
        reference = cast(Reference, json.loads(counts_path.read_text()))
    catalog = generate(selection, reference)
    (PACKAGE / "data/catalog.json").write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    )
    print(
        f"Generated {len(catalog['openings'])} drills; classified {reference['classifiedGames']}/{reference['totalGames']} source games."
    )
