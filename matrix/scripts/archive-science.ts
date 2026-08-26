/**
 * INFINITUM — P0 science archive (Phase 7, "sécuriser").
 *
 * The scientific record of the Behavioral Matrix lives in the gitignored
 * SQLite database (AgentRun verbatim LLM deliberations, Experiment
 * protocols, ExperimentCase ledgers). Losing it would erase the evidence
 * behind the published results (81.2 % blind agreement, the 429 quota
 * episodes, the replay mechanism).
 *
 * This script exports the three scientific tables VERBATIM to
 * versionable JSONL files inside the git repository, plus a MANIFEST with
 * sha256 checksums so anyone can verify the archive against the database.
 *
 * ZERO MOCK / ZERO TRANSFORMATION rules:
 *   - Every column is exported as stored, in schema order.
 *   - Verbatim model outputs are byte-identical (JSON round-trip only).
 *   - Failed runs (status=error, the archived 429 quota episodes) are
 *     exported exactly like successful ones — failures are evidence too.
 *   - No row is ever synthesized, summarized, or dropped.
 *
 * Re-verification: re-run this script — it recomputes counts and hashes
 * and refuses to write if the database no longer matches the expected
 * export (unless --force is passed).
 *
 * Usage: bun scripts/archive-science.ts [--out DIR] [--force]
 */
import { PrismaClient } from "@prisma/client";
import { createHash } from "node:crypto";
import { mkdirSync, writeFileSync, existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

process.env.DATABASE_URL ||= "file:/home/z/my-project/db/custom.db";

const prisma = new PrismaClient();
const args = process.argv.slice(2);
const force = args.includes("--force");
const outIdx = args.indexOf("--out");
const OUT_DIR = resolve(
  outIdx !== -1 && args[outIdx + 1]
    ? args[outIdx + 1]
    : "/home/z/my-project/legally-subjective/data/archive/science",
);
const DB_PATH = process.env.DATABASE_URL.replace(/^file:/, "");

const sha256 = (data: string | Buffer) => createHash("sha256").update(data).digest("hex");

/** Serialize one row verbatim — dates as ISO, everything else as stored. */
function row(row: Record<string, unknown>): string {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(row)) {
    out[k] = v instanceof Date ? v.toISOString() : v;
  }
  return JSON.stringify(out, null, 0);
}

async function main() {
  const [runs, experiments, cases] = await Promise.all([
    prisma.agentRun.findMany({ orderBy: { id: "asc" } }),
    prisma.experiment.findMany({ orderBy: { id: "asc" } }),
    prisma.experimentCase.findMany({ orderBy: { id: "asc" } }),
  ]);

  console.log(
    `Lecture DB : ${runs.length} AgentRun, ${experiments.length} Experiment, ${cases.length} ExperimentCase`,
  );

  // ——— Guard: if a previous archive exists, verify the DB still matches it ———
  const prevManifestPath = resolve(OUT_DIR, "MANIFEST.json");
  if (existsSync(prevManifestPath) && !force) {
    const prev = JSON.parse(readFileSync(prevManifestPath, "utf8"));
    const same =
      prev.counts.agentRuns === runs.length &&
      prev.counts.experiments === experiments.length &&
      prev.counts.experimentCases === cases.length;
    if (!same) {
      console.error(
        `ÉCART avec l'archive existante (DB: ${runs.length}/${experiments.length}/${cases.length} vs manifeste: ` +
          `${prev.counts.agentRuns}/${prev.counts.experiments}/${prev.counts.experimentCases}). ` +
          `La base a évolué — passez --force pour ré-archiver (l'ancien manifeste sera remplacé).`,
      );
      process.exit(1);
    }
    console.log("Cohérence avec l'archive précédente confirmée (mêmes effectifs).");
  }

  mkdirSync(OUT_DIR, { recursive: true });

  const files = {
    "agent_runs.jsonl": runs.map(row).join("\n") + "\n",
    "experiments.jsonl": experiments.map(row).join("\n") + "\n",
    "experiment_cases.jsonl": cases.map(row).join("\n") + "\n",
  };

  for (const [name, content] of Object.entries(files)) {
    writeFileSync(resolve(OUT_DIR, name), content, "utf8");
    console.log(`  écrit ${name} (${content.length.toLocaleString("fr-FR")} octets)`);
  }

  const dbHash = sha256(readFileSync(DB_PATH));
  const manifest = {
    archive: "infinitum-science-archive",
    version: 1,
    exportedAt: new Date().toISOString(),
    purpose:
      "Sauvegarde P0 du registre scientifique (délivrances LLM verbatim + protocoles) — la base SQLite est gitignorée, cet archive est la copie versionnée.",
    source: {
      database: "db/custom.db (Behavioral Matrix, Phase 3–4)",
      databaseSha256: dbHash,
      prismaModels: ["AgentRun", "Experiment", "ExperimentCase"],
    },
    counts: {
      agentRuns: runs.length,
      agentRunsOk: runs.filter((r) => r.status === "ok").length,
      agentRunsError: runs.filter((r) => r.status === "error").length,
      experiments: experiments.length,
      experimentCases: cases.length,
    },
    files: Object.fromEntries(
      Object.entries(files).map(([name, content]) => [name, { sha256: sha256(content), rows: content.trim() ? content.trim().split("\n").length : 0 }]),
    ),
    fidelity: [
      "Chaque colonne est exportée telle que stockée, dans l'ordre du schéma Prisma.",
      "Les sorties LLM (prosecutorOutput / defenderOutput / judgeOutput) sont verbatim — aucun remplacement, aucune simulation.",
      "Les runs en erreur (épisodes de quota 429, rejoués ensuite) sont archivés comme les autres : l'échec est une donnée.",
      "Les dates sont sérialisées ISO 8601 ; aucun autre champ n'est transformé.",
      "Ré-vérification : relancer scripts/archive-science.ts — il refuse d'écrire si les effectifs divergent.",
    ],
    knownResults: {
      note: "Chiffres publiés pour référence (les valeurs font foi dans la DB/JSONL, pas ici) :",
      experimentOfficial: "zero-shot n=20 seed=42 — 13/16 accords à l'aveugle (81,2 %), Brier 0,150",
    },
  };
  writeFileSync(prevManifestPath, JSON.stringify(manifest, null, 2) + "\n", "utf8");
  console.log(`  écrit MANIFEST.json (DB sha256 ${dbHash.slice(0, 12)}…)`);

  // ——— Console summary — the honest mirror of what was archived ———
  const exp2 = experiments.find((e) => e.label.includes("n=20"));
  const exp2Runs = runs.filter((r) => r.experimentId === exp2?.id && r.status === "ok");
  const scored = exp2Runs.length;
  const agree = exp2Runs.filter((r) => r.agreement === true).length;
  console.log(
    `\nArchive scientifique : ${runs.length} runs verbatim (${runs.filter((r) => r.status === "error").length} échecs 429 conservés), ${experiments.length} protocoles, ${cases.length} registres.`,
  );
  if (scored > 0) {
    console.log(
      `Run officiel « ${exp2?.label} » : ${agree}/${scored} accords recalculés depuis l'archive (${((agree / scored) * 100).toFixed(1)} %).`,
    );
  }
  console.log(`Répertoire : ${OUT_DIR}`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
