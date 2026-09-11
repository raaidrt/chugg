import { describe, expect, it } from 'vitest';
import type { OpeningLine } from '../src/types';
import { sampleOpening } from '../src/lib/sampling';

function line(id: string, familyId: string, popularity: number): OpeningLine {
  return {
    id,
    familyId,
    family: familyId,
    popularity,
    name: id,
    eco: 'A00',
    moves: ['e2e4'],
    description: '',
  };
}
function seeded(seed = 2025) {
  return () => {
    seed = (1664525 * seed + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}
function frequencies(lines: OpeningLine[], samples = 40000) {
  const rng = seeded();
  const totals: Record<string, number> = {};
  for (let i = 0; i < samples; i++) {
    const result = sampleOpening(lines, { rng })!;
    totals[result.id] = (totals[result.id] ?? 0) + 1 / samples;
  }
  return totals;
}

describe('opening sampler', () => {
  it('softens real frequency within a family while retaining zero-count exploration', () => {
    const observed = frequencies([
      line('common', 'a', 1000),
      line('rare', 'a', 10),
      line('unseen', 'a', 0),
    ]);
    const sum = 1000 ** 0.7 + 10 ** 0.7;
    expect(observed.common).toBeCloseTo((0.95 * 1000 ** 0.7) / sum + 0.05 / 3, 2);
    expect(observed.rare).toBeCloseTo((0.95 * 10 ** 0.7) / sum + 0.05 / 3, 2);
    expect(observed.unseen).toBeGreaterThan(0.01);
  });

  it('samples families independently of the number of catalog entries', () => {
    const lines = [
      line('a-one', 'a', 100),
      line('b-one', 'b', 100),
      ...Array.from({ length: 12 }, (_, i) => line(`b-${i}`, 'b', 0)),
    ];
    const observed = frequencies(lines);
    expect(observed['a-one']).toBeCloseTo(0.5, 2);
  });

  it('filters before sampling and excludes recent lines while alternatives exist', () => {
    const lines = [line('a', 'x', 5), line('b', 'x', 0), line('c', 'y', 9999)];
    expect(sampleOpening(lines, { familyId: 'x', recentIds: ['a'], rng: () => 0 })?.id).toBe('b');
    expect(sampleOpening(lines, { familyId: 'unknown' })).toBeUndefined();
    expect(sampleOpening([])).toBeUndefined();
    expect(sampleOpening(lines, { familyId: 'x', recentIds: ['a', 'b'], rng: () => 0 })?.id).toBe(
      'a',
    );
  });

  it('falls back to uniform weights if every candidate is unobserved', () => {
    const observed = frequencies([line('a', 'x', 0), line('b', 'x', 0)]);
    expect(observed.a).toBeCloseTo(0.5, 2);
  });

  it('does not mutate its input and rejects broken random sources', () => {
    const lines = Object.freeze([Object.freeze(line('a', 'x', 1))]);
    expect(sampleOpening([...lines], { rng: () => 0.999999 })?.id).toBe('a');
    expect(() => sampleOpening([...lines], { rng: () => 1 })).toThrow(RangeError);
  });
});
