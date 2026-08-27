/**
 * Docket access — the FILED record, read from the repository itself.
 * Server-side only. Nothing here is invented: every field comes from
 * data/dockets/*.json (immutable, sha256-sealed) and data/productions/*.
 */
import { readFile, readdir } from "fs/promises";
import path from "path";

export interface AxisResult {
  percentile: number | null;
  ci95: number[] | null;
  n: number;
  status: string;
  value?: number;
  metric?: string;
  metric_def?: string;
  sources?: string[];
  note?: string;
}

export interface Docket {
  standard: string;
  docket: string;
  revision: number;
  subject: {
    name: string;
    slug: string;
    role: string;
    court: string;
    bench: string;
    bench_n: number;
    small_bench: boolean;
  };
  status: string;
  filed_at: string;
  window: { start: string; end: string };
  raw: {
    merits_votes: number;
    lead_opinions: number;
    service_years_window: number;
    separate_writings: number;
    dissents: number;
  };
  axes: Record<string, AxisResult>;
  projections: Record<string, unknown>;
  limits: string[];
  chain: { computed_at: string; pipeline: string; sha256?: string };
}

export interface Agreement {
  computed_at: string;
  window: { start: string; end: string };
  basis: string;
  sources: string[];
  pairs: Record<string, { n: number; agree: number | null }>;
}

export const AXIS_ORDER = [
  "disposition",
  "temperament",
  "precedent",
  "reversal",
  "orality",
  "exposure",
] as const;

export const AXIS_LABELS: Record<string, string> = {
  disposition: "Disposition",
  temperament: "Temperament",
  precedent: "Precedent",
  reversal: "Reversal",
  orality: "Orality",
  exposure: "Exposure",
};

export const AXIS_METRIC_LABELS: Record<string, string> = {
  disposition: "petitioner-alignment rate",
  temperament: "dissent rate",
  precedent: "citation density",
  exposure: "publication rate",
};

export async function listDockets(): Promise<Docket[]> {
  const dir = path.join(process.cwd(), "data", "dockets");
  const files = (await readdir(dir)).filter(
    (f) => f.startsWith("LS-J-") && f.endsWith(".json"),
  );
  const dockets = await Promise.all(
    files.map(async (f) =>
      JSON.parse(await readFile(path.join(dir, f), "utf8")) as Docket,
    ),
  );
  return dockets.sort((a, b) => a.docket.localeCompare(b.docket));
}

export async function getDocket(id: string): Promise<Docket | null> {
  const safe = id.match(/^[A-Za-z0-9-]+$/)?.[0];
  if (!safe) return null;
  try {
    return JSON.parse(
      await readFile(
        path.join(process.cwd(), "data", "dockets", `${safe}.json`),
        "utf8",
      ),
    ) as Docket;
  } catch {
    return null;
  }
}

export async function getAgreement(): Promise<Agreement | null> {
  try {
    return JSON.parse(
      await readFile(
        path.join(process.cwd(), "data", "productions", "agreement.json"),
        "utf8",
      ),
    ) as Agreement;
  } catch {
    return null;
  }
}

export function agreementPair(
  agreement: Agreement | null,
  a: string,
  b: string,
): { n: number; agree: number | null } | null {
  if (!agreement) return null;
  const key1 = `${a}|${b}`;
  const key2 = `${b}|${a}`;
  return agreement.pairs[key1] ?? agreement.pairs[key2] ?? null;
}

/** Bluebook-style citation per LS-1.0 §7. */
export function citation(d: Docket): string {
  const [year, month, day] = d.filed_at.slice(0, 10).split("-");
  const months = [
    "Jan.", "Feb.", "Mar.", "Apr.", "May", "June",
    "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.",
  ];
  const date = `${months[parseInt(month, 10) - 1]} ${parseInt(day, 10)}, ${year}`;
  return `Legally Subjective, In re ${d.subject.name}, Docket ${d.docket} (${d.standard}, filed ${date}).`;
}

/** Family name for case captions — suffixes stripped ("Samuel A. Alito, Jr." -> "Alito"). */
export function lastName(name: string): string {
  const stripped = name.replace(/,?\s*(Jr\.|Sr\.|II|III|IV)\s*$/i, "").trim();
  return stripped.split(/\s+/).slice(-1)[0];
}

/** BibTeX per LS-1.0 §7. */
export function bibtex(d: Docket): string {
  const key = `ls${d.docket.replace(/-/g, "")}`;
  const year = d.filed_at.slice(0, 4);
  return [
    `@misc{${key},`,
    `  title        = {Legally Subjective, In re ${d.subject.name}},`,
    `  howpublished = {Docket ${d.docket}, Standard ${d.standard}},`,
    `  year         = {${year}},`,
    `  note         = {Filed ${d.filed_at.slice(0, 10)}. SHA-256 chain: ${d.chain.sha256 ?? "see docket"}},`,
    `}`,
  ].join("\n");
}
