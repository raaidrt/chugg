/** PGN mainline tokenizer; comments, NAGs and nested alternative lines never train counts. */
export function mainlineTokens(pgn) {
  let text = '',
    variationDepth = 0,
    brace = false,
    semicolon = false,
    header = false;
  for (const c of pgn) {
    if (semicolon) {
      if (c === '\n') {
        semicolon = false;
        text += ' ';
      }
      continue;
    }
    if (brace) {
      if (c === '}') {
        brace = false;
        text += ' ';
      }
      continue;
    }
    if (header) {
      if (c === ']') {
        header = false;
        text += ' ';
      }
      continue;
    }
    if (c === '{') {
      brace = true;
      continue;
    }
    if (c === ';') {
      semicolon = true;
      continue;
    }
    if (c === '[') {
      header = true;
      continue;
    }
    if (c === '(') {
      variationDepth++;
      text += ' ';
      continue;
    }
    if (c === ')') {
      variationDepth = Math.max(0, variationDepth - 1);
      continue;
    }
    if (variationDepth === 0) text += c;
  }
  return text
    .replace(/\$\d+/g, ' ')
    .replace(/\d+\.(?:\.\.)?/g, ' ')
    .split(/\s+/)
    .map((t) => t.replace(/[+#!?]/g, '').replace(/0/g, 'O'))
    .filter((t) => t && !['1-O', 'O-1', '1/2-1/2', '*', '...'].includes(t));
}

export function classifyPgn(pgn, lines) {
  const root = { next: new Map(), id: undefined };
  // Lexicographic ID resolves equal-length duplicate-sequence ties deterministically.
  for (const line of [...lines].sort((a, b) => a.id.localeCompare(b.id))) {
    let node = root;
    for (const move of mainlineTokens(line.pgn)) {
      if (!node.next.has(move)) node.next.set(move, { next: new Map(), id: undefined });
      node = node.next.get(move);
    }
    node.id ??= line.id;
  }
  const counts = Object.fromEntries(lines.map((line) => [line.id, 0]));
  let totalGames = 0,
    classifiedGames = 0,
    skippedGames = 0;
  const games = pgn
    .replace(/^\uFEFF/, '')
    .split(/(?=^\[Event\s)/m)
    .filter((game) => game.trim());
  for (const game of games) {
    if (!/^\[Event\s/m.test(game)) throw new Error('PGN games must have an Event header.');
    totalGames++;
    if (/^\[(?:SetUp\s+"1"|FEN\s+"|Variant\s+"(?!Standard"|Chess"))/m.test(game)) {
      skippedGames++;
      continue;
    }
    let node = root,
      match;
    for (const token of mainlineTokens(game)) {
      node = node.next.get(token);
      if (!node) break;
      if (node.id) match = node.id;
    }
    if (match) {
      counts[match]++;
      classifiedGames++;
    }
  }
  return {
    counts,
    totalGames,
    classifiedGames,
    skippedGames,
    unclassifiedGames: totalGames - classifiedGames - skippedGames,
  };
}
