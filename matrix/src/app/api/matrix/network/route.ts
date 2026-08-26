import { NextResponse } from "next/server";
import { getNetwork } from "@/lib/matrix/queries";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const minWeight = Number(url.searchParams.get("minWeight") ?? "5") || 5;
    const data = await getNetwork(minWeight);
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      { empty: true, message: `Erreur d'accès à l'index réel : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
