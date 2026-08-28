import { NextResponse } from "next/server";
import { getDocket } from "@/lib/dockets";

/* THE INTERFACE — one docket, canonical JSON.
   Serves the immutable artifact exactly as filed, seal included.
   force-static: prerendered at build from the FILED record. */

export const dynamic = "force-static";

export async function generateStaticParams() {
  const { listDockets } = await import("@/lib/dockets");
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

  return NextResponse.json(d, {
    headers: {
      "X-Standard": d.standard,
      "X-Docket": d.docket,
      "X-Docket-SHA256": d.chain.sha256 ?? "",
    },
  });
}
