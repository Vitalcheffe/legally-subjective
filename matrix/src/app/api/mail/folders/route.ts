import { NextResponse } from "next/server";
import { getFolders } from "@/lib/matrix/mailbox";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const data = await getFolders();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      { empty: true, message: `Erreur d'accès à la boîte réelle : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
