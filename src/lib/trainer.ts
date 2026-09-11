import { Chess, type Square } from 'chess.js';
import type { Side } from '../types';

export function positionAt(moves: string[], ply: number): Chess {
  const game = new Chess();
  for (const uci of moves.slice(0, ply)) {
    game.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci[4] });
  }
  return game;
}

export function playerMoveCount(moves: string[], side: Side, ply = moves.length): number {
  return moves.slice(0, ply).filter((_, index) => index % 2 === (side === 'w' ? 0 : 1)).length;
}

export function checkMove(
  game: Chess,
  from: Square,
  to: Square,
  expected: string,
  promotion?: string,
): 'correct' | 'different' | 'illegal' {
  const copy = new Chess(game.fen());
  try {
    const move = copy.move({ from, to, promotion });
    return `${move.from}${move.to}${move.promotion ?? ''}` === expected ? 'correct' : 'different';
  } catch {
    return 'illegal';
  }
}

export function notation(moves: string[]): string {
  const game = positionAt(moves, moves.length);
  return game
    .history()
    .map((move, index) => `${index % 2 === 0 ? `${Math.floor(index / 2) + 1}. ` : ''}${move}`)
    .join(' ');
}
