import { Draw } from "@/components/ls/draw";
import { getSystemState } from "@/lib/system-state";
import { getBench } from "@/lib/justices";
import { listDockets, getAgreement } from "@/lib/dockets";

/* ————————————————————————————————————————————————
   THE FRONT OF THE SHOP — one page, one question,
   one number, one button.

   The back room (dockets, axes, chain of custody) is
   built and real — it hides behind THE DRAW, one click
   deep, for the 2% who need to verify. The 98% spin,
   feel the floor move, and share.

   Every number the wheel can land on is real and
   traceable: data/dockets/LS-J-001..013.json, axis
   "disposition", measured on recorded SCDB votes
   (Corpus-Monde v1, OT2015–OT2023).

   LS-AUDIT-001, injonction 1: every public percentage
   below carries its EFFECTIVE N and its Wilson ±,
   computed here from the FILED record — never typed
   by hand, never juxtaposed without its base.
   ———————————————————————————————————————————————— */

/** Wilson half-width (percentage points) for a share p over n trials. */
function wilsonPm(p: number, n: number): number {
  const z = 1.959964;
  const denom = 1 + (z * z) / n;
  const center = (p + (z * z) / (2 * n)) / denom;
  const half = (z / denom) * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n));
  const lo = Math.max(0, center - half);
  const hi = Math.min(1, center + half);
  return Math.round((hi - lo) * 50);
}

interface Question {
  n: string;
  q: string;
  a: React.ReactNode;
  door: string;
  href: string;
}

export default async function Home() {
  const [sys, bench, dockets, agreement] = await Promise.all([
    getSystemState(),
    getBench(),
    listDockets(),
    getAgreement(),
  ]);
  const live = sys.state === "WARM";

  /* ——— The vedette pair, recomputed from the FILED record ———
     The most divided and the closest sitting pair, each with its
     shared-case count and Wilson ± — found in the agreement
     production, never typed by hand. */
  const pairs = agreement?.pairs ?? {};
  let dividedKey: string | null = null;
  let alignedKey: string | null = null;
  for (const [key, v] of Object.entries(pairs)) {
    if (v.agree == null) continue;
    if (!dividedKey || v.agree < pairs[dividedKey].agree) dividedKey = key;
    if (!alignedKey || v.agree > pairs[alignedKey].agree) alignedKey = key;
  }
  const divided = dividedKey ? pairs[dividedKey] : null;
  const aligned = alignedKey ? pairs[alignedKey] : null;
  const pctDiv = divided?.agree != null ? Math.round(divided.agree * 1000) / 10 : null;
  const pctAln = aligned?.agree != null ? Math.round(aligned.agree * 1000) / 10 : null;
  const fullName = (slug: string) =>
    dockets.find((d) => d.subject.slug === slug)?.subject.name ?? slug;
  const shortName = (slug: string) => {
    const n = fullName(slug);
    const stripped = n.replace(/,?\s*(Jr\.|Sr\.|II|III|IV)\s*$/i, "").trim();
    return stripped.split(/\s+/).slice(-1)[0];
  };
  const [divA, divB] = (dividedKey ?? "a|b").split("|");
  const [alnA, alnB] = (alignedKey ?? "a|b").split("|");

  /* ——— The dissent range and citation range, from the dockets ——— */
  const tempers = dockets
    .map((d) => ({ slug: d.subject.slug, name: d.subject.name, a: d.axes.temperament }))
    .filter((x) => x.a?.value != null)
    .map((x) => ({ ...x, v: x.a!.value as number, n: x.a!.n }));
  const loTemp = tempers.length
    ? tempers.reduce((m, x) => (x.v < m.v ? x : m), tempers[0])
    : null;
  const hiTemp = tempers.length
    ? tempers.reduce((m, x) => (x.v > m.v ? x : m), tempers[0])
    : null;
  const prec = dockets
    .map((d) => ({ name: d.subject.name, a: d.axes.precedent }))
    .filter((x) => x.a?.value != null)
    .map((x) => ({ v: x.a!.value as number, n: x.a!.n }));
  const loPrec = prec.length ? prec.reduce((m, x) => (x.v < m.v ? x : m), prec[0]) : null;
  const hiPrec = prec.length ? prec.reduce((m, x) => (x.v > m.v ? x : m), prec[0]) : null;
  const tempFold =
    loTemp && hiTemp && loTemp.v > 0 ? (hiTemp.v / loTemp.v).toFixed(1) : null;

  const split100 =
    divided?.agree != null ? Math.round((1 - divided.agree) * 100) : null;

  const QUESTIONS: Question[] = [
    {
      n: "01",
      q: "Does it matter which judge you draw?",
      a: (
        <>
          On the cases they decided together ({divided?.n ?? "—"} shared
          cases), {fullName(divA)} and {fullName(divB)} voted the same way{" "}
          <strong className="text-signal-deep">
            {pctDiv ?? "—"}%
          </strong>{" "}
          <span className="font-data text-[12px] text-ink-3">
            (±{divided?.agree != null ? wilsonPm(divided.agree, divided.n) : "—"} pts)
          </span>{" "}
          — they split on nearly half of them. {fullName(alnA)} and{" "}
          {fullName(alnB)}:{" "}
          <strong className="text-signal-deep">{pctAln ?? "—"}%</strong>{" "}
          <span className="font-data text-[12px] text-ink-3">
            (±{aligned?.agree != null ? wilsonPm(aligned.agree, aligned.n) : "—"} pts,{" "}
            {aligned?.n ?? "—"} shared cases)
          </span>
          . Same court. Same cases. Same law. Different bases — different
          counts, which is why each carries its own.
        </>
      ),
      door: "Meet the bench",
      href: "/court/scotus",
    },
    {
      n: "02",
      q: "Do feelings play a role in justice?",
      a: (
        <>
          Nobody can read a judge&apos;s heart. Behavior can be counted. How
          often a justice stands alone in dissent runs from{" "}
          <strong className="text-signal-deep">
            {loTemp ? (loTemp.v * 100).toFixed(1) : "—"}%
          </strong>{" "}
          {loTemp && (
            <span className="font-data text-[12px] text-ink-3">
              ({loTemp.n} votes, ±{wilsonPm(loTemp.v, loTemp.n)} pts)
            </span>
          )}{" "}
          to{" "}
          <strong className="text-signal-deep">
            {hiTemp ? (hiTemp.v * 100).toFixed(1) : "—"}%
          </strong>{" "}
          {hiTemp && (
            <span className="font-data text-[12px] text-ink-3">
              ({hiTemp.n} votes, ±{wilsonPm(hiTemp.v, hiTemp.n)} pts)
            </span>
          )}{" "}
          across this bench{tempFold ? ` — a ${tempFold}-fold gap` : ""}. How
          heavily their opinions anchor in precedent runs from{" "}
          <strong className="text-signal-deep">
            {loPrec ? Math.round(loPrec.v) : "—"}
          </strong>{" "}
          to{" "}
          <strong className="text-signal-deep">
            {hiPrec ? Math.round(hiPrec.v) : "—"}
          </strong>{" "}
          citing decisions per authored opinion
          {loPrec && hiPrec && (
            <span className="font-data text-[12px] text-ink-3">
              {" "}
              ({loPrec.n}–{hiPrec.n} opinions; means, no interval)
            </span>
          )}
          . Different judges are, measurably, different deciders.
        </>
      ),
      door: "See what we measure",
      href: "/standard",
    },
    {
      n: "03",
      q: "How different is one door from the next?",
      a: (
        <>
          Pick any two of the bench. The counterfactual is computed, not
          asserted: where they diverge, by how much, and with what
          uncertainty — all from votes they actually cast on cases they both
          heard. The most divided pair on this Court splits on{" "}
          <strong className="text-signal-deep">
            {split100 ?? "—"} of every 100
          </strong>{" "}
          common votes
          <span className="font-data text-[12px] text-ink-3">
            {" "}
            ({divided?.n ?? "—"} shared cases)
          </span>
          .
        </>
      ),
      door: "Compare two judges",
      href: dividedKey ? `/compare/${divA}/${divB}` : "/compare/kavanaugh/jackson",
    },
    {
      n: "04",
      q: "Why trust a number about a judge?",
      a: (
        <>
          Because you don&apos;t have to. Every figure on this site carries its
          own receipt: the exact public filing it came from, the date it was
          read, and a fingerprint anyone can re-verify at home. And since the
          internal audit of August 2026, every public percentage carries its
          vote count and its ± — a number without its interval is an opinion
          in costume, and this project refuses to wear it. If a number
          can&apos;t be traced to a public document, it doesn&apos;t appear
          here. That is the whole method.
        </>
      ),
      door: "Trace a number",
      href: "/docket/LS-J-001",
    },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-paper font-display text-ink">
      <main className="flex-1">
        {/* ——— THE DRAW — the whole store ——— */}
        <Draw
          bench={bench}
          windowLabel={sys.windowLabel}
          casesDecided={sys.casesDecided}
        />

        {/* ——— THE QUESTIONS — below the fold, for the 2% ——— */}
        <section id="questions" className="scroll-mt-16 border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-16 sm:px-10 lg:px-14 lg:py-20">
            <p className="micro">[002] For those who want to dig</p>
            <h2 className="mt-5 font-display text-[clamp(1.7rem,3.2vw,2.5rem)] font-bold uppercase leading-[1.02] tracking-[-0.02em]">
              The questions behind the wheel.
            </h2>
            <p className="mt-5 max-w-[62ch] font-display text-[15px] leading-relaxed text-ink-2">
              The spin makes you feel it; these pages prove it. No opinions —
              only counts from {sys.casesDecided} decided cases read off the
              public record{sys.windowLabel ? ` (${sys.windowLabel})` : ""},
              Supreme Court of the United States — each with its count and
              its honest width.
            </p>

            {/* LS-AUDIT-001 inj. 4 — the counter reconciliation, public.
                The corpus ladder itself is the display: each step is a
                documented filter, explained in one clause. */}
            <div className="mt-8 border border-ink bg-paper-2 px-5 py-4">
              <p className="font-data text-[10.5px] font-bold tracking-[0.1em] uppercase text-signal-deep">
                The count, reconciled — every step is a documented filter
              </p>
              <p className="mt-2.5 font-data text-[12px] leading-[1.8] tracking-[0.01em] text-ink-2">
                <span className="font-bold tabular text-ink">
                  {sys.corpusArgued}
                </span>{" "}
                argued cases entered the frozen corpus rule (OT2015–OT2023,
                argued on the merits)
                <span className="text-ink-3">
                  {" "}
                  — the rule is sealed, it does not move to flatter a result
                </span>{" "}
                →{" "}
                <span className="font-bold tabular text-ink">
                  {sys.joinedScdb}
                </span>{" "}
                carry machine-readable SCDB votes
                <span className="text-ink-3">
                  {" "}
                  (the rest kept their CourtListener docket — SCDB had not
                  coded them; a source gap, not a choice)
                </span>{" "}
                →{" "}
                <span className="font-bold tabular text-ink">
                  {sys.withDirection}
                </span>{" "}
                carry a coded decision direction
                <span className="text-ink-3">
                  {" "}
                  (conservative or liberal — the label every prediction task
                  in the protocol uses)
                </span>{" "}
                →{" "}
                <span className="font-bold tabular text-ink">
                  {sys.trainSplit}
                </span>{" "}
                form the training split (OT2015–OT2019) and{" "}
                <span className="font-bold tabular text-ink">
                  {sys.testSplit}
                </span>{" "}
                the test split (OT2020–2023)
                <span className="text-ink-3">
                  {" "}
                  — time-ordered, so no future leaks into the past
                </span>{" "}
                → and{" "}
                <span className="font-bold tabular text-ink">
                  {sys.sealed}
                </span>{" "}
                of the{" "}
                <span className="font-bold tabular text-ink">
                  {sys.fiveFour}
                </span>{" "}
                decisions won 5–4 are sealed under SHA-256 for the final
                exam. Every step is a documented filter, not a loss of truth.
              </p>
            </div>

            <div className="mt-10 border-t border-rule">
              {QUESTIONS.map((item) => {
                const row = (
                  <>
                    <span className="tabular font-data text-[13px] font-semibold text-ink-3">
                      {item.n}
                    </span>
                    <span className="font-display text-[clamp(1.05rem,1.8vw,1.45rem)] font-bold uppercase leading-tight tracking-[-0.01em]">
                      {item.q}
                    </span>
                    <span className="max-w-[68ch] text-[14.5px] leading-[1.75] text-ink-2">
                      {item.a}
                    </span>
                    <span className="font-data text-[11px] font-semibold tracking-[0.08em] uppercase text-signal-deep sm:justify-self-end">
                      {item.door} →
                    </span>
                  </>
                );
                const cls =
                  "grid grid-cols-1 gap-x-8 gap-y-2.5 border-b border-hairline py-6 sm:grid-cols-[44px_260px_1fr_170px] sm:items-baseline sm:gap-y-1.5";
                return live ? (
                  <a key={item.n} href={item.href} className={`${cls} hover:bg-row-hover`}>
                    {row}
                  </a>
                ) : (
                  <div key={item.n} className={cls}>
                    {row}
                  </div>
                );
              })}
            </div>

            <p className="micro mt-7 normal-case leading-relaxed tracking-[0.04em] text-ink-3">
              This is an open measurement project, not a law firm. It does not
              predict any case and does not give legal advice. It counts what
              thirteen public officials publicly did across nine terms — so
              that &ldquo;it depends on the judge&rdquo; stops being a saying
              and becomes a number with its interval.
            </p>

            <div className="mt-8 flex flex-wrap gap-x-10 gap-y-3 font-data text-[11px] font-semibold tracking-[0.08em] uppercase">
              <a href="/cases" className="text-ink-2 hover:text-ink">
                The record — every case, searchable →
              </a>
              <a href="/paper" className="text-ink-2 hover:text-ink">
                The science — the research article →
              </a>
            </div>
            <p className="mt-3 max-w-[62ch] font-data text-[10.5px] leading-relaxed tracking-[0.02em] text-ink-3">
              The record opens all {sys.casesDecided} cases — the votes, the
              margin, what would have flipped each one. The science is the
              full program behind every number: the frozen corpus, the
              baselines to beat, the sealed protocol, and the honest state of
              what is not yet trained.
            </p>
          </div>
        </section>
      </main>

      {/* ——— FOOTER — the frame of the page ——— */}
      <footer className="bg-ink text-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-5 font-data text-[10.5px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
          <span>LEGALLY SUBJECTIVE — AN OPEN STANDARD. NO ONE OWNS IT.</span>
          <span className="text-white/60">
            SOURCES: SCDB · COURTLISTENER{sys.windowLabel ? ` · ${sys.windowLabel}` : ""}
          </span>
          <span className="flex items-center gap-x-6">
            <a href="/cases" className="text-white/60 hover:text-white">
              THE RECORD →
            </a>
            <a href="/paper" className="text-white/60 hover:text-white">
              THE SCIENCE →
            </a>
          </span>
        </div>
      </footer>
    </div>
  );
}
