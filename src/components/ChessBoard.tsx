import type { Chess, Square } from 'chess.js';
import type { Side } from '../types';

const names = { p: 'pawn', n: 'knight', b: 'bishop', r: 'rook', q: 'queen', k: 'king' };
interface Props {
  game: Chess;
  side?: Side;
  selected?: Square | null;
  destinations?: Square[];
  lastMove?: string;
  hint?: string;
  interactive?: boolean;
  onSquare?: (square: Square) => void;
}
export function ChessBoard({
  game,
  side = 'w',
  selected,
  destinations = [],
  lastMove,
  hint,
  interactive = false,
  onSquare,
}: Props) {
  const files = (side === 'w' ? 'abcdefgh' : 'hgfedcba').split('');
  const ranks = side === 'w' ? [8, 7, 6, 5, 4, 3, 2, 1] : [1, 2, 3, 4, 5, 6, 7, 8];
  return (
    <div
      className={`chessboard ${interactive ? 'interactive' : ''}`}
      role="group"
      aria-label={`Chessboard, ${side === 'w' ? 'White' : 'Black'} at the bottom. Select a piece, then its destination.`}
    >
      {ranks.flatMap((rank, ri) =>
        files.map((file, fi) => {
          const square = `${file}${rank}` as Square;
          const piece = game.get(square);
          const dark = (file.charCodeAt(0) - 97 + rank) % 2 === 0;
          const isLast = lastMove?.slice(0, 2) === square || lastMove?.slice(2, 4) === square;
          const isHint = hint?.slice(0, 2) === square || hint?.slice(2, 4) === square;
          return (
            <button
              key={square}
              type="button"
              data-testid={`square-${square}`}
              className={`square ${dark ? 'dark' : 'light'} ${selected === square ? 'selected' : ''} ${isLast ? 'last-move' : ''} ${isHint ? 'hinted' : ''}`}
              disabled={!interactive}
              aria-pressed={selected === square}
              aria-label={`${square}, ${piece ? `${piece.color === 'w' ? 'White' : 'Black'} ${names[piece.type]}` : 'empty'}`}
              onClick={() => onSquare?.(square)}
            >
              {piece && (
                <img
                  src={`${import.meta.env.BASE_URL}piece/maestro/${piece.color}${piece.type.toUpperCase()}.svg`}
                  alt=""
                  draggable={false}
                />
              )}
              {destinations.includes(square) && (
                <span className={`destination ${piece ? 'capture' : ''}`} />
              )}
              {fi === 0 && (
                <span className="rank-label" aria-hidden="true">
                  {rank}
                </span>
              )}
              {ri === 7 && (
                <span className="file-label" aria-hidden="true">
                  {file}
                </span>
              )}
            </button>
          );
        }),
      )}
    </div>
  );
}
