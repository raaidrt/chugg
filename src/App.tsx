import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowDownToLine,
  ArrowRight,
  BookOpen,
  ChartNoAxesColumnIncreasing,
  Check,
  ChevronRight,
  CircleHelp,
  Search,
  Menu,
  ShieldCheck,
  X,
} from 'lucide-react';
import { openings, catalogMetadata } from './data/catalog';
import { sampleOpening, sampleSide } from './lib/sampling';
import { loadProgress, recordResult } from './lib/progress';
import type { DrillResult, LineProgress, OpeningLine, Side } from './types';
import { Trainer } from './components/Trainer';
import { InstallGuide, isStandalone } from './components/InstallGuide';
import { DataSettings } from './components/DataSettings';
import { DeviceDialog } from './components/DeviceDialog';
import { OfflineStatus } from './components/OfflineStatus';
import './styles.css';

type Page = 'practice' | 'library' | 'progress';

export default function App() {
  const [page, setPage] = useState<Page>('practice');
  const [side, setSide] = useState<Side>('w');
  const [progress, setProgress] = useState<LineProgress[]>([]);
  const [ready, setReady] = useState(false);
  const [line, setLine] = useState<OpeningLine>(() => sampleOpening(openings) ?? openings[0]);
  const [recentIds, setRecentIds] = useState<string[]>([]);
  const [training, setTraining] = useState(false);
  const [session, setSession] = useState(0);
  const [dialog, setDialog] = useState<'menu' | 'install' | 'settings' | 'sampling' | null>(null);
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
    void loadProgress()
      .then((saved) => {
        if (active) setProgress(saved);
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
  }, []);

  function navigate(next: Page) {
    setTraining(false);
    setPage(next);
    setDialog(null);
    window.scrollTo({ top: 0 });
  }
  function start(item?: OpeningLine) {
    const next = item ?? sampleOpening(openings, { recentIds });
    if (!next) return;
    setLine(next);
    setSide(sampleSide());
    setRecentIds((ids) => [next.id, ...ids].slice(0, 5));
    setSession((value) => value + 1);
    setPage('practice');
    setTraining(true);
    setDialog(null);
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
      const saved = await loadProgress();
      setProgress(saved);
    } catch {
      setError('We couldn’t load your imported progress. Please try again.');
    }
  }
  const totalSessions = progress.reduce((total, item) => total + item.completions, 0);
  const cleanSessions = progress.reduce((total, item) => total + item.cleanCompletions, 0);
  const uniqueLines = new Set(progress.map((item) => item.lineId)).size;
  const filtered = openings.filter(
    (item) =>
      (!libraryFamily || item.familyId === libraryFamily) &&
      `${item.name} ${item.family} ${item.eco}`.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="app-shell" data-training={training}>
      {!training && page !== 'practice' && (
        <header className="site-header">
          <div className="header-inner">
            <button className="brand" onClick={() => navigate('practice')} aria-label="Chugg home">
              Chugg
            </button>
            <button
              className="icon-button"
              onClick={() => setDialog('menu')}
              aria-label="Open menu"
            >
              <Menu size={20} />
            </button>
          </div>
        </header>
      )}
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
          key={`${line.id}-${side}-${session}`}
          line={line}
          side={side}
          onComplete={saveResult}
          onNext={() => start()}
          onExit={() => navigate('practice')}
        />
      ) : (
        <>
          {page === 'practice' && (
            <main className="home-page">
              <button
                className="icon-button home-menu"
                onClick={() => setDialog('menu')}
                aria-label="Open menu"
              >
                <Menu size={22} />
              </button>
              <div className="home-hero">
                <h1 className="home-title">Chugg</h1>
                <button
                  className="primary-button start-button"
                  disabled={!ready}
                  onClick={() => start()}
                >
                  Start
                </button>
              </div>
            </main>
          )}
          {page === 'library' && (
            <main className="collection-page page-enter">
              <div className="page-heading">
                <div>
                  <h1>Openings</h1>
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
                    <button className="library-card" key={item.id} onClick={() => start(item)}>
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
                      <div className="library-card-bottom">
                        <span>Practice opening</span>
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
                  <h1>Your progress</h1>
                </div>
              </div>
              <div className="stat-grid">
                <div>
                  <span>Practice sessions</span>
                  <strong>{totalSessions}</strong>
                </div>
                <div>
                  <span>Variations explored</span>
                  <strong>
                    {uniqueLines}
                    <small> / {openings.length}</small>
                  </strong>
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
                          onClick={() => opening && start(opening)}
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
                  <h2>No completed openings yet</h2>
                  <p>Complete an opening to start seeing your progress here.</p>
                  <button className="primary-button" onClick={() => navigate('practice')}>
                    Practice <ArrowRight size={18} />
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
        </>
      )}
      <div className="update-notice">
        <OfflineStatus allowUpdate={!training} quiet />
      </div>
      {dialog === 'menu' && (
        <DeviceDialog title="Chugg" id="menu-title" onClose={() => setDialog(null)}>
          <nav className="menu-actions" aria-label="Main navigation">
            <button onClick={() => navigate('library')}>
              <BookOpen size={18} /> Openings
            </button>
            <button onClick={() => navigate('progress')}>
              <ChartNoAxesColumnIncreasing size={18} /> Your progress
            </button>
            <button onClick={() => setDialog('settings')}>
              <ShieldCheck size={18} /> Settings and backups
            </button>
            <button onClick={() => setDialog('sampling')}>
              <CircleHelp size={18} /> How openings are picked
            </button>
            {!standalone && (
              <button onClick={() => setDialog('install')}>
                <ArrowDownToLine size={18} /> Install Chugg
              </button>
            )}
            <a href={`${import.meta.env.BASE_URL}credits.html`}>Credits</a>
          </nav>
        </DeviceDialog>
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
        Recently shown lines are avoided when other choices are available. White or Black is chosen
        at random for each new drill. You can also choose an opening from the library.
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
