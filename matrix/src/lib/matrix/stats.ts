/**
 * Behavioral Matrix — real statistics engine.
 * Pure deterministic math on real corpus outcomes. No random numbers are
 * ever used except inside the seeded bootstrap (a Monte-Carlo procedure
 * applied to REAL observed outcomes — the same methodology as the repo's
 * power analysis), and that generator is seeded for full reproducibility.
 */

export interface WilsonInterval {
  low: number;
  high: number;
}

/** Wilson score interval for a binomial proportion. */
export function wilsonInterval(k: number, n: number, z = 1.96): WilsonInterval {
  if (n === 0) return { low: 0, high: 0 };
  const p = k / n;
  const z2 = z * z;
  const denom = 1 + z2 / n;
  const centre = p + z2 / (2 * n);
  const margin = z * Math.sqrt((p * (1 - p) + z2 / (4 * n)) / n);
  return {
    low: Math.max(0, (centre - margin) / denom),
    high: Math.min(1, (centre + margin) / denom),
  };
}

/** Mean of a numeric sample. */
export function mean(xs: number[]): number {
  if (xs.length === 0) return 0;
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

/** Sample standard deviation. */
export function stdev(xs: number[]): number {
  if (xs.length < 2) return 0;
  const m = mean(xs);
  return Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / (xs.length - 1));
}

/**
 * Two-proportion z-score: a sub-group rate vs the corpus baseline.
 * Positive = the group affirms MORE than the baseline.
 */
export function zScoreVersusBaseline(
  k: number,
  n: number,
  baseK: number,
  baseN: number,
): number {
  if (n === 0 || baseN === 0) return 0;
  const p = baseK / baseN;
  const se = Math.sqrt((p * (1 - p)) / n);
  if (se === 0) return 0;
  return (k / n - p) / se;
}

// ---------------------------------------------------------------------------
// Seeded PRNG (mulberry32) — deterministic bootstrap machinery.
// ---------------------------------------------------------------------------

/** Deterministic 32-bit string hash (FNV-1a) — used to seed bootstraps from
 * the filter definition so any simulation is reproducible bit-for-bit. */
export function fnv1aHash(input: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface BootstrapResult {
  iterations: number;
  n: number;
  observed: number; // observed proportion in the real sample
  mean: number;
  median: number;
  p05: number;
  p25: number;
  p75: number;
  p95: number;
  histogram: { binStart: number; binEnd: number; count: number }[];
}

/**
 * Nonparametric bootstrap of a proportion over REAL binary outcomes.
 * outcomes[i] = 1 (affirmed) | 0 (reversed/vacated). The resampling acts on
 * the observed sample only — nothing is invented.
 */
export function bootstrapProportion(
  outcomes: number[],
  iterations: number,
  seed: number,
  bins = 40,
): BootstrapResult {
  const n = outcomes.length;
  if (n === 0) {
    return {
      iterations, n: 0, observed: 0, mean: 0, median: 0,
      p05: 0, p25: 0, p75: 0, p95: 0, histogram: [],
    };
  }
  const rand = mulberry32(seed);
  const means: number[] = new Array(iterations);
  for (let it = 0; it < iterations; it++) {
    let sum = 0;
    for (let i = 0; i < n; i++) {
      // integer floor sampling of the real outcomes array
      sum += outcomes[(rand() * n) | 0];
    }
    means[it] = sum / n;
  }
  means.sort((a, b) => a - b);
  const q = (p: number) => means[Math.min(means.length - 1, Math.floor(p * means.length))];
  const observed = outcomes.reduce((a, b) => a + b, 0) / n;

  const histogram: { binStart: number; binEnd: number; count: number }[] = [];
  const binW = 1 / bins;
  for (let b = 0; b < bins; b++) {
    histogram.push({ binStart: b * binW, binEnd: (b + 1) * binW, count: 0 });
  }
  for (const m of means) {
    const idx = Math.min(bins - 1, Math.floor(m / binW));
    histogram[idx].count += 1;
  }
  return {
    iterations,
    n,
    observed,
    mean: mean(means),
    median: q(0.5),
    p05: q(0.05),
    p25: q(0.25),
    p75: q(0.75),
    p95: q(0.95),
    histogram,
  };
}

/** Percentile rank of a value within a sample (0..100). */
export function percentileRank(sample: number[], value: number): number {
  if (sample.length === 0) return 0;
  let below = 0;
  for (const s of sample) if (s <= value) below += 1;
  return (below / sample.length) * 100;
}

export function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

export function round(v: number, digits = 4): number {
  const f = 10 ** digits;
  return Math.round(v * f) / f;
}
