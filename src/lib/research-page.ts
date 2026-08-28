/**
 * Presentation helpers for the research pages (server-side).
 */
import { readFile } from "fs/promises";
import path from "path";

/** Surname display labels for the nine, read from the FILED dockets. */
export async function getBenchLabels(): Promise<Record<string, string>> {
  const labels: Record<string, string> = {
    roberts: "Roberts",
    thomas: "Thomas",
    alito: "Alito",
    sotomayor: "Sotomayor",
    kagan: "Kagan",
    gorsuch: "Gorsuch",
    kavanaugh: "Kavanaugh",
    barrett: "Barrett",
    jackson: "Jackson",
  };
  try {
    const dir = path.join(process.cwd(), "data", "dockets");
    const { readdir } = await import("fs/promises");
    const files = (await readdir(dir)).filter(
      (f) => f.startsWith("LS-J-") && f.endsWith(".json"),
    );
    for (const f of files) {
      const d = JSON.parse(await readFile(path.join(dir, f), "utf8"));
      if (d?.subject?.slug && d?.subject?.name) {
        const surname = d.subject.name
          .replace(/,?\s*(Jr\.|Sr\.|II|III|IV)\s*$/i, "")
          .trim()
          .split(/\s+/)
          .slice(-1)[0];
        labels[d.subject.slug] = surname;
      }
    }
  } catch {
    /* fallback labels stand */
  }
  return labels;
}

const CIRCUIT_ALIASES: Record<string, string> = {
  "1st": "first", "2nd": "second", "3rd": "third", "4th": "fourth",
  "5th": "fifth", "6th": "sixth", "7th": "seventh", "8th": "eighth",
  "9th": "ninth", "10th": "tenth", "11th": "eleventh",
  "d.c.": "dc district of columbia", "fed.": "federal",
};

/** Search haystack fragment for a circuit — "9th Cir." also matches "ninth". */
export function circuitWords(circuit: string): string {
  const key = circuit.replace(" Cir.", "").toLowerCase();
  return `${circuit} ${CIRCUIT_ALIASES[key] ?? ""} circuit court appeals`;
}

