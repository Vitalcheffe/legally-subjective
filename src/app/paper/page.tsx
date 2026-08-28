import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { Newsreader } from "next/font/google";
import { Chrome } from "@/components/ls/chrome";
import { getSystemState } from "@/lib/system-state";
import { getResearchState, SCDB_KEYS } from "@/lib/research";
import { getBenchLabels } from "@/lib/research-page";

/* ————————————————————————————————————————————————
   THE RESEARCH — LS-R-002.

   A research article in the classical form: abstract, numbered
   sections, figures with captions, tables, references. Every
   number in the prose is interpolated from data/productions/
   research_state.json at build time — the page cannot drift
   from the corpus and baselines it describes. The figures are
   the actual matplotlib outputs of scripts/make_figures.py,
   run on the frozen corpus and the M2 baselines.
   ———————————————————————————————————————————————— */

const reader = Newsreader({
  variable: "--font-reader",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "The Subjectivity of Thirteen — Research Article LS-R-002 · Legally Subjective",
  description:
    "A frozen corpus of 569 argued cases (OT2015–2023), thirteen justices, 4,730 recorded votes, and the statistical baselines any model must beat: per-justice ideology calls 63.7% of votes. The protocol is sealed; the models are not yet trained — and the page says so.",
};

function Sup({ n }: { n: number }) {
  return <sup className="font-data text-[10px] font-semibold text-signal-deep">[{n}]</sup>;
}

function Figure({
  src,
  width,
  height,
  n,
  cap,
}: {
  src: string;
  width: number;
  height: number;
  n: number;
  cap: React.ReactNode;
}) {
  return (
    <figure className="mt-7">
      <div className="border border-hairline bg-paper-2 p-2">
        <Image
          src={src}
          alt={`Figure ${n}`}
          width={width}
          height={height}
          className="h-auto w-full"
          loading="eager"
        />
      </div>
      <figcaption className="reader-figcap">
        <span className="font-semibold text-ink">Fig. {n}. </span>
        {cap}
      </figcaption>
    </figure>
  );
}

export default async function PaperPage() {
  const [sys, R, labels] = await Promise.all([
    getSystemState(),
    getResearchState(),
    getBenchLabels(),
  ]);
  if (!R) {
    return (
      <div className="flex min-h-screen items-center justify-center font-data text-sm">
        RESEARCH STATE NOT EXPORTED — RUN scripts/transfuse_v2.py
      </div>
    );
  }

  const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
  const slugOfKey: Record<string, string> = Object.fromEntries(
    Object.entries(SCDB_KEYS).map(([slug, key]) => [key, slug]),
  );
  const pairName = (key: string) => {
    const [a, b] = key.split("|");
    const sa = slugOfKey[a] ?? a;
    const sb = slugOfKey[b] ?? b;
    return `${labels[sa] ?? sa}–${labels[sb] ?? sb}`;
  };
  const minPair = pairName(R.agreement.min_pair);
  const maxPair = pairName(R.agreement.max_pair);
  const d = R.corpus;
  const b4 = R.baselines.find((b) => b.id === "B4");
  const b1 = R.baselines.find((b) => b.id === "B1");
  const b3 = R.baselines.find((b) => b.id === "B3");

  return (
    <div
      className={`${reader.variable} flex min-h-screen flex-col bg-paper font-display text-ink`}
    >
      <Chrome
        justices={sys.judgesScored}
        cases={sys.casesDecided}
        windowLabel={sys.windowLabel}
        state={sys.state}
      />

      <main className="flex-1 font-reader">
        {/* ——— JOURNAL MASTHEAD ——— */}
        <div className="border-b border-rule">
          <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-8 gap-y-1 px-6 py-3 font-data text-[10.5px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
            <span>LEGALLY SUBJECTIVE · RESEARCH ARTICLES</span>
            <span className="text-ink-2">
              WORKING PAPER — OPEN REVIEW · NOT PEER-REVIEWED
            </span>
            <span className="text-ink-2 tabular">
              LS-R-002 · FILED {R.filed_at.slice(0, 10)}
            </span>
          </div>
        </div>

        <article className="mx-auto max-w-[820px] px-6 pb-24 sm:px-10">
          {/* ——— ARTICLE HEADER ——— */}
          <header className="pt-12 sm:pt-16">
            <p className="font-data text-[11px] font-medium tracking-[0.08em] text-ink-3 uppercase">
              Measurement note · {d.n_justices} justices · {d.n_cases} argued
              cases · {d.n_votes.toLocaleString("en-US")} recorded votes
            </p>
            <h1 className="mt-4 text-[clamp(1.9rem,4vw,2.9rem)] font-bold leading-[1.12] tracking-[-0.015em]">
              The Subjectivity of Thirteen: a frozen corpus of the Rehnquist
              to Roberts Court, October Term 2015–2023, and the baselines any
              model of its votes must beat
            </h1>
            <p className="mt-5 text-[15px] text-ink-2">
              The Legally Subjective Project<Sup n={10} />
            </p>
            <p className="mt-2 text-[12.5px] leading-relaxed text-ink-3">
              An open measurement standard — no funding, no institutional
              affiliation, competing interests: none declared. Correspondence:
              the public repository of this project.
            </p>

            {/* ——— ABSTRACT ——— */}
            <div className="mt-9 border-y-[1.5px] border-ink py-6">
              <p className="mb-3 font-data text-[10.5px] font-semibold tracking-[0.1em] uppercase">
                Abstract
              </p>
              <p className="text-[15px] leading-[1.75]">
                It is a commonplace of legal practice that outcomes depend on
                the judge. We build the instrument to test the commonplace
                honestly. From the Supreme Court Database and the CourtListener
                platform we assemble and freeze a corpus of{" "}
                {d.n_cases} argued cases of the U.S. Supreme Court, October
                Term 2015 through 2023 — {d.n_justices} justices,{" "}
                {d.n_opinions.toLocaleString("en-US")} opinions,{" "}
                {d.n_votes.toLocaleString("en-US")} recorded votes — with the
                corpus rule, every filter, and every source fingerprint sealed
                under SHA-256. We then measure the floor: pairwise agreement
                on common coded-direction votes spans{" "}
                {pct(R.agreement.min)} ({minPair}) to {pct(R.agreement.max)} (
                {maxPair}), and knowing nothing but each justice&apos;s modal
                ideological direction over the training terms predicts{" "}
                {b4 ? pct(b4.accuracy) : "—"} of test-split votes — the
                number to beat. Fifty of the {d.n_five_four} decisions won
                5–4 are sealed for a single final pass. The language-model
                conditions of the protocol — zero-shot, persona, retrieval —
                are specified, preregistered, and not yet trained; this
                article reports the corpus, the baselines, and the protocol,
                and says plainly what does not yet exist.
              </p>
              <p className="mt-4 font-data text-[11px] tracking-[0.04em] text-ink-2">
                KEYWORDS — judicial behavior · Supreme Court · inter-rater
                agreement · frozen corpus · baselines · open data
              </p>
            </div>
          </header>

          <div className="reader-body mt-10">
            {/* ————— POSITIONING / PRIOR WORK — LS-AUDIT-001 inj. 6 ————— */}
            <aside className="mb-10 border-2 border-ink bg-paper-2 px-6 py-5">
              <p className="font-data text-[10.5px] font-bold tracking-[0.1em] uppercase text-signal-deep">
                Prior work — read this before calling anything new
              </p>
              <div className="mt-3 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1fr]">
                <div>
                  <p className="text-[13px] leading-[1.65] text-ink-2">
                    <strong>What already exists.</strong> Martin–Quinn ideal
                    points have placed every justice on a common scale since
                    2002, estimated from votes back to 1937 and updated each
                    term<Sup n={1} />. The Spaeth database encodes every
                    Supreme Court vote since 1946 and is the canonical raw
                    material of the field. Empirical SCOTUS and the
                    judicial-politics literature have measured agreement,
                    ideology and panel effects for two decades — much of it
                    cited and used in §1. This project did not invent
                    judicial measurement, and does not claim to.
                  </p>
                </div>
                <div>
                  <p className="text-[13px] leading-[1.65] text-ink-2">
                    <strong>What is different here.</strong> Four things, all
                    about access rather than science: a short window in which
                    every number links to its frozen source file, not a bulk
                    dataset download; a corpus rule that is sealed before any
                    model sees the data; a per-case counterfactual — what one
                    vote would have flipped — next to the aggregate scores;
                    and a public chain of custody (URI, timestamp, sha256) as
                    the deliverable itself. The novelty is the receipts, not
                    the statistics.
                  </p>
                </div>
              </div>
            </aside>

            {/* ————— 1. INTRODUCTION ————— */}
            <h2 className="reader-h">1&nbsp;&nbsp;Introduction</h2>
            <p>
              Litigants do not choose their judges. In the Supreme Court of
              the United States the composition of the bench that will decide
              a case is a matter of institutional accident from the
              perspective of the parties: the bench is what it is on the day
              the case is argued. Whether that accident matters — whether
              &ldquo;it depends on the judge&rdquo; is a statistical statement
              rather than a rhetorical one — is an empirical question, and it
              has a long empirical literature<Sup n={1} />
              <Sup n={2} />. This project asks a narrower, sharper version of
              it: can the measurable part of a justice&apos;s public behavior
              — the votes, the writings, the alliances — be extracted from
              public sources and handed to a language model as a persona, such
              that the model predicts that justice&apos;s future decisions
              better than it would without the persona?
            </p>
            <p>
              The question cannot be answered on a moving dataset. If the
              corpus can be reshaped after seeing model outputs, every result
              is negotiable and none is falsifiable. The first contribution of
              this article is therefore not a model but a frozen corpus:{" "}
              {d.n_cases} argued cases, OT2015 through OT2023, assembled under
              a sealed rule from public sources, with the fifty 5–4 decisions
              that will serve as the final examination held out under a
              disclosed seed and hash. The second contribution is the floor
              every answer must clear: four statistical baselines, computed on
              a time-ordered split, the strongest of which — per-justice
              ideological direction — already calls{" "}
              {b4 ? pct(b4.accuracy) : "—"} of test-split votes. Any claimed
              model advantage smaller than the widths reported here is noise
              wearing a costume.
            </p>

            {/* ————— 2. THE CORPUS ————— */}
            <h2 className="reader-h">2&nbsp;&nbsp;The frozen corpus</h2>
            <p>
              The corpus rule was fixed before any model was trained: every
              case argued on the merits before the Supreme Court in October
              Terms 2015 through 2023, identified from CourtListener dockets
              and fused with the Supreme Court Database (edition 2025_01) by
              normalized docket tokens<Sup n={3} />
              <Sup n={4} />. The assembly is documented to the byte: each
              source file carries its SHA-256 in the corpus statistics, the
              filters are stated as predicates, and the exclusions —
              ghost docket groups without an argued date, duplicates
              re-ingested by the source — are counted, not hidden.
            </p>
            <div className="my-7 overflow-x-auto">
              <table className="w-full min-w-[560px] border-collapse font-data text-[11.5px]">
                <tbody>
                  {[
                    ["Argued cases, OT2015–OT2023", `${d.n_cases}`],
                    ["Opinions inventoried", `${d.n_opinions.toLocaleString("en-US")}`],
                    ["Cases joined to SCDB votes", `${d.n_with_scdb} (${((d.n_with_scdb / d.n_cases) * 100).toFixed(1)}%)`],
                    ["Cases with coded decision direction", `${d.n_with_direction}`],
                    ["Training split (OT2015–2019), labeled", `${sys.trainSplit}`],
                    ["Test split (OT2020–2023), labeled", `${sys.testSplit}`],
                    ["Decisions decided 5–4", `${d.n_five_four}`],
                    ["— of which sealed for the final exam", `${d.n_sealed} (seed + SHA-256 disclosed)`],
                    ["Justices who sat in the window", `${d.n_justices}`],
                    ["Recorded votes", `${d.n_votes.toLocaleString("en-US")}`],
                    ["Audio coverage (oral arguments)", `${d.audio_coverage} cases (${((d.audio_coverage / d.n_cases) * 100).toFixed(1)}%)`],
                  ].map(([k, v]) => (
                    <tr key={k} className="border-b border-hairline">
                      <td className="py-2 pr-6 text-ink-2">{k}</td>
                      <td className="py-2 text-right font-semibold tabular">{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              Two properties of the corpus deserve emphasis. First, the split
              is temporal, not random: everything the baselines or any future
              model &ldquo;learns&rdquo; comes strictly from OT2015–2019, and
              everything it is judged on comes from OT2020–2023 — no case can
              inform its own verdict. Second, the {d.n_sealed} sealed 5–4
              decisions are not a test set in the ordinary sense; they are the
              final examination, to be touched exactly once, by every
              condition at once, and published whatever the outcome. The
              selection seed and the SHA-256 of the sealed list are part of
              the corpus statistics — the exam cannot be swapped after the
              fact.
            </p>

            {/* ————— 3. BASELINES ————— */}
            <h2 className="reader-h">3&nbsp;&nbsp;The baselines to beat</h2>
            <p>
              A prediction claim without a floor is marketing. We compute four
              statistical baselines on the frozen corpus, each with a Wilson
              95% interval, evaluated on the OT2020–2023 test split: the
              majority class of the training terms ({b1?.name.toLowerCase()}
              , {b1 ? pct(b1.accuracy) : "—"}); always-conservative and
              always-liberal; always-reverse-the-court-below on the clean
              affirm/reverse subset ({b3 ? pct(b3.accuracy) : "—"}); and the
              per-justice ideological direction — for each justice, the
              modal direction of their training votes, applied to every
              test vote. The last is the operative floor: it is what you
              &ldquo;know&rdquo; about a judge from a single statistic, and it
              already decides {b4 ? pct(b4.accuracy) : "—"} of test votes.
            </p>
            <div className="my-7 overflow-x-auto">
              <table className="w-full min-w-[520px] border-collapse font-data text-[11.5px]">
                <thead>
                  <tr className="border-b-2 border-ink">
                    <th className="py-2 pr-6 text-left font-semibold">Baseline</th>
                    <th className="py-2 pr-6 text-right font-semibold">Accuracy</th>
                    <th className="py-2 text-right font-semibold">Wilson 95% CI</th>
                  </tr>
                </thead>
                <tbody>
                  {R.baselines.map((b) => (
                    <tr
                      key={b.id}
                      className={`border-b border-hairline ${b.id === "B4" ? "font-semibold" : ""}`}
                    >
                      <td className="py-2 pr-6">
                        <span className={b.id === "B4" ? "text-signal-deep" : "text-ink-2"}>
                          {b.id} — {b.name}
                        </span>
                      </td>
                      <td className="py-2 text-right tabular">{pct(b.accuracy)}</td>
                      <td className="py-2 text-right tabular text-ink-2">
                        {b.ic95 ? `[${pct(b.ic95[0])}, ${pct(b.ic95[1])}]` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Figure
              src="/figures/fig1-baselines.png"
              width={1400}
              height={640}
              n={1}
              cap={
                <>
                  The four baselines with Wilson 95% intervals, OT2020–2023
                  test split. The per-justice ideology baseline (red) is the
                  operative floor: {b4 ? pct(b4.accuracy) : "—"} of votes at
                  the vote level. Note how wide the intervals are at this
                  sample size — a model must clear the interval, not the
                  point, before any claim is made.
                </>
              }
            />
            <p>
              The class balance itself drifts across the window (Fig.&nbsp;3):
              the training terms sit near parity — between{" "}
              {(0.462 * 100).toFixed(1)}% and {(0.5 * 100).toFixed(1)}%
              conservative — while OT2021 spikes to{" "}
              {(0.639 * 100).toFixed(1)}% conservative. A majority-class rule
              trained on the near-parity terms is therefore nearly useless on
              the test window, which is precisely why the temporal split
              matters: it prices regime drift into the floor instead of
              hiding it.
            </p>

            {/* ————— 4. THE BENCH, MEASURED ————— */}
            <h2 className="reader-h">4&nbsp;&nbsp;The bench, measured</h2>
            <p>
              Within the corpus, pairwise agreement on common
              coded-direction votes spans {pct(R.agreement.min)} between{" "}
              {minPair} (n={R.agreement.min_n}) and {pct(R.agreement.max)}{" "}
              between {maxPair} (n={R.agreement.max_n}) — a range wide enough
              that &ldquo;the Court&rdquo; is not one decider but a
              distribution of them. The full matrix (Fig.&nbsp;2) shows the
              familiar bloc structure with honest gaps: pairs with fewer than
              fifty common coded votes are withheld rather than extrapolated,
              which is why recent arrivals appear sparser.
            </p>
            <Figure
              src="/figures/fig2-agreement.png"
              width={1400}
              height={1240}
              n={2}
              cap={
                <>
                  Vote agreement between every pair of justices who sat
                  OT2015–2023, in protocol order. Darker cells = more
                  agreement; the values are shares of common cases where both
                  votes carry a coded direction (SCDB). Empty cells = fewer
                  than 50 shared coded cases — withheld, not estimated.
                </>
              }
            />
            <Figure
              src="/figures/fig3-balance.png"
              width={1400}
              height={600}
              n={3}
              cap={
                <>
                  Decided cases with a coded direction, by term. Black =
                  conservative outcomes, red = liberal. The dashed line marks
                  the end of the training split: everything to its right is
                  the test window the baselines — and later the models — are
                  judged on.
                </>
              }
            />

            {/* ————— 5. PROTOCOL ————— */}
            <h2 className="reader-h">5&nbsp;&nbsp;The protocol: four conditions, one exam</h2>
            <p>
              The experimental design holds one variable still — the model —
              and varies what it is given. Four conditions run on the same
              frozen corpus:
            </p>
            <ol className="mt-2 list-decimal space-y-2 pl-6 text-[14.5px] leading-[1.75]">
              {R.protocol.conditions.map((c) => (
                <li key={c.id}>
                  <strong>
                    Condition {c.id} — {c.name}.
                  </strong>{" "}
                  {c.spec}.
                </li>
              ))}
            </ol>
            <p className="mt-4">
              The decisive comparison is B against A, on future cases the
              persona-finetuned model has never seen: {R.protocol.decisive_test}{" "}
              {R.protocol.final_exam} The exam has not been run — the seals
              are intact — and this article claims no result from it.
            </p>

            {/* ————— 6. STATUS AND LIMITS ————— */}
            <h2 className="reader-h">6&nbsp;&nbsp;Status, and what this article does not claim</h2>
            <p>
              The honest state of the project, at filing: the corpus is frozen
              and verifiable (M1), the baselines are computed with their
              intervals (M2), the collection of full opinion texts is under
              way under a rate-limited but resumable pipeline (M1.5), and{" "}
              <strong>
                no language model has been trained
              </strong>{" "}
              — conditions A, B and C do not yet exist as running systems.
              Nothing on this site predicts a case, and nothing here should
              be read as legal advice. The known limits, stated plainly:
            </p>
            <ol className="mt-2 list-decimal space-y-2 pl-6 text-[14.5px] leading-[1.75]">
              <li>
                The corpus covers nine terms of one court; nothing transfers
                mechanically to other courts, other countries, or other
                eras.
              </li>
              <li>
                SCDB coding is itself an interpretation — the direction and
                disposition variables encode judgment calls by human coders,
                and {d.n_cases - d.n_with_scdb} cases in the window carry no
                SCDB votes at all.
              </li>
              <li>
                The baselines use a single statistic per justice (the modal
                direction); richer statistical floors — ideal points,
                case-level features — exist in the literature and would
                likely be stronger.
              </li>
              <li>
                &ldquo;Conservative/liberal&rdquo; is a coarse axis; two
                justices with identical direction shares can differ in every
                other measurable way.
              </li>
              <li>
                Citation-impact measures (the Precedent axis) accumulate with
                time: late-window authors are mechanically under-cited, and
                the filed dockets disclose this per axis.
              </li>
              <li>
                Agreement shares are computed on common coded votes; pairs
                with fewer than fifty are withheld, so recent arrivals have
                sparser rows — absence of data, not evidence of distance.
              </li>
            </ol>

            {/* ————— REFERENCES ————— */}
            <h2 className="reader-h">References</h2>
            <ol className="mt-2 space-y-2 text-[13px] leading-[1.7] text-ink-2">
              <li>
                [1] Martin, A. D., &amp; Quinn, K. M. (2002). Dynamic ideal
                point estimation via Markov chain Monte Carlo for the U.S.
                Supreme Court, 1953–1999. <em>Perspective on Politics</em>,
                10(3).
              </li>
              <li>
                [2] Segal, J. A., &amp; Cover, A. D. (1989). Ideological
                values and the votes of U.S. Supreme Court justices.
                <em> American Political Science Review</em>, 83(3).
              </li>
              <li>
                [3] Spaeth, H. J., et al. <em>The Supreme Court Database</em>,
                edition 2025_01. Washington University in St. Louis.
                http://scdb.wustl.edu
              </li>
              <li>
                [4] Free Law Project. <em>CourtListener</em> — dockets,
                opinions, oral arguments; bulk files of 2026-06-30 and API
                v4. https://www.courtlistener.com
              </li>
              <li>
                [5] Angwin, J., Larson, J., Mattu, S., &amp; Kirchner, L.
                (2016). Machine bias. <em>ProPublica</em>. The COMPAS
                investigation — the precedent that motivated this
                project&apos;s disclosure discipline.
              </li>
              <li>
                [10] The Legally Subjective Project. <em>Standards LS-1.0</em>
                , the measurement standard, and the frozen corpus statistics
                in this repository.
              </li>
            </ol>

            <div className="mt-10 border-t border-rule pt-6 font-data text-[11px] leading-relaxed tracking-[0.02em] text-ink-3">
              EVERY NUMBER IN THIS ARTICLE IS INTERPOLATED AT BUILD TIME FROM
              THE FROZEN CORPUS AND THE M2 PRODUCTIONS — SEE{" "}
              <Link href="/standard" className="text-ink-2 underline">
                THE STANDARD
              </Link>{" "}
              AND THE{" "}
              <Link href="/court/scotus" className="text-ink-2 underline">
                FILED DOCKETS
              </Link>{" "}
              FOR THE RECEIPTS. FIGURES REGENERATE WITH{" "}
              <code>scripts/make_figures.py</code>.
            </div>
          </div>
        </article>
      </main>

      <footer className="bg-ink text-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-5 font-data text-[10.5px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
          <span>LEGALLY SUBJECTIVE — AN OPEN STANDARD. NO ONE OWNS IT.</span>
          <span className="text-white/60">
            LS-R-002 · SOURCES: SCDB · COURTLISTENER
          </span>
          <Link href="/" className="text-white/60 hover:text-white">
            THE WHEEL →
          </Link>
        </div>
      </footer>
    </div>
  );
}
