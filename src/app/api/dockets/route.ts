import { NextResponse } from "next/server";
import { listDockets } from "@/lib/dockets";

/* THE INTERFACE — canonical JSON for machines.
   The standard is only real if machines can consume it. */

export async function GET() {
  const dockets = await listDockets();
  return NextResponse.json(
    {
      standard: "LS-1.0",
      pipeline: "legally-subjective/1.0.0",
      count: dockets.length,
      dockets: dockets.map((d) => ({
        docket: d.docket,
        subject: d.subject.name,
        slug: d.subject.slug,
        role: d.subject.role,
        court: d.subject.court,
        bench: d.subject.bench,
        status: d.status,
        filed_at: d.filed_at,
        window: d.window,
        axes: Object.fromEntries(
          Object.entries(d.axes).map(([ax, a]) => [
            ax,
            {
              percentile: a.percentile,
              ci95: a.ci95,
              n: a.n,
              status: a.status,
            },
          ]),
        ),
        sha256: d.chain.sha256 ?? null,
        href: `/api/dockets/${d.docket}`,
      })),
    },
    {
      headers: {
        "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
        "X-Standard": "LS-1.0",
      },
    },
  );
}
