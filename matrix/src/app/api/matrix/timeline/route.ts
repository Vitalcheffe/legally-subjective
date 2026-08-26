import { NextResponse } from "next/server";
import { getTimeline } from "@/lib/matrix/queries";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const data = await getTimeline();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      { empty: true, message: `Erreur d'accès à l'index réel : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
