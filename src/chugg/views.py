"""Escaped HTML presentation; existing class names and assets preserve the visual design."""

import json
from collections.abc import Callable
from html import escape
from pathlib import Path
from typing import cast

import chess

from chugg.catalog import openings
from chugg.models import LineProgress
from chugg.trainer import Drill, notation, player_move_count

ICONS = cast(dict[str, str], json.loads((Path(__file__).parent / "data/icons.json").read_text()))
e = escape


def icon(name: str, size: int = 18) -> str:
    return (
        ICONS[name]
        .replace('width="24"', f'width="{size}"')
        .replace('height="24"', f'height="{size}"')
    )


def button(
    content: str,
    action: str,
    css: str = "",
    *,
    value: str = "",
    label: str = "",
    disabled: bool = False,
    extra: str = "",
) -> str:
    attributes = [
        'type="button"',
        f'class="{e(css)}"',
        f'data-action="{e(action)}"',
        f'data-value="{e(value)}"',
    ]
    if label:
        attributes.append(f'aria-label="{e(label)}"')
    if disabled:
        attributes.append("disabled")
    if extra:
        attributes.append(extra)
    return f"<button {' '.join(attributes)}>{content}</button>"


def home(ready: bool) -> str:
    return (
        f'<main class="home-page">{button(icon("Menu", 22), "menu", "icon-button home-menu", label="Open menu")}<div class="home-hero">'
        f'<h1 class="home-title">Chugg</h1>{button("Start", "start", "primary-button start-button", disabled=not ready)}</div>'
        f"</main>"
    )


def header() -> str:
    return (
        f'<header class="site-header">'
        f'<div class="header-inner">{button("Chugg", "practice", "brand", label="Chugg home")}{button(icon("Menu", 20), "menu", "icon-button", label="Open menu")}</div>'
        f"</header>"
    )


def library(query: str, family: str, progress: list[LineProgress]) -> str:
    families = sorted(
        {row["familyId"]: row["family"] for row in openings}.items(), key=lambda pair: pair[1]
    )
    options = '<option value="">All families</option>' + "".join(
        f'<option value="{e(key)}"{" selected" if key == family else ""}>{e(name)}</option>'
        for key, name in families
    )
    cards: list[str] = []
    for row in openings:
        if (
            family and row["familyId"] != family
        ) or query.lower() not in f"{row['name']} {row['family']} {row['eco']}".lower():
            continue
        learned = any(item["lineId"] == row["id"] for item in progress)
        status = (
            f'<span class="practiced-label">{icon("Check", 13)} Practiced</span>'
            if learned
            else f'<span class="small-muted">{e(row["family"])}</span>'
        )
        cards.append(
            button(
                (
                    f'<div class="library-card-top">'
                    f'<span class="eco-tag">{row["eco"]}</span>{status}</div>'
                    f"<h2>{e(row['name'])}</h2>"
                    f'<div class="library-card-bottom">'
                    f"<span>Practice opening</span>{icon('ArrowRight')}</div>"
                ),
                "start",
                "library-card",
                value=row["id"],
            )
        )
    empty = (
        ""
        if cards
        else (
            f'<div class="empty-state">{icon("Search", 28)}<h2>No matching openings</h2>'
            f"<p>Try another name or choose a different family.</p>{button('Clear filters', 'clear-filters', 'secondary-button')}</div>"
        )
    )
    return (
        f'<main class="collection-page page-enter">'
        f'<div class="page-heading">'
        f"<div>"
        f"<h1>Openings</h1>"
        f"</div>"
        f'<span class="count-pill">{len(openings)} variations</span>'
        f"</div>"
        f'<div class="library-tools">'
        f'<label class="search-field">{icon("Search")}<input data-action="search" value="{e(query)}" placeholder="Search opening, variation, or ECO…" aria-label="Search openings" />'
        f"</label>"
        f'<select data-action="family" aria-label="Filter opening family">{options}</select>'
        f"</div>"
        f'<div class="library-grid">{"".join(cards)}</div>{empty}</main>'
    )


def progress_page(records: list[LineProgress], date: Callable[[int], str]) -> str:
    total = sum(row["completions"] for row in records)
    clean = sum(row["cleanCompletions"] for row in records)
    unique = len({row["lineId"] for row in records})
    content = ""
    if records:
        rows: list[str] = []
        for row in sorted(records, key=lambda item: -item["lastCompletedAt"]):
            opening = next((item for item in openings if item["id"] == row["lineId"]), None)
            side = "White" if row["side"] == "w" else "Black"
            name = opening["name"] if opening else "Opening from another catalog"
            plural = "completion" if row["completions"] == 1 else "completions"
            rows.append(
                button(
                    (
                        f'<img src="piece/maestro/{row["side"]}N.svg" alt=""/>'
                        f"<div>"
                        f"<h3>{e(name)}</h3>"
                        f"<p>{side} · {row['completions']} {plural} · {row['cleanCompletions']} clean</p>"
                        f"</div>"
                        f'<span class="progress-date">{e(date(row["lastCompletedAt"]))}</span>{icon("ChevronRight")}'
                    ),
                    "start",
                    "progress-row",
                    value=row["lineId"],
                    disabled=opening is None,
                )
            )
        content = (
            '<section class="recent-practice"><div class="section-heading"><h2>Your practiced lines</h2><span class="small-muted">White and Black tracked separately</span></div>'
            + "".join(rows)
            + "</section>"
        )
    else:
        content = (
            f'<div class="empty-state">'
            f'<div class="empty-piece">'
            f'<img src="piece/maestro/wN.svg" alt=""/>'
            f"</div>"
            f"<h2>No completed openings yet</h2>"
            f"<p>Complete an opening to start seeing your progress here.</p>{button('Practice ' + icon('ArrowRight'), 'practice', 'primary-button')}</div>"
        )
    return (
        f'<main class="collection-page progress-page page-enter">'
        f'<div class="page-heading">'
        f"<div>"
        f"<h1>Your progress</h1>"
        f"</div>"
        f"</div>"
        f'<div class="stat-grid">'
        f"<div>"
        f"<span>Practice sessions</span>"
        f"<strong>{total}</strong>"
        f"</div>"
        f"<div>"
        f"<span>Variations explored</span>"
        f"<strong>{unique}<small> / {len(openings)}</small>"
        f"</strong>"
        f"</div>"
        f"<div>"
        f"<span>Clean recalls</span>"
        f"<strong>{clean}</strong>"
        f"<p>Completed without hints or retries</p>"
        f"</div>"
        f'</div>{content}<p class="local-data-note">{icon("ShieldCheck", 16)} Your progress stays on this device. {button("Manage backups", "settings", "text-button")}</p>'
        f"</main>"
    )


def chessboard(drill: Drill) -> str:
    files = "abcdefgh" if drill.side == "w" else "hgfedcba"
    ranks = range(8, 0, -1) if drill.side == "w" else range(1, 9)
    board = drill.board
    destinations = drill.destinations
    moves = drill.line["moves"]
    last = moves[drill.ply - 1] if drill.ply else ""
    hint = moves[drill.ply] if drill.hint and not drill.done else ""
    interactive = drill.own_turn and not drill.promotion
    squares: list[str] = []
    for ri, rank in enumerate(ranks):
        for fi, file in enumerate(files):
            square = f"{file}{rank}"
            piece = board.piece_at(chess.parse_square(square))
            classes = ["square", "dark" if (ord(file) - 97 + rank) % 2 == 0 else "light"]
            if square == drill.selected:
                classes.append("selected")
            if square in (last[:2], last[2:4]):
                classes.append("last-move")
            if square in (hint[:2], hint[2:4]):
                classes.append("hinted")
            content = ""
            name = "empty"
            if piece:
                color = "w" if piece.color else "b"
                content = f'<img src="piece/maestro/{color}{piece.symbol().upper()}.svg" alt="" draggable="false"/>'
                name = f"{'White' if piece.color else 'Black'} {chess.piece_name(piece.piece_type)}"
            if square in destinations:
                content += f'<span class="destination{" capture" if piece else ""}"></span>'
            if fi == 0:
                content += f'<span class="rank-label" aria-hidden="true">{rank}</span>'
            if ri == 7:
                content += f'<span class="file-label" aria-hidden="true">{file}</span>'
            squares.append(
                button(
                    content,
                    "square",
                    " ".join(classes),
                    value=square,
                    label=f"{square}, {name}",
                    disabled=not interactive,
                    extra=f'data-testid="square-{square}" aria-pressed="{str(square == drill.selected).lower()}"',
                )
            )
    return f'<div class="chessboard{" interactive" if interactive else ""}" role="group" aria-label="Chessboard, {"White" if drill.side == "w" else "Black"} at the bottom. Select a piece, then its destination.">{"".join(squares)}</div>'


def trainer(drill: Drill) -> str:
    line = drill.line
    if drill.introducing:
        return f'<main class="opening-intro" aria-live="polite"><h1 class="opening-intro-title">{e(line["name"])}</h1></main>'
    completed = player_move_count(line["moves"], drill.side, drill.ply)
    total = player_move_count(line["moves"], drill.side)
    promotion = ""
    if drill.promotion:
        options = "".join(
            button(
                f'<img src="piece/maestro/{drill.side}{piece.upper()}.svg" alt=""/>',
                "promote",
                value=piece,
                label=f"Promote to {name}",
            )
            for piece, name in [("q", "queen"), ("r", "rook"), ("b", "bishop"), ("n", "knight")]
        )
        promotion = (
            f'<div class="promotion-overlay">'
            f'<div class="promotion-card" role="dialog" aria-modal="true" aria-labelledby="promotion-heading">'
            f'<h3 id="promotion-heading">Promote to</h3>'
            f'<div class="promotion-options">{options}</div>{button("Cancel", "cancel-promotion", "text-button")}</div>'
            f"</div>"
        )
    if drill.done:
        actions = (
            f'<div class="completion-actions">'
            f'<span class="completion-summary">Done · {drill.mistakes} {"retry" if drill.mistakes == 1 else "retries"} · {drill.hints} {"hint" if drill.hints == 1 else "hints"}</span>{button(icon("RotateCcw", 16), "replay", "secondary-button", label="Play again")}{button("Next " + icon("ArrowRight"), "start", "primary-button next-opening-button")}</div>'
        )
    else:
        message = drill.message if drill.own_turn else "Chugg is moving…"
        actions = (
            f'<div class="drill-actions">'
            f'<div class="feedback{" is-hint" if drill.hint else ""}" aria-live="polite">'
            f"<p>{e(message)}</p>"
            f"</div>{button(icon('Lightbulb', 17) + ' Hint', 'hint', 'secondary-button hint-button', disabled=not drill.own_turn or drill.hint)}</div>"
        )
    return (
        f'<main class="trainer-page" data-complete="{str(drill.done).lower()}">'
        f'<header class="training-heading">{button(icon("X", 20), "practice", "icon-button trainer-exit", label="Back to home")}<div class="training-heading-text">'
        f'<h1 class="training-title" tabindex="-1">{e(line["name"])}</h1>'
        f'<div class="training-meta">'
        f'<span class="eco-tag">{line["eco"]}</span>'
        f"<span>{'White' if drill.side == 'w' else 'Black'}</span>"
        f'<span class="training-count">{completed}/{total}</span>'
        f"</div>"
        f"</div>{button(icon('List', 20), 'moves', 'icon-button trainer-moves', label='View moves')}</header>"
        f'<section class="training-board-section">'
        f'<div class="board-wrap">{chessboard(drill)}{promotion}</div>'
        f"</section>"
        f'<section class="training-details" aria-label="Drill controls">'
        f'<div class="progress-track" aria-hidden="true">'
        f'<span style="width:{completed / total * 100 if total else 0}%">'
        f"</span>"
        f"</div>{actions}</section>"
        f"</main>"
    )


def moves_dialog(drill: Drill) -> str:
    return f'<p class="move-notation">{e(notation(drill.line["moves"][: drill.ply]) if drill.ply else "No moves yet.")}</p>'
