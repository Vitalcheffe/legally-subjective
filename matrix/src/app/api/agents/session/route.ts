import { NextResponse } from "next/server";
import { runAgentSession } from "@/lib/matrix/agents";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

export async function POST(request: Request) {
  try {
    const body = (await request.json().catch(() => ({}))) as { caseId?: string };
    if (!body.caseId) {
      return NextResponse.json(
        { status: "error", error: "caseId requis — aucune session ne peut démarrer sans affaire réelle." },
        { status: 400 },
      );
    }
    const result = await runAgentSession(body.caseId);
    return NextResponse.json(result, { status: result.status === "error" ? 502 : 200 });
  } catch (e) {
    return NextResponse.json(
      { status: "error", error: `Échec de session multi-agents : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
