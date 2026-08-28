/**
 * System state — REAL telemetry, read from the repository itself.
 * The interface derives its state from the frozen Corpus-Monde v1
 * (data/processed/stats_v1.json + the FILED dockets): the build is the
 * sha256 of the standard, the counts come from the corpus rule itself.
 * Nothing here can be invented — if the data is empty, the page says COLD.
 */
import { createHash } from "crypto";
import { readFile, readdir } from "fs/promises";
import path from "path";

export interface SystemState {
  /** First 8 hex of sha256(standards/LS-1.0.md) — the build IS the standard. */
  build: string;
  /** Full sha256 of the standard — printed on /standard. */
  standardHash: string;
  /** Number of FILED dockets = number of justices scored. */
  judgesScored: number;
  /** Cases in the frozen corpus (argued, OT2015–OT2023). */
  casesDecided: number;
  /** Corpus ladder — LS-AUDIT-001 inj. 4: counters reconciled from the record.
   *  Cases that entered the frozen corpus rule. */
  corpusArgued: number;
  /** Corpus cases joined to machine-readable SCDB votes. */
  joinedScdb: number;
  /** Corpus cases carrying a coded decision direction (SCDB 1/2). */
  withDirection: number;
  /** Labeled cases in the M2 training split (OT2015–OT2019). */
  trainSplit: number;
  /** Labeled cases in the M2 test split (OT2020–OT2023). */
  testSplit: number;
  /** Decisions decided 5–4 in the corpus. */
  fiveFour: number;
  /** Of those, the ones sealed for the final exam (never touched until M4). */
  sealed: number;
  /** Human window label, from the corpus rule (e.g. OCT 2015 — JUN 2024). */
  windowLabel: string;
  /** COLD: nothing filed. WARM: data exists. */
  state: "COLD" | "WARM";
}

async function listFiles(dir: string): Promise<string[]> {
  try {
    return await readdir(path.join(process.cwd(), dir));
  } catch {
    return [];
  }
}

function fmtMonth(iso: string): string {
  const [y, m] = iso.split("-");
  const months = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
  ];
  return `${months[Number(m) - 1] ?? ""} ${y}`;
}

export async function getSystemState(): Promise<SystemState> {
  let build = "NO-STANDARD";
  let standardHash = "";
  try {
    const std = await readFile(
      path.join(process.cwd(), "standards", "LS-1.0.md"),
      "utf8",
    );
    standardHash = createHash("sha256").update(std).digest("hex").toUpperCase();
    build = standardHash.slice(0, 8);
  } catch {
    /* The standard is missing — the interface says so. It invents nothing. */
  }

  /** FILED dockets only — the MANIFEST is not a docket. */
  const judgesScored = (await listFiles("data/dockets")).filter((f) =>
    f.startsWith("LS-J-") && f.endsWith(".json"),
  ).length;

  /** The frozen corpus — its own stats file is the ladder of record. */
  let corpusArgued = 0;
  let joinedScdb = 0;
  let withDirection = 0;
  let trainSplit = 0;
  let testSplit = 0;
  let fiveFour = 0;
  let sealed = 0;
  let windowStart = "";
  let windowEnd = "";
  try {
    const stats = JSON.parse(
      await readFile(
        path.join(process.cwd(), "data", "processed", "stats_v1.json"),
        "utf8",
      ),
    ) as {
      n_cases?: number;
      n_with_scdb?: number;
      n_five_four?: number;
      five_four_selection?: { n_selected?: number };
    };
    corpusArgued = stats.n_cases ?? 0;
    joinedScdb = stats.n_with_scdb ?? 0;
    fiveFour = stats.n_five_four ?? 0;
    sealed = stats.five_four_selection?.n_selected ?? 0;
  } catch {
    /* No corpus stats — zero. Honest. */
  }

  /** Direction labels and the M2 split, counted from the corpus itself. */
  try {
    const { createGunzip } = await import("zlib");
    const { createReadStream } = await import("fs");
    const rl = await import("readline");
    const gz = createReadStream(
      path.join(process.cwd(), "data", "processed", "corpus_cases_v1.jsonl.gz"),
    ).pipe(createGunzip());
    const lines = rl.createInterface({ input: gz });
    for await (const line of lines) {
      const c = JSON.parse(line) as {
        term?: string;
        scdb?: { decision_direction?: string | null };
      };
      const d = c.scdb?.decision_direction;
      if (d === "1" || d === "2") {
        withDirection += 1;
        const t = Number(c.term ?? 0);
        if (t >= 2015 && t <= 2019) trainSplit += 1;
        else if (t >= 2020 && t <= 2023) testSplit += 1;
      }
    }
  } catch {
    /* Corpus file absent — the ladder stays at zero. Honest. */
  }

  /** Window label from the research state (argued → last decision). */
  try {
    const rs = JSON.parse(
      await readFile(
        path.join(process.cwd(), "data", "productions", "research_state.json"),
        "utf8",
      ),
    ) as { corpus?: { window?: { start?: string; end?: string } } };
    const w = rs.corpus?.window;
    if (w?.start && w?.end) {
      windowStart = fmtMonth(w.start);
      windowEnd = fmtMonth(w.end);
    }
  } catch {
    /* No research state — no window. */
  }

  return {
    build,
    standardHash,
    judgesScored,
    casesDecided: corpusArgued,
    corpusArgued,
    joinedScdb,
    withDirection,
    trainSplit,
    testSplit,
    fiveFour,
    sealed,
    windowLabel: windowStart && windowEnd ? `${windowStart} — ${windowEnd}` : "",
    state: judgesScored > 0 ? "WARM" : "COLD",
  };
}
