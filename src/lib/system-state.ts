/**
 * System state — REAL telemetry, read from the repository itself.
 * The interface derives its state from the actual system: the build is
 * the sha256 of the standard, the counts are file counts, the engine
 * state is the engine's own persisted state. Nothing here can be
 * invented — if the data is empty, the page says COLD.
 */
import { createHash } from "crypto";
import { readFile, readdir } from "fs/promises";
import path from "path";

export interface SystemState {
  /** First 8 hex of sha256(standards/LS-1.0.md) — the build IS the standard. */
  build: string;
  /** Full sha256 of the standard — printed on /standard. */
  standardHash: string;
  /** Number of FILED dockets = number of judges scored. */
  judgesScored: number;
  /** Number of cached source sets = cases ingested. */
  docketsIngested: number;
  /** Decided cases actually read (Oyez files carrying a decision record). */
  casesDecided: number;
  /** LS-AUDIT-001 inj. 4 — the public counter reconciliation, from the record itself. */
  /** Total Oyez case files interrogated (valid responses + archived misses). */
  oyezInterrogated: number;
  /** Requests that failed and were archived as .miss.json — not hidden. */
  oyezMisses: number;
  /** Valid Oyez case responses. */
  oyezUsable: number;
  /** Cases that entered the research model (decision + exploitable votes), from model.json. */
  casesModeled: number;
  /** Human window label, from the agreement production (e.g. OCT 2020 — AUG 2026). */
  windowLabel: string;
  /** Engine cycles from scripts/engine_state.json. */
  engineCycles: number;
  /** Engine last cycle, HH:MM:SSZ. */
  engineLast: string;
  /** COLD: nothing ingested. WARM: data exists. */
  state: "COLD" | "WARM";
}

async function listFiles(dir: string): Promise<string[]> {
  try {
    return await readdir(path.join(process.cwd(), dir));
  } catch {
    return [];
  }
}

async function listJsonRecursive(dir: string): Promise<string[]> {
  const out: string[] = [];
  const walk = async (d: string) => {
    try {
      const entries = await readdir(d, { withFileTypes: true });
      for (const e of entries) {
        const p = path.join(d, e.name);
        if (e.isFile() && e.name.endsWith(".json")) out.push(p);
        else if (e.isDirectory()) await walk(p);
      }
    } catch {
      /* Not there. */
    }
  };
  await walk(path.join(process.cwd(), dir));
  return out;
}

async function countJsonFiles(dir: string, recursive = false): Promise<number> {
  try {
    const entries = await readdir(path.join(process.cwd(), dir), { withFileTypes: true });
    let count = 0;
    for (const e of entries) {
      if (e.isFile() && e.name.endsWith(".json")) count += 1;
      else if (recursive && e.isDirectory()) {
        count += await countJsonFiles(path.join(dir, e.name), true);
      }
    }
    return count;
  } catch {
    return 0;
  }
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
  const docketsIngested = await countJsonFiles("data/sources", true);

  /** Decided cases = Oyez files carrying a non-empty decision record. */
  let casesDecided = 0;
  let oyezMisses = 0;
  let oyezUsable = 0;
  try {
    const oyezFiles = await listJsonRecursive("data/sources/oyez");
    oyezMisses = oyezFiles.filter((f) => f.endsWith(".miss.json")).length;
    const results = await Promise.all(
      oyezFiles.map(async (f) => {
        if (f.endsWith(".miss.json")) return 0;
        try {
          const d = JSON.parse(await readFile(f, "utf8"));
          const decs = (d as { decisions?: unknown }).decisions;
          const usable = d && typeof d === "object" ? 1 : 0;
          return (Array.isArray(decs) && decs.length > 0 ? 10 : 0) + usable;
        } catch {
          return 0;
        }
      }),
    );
    for (const r of results) {
      if (r >= 10) casesDecided += 1;
      if (r >= 1) oyezUsable += 1;
    }
  } catch {
    /* No Oyez sources — zero decided cases. Honest. */
  }
  const oyezInterrogated = oyezUsable + oyezMisses;

  /** Cases that entered the research model — from the model's own artifact. */
  let casesModeled = 0;
  try {
    const model = JSON.parse(
      await readFile(
        path.join(process.cwd(), "data", "productions", "model.json"),
        "utf8",
      ),
    ) as { dataset?: { cases?: number } };
    casesModeled = model?.dataset?.cases ?? 0;
  } catch {
    /* No model artifact — nothing modeled yet. Honest. */
  }

  /** Human window label from the agreement production. */
  let windowLabel = "";
  try {
    const agr = JSON.parse(
      await readFile(
        path.join(process.cwd(), "data", "productions", "agreement.json"),
        "utf8",
      ),
    ) as { window?: { start?: string; end?: string } };
    const fmt = (iso?: string) => {
      if (!iso) return "";
      const [y, m] = iso.split("-");
      const months = [
        "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
        "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
      ];
      return `${months[Number(m) - 1] ?? ""} ${y}`;
    };
    if (agr.window?.start && agr.window?.end) {
      windowLabel = `${fmt(agr.window.start)} — ${fmt(agr.window.end)}`;
    }
  } catch {
    /* No agreement production yet — no window. */
  }

  let engineCycles = 0;
  let engineLast = "NEVER";
  try {
    const raw = JSON.parse(
      await readFile(
        path.join(process.cwd(), "scripts", "engine_state.json"),
        "utf8",
      ),
    );
    engineCycles = typeof raw.cycles === "number" ? raw.cycles : 0;
    if (typeof raw.last_cycle === "string" && raw.last_cycle.includes("T")) {
      engineLast = `${raw.last_cycle.split("T")[1]}`;
    }
  } catch {
    /* Engine has never run on this system. Honest. */
  }

  return {
    build,
    standardHash,
    judgesScored,
    docketsIngested,
    casesDecided,
    oyezInterrogated,
    oyezMisses,
    oyezUsable,
    casesModeled,
    windowLabel,
    engineCycles,
    engineLast,
    state: judgesScored > 0 ? "WARM" : "COLD",
  };
}
