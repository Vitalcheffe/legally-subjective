import { NextResponse } from "next/server";
import { bibtex, getDocket, listDockets } from "@/lib/dockets";

/* THE INTERFACE — one docket, one BibTeX record (LS-1.0 §7).
   force-static: prerendered at build from the FILED record. */

export const dynamic = "force-static";

export async function generateStaticParams() {
  const dockets = await listDockets();
  return dockets.map((d) => ({ id: d.docket }));
}

export async function GET(
  _request: Request,
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

  return new NextResponse(bibtex(d), {
    headers: {
      "Content-Type": "application/x-bibtex; charset=utf-8",
      "X-Docket": d.docket,
    },
  });
}
