import { NextResponse } from "next/server";
import { stepExperiment, getExperimentState, retryFailedCases } from "@/lib/matrix/experiments";

export const dynamic = "force-dynamic";
// One step = one full Prosecutor → Defender → AI-Judge session (3 real LLM
// calls, retried with backoff on engine rate limits). Failures are archived
// verbatim, never simulated.
export const maxDuration = 300;

export async function POST(request: Request) {
  try {
    const body = (await request.json().catch(() => ({}))) as {
      id?: number;
      retryFailed?: boolean;
    };
    if (!body.id) {
      return NextResponse.json(
        { empty: true, message: "id du protocole requis." },
        { status: 400 },
      );
    }
    if (body.retryFailed) {
      await retryFailedCases(Number(body.id));
    }
    const state = await stepExperiment(Number(body.id));
    return NextResponse.json(state);
  } catch (e) {
    return NextResponse.json(
      { empty: true, message: `Étape de protocole échouée : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
