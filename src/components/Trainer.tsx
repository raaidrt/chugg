import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, Lightbulb, RotateCcw, Sparkles } from 'lucide-react';
import type { Square } from 'chess.js';
import type { DrillResult, OpeningLine, Side } from '../types';
import { checkMove, notation, playerMoveCount, positionAt } from '../lib/trainer';
import { ChessBoard } from './ChessBoard';

interface Props {
  line: OpeningLine;
  side: Side;
  onExit: () => void;
  onNext: () => void;
  onComplete: (result: DrillResult) => void;
}
export function Trainer({ line, side, onExit, onNext, onComplete }: Props) {
  const [ply, setPly] = useState(0);
  const [selected, setSelected] = useState<Square | null>(null);
  const [hints, setHints] = useState(0);
  const [mistakes, setMistakes] = useState(0);
  const [hint, setHint] = useState(false);
  const [message, setMessage] = useState('Tap a piece, then tap its destination.');
  const [promotion, setPromotion] = useState<{ from: Square; to: Square } | null>(null);
  const [round, setRound] = useState(0);
  const reported = useRef(false);
  const game = useMemo(() => positionAt(line.moves, ply), [line.moves, ply]);
  const done = ply >= line.moves.length;
  const ownTurn = !done && game.turn() === side;
  const completed = playerMoveCount(line.moves, side, ply);
  const total = playerMoveCount(line.moves, side);
  const destinations = selected
    ? game.moves({ square: selected, verbose: true }).map((move) => move.to)
    : [];

  useEffect(() => {
    if (done || game.turn() === side) return;
    const timer = window.setTimeout(() => {
      setPly((value) => (value === ply ? value + 1 : value));
      setMessage('Your turn. Find the next move in this variation.');
    }, 650);
    return () => window.clearTimeout(timer);
  }, [ply, done, game, side, round]);

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
      setMessage('That’s it. Keep going.');
    } else {
      setMistakes((value) => value + 1);
      setSelected(null);
      setMessage(
        verdict === 'illegal'
          ? 'That move isn’t legal in this position. Try another square.'
          : 'A legal move, but a different line. Try the next move in this variation.',
      );
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
      setMessage('First select one of your pieces.');
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
        .at(-1)}. The starting and destination squares are highlighted.`,
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
    setMessage('Tap a piece, then tap its destination.');
    setRound((value) => value + 1);
  }

  return (
    <main className="trainer-page page-enter">
      <button className="text-button back-link" onClick={onExit}>
        <ArrowLeft size={17} /> Back to practice
      </button>
      <div className="trainer-layout">
        <section className="training-board-section">
          <div className="player-row">
            <div className="player-name">
              <span className={`side-dot ${side === 'w' ? 'black' : 'white'}`} />
              <span>
                Chugg <small>{side === 'w' ? 'Black' : 'White'}</small>
              </span>
            </div>
            <span className="small-muted">Your practice partner</span>
          </div>
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
                  <h3 id="promotion-heading">Promote your pawn</h3>
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
          <div className="player-row">
            <div className="player-name">
              <span className={`side-dot ${side === 'w' ? 'white' : 'black'}`} />
              <span>
                You <small>{side === 'w' ? 'White' : 'Black'}</small>
              </span>
            </div>
            <span className={`turn-indicator ${ownTurn ? 'active' : ''}`}>
              {done ? 'Line complete' : ownTurn ? 'Your turn' : 'Chugg is moving…'}
            </span>
          </div>
        </section>
        <section className="training-details" aria-label="Drill details">
          <div className="eyebrow">
            {done ? 'A little more familiar' : 'Recall the opening'}{' '}
            <span className="eco-tag">{line.eco}</span>
          </div>
          <h1 className="training-title">{line.name}</h1>
          {done ? (
            <div className="completion page-enter">
              <div className="completion-mark">
                <Check size={28} strokeWidth={1.7} />
              </div>
              <h2>One line closer.</h2>
              <p>
                {hints === 0 && mistakes === 0
                  ? 'Every move from memory. Nicely played.'
                  : 'You’ve completed the line. A little repetition makes it stick.'}
              </p>
              <div className="result-stats">
                <div>
                  <strong>{total}</strong>
                  <span>moves played</span>
                </div>
                <div>
                  <strong>{mistakes}</strong>
                  <span>retries</span>
                </div>
                <div>
                  <strong>{hints}</strong>
                  <span>hints</span>
                </div>
              </div>
              <p className="opening-explanation">{line.description}</p>
              <div className="recap">
                <span className="eyebrow">The complete line</span>
                <p>{notation(line.moves)}</p>
              </div>
              <button className="primary-button" onClick={onNext}>
                Next opening <ArrowRight size={18} />
              </button>
              <button className="secondary-button full-width" onClick={restart}>
                <RotateCcw size={16} /> Practice again
              </button>
            </div>
          ) : (
            <>
              <p className="training-description">
                You’re playing as <strong>{side === 'w' ? 'White' : 'Black'}</strong>. Bring this
                variation to life, one move at a time.
              </p>
              <div className="drill-progress">
                <div>
                  <span>Your moves</span>
                  <strong>
                    {completed} <span>/ {total}</span>
                  </strong>
                </div>
                <div className="progress-track">
                  <span style={{ width: `${total ? (completed / total) * 100 : 0}%` }} />
                </div>
              </div>
              <div className={`feedback ${hint ? 'is-hint' : ''}`} aria-live="polite">
                <Sparkles size={18} />
                <p>{ownTurn ? message : 'Chugg is playing the other side. Your move is next.'}</p>
              </div>
              <button
                className="secondary-button hint-button"
                onClick={showHint}
                disabled={!ownTurn || hint}
              >
                <Lightbulb size={17} /> {hint ? 'Hint shown' : 'Give me a hint'}
              </button>
              <div className="played-moves">
                <span className="eyebrow">Moves so far</span>
                <p>{ply ? notation(line.moves.slice(0, ply)) : 'The board is yours.'}</p>
              </div>
              <p className="quiet-note">Take your time. This is practice.</p>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
