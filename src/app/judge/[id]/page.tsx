import Link from "next/link";
import { notFound } from "next/navigation";
import { Chrome } from "@/components/ls/chrome";
import { Glyph } from "@/components/ls/glyph";
import { getSystemState } from "@/lib/system-state";
import { getCases } from "@/lib/research";
import {
  AXIS_LABELS,
  AXIS_METRIC_LABELS,
  AXIS_ORDER,
  citation,
  getDocket,
  lastName,
  listDockets,
  type Docket,
} from "@/lib/dockets";

/* ————————————————————————————————————————————————
   THE CASE FILE — one judge, the whole record.
   Function: display the filed fingerprint with its uncertainty,
   its raw counts, its limits, and its chain of custody.
   Result: a page that is the docket — nothing decorative.
   ———————————————————————————————————————————————— */

export async function generateStaticParams() {
  const dockets = await listDockets();
  return dockets.map((d) => ({ id: d.docket }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const d = await getDocket(id);
  if (!d) return { title: "Docket not found — Legally Subjective" };
  return {
    title: `In re ${d.subject.name} — ${d.docket} · Legally Subjective`,
    description: `The filed Subjectivity Fingerprint of ${d.subject.name}: six axes, percentiles against the declared bench of thirteen, confidence intervals, N. ${d.raw.merits_votes} merits votes, ${d.raw.lead_opinions} lead opinions.`,
  };
}

function PercentileBar({ pct }: { pct: number | null }) {
  if (pct == null) {
    return <div className="h-[6px] w-full border border-dashed border-rule bg-paper" />;
  }
  return (
    <div className="relative h-[6px] w-full border border-rule bg-paper">
      <div className="absolute inset-y-0 left-0 bg-signal" style={{ width: `${pct}%` }} />
    </div>
  );
}

function AxisRow({ axis, d }: { axis: string; d: Docket }) {
  const a = d.axes[axis];
  const ok = a.percentile != null;
  return (
    <div className="grid grid-cols-1 gap-x-8 gap-y-3 border-b border-hairline py-5 lg:grid-cols-[210px_150px_1fr_110px]">
      <div>
        <p className="font-display text-[15px] font-bold uppercase tracking-[0.01em]">
          {AXIS_LABELS[axis]}
        </p>
        <p className="mt-1 font-data text-[10.5px] tracking-[0.04em] text-ink-3 uppercase">
          {ok ? AXIS_METRIC_LABELS[axis] : a.note ?? a.status}
        </p>
      </div>
      <div>
        {ok ? (
          <>
            <p className="font-data text-[30px] leading-none font-semibold tabular">
              {a.percentile}
              <span className="text-[13px] font-medium text-ink-3"> pct</span>
            </p>
            <p className="mt-1.5 font-data text-[11px] text-ink-2 tabular">
              RANK BAND [{a.rank_band?.[0] ?? "—"}, {a.rank_band?.[1] ?? "—"}] · N={a.n.toLocaleString("en-US")}
              {a.value_ci95 && (
                <span className="text-signal-deep">
                  {" ·"} VALUE 95% CI [{(a.value_ci95[0] * 100).toFixed(1)}–{(a.value_ci95[1] * 100).toFixed(1)}%]
                </span>
              )}
            </p>
          </>
        ) : (
          <p className="font-data text-[30px] leading-none font-semibold text-ink-3">—</p>
        )}
      </div>
      <div className="text-[12.5px] leading-relaxed text-ink-2">
        {a.metric_def ?? "Not computable from current sources. Rendered as missing — never estimated."}
        {ok && a.value != null && (
          <span className="mt-1 block font-data text-[11px] text-ink-3">
            measured value: {a.value.toLocaleString("en-US", { maximumFractionDigits: 4 })}
          </span>
        )}
      </div>
      <div className="lg:justify-self-end">
        <span
          className={`font-data text-[10px] font-medium tracking-[0.08em] uppercase ${
            ok ? "text-signal-deep" : "text-ink-3"
          }`}
        >
          {ok ? "■ FILED" : "○ " + a.status.toUpperCase()}
        </span>
      </div>
    </div>
  );
}

export default async function JudgePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [d, sys, allCases] = await Promise.all([
    getDocket(id),
    getSystemState(),
    getCases(),
  ]);
  if (!d || d.status !== "FILED") notFound();

  const slug = d.subject.slug;

  // ——— DIVERGENCE PROFILE: where this justice breaks with the bench, per issue area ———
  // (Renamed from "blind spots" — LS-AUDIT-001 inj. 11: no normative label
  // on a named judge. A divergence is a fact; a "blind spot" is a verdict.)
  // Real computation from the case record: for each issue area with
  // enough shared cases, the justice's dissent rate vs the bench's on the
  // same cases (self excluded). Divergence = the gap in points.
  const blindSpots: { circuit: string; n: number; own: number; bench: number; gap: number }[] = [];
  if (allCases) {
    const byCircuit = new Map<string, { own: [number, number]; others: [number, number] }>();
    for (const c of allCases.cases) {
      const own = c.votes[slug];
      const participants = Object.keys(c.votes);
      if (!participants.includes(slug)) continue;
      let rec = byCircuit.get(c.issue_area);
      if (!rec) {
        rec = { own: [0, 0], others: [0, 0] };
        byCircuit.set(c.issue_area, rec);
      }
      if (own === "minority") rec.own[0] += 1;
      rec.own[1] += 1;
      for (const s of participants) {
        if (s === slug) continue;
        if (c.votes[s] === "minority") rec.others[0] += 1;
        rec.others[1] += 1;
      }
    }
    for (const [circuit, rec] of byCircuit) {
      if (rec.own[1] < 6) continue;
      const ownRate = rec.own[0] / rec.own[1];
      const benchRate = rec.others[0] / Math.max(rec.others[1], 1);
      blindSpots.push({
        circuit,
        n: rec.own[1],
        own: ownRate,
        bench: benchRate,
        gap: ownRate - benchRate,
      });
    }
    blindSpots.sort((a, b) => Math.abs(b.gap) - Math.abs(a.gap));
  }
  const axesForGlyph = Object.fromEntries(
    AXIS_ORDER.map((ax) => [ax, d.axes[ax]?.percentile ?? null]),
  );
  const maxN = Math.max(d.raw.merits_votes, d.raw.lead_opinions);

  return (
    <div className="flex min-h-screen flex-col bg-paper font-display text-ink">
      <Chrome
        justices={sys.judgesScored}
        cases={sys.casesDecided}
        windowLabel={sys.windowLabel}
        state={sys.state}
      />

      <main className="flex-1">
        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14 lg:py-14">
            <p className="micro">[{d.docket}] · The case file</p>
            <div className="mt-5 grid grid-cols-1 gap-x-14 gap-y-8 lg:grid-cols-[1fr_300px]">
              <div>
                <h1 className="font-display text-[clamp(2.4rem,5.2vw,4.2rem)] font-bold uppercase leading-[0.98] tracking-[-0.02em]">
                  In re {d.subject.name}
                </h1>
                <dl className="mt-7 grid max-w-3xl grid-cols-2 gap-x-8 gap-y-3 font-data text-[12px] sm:grid-cols-4">
                  {[
                    ["Role", d.subject.role.replace("-", " ")],
                    ["Court", "SCOTUS"],
                    ["Bench", `${d.subject.bench_n} · §3.5bis`],
                    ["Window", `${d.window.start.slice(0, 4)} — ${d.window.end.slice(0, 10)}`],
                    ["Status", d.status],
                    ["Filed", d.filed_at.slice(0, 10)],
                    ["Standard", d.standard],
                    ["Revision", String(d.revision)],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <dt className="text-[10px] tracking-[0.08em] text-ink-3 uppercase">{k}</dt>
                      <dd className="mt-0.5 font-medium tracking-[0.01em] uppercase">{v}</dd>
                    </div>
                  ))}
                </dl>
              </div>
              <figure className="mx-auto w-full max-w-[300px]">
                <Glyph docketId={d.docket} axes={axesForGlyph} n={maxN} maxN={400} className="w-full" />
                <figcaption className="mt-3 font-data text-[10px] tracking-[0.04em] text-ink-3 uppercase">
                  Fingerprint {d.docket} · evidence ring n={maxN.toLocaleString("en-US")} · dashed = insufficient data
                </figcaption>
              </figure>
            </div>
          </div>
        </section>

        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <p className="micro">[001] The raw count</p>
            <div className="mt-6 grid grid-cols-2 gap-px border border-rule bg-rule sm:grid-cols-3 lg:grid-cols-6">
              {[
                ["Merits votes", d.raw.merits_votes.toLocaleString("en-US"), "SCDB 2025_01 · vote records"],
                ["Dissents", d.raw.dissents.toLocaleString("en-US"), "votes cast with the minority"],
                ["Separate writings", d.raw.separate_writings.toLocaleString("en-US"), "SCDB opinion codes 2/3 — written positions"],
                ["Lead opinions", d.raw.lead_opinions.toLocaleString("en-US"), "SCDB · majOpinWriter"],
                ["Service years", String(d.raw.service_years_window), "terms present in the window"],
                ["Dissent rate", `${((d.raw.dissents / Math.max(d.raw.merits_votes, 1)) * 100).toFixed(1)}%`, "raw · pre-percentile"],
              ].map(([k, v, note]) => (
                <div key={k} className="bg-paper px-5 py-6">
                  <p className="font-data text-[10px] tracking-[0.08em] text-ink-3 uppercase">{k}</p>
                  <p className="mt-2 font-data text-[26px] leading-none font-semibold tabular">{v}</p>
                  <p className="mt-2 text-[11px] leading-snug text-ink-3">{note}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <p className="micro">[002] The six axes — percentile against the declared bench of thirteen</p>
            <h2 className="mt-4 font-display text-[clamp(1.7rem,3vw,2.5rem)] font-bold uppercase leading-[1.02] tracking-[-0.01em]">
              The fingerprint, with its uncertainty in full view.
            </h2>
            <div className="mt-8 border-t border-rule">
              {AXIS_ORDER.map((ax) => (
                <AxisRow key={ax} axis={ax} d={d} />
              ))}
            </div>
            <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_260px]">
              <div>
                {Object.entries(d.axes)
                  .filter(([, a]) => a.percentile != null)
                  .map(([ax, a]) => (
                    <div key={ax} className="mb-3">
                      <p className="mb-1 flex items-baseline justify-between font-data text-[10.5px] tracking-[0.04em] uppercase">
                        <span className="text-ink-2">{AXIS_LABELS[ax]}</span>
                        <span className="tabular">{a.percentile} · RANK [{a.rank_band?.[0]}, {a.rank_band?.[1]}]</span>
                      </p>
                      <PercentileBar pct={a.percentile} />
                    </div>
                  ))}
              </div>
              <p className="font-data text-[11px] leading-relaxed tracking-[0.02em] text-ink-3">
                Percentile = median-rank within the declared bench (the
                thirteen justices who sat OT2015–2023). A bench of thirteen
                yields thirteen discrete values — the granularity is coarse
                by construction and disclosed per §3.5bis.
                The bracketed band is the bootstrap range of that RANK on the
                bench — it is not a confidence interval of the measured value;
                where the value itself admits one (a binomial share), its
                Wilson 95% interval is shown beside it.
              </p>
            </div>
          </div>
        </section>

        <section className="border-b border-rule bg-paper-2">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <p className="micro">[003] The limits — read before citing</p>
            <ul className="mt-6 max-w-4xl space-y-3">
              {d.limits.map((l, i) => (
                <li key={i} className="flex gap-4 border-b border-hairline pb-3 text-[13.5px] leading-relaxed text-ink-2">
                  <span className="font-data text-[11px] font-semibold text-signal-deep tabular">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  {l}
                </li>
              ))}
            </ul>
          </div>
        </section>

        {blindSpots.length > 0 && (
          <section className="border-b border-rule">
            <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
              <p className="micro">[003b] Divergence profile — where {lastName(d.subject.name)} breaks with the bench</p>
              <h2 className="mt-4 font-display text-[clamp(1.5rem,2.8vw,2.2rem)] font-bold uppercase leading-[1.05] tracking-[-0.01em]">
                The cases where this justice votes apart from the others.
              </h2>
              <p className="mt-4 max-w-[70ch] text-[14px] leading-[1.7] text-ink-2">
                Grouped by the issue area of the case (SCDB 2025_01 coding),
                each row below compares this justice&apos;s dissent rate with
                the rate of the rest of the bench on the very same cases. A
                gap is a measured divergence on shared cases — not a
                deficiency, not a virtue, and not a prediction: walk the same
                appeal through it, and the record says the room behaved
                differently around you.
              </p>
              <div className="mt-7 border-t border-rule">
                {blindSpots.slice(0, 5).map((b) => (
                  <div
                    key={b.circuit}
                    className="grid grid-cols-1 gap-x-6 gap-y-1.5 border-b border-hairline py-4 sm:grid-cols-[170px_90px_1fr_130px] sm:items-baseline"
                  >
                    <span className="font-data text-[12px] font-semibold tracking-[0.03em] uppercase">
                      {b.circuit}
                    </span>
                    <span className="font-data text-[11px] text-ink-3 tabular">
                      n={b.n}
                    </span>
                    <span className="text-[13px] leading-relaxed text-ink-2">
                      dissents in <strong className="text-ink">{(b.own * 100).toFixed(0)}%</strong> of
                      cases in this area, while the rest of the bench dissents in{" "}
                      <strong className="text-ink">{(b.bench * 100).toFixed(0)}%</strong> of the
                      same cases
                    </span>
                    <span
                      className={`font-data text-[13px] font-bold tabular sm:justify-self-end ${
                        Math.abs(b.gap) >= 0.15
                          ? "text-signal-deep"
                          : "text-ink-3"
                      }`}
                    >
                      {b.gap > 0 ? "+" : "−"}
                      {Math.abs(b.gap * 100).toFixed(0)} pts
                    </span>
                  </div>
                ))}
              </div>
              <p className="mt-4 font-data text-[11px] leading-relaxed tracking-[0.02em] text-ink-3">
                Computed from the same filed votes as every other number on this
                page. Issue areas with fewer than 6 shared cases are withheld — a
                smaller sample would be gossip, not measurement.
              </p>
            </div>
          </section>
        )}

        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <p className="micro">[004] The chain</p>
            <div className="mt-6 grid grid-cols-1 gap-10 lg:grid-cols-2">
              <div>
                <h3 className="font-display text-[15px] font-bold uppercase">Custody</h3>
                <dl className="mt-4 space-y-2.5 font-data text-[12px]">
                  {[
                    ["Pipeline", d.chain.pipeline],
                    ["Computed at", d.chain.computed_at.replace("T", " ").replace("Z", " UTC")],
                    ["SHA-256", d.chain.sha256 ?? "—"],
                    ["Bootstrap", "10,000 iters · seed = sha256(docket|axis|LS-1.0) truncated to 32 bits"],
                  ].map(([k, v]) => (
                    <div key={k} className="grid grid-cols-[130px_1fr] gap-3 border-b border-hairline pb-2.5">
                      <dt className="text-[10px] tracking-[0.08em] text-ink-3 uppercase">{k}</dt>
                      <dd className="break-all">{v}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-5 flex flex-wrap gap-3 font-data text-[11px] font-medium tracking-[0.06em] uppercase">
                  <Link href={`/docket/${d.docket}`} className="border border-ink px-4 py-2.5 hover:bg-ink hover:text-white">
                    Chain of custody →
                  </Link>
                  <Link href={`/api/dockets/${d.docket}`} className="border border-rule px-4 py-2.5 text-ink-2 hover:border-ink hover:text-ink">
                    Canonical JSON →
                  </Link>
                  <Link href={`/compare/${d.subject.slug}/${d.subject.slug === "sotomayor" ? "alito" : "sotomayor"}`} className="border border-rule px-4 py-2.5 text-ink-2 hover:border-ink hover:text-ink">
                    Head to head →
                  </Link>
                </div>
              </div>
              <div>
                <h3 className="font-display text-[15px] font-bold uppercase">Cite this docket</h3>
                <blockquote className="mt-4 border-l-2 border-signal pl-4 text-[13.5px] leading-relaxed text-ink-2 italic">
                  {citation(d)}
                </blockquote>
                <p className="mt-4 font-data text-[11px] leading-relaxed text-ink-3">
                  BibTeX served alongside every docket at{" "}
                  <a href={`/api/dockets/${d.docket}/bibtex`} className="text-ink-2 underline">
                    /api/dockets/{d.docket}/bibtex
                  </a>
                  . Filed dockets are immutable; corrections produce revision + 1 with a
                  supersede pointer.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-ink text-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-5 font-data text-[10.5px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
          <span>LEGALLY SUBJECTIVE — AN OPEN STANDARD. NO ONE OWNS IT.</span>
          <span className="text-white/60">{d.docket} · {d.standard} · UI-1.0 EXHIBIT</span>
          <Link href="/court/scotus" className="text-white/60 hover:text-white">
            THE BENCH →
          </Link>
        </div>
      </footer>
    </div>
  );
}
