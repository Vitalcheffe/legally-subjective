import Link from "next/link";
import { notFound } from "next/navigation";
import { Chrome } from "@/components/ls/chrome";
import { Glyph } from "@/components/ls/glyph";
import { getSystemState } from "@/lib/system-state";
import {
  agreementPair,
  getAgreement,
  listDockets,
  lastName,
  type Docket,
} from "@/lib/dockets";

/* ————————————————————————————————————————————————
   THE BENCH — one court, every judge, every axis.
   Function: rank the bench by any axis (server-side sort via ?by=),
   show the per-axis spread, and the agreement matrix computed from
   common merits votes.
   Result: the proof that the bench is not uniform — in numbers.
   ———————————————————————————————————————————————— */

const SORTABLE = ["docket", "disposition", "temperament", "precedent", "exposure"] as const;
type SortKey = (typeof SORTABLE)[number];

export async function generateStaticParams() {
  return [{ id: "scotus" }];
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (id !== "scotus") return { title: "Court not found — Legally Subjective" };
  return {
    title: "The Bench — Supreme Court of the United States · Legally Subjective",
    description:
      "The sitting Nine, ranked axis by axis by their filed Subjectivity Fingerprints. The spread per axis — and the agreement matrix over common merits votes. The bench is not uniform.",
  };
}

function grayFor(v: number | null): string {
  // agreement 0..1 -> grayscale ink density (0.06 .. 0.92)
  if (v == null) return "transparent";
  const a = 0.06 + v * 0.86;
  return `rgba(10,10,10,${a.toFixed(3)})`;
}

export default async function CourtPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ by?: string }>;
}) {
  const [{ id }, sp, sys] = await Promise.all([params, searchParams, getSystemState()]);
  if (id !== "scotus") notFound();

  const [dockets, agreement] = await Promise.all([listDockets(), getAgreement()]);
  if (dockets.length === 0) notFound();

  const by = (SORTABLE as readonly string[]).includes(sp.by ?? "") ? (sp.by as SortKey) : "docket";

  const sorted = [...dockets].sort((a, b) => {
    if (by === "docket") return a.docket.localeCompare(b.docket);
    const av = a.axes[by]?.percentile ?? -1;
    const bv = b.axes[by]?.percentile ?? -1;
    return bv - av || a.docket.localeCompare(b.docket);
  });

  const axes = ["disposition", "temperament", "precedent", "exposure"] as const;

  // per-axis spread: max − min percentile (nulls excluded)
  const spreads = Object.fromEntries(
    axes.map((ax) => {
      const vals = dockets
        .map((d) => d.axes[ax]?.percentile ?? null)
        .filter((v): v is number => v != null);
      return [ax, vals.length ? { min: Math.min(...vals), max: Math.max(...vals) } : null];
    }),
  );

  // agreement extremes
  let best: { a: string; b: string; n: number; agree: number } | null = null;
  let worst: { a: string; b: string; n: number; agree: number } | null = null;
  if (agreement) {
    for (const [key, v] of Object.entries(agreement.pairs)) {
      if (v.agree == null) continue;
      const [a, b] = key.split("|");
      if (!best || v.agree > best.agree) best = { a, b, n: v.n, agree: v.agree };
      if (!worst || v.agree < worst.agree) worst = { a, b, n: v.n, agree: v.agree };
    }
  }
  const nameOf = (slug: string) =>
    dockets.find((d) => d.subject.slug === slug)?.subject.name ?? slug;
  const docketOf = (slug: string) =>
    dockets.find((d) => d.subject.slug === slug)?.docket ?? slug;

  const totalVotes = Math.max(...dockets.map((d) => d.raw.merits_votes));

  return (
    <div className="flex min-h-screen flex-col bg-paper font-display text-ink">
      <Chrome
        build={sys.build}
        judgesScored={sys.judgesScored}
        docketsIngested={sys.docketsIngested}
        engineCycles={sys.engineCycles}
        engineLast={sys.engineLast}
        state={sys.state}
        route={`/court/${id}`}
      />

      <main className="flex-1">
        {/* ——— MASTHEAD ——— */}
        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14 lg:py-14">
            <p className="micro">[BENCH-{id.toUpperCase()}] · The bench</p>
            <h1 className="mt-5 font-display text-[clamp(2.2rem,4.6vw,3.8rem)] font-bold uppercase leading-[0.98] tracking-[-0.02em]">
              Supreme Court of the United States
            </h1>
            <p className="mt-4 max-w-3xl text-[14px] leading-relaxed text-ink-2">
              The sitting Nine, measured from filed records — {totalVotes.toLocaleString("en-US")} merits
              votes and {dockets.reduce((s, d) => s + d.raw.lead_opinions, 0).toLocaleString("en-US")} lead
              opinions, window {dockets[0].window.start.slice(0, 4)}–{dockets[0].window.end.slice(0, 10)}.
              Every number on this page traces to a public source. Sort by any axis — the
              order changes because the bench is not uniform.
            </p>
            <dl className="mt-7 grid max-w-3xl grid-cols-2 gap-x-8 gap-y-3 font-data text-[12px] sm:grid-cols-4">
              {[
                ["Justices filed", String(dockets.length)],
                ["Bench", `${dockets[0].subject.bench_n} · small-bench §3.5bis`],
                ["Axes computed", "4 of 6"],
                ["Null axes", "Reversal · Orality"],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt className="text-[10px] tracking-[0.08em] text-ink-3 uppercase">{k}</dt>
                  <dd className="mt-0.5 font-medium uppercase">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        {/* ——— THE TABLE — rank by axis ——— */}
        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <p className="micro">[001] The ranking — click a column to re-rank the bench</p>
            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[860px] border-collapse">
                <thead>
                  <tr className="border-b-2 border-ink">
                    <th className="py-3 pr-4 text-left font-data text-[10px] font-semibold tracking-[0.08em] uppercase">
                      <Link href={`/court/${id}?by=docket`} className={by === "docket" ? "text-signal-deep" : "hover:text-signal-deep"}>
                        Docket ↓
                      </Link>
                    </th>
                    <th className="py-3 pr-4 text-left font-data text-[10px] font-semibold tracking-[0.08em] uppercase">Justice</th>
                    {axes.map((ax) => (
                      <th key={ax} className="py-3 pr-4 text-right font-data text-[10px] font-semibold tracking-[0.08em] uppercase">
                        <Link href={`/court/${id}?by=${ax}`} className={by === ax ? "text-signal-deep" : "hover:text-signal-deep"}>
                          {ax} {by === ax ? "↓" : "↕"}
                        </Link>
                      </th>
                    ))}
                    <th className="py-3 text-right font-data text-[10px] font-semibold tracking-[0.08em] uppercase">Votes</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((d: Docket, i) => (
                    <tr key={d.docket} className="border-b border-hairline hover:bg-row-hover">
                      <td className="py-3.5 pr-4 font-data text-[12px] font-semibold tabular">
                        <Link href={`/judge/${d.docket}`} className="hover:text-signal-deep">
                          {d.docket}
                        </Link>
                      </td>
                      <td className="py-3.5 pr-4">
                        <Link href={`/judge/${d.docket}`} className="flex items-center gap-3 group">
                          <Glyph
                            docketId={d.docket}
                            axes={Object.fromEntries(
                              ["disposition", "temperament", "precedent", "reversal", "orality", "exposure"].map(
                                (ax) => [ax, d.axes[ax]?.percentile ?? null],
                              ),
                            )}
                            n={Math.max(d.raw.merits_votes, d.raw.lead_opinions)}
                            maxN={400}
                            strokeWidth={4}
                            className="h-[34px] w-[34px] shrink-0"
                          />
                          <span className="text-[14px] font-semibold group-hover:text-signal-deep">
                            {d.subject.name}
                          </span>
                        </Link>
                      </td>
                      {axes.map((ax) => {
                        const a = d.axes[ax];
                        const v = a?.percentile;
                        return (
                          <td key={ax} className="py-3.5 pr-4 text-right font-data text-[15px] font-semibold tabular">
                            {v == null ? <span className="text-ink-3">—</span> : v}
                            <span className="block text-[9.5px] font-normal text-ink-3">
                              {v == null ? a?.status : `±${Math.abs((a.ci95?.[1] ?? 0) - (a.ci95?.[0] ?? 0))} ci`}
                            </span>
                          </td>
                        );
                      })}
                      <td className="py-3.5 text-right font-data text-[12px] text-ink-2 tabular">
                        {d.raw.merits_votes.toLocaleString("en-US")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="micro mt-5 normal-case tracking-[0.02em] text-ink-3">
              Percentile against the bench of nine · CI width in gray under each value ·
              dashed glyph spokes = insufficient data (Reversal, Orality).
            </p>
          </div>
        </section>

        {/* ——— THE SPREAD — proof the bench is not uniform ——— */}
        <section className="border-b border-rule bg-paper-2">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <p className="micro">[002] The spread — same court, different judges</p>
            <div className="mt-6 grid grid-cols-1 gap-px border border-rule bg-rule sm:grid-cols-2 lg:grid-cols-4">
              {axes.map((ax) => {
                const s = spreads[ax];
                const minD = dockets.find((d) => d.axes[ax]?.percentile === s?.min);
                const maxD = dockets.find((d) => d.axes[ax]?.percentile === s?.max);
                return (
                  <div key={ax} className="bg-paper-2 px-5 py-6">
                    <p className="font-data text-[10px] tracking-[0.08em] text-ink-3 uppercase">{ax}</p>
                    <p className="mt-2 font-data text-[34px] leading-none font-semibold tabular">
                      {s ? s.max - s.min : "—"}
                      <span className="text-[13px] font-medium text-ink-3"> pts</span>
                    </p>
                    <p className="mt-3 text-[11.5px] leading-snug text-ink-2">
                      {s && minD && maxD ? (
                        <>
                          {lastName(maxD.subject.name)} at {s.max} ·{" "}
                          {lastName(minD.subject.name)} at {s.min}
                        </>
                      ) : (
                        "insufficient data"
                      )}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ——— THE AGREEMENT MATRIX — computed from common votes ——— */}
        {agreement && (
          <section className="border-b border-rule">
            <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
              <p className="micro">[003] The agreement matrix — click a cell to open the head-to-head</p>
              <h2 className="mt-4 font-display text-[clamp(1.7rem,3vw,2.5rem)] font-bold uppercase leading-[1.02] tracking-[-0.01em]">
                Over {agreement.pairs[Object.keys(agreement.pairs)[0]]?.n.toLocaleString("en-US") ?? "N"} shared
                cases, some pairs never split.
              </h2>
              <div className="mt-8 overflow-x-auto">
                <table className="w-full min-w-[760px] border-collapse">
                  <thead>
                    <tr>
                      <th className="w-[130px]" />
                      {dockets.map((d) => (
                        <th key={d.docket} className="px-1 py-2 font-data text-[10px] font-semibold tracking-[0.06em] text-ink-3 uppercase">
                          {lastName(d.subject.name)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {dockets.map((rd) => (
                      <tr key={rd.docket}>
                        <th className="py-1 pr-3 text-right font-data text-[10.5px] font-semibold tracking-[0.04em] text-ink-2 uppercase">
                          <Link href={`/judge/${rd.docket}`} className="hover:text-signal-deep">
                            {lastName(rd.subject.name)}
                          </Link>
                        </th>
                        {dockets.map((cd) => {
                          if (rd.docket === cd.docket) {
                            return (
                              <td key={cd.docket} className="border border-hairline bg-paper-2 p-0">
                                <div className="flex h-[38px] w-[68px] items-center justify-center font-data text-[10px] text-ink-3">
                                  —
                                </div>
                              </td>
                            );
                          }
                          const p = agreementPair(agreement, rd.subject.slug, cd.subject.slug);
                          const v = p?.agree ?? null;
                          const isExtreme =
                            (best && ((rd.subject.slug === best.a && cd.subject.slug === best.b) || (rd.subject.slug === best.b && cd.subject.slug === best.a))) ||
                            (worst && ((rd.subject.slug === worst.a && cd.subject.slug === worst.b) || (rd.subject.slug === worst.b && cd.subject.slug === worst.a)));
                          // density threshold: above 0.72 the fill is dark enough for white text
                          const dark = v != null && v >= 0.72;
                          return (
                            <td key={cd.docket} className="border border-hairline p-0">
                              <Link
                                href={`/compare/${rd.subject.slug}/${cd.subject.slug}`}
                                className={`group flex h-[38px] w-[68px] flex-col items-center justify-center font-data text-[11px] font-semibold tabular hover:outline hover:outline-2 hover:outline-signal ${dark ? "text-white" : "text-ink"}`}
                                style={v != null ? { backgroundColor: grayFor(v) } : undefined}
                                title={`${rd.subject.name} v. ${cd.subject.name} — ${v != null ? (v * 100).toFixed(1) : "?"}% agreement over ${p?.n ?? 0} common cases`}
                              >
                                <span>{v != null ? `${(v * 100).toFixed(0)}%` : "—"}</span>
                                <span className={`text-[8.5px] font-normal ${dark ? "text-white/75" : "text-ink-3"}`}>
                                  n={p?.n ?? 0}
                                </span>
                              </Link>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {best && worst && (
                <div className="mt-6 grid grid-cols-1 gap-8 lg:grid-cols-2">
                  <div className="border-l-2 border-signal pl-4">
                    <p className="font-data text-[10px] tracking-[0.08em] text-ink-3 uppercase">Most aligned pair</p>
                    <p className="mt-1 text-[14px] font-semibold">
                      {nameOf(best.a)} · {nameOf(best.b)} — {(best.agree * 100).toFixed(1)}% over n={best.n}
                    </p>
                    <Link href={`/compare/${best.a}/${best.b}`} className="mt-1 inline-block font-data text-[11px] text-signal-deep hover:underline">
                      open {docketOf(best.a)} v. {docketOf(best.b)} →
                    </Link>
                  </div>
                  <div className="border-l-2 border-ink pl-4">
                    <p className="font-data text-[10px] tracking-[0.08em] text-ink-3 uppercase">Most split pair</p>
                    <p className="mt-1 text-[14px] font-semibold">
                      {nameOf(worst.a)} · {nameOf(worst.b)} — {(worst.agree * 100).toFixed(1)}% over n={worst.n}
                    </p>
                    <Link href={`/compare/${worst.a}/${worst.b}`} className="mt-1 inline-block font-data text-[11px] text-signal-deep hover:underline">
                      open {docketOf(worst.a)} v. {docketOf(worst.b)} →
                    </Link>
                  </div>
                </div>
              )}
              <p className="micro mt-6 normal-case tracking-[0.02em] text-ink-3">
                Basis: {agreement.basis}. Cell shading scales with agreement density. This
                matrix is navigation, not decoration — every cell opens the head-to-head.
              </p>
            </div>
          </section>
        )}
      </main>

      <footer className="bg-ink text-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-5 font-data text-[10.5px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
          <span>LEGALLY SUBJECTIVE — AN OPEN STANDARD. NO ONE OWNS IT.</span>
          <span className="text-white/60">BENCH-{id.toUpperCase()} · {dockets[0].standard} · UI-1.0 EXHIBIT</span>
          <Link href="/" className="text-white/60 hover:text-white">
            THE INTERROGATION →
          </Link>
        </div>
      </footer>
    </div>
  );
}
