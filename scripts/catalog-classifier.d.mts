export function mainlineTokens(pgn: string): string[];
export function classifyPgn(
  pgn: string,
  lines: { id: string; pgn: string }[],
): {
  counts: Record<string, number>;
  totalGames: number;
  classifiedGames: number;
  skippedGames: number;
  unclassifiedGames: number;
};
