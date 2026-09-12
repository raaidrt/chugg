import chess
import pytest

from chugg.catalog import openings
from chugg.models import Side
from chugg.trainer import Drill, check_move, notation, player_move_count, position_at

ITALIAN = ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5"]


def test_positions_and_verdicts_do_not_mutate_board() -> None:
    board = position_at(ITALIAN, 3)
    assert [move.uci() for move in board.move_stack] == ITALIAN[:3]
    board = chess.Board()
    for source, destination, expected in [
        ("e2", "e4", "correct"),
        ("d2", "d4", "different"),
        ("e2", "e5", "illegal"),
        ("e7", "e5", "illegal"),
    ]:
        assert check_move(board, source, destination, ITALIAN[0]) == expected
    assert board.fen() == chess.Board().fen()
    assert not board.move_stack


def test_castling_capture_en_passant_and_checks() -> None:
    board = position_at(ITALIAN, 6)
    assert check_move(board, "e1", "g1", "e1g1") == "correct"
    board = position_at([*ITALIAN, "e1g1"], 7)
    assert board.piece_at(chess.G1) == chess.Piece(chess.KING, chess.WHITE)
    assert board.piece_at(chess.F1) == chess.Piece(chess.ROOK, chess.WHITE)
    assert board.piece_at(chess.H1) is None
    assert notation([*ITALIAN, "e1g1"]) == "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O"
    assert notation(["e2e4", "d7d5", "e4d5", "d8d5"]) == "1. e4 d5 2. exd5 Qxd5"
    board = position_at(["e2e4", "a7a6", "e4e5", "d7d5", "e5d6"], 5)
    assert board.piece_at(chess.D6) == chess.Piece(chess.PAWN, chess.WHITE)
    assert board.piece_at(chess.D5) is None
    assert (
        notation(["e2e4", "e7e5", "f1c4", "d7d6", "d1h5", "g8f6", "h5f7"])
        == "1. e4 e5 2. Bc4 d6 3. Qh5 Nf6 4. Qxf7#"
    )
    assert notation([]) == ""


def test_exact_promotion_required() -> None:
    board = chess.Board("7k/P7/8/8/8/8/8/7K w - - 0 1")
    assert check_move(board, "a7", "a8", "a7a8n", "n") == "correct"
    assert check_move(board, "a7", "a8", "a7a8n", "q") == "different"
    assert check_move(board, "a7", "a8", "a7a8n") == "illegal"


@pytest.mark.parametrize("side", ["w", "b"])
def test_all_drills_complete_for_both_sides(side: Side) -> None:
    for line in openings:
        drill = Drill(line, side)
        assert not drill.own_turn
        drill.select("e2")
        assert drill.selected is None
        drill.introducing = False
        while not drill.done:
            if drill.own_turn:
                uci = line["moves"][drill.ply]
                drill.select(uci[:2])
                assert uci[2:4] in drill.destinations
                drill.select(uci[2:4])
                if drill.promotion:
                    drill.attempt(*drill.promotion, uci[4:])
            else:
                drill.reply()
        assert drill.mistakes == drill.hints == 0
        assert player_move_count(line["moves"], side, drill.ply) == player_move_count(
            line["moves"], side
        )


def test_hints_errors_selection_and_odd_endings() -> None:
    drill = Drill(openings[1], "w", introducing=False)
    drill.select("e4")
    assert drill.message == "Pick one of your pieces first."
    drill.select("e2")
    drill.select("e2")
    assert drill.selected is None
    drill.select("e2")
    drill.select("e5")
    assert drill.mistakes == 1 and drill.message == "Illegal move."
    drill.select("d2")
    drill.select("d4")
    assert drill.mistakes == 2 and drill.message == "Not this line. Try again."
    drill.show_hint()
    drill.show_hint()
    assert drill.hints == 1 and drill.message == "Play e4."
    drill.select("e2")
    drill.select("e4")
    assert drill.ply == 1 and not drill.hint and not drill.own_turn
    drill.show_hint()
    assert drill.hints == 1
    assert player_move_count([*ITALIAN, "e1g1"], "w") == 4
    assert player_move_count([*ITALIAN, "e1g1"], "b") == 3
    assert player_move_count(ITALIAN, "b", 1) == 0
    assert player_move_count(ITALIAN, "w", 5) == 3
