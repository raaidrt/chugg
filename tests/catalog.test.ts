import { describe, expect, it } from 'vitest';
import { Chess } from 'chess.js';
import { openings, catalogMetadata } from '../src/data/catalog';
import { classifyPgn, mainlineTokens } from '../scripts/catalog-classifier.mjs';
import selection from '../scripts/catalog-selection.json';
import counts from '../scripts/catalog-counts.json';

describe('bundled opening catalog', () => {
  it('has unique stable IDs and replays every exact upstream sequence legally', () => {
    expect(openings.length).toBeGreaterThanOrEqual(30);
    expect(new Set(openings.map((line) => line.id)).size).toBe(openings.length);
    for (const line of openings) {
      expect(line.id).toMatch(/^[a-z0-9-]+$/);
      expect(line.eco).toMatch(/^[A-E]\d{2}$/);
      const board = new Chess();
      for (const uci of line.moves) {
        expect(uci).toMatch(/^[a-h][1-8][a-h][1-8][qrbn]?$/);
        expect(
          board.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci[4] }),
        ).toBeTruthy();
      }
      const upstream = selection.find((row) => row.id === line.id)!;
      const reference = new Chess();
      reference.loadPgn(upstream.pgn);
      expect(board.fen()).toBe(reference.fen());
      expect(line.name).toBe(upstream.name);
      expect(line.moves.length).toBeGreaterThanOrEqual(3);
    }
  });

  it('accounts for the reference cohort without double-counting games', () => {
    expect(openings.reduce((sum, line) => sum + line.popularity, 0)).toBe(
      catalogMetadata.classifiedGames,
    );
    expect(counts.classifiedGames + counts.unclassifiedGames + counts.skippedGames).toBe(
      counts.totalGames,
    );
    expect(counts.files.reduce((sum, file) => sum + file.games, 0)).toBe(counts.totalGames);
    expect(catalogMetadata.totalGames).toBeGreaterThan(30000);
    expect(catalogMetadata.description).toContain('not online rapid');
  });
});

describe('PGN popularity preprocessing', () => {
  const lines = [
    { id: 'italian', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bc4' },
    { id: 'piano', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5' },
  ];
  it('assigns nested openings only once to the longest matching line', () => {
    const result = classifyPgn('[Event "Test"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 *', lines);
    expect(result.counts).toEqual({ italian: 0, piano: 1 });
    expect(result.classifiedGames).toBe(1);
  });
  it('ignores comments and alternate lines and reports unclassified and setup games', () => {
    const pgn =
      '[Event "A"]\n\n1.e4 {e5} e5 2.Nf3 (2.Bc4 (2.d4)) Nc6 $1 3.Bc4!? Nf6 *\n\n[Event "B"]\n\n1.d4 d5 *\n\n[Event "C"]\n[SetUp "1"]\n\n1.e4 e5 *';
    const result = classifyPgn(pgn, lines);
    expect(result.counts).toEqual({ italian: 1, piano: 0 });
    expect([
      result.totalGames,
      result.classifiedGames,
      result.unclassifiedGames,
      result.skippedGames,
    ]).toEqual([3, 1, 1, 1]);
    expect(mainlineTokens('1. e4 ; e5\n c5 2. Nf3 1-0')).toEqual(['e4', 'c5', 'Nf3']);
  });
  it('resolves duplicate sequence ties independently of catalog order', () => {
    const rows = [
      { id: 'z', pgn: '1. e4' },
      { id: 'a', pgn: '1. e4' },
    ];
    expect(classifyPgn('[Event "Test"]\n\n1.e4 *', rows).counts).toEqual({ z: 0, a: 1 });
  });
});
