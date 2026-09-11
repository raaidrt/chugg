import { describe, expect, it } from 'vitest';
import { Chess } from 'chess.js';
import { checkMove, notation, playerMoveCount, positionAt } from '../src/lib/trainer';

const italian = ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1c4', 'f8c5'];

describe('trainer positions and recalls', () => {
  it('reconstructs only the played prefix, keeping future moves off the board', () => {
    const game = positionAt(italian, 3);
    expect(game.turn()).toBe('b');
    expect(game.get('f3')).toMatchObject({ color: 'w', type: 'n' });
    expect(game.get('b8')).toMatchObject({ color: 'b', type: 'n' });
    expect(game.get('c6')).toBeUndefined();
    expect(game.history()).toEqual(['e4', 'e5', 'Nf3']);
  });

  it('distinguishes a correct move from a legal alternative and an illegal move without changing the position', () => {
    const game = new Chess();
    const before = game.fen();
    expect(checkMove(game, 'e2', 'e4', italian[0])).toBe('correct');
    expect(checkMove(game, 'd2', 'd4', italian[0])).toBe('different');
    expect(checkMove(game, 'e2', 'e5', italian[0])).toBe('illegal');
    expect(checkMove(game, 'e7', 'e5', italian[0])).toBe('illegal');
    expect(game.fen()).toBe(before);
    expect(game.history()).toEqual([]);
  });

  it('moves both king and rook for castling and includes the castle in the recap', () => {
    const game = positionAt(italian, italian.length);
    expect(checkMove(game, 'e1', 'g1', 'e1g1')).toBe('correct');
    const castled = positionAt([...italian, 'e1g1'], 7);
    expect(castled.get('g1')).toMatchObject({ color: 'w', type: 'k' });
    expect(castled.get('f1')).toMatchObject({ color: 'w', type: 'r' });
    expect(castled.get('h1')).toBeUndefined();
    expect(notation([...italian, 'e1g1'])).toBe('1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O');
  });

  it('removes captured pieces and keeps the resulting turn accurate', () => {
    const line = ['e2e4', 'd7d5', 'e4d5', 'd8d5'];
    const game = positionAt(line, 2);
    expect(checkMove(game, 'e4', 'd5', line[2])).toBe('correct');
    const captured = positionAt(line, 4);
    expect(captured.get('d5')).toMatchObject({ color: 'b', type: 'q' });
    expect(captured.get('e4')).toBeUndefined();
    expect(captured.get('d8')).toBeUndefined();
    expect(captured.turn()).toBe('w');
    expect(notation(line)).toBe('1. e4 d5 2. exd5 Qxd5');
  });

  it('handles en passant by removing the pawn from its actual square', () => {
    const line = ['e2e4', 'a7a6', 'e4e5', 'd7d5', 'e5d6'];
    const captured = positionAt(line, line.length);
    expect(captured.get('d6')).toMatchObject({ color: 'w', type: 'p' });
    expect(captured.get('d5')).toBeUndefined();
    expect(captured.get('e5')).toBeUndefined();
  });

  it('counts only player moves for both even and odd line endings', () => {
    expect(playerMoveCount(italian, 'w')).toBe(3);
    expect(playerMoveCount(italian, 'b')).toBe(3);
    const odd = [...italian, 'e1g1'];
    expect(playerMoveCount(odd, 'w')).toBe(4);
    expect(playerMoveCount(odd, 'b')).toBe(3);
    expect(playerMoveCount(odd, 'w', 0)).toBe(0);
    expect(playerMoveCount(odd, 'b', 1)).toBe(0);
    expect(playerMoveCount(odd, 'w', 5)).toBe(3);
    expect(playerMoveCount(odd, 'b', 5)).toBe(2);
  });

  it('requires the recorded promotion piece rather than accepting any legal promotion', () => {
    const game = new Chess('7k/P7/8/8/8/8/8/7K w - - 0 1');
    expect(checkMove(game, 'a7', 'a8', 'a7a8n', 'n')).toBe('correct');
    expect(checkMove(game, 'a7', 'a8', 'a7a8n', 'q')).toBe('different');
    expect(checkMove(game, 'a7', 'a8', 'a7a8n')).toBe('illegal');
    expect(game.get('a7')).toMatchObject({ color: 'w', type: 'p' });
  });

  it('uses legal SAN recap notation including checks', () => {
    const line = ['e2e4', 'e7e5', 'f1c4', 'd7d6', 'd1h5', 'g8f6', 'h5f7'];
    expect(notation(line)).toBe('1. e4 e5 2. Bc4 d6 3. Qh5 Nf6 4. Qxf7#');
    expect(notation([])).toBe('');
  });
});
