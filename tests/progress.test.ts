import 'fake-indexeddb/auto';
import { deleteDB } from 'idb';
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import {
  exportBackup,
  importBackup,
  loadPreferences,
  loadProgress,
  recordResult,
  savePreferences,
  MAX_BACKUP_BYTES,
} from '../src/lib/progress';
import type { DrillResult } from '../src/types';

const result = (override: Partial<DrillResult> = {}): DrillResult => ({
  lineId: 'italian-main',
  side: 'w',
  mistakes: 0,
  hints: 0,
  completedAt: 1_700_000_000_000,
  ...override,
});
const backupWith = async (changes: Record<string, unknown>) =>
  JSON.stringify({ ...JSON.parse(await exportBackup()), ...changes });
beforeEach(async () => {
  await deleteDB('chugg');
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('device progress', () => {
  it('has fresh defaults and persists preferences', async () => {
    expect(await loadPreferences()).toEqual({ side: 'w', familyId: 'all' });
    await savePreferences({ side: 'b', familyId: 'sicilian' });
    expect(await loadPreferences()).toEqual({ side: 'b', familyId: 'sicilian' });
  });
  it('keeps progress separate by line and side, and clean requires no mistakes or hints', async () => {
    await recordResult(result());
    await recordResult(result({ hints: 1, completedAt: 1_700_000_000_100 }));
    await recordResult(result({ side: 'b', mistakes: 2 }));
    await recordResult(result({ lineId: 'sicilian-main' }));
    const records = await loadProgress();
    expect(records).toHaveLength(3);
    expect(records.find((r) => r.lineId === 'italian-main' && r.side === 'w')).toMatchObject({
      completions: 2,
      cleanCompletions: 1,
      lastHints: 1,
    });
    expect(records.find((r) => r.side === 'b')).toMatchObject({
      completions: 1,
      cleanCompletions: 0,
    });
  });
  it('serializes concurrent completions without losing increments', async () => {
    await Promise.all(
      Array.from({ length: 12 }, (_, i) =>
        recordResult(result({ completedAt: 1_700_000_000_000 + i })),
      ),
    );
    expect((await loadProgress())[0]).toMatchObject({
      completions: 12,
      cleanCompletions: 12,
      lastCompletedAt: 1_700_000_000_011,
    });
  });
  it('retains newest last-attempt details for out of order records', async () => {
    await recordResult(result({ completedAt: 1_700_000_000_500, mistakes: 2 }));
    await recordResult(result());
    expect((await loadProgress())[0]).toMatchObject({
      completions: 2,
      lastMistakes: 2,
      lastCompletedAt: 1_700_000_000_500,
    });
  });
  it('reports unavailable storage rather than pretending to save', async () => {
    vi.stubGlobal('indexedDB', undefined);
    await expect(recordResult(result())).rejects.toThrow('storage is unavailable');
    await expect(loadProgress()).rejects.toThrow('storage is unavailable');
  });
});

describe('backups', () => {
  it('round-trips on a fresh device and repeated import never duplicates counts', async () => {
    await savePreferences({ side: 'b', familyId: 'sicilian' });
    await recordResult(result());
    await recordResult(result({ side: 'b', hints: 1 }));
    const before = await loadProgress();
    const text = await exportBackup();
    await deleteDB('chugg');
    await importBackup(text);
    await importBackup(text);
    expect(await loadProgress()).toEqual(before);
    expect(await loadPreferences()).toEqual({ side: 'b', familyId: 'sicilian' });
  });
  it('preserves newer local progress and existing preferences', async () => {
    await recordResult(result());
    const old = await exportBackup();
    await recordResult(result({ completedAt: 1_700_000_001_000, mistakes: 3 }));
    await savePreferences({ side: 'b', familyId: 'all' });
    await importBackup(old);
    expect((await loadProgress())[0]).toMatchObject({
      completions: 2,
      cleanCompletions: 1,
      lastMistakes: 3,
      lastCompletedAt: 1_700_000_001_000,
    });
    expect((await loadPreferences()).side).toBe('b');
  });
  it('merges snapshot maxima without overwriting newer last-attempt details', async () => {
    await recordResult(result({ completedAt: 1_700_000_001_000, mistakes: 2 }));
    const [existing] = await loadProgress();
    const text = await backupWith({
      progress: [
        {
          ...existing,
          completions: 8,
          cleanCompletions: 5,
          lastCompletedAt: 1_700_000_000_000,
          lastMistakes: 0,
        },
      ],
    });
    await importBackup(text);
    expect((await loadProgress())[0]).toMatchObject({
      completions: 8,
      cleanCompletions: 5,
      lastCompletedAt: 1_700_000_001_000,
      lastMistakes: 2,
    });
  });
  it('validates every row before importing, leaving no partial writes', async () => {
    await recordResult(result());
    const [existing] = await loadProgress();
    const text = await backupWith({
      progress: [
        { ...existing, lineId: 'new-line' },
        { ...existing, completions: -1 },
      ],
    });
    await expect(importBackup(text)).rejects.toThrow('Invalid progress');
    expect(await loadProgress()).toEqual([existing]);
  });
  it('rolls back the whole transaction on a write failure', async () => {
    await recordResult(result());
    const text = await exportBackup();
    await deleteDB('chugg');
    const original = IDBObjectStore.prototype.put;
    vi.spyOn(IDBObjectStore.prototype, 'put').mockImplementation(function (
      this: IDBObjectStore,
      ...args: Parameters<IDBObjectStore['put']>
    ) {
      if (this.name === 'settings') throw new DOMException('Storage full', 'QuotaExceededError');
      return original.apply(this, args);
    });
    await expect(importBackup(text)).rejects.toThrow('Storage full');
    expect(await loadProgress()).toEqual([]);
  });
  it('rejects duplicate line/side keys', async () => {
    await recordResult(result());
    const [existing] = await loadProgress();
    await expect(
      importBackup(await backupWith({ progress: [existing, existing] })),
    ).rejects.toThrow('duplicate');
  });
  it.each([
    { side: 'x' },
    { lineId: '../evil' },
    { cleanCompletions: 2 },
    { lastHints: 0.5 },
    { lastMistakes: Number.MAX_SAFE_INTEGER },
    { lastCompletedAt: 99_999_999_999_999 },
    { extra: true },
  ])('rejects invalid record values %j', async (change) => {
    await recordResult(result());
    const [existing] = await loadProgress();
    await expect(
      importBackup(await backupWith({ progress: [{ ...existing, ...change }] })),
    ).rejects.toThrow('Invalid progress');
  });
  it('rejects wrong versions, malformed JSON, invalid preferences, and oversize files', async () => {
    await expect(importBackup(await backupWith({ version: 2 }))).rejects.toThrow('supported');
    await expect(importBackup('{')).rejects.toThrow('valid JSON');
    await expect(
      importBackup(await backupWith({ preferences: { side: 'w', familyId: '' } })),
    ).rejects.toThrow('preferences');
    await expect(importBackup(' '.repeat(MAX_BACKUP_BYTES + 1))).rejects.toThrow('too large');
  });
});
