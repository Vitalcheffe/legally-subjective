"use client";

/**
 * The Bench table — client-side ranking.
 * The page ships as pure static HTML; re-ranking the bench by axis is a
 * local computation over the filed numbers (no server round-trip, no
 * dynamic rendering). The order changes because the bench is not uniform.
 */
import { useState } from "react";
import Link from "next/link";
import { Glyph } from "@/components/ls/glyph";

const AXES = ["disposition", "temperament", "precedent", "exposure"] as const;
type SortKey = "docket" | (typeof AXES)[number];

export interface BenchRow {
  docket: string;
  name: string;
  /** percentiles for the glyph (all six axes, null = insufficient) */
  glyphAxes: Record<string, number | null>;
  /** percentile per sortable axis, null = insufficient */
  values: Partial<Record<SortKey, number | null>>;
  /** CI width per axis for the gray sub-label */
  ciWidths: Partial<Record<SortKey, number | null>>;
  n: number;
  votes: number;
}

export function BenchTable({ rows }: { rows: BenchRow[] }) {
  const [by, setBy] = useState<SortKey>("docket");

  const sorted = [...rows].sort((a, b) => {
    if (by === "docket") return a.docket.localeCompare(b.docket);
    const av = a.values[by] ?? -1;
    const bv = b.values[by] ?? -1;
    return bv - av || a.docket.localeCompare(b.docket);
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[860px] border-collapse">
        <thead>
          <tr className="border-b-2 border-ink">
            <th className="py-3 pr-4 text-left font-data text-[10px] font-semibold tracking-[0.08em] uppercase">
              <button
                type="button"
                onClick={() => setBy("docket")}
                className={by === "docket" ? "text-signal-deep" : "hover:text-signal-deep"}
              >
                Docket {by === "docket" ? "↓" : "↕"}
              </button>
            </th>
            <th className="py-3 pr-4 text-left font-data text-[10px] font-semibold tracking-[0.08em] uppercase">Justice</th>
            {AXES.map((ax) => (
              <th key={ax} className="py-3 pr-4 text-right font-data text-[10px] font-semibold tracking-[0.08em] uppercase">
                <button
                  type="button"
                  onClick={() => setBy(ax)}
                  className={by === ax ? "text-signal-deep" : "hover:text-signal-deep"}
                >
                  {ax} {by === ax ? "↓" : "↕"}
                </button>
              </th>
            ))}
            <th className="py-3 text-right font-data text-[10px] font-semibold tracking-[0.08em] uppercase">Votes</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((d) => (
            <tr key={d.docket} className="border-b border-hairline hover:bg-row-hover">
              <td className="py-3.5 pr-4 font-data text-[12px] font-semibold tabular">
                <Link href={`/judge/${d.docket}`} className="hover:text-signal-deep">
                  {d.docket}
                </Link>
              </td>
              <td className="py-3.5 pr-4">
                <Link href={`/judge/${d.docket}`} className="group flex items-center gap-3">
                  <Glyph
                    docketId={d.docket}
                    axes={d.glyphAxes}
                    n={d.n}
                    maxN={400}
                    strokeWidth={4}
                    className="h-[34px] w-[34px] shrink-0"
                  />
                  <span className="text-[14px] font-semibold group-hover:text-signal-deep">
                    {d.name}
                  </span>
                </Link>
              </td>
              {AXES.map((ax) => {
                const v = d.values[ax] ?? null;
                const ci = d.ciWidths[ax] ?? null;
                return (
                  <td key={ax} className="py-3.5 pr-4 text-right font-data text-[15px] font-semibold tabular">
                    {v == null ? <span className="text-ink-3">—</span> : v}
                    <span className="block text-[9.5px] font-normal text-ink-3">
                      {v == null ? "insufficient-data" : ci != null ? `±${ci} ci` : ""}
                    </span>
                  </td>
                );
              })}
              <td className="py-3.5 text-right font-data text-[12px] text-ink-2 tabular">
                {d.votes.toLocaleString("en-US")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
