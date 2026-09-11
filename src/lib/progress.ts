import { openDB, type DBSchema } from 'idb';
import type { DrillResult, LineProgress, Preferences } from '../types';

interface ChuggDB extends DBSchema {
  progress: { key: [string, string]; value: LineProgress };
  settings: { key: string; value: Preferences };
}

export const MAX_BACKUP_BYTES = 2 * 1024 * 1024;
const MAX_RECORDS = 10_000;
const MAX_COUNT = 1_000_000_000;
const DEFAULT_PREFERENCES: Preferences = { side: 'w', familyId: 'all' };
const validId = (value: unknown): value is string =>
  typeof value === 'string' && /^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,159}$/.test(value);
const integer = (value: unknown, max = MAX_COUNT): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 && value <= max;
const timestamp = (value: unknown): value is number => integer(value, Date.now() + 86_400_000);
const object = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);
const exactKeys = (value: Record<string, unknown>, keys: string[]) =>
  Object.keys(value).length === keys.length && keys.every((key) => Object.hasOwn(value, key));

function preferences(value: unknown): Preferences {
  if (
    !object(value) ||
    !exactKeys(value, ['side', 'familyId']) ||
    (value.side !== 'w' && value.side !== 'b') ||
    !validId(value.familyId)
  )
    throw new Error('Invalid backup preferences.');
  return { side: value.side, familyId: value.familyId };
}
function progress(value: unknown): LineProgress {
  if (
    !object(value) ||
    !exactKeys(value, [
      'lineId',
      'side',
      'completions',
      'cleanCompletions',
      'lastCompletedAt',
      'lastMistakes',
      'lastHints',
    ]) ||
    !validId(value.lineId) ||
    (value.side !== 'w' && value.side !== 'b') ||
    !integer(value.completions) ||
    value.completions < 1 ||
    !integer(value.cleanCompletions) ||
    value.cleanCompletions > value.completions ||
    !timestamp(value.lastCompletedAt) ||
    !integer(value.lastMistakes) ||
    !integer(value.lastHints)
  )
    throw new Error('Invalid progress record in backup.');
  return value as unknown as LineProgress;
}
async function database() {
  if (typeof indexedDB === 'undefined')
    throw new Error('Device storage is unavailable. Progress cannot be saved in this browser.');
  return openDB<ChuggDB>('chugg', 1, {
    upgrade(db) {
      db.createObjectStore('progress', { keyPath: ['lineId', 'side'] });
      db.createObjectStore('settings');
    },
    blocking(_current, _blocked, event) {
      (event.target as IDBDatabase)?.close();
    },
  });
}

export async function loadPreferences(): Promise<Preferences> {
  const db = await database();
  try {
    return (await db.get('settings', 'preferences')) ?? { ...DEFAULT_PREFERENCES };
  } finally {
    db.close();
  }
}
export async function savePreferences(value: Preferences): Promise<void> {
  const validated = preferences(value);
  const db = await database();
  try {
    await db.put('settings', validated, 'preferences');
  } finally {
    db.close();
  }
}
export async function loadProgress(): Promise<LineProgress[]> {
  const db = await database();
  try {
    return await db.getAll('progress');
  } finally {
    db.close();
  }
}
export async function recordResult(result: DrillResult): Promise<LineProgress> {
  if (
    !validId(result.lineId) ||
    (result.side !== 'w' && result.side !== 'b') ||
    !integer(result.mistakes) ||
    !integer(result.hints) ||
    !timestamp(result.completedAt)
  )
    throw new Error('Invalid drill result.');
  const db = await database();
  const tx = db.transaction('progress', 'readwrite');
  try {
    const previous = await tx.store.get([result.lineId, result.side]);
    const latest = !previous || result.completedAt >= previous.lastCompletedAt;
    const next: LineProgress = {
      lineId: result.lineId,
      side: result.side,
      completions: Math.min(MAX_COUNT, (previous?.completions ?? 0) + 1),
      cleanCompletions: Math.min(
        MAX_COUNT,
        (previous?.cleanCompletions ?? 0) + (result.mistakes === 0 && result.hints === 0 ? 1 : 0),
      ),
      lastCompletedAt: latest ? result.completedAt : previous.lastCompletedAt,
      lastMistakes: latest ? result.mistakes : previous.lastMistakes,
      lastHints: latest ? result.hints : previous.lastHints,
    };
    await tx.store.put(next);
    await tx.done;
    return next;
  } catch (error) {
    try {
      tx.abort();
    } catch {
      /* The transaction may already have aborted. */
    }
    await tx.done.catch(() => undefined);
    throw error;
  } finally {
    db.close();
  }
}
export async function exportBackup(): Promise<string> {
  const db = await database();
  try {
    const tx = db.transaction(['progress', 'settings'], 'readonly');
    const [records, prefs] = await Promise.all([
      tx.objectStore('progress').getAll(),
      tx.objectStore('settings').get('preferences'),
    ]);
    await tx.done;
    return JSON.stringify(
      {
        app: 'chugg',
        version: 1,
        exportedAt: Date.now(),
        preferences: prefs ?? DEFAULT_PREFERENCES,
        progress: records,
      },
      null,
      2,
    );
  } finally {
    db.close();
  }
}
export async function importBackup(text: string): Promise<void> {
  if (new TextEncoder().encode(text).byteLength > MAX_BACKUP_BYTES)
    throw new Error('This backup is too large. Choose a file smaller than 2 MB.');
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error('This file is not valid JSON. Choose a Chugg backup.');
  }
  if (
    !object(parsed) ||
    !exactKeys(parsed, ['app', 'version', 'exportedAt', 'preferences', 'progress']) ||
    parsed.app !== 'chugg' ||
    parsed.version !== 1 ||
    !timestamp(parsed.exportedAt) ||
    !Array.isArray(parsed.progress) ||
    parsed.progress.length > MAX_RECORDS
  )
    throw new Error('This is not a supported Chugg backup (version 1).');
  const prefs = preferences(parsed.preferences);
  const records = parsed.progress.map(progress);
  const seen = new Set<string>();
  for (const record of records) {
    const key = `${record.lineId}/${record.side}`;
    if (seen.has(key))
      throw new Error('This backup contains duplicate progress records. Nothing was imported.');
    seen.add(key);
  }
  // All input is validated before opening the one atomic write transaction.
  const db = await database();
  const tx = db.transaction(['progress', 'settings'], 'readwrite');
  try {
    const store = tx.objectStore('progress');
    for (const incoming of records) {
      const local = await store.get([incoming.lineId, incoming.side]);
      // A snapshot is never added to another snapshot: repeated imports are idempotent.
      // Preserve newer last-attempt details and the largest observed counters.
      const latest = local && local.lastCompletedAt >= incoming.lastCompletedAt ? local : incoming;
      await store.put({
        ...latest,
        completions: Math.max(local?.completions ?? 0, incoming.completions),
        cleanCompletions: Math.max(local?.cleanCompletions ?? 0, incoming.cleanCompletions),
      });
    }
    // Current device preferences win; restore them only on a fresh device.
    if (!(await tx.objectStore('settings').get('preferences')))
      await tx.objectStore('settings').put(prefs, 'preferences');
    await tx.done;
  } catch (error) {
    try {
      tx.abort();
    } catch {
      /* The transaction may already have aborted. */
    }
    await tx.done.catch(() => undefined);
    throw error;
  } finally {
    db.close();
  }
}
export async function requestPersistence(): Promise<boolean> {
  if (typeof navigator === 'undefined' || !navigator.storage?.persist) return false;
  if (await navigator.storage.persisted()) return true;
  return navigator.storage.persist();
}
