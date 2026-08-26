import { NextResponse } from "next/server";
import { getPrecedents } from "@/lib/matrix/queries";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const topN = Math.min(Number(url.searchParams.get("topN") ?? "40") || 40, 80);
    const data = await getPrecedents(topN);
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      { empty: true, message: `Erreur d'accès à l'index réel : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
