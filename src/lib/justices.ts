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
}

interface DocketFile {
  docket: string;
  subject: { name: string; slug: string };
  axes: {
    disposition?: { value?: number; n?: number };
  };
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

  const bench: JusticeDraw[] = [];
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
      bench.push({
        docket: d.docket,
        name: d.subject.name,
        stamp: stampOf(d.subject.name),
        slug: d.subject.slug,
        forTheAsking: disp.value,
        votes: disp.n,
      });
    } catch {
      /* A docket that can't be read doesn't exist for the draw. */
    }
  }
  return bench;
}
