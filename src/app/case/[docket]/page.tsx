import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Chrome } from "@/components/ls/chrome";
import { getSystemState } from "@/lib/system-state";
import { getCase, getResearchState, BENCH_ORDER, fmtDate } from "@/lib/research";
import { getBenchLabels } from "@/lib/research-page";

/* ————————————————————————————————————————————————
   ONE CASE — the record opened.

   Function: show what the public officials who sat on
   one dispute did — the votes, the margin, and what
   would have flipped it. Result: "it depends on the
   judge" becomes a specific, inspectable sentence
   about this case.
   ———————————————————————————————————————————————— */

export async function generateStaticParams() {
  const { getCases } = await import("@/lib/research");
  const all = await getCases();
  return (all?.cases ?? []).map((c) => ({ docket: c.docket }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ docket: string }>;
}) {
  const { docket } = await params;
  const c = await getCase(docket);
  if (!c) return { title: "Case not found — Legally Subjective" };
  return {
    title: `${c.name} — ${c.docket} · Legally Subjective`,
    description: `How the bench voted in ${c.name}: the ${c.split} split, ${c.flip_margin === 1 ? "one vote from flipping" : `${c.flip_margin ?? "—"} votes from flipping`}, and the direction on the record.`,
  };
}

export default async function CasePage({
  params,
}: {
  params: Promise<{ docket: string }>;
}) {
  const { docket } = await params;
  const [c, sys, rs, labels] = await Promise.all([
    getCase(docket),
    getSystemState(),
    getResearchState(),
    getBenchLabels(),
  ]);
  if (!c) notFound();

  const dissenters = BENCH_ORDER.filter(
    (s) => c.votes[s] === "minority",
  );
  const missing = BENCH_ORDER.filter((s) => !(s in c.votes));
  const b4 = rs?.baselines.find((b) => b.id === "B4") ?? null;

  return (
    <div className="flex min-h-screen flex-col bg-paper font-display text-ink">
      <Chrome
        justices={sys.judgesScored}
        cases={sys.casesDecided}
        windowLabel={sys.windowLabel}
        state={sys.state}
      />

      <main className="flex-1">
        {/* ——— HEADER ——— */}
        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14 lg:py-12">
            <p className="micro">
              <Link href="/cases" className="hover:text-ink">
                The record
              </Link>{" "}
              · No. {c.docket}
            </p>
            <h1 className="mt-4 max-w-5xl font-display text-[clamp(1.8rem,4vw,3.2rem)] font-bold uppercase leading-[1.02] tracking-[-0.02em]">
              {c.name}
            </h1>
            <dl className="mt-6 grid max-w-3xl grid-cols-2 gap-x-8 gap-y-3 font-data text-[12px] sm:grid-cols-4">
              {[
                ["Docket", `No. ${c.docket}`],
                ["Term", `OT${String(c.term).slice(2)}`],
                ["Issue area", c.issue_area],
                ["Decided", fmtDate(c.decided)],
                ["Split", c.split],
                [
                  "Direction",
                  c.direction === "conservative"
                    ? "conservative"
                    : c.direction === "liberal"
                      ? "liberal"
                      : "uncoded",
                ],
                [
                  "Disposition",
                  c.disposition ?? "—",
                ],
                ["Flip margin", c.flip_margin == null ? "not computable" : `${c.flip_margin} vote${c.flip_margin > 1 ? "s" : ""}`],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt className="text-[10px] tracking-[0.08em] text-ink-3 uppercase">{k}</dt>
                  <dd className="mt-0.5 font-medium tracking-[0.01em] uppercase">{v}</dd>
                </div>
              ))}
            </dl>
            {c.question && (
              <div className="mt-7 max-w-[75ch] border-l-2 border-ink pl-5">
                <p className="micro mb-2">Question presented</p>
                <p className="text-[15px] leading-[1.7] text-ink-2">{c.question}</p>
              </div>
            )}
            {c.direction && (
              <p className="mt-5 max-w-[70ch] font-data text-[11.5px] leading-relaxed tracking-[0.02em] text-ink-3">
                DIRECTION ON THE RECORD: {c.direction.toUpperCase()} (SCDB
                decisionDirection) · DISPOSITION: {(c.disposition ?? "uncoded").toUpperCase()}
                {c.petitioner_won === true
                  ? " · THE PARTY SEEKING RELIEF PREVAILED (REVERSAL)"
                  : c.petitioner_won === false
                    ? " · THE PARTY SEEKING RELIEF LOST (AFFIRMANCE)"
                    : ""}
                .
              </p>
            )}
          </div>
        </section>

        {/* ——— THE VOTE ——— */}
        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <p className="micro">[001] The vote — as recorded</p>
            <div className="mt-6 grid grid-cols-1 gap-px border border-rule bg-rule sm:grid-cols-2 lg:grid-cols-3">
              {BENCH_ORDER.map((s) => {
                const v = c.votes[s];
                const docketMap: Record<string, string> = {
                  roberts: "LS-J-001", thomas: "LS-J-002", alito: "LS-J-003",
                  sotomayor: "LS-J-004", kagan: "LS-J-005", gorsuch: "LS-J-006",
                  kavanaugh: "LS-J-007", barrett: "LS-J-008", jackson: "LS-J-009",
                  scalia: "LS-J-010", kennedy: "LS-J-011", ginsburg: "LS-J-012",
                  breyer: "LS-J-013",
                };
                return (
                  <div key={s} className="flex items-baseline justify-between gap-4 bg-paper px-5 py-4">
                    <div>
                      <p className="text-[15px] font-bold">{labels[s] ?? s}</p>
                      <Link
                        href={`/judge/${docketMap[s]}`}
                        className="font-data text-[10px] tracking-[0.05em] text-ink-3 uppercase hover:text-ink"
                      >
                        case file →
                      </Link>
                    </div>
                    <span
                      className={`font-data text-[11px] font-bold tracking-[0.1em] uppercase ${
                        v === "minority"
                          ? "bg-signal px-2.5 py-1 text-white"
                          : v === "majority"
                            ? "text-ink"
                            : "text-ink-3"
                      }`}
                    >
                      {v === "minority" ? "dissent" : v === "majority" ? "majority" : "not voting"}
                    </span>
                  </div>
                );
              })}
            </div>
            {missing.length > 0 && (
              <p className="mt-3 font-data text-[11px] tracking-[0.03em] text-ink-3">
                NOT VOTING: {missing.map((s) => labels[s] ?? s).join(", ")} — not
                on the bench that term, recused, or absent: recorded, never
                assumed.
              </p>
            )}
          </div>
        </section>

        {/* ——— ONE DOOR DOWN ——— */}
        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <p className="micro">[002] One door down</p>
            <div className="mt-5 grid grid-cols-1 gap-x-14 gap-y-8 lg:grid-cols-[1fr_360px]">
              <div>
                <p className="max-w-[75ch] text-[15px] leading-[1.75] text-ink-2">
                  {c.flip_margin == null ? (
                    <>
                      The public record for this case shows an irregular split —
                      no outright majority among the recorded votes. Rather
                      than guess at the arithmetic, the flip margin is
                      withheld: a number that cannot be computed from the
                      filing does not appear here. The votes themselves, below
                      and above, are exactly as recorded.
                    </>
                  ) : c.flip_margin === 1 ? (
                    <>
                      This case sat{" "}
                      <strong className="text-signal-deep">one vote</strong>{" "}
                      from the other outcome.{" "}
                      {dissenters.length > 0
                        ? `${dissenters.map((s) => labels[s]).join(", ")} ${
                            dissenters.length === 1 ? "was" : "were"
                          } already on the other side of the door — one more justice switching would have reversed the result outright.`
                        : "A single justice switching sides would have changed who won."}
                    </>
                  ) : (
                    <>
                      Flipping this case outright would have taken{" "}
                      <strong className="text-ink">
                        {c.flip_margin} justice{c.flip_margin > 1 ? "s" : ""}
                      </strong>{" "}
                      switching sides
                      {dissenters.length > 0
                        ? ` — ${dissenters.map((s) => labels[s]).join(", ")} ${
                            dissenters.length === 1 ? "was" : "were"
                          } already there.`
                        : "."}
                    </>
                  )}{" "}
                  The court records no reasons for votes — only the votes
                  themselves. Who was in the room is the part the parties never
                  chose.
                </p>
                {dissenters.length > 0 && (
                  <div className="mt-6">
                    <p className="micro mb-3">On the other side of the door</p>
                    <div className="flex flex-wrap gap-2">
                      {dissenters.map((s) => (
                        <span
                          key={s}
                          className="border border-signal px-3 py-1.5 font-data text-[11px] font-bold tracking-[0.08em] text-signal-deep uppercase"
                        >
                          {labels[s] ?? s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="self-start border border-rule">
                <div className="border-b border-rule bg-paper-2 px-5 py-4">
                  <p className="font-data text-[10px] tracking-[0.08em] text-ink-3 uppercase">
                    The margin
                  </p>
                  <p className="mt-2 font-data text-[40px] leading-none font-bold tabular">
                    {c.split}
                  </p>
                  <p className="mt-2 font-data text-[11px] tracking-[0.03em] text-ink-3 uppercase">
                    majority — minority
                  </p>
                </div>
                <div className="px-5 py-4">
                  <p className="font-data text-[11px] leading-relaxed text-ink-2">
                    FLIP MARGIN = {c.flip_margin ?? "—"}. Definition: the number of
                    justices whose switch to the other side changes the winner
                    outright. A tie is not a flip.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ——— THE BASELINE'S CALL — the dumb rule, in full view ——— */}
        <section className="border-b border-rule bg-paper-2">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <p className="micro">[003] The baseline&apos;s call — B4, the dumb rule</p>
            <h2 className="mt-4 max-w-3xl font-display text-[clamp(1.4rem,2.6vw,2rem)] font-bold uppercase leading-[1.05] tracking-[-0.01em]">
              What the dumbest honest rule expected — and what the room did.
            </h2>
            <p className="mt-4 max-w-[75ch] text-[14px] leading-[1.7] text-ink-2">
              <strong>What it saw before predicting:</strong> nothing about
              this case. Each justice&apos;s ideological lean was measured on
              the training split alone (OT2015–OT2019 votes, direction coded);
              the rule then predicts every vote by that lean, and the case by
              the majority of those predictions. This case&apos;s own votes
              never informed it — that is what makes it a baseline rather
              than a leak.
            </p>
            <p className="mt-3 max-w-[75ch] text-[14px] leading-[1.7] text-ink-2">
              <strong>The honest part:</strong> the language-model conditions
              of the protocol (zero-shot, persona, context) are not trained
              yet — milestone M3 is pending, and this page refuses to invent
              their calls. Until they exist, the dumb rule is the only
              prediction on the record, and it is shown with its misses, not
              its hits.
            </p>
            {c.baseline_call != null && (
              <div className="mt-4 max-w-[75ch] border-l-4 border-signal px-4 py-2.5 font-data text-[11.5px] leading-relaxed tracking-[0.02em] text-ink-2">
                THE CALL, IN FULL VIEW: the per-justice ideology baseline
                called this case{" "}
                <strong className="uppercase">{c.baseline_call}</strong>
                {c.direction
                  ? ` — the recorded direction is ${c.direction}, so the rule ${
                      c.baseline_correct ? "got it right" : "missed it"
                    }`
                  : " — the record carries no coded direction here, so no verdict on the call is offered"}
                . Across the whole test split, this rule sits at{" "}
                {b4 ? `${(b4.accuracy * 100).toFixed(1)}%` : "—"} (vote level)
                — the number any trained model has to beat, honestly.
              </div>
            )}
            <div className="mt-7 border-t border-rule">
              {BENCH_ORDER.filter((s) => s in c.votes).map((s) => {
                const lean = rs?.justice_lean?.[s] ?? null;
                const share = lean?.conservative_share ?? null;
                const voteDir = c.vote_dirs?.[s] ?? null;
                const called = lean?.modal ?? null;
                const right =
                  called != null && voteDir != null ? called === voteDir : null;
                return (
                  <div
                    key={s}
                    className="grid grid-cols-1 gap-x-6 gap-y-2 border-b border-hairline py-3.5 sm:grid-cols-[130px_1fr_150px_110px] sm:items-center"
                  >
                    <p className="text-[14px] font-bold">{labels[s] ?? s}</p>
                    <div className="relative h-[14px] w-full border border-rule bg-paper">
                      {share != null && (
                        <div
                          className={`absolute inset-y-0 left-0 ${voteDir === "conservative" ? "bg-ink" : "bg-signal"}`}
                          style={{ width: `${Math.round(share * 100)}%` }}
                        />
                      )}
                      <div className="absolute inset-y-0 left-1/2 w-px bg-ink-3" />
                    </div>
                    <p className="font-data text-[12px] font-semibold tabular">
                      {share != null
                        ? `lean C ${(share * 100).toFixed(0)}%`
                        : "no train profile"}
                    </p>
                    <p
                      className={`font-data text-[10.5px] font-bold tracking-[0.06em] uppercase sm:justify-self-end ${
                        right == null
                          ? "text-ink-3"
                          : right
                            ? "text-ink-2"
                            : "text-signal-deep"
                      }`}
                      title="The lean is measured on the training split only (OT2015-2019); the recorded vote direction is what actually happened."
                    >
                      {right == null
                        ? voteDir ?? "—"
                        : right
                          ? "called it"
                          : "missed it"}
                    </p>
                  </div>
                );
              })}
            </div>
            <p className="mt-5 max-w-[75ch] font-data text-[11px] leading-relaxed tracking-[0.02em] text-ink-3">
              METHODOLOGY IN ONE LINE: per-justice modal direction on the
              training split (SCDB 2025_01 vote directions, OT2015–OT2019,
              justices with at least 20 train votes); the case call is the
              majority of those modal votes. Bars: the justice&apos;s
              conservative share of train votes — black when the recorded
              vote was conservative, red when liberal; the tick marks 50%.
              Justices seated after 2019 carry no train profile by
              construction — a fact, rendered as missing, never estimated.
              Full specification and limitations: the research article.
            </p>
            <Link
              href="/paper"
              className="mt-5 inline-block border border-ink px-4 py-2.5 font-data text-[11px] font-semibold tracking-[0.08em] uppercase hover:bg-ink hover:text-white"
            >
              Read the research article →
            </Link>
          </div>
        </section>
      </main>

      <footer className="bg-ink text-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-5 font-data text-[10.5px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
          <span>LEGALLY SUBJECTIVE — AN OPEN STANDARD. NO ONE OWNS IT.</span>
          <span className="text-white/60">
            SOURCE: SCDB 2025_01 + COURTLISTENER · CASE {c.docket} · FROZEN CORPUS V1
          </span>
          <Link href="/cases" className="text-white/60 hover:text-white">
            THE RECORD →
          </Link>
        </div>
      </footer>
    </div>
  );
}
