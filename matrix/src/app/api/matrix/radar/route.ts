import { NextResponse } from "next/server";
import { getRadar } from "@/lib/matrix/queries";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const judge = url.searchParams.get("judge") ?? undefined;
    const data = await getRadar(judge);
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      { empty: true, message: `Erreur d'accès à l'index réel : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
