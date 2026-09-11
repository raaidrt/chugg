import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowDownToLine,
  ArrowRight,
  BookOpen,
  ChartNoAxesColumnIncreasing,
  Check,
  ChevronRight,
  CircleHelp,
  Layers,
  Search,
  Settings2,
  ShieldCheck,
  Shuffle,
  Sparkles,
  Target,
  X,
} from 'lucide-react';
import { openings, catalogMetadata } from './data/catalog';
import { sampleOpening } from './lib/sampling';
import { loadPreferences, loadProgress, recordResult, savePreferences } from './lib/progress';
import { playerMoveCount, positionAt } from './lib/trainer';
import type { DrillResult, LineProgress, OpeningLine, Preferences, Side } from './types';
import { ChessBoard } from './components/ChessBoard';
import { Trainer } from './components/Trainer';
import { InstallGuide, isStandalone } from './components/InstallGuide';
import { DataSettings } from './components/DataSettings';
import { DeviceDialog } from './components/DeviceDialog';
import { OfflineStatus } from './components/OfflineStatus';
import './styles.css';

type Page = 'practice' | 'library' | 'progress';
const defaultPreferences: Preferences = { side: 'w', familyId: 'all' };

export default function App() {
  const [page, setPage] = useState<Page>('practice');
  const [preferences, setPreferences] = useState<Preferences>(defaultPreferences);
  const [progress, setProgress] = useState<LineProgress[]>([]);
  const [ready, setReady] = useState(false);
  const [line, setLine] = useState<OpeningLine>(() => sampleOpening(openings) ?? openings[0]);
  const [recentIds, setRecentIds] = useState<string[]>([]);
  const [training, setTraining] = useState(false);
  const [session, setSession] = useState(0);
  const [dialog, setDialog] = useState<'install' | 'settings' | 'sampling' | null>(null);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [libraryFamily, setLibraryFamily] = useState('');
  const [standalone] = useState(isStandalone);
  const families = useMemo(
    () =>
      Array.from(new Map(openings.map((item) => [item.familyId, item.family])).entries()).sort(
        (a, b) => a[1].localeCompare(b[1]),
      ),
    [],
  );

  useEffect(() => {
    let active = true;
    void Promise.all([loadPreferences(), loadProgress()])
      .then(([prefs, saved]) => {
        if (!active) return;
        const normalized = {
          ...prefs,
          familyId: families.some(([id]) => id === prefs.familyId) ? prefs.familyId : 'all',
        };
        setPreferences(normalized);
        setProgress(saved);
        setLine(
          sampleOpening(openings, {
            familyId: normalized.familyId === 'all' ? undefined : normalized.familyId,
          }) ?? openings[0],
        );
      })
      .catch(() => {
        if (active)
          setError(
            'Device storage is unavailable. You can practice, but progress may not be saved.',
          );
      })
      .finally(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, [families]);

  function changePreferences(next: Preferences) {
    setPreferences(next);
    void savePreferences(next).catch(() =>
      setError('We couldn’t save your preferences on this device.'),
    );
  }
  function chooseSide(side: Side) {
    changePreferences({ ...preferences, side });
  }
  function shuffle(familyId = preferences.familyId) {
    const next = sampleOpening(openings, {
      familyId: familyId === 'all' ? undefined : familyId,
      recentIds: [line.id, ...recentIds].slice(0, 5),
    });
    if (next) {
      setRecentIds((ids) => [line.id, ...ids].slice(0, 5));
      setLine(next);
    }
  }
  function selectFamily(familyId: string) {
    changePreferences({ ...preferences, familyId });
    shuffle(familyId);
  }
  function openLine(item: OpeningLine) {
    setLine(item);
    setPage('practice');
    setTraining(false);
    window.scrollTo({ top: 0 });
  }
  function navigate(next: Page) {
    setTraining(false);
    setPage(next);
    window.scrollTo({ top: 0 });
  }
  function start() {
    setSession((value) => value + 1);
    setTraining(true);
    window.scrollTo({ top: 0 });
  }
  const saveResult = useCallback((result: DrillResult) => {
    void recordResult(result)
      .then((saved) =>
        setProgress((items) => [
          ...items.filter((item) => !(item.lineId === saved.lineId && item.side === saved.side)),
          saved,
        ]),
      )
      .catch(() =>
        setError(
          'Your line is complete, but we couldn’t save this result. Export a backup from Settings if device storage is full.',
        ),
      );
  }, []);
  async function refresh() {
    try {
      const [prefs, saved] = await Promise.all([loadPreferences(), loadProgress()]);
      setPreferences({
        ...prefs,
        familyId: families.some(([id]) => id === prefs.familyId) ? prefs.familyId : 'all',
      });
      setProgress(saved);
    } catch {
      setError('We couldn’t load your imported progress. Please try again.');
    }
  }
  const totalSessions = progress.reduce((total, item) => total + item.completions, 0);
  const cleanSessions = progress.reduce((total, item) => total + item.cleanCompletions, 0);
  const uniqueLines = new Set(progress.map((item) => item.lineId)).size;
  const lineProgress = progress.find(
    (item) => item.lineId === line.id && item.side === preferences.side,
  );
  const previewGame = useMemo(() => positionAt(line.moves, Math.min(line.moves.length, 6)), [line]);
  const filtered = openings.filter(
    (item) =>
      (!libraryFamily || item.familyId === libraryFamily) &&
      `${item.name} ${item.family} ${item.eco}`.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="header-inner">
          <button className="brand" onClick={() => navigate('practice')} aria-label="Chugg home">
            <span className="brand-icon" aria-hidden="true">
              ♞
            </span>
            chugg<span className="brand-dot">.</span>
          </button>
          <nav className="main-nav" aria-label="Main navigation">
            {(
              [
                { id: 'practice', label: 'Practice', icon: Target },
                { id: 'library', label: 'Openings', icon: BookOpen },
                { id: 'progress', label: 'Your progress', icon: ChartNoAxesColumnIncreasing },
              ] as const
            ).map((item) => (
              <button
                key={item.id}
                className={page === item.id ? 'active' : ''}
                aria-current={page === item.id ? 'page' : undefined}
                onClick={() => navigate(item.id)}
              >
                <item.icon size={17} />
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
          <button
            className="icon-button settings-button"
            onClick={() => setDialog('settings')}
            aria-label="Settings and backups"
          >
            <Settings2 size={20} />
          </button>
        </div>
      </header>
      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button
            className="icon-button"
            onClick={() => setError('')}
            aria-label="Dismiss notification"
          >
            <X size={16} />
          </button>
        </div>
      )}
      {training ? (
        <Trainer
          key={`${line.id}-${preferences.side}-${session}`}
          line={line}
          side={preferences.side}
          onComplete={saveResult}
          onExit={() => setTraining(false)}
          onNext={() => {
            shuffle();
            setTraining(false);
          }}
        />
      ) : (
        <>
          {page === 'practice' && (
            <main className="home-page page-enter">
              <section className="hero-copy">
                <div className="eyebrow">
                  <span className="tiny-diamond" /> A little practice. A better opening.
                </div>
                <h1>
                  Make your next
                  <br />
                  move <em>familiar.</em>
                </h1>
                <p className="hero-description">
                  Learn the opening. Recall the moves.
                  <br className="desktop-break" /> Build a repertoire that stays with you.
                </p>
                <div className="practice-controls">
                  <div className="control-heading">
                    <label htmlFor="opening-family">Your practice</label>
                    <button className="info-button" onClick={() => setDialog('sampling')}>
                      <CircleHelp size={14} /> How we pick
                    </button>
                  </div>
                  <select
                    id="opening-family"
                    value={preferences.familyId}
                    onChange={(event) => selectFamily(event.target.value)}
                    disabled={!ready}
                  >
                    <option value="all">All opening families</option>
                    {families.map(([id, name]) => (
                      <option key={id} value={id}>
                        {name}
                      </option>
                    ))}
                  </select>
                  <span className="field-label" id="side-label">
                    I’m playing as
                  </span>
                  <div className="side-switch" role="group" aria-labelledby="side-label">
                    <button
                      aria-pressed={preferences.side === 'w'}
                      disabled={!ready}
                      onClick={() => chooseSide('w')}
                    >
                      <img src={`${import.meta.env.BASE_URL}piece/maestro/wK.svg`} alt="" /> White{' '}
                      <span>You move first</span>
                      {preferences.side === 'w' && <Check size={16} />}
                    </button>
                    <button
                      aria-pressed={preferences.side === 'b'}
                      disabled={!ready}
                      onClick={() => chooseSide('b')}
                    >
                      <img src={`${import.meta.env.BASE_URL}piece/maestro/bK.svg`} alt="" /> Black{' '}
                      <span>Chugg moves first</span>
                      {preferences.side === 'b' && <Check size={16} />}
                    </button>
                  </div>
                  <div className="opening-intro">
                    <div className="opening-intro-top">
                      <span className="eyebrow">Up next · {line.eco}</span>
                      <button
                        className="text-button shuffle-button"
                        onClick={() => shuffle()}
                        disabled={!ready}
                        aria-label="Pick another opening"
                      >
                        <Shuffle size={15} /> Shuffle
                      </button>
                    </div>
                    <h2>{line.name}</h2>
                    <p>
                      {playerMoveCount(line.moves, preferences.side)} moves to recall <span>·</span>{' '}
                      {lineProgress?.completions
                        ? `${lineProgress.completions} ${lineProgress.completions === 1 ? 'practice' : 'practices'}`
                        : 'A fresh line to learn'}
                    </p>
                  </div>
                  <button className="primary-button start-button" disabled={!ready} onClick={start}>
                    {ready ? 'Practice this opening' : 'Getting your board ready…'}
                    <ArrowRight size={19} />
                  </button>
                  <p className="practice-footnote">
                    <ShieldCheck size={14} /> No account. No clock. Just your next move.
                  </p>
                </div>
              </section>
              <section className="hero-board-section" aria-label="Opening preview">
                <div className="board-top-label">
                  <span>
                    <span className="live-dot" /> YOUR REPERTOIRE STARTS HERE
                  </span>
                  <span>01 / ∞</span>
                </div>
                <div className="preview-board">
                  <ChessBoard
                    game={previewGame}
                    side={preferences.side}
                    lastMove={line.moves[Math.min(line.moves.length, 6) - 1]}
                  />
                </div>
                <div className="preview-caption">
                  <span>
                    <Layers size={17} /> Preview after {Math.min(line.moves.length, 6)} half-moves
                  </span>
                  <span>{line.eco}</span>
                </div>
                <div className="board-note">
                  <span className="note-spark">✳</span>
                  <p>
                    The best opening is one
                    <br />
                    <em>you remember.</em>
                  </p>
                </div>
              </section>
              <section className="how-it-works" aria-label="How Chugg works">
                <div>
                  <span className="step-number">01</span>
                  <h3>Meet the variation</h3>
                  <p>Know exactly which line you’re learning.</p>
                </div>
                <div>
                  <span className="step-number">02</span>
                  <h3>Find your moves</h3>
                  <p>You play one side. Chugg plays the other.</p>
                </div>
                <div>
                  <span className="step-number">03</span>
                  <h3>Make it stick</h3>
                  <p>Repeat a line. Build a little confidence.</p>
                </div>
              </section>
            </main>
          )}
          {page === 'library' && (
            <main className="collection-page page-enter">
              <div className="page-heading">
                <div>
                  <div className="eyebrow">Build your repertoire</div>
                  <h1>A world of openings.</h1>
                  <p>Find a familiar favorite. Make a new one.</p>
                </div>
                <span className="count-pill">{openings.length} variations</span>
              </div>
              <div className="library-tools">
                <label className="search-field">
                  <Search size={18} />
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search opening, variation, or ECO…"
                    aria-label="Search openings"
                  />
                </label>
                <select
                  aria-label="Filter opening family"
                  value={libraryFamily}
                  onChange={(event) => setLibraryFamily(event.target.value)}
                >
                  <option value="">All families</option>
                  {families.map(([id, name]) => (
                    <option key={id} value={id}>
                      {name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="library-grid">
                {filtered.map((item) => {
                  const learned = progress.some((entry) => entry.lineId === item.id);
                  return (
                    <button className="library-card" key={item.id} onClick={() => openLine(item)}>
                      <div className="library-card-top">
                        <span className="eco-tag">{item.eco}</span>
                        {learned ? (
                          <span className="practiced-label">
                            <Check size={13} /> Practiced
                          </span>
                        ) : (
                          <span className="small-muted">{item.family}</span>
                        )}
                      </div>
                      <h2>{item.name}</h2>
                      <p>{item.description}</p>
                      <div className="library-card-bottom">
                        <span>
                          {playerMoveCount(item.moves, preferences.side)} moves as{' '}
                          {preferences.side === 'w' ? 'White' : 'Black'}
                        </span>
                        <ArrowRight size={18} />
                      </div>
                    </button>
                  );
                })}
              </div>
              {!filtered.length && (
                <div className="empty-state">
                  <Search size={28} />
                  <h2>No matching openings</h2>
                  <p>Try another name or choose a different family.</p>
                  <button
                    className="secondary-button"
                    onClick={() => {
                      setQuery('');
                      setLibraryFamily('');
                    }}
                  >
                    Clear filters
                  </button>
                </div>
              )}
            </main>
          )}
          {page === 'progress' && (
            <main className="collection-page progress-page page-enter">
              <div className="page-heading">
                <div>
                  <div className="eyebrow">Little by little</div>
                  <h1>Your repertoire, growing.</h1>
                  <p>Every line you practice is another place to feel at home.</p>
                </div>
                <Sparkles size={32} strokeWidth={1.3} />
              </div>
              <div className="stat-grid">
                <div>
                  <span>Practice sessions</span>
                  <strong>{totalSessions}</strong>
                  <p>One completed line at a time</p>
                </div>
                <div>
                  <span>Variations explored</span>
                  <strong>
                    {uniqueLines}
                    <small> / {openings.length}</small>
                  </strong>
                  <p>A wider world of possibilities</p>
                </div>
                <div>
                  <span>Clean recalls</span>
                  <strong>{cleanSessions}</strong>
                  <p>Completed without hints or retries</p>
                </div>
              </div>
              {progress.length ? (
                <section className="recent-practice">
                  <div className="section-heading">
                    <h2>Your practiced lines</h2>
                    <span className="small-muted">White and Black tracked separately</span>
                  </div>
                  {[...progress]
                    .sort((a, b) => b.lastCompletedAt - a.lastCompletedAt)
                    .map((item) => {
                      const opening = openings.find((entry) => entry.id === item.lineId);
                      return (
                        <button
                          key={`${item.lineId}-${item.side}`}
                          className="progress-row"
                          disabled={!opening}
                          onClick={() => {
                            if (opening) {
                              chooseSide(item.side);
                              openLine(opening);
                            }
                          }}
                        >
                          <img
                            src={`${import.meta.env.BASE_URL}piece/maestro/${item.side}N.svg`}
                            alt=""
                          />
                          <div>
                            <h3>{opening?.name ?? 'Opening from another catalog'}</h3>
                            <p>
                              {item.side === 'w' ? 'White' : 'Black'} · {item.completions}{' '}
                              {item.completions === 1 ? 'completion' : 'completions'} ·{' '}
                              {item.cleanCompletions} clean
                            </p>
                          </div>
                          <span className="progress-date">
                            {new Date(item.lastCompletedAt).toLocaleDateString(undefined, {
                              month: 'short',
                              day: 'numeric',
                            })}
                          </span>
                          <ChevronRight size={18} />
                        </button>
                      );
                    })}
                </section>
              ) : (
                <div className="empty-state">
                  <div className="empty-piece">
                    <img src={`${import.meta.env.BASE_URL}piece/maestro/wN.svg`} alt="" />
                  </div>
                  <h2>Your first line is waiting.</h2>
                  <p>Complete an opening to start seeing your progress here.</p>
                  <button className="primary-button" onClick={() => navigate('practice')}>
                    Let’s practice <ArrowRight size={18} />
                  </button>
                </div>
              )}
              <p className="local-data-note">
                <ShieldCheck size={16} /> Your progress stays on this device.{' '}
                <button className="text-button" onClick={() => setDialog('settings')}>
                  Manage backups
                </button>
              </p>
            </main>
          )}
          <footer className="site-footer">
            <div>
              <span className="footer-brand">chugg.</span>
              <span>A small habit. A stronger opening.</span>
            </div>
            <div className="footer-actions">
              <OfflineStatus allowUpdate={!training} />
              <a className="text-button" href={`${import.meta.env.BASE_URL}credits.html`}>
                Credits
              </a>
              {!standalone && (
                <button className="text-button" onClick={() => setDialog('install')}>
                  <ArrowDownToLine size={16} /> Install Chugg
                </button>
              )}
            </div>
          </footer>
        </>
      )}
      {dialog === 'install' && <InstallGuide onClose={() => setDialog(null)} />}
      {dialog === 'settings' && (
        <DataSettings
          onClose={() => setDialog(null)}
          onImported={() => {
            void refresh();
          }}
        />
      )}
      {dialog === 'sampling' && <SamplingInfo onClose={() => setDialog(null)} />}
    </div>
  );
}

function SamplingInfo({ onClose }: { onClose: () => void }) {
  return (
    <DeviceDialog title="How Chugg picks your opening" id="sampling-title" onClose={onClose}>
      <p>
        Chugg gives common opening families more weight, then picks a variation within the family.
        We soften the weights so less common lines still get their turn.
      </p>
      <p>
        Our catalog uses <strong>{catalogMetadata.totalGames.toLocaleString()} games</strong> from{' '}
        {catalogMetadata.source}. {catalogMetadata.classifiedGames.toLocaleString()} games matched a
        supported training line.
      </p>
      <p>{catalogMetadata.description}</p>
      <p>
        Recently shown lines are avoided when other choices are available. Choose a family to focus
        your practice, or explore every line in the library.
      </p>
      <a className="device-dialog-help" href={`${import.meta.env.BASE_URL}credits.html`}>
        Catalog sources and credits <ArrowRight size={14} />
      </a>
      <div className="device-dialog-section">
        <button className="primary-button full-width" onClick={onClose}>
          Got it <Check size={17} />
        </button>
      </div>
    </DeviceDialog>
  );
}
