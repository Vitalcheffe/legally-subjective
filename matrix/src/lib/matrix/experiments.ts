/**
 * Behavioral Matrix — experimental protocol engine (Phase 4).
 *
 * Zero-shot trial: the multi-agent engine (Prosecutor → Defender → AI-Judge)
 * renders a verdict on a seeded stratified sample of REAL cases. The human
 * decision is NEVER shown to the agents during a run (it is only used to
 * score the run afterwards). Everything is archived verbatim; failures are
 * recorded as errors, never simulated.
 *
 * Inclusion criteria (documented, like an RCT protocol):
 *   - binaryEligible = true (affirmed | reversed_vacated disposition)
 *   - official recital excerpt of at least 120 characters (the agents need
 *     the real facts to deliberate; cases below this threshold are excluded
 *     and the exclusion is surfaced in the UI, not hidden)
 *
 * Stratification: proportional allocation over department × binary outcome,
 * sampled with a seeded PRNG (mulberry32 seeded by FNV-1a of the protocol
 * parameters) so a given (seed, targetN) always draws the exact same sample.
 */
import { db } from "@/lib/db";
import { runAgentSession } from "./agents";
import {
  wilsonInterval, brierScore, calibrationBuckets, mcnemarExact,
  fnv1aHash, mulberry32, round,
} from "./stats";

export const MIN_RECITAL_CHARS = 120;

/** Seeded proportional stratified sample over department × binary outcome. */
export function stratifiedSample<T extends { department: string; dispositionBinary: string }>(
  pool: T[],
  targetN: number,
  seed: number,
): T[] {
  if (pool.length === 0 || targetN <= 0) return [];
  const strata = new Map<string, T[]>();
  for (const item of pool) {
    const key = `${item.department}|${item.dispositionBinary}`;
    const arr = strata.get(key) ?? [];
    arr.push(item);
    strata.set(key, arr);
  }
  // deterministic order of strata
  const keys = [...strata.keys()].sort();
  // proportional allocation with largest-remainder rounding
  const quotas = new Map<string, number>();
  let allocated = 0;
  const remainders: { key: string; rem: number }[] = [];
  for (const key of keys) {
    const size = strata.get(key)!.length;
    const exact = (size * targetN) / pool.length;
    const floor = Math.floor(exact);
    quotas.set(key, floor);
    allocated += floor;
    remainders.push({ key, rem: exact - floor });
  }
  remainders.sort((a, b) => b.rem - a.rem || (a.key < b.key ? -1 : 1));
  let i = 0;
  while (allocated < targetN && remainders.length > 0) {
    const k = remainders[i % remainders.length].key;
    if (quotas.get(k)! < strata.get(k)!.length) {
      quotas.set(k, quotas.get(k)! + 1);
      allocated += 1;
    }
    i += 1;
    if (i > remainders.length * 2 + targetN) break; // pool exhausted guard
  }

  const rng = mulberry32(fnv1aHash(`sample:${seed}:${targetN}`));
  const drawn: T[] = [];
  for (const key of keys) {
    const arr = [...strata.get(key)!];
    // seeded Fisher-Yates on the stratum copy → reproducible draw
    for (let j = arr.length - 1; j > 0; j--) {
      const r = (rng() * (j + 1)) | 0;
      [arr[j], arr[r]] = [arr[r], arr[j]];
    }
    drawn.push(...arr.slice(0, quotas.get(key)!));
  }
  return drawn;
}

export async function createExperiment(label: string, targetN: number, seed: number) {
  const pool = await db.opinion.findMany({
    where: {
      binaryEligible: true,
      dispositionBinary: { in: ["affirmed", "reversed_vacated"] },
    },
    select: { caseId: true, department: true, dispositionBinary: true },
  });
  const eligible = await db.opinion.findMany({
    where: {
      binaryEligible: true,
      dispositionBinary: { in: ["affirmed", "reversed_vacated"] },
      factsExcerpt: { not: null },
    },
    select: { caseId: true, department: true, dispositionBinary: true, factsExcerpt: true },
  });
  const eligiblePool = eligible.filter(
    (o) => (o.factsExcerpt ?? "").length >= MIN_RECITAL_CHARS,
  );

  const effectiveN = Math.min(targetN, eligiblePool.length);
  const sample = stratifiedSample(eligiblePool, effectiveN, seed);

  const experiment = await db.experiment.create({
    data: {
      label,
      seed,
      targetN: effectiveN,
      status: "running",
      caseIds: JSON.stringify(sample.map((s) => s.caseId)),
      cases: {
        create: sample.map((s, idx) => ({
          caseId: s.caseId,
          position: idx,
          state: "pending",
        })),
      },
    },
    include: { cases: true },
  });

  // exclusion report (real counts, surfaced in the UI)
  const excludedNoRecital = pool.length - eligiblePool.length;
  return {
    id: experiment.id,
    label,
    seed,
    targetN: effectiveN,
    requestedN: targetN,
    poolSize: eligiblePool.length,
    binaryEligibleTotal: pool.length,
    excludedNoRecital,
    status: experiment.status,
  };
}

/**
 * Run the NEXT pending case of an experiment (one case = one full
 * Prosecutor → Defender → AI-Judge session). Returns the new state.
 * A case already in "running" state is re-claimed (crash recovery).
 */
export async function stepExperiment(id: number) {
  const experiment = await db.experiment.findUnique({
    where: { id },
    include: { cases: { orderBy: { position: "asc" } } },
  });
  if (!experiment) throw new Error(`Protocole inconnu : ${id}`);
  if (experiment.status === "done") {
    return getExperimentState(id);
  }

  const next =
    experiment.cases.find((c) => c.state === "pending") ??
    experiment.cases.find((c) => c.state === "running");
  if (!next) {
    await db.experiment.update({
      where: { id },
      data: { status: "done", completedAt: new Date() },
    });
    return getExperimentState(id);
  }

  await db.experimentCase.update({
    where: { id: next.id },
    data: { state: "running" },
  });

  try {
    const result = await runAgentSession(next.caseId, id);
    const ok = result.status === "ok";
    await db.experimentCase.update({
      where: { id: next.id },
      data: {
        state: ok ? "done" : "error",
        note: ok ? null : (result.error ?? "échec de session (archivé verbatim)"),
      },
    });
  } catch (e) {
    await db.experimentCase.update({
      where: { id: next.id },
      data: {
        state: "error",
        note: `erreur moteur : ${(e as Error).message}`,
      },
    });
  }

  // progress = resolved cases (done + error), targetN total
  const cases = await db.experimentCase.findMany({
    where: { experimentId: id },
    select: { state: true },
  });
  const resolved = cases.filter((c) => c.state === "done" || c.state === "error").length;
  const stillPending = cases.some((c) => c.state === "pending" || c.state === "running");
  await db.experiment.update({
    where: { id },
    data: {
      progress: resolved,
      status: stillPending ? "running" : "done",
      completedAt: stillPending ? null : new Date(),
    },
  });

  return getExperimentState(id);
}

export interface ExperimentState {
  empty: boolean;
  message?: string;
  experiment: {
    id: number;
    label: string;
    seed: number;
    targetN: number;
    status: string;
    progress: number;
    createdAt: string;
    completedAt: string | null;
  };
  protocol: {
    poolSize: number;
    binaryEligibleTotal: number;
    excludedNoRecital: number;
    minRecitalChars: number;
  };
  pending: number;
  errors: { caseId: string; note: string }[];
  results: {
    nScored: number; // ok runs on binary-eligible cases
    nError: number;
    agreement: number; // AI verdict == human verdict (0..1)
    agreementK: number;
    wilson: { low: number; high: number };
    baseRate: number; // share of affirmed in the scored sample
    baselineAccuracy: number; // always-affirm accuracy on the same cases
    confusion: {
      aiAffirmedHumanAffirmed: number;
      aiAffirmedHumanReversed: number;
      aiReversedHumanAffirmed: number;
      aiReversedHumanReversed: number;
    };
    brier: number;
    brierBaseline: number; // Brier of the base-rate predictor
    calibration: {
      label: string; n: number; meanConfidence: number; observedRate: number;
    }[];
    mcnemar: { b: number; c: number; exactP: number };
    perDepartment: {
      department: string; n: number; agreement: number;
    }[];
    runs: {
      runId: number; caseId: string; caseName: string; department: string;
      human: string; ai: string; confidence: number; agreement: boolean;
    }[];
  };
}

/**
 * Reset every errored case of an experiment back to `pending` so the run loop
 * re-attempts them (e.g. after an engine rate-limit window has passed).
 * Already-scored cases are never touched. Returns the number of cases requeued.
 */
export async function retryFailedCases(id: number): Promise<number> {
  const experiment = await db.experiment.findUnique({
    where: { id },
    include: { cases: true },
  });
  if (!experiment) throw new Error(`Protocole inconnu : ${id}`);
  const failed = experiment.cases.filter((c) => c.state === "error");
  if (failed.length === 0) return 0;
  await db.experimentCase.updateMany({
    where: { id: { in: failed.map((c) => c.id) } },
    data: { state: "pending", note: null },
  });
  // delete the errored AgentRuns of this experiment so state is recomputed
  // from real sessions only (the verbatim failures remain in the run archive
  // list, but scored aggregates ignore error runs by status filter anyway)
  await db.experiment.update({
    where: { id },
    data: { status: "running" },
  });
  return failed.length;
}

export async function getExperimentState(id: number): Promise<ExperimentState> {
  const experiment = await db.experiment.findUnique({
    where: { id },
    include: { cases: { orderBy: { position: "asc" } } },
  });
  if (!experiment) {
    return {
      empty: true,
      message: `Protocole #${id} introuvable dans l'index.`,
      experiment: {
        id, label: "", seed: 0, targetN: 0, status: "unknown",
        progress: 0, createdAt: "", completedAt: null,
      },
      protocol: { poolSize: 0, binaryEligibleTotal: 0, excludedNoRecital: 0, minRecitalChars: MIN_RECITAL_CHARS },
      pending: 0,
      errors: [],
      results: {
        nScored: 0, nError: 0, agreement: 0, agreementK: 0,
        wilson: { low: 0, high: 0 }, baseRate: 0, baselineAccuracy: 0,
        confusion: {
          aiAffirmedHumanAffirmed: 0, aiAffirmedHumanReversed: 0,
          aiReversedHumanAffirmed: 0, aiReversedHumanReversed: 0,
        },
        brier: 0, brierBaseline: 0, calibration: [],
        mcnemar: { b: 0, c: 0, exactP: 1 },
        perDepartment: [], runs: [],
      },
    };
  }

  const runs = await db.agentRun.findMany({
    where: { experimentId: id, status: "ok", aiVerdict: { not: null }, aiConfidence: { not: null } },
    include: { opinion: { select: { caseName: true, department: true, dispositionBinary: true } } },
    orderBy: { id: "asc" },
  });

  const scored = runs.filter(
    (r) => r.opinion?.dispositionBinary === "affirmed" || r.opinion?.dispositionBinary === "reversed_vacated",
  );

  const caseIds = JSON.parse(experiment.caseIds) as string[];
  const opinions = await db.opinion.findMany({
    where: { caseId: { in: caseIds } },
    select: { caseId: true, department: true, dispositionBinary: true },
  });
  const opinionByCase = new Map(opinions.map((o) => [o.caseId, o]));

  const errCases = experiment.cases.filter((c) => c.state === "error");

  let k = 0;
  let baseK = 0;
  const confusion = {
    aiAffirmedHumanAffirmed: 0, aiAffirmedHumanReversed: 0,
    aiReversedHumanAffirmed: 0, aiReversedHumanReversed: 0,
  };
  const predictions: { p: number; outcome: 0 | 1 }[] = [];
  const deptAgg = new Map<string, { n: number; agree: number }>();

  for (const r of scored) {
    const human = r.opinion!.dispositionBinary as "affirmed" | "reversed_vacated";
    const ai = r.aiVerdict as "affirmed" | "reversed";
    const humanAffirmed = human === "affirmed";
    const aiAffirmed = ai === "affirmed";
    const agree = aiAffirmed === humanAffirmed;
    if (agree) k += 1;
    if (humanAffirmed) baseK += 1;
    if (aiAffirmed && humanAffirmed) confusion.aiAffirmedHumanAffirmed += 1;
    else if (aiAffirmed && !humanAffirmed) confusion.aiAffirmedHumanReversed += 1;
    else if (!aiAffirmed && humanAffirmed) confusion.aiReversedHumanAffirmed += 1;
    else confusion.aiReversedHumanReversed += 1;

    const conf = r.aiConfidence ?? 0.5;
    predictions.push({ p: aiAffirmed ? conf : 1 - conf, outcome: humanAffirmed ? 1 : 0 });

    const dept = r.opinion!.department;
    const d = deptAgg.get(dept) ?? { n: 0, agree: 0 };
    d.n += 1;
    if (agree) d.agree += 1;
    deptAgg.set(dept, d);
  }

  const n = scored.length;
  // McNemar: AI vs always-affirm baseline on the same cases
  let b = 0; // baseline right, AI wrong
  let c = 0; // AI right, baseline wrong
  for (const r of scored) {
    const humanAffirmed = r.opinion!.dispositionBinary === "affirmed";
    const aiRight = (r.aiVerdict === "affirmed") === humanAffirmed;
    const baseRight = humanAffirmed; // always-affirm
    if (!aiRight && baseRight) b += 1;
    if (aiRight && !baseRight) c += 1;
  }

  const baseRate = n > 0 ? baseK / n : 0;
  const brierBasePredictions = predictions.map((p) => ({ p: baseRate, outcome: p.outcome }));

  const protocolPool = await db.opinion.count({ where: { binaryEligible: true } });

  return {
    empty: false,
    experiment: {
      id: experiment.id,
      label: experiment.label,
      seed: experiment.seed,
      targetN: experiment.targetN,
      status: experiment.status,
      progress: experiment.progress,
      createdAt: experiment.createdAt.toISOString(),
      completedAt: experiment.completedAt?.toISOString() ?? null,
    },
    protocol: {
      poolSize: caseIds.length,
      binaryEligibleTotal: protocolPool,
      excludedNoRecital: protocolPool - caseIds.length,
      minRecitalChars: MIN_RECITAL_CHARS,
    },
    pending: experiment.cases.filter((c2) => c2.state === "pending" || c2.state === "running").length,
    errors: errCases.map((c2) => ({ caseId: c2.caseId, note: c2.note ?? "" })),
    results: {
      nScored: n,
      nError: errCases.length,
      agreement: n > 0 ? k / n : 0,
      agreementK: k,
      wilson: wilsonInterval(k, n),
      baseRate,
      baselineAccuracy: baseRate,
      confusion,
      brier: round(brierScore(predictions), 4),
      brierBaseline: round(brierScore(brierBasePredictions), 4),
      calibration: calibrationBuckets(predictions).map((x) => ({
        label: x.label, n: x.n,
        meanConfidence: round(x.meanConfidence, 3), observedRate: round(x.observedRate, 3),
      })),
      mcnemar: mcnemarExact(b, c),
      perDepartment: [...deptAgg.entries()]
        .map(([department, v]) => ({ department, n: v.n, agreement: round(v.agree / v.n, 3) }))
        .sort((x, y) => y.n - x.n),
      runs: scored.map((r) => ({
        runId: r.id,
        caseId: r.caseId,
        caseName: r.opinion?.caseName ?? r.caseId,
        department: r.opinion?.department ?? "?",
        human: r.opinion!.dispositionBinary!,
        ai: r.aiVerdict!,
        confidence: r.aiConfidence ?? 0,
        agreement: r.agreement ?? false,
      })),
    },
  };
}

export async function listExperiments() {
  const experiments = await db.experiment.findMany({
    orderBy: { id: "desc" },
    include: { _count: { select: { cases: true, runs: true } } },
  });
  return {
    empty: experiments.length === 0,
    experiments: experiments.map((e) => ({
      id: e.id,
      label: e.label,
      seed: e.seed,
      targetN: e.targetN,
      status: e.status,
      progress: e.progress,
      createdAt: e.createdAt.toISOString(),
      completedAt: e.completedAt?.toISOString() ?? null,
      runs: e._count.runs,
    })),
  };
}
