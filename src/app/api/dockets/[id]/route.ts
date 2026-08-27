import { NextResponse } from "next/server";
import { bibtex, getDocket } from "@/lib/dockets";

/* THE INTERFACE — one docket, canonical JSON (or BibTeX).
   Serves the immutable artifact exactly as filed, seal included. */

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const d = await getDocket(id);
  if (!d || d.status !== "FILED") {
    return NextResponse.json(
      { error: "docket-not-found", docket: id },
      { status: 404 },
    );
  }

  const format = new URL(request.url).searchParams.get("format");
  if (format === "bibtex") {
    return new NextResponse(bibtex(d), {
      headers: {
        "Content-Type": "application/x-bibtex; charset=utf-8",
        "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
        "X-Docket": d.docket,
      },
    });
  }

  return NextResponse.json(d, {
    headers: {
      "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
      "X-Standard": d.standard,
      "X-Docket": d.docket,
      "X-Docket-SHA256": d.chain.sha256 ?? "",
    },
  });
}
