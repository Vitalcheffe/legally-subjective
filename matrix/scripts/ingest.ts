/**
 * Behavioral Matrix — real-data ingestion (ZERO MOCK, ZERO HARD-CODE).
 *
 * Source of truth: the validated Phase 2 corpus of legally-subjective —
 *   data/structured/corpus_structured.jsonl   (1,387 real criminal appeals,
 *                                              extraction evidence attached)
 *   data/corpus/documents/<cluster_id>.html   (the official opinion documents)
 *   data/analysis/base_rate_corpus.json       (official stats used for
 *                                              automatic cross-validation)
 *
 * This script is a derived INDEX builder. It never modifies the source data.
 * Every derived field is deterministic and its rule is documented below.
 * If a source document is missing, the corresponding fields stay empty/zero —
 * absence is recorded, never faked.
 *
 * Deterministic rules applied here:
 *   R1  Judge identity = normalized surname of the official panel line.
 *       Junk tokens (P.J., J.P., JJ, AND, Department prefixes) dropped;
 *       casing normalized; suffixes normalized (Jr → Jr., III...).
 *   R2  Department = first "Appellate Division, <ord> Department" match in
 *       the official document header — byte-identical behavior to the repo's
 *       analyze_base_rate block (same regex, same normalization map), so the
 *       index always agrees with the validated analysis. "unknown" when
 *       absent (kept unknown, never guessed).
 *   R3  Opinion text = document HTML minus <script>/<style> blocks and tags,
 *       entities decoded, whitespace collapsed.
 *   R4  Stylometry (tokens, sentences, TTR, punitive/rehab lexicon hits) is
 *       computed on the text from R3 with the lexicons defined below.
 *   R5  Cited authorities = regex-extracted NY case citations and statutory
 *       references from the text from R3.
 *   R6  Cross-validation against data/analysis/base_rate_corpus.json:
 *       record counts, binary split, per-year and per-department figures
 *       must match the official analysis or the script exits non-zero.
 */
import { PrismaClient } from "@prisma/client";
import { readFileSync, existsSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";

process.env.DATABASE_URL ||= "file:/home/z/my-project/db/custom.db";
const db = new PrismaClient({ log: ["error", "warn"] });

// ---------------------------------------------------------------------------
// Corpus location resolution (no hard-coded absolute dependency)
// ---------------------------------------------------------------------------
const PROJECT_ROOT = resolve(__dirname, "..");
const CANDIDATES = [
  process.env.CORPUS_ROOT,
  join(PROJECT_ROOT, "legally-subjective"),
  join(PROJECT_ROOT, "..", "legally-subjective"),
].filter(Boolean) as string[];

const CORPUS_ROOT = CANDIDATES.find((p) =>
  existsSync(join(p, "data", "structured", "corpus_structured.jsonl")),
);
if (!CORPUS_ROOT) {
  console.error(
    "FATAL: corpus root not found. Set CORPUS_ROOT or place legally-subjective next to this project.",
  );
  process.exit(1);
}
console.log(`[ingest] corpus root: ${CORPUS_ROOT}`);

// ---------------------------------------------------------------------------
// R1 — judge name normalization
// ---------------------------------------------------------------------------
const JUNK_TOKENS = new Set([
  "J", "JJ", "JP", "PJ", "AND", "DEPT", "DEPARTMENT",
]);
const SUFFIX_MAP: Record<string, string> = {
  jr: "Jr.", sr: "Sr.", ii: "II", iii: "III", iv: "IV",
};

export function normalizeJudgeName(raw: string): string | null {
  let s = raw.replace(/\s+/g, " ").trim();
  s = s.replace(/^[^A-Za-z]+/, "").replace(/[^A-Za-z.'’-]+$/, "");
  if (!s) return null;
  const tokens = s.split(" ").filter((t) => t.length > 0);
  const kept: string[] = [];
  for (const t of tokens) {
    const bare = t.toUpperCase().replace(/\./g, "").replace(/,$/, "");
    if (JUNK_TOKENS.has(bare)) continue;
    kept.push(t);
  }
  while (kept.length && /^department$/i.test(kept[0])) kept.shift();
  if (kept.length === 0) return null;

  const parts = kept.map((t) => {
    const up = t.toUpperCase().replace(/\.$/, "");
    if (SUFFIX_MAP[up]) return SUFFIX_MAP[up];
    return t
      .toLowerCase()
      .replace(/(^|['’\-])([a-z])/g, (_m, p1: string, p2: string) => p1 + p2.toUpperCase());
  });
  const name = parts.join(" ").replace(/\s+/g, " ").trim();
  if (name.replace(/[^A-Za-z]/g, "").length < 3) return null;
  if (/^per curiam$/i.test(name)) return null; // institutional author, not a judge
  return name;
}

// ---------------------------------------------------------------------------
// R2 — department extraction (byte-identical to the repo's analyze_base_rate)
// ---------------------------------------------------------------------------
const DEPT_RX =
  /appellate\s+division[,\s]+(first|second|third|fourth|1st|2d|2nd|3d|3rd|4th)\s+department/i;
const DEPT_NORM: Record<string, string> = {
  "1st": "1st", first: "1st",
  "2d": "2nd", "2nd": "2nd", second: "2nd",
  "3d": "3rd", "3rd": "3rd", third: "3rd",
  "4th": "4th", fourth: "4th",
};
function extractDepartment(rawHtml: string): string {
  const m = rawHtml.match(DEPT_RX);
  if (!m) return "unknown";
  return DEPT_NORM[m[1].toLowerCase()] ?? "unknown";
}

// ---------------------------------------------------------------------------
// R3 — HTML → text
// ---------------------------------------------------------------------------
export function htmlToText(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(p|div|tr|li)>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&rsquo;|&apos;/gi, "'")
    .replace(/&lsquo;/gi, "'")
    .replace(/&ldquo;|&rdquo;/gi, '"')
    .replace(/&sect;/gi, "§")
    .replace(/&para;/gi, "¶")
    .replace(/[ \t]+/g, " ")
    .replace(/\n\s*\n\s*\n+/g, "\n\n")
    .trim();
}

// ---------------------------------------------------------------------------
// R4 — stylometry
// ---------------------------------------------------------------------------
// Lexicons: stems are counted as substrings (catch inflections);
// multi-word terms counted verbatim, case-insensitive. Lists are documented
// methodology, not data.
const PUNITIVE_TERMS = [
  "retribution", "punish", "punitive", "deterrence", "deterrent",
  "heinous", "egregious", "depraved", "predatory", "maximum term",
  "consecutive", "violent felony", "dangerous", "vicious", "brutal",
  "menace", "scourge",
];
const REHAB_TERMS = [
  "rehabilitat", "mitigat", "treatment", "probation", "diversion",
  "youthful offender", "lenienc", "mercy", "restor", "reintegrat",
  "redempt", "alternative to incarceration", "alternatives to incarceration",
  "reform",
];

function countTerm(textLower: string, term: string): number {
  let idx = 0, count = 0;
  for (;;) {
    const found = textLower.indexOf(term, idx);
    if (found === -1) break;
    count += 1;
    idx = found + term.length;
  }
  return count;
}

export function computeStylometry(text: string) {
  const lower = text.toLowerCase();
  const tokens = lower.match(/[a-z][a-z']*/g) ?? [];
  const sentences = text.match(/[^.!?]+[.!?]+/g) ?? [];
  const types = new Set(tokens);
  let punitiveHits = 0;
  for (const t of PUNITIVE_TERMS) punitiveHits += countTerm(lower, t);
  let rehabHits = 0;
  for (const t of REHAB_TERMS) rehabHits += countTerm(lower, t);
  return {
    textChars: text.length,
    tokenCount: tokens.length,
    sentenceCount: sentences.length,
    avgSentenceLen: sentences.length > 0 ? text.length / sentences.length : 0,
    typeTokenRatio: tokens.length > 0 ? types.size / tokens.length : 0,
    punitiveHits,
    rehabHits,
  };
}

// ---------------------------------------------------------------------------
// R5 — citation extraction
// ---------------------------------------------------------------------------
export interface CitedTarget { target: string; kind: "case" | "statute"; count: number }

const CASE_CITE_RX = new RegExp(
  "\\b((?:People|Matter\\s+of|In\\s+re)\\s+v\\.?\\s+[A-Z][A-Za-z'’.\\-]*" +
  "(?:\\s+[A-Z][A-Za-z'’.\\-]*){0,3})\\s*,?\\s*\\(\\s*(?:\\d{4}\\s+)?" +
  "(?:N\\.?Y\\.?3d|N\\.?Y\\.?2d|A\\.?D\\.?3d|A\\.?D\\.?2d|N\\.?Y\\.?S\\.?[23]d|NY\\s+Slip\\s+Op)",
  "g",
);
const STATUTE_RX =
  /\b(CPL|CPLR|Penal Law|Correction Law|Executive Law|Judiciary Law|Family Court Act|Vehicle and Traffic Law)\s+§?\s*(\d+(?:\.\d+)*)/g;

export function extractCitations(text: string): { targets: CitedTarget[]; caseMentionCount: number } {
  const counts = new Map<string, CitedTarget>();
  let caseMentionCount = 0;

  for (const m of text.matchAll(CASE_CITE_RX)) {
    const raw = m[1].replace(/\s+/g, " ").replace(/,$/, "").trim();
    if (!raw) continue;
    const key = `case:${raw}`;
    const entry = counts.get(key) ?? { target: raw, kind: "case" as const, count: 0 };
    entry.count += 1;
    counts.set(key, entry);
    caseMentionCount += 1;
  }
  for (const m of text.matchAll(STATUTE_RX)) {
    const raw = `${m[1]} ${m[2]}`;
    const key = `statute:${raw}`;
    const entry = counts.get(key) ?? { target: raw, kind: "statute" as const, count: 0 };
    entry.count += 1;
    counts.set(key, entry);
  }
  return { targets: [...counts.values()], caseMentionCount };
}

// ---------------------------------------------------------------------------
// Ingestion
// ---------------------------------------------------------------------------
interface RawStructured {
  case_id: string;
  case_name: string;
  court: { id: string; name: string };
  date_filed: string;
  docket_number?: string;
  citations?: string[];
  window: string;
  panel?: {
    judges?: { name: string; role?: string }[];
    presiding?: string | null;
    evidence?: string;
  };
  charge?: { value?: string | null };
  facts?: { recital_excerpt?: { value?: string | null } };
  disposition?: {
    primary?: string | null;
    binary?: string | null;
    binary_eligible?: boolean;
  };
}
interface RawCase {
  cluster_id: number;
  document_path?: string;
  document_sha256?: string;
  document_channel?: string;
}

function readJsonl(path: string): unknown[] {
  const out: unknown[] = [];
  for (const line of readFileSync(path, "utf-8").split("\n")) {
    const t = line.trim();
    if (t) out.push(JSON.parse(t));
  }
  return out;
}

async function main() {
  const structuredPath = join(CORPUS_ROOT, "data", "structured", "corpus_structured.jsonl");
  const casesPath = join(CORPUS_ROOT, "data", "corpus", "cases.jsonl");
  const basePath = join(CORPUS_ROOT, "data", "analysis", "base_rate_corpus.json");
  const docsDir = join(CORPUS_ROOT, "data", "corpus", "documents");

  const records = readJsonl(structuredPath) as RawStructured[];
  const caseRows = readJsonl(casesPath) as RawCase[];
  const docByCluster = new Map<number, RawCase>();
  for (const c of caseRows) docByCluster.set(c.cluster_id, c);

  const availableDocs = new Set(readdirSync(docsDir).map((f) => f.replace(/\.html$/, "")));

  // Full deterministic rebuild — the DB is an index, not a source of truth.
  await db.citedAuthority.deleteMany();
  await db.panelSeat.deleteMany();
  await db.agentRun.deleteMany();
  await db.opinion.deleteMany();
  await db.judge.deleteMany();

  // Pass 1 — judges
  const judgeRaws = new Map<string, Set<string>>();
  const seatRows: { judgeName: string; caseId: string; role: string }[] = [];
  const presidingFromEvidence = (r: RawStructured): string | null => {
    const p = r.panel?.presiding;
    if (p) return p;
    const ev = r.panel?.evidence ?? "";
    const m = ev.match(/Decided on [^.]+\s+([A-Z][A-Za-z.'’\- ]+?),\s*J\.P\./);
    return m ? m[1] : null;
  };

  for (const r of records) {
    const presidingRaw = presidingFromEvidence(r);
    const presidingNorm = presidingRaw ? normalizeJudgeName(presidingRaw) : null;
    for (const j of r.panel?.judges ?? []) {
      const norm = normalizeJudgeName(j.name);
      if (!norm) continue;
      if (!judgeRaws.has(norm)) judgeRaws.set(norm, new Set());
      judgeRaws.get(norm)!.add(j.name);
      seatRows.push({
        judgeName: norm,
        caseId: r.case_id,
        role: presidingNorm && norm === presidingNorm ? "presiding" : "panel",
      });
    }
  }
  console.log(
    `[ingest] judges: ${judgeRaws.size} normalized identities from ${seatRows.length} panel seats`,
  );

  const judgeIdByName = new Map<string, number>();
  for (const [name, raws] of judgeRaws) {
    const j = await db.judge.create({
      data: { name, rawVariants: JSON.stringify([...raws].sort()) },
    });
    judgeIdByName.set(name, j.id);
  }

  // Pass 2 — opinions (+ stylometry + citations from the official documents)
  const opinionIdByCase = new Map<string, number>();
  const citationRows: { caseId: string; target: string; kind: string; count: number }[] = [];
  let missingDocs = 0, unknownDept = 0;
  const stylometryAccum = { opinionsWithText: 0 };

  for (const r of records) {
    const cluster = Number(r.case_id.split("-")[1]);
    const docMeta = docByCluster.get(cluster);
    const docKey = String(cluster);
    const docPath = docMeta?.document_path
      ? join(CORPUS_ROOT, docMeta.document_path)
      : join(docsDir, `${cluster}.html`);

    let rawHtml: string | null = null;
    if (availableDocs.has(docKey) && existsSync(docPath)) {
      rawHtml = readFileSync(docPath, "utf-8");
    } else {
      missingDocs += 1;
    }

    const department = rawHtml ? extractDepartment(rawHtml) : "unknown";
    if (department === "unknown") unknownDept += 1;

    let styl = {
      textChars: 0, tokenCount: 0, sentenceCount: 0,
      avgSentenceLen: 0, typeTokenRatio: 0, punitiveHits: 0, rehabHits: 0,
    };
    let citationMentions = 0;
    if (rawHtml) {
      const text = htmlToText(rawHtml);
      styl = computeStylometry(text);
      if (styl.textChars > 200) stylometryAccum.opinionsWithText += 1;
      const { targets, caseMentionCount } = extractCitations(text);
      citationMentions = caseMentionCount;
      for (const t of targets) {
        citationRows.push({ caseId: r.case_id, target: t.target, kind: t.kind, count: t.count });
      }
    }

    const date = new Date(r.date_filed + "T12:00:00Z");
    const op = await db.opinion.create({
      data: {
        caseId: r.case_id,
        caseName: r.case_name,
        courtId: r.court?.id ?? "nyappdiv",
        docketNumber: r.docket_number ?? null,
        dateFiled: date,
        year: date.getUTCFullYear(),
        month: date.getUTCMonth() + 1,
        window: r.window,
        department,
        citation: r.citations?.[0] ?? null,
        charge: r.charge?.value ?? null,
        factsExcerpt: r.facts?.recital_excerpt?.value ?? null,
        dispositionPrimary: r.disposition?.primary ?? null,
        dispositionBinary: r.disposition?.binary ?? null,
        binaryEligible: Boolean(r.disposition?.binary_eligible),
        ...styl,
        citationMentions,
      },
    });
    opinionIdByCase.set(r.case_id, op.id);
  }
  console.log(
    `[ingest] opinions: ${opinionIdByCase.size}; missing documents: ${missingDocs}; ` +
    `unknown department: ${unknownDept}; with text: ${stylometryAccum.opinionsWithText}`,
  );

  // Pass 3 — panel seats
  let seatsWritten = 0;
  const seatBatch: { judgeId: number; opinionId: number; role: string }[] = [];
  for (const s of seatRows) {
    const judgeId = judgeIdByName.get(s.judgeName);
    const opinionId = opinionIdByCase.get(s.caseId);
    if (!judgeId || !opinionId) continue;
    seatBatch.push({ judgeId, opinionId, role: s.role });
    seatsWritten += 1;
  }
  // de-duplicate (same judge twice on one opinion in raw data)
  const seen = new Set<string>();
  const deduped = seatBatch.filter((s) => {
    const k = `${s.judgeId}:${s.opinionId}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  await db.panelSeat.createMany({ data: deduped });
  console.log(`[ingest] panel seats: ${deduped.length} (from ${seatsWritten} raw)`);

  // Pass 4 — cited authorities
  const citeAccum = new Map<string, { opinionId: number; target: string; kind: string; count: number }>();
  for (const c of citationRows) {
    const opinionId = opinionIdByCase.get(c.caseId);
    if (!opinionId) continue;
    const key = `${opinionId}|${c.kind}|${c.target}`;
    const entry = citeAccum.get(key) ??
      { opinionId, target: c.target, kind: c.kind, count: 0 };
    entry.count += c.count;
    citeAccum.set(key, entry);
  }
  await db.citedAuthority.createMany({ data: [...citeAccum.values()] });
  console.log(
    `[ingest] cited authorities: ${citeAccum.size} unique (opinion,target) pairs, ` +
    `${[...citeAccum.values()].reduce((a, b) => a + b.count, 0)} total mentions`,
  );

  // ------------------------------------------------------------------
  // R6 — cross-validation against the official analysis
  // ------------------------------------------------------------------
  const base = JSON.parse(readFileSync(basePath, "utf-8")) as {
    records: number;
    binary: { affirmed: number; reversed_vacated: number; n: number };
    by_year: Record<string, { n: number; affirmed: number }>;
    by_department: Record<string, { n: number; affirmed: number }>;
  };
  const dbRecords = await db.opinion.count();
  const dbBinary = await db.opinion.count({ where: { binaryEligible: true } });
  const dbAffirmed = await db.opinion.count({
    where: { binaryEligible: true, dispositionBinary: "affirmed" },
  });
  const dbReversed = await db.opinion.count({
    where: { binaryEligible: true, dispositionBinary: "reversed_vacated" },
  });

  const checks: { name: string; expected: number; got: number; pass: boolean }[] = [
    { name: "total records", expected: base.records, got: dbRecords, pass: false },
    { name: "binary eligible", expected: base.binary.n, got: dbBinary, pass: false },
    { name: "binary affirmed", expected: base.binary.affirmed, got: dbAffirmed, pass: false },
    { name: "binary reversed_vacated", expected: base.binary.reversed_vacated, got: dbReversed, pass: false },
  ];
  for (const c of checks) c.pass = c.expected === c.got;

  let yearFails = 0;
  for (const [year, exp] of Object.entries(base.by_year)) {
    const got = await db.opinion.groupBy({
      by: ["dispositionBinary"],
      where: { year: Number(year), binaryEligible: true },
      _count: { _all: true },
    });
    const affirmed = got.find((g) => g.dispositionBinary === "affirmed")?._count._all ?? 0;
    const n = got.reduce((a, b) => a + b._count._all, 0);
    if (n !== exp.n || affirmed !== exp.affirmed) {
      yearFails += 1;
      console.error(
        `[validation] year ${year}: expected n=${exp.n} affirmed=${exp.affirmed}, got n=${n} affirmed=${affirmed}`,
      );
    }
  }
  checks.push({
    name: "by-year breakdown", expected: 0, got: yearFails, pass: yearFails === 0,
  });

  let deptFails = 0;
  const dbDept = await db.opinion.groupBy({
    by: ["department", "dispositionBinary"],
    where: { binaryEligible: true },
    _count: { _all: true },
  });
  const deptAgg = new Map<string, { n: number; affirmed: number }>();
  for (const row of dbDept) {
    const cur = deptAgg.get(row.department) ?? { n: 0, affirmed: 0 };
    cur.n += row._count._all;
    if (row.dispositionBinary === "affirmed") cur.affirmed = row._count._all;
    deptAgg.set(row.department, cur);
  }
  for (const [dept, exp] of Object.entries(base.by_department)) {
    const got = deptAgg.get(dept) ?? { n: 0, affirmed: 0 };
    if (got.n !== exp.n || got.affirmed !== exp.affirmed) {
      deptFails += 1;
      console.error(
        `[validation] dept ${dept}: expected n=${exp.n} affirmed=${exp.affirmed}, got n=${got.n} affirmed=${got.affirmed}`,
      );
    }
  }
  checks.push({
    name: "by-department breakdown", expected: 0, got: deptFails, pass: deptFails === 0,
  });

  console.log("\n[validation] cross-check vs data/analysis/base_rate_corpus.json");
  for (const c of checks) {
    console.log(
      `  ${c.pass ? "PASS" : "FAIL"}  ${c.name}: expected=${c.expected} got=${c.got}`,
    );
  }
  const allPass = checks.every((c) => c.pass);
  console.log(`\n[ingest] ${allPass ? "ALL CHECKS PASSED" : "VALIDATION FAILED"}`);

  await db.$disconnect();
  if (!allPass) process.exit(2);
}

main().catch(async (e) => {
  console.error(e);
  await db.$disconnect();
  process.exit(1);
});
