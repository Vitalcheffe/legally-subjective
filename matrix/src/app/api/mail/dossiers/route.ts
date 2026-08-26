import { NextResponse } from "next/server";
import { getMailbox } from "@/lib/matrix/mailbox";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const box = url.searchParams.get("box") ?? "inbox";
    const q = url.searchParams.get("q") ?? undefined;
    const idsRaw = url.searchParams.get("ids") ?? "";
    const ids = idsRaw ? idsRaw.split(",").map((s) => s.trim()).filter(Boolean) : undefined;
    const page = Number(url.searchParams.get("page") ?? "1");
    const pageSize = Number(url.searchParams.get("pageSize") ?? "50");
    const data = await getMailbox({
      box,
      q,
      ids,
      page: Number.isFinite(page) ? page : 1,
      pageSize: Number.isFinite(pageSize) ? pageSize : 50,
    });
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      { empty: true, message: `Erreur d'accès à la boîte réelle : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
