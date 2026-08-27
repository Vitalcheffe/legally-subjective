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
  /** Engine cycles from scripts/engine_state.json. */
  engineCycles: number;
  /** Engine last cycle, HH:MM:SSZ. */
  engineLast: string;
  /** COLD: nothing ingested. WARM: data exists. */
  state: "COLD" | "WARM";
}

async function countJsonFiles(dir: string): Promise<number> {
  try {
    const entries = await readdir(path.join(process.cwd(), dir));
    return entries.filter((f) => f.endsWith(".json")).length;
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

  const judgesScored = await countJsonFiles("data/dockets");
  const docketsIngested = await countJsonFiles("data/sources");

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
    engineCycles,
    engineLast,
    state: judgesScored > 0 ? "WARM" : "COLD",
  };
}
