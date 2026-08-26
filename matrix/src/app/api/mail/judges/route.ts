import { NextResponse } from "next/server";
import { getJudgeDirectory } from "@/lib/matrix/mailbox";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const q = url.searchParams.get("q") ?? undefined;
    const judges = await getJudgeDirectory(q);
    return NextResponse.json({ empty: judges.length === 0, judges });
  } catch (e) {
    return NextResponse.json(
      { empty: true, message: `Erreur d'accès à l'annuaire réel : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
