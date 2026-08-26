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

// ---------------------------------------------------------------------------
// Experimental protocol statistics (Phase 4)
// ---------------------------------------------------------------------------

/**
 * Brier score for probabilistic binary predictions.
 * Each item: predicted probability of the observed event (0..1) and the
 * realized outcome (0|1). Score = mean squared error; 0 = perfect,
 * 0.25 = the constant-0.5 no-skill prediction.
 */
export function brierScore(
  predictions: { p: number; outcome: 0 | 1 }[],
): number {
  if (predictions.length === 0) return 0;
  return (
    predictions.reduce((a, x) => a + (x.p - x.outcome) ** 2, 0) /
    predictions.length
  );
}

export interface CalibrationBucket {
  // e.g. label "0.60–0.70": AI confidence in this range
  label: string;
  n: number;
  meanConfidence: number; // mean predicted probability in the bucket
  observedRate: number; // observed frequency of the predicted event
}

/**
 * Calibration buckets — reliability diagram data. Predictions are bucketed
 * by confidence into `k` equal-width bins over [0,1]; for each bin we report
 * the mean confidence and the observed event frequency. A perfectly
 * calibrated predictor has observedRate == meanConfidence in every bucket.
 */
export function calibrationBuckets(
  predictions: { p: number; outcome: 0 | 1 }[],
  k = 5,
): CalibrationBucket[] {
  const buckets: CalibrationBucket[] = [];
  for (let b = 0; b < k; b++) {
    const lo = b / k;
    const hi = (b + 1) / k;
    const inBucket = predictions.filter(
      (x) => (b === 0 ? x.p >= lo : x.p > lo) && x.p <= hi,
    );
    const n = inBucket.length;
    buckets.push({
      label: `${lo.toFixed(2)}–${hi.toFixed(2)}`,
      n,
      meanConfidence: n > 0 ? mean(inBucket.map((x) => x.p)) : 0,
      observedRate:
        n > 0 ? inBucket.reduce((a, x) => a + x.outcome, 0) / n : 0,
    });
  }
  return buckets;
}

export interface McNemarResult {
  b: number; // AI wrong, baseline right
  c: number; // AI right, baseline wrong
  exactP: number; // two-sided exact binomial p-value on discordant pairs
}

/**
 * McNemar exact test on paired classifier outcomes (AI vs baseline over the
 * same real cases). b = discordant pairs where only the baseline is right,
 * c = discordant pairs where only the AI is right. The exact two-sided
 * p-value is 2 * P(X <= min(b,c)) with X ~ Binomial(b+c, 0.5), capped at 1.
 */
export function mcnemarExact(b: number, c: number): McNemarResult {
  const n = b + c;
  if (n === 0) return { b, c, exactP: 1 };
  // P(X <= x) for X ~ Bin(n, 0.5): sum of C(n,k) for k <= x, over 2^n.
  // C(n,k) is computed iteratively (exact integer values; the final ratio
  // stays within float64 precision for the n sizes involved here).
  const x = Math.min(b, c);
  let cdf = 0;
  let binom = 1; // C(n,0)
  for (let k = 0; k <= x; k++) {
    if (k > 0) binom = (binom * (n - k + 1)) / k;
    cdf += binom;
  }
  const pLower = cdf / 2 ** n;
  return { b, c, exactP: Math.min(1, 2 * pLower) };
}


export function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

export function round(v: number, digits = 4): number {
  const f = 10 ** digits;
  return Math.round(v * f) / f;
}
