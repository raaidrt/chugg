import type { OpeningLine } from '../types';

export const POPULARITY_EXPONENT = 0.7;
export const EXPLORATION_SHARE = 0.05;

export interface SamplingOptions {
  familyId?: string;
  /** Recently completed/selected IDs; omitted whenever another candidate is available. */
  recentIds?: string[];
  rng?: () => number;
}

function validCount(value: number): number {
  return Number.isFinite(value) && value > 0 ? value : 0;
}

/** Temperature-softened frequency, mixed with a uniform exploration component. */
function weightedPick<T>(items: T[], getCount: (item: T) => number, rng: () => number): T {
  const weights = items.map((item) => Math.pow(validCount(getCount(item)), POPULARITY_EXPONENT));
  const total = weights.reduce((sum, value) => sum + value, 0);
  const draw = rng();
  if (!Number.isFinite(draw) || draw < 0 || draw >= 1)
    throw new RangeError('Sampling RNG must return a number in [0, 1).');
  let remaining = draw;
  for (let index = 0; index < items.length; index++) {
    const probability =
      total > 0
        ? ((1 - EXPLORATION_SHARE) * weights[index]) / total + EXPLORATION_SHARE / items.length
        : 1 / items.length;
    remaining -= probability;
    if (remaining < 0) return items[index];
  }
  // Floating-point round-off at the end of the cumulative distribution.
  return items[items.length - 1];
}

/**
 * Draw a family, then one complete fixed line. Disjoint game counts may be summed
 * for family weights; adding a zero-count line cannot boost that family's weight.
 * Cooldown falls back to the filtered pool when every available drill is recent.
 */
export function sampleOpening(
  lines: OpeningLine[],
  options: SamplingOptions = {},
): OpeningLine | undefined {
  const filtered = lines.filter(
    (line) => !options.familyId || options.familyId === 'all' || line.familyId === options.familyId,
  );
  if (!filtered.length) return undefined;
  const recent = new Set(options.recentIds ?? []);
  const fresh = filtered.filter((line) => !recent.has(line.id));
  const pool = fresh.length ? fresh : filtered;
  const families = new Map<string, OpeningLine[]>();
  for (const line of pool) {
    const group = families.get(line.familyId) ?? [];
    group.push(line);
    families.set(line.familyId, group);
  }
  // Preserve full family frequency when cooldown temporarily hides a variation.
  const familyCounts = new Map<string, number>();
  for (const line of filtered)
    familyCounts.set(
      line.familyId,
      (familyCounts.get(line.familyId) ?? 0) + validCount(line.popularity),
    );
  const rng = options.rng ?? Math.random;
  const family = weightedPick([...families.entries()], ([id]) => familyCounts.get(id) ?? 0, rng)[1];
  return weightedPick(family, (line) => line.popularity, rng);
}
