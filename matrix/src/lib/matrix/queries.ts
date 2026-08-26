/**
 * Behavioral Matrix — data access layer.
 * Every function reads the REAL corpus index (SQLite, populated exclusively
 * by scripts/ingest.ts from the legally-subjective Phase 2 corpus) and
 * computes statistics with src/lib/matrix/stats.ts. Nothing here invents,
 * fills, or approximates data: when the index is empty the caller receives
 * `empty: true` and must surface a real waiting state.
 */
import { db } from "@/lib/db";
import {
  wilsonInterval, zScoreVersusBaseline, stdev, mean, round,
  percentileRank, bootstrapProportion, fnv1aHash,
} from "./stats";

export interface EmptyPayload {
  empty: true;
  message: string;
}

export async function corpusIsEmpty(): Promise<boolean> {
  const count = await db.opinion.count();
  return count === 0;
}

export function emptyPayload(message: string): EmptyPayload {
  return { empty: true, message };
}

export const EMPTY_MESSAGE =
  "Index vide — aucune donnée réelle ingérée. Exécutez `bun scripts/ingest.ts` " +
  "(source : legally-subjective, corpus Phase 2, 1 387 appels criminels réels). " +
  "Aucune donnée de substitution ne sera affichée.";

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------
export async function getOverview() {
  const opinions = await db.opinion.findMany({
    select: {
      year: true, month: true, dateFiled: true, department: true,
      dispositionPrimary: true, dispositionBinary: true, binaryEligible: true,
      caseName: true, citationMentions: true, textChars: true,
    },
  });
  if (opinions.length === 0) return emptyPayload(EMPTY_MESSAGE);

  const binary = opinions.filter((o) => o.binaryEligible);
  const affirmed = binary.filter((o) => o.dispositionBinary === "affirmed").length;

  const dispositions = new Map<string, number>();
  for (const o of opinions) {
    const key = o.dispositionPrimary ?? "non_classé";
    dispositions.set(key, (dispositions.get(key) ?? 0) + 1);
  }

  const deptAgg = new Map<string, { n: number; affirmed: number }>();
  for (const o of binary) {
    const cur = deptAgg.get(o.department) ?? { n: 0, affirmed: 0 };
    cur.n += 1;
    if (o.dispositionBinary === "affirmed") cur.affirmed += 1;
    deptAgg.set(o.department, cur);
  }

  const dates = opinions.map((o) => o.dateFiled.getTime()).sort((a, b) => a - b);
  const judges = await db.judge.count();
  const seats = await db.panelSeat.count();
  const authorities = await db.citedAuthority.groupBy({
    by: ["target"],
    _count: { opinionId: true },
  });
  const totalMentions = await db.citedAuthority.aggregate({ _sum: { count: true } });

  const peopleV = opinions.filter((o) => o.caseName.startsWith("People v")).length;

  return {
    empty: false as const,
    corpus: {
      records: opinions.length,
      firstDate: new Date(dates[0]).toISOString().slice(0, 10),
      lastDate: new Date(dates[dates.length - 1]).toISOString().slice(0, 10),
      years: [...new Set(opinions.map((o) => o.year))].sort(),
      peopleV,
      other: opinions.length - peopleV,
      withText: opinions.filter((o) => o.textChars > 200).length,
    },
    binary: {
      n: binary.length,
      affirmed,
      reversedVacated: binary.length - affirmed,
      rate: affirmed / binary.length,
      wilson95: wilsonInterval(affirmed, binary.length),
    },
    dispositions: [...dispositions.entries()]
      .map(([key, count]) => ({
        key,
        count,
        share: count / opinions.length,
        wilson95: wilsonInterval(count, opinions.length),
      }))
      .sort((a, b) => b.count - a.count),
    departments: [...deptAgg.entries()]
      .map(([dept, v]) => ({
        dept,
        n: v.n,
        affirmed: v.affirmed,
        rate: v.affirmed / v.n,
        wilson95: wilsonInterval(v.affirmed, v.n),
      }))
      .sort((a, b) => b.n - a.n),
    judges,
    seats,
    citedTargets: authorities.length,
    citedMentions: totalMentions._sum.count ?? 0,
  };
}

// ---------------------------------------------------------------------------
// Judge metrics (Weakness Matrix + Radar + Neural Map payloads)
// ---------------------------------------------------------------------------
export interface JudgeMetric {
  name: string;
  rawVariants: string[];
  nOpinions: number;
  nBinary: number;
  affirmed: number;
  rate: number;
  wilson95: { low: number; high: number };
  z: number;
  presidingCount: number;
  uniqueCoJudges: number;
  dominantDepartment: string;
  yearSpan: [number, number] | null;
  yearlyRates: { year: number; n: number; affirmed: number; rate: number }[];
  volatility: number;
  avgCitations: number;
  punitiveHits: number;
  rehabHits: number;
  deviatesUp: boolean;
  deviatesDown: boolean;
}

export async function getJudgeMetrics(): Promise<JudgeMetric[] | EmptyPayload> {
  const opinions = await db.opinion.findMany({
    select: {
      id: true, year: true, department: true, binaryEligible: true,
      dispositionBinary: true, citationMentions: true,
      punitiveHits: true, rehabHits: true,
    },
  });
  if (opinions.length === 0) return emptyPayload(EMPTY_MESSAGE);
  const opinionById = new Map(opinions.map((o) => [o.id, o]));

  const seats = await db.panelSeat.findMany({ select: { judgeId: true, opinionId: true, role: true } });
  const judges = await db.judge.findMany({ select: { id: true, name: true, rawVariants: true } });

  const baseK = opinions.filter((o) => o.binaryEligible && o.dispositionBinary === "affirmed").length;
  const baseN = opinions.filter((o) => o.binaryEligible).length;

  const perJudge = new Map<
    number,
    {
      name: string; rawVariants: string[]; opinionIds: Set<number>;
      binaryIds: Set<number>; affirmed: number; presiding: number;
      coJudges: Set<number>; deptCount: Map<string, number>;
      years: Map<number, { n: number; affirmed: number }>;
      citations: number[]; punitive: number; rehab: number;
    }
  >();

  const seatsByOpinion = new Map<number, { judgeId: number; role: string }[]>();
  for (const s of seats) {
    if (!seatsByOpinion.has(s.opinionId)) seatsByOpinion.set(s.opinionId, []);
    seatsByOpinion.get(s.opinionId)!.push({ judgeId: s.judgeId, role: s.role });
  }

  for (const j of judges) {
    perJudge.set(j.id, {
      name: j.name,
      rawVariants: JSON.parse(j.rawVariants) as string[],
      opinionIds: new Set(), binaryIds: new Set(), affirmed: 0, presiding: 0,
      coJudges: new Set(), deptCount: new Map(), years: new Map(),
      citations: [], punitive: 0, rehab: 0,
    });
  }

  for (const s of seats) {
    const g = perJudge.get(s.judgeId);
    const op = opinionById.get(s.opinionId);
    if (!g || !op) continue;
    g.opinionIds.add(s.opinionId);
    if (op.binaryEligible) {
      g.binaryIds.add(s.opinionId);
      if (op.dispositionBinary === "affirmed") g.affirmed += 1;
      const y = g.years.get(op.year) ?? { n: 0, affirmed: 0 };
      y.n += 1;
      if (op.dispositionBinary === "affirmed") y.affirmed += 1;
      g.years.set(op.year, y);
    }
    if (s.role === "presiding") g.presiding += 1;
    g.deptCount.set(op.department, (g.deptCount.get(op.department) ?? 0) + 1);
    g.citations.push(op.citationMentions);
    g.punitive += op.punitiveHits;
    g.rehab += op.rehabHits;
    for (const co of seatsByOpinion.get(s.opinionId) ?? []) {
      if (co.judgeId !== s.judgeId) g.coJudges.add(co.judgeId);
    }
  }

  const metrics: JudgeMetric[] = [];
  for (const g of perJudge.values()) {
    const nBinary = g.binaryIds.size;
    const rate = nBinary > 0 ? g.affirmed / nBinary : 0;
    const z = zScoreVersusBaseline(g.affirmed, nBinary, baseK, baseN);
    const yearlyRates = [...g.years.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([year, v]) => ({ year, n: v.n, affirmed: v.affirmed, rate: v.n > 0 ? v.affirmed / v.n : 0 }));
    const volatility = yearlyRates.filter((y) => y.n >= 5).length >= 3
      ? stdev(yearlyRates.filter((y) => y.n >= 5).map((y) => y.rate))
      : 0;
    const yearsSorted = [...g.years.keys()].sort();
    const dominant = [...g.deptCount.entries()].sort((a, b) => b[1] - a[1])[0];
    metrics.push({
      name: g.name,
      rawVariants: g.rawVariants,
      nOpinions: g.opinionIds.size,
      nBinary,
      affirmed: g.affirmed,
      rate,
      wilson95: wilsonInterval(g.affirmed, nBinary),
      z,
      presidingCount: g.presiding,
      uniqueCoJudges: g.coJudges.size,
      dominantDepartment: dominant ? dominant[0] : "unknown",
      yearSpan: yearsSorted.length ? [yearsSorted[0], yearsSorted[yearsSorted.length - 1]] : null,
      yearlyRates,
      volatility,
      avgCitations: mean(g.citations),
      punitiveHits: g.punitive,
      rehabHits: g.rehab,
      deviatesUp: z >= 2 && nBinary >= 30,
      deviatesDown: z <= -2 && nBinary >= 30,
    });
  }
  return metrics.sort((a, b) => b.nBinary - a.nBinary);
}

// ---------------------------------------------------------------------------
// Heatmap (Bias Heatmap module)
// ---------------------------------------------------------------------------
export async function getHeatmap() {
  const opinions = await db.opinion.findMany({
    select: { year: true, department: true, binaryEligible: true, dispositionBinary: true },
  });
  if (opinions.length === 0) return emptyPayload(EMPTY_MESSAGE);
  const binary = opinions.filter((o) => o.binaryEligible);

  const years = [...new Set(opinions.map((o) => o.year))].sort();
  const depts = [...new Set(opinions.map((o) => o.department))].sort();

  const cell = (key: string) => {
    const [dept, year] = key.split("|");
    const rows = binary.filter((o) => o.department === dept && o.year === Number(year));
    const affirmed = rows.filter((o) => o.dispositionBinary === "affirmed").length;
    return { n: rows.length, affirmed, rate: rows.length ? affirmed / rows.length : null };
  };

  const deptYear = depts.map((dept) => ({
    rowKey: dept,
    cells: years.map((year) => ({ colKey: String(year), ...cell(`${dept}|${year}`) })),
  }));

  // per-year corpus baseline for deviation flags
  const byYear = years.map((year) => {
    const rows = binary.filter((o) => o.year === year);
    const affirmed = rows.filter((o) => o.dispositionBinary === "affirmed").length;
    return { year, n: rows.length, affirmed, rate: rows.length ? affirmed / rows.length : 0 };
  });

  return {
    empty: false as const,
    departments: depts,
    years: years.map(String),
    deptYear,
    byYear,
    binaryN: binary.length,
  };
}

// ---------------------------------------------------------------------------
// Timeline (Cognitive Timeline module)
// ---------------------------------------------------------------------------
export async function getTimeline() {
  const opinions = await db.opinion.findMany({
    select: { year: true, month: true, binaryEligible: true, dispositionBinary: true, dateFiled: true },
  });
  if (opinions.length === 0) return emptyPayload(EMPTY_MESSAGE);
  const binary = opinions.filter((o) => o.binaryEligible);

  const monthAgg = new Map<string, { n: number; affirmed: number; total: number }>();
  for (const o of binary) {
    const key = `${o.year}-${String(o.month).padStart(2, "0")}`;
    const cur = monthAgg.get(key) ?? { n: 0, affirmed: 0, total: 0 };
    cur.n += 1;
    if (o.dispositionBinary === "affirmed") cur.affirmed += 1;
    cur.total += 1;
    monthAgg.set(key, cur);
  }
  // volume for ALL opinions (not just binary)
  for (const o of opinions) {
    const key = `${o.year}-${String(o.month).padStart(2, "0")}`;
    const cur = monthAgg.get(key) ?? { n: 0, affirmed: 0, total: 0 };
    cur.total += 1;
    monthAgg.set(key, cur);
  }

  const monthly = [...monthAgg.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, v]) => ({
      month: key,
      nBinary: v.n,
      volume: v.total,
      affirmed: v.affirmed,
      rate: v.n > 0 ? v.affirmed / v.n : null,
    }));

  const monthOfYear = Array.from({ length: 12 }, (_, i) => {
    const m = i + 1;
    const rows = binary.filter((o) => o.month === m);
    const affirmed = rows.filter((o) => o.dispositionBinary === "affirmed").length;
    return {
      month: m,
      n: rows.length,
      affirmed,
      rate: rows.length ? affirmed / rows.length : null,
    };
  });

  const byYear = [...new Set(opinions.map((o) => o.year))].sort().map((year) => {
    const rows = binary.filter((o) => o.year === year);
    const affirmed = rows.filter((o) => o.dispositionBinary === "affirmed").length;
    return { year, n: rows.length, affirmed, rate: rows.length ? affirmed / rows.length : 0 };
  });

  // rolling 12-month affirmance rate
  const rolling: { month: string; rate: number | null; n: number }[] = [];
  for (let i = 0; i < monthly.length; i++) {
    const window = monthly.slice(Math.max(0, i - 11), i + 1).filter((m) => m.nBinary > 0);
    const n = window.reduce((a, b) => a + b.nBinary, 0);
    const affirmed = window.reduce((a, b) => a + (b.affirmed ?? 0), 0);
    rolling.push({ month: monthly[i].month, rate: n >= 20 ? affirmed / n : null, n });
  }

  return { empty: false as const, monthly, monthOfYear, byYear, rolling };
}

// ---------------------------------------------------------------------------
// Network (Neural Map module) — co-panel graph
// ---------------------------------------------------------------------------
export async function getNetwork(minWeight = 5) {
  const seats = await db.panelSeat.findMany({ select: { judgeId: true, opinionId: true } });
  if (seats.length === 0) return emptyPayload(EMPTY_MESSAGE);

  const judges = await db.judge.findMany({ select: { id: true, name: true } });
  const opinions = await db.opinion.findMany({
    select: {
      id: true, department: true, binaryEligible: true, dispositionBinary: true,
    },
  });
  const opById = new Map(opinions.map((o) => [o.id, o]));
  const nameById = new Map(judges.map((j) => [j.id, j.name]));

  const seatsByOpinion = new Map<number, number[]>();
  for (const s of seats) {
    if (!seatsByOpinion.has(s.opinionId)) seatsByOpinion.set(s.opinionId, []);
    seatsByOpinion.get(s.opinionId)!.push(s.judgeId);
  }

  // judge stats
  const stat = new Map<number, { n: number; binary: number; affirmed: number; dept: Map<string, number> }>();
  for (const [opId, judgeIds] of seatsByOpinion) {
    const op = opById.get(opId);
    if (!op) continue;
    for (const jid of judgeIds) {
      const cur = stat.get(jid) ?? { n: 0, binary: 0, affirmed: 0, dept: new Map() };
      cur.n += 1;
      if (op.binaryEligible) {
        cur.binary += 1;
        if (op.dispositionBinary === "affirmed") cur.affirmed += 1;
      }
      cur.dept.set(op.department, (cur.dept.get(op.department) ?? 0) + 1);
      stat.set(jid, cur);
    }
  }

  const baseK = opinions.filter((o) => o.binaryEligible && o.dispositionBinary === "affirmed").length;
  const baseN = opinions.filter((o) => o.binaryEligible).length;

  const nodes = judges
    .filter((j) => stat.has(j.id))
    .map((j) => {
      const s = stat.get(j.id)!;
      const dominant = [...s.dept.entries()].sort((a, b) => b[1] - a[1])[0];
      return {
        id: j.id,
        name: j.name,
        volume: s.n,
        binaryN: s.binary,
        rate: s.binary > 0 ? s.affirmed / s.binary : null,
        z: s.binary > 0 ? zScoreVersusBaseline(s.affirmed, s.binary, baseK, baseN) : 0,
        dominantDepartment: dominant ? dominant[0] : "unknown",
      };
    });

  // co-panel edges
  const pairCount = new Map<string, number>();
  for (const judgeIds of seatsByOpinion.values()) {
    const unique = [...new Set(judgeIds)].sort((a, b) => a - b);
    for (let i = 0; i < unique.length; i++) {
      for (let k = i + 1; k < unique.length; k++) {
        const key = `${unique[i]}-${unique[k]}`;
        pairCount.set(key, (pairCount.get(key) ?? 0) + 1);
      }
    }
  }
  const edges = [...pairCount.entries()]
    .filter(([, w]) => w >= minWeight)
    .map(([key, weight]) => {
      const [a, b] = key.split("-").map(Number);
      return { source: a, target: b, weight };
    })
    .sort((a, b) => b.weight - a.weight);

  return {
    empty: false as const,
    nodes,
    edges,
    minWeight,
    totalPairs: pairCount.size,
  };
}

// ---------------------------------------------------------------------------
// Stylometry (Spectrum module)
// ---------------------------------------------------------------------------
export async function getStylometry() {
  const opinions = await db.opinion.findMany({
    select: {
      department: true, textChars: true, tokenCount: true, sentenceCount: true,
      avgSentenceLen: true, typeTokenRatio: true, punitiveHits: true,
      rehabHits: true, year: true,
    },
  });
  if (opinions.length === 0) return emptyPayload(EMPTY_MESSAGE);
  const withText = opinions.filter((o) => o.textChars > 200);
  if (withText.length === 0) return emptyPayload("Aucun texte officiel indexé — stylométrie indisponible.");

  const agg = (rows: typeof opinions) => {
    const n = rows.length;
    const tokens = rows.reduce((a, b) => a + b.tokenCount, 0);
    const punitive = rows.reduce((a, b) => a + b.punitiveHits, 0);
    const rehab = rows.reduce((a, b) => a + b.rehabHits, 0);
    return {
      n,
      avgSentenceLen: mean(rows.map((r) => r.avgSentenceLen)),
      avgTtr: mean(rows.map((r) => r.typeTokenRatio)),
      avgTokens: mean(rows.map((r) => r.tokenCount)),
      punitivePer1k: tokens > 0 ? (punitive / tokens) * 1000 : 0,
      rehabPer1k: tokens > 0 ? (rehab / tokens) * 1000 : 0,
      punitiveTotal: punitive,
      rehabTotal: rehab,
      ratio: rehab > 0 ? punitive / rehab : null,
    };
  };

  const depts = [...new Set(withText.map((o) => o.department))].sort();
  const byDepartment = depts.map((dept) => ({ department: dept, ...agg(withText.filter((o) => o.department === dept)) }));

  const years = [...new Set(withText.map((o) => o.year))].sort();
  const byYear = years.map((year) => ({ year, ...agg(withText.filter((o) => o.year === year)) }));

  // ratio histogram (per-opinion punitive/rehab ratio, log-ish bins)
  const ratioHistogram = (() => {
    const bins = 12;
    const counts = new Array(bins).fill(0);
    let included = 0;
    for (const o of withText) {
      if (o.rehabHits === 0 && o.punitiveHits === 0) continue;
      const ratio = o.rehabHits > 0 ? o.punitiveHits / o.rehabHits : o.punitiveHits;
      const idx = Math.min(bins - 1, Math.floor(Math.log2(1 + ratio) * 2));
      counts[idx] += 1;
      included += 1;
    }
    return counts.map((count, i) => ({
      binLabel: `2^${i / 2}×`,
      binStart: 2 ** (i / 2),
      count,
    }));
  })();

  const sentenceHistogram = (() => {
    const bins = 18;
    const lo = 40, hi = 220;
    const counts = new Array(bins).fill(0);
    for (const o of withText) {
      const idx = Math.min(bins - 1, Math.max(0, Math.floor(((o.avgSentenceLen - lo) / (hi - lo)) * bins)));
      counts[idx] += 1;
    }
    return counts.map((count, i) => ({
      binLabel: `${Math.round(lo + ((hi - lo) * i) / bins)}`,
      count,
    }));
  })();

  return {
    empty: false as const,
    corpus: agg(withText),
    byDepartment,
    byYear,
    ratioHistogram,
    sentenceHistogram,
    methodNote:
      "Stylométrie calculée sur le texte officiel intégral de chaque opinion " +
      "(script <style>/<style> retiré, balises supprimées, entités décodées). " +
      "Lexiques punitif/réhabilitatif documentés dans scripts/ingest.ts (règle R4).",
  };
}

// ---------------------------------------------------------------------------
// Precedents (Precedent Net module)
// ---------------------------------------------------------------------------
export async function getPrecedents(topN = 40) {
  const citations = await db.citedAuthority.findMany({
    select: { target: true, kind: true, count: true, opinionId: true },
  });
  if (citations.length === 0) return emptyPayload(EMPTY_MESSAGE);
  const opinions = await db.opinion.findMany({
    select: { id: true, department: true, year: true },
  });
  const opById = new Map(opinions.map((o) => [o.id, o]));

  const agg = new Map<string, { target: string; kind: string; opinions: Set<number>; mentions: number; dept: Map<string, number> }>();
  for (const c of citations) {
    const cur = agg.get(c.target) ?? {
      target: c.target, kind: c.kind, opinions: new Set<number>(), mentions: 0, dept: new Map(),
    };
    cur.opinions.add(c.opinionId);
    cur.mentions += c.count;
    const op = opById.get(c.opinionId);
    if (op) cur.dept.set(op.department, (cur.dept.get(op.department) ?? 0) + 1);
    agg.set(c.target, cur);
  }

  const top = [...agg.values()].sort((a, b) => b.opinions.size - a.opinions.size).slice(0, topN);
  const topTargets = new Set(top.map((t) => t.target));

  // co-citation edges among top authorities
  const opinionsOf = new Map<string, number[]>();
  for (const c of citations) {
    if (!topTargets.has(c.target)) continue;
    if (!opinionsOf.has(c.target)) opinionsOf.set(c.target, []);
    opinionsOf.get(c.target)!.push(c.opinionId);
  }
  const edges: { source: string; target: string; weight: number }[] = [];
  const topList = top.map((t) => t.target);
  for (let i = 0; i < topList.length; i++) {
    for (let k = i + 1; k < topList.length; k++) {
      const a = new Set(opinionsOf.get(topList[i]) ?? []);
      const b = opinionsOf.get(topList[k]) ?? [];
      let shared = 0;
      for (const opId of b) if (a.has(opId)) shared += 1;
      if (shared >= 3) edges.push({ source: topList[i], target: topList[k], weight: shared });
    }
  }
  edges.sort((a, b) => b.weight - a.weight);

  return {
    empty: false as const,
    nodes: top.map((t) => {
      const dominant = [...t.dept.entries()].sort((a, b) => b[1] - a[1])[0];
      return {
        target: t.target,
        kind: t.kind,
        citedInOpinions: t.opinions.size,
        mentions: t.mentions,
        dominantDepartment: dominant ? dominant[0] : "unknown",
      };
    }),
    edges: edges.slice(0, 160),
    totalUniqueTargets: agg.size,
    totalMentions: citations.reduce((a, b) => a + b.count, 0),
  };
}

// ---------------------------------------------------------------------------
// Monte-Carlo (Verdict Simulator) — bootstrap over REAL outcomes
// ---------------------------------------------------------------------------
export interface MonteCarloFilter {
  department?: string;
  judge?: string;
  yearFrom?: number;
  yearTo?: number;
  chargeLike?: string;
}

export async function runMonteCarlo(filter: MonteCarloFilter, iterations = 10000) {
  const seats = await db.panelSeat.findMany({
    where: filter.judge ? { judge: { name: filter.judge } } : undefined,
    select: { opinionId: true },
  });
  const judgeOpinionIds = filter.judge ? new Set(seats.map((s) => s.opinionId)) : null;

  const opinions = await db.opinion.findMany({
    where: {
      binaryEligible: true,
      department: filter.department || undefined,
      year: {
        gte: filter.yearFrom ?? undefined,
        lte: filter.yearTo ?? undefined,
      },
    },
    select: {
      id: true, dispositionBinary: true, charge: true, caseId: true,
    },
  });
  const selected = opinions.filter((o) => {
    if (judgeOpinionIds && !judgeOpinionIds.has(o.id)) return false;
    if (filter.chargeLike && !(o.charge ?? "").toLowerCase().includes(filter.chargeLike.toLowerCase())) return false;
    return true;
  });

  if (selected.length === 0) {
    return emptyPayload(
      "Aucune affaire réelle ne correspond à ce filtre — la simulation refuse de s'exécuter sur un échantillon vide.",
    );
  }

  const outcomes = selected.map((o) => (o.dispositionBinary === "affirmed" ? 1 : 0));
  const seed = fnv1aHash(JSON.stringify(filter ?? {}));
  const result = bootstrapProportion(outcomes, iterations, seed);

  // corpus baseline for comparison
  const base = await db.opinion.aggregate({
    where: { binaryEligible: true, dispositionBinary: "affirmed" },
    _count: { _all: true },
  });
  const baseAll = await db.opinion.count({ where: { binaryEligible: true } });

  return {
    empty: false as const,
    filter,
    sampleSize: selected.length,
    affirmed: outcomes.reduce((a, b) => a + b, 0),
    ...result,
    baseline: { n: baseAll, rate: baseAll > 0 ? base._count._all / baseAll : 0 },
    methodNote:
      `Bootstrap non paramétrique : ${iterations} ré-échantillonnages avec remise des ${selected.length} ` +
      "issues binaires RÉELLES du filtre (générateur mulberry32, graine = hache FNV-1a du filtre — " +
      "simulation déterministe et reproductible). Aucune valeur inventée.",
  };
}

// ---------------------------------------------------------------------------
// Cases (picker for the Comparison Shield)
// ---------------------------------------------------------------------------
export async function getCases(params: { search?: string; limit?: number; offset?: number }) {
  const limit = Math.min(params.limit ?? 30, 100);
  const offset = params.offset ?? 0;
  const search = params.search?.trim().toLowerCase();

  const where = search
    ? {
        OR: [
          { caseName: { contains: search } },
          { citation: { contains: search } },
          { charge: { contains: search } },
          { caseId: { contains: search } },
        ],
      }
    : undefined;

  const [total, rows] = await Promise.all([
    db.opinion.count({ where }),
    db.opinion.findMany({
      where,
      orderBy: { dateFiled: "desc" },
      select: {
        caseId: true, caseName: true, citation: true, charge: true,
        dateFiled: true, department: true, dispositionPrimary: true,
        dispositionBinary: true, binaryEligible: true, factsExcerpt: true,
      },
      take: limit,
      skip: offset,
    }),
  ]);
  if (total === 0 && offset === 0 && !search) return emptyPayload(EMPTY_MESSAGE);
  return {
    empty: false as const,
    total,
    limit,
    offset,
    cases: rows.map((r) => ({
      ...r,
      dateFiled: r.dateFiled.toISOString().slice(0, 10),
      factsExcerpt: r.factsExcerpt ? r.factsExcerpt.slice(0, 900) : null,
    })),
  };
}

// ---------------------------------------------------------------------------
// Judge radar (Deviation Radar module)
// ---------------------------------------------------------------------------
export async function getRadar(judgeName?: string) {
  const metrics = await getJudgeMetrics();
  if ("empty" in metrics) return metrics;
  const eligible = metrics.filter((m) => m.nBinary >= 30);

  const sample = {
    volume: eligible.map((m) => m.nOpinions),
    severity: eligible.map((m) => m.rate),
    volatility: eligible.map((m) => m.volatility),
    diversity: eligible.map((m) => m.uniqueCoJudges),
    citationIntensity: eligible.map((m) => m.avgCitations),
    presidingShare: eligible.map((m) => (m.nOpinions > 0 ? m.presidingCount / m.nOpinions : 0)),
  };
  const median = (xs: number[]) => {
    if (xs.length === 0) return 0;
    const s = [...xs].sort((a, b) => a - b);
    const mid = Math.floor(s.length / 2);
    return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
  };

  const axes = [
    { key: "severity", label: "Sévérité (taux de confirmation)" },
    { key: "volume", label: "Volume décisionnel" },
    { key: "volatility", label: "Volatilité temporelle" },
    { key: "diversity", label: "Diversité de panel" },
    { key: "citationIntensity", label: "Intensité de citation" },
    { key: "presidingShare", label: "Taux de présidence" },
  ] as const;

  const target = judgeName
    ? eligible.find((m) => m.name === judgeName) ?? eligible[0]
    : eligible[0];
  if (!target) return emptyPayload("Aucun juge avec n ≥ 30 décisions binaires dans l'index réel.");

  const valueFor = (m: (typeof eligible)[number], key: (typeof axes)[number]["key"]) => {
    switch (key) {
      case "severity": return m.rate;
      case "volume": return m.nOpinions;
      case "volatility": return m.volatility;
      case "diversity": return m.uniqueCoJudges;
      case "citationIntensity": return m.avgCitations;
      case "presidingShare": return m.nOpinions > 0 ? m.presidingCount / m.nOpinions : 0;
    }
  };

  const targetValues = axes.map((a) => ({
    axis: a.label,
    percentile: round(percentileRank(sample[a.key], valueFor(target, a.key)), 1),
    value: round(valueFor(target, a.key), 4),
    median: round(median(sample[a.key]), 4),
  }));

  return {
    empty: false as const,
    judge: {
      name: target.name,
      nBinary: target.nBinary,
      nOpinions: target.nOpinions,
      rate: target.rate,
      z: target.z,
      wilson95: target.wilson95,
      presidingCount: target.presidingCount,
      dominantDepartment: target.dominantDepartment,
      yearSpan: target.yearSpan,
      volatility: target.volatility,
    },
    axes: targetValues,
    eligibleJudges: eligible.map((m) => ({
      name: m.name, nBinary: m.nBinary, rate: round(m.rate, 4), z: round(m.z, 2),
    })),
    nEligible: eligible.length,
    methodNote:
      "Chaque axe = rang percentile du juge parmi les juges éligibles (n binaire ≥ 30, " +
      "seuil de significativité statistique). Médiane du corpus affichée en superposition. " +
      "Percentiles calculés sur les métriques réelles de l'index.",
  };
}
