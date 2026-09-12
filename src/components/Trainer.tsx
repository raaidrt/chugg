import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowRight, Lightbulb, RotateCcw, List, X } from 'lucide-react';
import type { Square } from 'chess.js';
import type { DrillResult, OpeningLine, Side } from '../types';
import { checkMove, notation, playerMoveCount, positionAt } from '../lib/trainer';
import { ChessBoard } from './ChessBoard';
import { DeviceDialog } from './DeviceDialog';

const INTRO_MS = 1000;

interface Props {
  line: OpeningLine;
  side: Side;
  onNext: () => void;
  onExit: () => void;
  onComplete: (result: DrillResult) => void;
}
export function Trainer({ line, side, onNext, onExit, onComplete }: Props) {
  const [showMoves, setShowMoves] = useState(false);
  const [introducing, setIntroducing] = useState(true);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const [ply, setPly] = useState(0);
  const [selected, setSelected] = useState<Square | null>(null);
  const [hints, setHints] = useState(0);
  const [mistakes, setMistakes] = useState(0);
  const [hint, setHint] = useState(false);
  const [message, setMessage] = useState('Your move.');
  const [promotion, setPromotion] = useState<{ from: Square; to: Square } | null>(null);
  const [round, setRound] = useState(0);
  const reported = useRef(false);
  const game = useMemo(() => positionAt(line.moves, ply), [line.moves, ply]);
  const done = ply >= line.moves.length;
  const ownTurn = !introducing && !done && game.turn() === side;
  const completed = playerMoveCount(line.moves, side, ply);
  const total = playerMoveCount(line.moves, side);
  const destinations = selected
    ? game.moves({ square: selected, verbose: true }).map((move) => move.to)
    : [];

  // Show only the opening name for a moment, then reveal the board.
  useEffect(() => {
    const timer = window.setTimeout(() => setIntroducing(false), INTRO_MS);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!introducing) titleRef.current?.focus({ preventScroll: true });
  }, [introducing]);

  useEffect(() => {
    if (introducing || done || game.turn() === side) return;
    const timer = window.setTimeout(() => {
      setPly((value) => (value === ply ? value + 1 : value));
      setMessage('Your move.');
    }, 650);
    return () => window.clearTimeout(timer);
  }, [introducing, ply, done, game, side, round]);

  useEffect(() => {
    if (done && !reported.current) {
      reported.current = true;
      onComplete({ lineId: line.id, side, hints, mistakes, completedAt: Date.now() });
    }
  }, [done, hints, mistakes, line.id, side, onComplete]);

  function attempt(from: Square, to: Square, promoted?: string) {
    if (!ownTurn) return;
    const verdict = checkMove(game, from, to, line.moves[ply], promoted);
    setPromotion(null);
    if (verdict === 'correct') {
      setPly((value) => value + 1);
      setSelected(null);
      setHint(false);
      setMessage('Correct.');
    } else {
      setMistakes((value) => value + 1);
      setSelected(null);
      setMessage(verdict === 'illegal' ? 'Illegal move.' : 'Not this line. Try again.');
    }
  }
  function onSquare(square: Square) {
    if (!ownTurn || promotion) return;
    const piece = game.get(square);
    if (selected === square) {
      setSelected(null);
      return;
    }
    if (piece?.color === side) {
      setSelected(square);
      return;
    }
    if (!selected) {
      setMessage('Pick one of your pieces first.');
      return;
    }
    if (
      game.get(selected)?.type === 'p' &&
      (square[1] === '8' || square[1] === '1') &&
      destinations.includes(square)
    ) {
      setPromotion({ from: selected, to: square });
      return;
    }
    attempt(selected, square);
  }
  function showHint() {
    if (!ownTurn || hint) return;
    setHints((value) => value + 1);
    setHint(true);
    setMessage(
      `Play ${notation(line.moves.slice(0, ply + 1))
        .split(' ')
        .at(-1)}.`,
    );
  }
  function restart() {
    reported.current = false;
    setPly(0);
    setHints(0);
    setMistakes(0);
    setHint(false);
    setSelected(null);
    setPromotion(null);
    setMessage('Your move.');
    setRound((value) => value + 1);
  }

  if (introducing) {
    return (
      <main className="opening-intro" aria-live="polite">
        <h1 className="opening-intro-title">{line.name}</h1>
      </main>
    );
  }

  return (
    <main className="trainer-page" data-complete={done}>
      <header className="training-heading">
        <button className="icon-button trainer-exit" onClick={onExit} aria-label="Back to home">
          <X size={20} />
        </button>
        <div className="training-heading-text">
          <h1 className="training-title" tabIndex={-1} ref={titleRef}>
            {line.name}
          </h1>
          <div className="training-meta">
            <span className="eco-tag">{line.eco}</span>
            <span>{side === 'w' ? 'White' : 'Black'}</span>
            <span className="training-count">
              {completed}/{total}
            </span>
          </div>
        </div>
        <button
          className="icon-button trainer-moves"
          onClick={() => setShowMoves(true)}
          aria-label="View moves"
        >
          <List size={20} />
        </button>
      </header>
      <section className="training-board-section">
        <div className="board-wrap">
          <ChessBoard
            game={game}
            side={side}
            selected={selected}
            destinations={destinations}
            lastMove={line.moves[ply - 1]}
            hint={hint ? line.moves[ply] : undefined}
            interactive={ownTurn && !promotion}
            onSquare={onSquare}
          />
          {promotion && (
            <div className="promotion-overlay">
              <div
                className="promotion-card"
                role="dialog"
                aria-modal="true"
                aria-labelledby="promotion-heading"
              >
                <h3 id="promotion-heading">Promote to</h3>
                <div className="promotion-options">
                  {(['q', 'r', 'b', 'n'] as const).map((piece) => (
                    <button
                      key={piece}
                      aria-label={`Promote to ${{ q: 'queen', r: 'rook', b: 'bishop', n: 'knight' }[piece]}`}
                      onClick={() => attempt(promotion.from, promotion.to, piece)}
                    >
                      <img
                        src={`${import.meta.env.BASE_URL}piece/maestro/${side}${piece.toUpperCase()}.svg`}
                        alt=""
                      />
                    </button>
                  ))}
                </div>
                <button className="text-button" onClick={() => setPromotion(null)}>
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </section>
      <section className="training-details" aria-label="Drill controls">
        <div className="progress-track" aria-hidden="true">
          <span style={{ width: `${total ? (completed / total) * 100 : 0}%` }} />
        </div>
        {done ? (
          <div className="completion-actions">
            <span className="completion-summary">
              Done · {mistakes} {mistakes === 1 ? 'retry' : 'retries'} · {hints}{' '}
              {hints === 1 ? 'hint' : 'hints'}
            </span>
            <button className="secondary-button" onClick={restart} aria-label="Play again">
              <RotateCcw size={16} />
            </button>
            <button className="primary-button next-opening-button" onClick={onNext}>
              Next <ArrowRight size={18} />
            </button>
          </div>
        ) : (
          <div className="drill-actions">
            <div className={`feedback ${hint ? 'is-hint' : ''}`} aria-live="polite">
              <p>{ownTurn ? message : 'Chugg is moving…'}</p>
            </div>
            <button
              className="secondary-button hint-button"
              onClick={showHint}
              disabled={!ownTurn || hint}
            >
              <Lightbulb size={17} /> Hint
            </button>
          </div>
        )}
      </section>
      {showMoves && (
        <DeviceDialog title="Moves" id="moves-title" onClose={() => setShowMoves(false)}>
          <p className="move-notation">
            {ply ? notation(line.moves.slice(0, ply)) : 'No moves yet.'}
          </p>
        </DeviceDialog>
      )}
    </main>
  );
}
