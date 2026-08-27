/**
 * Research access — LS-M-001, the trained model and the case record.
 * Server-side only. Everything typed here is produced by scripts/train.py
 * from the cached public record (data/sources/) — nothing is invented.
 */
import { readFile } from "fs/promises";
import path from "path";

export interface TaskResult {
  auc: number;
  accuracy: number;
  brier: number;
  log_loss: number;
  n: number;
}

export interface PerJustice {
  name: string;
  n_votes: number;
  dissents: number;
  dissent_rate: number;
  dissent_ci: [number, number];
  direction_rate: number | null;
  auc_dissent: number;
  auc_direction: number;
}

export interface SpectrumPoint {
  logit: number;
  ci: [number, number];
}

export interface LearningPoint {
  n_train_cases: number;
  fraction: number;
  auc_mean: number;
  auc_std: number;
  reps: number;
}

export interface ModelFile {
  model_id: string;
  trained_at: string;
  seed: number;
  reproduce: string;
  environment: {
    python: string;
    scikit_learn: string;
    numpy: string;
    scipy: string;
    matplotlib: string;
  };
  dataset: {
    votes: number;
    cases: number;
    terms: string[];
    justices: number;
    dissent_votes: number;
    dissent_rate: number;
    direction_resolvable_votes: number;
    direction_rate: number;
    circuits: string[];
  };
  design: {
    cv: string;
    model: string;
    spec_A: string;
    spec_B: string;
    baselines: string;
    bootstrap: string;
  };
  results: {
    direction: { A: TaskResult; B: TaskResult; baseline: TaskResult };
    dissent: { A: TaskResult; B: TaskResult; baseline: TaskResult };
    learning_curve_direction: LearningPoint[];
    learning_curve_dissent: LearningPoint[];
    per_justice: Record<string, PerJustice>;
    spectrum: Record<string, SpectrumPoint>;
    tests: {
      chi2_dissent_x_justice: { chi2: number; p: number; dof: number; levels: number };
      chi2_dissent_x_term: { chi2: number; p: number; dof: number; levels: number };
      fleiss_kappa: {
        kappa: number;
        P_bar: number;
        P_e: number;
        items: number;
        raters: number;
      } | null;
    };
    agreement: {
      n_pairs: number;
      min: number;
      max: number;
      mean: number;
      min_pair: string;
      max_pair: string;
    };
  };
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
  circuit: string;
  question: string;
  first_party: string;
  second_party: string;
  winning_party: string | null;
  petitioner_won: boolean | null;
  split: string;
  n_maj: number;
  n_min: number;
  /** Justices whose switch flips the winner; null = irregular recorded split. */
  flip_margin: number | null;
  unanimous: boolean;
  votes: Record<string, "majority" | "minority">;
  model: Record<string, CaseVoteModel>;
}

export interface CasesFile {
  n_cases: number;
  model_id: string;
  cases: CaseRecord[];
}

export async function getModel(): Promise<ModelFile | null> {
  try {
    return JSON.parse(
      await readFile(
        path.join(process.cwd(), "data", "productions", "model.json"),
        "utf8",
      ),
    ) as ModelFile;
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

/** The Nine in protocol order (matches data/dockets). */
export const BENCH_ORDER = [
  "roberts",
  "thomas",
  "alito",
  "sotomayor",
  "kagan",
  "gorsuch",
  "kavanaugh",
  "barrett",
  "jackson",
] as const;

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
