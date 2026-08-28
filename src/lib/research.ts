/**
 * Research access — the frozen Corpus-Monde v1 and the M2 baselines.
 * Server-side only. Everything typed here is produced by scripts/
 * transfuse_v2.py from data/processed/ (SCDB 2025_01 + CourtListener
 * fused corpus) — nothing is invented.
 */
import { readFile } from "fs/promises";
import path from "path";

export interface Baseline {
  id: string;
  name: string;
  accuracy: number;
  ic95: [number, number] | null;
  n: number | null;
  note?: string;
}

export interface ResearchStateFile {
  state_id: string;
  filed_at: string;
  corpus: {
    name: string;
    n_cases: number;
    n_opinions: number;
    n_with_scdb: number;
    n_with_direction: number;
    n_votes: number;
    n_justices: number;
    terms: string;
    window: { start: string; end: string };
    n_five_four: number;
    n_sealed: number;
    sealed_sha256: string;
    audio_coverage: number;
    transcript_coverage: number;
    one_vote_margin_cases: number;
  };
  split: { train: string; test: string };
  baselines: Baseline[];
  agreement: {
    n_pairs: number;
    min: number;
    min_pair: string;
    min_n: number;
    min_ic95: [number, number];
    max: number;
    max_pair: string;
    max_n: number;
    max_ic95: [number, number];
  };
  /** Per-justice ideological lean measured on the training split (B4 basis). */
  justice_lean: Record<
    string,
    {
      modal: "conservative" | "liberal";
      conservative_share: number;
      n_train: number;
    }
  >;
  protocol: {
    conditions: Array<{ id: string; name: string; spec: string }>;
    decisive_test: string;
    final_exam: string;
  };
  status: Record<string, string>;
  figures: string[];
}

export interface CaseVoteModel {
  p_dissent: number | null;
  p_direction: number | null;
  actual_direction: number | null;
}

export interface CaseRecord {
  docket: string;
  name: string;
  term: string;
  decided: number | null;
  /** SCDB issue area of the case ("Criminal Procedure", …). */
  issue_area: string;
  /** "conservative" | "liberal" | null — SCDB decisionDirection. */
  direction: string | null;
  /** SCDB caseDisposition, human label where clean ("affirmed"/"reversed"). */
  disposition: string | null;
  question: string | null;
  winning_party: string | null;
  petitioner_won: boolean | null;
  split: string;
  n_maj: number | null;
  n_min: number | null;
  /** Justices whose switch flips the winner; null = irregular recorded split. */
  flip_margin: number | null;
  unanimous: boolean;
  votes: Record<string, "majority" | "minority">;
  /** Recorded vote direction per justice (SCDB direction 1/2), where coded. */
  vote_dirs: Record<string, "conservative" | "liberal">;
  /** The B4 baseline's call on this case (majority of train-modal votes). */
  baseline_call: "conservative" | "liberal" | null;
  /** Whether that call matched the recorded direction; null = uncoded. */
  baseline_correct: boolean | null;
  /** Per-vote model predictions — empty until M3 is trained. */
  model: Record<string, CaseVoteModel>;
}

export interface CasesFile {
  n_cases: number;
  record_id: string;
  cases: CaseRecord[];
}

export async function getResearchState(): Promise<ResearchStateFile | null> {
  try {
    return JSON.parse(
      await readFile(
        path.join(process.cwd(), "data", "productions", "research_state.json"),
        "utf8",
      ),
    ) as ResearchStateFile;
  } catch {
    return null;
  }
}

export async function getCases(): Promise<CasesFile | null> {
  try {
    return JSON.parse(
      await readFile(
        path.join(process.cwd(), "data", "productions", "cases.json"),
        "utf8",
      ),
    ) as CasesFile;
  } catch {
    return null;
  }
}

export async function getCase(docket: string): Promise<CaseRecord | null> {
  const all = await getCases();
  return all?.cases.find((c) => c.docket === docket) ?? null;
}

/** The bench in protocol order — the Chief, then seniority at seating. */
export const BENCH_ORDER = [
  "roberts",
  "scalia",
  "kennedy",
  "thomas",
  "ginsburg",
  "breyer",
  "alito",
  "sotomayor",
  "kagan",
  "gorsuch",
  "kavanaugh",
  "barrett",
  "jackson",
] as const;

/** SCDB justice keys, for reading the corpus directly. */
export const SCDB_KEYS: Record<string, string> = {
  roberts: "JGRoberts",
  scalia: "AScalia",
  kennedy: "AMKennedy",
  thomas: "CThomas",
  ginsburg: "RBGinsburg",
  breyer: "SGBreyer",
  alito: "SAAlito",
  sotomayor: "SSotomayor",
  kagan: "EKagan",
  gorsuch: "NMGorsuch",
  kavanaugh: "BMKavanaugh",
  barrett: "ACBarrett",
  jackson: "KBJackson",
};

/** Compact formatted p-value for academic tables. */
export function fmtP(p: number): string {
  if (p < 0.001) return "p < 0.001";
  return `p = ${p.toFixed(3)}`;
}

/** ISO epoch seconds -> "Mar. 24, 2021". */
export function fmtDate(epoch: number | null): string {
  if (!epoch) return "—";
  const months = [
    "Jan.", "Feb.", "Mar.", "Apr.", "May", "June",
    "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.",
  ];
  const d = new Date(epoch * 1000);
  return `${months[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
}
