import { NextResponse } from "next/server";
import { runSandboxSession } from "@/lib/matrix/agents";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

/**
 * Public sandbox — the ONLY interactive surface of the public interface.
 * Runs the real three-agent engine on a user-supplied sample. Ephemeral by
 * design: no DB write, no corpus mutation, no model change. Failures are
 * reported verbatim, never simulated.
 */
export async function POST(request: Request) {
  try {
    const body = (await request.json().catch(() => ({}))) as {
      title?: string;
      text?: string;
    };
    const result = await runSandboxSession({ title: body.title, text: body.text });
    const code = result.status === "ok" ? 200 : result.status === "refused" ? 400 : 502;
    return NextResponse.json(result, { status: code });
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
