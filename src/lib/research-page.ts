/**
 * Presentation helpers for the research pages (server-side).
 */
import { readFile } from "fs/promises";
import path from "path";

/** Surname display labels for the bench, read from the FILED dockets. */
export async function getBenchLabels(): Promise<Record<string, string>> {
  const labels: Record<string, string> = {};
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
    /* no dockets — no labels */
  }
  return labels;
}

