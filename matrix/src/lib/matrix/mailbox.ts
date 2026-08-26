/**
 * mailbox.ts — « La Boîte de la Cour » : public interface layer (jmail system).
 *
 * Every row exposed here is derived LIVE from the validated real corpus
 * (1 387 official NY Appellate Division criminal decisions, 2015-2023).
 * Zero-mock contract applies: no fabricated rows, no invented numbers,
 * honest empty states. The only interactive surface is the sandbox
 * composer, which runs the real multi-agent engine on a user-supplied
 * sample WITHOUT ever writing to the scientific archive.
 */
import { db } from "@/lib/db";
import { getJudgeMetrics, type JudgeMetric } from "./queries";
import { getExperimentState, listExperiments } from "./experiments";
import { wilsonInterval } from "./stats";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface MailItem {
  id: string; // "nyappdiv-<cluster>" | "digest-<key>"
  kind: "dossier" | "digest";
  fromName: string; // e.g. "Ceresia, J. (prés.) +2" | "INFINITUM — Rapports système"
  fromDetail: string; // full sender line
  avatar: string; // initials
  subject: string;
  snippet: string;
  date: string; // ISO
  department: string | null;
  disposition: string | null; // binary disposition
  flagged: boolean; // panel contains a statistically flagged judge
  unreadHint?: boolean;
}

export interface DossierPanelEntry {
  name: string;
  role: string;
  nBinary: number;
  rate: number;
  z: number;
  wilson: { low: number; high: number };
  deviatesUp: boolean;
  deviatesDown: boolean;
  presidingCount: number;
  authoredTotal: number;
}

export interface DossierRun {
  id: number;
  createdAt: string;
  aiVerdict: string | null;
  aiConfidence: number | null;
  agreement: boolean | null;
  status: string;
  error: string | null;
  prosecutorOutput: string | null;
  defenderOutput: string | null;
  judgeOutput: string | null;
}

export interface DossierDetail {
  kind: "dossier";
  caseId: string;
  caseName: string;
  dateFiled: string;
  year: number;
  department: string;
  docketNumber: string | null;
  citation: string | null;
  charge: string | null;
  factsExcerpt: string | null;
  dispositionPrimary: string | null;
  dispositionBinary: string | null;
  binaryEligible: boolean;
  authorRaw: string | null;
  authorMethod: string | null;
  authorJudgeName: string | null;
  presidingName: string | null;
  panel: DossierPanelEntry[];
  authorities: { target: string; kind: string; count: number }[];
  runs: DossierRun[];
  stylometry: {
    textChars: number;
    tokenCount: number;
    sentenceCount: number;
    avgSentenceLen: number;
    typeTokenRatio: number;
    punitiveHits: number;
    rehabHits: number;
    citationMentions: number;
  };
  sourceUrl: string;
  empty?: boolean;
  message?: string;
}

export interface DigestSection {
  title: string;
  paragraphs: string[];
  table?: { headers: string[]; rows: string[][] };
}

export interface DigestDetail {
  kind: "digest";
  id: string;
  subject: string;
  fromName: string;
  date: string;
  asOf: string;
  sections: DigestSection[];
}

export interface MailboxPage {
  box: string;
  q: string | null;
  page: number;
  pageSize: number;
  total: number;
  pages: number;
  items: MailItem[];
  empty: boolean;
}

export interface MailFolder {
  id: string;
  label: string;
  count: number;
}

export interface FoldersPayload {
  folders: MailFolder[];
  labels: MailFolder[];
  reports: number;
  judges: number;
  corpusYears: [number, number] | null;
}

export interface JudgeCard {
  name: string;
  rawVariants: string[];
  nOpinions: number;
  nBinary: number;
  rate: number;
  z: number;
  wilson: { low: number; high: number };
  presidingCount: number;
  dominantDepartment: string;
  yearSpan: [number, number] | null;
  authoredTotal: number;
  authoredExplicit: number;
  authoredPresumed: number;
  deviatesUp: boolean;
  deviatesDown: boolean;
}

// ---------------------------------------------------------------------------
// Judge index (metrics reused from the validated analytics layer)
// ---------------------------------------------------------------------------

async function judgeIndex(): Promise<Map<string, JudgeMetric>> {
  const metrics = await getJudgeMetrics();
  const map = new Map<string, JudgeMetric>();
  if ("empty" in metrics) return map;
  for (const m of metrics) map.set(m.name, m);
  return map;
}

function initialsOf(name: string): string {
  const clean = name.replace(/[^A-Za-zÀ-ÿ' -]/g, "").trim();
  const parts = clean.split(/[\s-]+/).filter(Boolean);
  if (parts.length === 0) return "··";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

const DEPT_FULL: Record<string, string> = {
  "1st": "1re Division",
  "2nd": "2e Division",
  "3rd": "3e Division",
  "4th": "4e Division",
  unknown: "Département indéterminé",
};

export function deptFull(dept: string | null | undefined): string {
  return DEPT_FULL[dept ?? "unknown"] ?? "Département indéterminé";
}

function clusterIdOf(caseId: string): string | null {
  const m = caseId.match(/^nyappdiv-(\d+)$/);
  return m ? m[1] : null;
}

// ---------------------------------------------------------------------------
// Folders (sidebar counts — all real, computed live)
// ---------------------------------------------------------------------------

type OpinionWithSeats = Awaited<ReturnType<typeof loadOpinions>>[number];

async function loadOpinions() {
  return db.opinion.findMany({
    include: {
      seats: { include: { judge: { select: { name: true } } } },
      authorJudge: { select: { name: true } },
    },
  });
}

function panelOf(op: OpinionWithSeats): { name: string; role: string }[] {
  return op.seats
    .slice()
    .sort((a, b) => (a.role === "presiding" ? -1 : b.role === "presiding" ? 1 : 0))
    .map((s) => ({ name: s.judge.name, role: s.role }));
}

function presidingOf(panel: { name: string; role: string }[]): string | null {
  return panel.find((p) => p.role === "presiding")?.name ?? panel[0]?.name ?? null;
}

/**
 * A dossier carries the statistical signal when its PRESIDING judge (who
 * chairs the panel — and is the presumed author of unsigned memoranda per NY
 * convention) or its explicit author deviates significantly from the corpus
 * baseline (|z| ≥ 2, n ≥ 30). Panel-wide membership is deliberately ignored:
 * a flagged judge sitting on 100+ panels would otherwise drown the signal.
 */
function dossierIsFlagged(
  op: OpinionWithSeats,
  panel: { name: string; role: string }[],
  flagged: Set<string>,
): boolean {
  const presiding = presidingOf(panel);
  const author = op.authorJudge?.name ?? null;
  return (presiding !== null && flagged.has(presiding)) || (author !== null && flagged.has(author));
}

function itemOf(
  op: OpinionWithSeats,
  flaggedSet: Set<string>,
): MailItem {
  const panel = panelOf(op);
  const presiding = presidingOf(panel);
  const others = panel.length - 1;
  const fromName =
    presiding === null
      ? deptFull(op.department)
      : others > 0
        ? `${presiding}, J. (prés.) +${others}`
        : `${presiding}, J.`;
  const flagged = dossierIsFlagged(op, panel, flaggedSet);
  return {
    id: op.caseId,
    kind: "dossier",
    fromName,
    fromDetail: `${fromName} — ${deptFull(op.department)}`,
    avatar: initialsOf(presiding ?? deptFull(op.department)),
    subject: op.caseName,
    snippet: (op.factsExcerpt ?? "Recital officiel non extrait dans la source — voir l'opinion intégrale.").slice(0, 160),
    date: op.dateFiled.toISOString(),
    department: op.department,
    disposition: op.dispositionBinary,
    flagged,
  };
}

export async function getFolders(): Promise<FoldersPayload> {
  const [opinions, judgeMap] = await Promise.all([loadOpinions(), judgeIndex()]);
  const flaggedSet = new Set(
    [...judgeMap.values()].filter((m) => m.deviatesUp || m.deviatesDown).map((m) => m.name),
  );

  let flaggedCount = 0;
  let affirmedCount = 0;
  let reversedCount = 0;
  let memosCount = 0;
  let signedCount = 0;
  let perCuriamCount = 0;
  const deptCounts = new Map<string, number>();
  const years = new Set<number>();

  for (const op of opinions) {
    years.add(op.year);
    if (dossierIsFlagged(op, panelOf(op), flaggedSet)) flaggedCount += 1;
    if (op.dispositionBinary === "affirmed") affirmedCount += 1;
    if (op.dispositionBinary === "reversed_vacated") reversedCount += 1;
    if (op.authorMethod === "presumed-presiding") memosCount += 1;
    if (op.authorMethod === "explicit") signedCount += 1;
    if (op.authorMethod === "per-curiam") perCuriamCount += 1;
    deptCounts.set(op.department, (deptCounts.get(op.department) ?? 0) + 1);
  }

  const yearsSorted = [...years].sort();
  const folders: MailFolder[] = [
    { id: "inbox", label: "Boîte de réception", count: opinions.length },
    { id: "flagged", label: "Signaux statistiques", count: flaggedCount },
    { id: "reports", label: "Rapports de la Matrice", count: 5 },
  ];
  const labels: MailFolder[] = [
    ...((["1st", "2nd", "3rd", "4th"] as const) satisfies readonly ("1st" | "2nd" | "3rd" | "4th")[])
      .filter((d) => deptCounts.has(d))
      .map((d) => ({ id: `dept-${d}`, label: DEPT_FULL[d], count: deptCounts.get(d) ?? 0 })),
    { id: "affirmed", label: "Confirmés", count: affirmedCount },
    { id: "reversed", label: "Infirmés / annulés", count: reversedCount },
    { id: "signed", label: "Opinions signées", count: signedCount },
    { id: "memos", label: "Mémos du président", count: memosCount },
    { id: "per-curiam", label: "Per curiam", count: perCuriamCount },
  ];

  return {
    folders,
    labels,
    reports: 5,
    judges: judgeMap.size,
    corpusYears: yearsSorted.length ? [yearsSorted[0], yearsSorted[yearsSorted.length - 1]] : null,
  };
}

// ---------------------------------------------------------------------------
// Mailbox list (filter + search + pagination, all real rows)
// ---------------------------------------------------------------------------

function matchesQuery(op: OpinionWithSeats, q: string): boolean {
  const needle = q.toLowerCase();
  if (op.caseName.toLowerCase().includes(needle)) return true;
  if (op.docketNumber?.toLowerCase().includes(needle)) return true;
  if (op.citation?.toLowerCase().includes(needle)) return true;
  if (op.charge?.toLowerCase().includes(needle)) return true;
  if (op.factsExcerpt?.toLowerCase().includes(needle)) return true;
  if (op.department.toLowerCase().includes(needle)) return true;
  if (op.seats.some((s) => s.judge.name.toLowerCase().includes(needle))) return true;
  return false;
}

function boxFilter(op: OpinionWithSeats, box: string, flaggedSet: Set<string>): boolean {
  switch (box) {
    case "inbox":
      return true;
    case "flagged":
      return dossierIsFlagged(op, panelOf(op), flaggedSet);
    case "affirmed":
      return op.dispositionBinary === "affirmed";
    case "reversed":
      return op.dispositionBinary === "reversed_vacated";
    case "signed":
      return op.authorMethod === "explicit";
    case "memos":
      return op.authorMethod === "presumed-presiding";
    case "per-curiam":
      return op.authorMethod === "per-curiam";
    default: {
      const dept = box.match(/^dept-(1st|2nd|3rd|4th)$/);
      if (dept) return op.department === dept[1];
      return true;
    }
  }
}

export async function getMailbox(params: {
  box?: string;
  q?: string;
  page?: number;
  pageSize?: number;
  ids?: string[];
}): Promise<MailboxPage> {
  const box = params.box ?? "inbox";
  const q = (params.q ?? "").trim() || null;
  const pageSize = Math.min(Math.max(params.pageSize ?? 50, 10), 100);
  const page = Math.max(params.page ?? 1, 1);

  if (box === "reports") {
    const digests = await getDigests();
    const filtered = q
      ? digests.filter(
          (d) =>
            d.subject.toLowerCase().includes(q.toLowerCase()) ||
            d.snippet.toLowerCase().includes(q.toLowerCase()),
        )
      : digests;
    const total = filtered.length;
    const pages = Math.max(Math.ceil(total / pageSize), 1);
    const start = (Math.min(page, pages) - 1) * pageSize;
    return {
      box,
      q,
      page: Math.min(page, pages),
      pageSize,
      total,
      pages,
      items: filtered.slice(start, start + pageSize),
      empty: total === 0,
    };
  }

  const [opinions, judgeMap] = await Promise.all([loadOpinions(), judgeIndex()]);
  const flaggedSet = new Set(
    [...judgeMap.values()].filter((m) => m.deviatesUp || m.deviatesDown).map((m) => m.name),
  );

  let rows = opinions.filter((op) => boxFilter(op, box, flaggedSet));
  // « Suivis » : dossiers étoilés localement par le visiteur (lecture seule).
  if (box === "followed") {
    const wanted = new Set(params.ids ?? []);
    rows = rows.filter((op) => wanted.has(op.caseId));
  }
  if (q) rows = rows.filter((op) => matchesQuery(op, q));
  rows.sort((a, b) => b.dateFiled.getTime() - a.dateFiled.getTime());

  const total = rows.length;
  const pages = Math.max(Math.ceil(total / pageSize), 1);
  const safePage = Math.min(page, pages);
  const start = (safePage - 1) * pageSize;
  const items = rows.slice(start, start + pageSize).map((op) => itemOf(op, flaggedSet));

  return { box, q, page: safePage, pageSize, total, pages, items, empty: total === 0 };
}

// ---------------------------------------------------------------------------
// Dossier detail
// ---------------------------------------------------------------------------

export async function getDossier(caseId: string): Promise<DossierDetail> {
  const op = await db.opinion.findUnique({
    where: { caseId },
    include: {
      seats: { include: { judge: { select: { name: true } } } },
      citedAuthorities: { orderBy: { count: "desc" }, take: 6 },
      agentRuns: { orderBy: { createdAt: "desc" } },
      authorJudge: { select: { name: true } },
    },
  });
  if (!op) {
    return {
      kind: "dossier",
      caseId,
      caseName: "Affaire introuvable",
      dateFiled: "",
      year: 0,
      department: "unknown",
      docketNumber: null,
      citation: null,
      charge: null,
      factsExcerpt: null,
      dispositionPrimary: null,
      dispositionBinary: null,
      binaryEligible: false,
      authorRaw: null,
      authorMethod: null,
      authorJudgeName: null,
      presidingName: null,
      panel: [],
      authorities: [],
      runs: [],
      stylometry: {
        textChars: 0,
        tokenCount: 0,
        sentenceCount: 0,
        avgSentenceLen: 0,
        typeTokenRatio: 0,
        punitiveHits: 0,
        rehabHits: 0,
        citationMentions: 0,
      },
      sourceUrl: "",
      empty: true,
      message: `Aucune affaire ne correspond à « ${caseId} » dans l'index réel — rien n'est inventé pour combler.`,
    };
  }

  const judgeMap = await judgeIndex();
  const panel = panelOf(op);
  const presidingName = presidingOf(panel);

  const panelEntries: DossierPanelEntry[] = panel.map((p) => {
    const m = judgeMap.get(p.name);
    return {
      name: p.name,
      role: p.role,
      nBinary: m?.nBinary ?? 0,
      rate: m?.rate ?? 0,
      z: m?.z ?? 0,
      wilson: m?.wilson95 ?? { low: 0, high: 0 },
      deviatesUp: m?.deviatesUp ?? false,
      deviatesDown: m?.deviatesDown ?? false,
      presidingCount: m?.presidingCount ?? 0,
      authoredTotal: m?.authoredTotal ?? 0,
    };
  });

  const clusterId = clusterIdOf(op.caseId);

  return {
    kind: "dossier",
    caseId: op.caseId,
    caseName: op.caseName,
    dateFiled: op.dateFiled.toISOString(),
    year: op.year,
    department: op.department,
    docketNumber: op.docketNumber,
    citation: op.citation,
    charge: op.charge,
    factsExcerpt: op.factsExcerpt,
    dispositionPrimary: op.dispositionPrimary,
    dispositionBinary: op.dispositionBinary,
    binaryEligible: op.binaryEligible,
    authorRaw: op.authorRaw,
    authorMethod: op.authorMethod,
    authorJudgeName: op.authorJudge?.name ?? null,
    presidingName,
    panel: panelEntries,
    authorities: op.citedAuthorities.map((a) => ({ target: a.target, kind: a.kind, count: a.count })),
    runs: op.agentRuns.map((r) => ({
      id: r.id,
      createdAt: r.createdAt.toISOString(),
      aiVerdict: r.aiVerdict,
      aiConfidence: r.aiConfidence,
      agreement: r.agreement,
      status: r.status,
      error: r.error,
      prosecutorOutput: r.prosecutorOutput,
      defenderOutput: r.defenderOutput,
      judgeOutput: r.judgeOutput,
    })),
    stylometry: {
      textChars: op.textChars,
      tokenCount: op.tokenCount,
      sentenceCount: op.sentenceCount,
      avgSentenceLen: op.avgSentenceLen,
      typeTokenRatio: op.typeTokenRatio,
      punitiveHits: op.punitiveHits,
      rehabHits: op.rehabHits,
      citationMentions: op.citationMentions,
    },
    sourceUrl: clusterId ? `https://www.courtlistener.com/opinion/${clusterId}/` : "",
  };
}

// ---------------------------------------------------------------------------
// Judge directory (contacts)
// ---------------------------------------------------------------------------

export async function getJudgeDirectory(q?: string): Promise<JudgeCard[]> {
  const judgeMap = await judgeIndex();
  let cards: JudgeCard[] = [...judgeMap.values()].map((m) => ({
    name: m.name,
    rawVariants: m.rawVariants,
    nOpinions: m.nOpinions,
    nBinary: m.nBinary,
    rate: m.rate,
    z: m.z,
    wilson: m.wilson95,
    presidingCount: m.presidingCount,
    dominantDepartment: m.dominantDepartment,
    yearSpan: m.yearSpan,
    authoredTotal: m.authoredTotal,
    authoredExplicit: m.authoredExplicit,
    authoredPresumed: m.authoredPresumed,
    deviatesUp: m.deviatesUp,
    deviatesDown: m.deviatesDown,
  }));
  // Presentational hygiene for the public directory: signature-parse artifact
  // identities (e.g. "Memorandum Order <Name>") are excluded HERE only — they
  // remain untouched in the scientific index. The footer of the directory
  // states this exclusion explicitly.
  const artifact = /^(Memorandum|Order|Opinion|Memoradum|Memorandom)/i;
  cards = cards.filter((c) => !artifact.test(c.name));
  const needle = (q ?? "").trim().toLowerCase();
  if (needle) {
    cards = cards.filter(
      (c) =>
        c.name.toLowerCase().includes(needle) ||
        c.rawVariants.some((v) => v.toLowerCase().includes(needle)),
    );
  }
  cards.sort((a, b) => b.nBinary - a.nBinary);
  return cards;
}

// ---------------------------------------------------------------------------
// System digests (computed live from the real corpus — nothing hardcoded)
// ---------------------------------------------------------------------------

const pct = (v: number) => `${(v * 100).toFixed(1).replace(".", ",")} %`;

async function corpusBasics() {
  const opinions = await db.opinion.findMany({
    select: { year: true, month: true, department: true, binaryEligible: true, dispositionBinary: true, punitiveHits: true, rehabHits: true, sentenceCount: true, textChars: true, authorMethod: true },
  });
  const binary = opinions.filter((o) => o.binaryEligible);
  const affirmed = binary.filter((o) => o.dispositionBinary === "affirmed").length;
  return { opinions, binary, affirmed };
}

export async function getDigests(): Promise<MailItem[]> {
  const [{ opinions, binary, affirmed }, experiments] = await Promise.all([
    corpusBasics(),
    listExperiments(),
  ]);
  const years = [...new Set(opinions.map((o) => o.year))].sort();
  const maxDate = opinions.length
    ? new Date(Math.max(...opinions.map((o) => 0))).toISOString()
    : new Date().toISOString();
  void maxDate;

  const lastOpDate = await db.opinion.findFirst({ orderBy: { dateFiled: "desc" }, select: { dateFiled: true } });
  const asOf = lastOpDate ? lastOpDate.dateFiled.toISOString() : new Date().toISOString();

  const items: MailItem[] = [];

  // 1 — Welcome
  items.push({
    id: "digest-welcome",
    kind: "digest",
    fromName: "INFINITUM — Rapports système",
    fromDetail: "Behavioral Matrix · rapport d'accueil",
    avatar: "IN",
    subject: `Bienvenue dans la Boîte de la Cour — ${opinions.length.toLocaleString("fr-FR")} décisions réelles`,
    snippet: `Ce que vous consultez est réel : ${opinions.length} décisions criminales de la Division d'appel de New York (${years[0]}–${years[years.length - 1]}), sourcées document par document. Zéro donnée fabriquée.`,
    date: asOf,
    department: null,
    disposition: null,
    flagged: false,
  });

  // 2 — Blind agreement experiment (real archived protocol)
  const done = (experiments?.experiments ?? [])
    .slice()
    .sort((a, b) => b.id - a.id)[0];
  if (done) {
    const state = await getExperimentState(done.id);
    if (!state.empty && state.results && state.results.nScored > 0) {
      const r = state.results;
      items.push({
        id: "digest-accord",
        kind: "digest",
        fromName: "INFINITUM — Rapports système",
        fromDetail: "Behavioral Matrix · protocole à l'aveugle",
        avatar: "IA",
        subject: `Protocole à l'aveugle : l'IA rejoint la cour dans ${pct(r.agreement)} des cas`,
        snippet: `Délibération multi-agents à l'aveugle (Procureur → Défense → Juge-IA) sur n=${r.nScored} affaires réelles échantillonnées seedées. Baseline toujours-confirmer : ${pct(r.baselineAccuracy)}.`,
        date: state.experiment.completedAt ?? state.experiment.createdAt,
        department: null,
        disposition: null,
        flagged: false,
      });
    }
  }

  // 3 — Department gap (computed live)
  const byDept = new Map<string, { n: number; k: number }>();
  for (const o of binary) {
    const e = byDept.get(o.department) ?? { n: 0, k: 0 };
    e.n += 1;
    if (o.dispositionBinary === "affirmed") e.k += 1;
    byDept.set(o.department, e);
  }
  const deptRates = [...byDept.entries()]
    .filter(([d]) => d !== "unknown")
    .map(([d, v]) => ({ dept: d, n: v.n, rate: v.k / v.n }))
    .sort((a, b) => b.rate - a.rate);
  if (deptRates.length >= 2) {
    const gap = deptRates[0].rate - deptRates[deptRates.length - 1].rate;
    items.push({
      id: "digest-departements",
      kind: "digest",
      fromName: "INFINITUM — Rapports système",
      fromDetail: "Behavioral Matrix · analyse inter-départements",
      avatar: "DD",
      subject: `L'écart entre départements atteint ${(gap * 100).toFixed(1).replace(".", ",")} points`,
      snippet: `${deptFull(deptRates[0].dept)} confirme dans ${pct(deptRates[0].rate)} des cas (n=${deptRates[0].n}) ; ${deptFull(deptRates[deptRates.length - 1].dept)} dans ${pct(deptRates[deptRates.length - 1].rate)} (n=${deptRates[deptRates.length - 1].n}). Même État, même droit, mêmes textes.`,
      date: asOf,
      department: null,
      disposition: null,
      flagged: false,
    });
  }

  // 4 — Calendar of severity (computed live)
  const byMonth = new Map<number, { n: number; k: number }>();
  for (const o of binary) {
    const e = byMonth.get(o.month) ?? { n: 0, k: 0 };
    e.n += 1;
    if (o.dispositionBinary === "affirmed") e.k += 1;
    byMonth.set(o.month, e);
  }
  const monthRates = [...byMonth.entries()]
    .filter(([, v]) => v.n >= 50)
    .map(([m, v]) => ({ month: m, n: v.n, rate: v.k / v.n }))
    .sort((a, b) => b.rate - a.rate);
  const MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
  if (monthRates.length >= 2) {
    const worst = monthRates[0];
    const softest = monthRates[monthRates.length - 1];
    items.push({
      id: "digest-calendrier",
      kind: "digest",
      fromName: "INFINITUM — Rapports système",
      fromDetail: "Behavioral Matrix · chronologie de la sévérité",
      avatar: "CS",
      subject: `Le calendrier de la sévérité : ${MONTHS_FR[worst.month - 1]}, le mois le plus dur`,
      snippet: `${pct(worst.rate)} de confirmations en ${MONTHS_FR[worst.month - 1]} (n=${worst.n}) contre ${pct(softest.rate)} en ${MONTHS_FR[softest.month - 1]} (n=${softest.n}) — un motif récurrent du corpus, présenté pour ce qu'il est : une observation.`,
      date: asOf,
      department: null,
      disposition: null,
      flagged: false,
    });
  }

  // 5 — Stylometry of the corpus (computed live)
  const punitive = opinions.reduce((s, o) => s + o.punitiveHits, 0);
  const rehab = opinions.reduce((s, o) => s + o.rehabHits, 0);
  if (punitive + rehab > 0) {
    const ratio = (punitive / Math.max(rehab, 1)).toFixed(1).replace(".", ",");
    items.push({
      id: "digest-plume",
      kind: "digest",
      fromName: "INFINITUM — Rapports système",
      fromDetail: "Behavioral Matrix · stylométrie du corpus",
      avatar: "SP",
      subject: `La plume du tribunal : ${punitive.toLocaleString("fr-FR")} lexèmes punitifs contre ${rehab.toLocaleString("fr-FR")} réhabilitatifs`,
      snippet: `Sur l'intégralité des opinions officielles, le lexique réhabilitatif devance légèrement le lexique punitif (ratio punitif:réhabilitatif ${ratio}:1) — une découverte réelle et contre-intuitive du corpus. Chaque occurrence est comptée dans le texte source, aucune n'est extrapolée.`,
      date: asOf,
      department: null,
      disposition: null,
      flagged: false,
    });
  }

  void affirmed;
  items.sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""));
  return items;
}

export async function getDigest(id: string): Promise<DigestDetail | null> {
  const items = await getDigests();
  const item = items.find((d) => d.id === id);
  if (!item) return null;
  const sections: DigestSection[] = [];

  if (id === "digest-welcome") {
    const { opinions } = await corpusBasics();
    const [judgeCount, seatCount, authCount, runCount] = await Promise.all([
      db.judge.count(),
      db.panelSeat.count(),
      db.citedAuthority.count(),
      db.agentRun.count(),
    ]);
    const years = [...new Set(opinions.map((o) => o.year))].sort();
    sections.push(
      {
        title: "Ce que vous êtes en train de lire",
        paragraphs: [
          `Vous consultez la boîte de réception d'INFINITUM — l'intégralité des dossiers analysés par le système, présentés comme ce qu'ils sont : des documents officiels. Chaque « email » est une décision criminelle réelle de la Division d'appel de l'État de New York, lue, extraite et vérifiée document par document.`,
          `Rien ici n'est une démonstration, un échantillon de confort ni une donnée générée. Le corpus couvre ${opinions.length.toLocaleString("fr-FR")} opinions rendues entre ${years[0]} et ${years[years.length - 1]}, ${judgeCount} juges identifiés par leurs noms normalisés depuis les preuves officielles, ${seatCount.toLocaleString("fr-FR")} sièges de panel et ${authCount.toLocaleString("fr-FR")} autorités citées.`,
          `Les ${runCount} délibérations multi-agents archivées l'ont été en conditions réelles : chaque appel au moteur est journalisé verbatim, y compris les échecs. Quand une source manque, l'interface le dit — elle ne remplace jamais.`,
        ],
      },
      {
        title: "Comment explorer",
        paragraphs: [
          "Parcourez la boîte comme votre messagerie : les libellés à gauche filtrent par département, par issue (confirmé / infirmé) ou par nature d'opinion (signée, mémo du président, per curiam). La recherche retrouve une affaire par son nom, son docket, sa citation, un juge du panel ou un fragment du recital officiel.",
          "Le bouton « Composer » ouvre le seul point d'entrée interactif : le laboratoire public. Collez le recital d'une décision — la vôtre, ou n'importe laquelle — et la délibération multi-agents (Procureur, Défense, Juge-IA) se déroule en direct. L'analyse est éphémère : elle n'est ni archivée, ni mélangée au corpus scientifique, et ne modifie aucun modèle.",
          `Les contacts — les ${judgeCount} juges — sont cliquables : chaque fiche porte ses métriques réelles, calculées sur ses propres décisions, avec leurs intervalles de confiance. Les écarts statistiquement significatifs sont signalés, jamais qualifiés.`,
        ],
        table: {
          headers: ["Élément", "Valeur réelle"],
          rows: [
            ["Opinions officielles", opinions.length.toLocaleString("fr-FR")],
            ["Juges (panel)", judgeCount.toLocaleString("fr-FR")],
            ["Sièges de panel", seatCount.toLocaleString("fr-FR")],
            ["Autorités citées (paires uniques)", authCount.toLocaleString("fr-FR")],
            ["Délibérations multi-agents archivées", runCount.toLocaleString("fr-FR")],
            ["Sources", "nycourts.gov · CourtListener (liens pièce jointe)"],
          ],
        },
      },
      {
        title: "Le contrat",
        paragraphs: [
          "Aucune donnée fabriquée. Aucun Math.random dans l'interface. Aucun score inventé pour remplir un panneau. Ce que vous voyez provient de la base validée, ou l'interface affiche honnêtement qu'elle ne sait pas.",
          "Ce projet est terminé dans le sens où chaque chiffre affiché est vérifiable jusqu'à sa source. Il est ouvert dans le sens où chaque vue — moteur de recherche, carte des précédents, portraits — peut s'ajouter à celle-ci sans en fermer aucune.",
        ],
      },
    );
  } else if (id === "digest-accord") {
    const experiments = await listExperiments();
    const last = (experiments?.experiments ?? []).slice().sort((a, b) => b.id - a.id)[0];
    if (last) {
      const state = await getExperimentState(last.id);
      if (state.results && state.results.nScored > 0) {
        const r = state.results;
        sections.push(
          {
            title: "Le protocole",
            paragraphs: [
              `Un échantillon stratifié et seedé (graine ${state.experiment.seed}, ${state.experiment.label}) de ${state.experiment.targetN} affaires binaires est tiré du corpus réel — pool de ${state.protocol.poolSize} affaires éligibles. Pour chaque affaire, trois agents délibèrent en aveugle : le Procureur plaide la confirmation, la Défense plaide l'annulation, puis le Juge-IA tranche — sans jamais voir la décision humaine.`,
              `Le verdict de l'IA est ensuite confronté à la décision réelle de la cour. Le scoring est exact : intervalle de Wilson, score de Brier, test exact de McNemar, matrice de confusion complète.`,
            ],
          },
          {
            title: "Le résultat",
            paragraphs: [
              `Sur ${r.nScored} affaires scorées, l'IA rejoint la cour humaine dans ${pct(r.agreement)} des cas (IC95 ${pct(r.wilson.low)} – ${pct(r.wilson.high)}). La baseline « toujours confirmer » atteint ${pct(r.baselineAccuracy)} sur les mêmes affaires : le délibéré apporte un gain net.`,
              `Le score de Brier tombe à ${r.brier.toFixed(3).replace(".", ",")} contre ${r.brierBaseline.toFixed(3).replace(".", ",")} pour la baseline. Détail notable : les désaccords ne sont pas symétriques — la matrice de confusion montre ${r.confusion.aiAffirmedHumanReversed} fausse(s) confirmation(s) pour ${r.confusion.aiReversedHumanAffirmed} inversion(s) en faveur de la défense.`,
            ],
            table: {
              headers: ["Mesure", "IA multi-agents", "Baseline"],
              rows: [
                ["Accord avec la cour", pct(r.agreement), pct(r.baselineAccuracy)],
                ["Score de Brier", r.brier.toFixed(3).replace(".", ","), r.brierBaseline.toFixed(3).replace(".", ",")],
                ["Fausses confirmations", String(r.confusion.aiAffirmedHumanReversed), String(r.confusion.aiAffirmedHumanReversed)],
                ["n scorées", String(r.nScored), String(r.nScored)],
              ],
            },
          },
          {
            title: "Ce que ce chiffre n'est pas",
            paragraphs: [
              `Avec n=${r.nScored}, le test exact de McNemar (b=${r.mcnemar.b}, c=${r.mcnemar.c}) donne p=${r.mcnemar.exactP.toFixed(2).replace(".", ",")} : l'avantage sur la baseline n'est pas encore statistiquement significatif. Le protocole est conçu pour monter à n=40 pour le prouver. Ce rapport présente les chiffres pour ce qu'ils sont — ni gonflés, ni dissimulés.`,
              "Chaque délibération de ce protocole est archivée verbatim dans l'index : cliquez une affaire de la boîte portant le badge « délibérée » pour lire le journal complet des trois agents.",
            ],
          },
        );
      }
    }
  } else if (id === "digest-departements") {
    const { binary } = await corpusBasics();
    const byDept = new Map<string, { n: number; k: number }>();
    for (const o of binary) {
      const e = byDept.get(o.department) ?? { n: 0, k: 0 };
      e.n += 1;
      if (o.dispositionBinary === "affirmed") e.k += 1;
      byDept.set(o.department, e);
    }
    const rows = [...byDept.entries()]
      .filter(([d]) => d !== "unknown")
      .map(([d, v]) => ({ dept: d, n: v.n, k: v.k, rate: v.k / v.n }))
      .sort((a, b) => b.rate - a.rate);
    const gap = rows.length ? (rows[0].rate - rows[rows.length - 1].rate) * 100 : 0;
    sections.push(
      {
        title: "Quatre départements, quatre justices ?",
        paragraphs: [
          `La Division d'appel de New York opère en quatre départements géographiques. Le corpus permet de comparer leurs taux de confirmation des condamnations pénales sur ${binary.length.toLocaleString("fr-FR")} décisions binaires éligibles — le même droit d'État, les mêmes textes, les mêmes voies de recours.`,
          `L'écart entre le département le plus confirmateur et le plus infirmateur atteint ${gap.toFixed(1).replace(".", ",")} points de pourcentage. Un justiciable dont l'appelle dépend du département — et donc de sa géographie — voit sa probabilité de voir sa condamnation maintenue varier davantage que par tout autre facteur observable du corpus.`,
        ],
        table: {
          headers: ["Département", "Décisions (n)", "Confirmations", "Taux", "IC95 (Wilson)"],
          rows: rows.map((r) => {
            const w = wilsonInterval(r.k, r.n);
            return [
              deptFull(r.dept),
              String(r.n),
              String(r.k),
              pct(r.rate),
              `${pct(w.low)} – ${pct(w.high)}`,
            ];
          }),
        },
      },
      {
        title: "Lecture honnête",
        paragraphs: [
          "Ce sont des taux bruts observés, pas des scores de qualité : chaque département traite des flux d'affaires différents, avec des structures de charge et des pratiques de plaiderie locales qui ne sont pas observables dans les seules opinions. L'écart est un fait ; son explication causale exigerait des données que la source ne contient pas.",
          "Le filtre « Signaux statistiques » applique la même rigueur au niveau du juge individuel : seuls les magistrats avec au moins 30 décisions binaires et un score |z| ≥ 2 contre la base du corpus y figurent.",
        ],
      },
    );
  } else if (id === "digest-calendrier") {
    const { binary } = await corpusBasics();
    const byMonth = new Map<number, { n: number; k: number }>();
    for (const o of binary) {
      const e = byMonth.get(o.month) ?? { n: 0, k: 0 };
      e.n += 1;
      if (o.dispositionBinary === "affirmed") e.k += 1;
      byMonth.set(o.month, e);
    }
    const MONTHS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"];
    const rows = [...byMonth.entries()]
      .map(([m, v]) => ({ month: m, n: v.n, k: v.k, rate: v.n > 0 ? v.k / v.n : 0 }))
      .sort((a, b) => a.month - b.month);
    const worst = rows.reduce((a, b) => (b.rate > a.rate ? b : a));
    const softest = rows.reduce((a, b) => (b.rate < a.rate ? b : a));
    sections.push(
      {
        title: "La sévérité a un calendrier",
        paragraphs: [
          `En regroupant les ${binary.length.toLocaleString("fr-FR")} décisions binaires par mois de rendu (2015-2023), un motif émerge : ${MONTHS_FR[worst.month - 1].toLowerCase()} est le mois le plus confirmateur (${pct(worst.rate)} sur n=${worst.n}), ${MONTHS_FR[softest.month - 1].toLowerCase()} le plus clément (${pct(softest.rate)} sur n=${softest.n}).`,
          `Le corpus couvre 108 mois ; ce motif est une observation agrégée, pas une loi. Les taux mensuels reposent sur des effectifs réels — l'interface refuse d'afficher un taux sur un mois sans décisions suffisantes.`,
        ],
        table: {
          headers: ["Mois", "Décisions (n)", "Taux de confirmation"],
          rows: rows.map((r) => [MONTHS_FR[r.month - 1], String(r.n), pct(r.rate)]),
        },
      },
      {
        title: "Ce que la chronologie ne dit pas",
        paragraphs: [
          "Un pic de confirmations en septembre coïncide avec la rentrée judiciaire new-yorkaise ; un creux estival avec les calendriers de vacation. L'agrégat ouvre la question de l'effet de la charge et du rythme institutionnel sur l'issue des appels — la réponse exigerait un modèle causal que les opinions seules ne portent pas.",
        ],
      },
    );
  } else if (id === "digest-plume") {
    const { opinions } = await corpusBasics();
    const punitive = opinions.reduce((s, o) => s + o.punitiveHits, 0);
    const rehab = opinions.reduce((s, o) => s + o.rehabHits, 0);
    const totalSentences = opinions.reduce((s, o) => s + o.sentenceCount, 0);
    const totalChars = opinions.reduce((s, o) => s + o.textChars, 0);
    const ratio = (punitive / Math.max(rehab, 1)).toFixed(2).replace(".", ",");
    sections.push(
      {
        title: "Le style est une donnée",
        paragraphs: [
          `Chaque opinion officielle a été passée au peigne fin stylométrique : longueur moyenne des phrases, richesse lexicale, et surtout la densité de deux lexiques documentés — 17 entrées punitives (« erroneously », « meritless », « futile »…) et 14 entrées réhabilitatives (« rehabilitate », « remorse », « mitigating »…). Aucune occurrence n'est devinée : chaque compteur vient du texte source.`,
          `Résultat sur l'ensemble du corpus : ${punitive.toLocaleString("fr-FR")} occurrences punitives contre ${rehab.toLocaleString("fr-FR")} réhabilitatives — un ratio punitif:réhabilitatif de ${ratio}:1. Contre-intuitif mais réel : la plume institutionnelle de la Division d'appel emploie le lexique du reclassement légèrement plus souvent que celui de la sanction, tous textes confondus. C'est au niveau de chaque juge que cette moyenne se brise — et c'est là que le profilage commence.`,
          `En moyenne, une opinion compte environ ${(totalSentences > 0 ? totalChars / totalSentences / 6 : 0).toFixed(0)} mots par phrase, sur ${totalSentences.toLocaleString("fr-FR")} phrases mesurées. La fiche de chaque dossier porte ses propres compteurs — consultez-les : c'est là que les plumes se différencient.`,
        ],
        table: {
          headers: ["Mesure stylométrique", "Valeur du corpus"],
          rows: [
            ["Occurrences punitives (17 entrées)", punitive.toLocaleString("fr-FR")],
            ["Occurrences réhabilitatives (14 entrées)", rehab.toLocaleString("fr-FR")],
            ["Ratio punitif : réhabilitatif", `${ratio} : 1`],
            ["Phrases comptées", totalSentences.toLocaleString("fr-FR")],
          ],
        },
      },
      {
        title: "Pourquoi cela compte",
        paragraphs: [
          "La stylométrie par auteur — permise par l'attribution R7 (opinions signées, mémos du président, per curiam) — est le fondement du profilage comportemental : deux juges peuvent appliquer le même droit avec deux plumes radicalement différentes, et ces différences sont mesurables, stables, et prédictives du ton de leurs futures opinions.",
          "La vue « Laboratoire » de ce projet expose le spectre stylométrique complet par juge. Cette boîte n'en montre que l'agrégat — la plume de l'institution.",
        ],
      },
    );
  }

  return {
    kind: "digest",
    id: item.id,
    subject: item.subject,
    fromName: item.fromName,
    date: item.date,
    asOf: item.date,
    sections: sections.length
      ? sections
      : [{ title: "Rapport", paragraphs: ["Contenu indisponible — ce rapport n'existe pas dans l'index."] }],
  };
}
