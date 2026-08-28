"use client";

/**
 * THE RECORD — searchable index of every decided case.
 * Client-side filtering over the slim index passed from the
 * server (static, SSG). Nothing to invent: each row is a
 * filed public case with its recorded votes.
 */
import { useMemo, useState } from "react";
import Link from "next/link";

export interface SlimCase {
  docket: string;
  name: string;
  term: string;
  issueArea: string;
  split: string;
  flip: number | null;
  unanimous: boolean;
  winner: string | null;
  petitionerWon: boolean | null;
  /** Precomputed lowercase haystack incl. the issue area and term. */
  hay: string;
}

export function CaseSearch({ cases }: { cases: SlimCase[] }) {
  const [q, setQ] = useState("");
  const [term, setTerm] = useState("ALL");
  const [closeOnly, setCloseOnly] = useState(false);

  const terms = useMemo(
    () => ["ALL", ...Array.from(new Set(cases.map((c) => c.term))).sort().reverse()],
    [cases],
  );

  const results = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return cases.filter((c) => {
      if (term !== "ALL" && c.term !== term) return false;
      if (closeOnly && c.flip !== 1) return false;
      if (!needle) return true;
      return c.hay.includes(needle);
    });
  }, [cases, q, term, closeOnly]);

  return (
    <div>
      {/* ——— Controls ——— */}
      <div className="grid grid-cols-1 gap-4 border-y border-rule py-5 lg:grid-cols-[1fr_420px]">
        <div>
          <label
            htmlFor="case-q"
            className="micro mb-2 block"
          >
            Search the record — name, docket, issue area
          </label>
          <input
            id="case-q"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="e.g. Trump, 23-726, Criminal Procedure…"
            className="w-full border border-ink bg-paper px-4 py-3 font-data text-[14px] tracking-[0.01em] text-ink placeholder:text-ink-3 focus:outline-none focus-visible:outline-2 focus-visible:outline-signal"
          />
        </div>
        <div className="flex flex-wrap items-end gap-x-4 gap-y-3">
          <div>
            <p className="micro mb-2">Term</p>
            <div className="flex flex-wrap gap-1">
              {terms.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTerm(t)}
                  className={`border px-3 py-1.5 font-data text-[11px] font-semibold tracking-[0.04em] transition-colors ${
                    term === t
                      ? "border-ink bg-ink text-white"
                      : "border-rule bg-paper text-ink-2 hover:border-ink hover:text-ink"
                  }`}
                >
                  {t === "ALL" ? "ALL" : `OT${t.slice(2)}`}
                </button>
              ))}
            </div>
          </div>
          <button
            type="button"
            onClick={() => setCloseOnly((v) => !v)}
            aria-pressed={closeOnly}
            className={`border px-3 py-1.5 font-data text-[11px] font-semibold tracking-[0.04em] uppercase transition-colors ${
              closeOnly
                ? "border-signal bg-signal text-white"
                : "border-rule bg-paper text-ink-2 hover:border-signal hover:text-signal-deep"
            }`}
          >
            One vote from flipping
          </button>
        </div>
      </div>

      {/* ——— Counter ——— */}
      <p className="micro mt-4 tabular">
        {results.length.toLocaleString("en-US")} OF{" "}
        {cases.length.toLocaleString("en-US")} CASES
        {q || term !== "ALL" || closeOnly ? " — FILTERED" : " — THE FULL RECORD"}
      </p>

      {/* ——— Results ——— */}
      <div className="mt-3 border-t border-rule">
        {results.slice(0, 300).map((c) => (
          <Link
            key={c.docket}
            href={`/case/${c.docket}`}
            className="grid grid-cols-1 gap-x-6 gap-y-1.5 border-b border-hairline py-4 hover:bg-row-hover sm:grid-cols-[110px_1fr_120px_90px_150px] sm:items-baseline"
          >
            <span className="font-data text-[12px] font-semibold tracking-[0.02em] text-ink-3 tabular">
              {c.docket}
            </span>
            <span className="text-[14.5px] font-semibold leading-snug">
              {c.name}
            </span>
            <span className="font-data text-[11px] tracking-[0.03em] text-ink-2 uppercase">
              {c.issueArea}
            </span>
            <span className="font-data text-[13px] font-semibold tabular">
              {c.split}
            </span>
            <span
              className={`font-data text-[10.5px] font-semibold tracking-[0.05em] uppercase sm:justify-self-end ${
                c.flip === 1
                  ? "text-signal-deep"
                  : c.flip == null
                    ? "text-ink-3"
                    : "text-ink-3"
              }`}
            >
              {c.flip === 1
                ? "■ ONE DOOR"
                : c.flip == null
                  ? "IRREGULAR"
                  : c.unanimous
                    ? "9–0"
                    : `FLIP×${c.flip}`}
            </span>
          </Link>
        ))}
        {results.length > 300 && (
          <p className="micro py-4 normal-case">
            Showing the first 300 matches — refine the search to narrow further.
          </p>
        )}
        {results.length === 0 && (
          <p className="py-10 text-center font-data text-[13px] text-ink-3">
            NO CASE MATCHES — THE RECORD DOES NOT EXTEND BEYOND WHAT WAS FILED.
          </p>
        )}
      </div>
    </div>
  );
}
