import { NextResponse } from "next/server";
import { listDockets } from "@/lib/dockets";

/* THE INTERFACE — canonical JSON for machines.
   The standard is only real if machines can consume it.
   force-static: computed once at build from the FILED record, then served
   immutably — a filed docket never changes, and neither does its JSON. */

export const dynamic = "force-static";

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
              rank_band: a.rank_band,
              value_ci95: a.value_ci95 ?? null,
              n: a.n,
              status: a.status,
            },
          ]),
        ),
        revision: d.revision,
        supersedes: d.supersedes ?? null,
        sha256: d.chain.sha256 ?? null,
        href: `/api/dockets/${d.docket}`,
      })),
    },
    {
      headers: {
        "X-Standard": "LS-1.0",
      },
    },
  );
}
