import { NextResponse } from "next/server";
import { listRuns } from "@/lib/matrix/agents";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const limit = Math.min(Number(url.searchParams.get("limit") ?? "20") || 20, 100);
    const data = await listRuns(limit);
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      { empty: true, runs: [], message: `Erreur : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
