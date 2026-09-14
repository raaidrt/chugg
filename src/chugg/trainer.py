"""Chess rules and drill state, independent of DOM, clocks, and storage."""

from dataclasses import dataclass
from typing import Literal

import chess

from chugg.models import OpeningLine, Side


def position_at(moves: list[str], ply: int) -> chess.Board:
    board = chess.Board()
    for uci in moves[:ply]:
        board.push_uci(uci)
    return board


def player_move_count(moves: list[str], side: Side, ply: int | None = None) -> int:
    return len(moves[:ply][0 if side == "w" else 1 :: 2])


def check_move(
    board: chess.Board, source: str, destination: str, expected: str, promotion: str = ""
) -> Literal["correct", "different", "illegal"]:
    try:
        move = chess.Move.from_uci(source + destination + promotion)
        if move not in board.legal_moves:
            return "illegal"
        return "correct" if move.uci() == expected else "different"
    except ValueError:
        return "illegal"


def notation(moves: list[str]) -> str:
    board = chess.Board()
    result: list[str] = []
    for index, uci in enumerate(moves):
        move = board.parse_uci(uci)
        result.append((f"{index // 2 + 1}. " if index % 2 == 0 else "") + board.san(move))
        board.push(move)
    return " ".join(result)


@dataclass
class Drill:
    line: OpeningLine
    side: Side
    ply: int = 0
    selected: str | None = None
    hints: int = 0
    mistakes: int = 0
    hint: bool = False
    message: str = "Your move."
    promotion: tuple[str, str] | None = None
    introducing: bool = True
    reported: bool = False

    @property
    def board(self) -> chess.Board:
        return position_at(self.line["moves"], self.ply)

    @property
    def done(self) -> bool:
        return self.ply >= len(self.line["moves"])

    @property
    def own_turn(self) -> bool:
        return not self.introducing and not self.done and self.board.turn == (self.side == "w")

    @property
    def destinations(self) -> list[str]:
        return [
            chess.square_name(move.to_square)
            for move in self.board.legal_moves
            if self.selected == chess.square_name(move.from_square)
        ]

    def attempt(self, source: str, destination: str, promotion: str = "") -> None:
        if not self.own_turn:
            return
        verdict = check_move(
            self.board, source, destination, self.line["moves"][self.ply], promotion
        )
        self.promotion = None
        self.selected = None
        if verdict == "correct":
            self.ply += 1
            self.hint = False
            self.message = "Correct."
        else:
            self.mistakes += 1
            self.message = "Illegal move." if verdict == "illegal" else "Not this line. Try again."

    def select(self, square: str) -> None:
        if not self.own_turn or self.promotion:
            return
        piece = self.board.piece_at(chess.parse_square(square))
        if self.selected == square:
            self.selected = None
        elif piece and piece.color == (self.side == "w"):
            self.selected = square
        elif not self.selected:
            self.message = "Pick one of your pieces first."
        else:
            selected_piece = self.board.piece_at(chess.parse_square(self.selected))
            if (
                selected_piece
                and selected_piece.piece_type == chess.PAWN
                and square[1] in "18"
                and square in self.destinations
            ):
                self.promotion = (self.selected, square)
            else:
                self.attempt(self.selected, square)

    def move(self, source: str, destination: str) -> None:
        """Drag-and-drop equivalent of selecting a piece, then its destination."""
        if not self.own_turn or self.promotion or source == destination:
            return
        try:
            piece = self.board.piece_at(chess.parse_square(source))
            landing = chess.parse_square(destination)
        except ValueError:
            return
        if not piece or piece.color != (self.side == "w"):
            return
        self.selected = source
        landed = self.board.piece_at(landing)
        if landed and landed.color == (self.side == "w"):
            self.selected = destination
            return
        if (
            piece.piece_type == chess.PAWN
            and destination[1] in "18"
            and destination in self.destinations
        ):
            self.promotion = (source, destination)
        else:
            self.attempt(source, destination)

    def show_hint(self) -> None:
        if self.own_turn and not self.hint:
            self.hints += 1
            self.hint = True
            self.message = f"Play {notation(self.line['moves'][: self.ply + 1]).split(' ')[-1]}."

    def reply(self) -> None:
        if not self.introducing and not self.done and not self.own_turn:
            self.ply += 1
            self.message = "Your move."
