/**
 * The bench, loaded from the FILED dockets — server-side.
 * The draw experience consumes exactly what the record contains:
 * the disposition rate (how often this justice's vote favored the
 * person asking the court for relief), its vote count, and the
 * docket id where the receipt lives. Nothing else, nothing invented.
 */
import { readFile } from "fs/promises";
import path from "path";

export interface JusticeDraw {
  /** Docket id, e.g. LS-J-007 — the receipt address. */
  docket: string;
  /** Full display name, e.g. "Brett M. Kavanaugh". */
  name: string;
  /** Short name for the stamp, e.g. "KAVANAUGH". */
  stamp: string;
  /** URL slug, e.g. "kavanaugh". */
  slug: string;
  /** Disposition: share of recorded votes that favored the petitioner. 0–1. */
  forTheAsking: number;
  /** Recorded votes the rate was measured on. */
  votes: number;
  /** Wilson 95% half-width of forTheAsking, in percentage points (LS-AUDIT-001 inj. 1 & 12). */
  pm: number;
  /** Wilson 95% lower bound, 0–1. */
  ciLo: number;
  /** Wilson 95% upper bound, 0–1. */
  ciHi: number;
  /** True when the justice served fewer in-window terms than the bench max — a mid-window arrival whose record is shorter and less stabilized (LS-AUDIT-001 inj. 5). */
  shortMandate: boolean;
  /** Terms of service inside the declared window. */
  serviceYears: number;
  /** Bench-maximum terms inside the window — the comparison basis for shortMandate. */
  benchMaxYears: number;
}

interface DocketFile {
  docket: string;
  subject: { name: string; slug: string };
  raw?: { service_years_window?: number };
  axes: {
    disposition?: { value?: number; n?: number };
  };
}

/** Wilson score interval (95%) for a binomial share — the same arithmetic
 *  as the kernel's wilson_ci (core/src/legally_subjective/axes/v1.py).
 *  Mirrored client-side so the number and its interval can never disagree. */
function wilson(p: number, n: number): [number, number] {
  const z = 1.959964;
  const denom = 1 + (z * z) / n;
  const center = (p + (z * z) / (2 * n)) / denom;
  const half = (z / denom) * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n));
  return [Math.max(0, center - half), Math.min(1, center + half)];
}

function stampOf(name: string): string {
  const surname = name.split(",")[0].trim().split(" ").pop() ?? name;
  return surname.toUpperCase();
}

export async function getBench(): Promise<JusticeDraw[]> {
  const dir = path.join(process.cwd(), "data", "dockets");
  const { readdir } = await import("fs/promises");
  let files: string[] = [];
  try {
    files = (await readdir(dir)).filter(
      (f) => f.startsWith("LS-J-") && f.endsWith(".json"),
    );
  } catch {
    return [];
  }

  const parsed: DocketFile[] = [];
  for (const f of files.sort()) {
    try {
      const d = JSON.parse(
        await readFile(path.join(dir, f), "utf8"),
      ) as DocketFile;
      const disp = d.axes?.disposition;
      if (
        !d.subject?.name ||
        !d.subject?.slug ||
        typeof disp?.value !== "number" ||
        typeof disp?.n !== "number"
      ) {
        continue;
      }
      parsed.push(d);
    } catch {
      /* A docket that can't be read doesn't exist for the draw. */
    }
  }

  /** The bench maximum of in-window service years — mid-window arrivals are
   *  flagged against it (LS-AUDIT-001 inj. 5), never by hard-coded name. */
  const benchMaxYears = Math.max(
    ...parsed.map((d) => d.raw?.service_years_window ?? 0),
  );

  return parsed.map((d) => {
    const value = d.axes.disposition.value as number;
    const votes = d.axes.disposition.n as number;
    const [lo, hi] = wilson(value, votes);
    const serviceYears = d.raw?.service_years_window ?? 0;
    return {
      docket: d.docket,
      name: d.subject.name,
      stamp: stampOf(d.subject.name),
      slug: d.subject.slug,
      forTheAsking: value,
      votes,
      pm: Math.round((hi - lo) * 50),
      ciLo: lo,
      ciHi: hi,
      shortMandate: serviceYears < benchMaxYears,
      serviceYears,
      benchMaxYears,
    };
  });
}
