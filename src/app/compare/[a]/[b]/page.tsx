import Link from "next/link";
import { notFound } from "next/navigation";
import { Chrome } from "@/components/ls/chrome";
import { Glyph } from "@/components/ls/glyph";
import { getSystemState } from "@/lib/system-state";
import {
  agreementPair,
  getAgreement,
  getDocket,
  listDockets,
  AXIS_LABELS,
  AXIS_METRIC_LABELS,
  lastName,
} from "@/lib/dockets";

/* ————————————————————————————————————————————————
   THE OTHER DOOR — two judges, the quantified counterfactual.
   Function: superimpose two filed fingerprints, expose per-axis deltas,
   and state — from common merits votes — how often the two split.
   Result: the ONE DOOR DOWN question, answered with numbers.
   ———————————————————————————————————————————————— */

const AXES = ["disposition", "temperament", "precedent", "reversal", "orality", "exposure"] as const;

export async function generateStaticParams() {
  const dockets = await listDockets();
  const out: Array<{ a: string; b: string }> = [];
  for (const x of dockets) {
    for (const y of dockets) {
      if (x.subject.slug !== y.subject.slug) out.push({ a: x.subject.slug, b: y.subject.slug });
    }
  }
  return out;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ a: string; b: string }>;
}) {
  const { a, b } = await params;
  const [da, db] = await Promise.all([getDocketBySlug(a), getDocketBySlug(b)]);
  if (!da || !db) return { title: "Comparison not found — Legally Subjective" };
  return {
    title: `${lastName(da.subject.name)} v. ${lastName(db.subject.name)} · Legally Subjective`,
    description: `The quantified counterfactual: ${da.subject.name} and ${db.subject.name}, fingerprint against fingerprint, axis by axis. One door down.`,
  };
}

async function getDocketBySlug(slug: string) {
  const dockets = await listDockets();
  return dockets.find((d) => d.subject.slug === slug) ?? null;
}

export default async function ComparePage({
  params,
}: {
  params: Promise<{ a: string; b: string }>;
}) {
  const [{ a, b }, sys] = await Promise.all([params, getSystemState()]);
  const [da, db, agreement] = await Promise.all([
    getDocketBySlug(a),
    getDocketBySlug(b),
    getAgreement(),
  ]);
  if (!da || !db || da.docket === db.docket) notFound();

  const pair = agreementPair(agreement, da.subject.slug, db.subject.slug);
  const agreePct = pair?.agree != null ? pair.agree * 100 : null;
  const splitPct = agreePct != null ? 100 - agreePct : null;

  const axesOf = (d: typeof da) =>
    Object.fromEntries(AXES.map((ax) => [ax, d.axes[ax]?.percentile ?? null]));

  const swapHref = `/compare/${db.subject.slug}/${da.subject.slug}`;

  return (
    <div className="flex min-h-screen flex-col bg-paper font-display text-ink">
      <Chrome
        build={sys.build}
        judgesScored={sys.judgesScored}
        docketsIngested={sys.docketsIngested}
        engineCycles={sys.engineCycles}
        engineLast={sys.engineLast}
        state={sys.state}
        route={`/compare/${da.subject.slug}/${db.subject.slug}`}
      />

      <main className="flex-1">
        {/* ——— THE CAPTION — a case between two judges ——— */}
        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14 lg:py-14">
            <p className="micro">
              [{da.docket} v. {db.docket}] · The other door
            </p>
            <h1 className="mt-5 font-display text-[clamp(2rem,4.4vw,3.6rem)] font-bold uppercase leading-[0.98] tracking-[-0.02em]">
              {lastName(da.subject.name)} <span className="text-signal">v.</span> {lastName(db.subject.name)}
            </h1>
            <p className="mt-4 max-w-3xl text-[14px] leading-relaxed text-ink-2">
              {da.subject.name} and {db.subject.name}, measured from the same filed
              record — window {da.window.start.slice(0, 4)}–{da.window.end.slice(0, 10)},
              standard {da.standard}. Same court, different door. What changes when the
              door changes is below — in numbers, with their uncertainty.
            </p>
            <div className="mt-6 flex flex-wrap gap-3 font-data text-[11px] font-medium tracking-[0.06em] uppercase">
              <Link href={swapHref} className="border border-ink px-4 py-2.5 hover:bg-ink hover:text-white">
                Swap the door ⇄
              </Link>
              <Link href={`/judge/${da.docket}`} className="border border-rule px-4 py-2.5 text-ink-2 hover:border-ink hover:text-ink">
                {da.docket} case file →
              </Link>
              <Link href={`/judge/${db.docket}`} className="border border-rule px-4 py-2.5 text-ink-2 hover:border-ink hover:text-ink">
                {db.docket} case file →
              </Link>
            </div>
          </div>
        </section>

        {/* ——— THE HEADLINE NUMBER — the split rate ——— */}
        {splitPct != null && (
          <section className="border-b border-rule">
            <div className="mx-auto max-w-[1600px] px-6 py-12 sm:px-10 lg:px-14">
              <p className="micro">[001] The split — computed from common merits votes</p>
              <div className="mt-6 grid grid-cols-1 items-end gap-10 lg:grid-cols-[1.1fr_1fr]">
                <div>
                  <p className="font-data text-[clamp(4.5rem,11vw,9rem)] leading-[0.85] font-semibold tabular">
                    {splitPct.toFixed(1)}
                    <span className="text-[0.35em] font-medium">%</span>
                  </p>
                  <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-ink-2">
                    In the {pair?.n.toLocaleString("en-US")} merits cases{" "}
                    {lastName(da.subject.name)} and {lastName(db.subject.name)} sat on together, their votes
                    split <strong>{splitPct.toFixed(1)}%</strong> of the time. The rest of
                    this page decomposes that split — axis by axis — into measured
                    differences of temperament, disposition, and craft. It is a record,
                    not a prediction.
                  </p>
                </div>
                {/* both fingerprints, side by side */}
                <div className="flex items-center gap-6">
                  <figure className="flex-1">
                    <Glyph
                      docketId={da.docket}
                      axes={axesOf(da)}
                      n={Math.max(da.raw.merits_votes, da.raw.lead_opinions)}
                      maxN={400}
                      className="w-full"
                    />
                    <figcaption className="mt-2 text-center font-data text-[10px] tracking-[0.04em] text-ink-3 uppercase">
                      {da.docket} · {lastName(da.subject.name)}
                    </figcaption>
                  </figure>
                  <span className="font-display text-[22px] font-bold text-signal">v.</span>
                  <figure className="flex-1">
                    <Glyph
                      docketId={db.docket}
                      axes={axesOf(db)}
                      n={Math.max(db.raw.merits_votes, db.raw.lead_opinions)}
                      maxN={400}
                      className="w-full"
                    />
                    <figcaption className="mt-2 text-center font-data text-[10px] tracking-[0.04em] text-ink-3 uppercase">
                      {db.docket} · {lastName(db.subject.name)}
                    </figcaption>
                  </figure>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ——— THE DELTAS — per-axis counterfactual ——— */}
        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <p className="micro">[002] The deltas — signed percentile differences ({lastName(da.subject.name)} − {lastName(db.subject.name)})</p>
            <div className="mt-6 border-t border-rule">
              {AXES.map((ax) => {
                const va = da.axes[ax]?.percentile ?? null;
                const vb = db.axes[ax]?.percentile ?? null;
                const delta = va != null && vb != null ? va - vb : null;
                const maxAbs = Math.max(
                  Math.abs(delta ?? 0),
                  ...AXES.flatMap((x) => {
                    const xa = da.axes[x]?.percentile;
                    const xb = db.axes[x]?.percentile;
                    return xa != null && xb != null ? [Math.abs(xa - xb)] : [0];
                  }),
                );
                return (
                  <div
                    key={ax}
                    className="grid grid-cols-1 gap-x-8 gap-y-2 border-b border-hairline py-4 sm:grid-cols-[190px_90px_90px_90px_1fr]"
                  >
                    <p className="font-display text-[14px] font-bold uppercase">{AXIS_LABELS[ax]}</p>
                    <p className="font-data text-[14px] font-semibold tabular">
                      {va == null ? <span className="text-ink-3">—</span> : va}
                    </p>
                    <p className="font-data text-[14px] font-semibold tabular">
                      {vb == null ? <span className="text-ink-3">—</span> : vb}
                    </p>
                    <p
                      className={`font-data text-[16px] font-semibold tabular ${
                        delta == null ? "text-ink-3" : delta > 0 ? "text-signal-deep" : delta < 0 ? "text-ink" : "text-ink-3"
                      }`}
                    >
                      {delta == null ? "—" : delta > 0 ? `+${delta}` : delta}
                    </p>
                    {/* diverging bar from center */}
                    <div className="relative hidden h-[10px] self-center border border-rule sm:block">
                      <div className="absolute inset-y-0 left-1/2 w-px bg-rule" />
                      {delta != null && maxAbs > 0 && (
                        <div
                          className={`absolute inset-y-[2px] ${delta > 0 ? "bg-signal" : "bg-ink"}`}
                          style={{
                            left: delta > 0 ? "50%" : `${50 - (Math.abs(delta) / maxAbs) * 48}%`,
                            width: `${(Math.abs(delta) / maxAbs) * 48}%`,
                          }}
                        />
                      )}
                    </div>
                    <p className="text-[11px] leading-snug text-ink-3 sm:col-span-5">
                      {delta == null
                        ? "Insufficient data on at least one side — delta is null, never estimated."
                        : `${AXIS_METRIC_LABELS[ax]} · ${da.axes[ax].metric_def?.split(".")[0] ?? ""}.`}
                    </p>
                  </div>
                );
              })}
            </div>
            <p className="micro mt-5 normal-case tracking-[0.02em] text-ink-3">
              Per LS-1.0 §6, the v. inherits the older standard version of the pair and
              flags any version mismatch. Here: {da.standard} / {db.standard}
              {da.standard === db.standard ? " — no mismatch." : " — MISMATCH FLAGGED."}
            </p>
          </div>
        </section>

        {/* ——— THE UNION OF CHAINS ——— */}
        <section className="border-b border-rule bg-paper-2">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <p className="micro">[003] The union of chains — both records, full custody</p>
            <div className="mt-6 grid grid-cols-1 gap-10 lg:grid-cols-2">
              {[da, db].map((d) => (
                <div key={d.docket}>
                  <p className="font-display text-[15px] font-bold uppercase">
                    {d.docket} — {d.subject.name}
                  </p>
                  <dl className="mt-3 space-y-2 font-data text-[11.5px]">
                    {[
                      ["SHA-256", d.chain.sha256 ?? "—"],
                      ["Filed", d.filed_at.slice(0, 10)],
                      ["Pipeline", d.chain.pipeline],
                      ["Votes / opinions", `${d.raw.merits_votes.toLocaleString("en-US")} / ${d.raw.lead_opinions}`],
                      ["Limits", `${d.limits.length} disclosed`],
                    ].map(([k, v]) => (
                      <div key={k} className="grid grid-cols-[140px_1fr] gap-3 border-b border-hairline pb-2">
                        <dt className="text-[9.5px] tracking-[0.08em] text-ink-3 uppercase">{k}</dt>
                        <dd className="break-all">{v}</dd>
                      </div>
                    ))}
                  </dl>
                  <Link href={`/docket/${d.docket}`} className="mt-3 inline-block font-data text-[11px] text-signal-deep hover:underline">
                    full chain of custody →
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-ink text-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-5 font-data text-[10.5px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
          <span>LEGALLY SUBJECTIVE — AN OPEN STANDARD. NO ONE OWNS IT.</span>
          <span className="text-white/60">
            {da.docket} v. {db.docket} · {da.standard} · UI-1.0 EXHIBIT
          </span>
          <Link href="/court/scotus" className="text-white/60 hover:text-white">
            THE BENCH →
          </Link>
        </div>
      </footer>
    </div>
  );
}
