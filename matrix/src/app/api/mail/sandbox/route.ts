import { NextResponse } from "next/server";
import { runSandboxSession } from "@/lib/matrix/agents";
import { clientKeyOf, rateLimit } from "@/lib/matrix/rate-limit";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

/**
 * Public sandbox — the ONLY interactive surface of the public interface.
 * Runs the real three-agent engine on a user-supplied sample. Ephemeral by
 * design: no DB write, no corpus mutation, no model change. Failures are
 * reported verbatim, never simulated.
 *
 * Phase 7 hardening — each session spends real LLM quota, so the endpoint
 * is rate-limited per client (sliding window, in-memory, per instance).
 * A blocked request receives an explicit 429 with the exact wait time;
 * nothing is queued silently and no analysis is ever substituted.
 */
const SANDBOX_RATE_LIMIT = { limit: 5, windowMs: 10 * 60 * 1000 }; // 5 sessions / 10 min / client

export async function POST(request: Request) {
  // ——— Rate limit first: a blocked caller spends no quota at all. ———
  const rl = rateLimit(`sandbox:${clientKeyOf(request)}`, SANDBOX_RATE_LIMIT);
  if (!rl.allowed) {
    return NextResponse.json(
      {
        status: "rate_limited",
        ephemeral: true,
        error: `Laboratoire saturé — limite de ${SANDBOX_RATE_LIMIT.limit} analyses par ${SANDBOX_RATE_LIMIT.windowMs / 60000} minutes par visiteur atteinte. Réessayez dans ${rl.retryAfterSeconds} secondes.`,
        notice:
          "Aucune analyse n'est mise en file ni simulée pendant l'attente — le quota protégé est celui de la science.",
        retryAfterSeconds: rl.retryAfterSeconds,
      },
      {
        status: 429,
        headers: { "Retry-After": String(rl.retryAfterSeconds) },
      },
    );
  }

  try {
    const body = (await request.json().catch(() => ({}))) as {
      title?: string;
      text?: string;
    };
    const result = await runSandboxSession({ title: body.title, text: body.text });
    const code = result.status === "ok" ? 200 : result.status === "refused" ? 400 : 502;
    return NextResponse.json(
      { ...result, remainingSessions: rl.remaining },
      { status: code },
    );
  } catch (e) {
    return NextResponse.json(
      {
        status: "error",
        ephemeral: true,
        error: `Échec du laboratoire public : ${(e as Error).message}`,
        notice: "Aucune analyse simulée n'est substituée à un échec.",
      },
      { status: 500 },
    );
  }
}
