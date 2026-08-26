/**
 * Behavioral Matrix — multi-agent engine (REAL LLM binding).
 *
 * Every agent call goes through z-ai-web-dev-sdk (backend only). There are
 * NO pre-written responses and NO simulated loops: if the model endpoint is
 * unavailable the session is recorded as `error` with the verbatim failure,
 * and the UI must surface that state. Responses are stored verbatim so the
 * reasoning of each agent can be audited (chain-of-thought logs).
 */
import { db } from "@/lib/db";

export interface AgentVerdict {
  role: string;
  key_arguments: string[];
  verdict: "affirmed" | "reversed";
  confidence: number;
  summary: string;
}

export interface AgentSessionResult {
  runId: number;
  status: "ok" | "error";
  error?: string;
  case: {
    caseId: string;
    caseName: string;
    charge: string | null;
    department: string;
    dateFiled: string;
    factsExcerpt: string | null;
    humanDisposition: string | null;
    humanBinary: string | null;
    binaryEligible: boolean;
  };
  prosecutor?: AgentVerdict;
  defender?: AgentVerdict;
  judge?: AgentVerdict;
  agreement?: boolean | null;
  delta?: number | null;
  model?: string;
}

const JSON_INSTRUCTION = `Réponds STRICTEMENT en JSON valide, sans texte hors JSON, au format:
{
  "role": "<ton rôle>",
  "key_arguments": ["argument 1", "argument 2", "argument 3"],
  "verdict": "affirmed" | "reversed",
  "confidence": <nombre entre 0 et 1>,
  "summary": "<synthèse en 2 phrases>"
}
Le champ verdict : "affirmed" = la condamnation doit être confirmée ; "reversed" = elle doit être annulée/infirmée.`;

function buildCaseBrief(c: {
  caseName: string;
  charge: string | null;
  department: string;
  dateFiled: string;
  factsExcerpt: string | null;
}): string {
  return `DOSSIER RÉEL — Appellate Division, New York (département ${c.department}), décision du ${c.dateFiled}.
Affaire : ${c.caseName}
Chef d'accusation (extrait du recital officiel) : ${c.charge ?? "non extrait"}
Recital officiel des faits (verbatim) :
"""
${c.factsExcerpt ?? "(aucun recital extrait — refuse de conclure si insuffisant)"}
"""`;
}

/** Robust JSON extraction from a model response (handles ```json fences). */
function parseAgentJson(raw: string): { ok: true; value: AgentVerdict } | { ok: false; error: string } {
  let text = raw.trim();
  const fence = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fence) text = fence[1].trim();
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start === -1 || end === -1 || end <= start) {
    return { ok: false, error: "Réponse sans objet JSON" };
  }
  try {
    const parsed = JSON.parse(text.slice(start, end + 1)) as Partial<AgentVerdict>;
    if (!parsed.verdict || (parsed.verdict !== "affirmed" && parsed.verdict !== "reversed")) {
      return { ok: false, error: "Verdict manquant ou invalide" };
    }
    return {
      ok: true,
      value: {
        role: parsed.role ?? "agent",
        key_arguments: Array.isArray(parsed.key_arguments) ? parsed.key_arguments.map(String) : [],
        verdict: parsed.verdict,
        confidence: typeof parsed.confidence === "number" ? parsed.confidence : 0.5,
        summary: typeof parsed.summary === "string" ? parsed.summary : "",
      },
    };
  } catch (e) {
    return { ok: false, error: `JSON invalide: ${(e as Error).message}` };
  }
}

async function callAgent(
  zai: Awaited<ReturnType<typeof import("z-ai-web-dev-sdk").default.create>>,
  system: string,
  user: string,
): Promise<{ raw: string; parsed: ReturnType<typeof parseAgentJson> }> {
  const completion = await zai.chat.completions.create({
    messages: [
      { role: "assistant", content: system },
      { role: "user", content: user },
    ],
    thinking: { type: "disabled" },
  });
  const raw = completion.choices[0]?.message?.content ?? "";
  return { raw, parsed: parseAgentJson(raw) };
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Rate-limit resilient call: on a 429 (engine quota) the call is retried with
 * exponential backoff (3 attempts: ~20s, ~45s). The verbatim 429 is archived
 * only when every retry is exhausted — the session is then recorded as an
 * error, never simulated.
 */
async function callAgentResilient(
  zai: Awaited<ReturnType<typeof import("z-ai-web-dev-sdk").default.create>>,
  system: string,
  user: string,
): Promise<{ raw: string; parsed: ReturnType<typeof parseAgentJson> }> {
  const waits = [20000, 45000];
  let lastError: Error | null = null;
  for (let attempt = 0; attempt <= waits.length; attempt++) {
    if (attempt > 0) await sleep(waits[attempt - 1]);
    try {
      return await callAgent(zai, system, user);
    } catch (e) {
      lastError = e as Error;
      const msg = (e as Error).message ?? "";
      if (!msg.includes("429")) throw e; // only rate limits are retried
    }
  }
  throw lastError ?? new Error("appel moteur échoué");
}

export async function runAgentSession(
  caseId: string,
  experimentId?: number,
): Promise<AgentSessionResult> {
  const opinion = await db.opinion.findUnique({ where: { caseId } });
  if (!opinion) {
    throw new Error(`Affaire inconnue dans l'index réel : ${caseId}`);
  }

  const caseInfo = {
    caseId: opinion.caseId,
    caseName: opinion.caseName,
    charge: opinion.charge,
    department: opinion.department,
    dateFiled: opinion.dateFiled.toISOString().slice(0, 10),
    factsExcerpt: opinion.factsExcerpt,
    humanDisposition: opinion.dispositionPrimary,
    humanBinary: opinion.dispositionBinary,
    binaryEligible: opinion.binaryEligible,
  };

  const baseResult: AgentSessionResult = { runId: 0, status: "error", case: caseInfo };

  if (!opinion.factsExcerpt || opinion.factsExcerpt.length < 120) {
    const run = await db.agentRun.create({
      data: {
        caseId,
        experimentId: experimentId ?? null,
        humanDisposition: opinion.dispositionPrimary,
        status: "error",
        error: "Recital des faits insuffisant dans la source officielle — session refusée (aucune donnée inventée).",
      },
    });
    return {
      ...baseResult,
      runId: run.id,
      error: "Recital des faits insuffisant dans la source officielle — session refusée (aucune donnée inventée).",
    };
  }

  try {
    const ZAI = (await import("z-ai-web-dev-sdk")).default;
    const zai = await ZAI.create();

    const brief = buildCaseBrief(caseInfo);

    // 1 — PROCUREUR : argues the conviction must stand
    const prosecutor = await callAgentResilient(
      zai,
      `Tu es le PROCUREUR (agent d'accusation) dans une cour d'appel criminelle américaine. Ton analyse est froide, procédurale, fondée uniquement sur le dossier. Tu pléides pour la confirmation de la condamnation en identifiant les points procéduraux et factuels solides. ${JSON_INSTRUCTION}`,
      brief,
    );

    // 2 — DÉFENSE : argues the conviction must fall
    const defender = await callAgentResilient(
      zai,
      `Tu es l'AVOCAT DE LA DÉFENSE (agent de défense) dans une cour d'appel criminelle américaine. Ton analyse est froide, procédurale, fondée uniquement sur le dossier. Tu pléides pour l'annulation/infirmation en identifiant vices de procédure, erreurs de droit et failles factuelles. ${JSON_INSTRUCTION}`,
      brief,
    );

    // 3 — JUGE-IA : neutral arbiter, sees both sides' key arguments
    const duel =
      prosecutor.parsed.ok && defender.parsed.ok
        ? `\n\nARGUMENTS DU PROCUREUR :\n${prosecutor.parsed.value.key_arguments.map((a, i) => `${i + 1}. ${a}`).join("\n")}` +
          `\n\nARGUMENTS DE LA DÉFENSE :\n${defender.parsed.value.key_arguments.map((a, i) => `${i + 1}. ${a}`).join("\n")}`
        : "";
    const judge = await callAgentResilient(
      zai,
      `Tu es le JUGE-IA : arbitre neutre et déterministe d'une cour d'appel criminelle. Tu rends un verdict purement juridique, sans considération émotionnelle, en pesant les arguments des deux parties sur le dossier. ${JSON_INSTRUCTION}`,
      brief + duel,
    );

    const parsedPros = prosecutor.parsed.ok ? prosecutor.parsed.value : undefined;
    const parsedDef = defender.parsed.ok ? defender.parsed.value : undefined;
    const parsedJudge = judge.parsed.ok ? judge.parsed.value : undefined;

    const humanBinary = opinion.dispositionBinary; // affirmed | reversed_vacated
    let agreement: boolean | null = null;
    let delta: number | null = null;
    if (parsedJudge && opinion.binaryEligible && humanBinary) {
      agreement = parsedJudge.verdict === (humanBinary === "affirmed" ? "affirmed" : "reversed");
      // Δ_human : signed divergence between the pure-AI verdict and the human one.
      delta = agreement ? parsedJudge.confidence : -parsedJudge.confidence;
    }

    const anyError = [prosecutor.parsed, defender.parsed, judge.parsed]
      .filter((p) => !p.ok)
      .map((p) => !p.ok ? p.error : "")
      .filter(Boolean)
      .join(" | ");

    const run = await db.agentRun.create({
      data: {
        caseId,
        experimentId: experimentId ?? null,
        prosecutorOutput: prosecutor.raw,
        defenderOutput: defender.raw,
        judgeOutput: judge.raw,
        humanDisposition: opinion.dispositionPrimary,
        aiVerdict: parsedJudge?.verdict ?? null,
        aiConfidence: parsedJudge?.confidence ?? null,
        agreement,
        status: anyError ? "error" : "ok",
        error: anyError || null,
        model: "z-ai-web-dev-sdk (GLM)",
      },
    });

    return {
      runId: run.id,
      status: anyError ? "error" : "ok",
      error: anyError || undefined,
      case: caseInfo,
      prosecutor: parsedPros,
      defender: parsedDef,
      judge: parsedJudge,
      agreement,
      delta,
      model: "z-ai-web-dev-sdk (GLM)",
    };
  } catch (e) {
    const message = `Moteur LLM indisponible : ${(e as Error).message}`;
    const run = await db.agentRun.create({
      data: {
        caseId,
        experimentId: experimentId ?? null,
        humanDisposition: opinion.dispositionPrimary,
        status: "error",
        error: message,
        model: "z-ai-web-dev-sdk (GLM)",
      },
    });
    return { ...baseResult, runId: run.id, error: message };
  }
}

export async function listRuns(limit = 20) {
  const runs = await db.agentRun.findMany({
    orderBy: { createdAt: "desc" },
    take: limit,
    include: { opinion: { select: { caseName: true, department: true, year: true } } },
  });
  return {
    empty: runs.length === 0,
    runs: runs.map((r) => ({
      id: r.id,
      createdAt: r.createdAt.toISOString(),
      caseId: r.caseId,
      caseName: r.opinion?.caseName ?? null,
      department: r.opinion?.department ?? null,
      year: r.opinion?.year ?? null,
      humanDisposition: r.humanDisposition,
      aiVerdict: r.aiVerdict,
      aiConfidence: r.aiConfidence,
      agreement: r.agreement,
      status: r.status,
      error: r.error,
    })),
  };
}

// ---------------------------------------------------------------------------
// Public sandbox — deliberation on a USER-SUPPLIED sample.
//
// Runs the same real three-agent engine (Procureur → Défense → Juge-IA) but
// on arbitrary text pasted by a visitor. Deliberately EPHEMERAL: nothing is
// written to the scientific archive, the corpus is never modified, and no
// model is touched. If the engine fails, the failure is reported verbatim —
// never simulated.
// ---------------------------------------------------------------------------

export interface SandboxResult {
  status: "ok" | "error" | "refused";
  ephemeral: true;
  title: string;
  prosecutor?: AgentVerdict;
  defender?: AgentVerdict;
  judge?: AgentVerdict;
  error?: string;
  notice: string;
}

const SANDBOX_MIN_CHARS = 120; // same scientific threshold as the corpus protocol
const SANDBOX_MAX_CHARS = 12000;

export async function runSandboxSession(input: {
  title?: string;
  text?: string;
}): Promise<SandboxResult> {
  const text = (input.text ?? "").trim();
  const title = (input.title ?? "").trim().slice(0, 120) || "Échantillon sans titre";
  const notice =
    "Analyse éphémère sur échantillon fourni par l'utilisateur : rien n'est archivé, le corpus scientifique et les modèles ne sont pas modifiés.";

  if (text.length < SANDBOX_MIN_CHARS) {
    return {
      status: "refused",
      ephemeral: true,
      title,
      error: `Texte insuffisant (${text.length} caractères) — le protocole exige au moins ${SANDBOX_MIN_CHARS} caractères de recital, comme pour les affaires du corpus. Aucune analyse n'est fabriquée sur un dossier vide.`,
      notice,
    };
  }
  if (text.length > SANDBOX_MAX_CHARS) {
    return {
      status: "refused",
      ephemeral: true,
      title,
      error: `Texte trop long (${text.length} caractères, maximum ${SANDBOX_MAX_CHARS}) — soumettez l'extrait décisif du recital.`,
      notice,
    };
  }

  const brief = `ÉCHANTILLON FOURNI PAR UN UTILISATEUR — hors corpus validé, non archivé.
Désignation : ${title}
Texte soumis (verbatim) :
"""
${text}
"""`;

  try {
    const ZAI = (await import("z-ai-web-dev-sdk")).default;
    const zai = await ZAI.create();

    const prosecutor = await callAgentResilient(
      zai,
      `Tu es le PROCUREUR (agent d'accusation) dans une cour d'appel criminelle. Ton analyse est froide, procédurale, fondée uniquement sur le dossier soumis. Tu plaides pour la confirmation de la condamnation en identifiant les points procéduraux et factuels solides. Si le texte soumis ne permet pas de conclure, dis-le explicitement dans ton résumé. ${JSON_INSTRUCTION}`,
      brief,
    );

    const defender = await callAgentResilient(
      zai,
      `Tu es l'AVOCAT DE LA DÉFENSE (agent de défense) dans une cour d'appel criminelle. Ton analyse est froide, procédurale, fondée uniquement sur le dossier soumis. Tu plaides pour l'annulation/infirmation en identifiant vices de procédure, erreurs de droit et failles factuelles. Si le texte soumis ne permet pas de conclure, dis-le explicitement dans ton résumé. ${JSON_INSTRUCTION}`,
      brief,
    );

    const duel =
      prosecutor.parsed.ok && defender.parsed.ok
        ? `\n\nARGUMENTS DU PROCUREUR :\n${prosecutor.parsed.value.key_arguments.map((a, i) => `${i + 1}. ${a}`).join("\n")}` +
            `\n\nARGUMENTS DE LA DÉFENSE :\n${defender.parsed.value.key_arguments.map((a, i) => `${i + 1}. ${a}`).join("\n")}`
        : "";
    const judge = await callAgentResilient(
      zai,
      `Tu es le JUGE-IA : arbitre neutre et déterministe d'une cour d'appel criminelle. Tu rends un verdict purement juridique, sans considération émotionnelle, en pesant les arguments des deux parties sur le dossier soumis. ${JSON_INSTRUCTION}`,
      brief + duel,
    );

    const anyError = [prosecutor.parsed, defender.parsed, judge.parsed]
      .filter((p) => !p.ok)
      .map((p) => (!p.ok ? p.error : ""))
      .filter(Boolean)
      .join(" | ");

    return {
      status: anyError ? "error" : "ok",
      ephemeral: true,
      title,
      prosecutor: prosecutor.parsed.ok ? prosecutor.parsed.value : undefined,
      defender: defender.parsed.ok ? defender.parsed.value : undefined,
      judge: judge.parsed.ok ? judge.parsed.value : undefined,
      error: anyError || undefined,
      notice,
    };
  } catch (e) {
    return {
      status: "error",
      ephemeral: true,
      title,
      error: `Moteur LLM indisponible : ${(e as Error).message}. L'échec est rapporté tel quel — aucune analyse simulée n'est substituée.`,
      notice,
    };
  }
}
