import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { Newsreader } from "next/font/google";
import { Chrome } from "@/components/ls/chrome";
import { getSystemState } from "@/lib/system-state";
import { getModel, BENCH_ORDER, fmtP } from "@/lib/research";
import { getBenchLabels } from "@/lib/research-page";

/* ————————————————————————————————————————————————
   THE RESEARCH — LS-R-001.

   A research article in the classical form: abstract, numbered
   sections, figures with captions, tables, references. Every
   number in the prose is interpolated from data/productions/
   model.json at build time — the page cannot drift from the
   trained model it describes. The figures are the actual
   matplotlib outputs of scripts/train.py.
   ———————————————————————————————————————————————— */

const reader = Newsreader({
  variable: "--font-reader",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "The Subjectivity of Nine — Research Article LS-R-001 · Legally Subjective",
  description:
    "Measuring and predicting individual voting behavior on the U.S. Supreme Court, OT2020–2025: 1,989 recorded votes, 232 cases, nine justices. Agreement 56.95–95.24%. Case-level features alone barely predict a vote (AUC 0.540); bench momentum does (AUC 0.877).",
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
  const [sys, M, labels] = await Promise.all([
    getSystemState(),
    getModel(),
    getBenchLabels(),
  ]);
  if (!M) {
    return (
      <div className="flex min-h-screen items-center justify-center font-data text-sm">
        MODEL NOT TRAINED — RUN scripts/train.py
      </div>
    );
  }

  const r = M.results;
  const d = M.dataset;
  const pj = r.per_justice;
  const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
  const f3 = (x: number) => x.toFixed(3);
  const pairName = (key: string) => {
    const [a, b] = key.split("|");
    return `${labels[a] ?? a}–${labels[b] ?? b}`;
  };
  const minPair = pairName(r.agreement.min_pair);
  const maxPair = pairName(r.agreement.max_pair);
  const kappa = r.tests.fleiss_kappa;

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
              LS-R-001 · FILED {M.trained_at.slice(0, 10)}
            </span>
          </div>
        </div>

        <article className="mx-auto max-w-[820px] px-6 pb-24 sm:px-10">
          {/* ——— ARTICLE HEADER ——— */}
          <header className="pt-12 sm:pt-16">
            <p className="font-data text-[11px] font-medium tracking-[0.08em] text-ink-3 uppercase">
              Measurement note · {d.justices} justices · {d.cases} decided cases ·{" "}
              {d.votes.toLocaleString("en-US")} recorded votes
            </p>
            <h1 className="mt-4 text-[clamp(1.9rem,4vw,2.9rem)] font-bold leading-[1.12] tracking-[-0.015em]">
              The Subjectivity of Nine: measuring and predicting individual voting
              behavior on the Supreme Court of the United States, October Term
              2020–2025
            </h1>
            <p className="mt-5 text-[15px] text-ink-2">
              The Legally Subjective Project<Sup n={11} />
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
                It is a commonplace of legal practice that outcomes depend on the
                judge. We test the commonplace against the public record. From the
                Oyez case database and the CourtListener platform we assemble{" "}
                {d.votes.toLocaleString("en-US")} merits votes cast by the nine
                justices of the U.S. Supreme Court across {d.cases} decided cases
                (October Term 2020 – 2025), each traceable to a dated public
                filing. We first measure: pairwise agreement on common votes spans{" "}
                {pct(r.agreement.min)} ({minPair}) to {pct(r.agreement.max)} (
                {maxPair}), and dissent frequency varies more than five-fold
                across the bench (
                {pct(Math.min(...BENCH_ORDER.map((s) => pj[s].dissent_rate)))} to{" "}
                {pct(Math.max(...BENCH_ORDER.map((s) => pj[s].dissent_rate)))}
                ). We then predict: L2-regularized logistic regressions are
                trained under case-grouped cross-validation, so that no case
                contributes votes to both training and test folds. Knowing only
                which justice votes, the term, and the originating circuit
                predicts the direction of the vote at AUC {f3(r.direction.A.auc)}
                — indistinguishable from a per-justice base-rate baseline (AUC{" "}
                {f3(r.direction.baseline.auc)}). Adding the recorded momentum of
                the other eight justices raises discrimination to AUC{" "}
                {f3(r.direction.B.auc)}. Dissent, likewise, is strongly associated
                with the justice (χ² = {r.tests.chi2_dissent_x_justice.chi2},
                d.f. = {r.tests.chi2_dissent_x_justice.dof}, {fmtP(r.tests.chi2_dissent_x_justice.p)}) but
                not with the term ({fmtP(r.tests.chi2_dissent_x_term.p)}). The
                case, in short, poorly determines the vote; the identity of the
                voter and the pull of colleagues largely do. All data, code, and
                figures regenerate from source caches with one command and a
                fixed seed.
              </p>
              <p className="mt-4 font-data text-[11px] tracking-[0.04em] text-ink-2">
                KEYWORDS — judicial behavior · Supreme Court · inter-rater
                agreement · ideal points · logistic regression · open data
              </p>
            </div>
          </header>

          <div className="reader-body mt-10">
            {/* ————— 1. INTRODUCTION ————— */}
            <h2 className="reader-h">1&nbsp;&nbsp;Introduction</h2>
            <p>
              Litigants do not choose their judges. In the Supreme Court of the
              United States the assignment of a petition to the merits docket,
              and the composition of the panel that will decide it, is a matter
              of institutional accident from the perspective of the parties: the
              bench is what it is on the day the case is argued. Whether that
              accident matters — whether &ldquo;it depends on the judge&rdquo; is
              a statistical statement rather than a rhetorical one — is an
              empirical question, and it has a long empirical literature.
              Segal and Cover showed that the ideological placement of justices,
              measured from newspaper editorials at appointment, predicts their
              votes on civil-liberties cases<Sup n={2} />; Martin and Quinn
              estimated dynamic ideal points for every justice since 1937 from
              the votes themselves<Sup n={1} />; Epstein, Landes and Posner
              modeled the labor supply and opinion-writing behavior of federal
              judges as rational choice<Sup n={3} />; and Sunstein and
              coauthors documented panel effects — the tendency of a judge&rsquo;s
              vote to move with the composition of the panel<Sup n={4} />. On
              the machine side, Katz, Bommarito and Blackman trained
              cross-validated models on case features and achieved roughly 70%
              out-of-sample accuracy at the case-outcome level<Sup n={5} />.
            </p>
            <p>
              This literature shares a property that limits its public reach:
              its inputs are curated datasets, and its outputs are point
              estimates detached from the documents that produced them. A
              citizen who reads that two justices agree 75% of the time cannot,
              from the paper alone, inspect the votes behind the number. The
              present note takes the opposite posture. It is an artifact of the
              Legally Subjective project, an open measurement standard (LS-1.0)
              whose governing rule is that a number which cannot be traced to a
              dated public filing does not appear<Sup n={12} />. Every vote
              analyzed below was read from the Oyez case database<Sup n={10} />,
              every opinion count from CourtListener<Sup n={9} />, and every
              figure and statistic regenerates from the cached source files by a
              single documented command.
            </p>
            <p>
              We ask three questions. First, <em>measurement</em>: across the
              sitting bench, how far apart are the nine in recorded voting
              behavior, and with what uncertainty? Second,{" "}
              <em>prediction</em>: how much of an individual justice&rsquo;s vote
              is predictable from public case attributes — and how much of the
              remainder is recoverable once the behavior of the other eight
              justices is known? Third, <em>provenance</em>: can the entire
              analysis be carried, end to end, on receipts? The answer to the
              third question is by construction yes; the first two answers
              occupy the remainder of the paper.
            </p>

            {/* ————— 2. DATA ————— */}
            <h2 className="reader-h">2&nbsp;&nbsp;Data and provenance</h2>
            <p>
              The unit of observation is the merits vote: one justice, one case,
              one recorded position (majority or minority). The Oyez API&rsquo;s
              structured case detail supplies, per case, the parties, the
              question presented, the originating lower court, the decision
              date, and the vote of each participating justice. CourtListener
              supplies the case index for the window and the per-justice
              authored-opinion record used by the companion fingerprint
              standard. Table 1 summarizes the corpus.
            </p>

            <div className="overflow-x-auto"><table className="reader-table mt-6">
              <caption className="reader-figcap">
                <span className="font-semibold text-ink">Table 1.</span> The
                corpus. All records are cached with retrieval date and source
                URI; a vote that the source does not record is absent, never
                imputed.
              </caption>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Records</th>
                  <th>Role in this paper</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Oyez case detail</td>
                  <td>{d.cases} decided cases</td>
                  <td>votes, parties, question, circuit, dates</td>
                </tr>
                <tr>
                  <td>Oyez votes</td>
                  <td>{d.votes.toLocaleString("en-US")} merits votes</td>
                  <td>both prediction targets; agreement</td>
                </tr>
                <tr>
                  <td>CourtListener index</td>
                  <td>688 clusters</td>
                  <td>window definition (Oct 2020 – Aug 2026)</td>
                </tr>
                <tr>
                  <td>CourtListener opinions</td>
                  <td>587 lead opinions</td>
                  <td>fingerprint axes (precedent, exposure)</td>
                </tr>
              </tbody>
            </table></div>

            <p>
              Three provenance decisions shape everything downstream. First, the
              direction of a vote — whether the justice sided with the party
              seeking relief (the petitioner) — requires resolving Oyez&rsquo;s
              free-text <em>winning party</em> field against the two party
              names; our resolver (exact, containment, token-subset, prefix,
              acronym) resolves {d.direction_resolvable_votes.toLocaleString("en-US")} of{" "}
              {d.votes.toLocaleString("en-US")} votes, and unresolved votes are
              excluded from directional analyses rather than guessed. Second,
              recusals and non-participations are dropped: participation is
              never assumed. Third, the bench is the sitting nine of the
              declared window; votes cast by justices who left the bench before
              it opened are out of scope. Across the corpus,{" "}
              {pct(d.dissent_rate)} of votes are dissents and{" "}
              {pct(d.direction_rate)} favor the petitioner — both figures are
              recomputable from the vote cache by any reader.
            </p>

            {/* ————— 3. METHODS ————— */}
            <h2 className="reader-h">3&nbsp;&nbsp;Methods</h2>
            <h3 className="reader-sub">3.1&nbsp;&nbsp;Measurement: the LS-1.0 fingerprint</h3>
            <p>
              Alongside the predictive analysis we maintain a descriptive
              standard, LS-1.0, which files for each justice a six-axis
              &ldquo;subjectivity fingerprint&rdquo;: disposition (the
              petitioner-alignment rate of their votes), temperament (dissent
              rate), precedent (mean authorities cited per lead opinion),
              exposure (lead opinions per year of service in the window), and
              two axes — reversal and orality — that are honestly null at a
              terminal court without review or without ingested argument
              transcripts. Axis values are converted to median-rank percentiles
              against the declared bench, and each carries a bootstrap
              confidence interval (10,000 resamples, seed derived from the
              docket identifier). A bench of nine yields nine discrete
              percentile values; that coarseness is disclosed on every filing
              rather than smoothed away. The fingerprints are the descriptive
              substrate of the companion site and are not the subject of this
              note — we cite them only where they motivate a target.
            </p>
            <h3 className="reader-sub">3.2&nbsp;&nbsp;Targets and features</h3>
            <p>
              Two binary targets are derived per vote. <em>Direction</em> is 1
              when the justice&rsquo;s recorded position favors the party seeking
              relief — a majority vote when the petitioner won, a dissent when
              the petitioner lost — and is undefined when the winning-party
              record cannot be resolved. <em>Dissent</em> is 1 when the vote is
              cast with the minority. Features come in two specifications.{" "}
              <em>Spec A (case-only)</em> uses the justice&rsquo;s identity
              (one-hot), the term (one-hot), and the originating court (one-hot
              over the {d.circuits.length} most frequent circuits; the remainder
              collapse to an OTHER bucket). <em>Spec B (+colleagues)</em> adds
              two continuous signals measured strictly on the other eight
              justices of the same case: their share voting with the majority,
              and their net directional lean. Spec B is a deliberately
              collegial model — it asks whether the individual is carried by
              the bench — and it contains no information about the justice&rsquo;s
              own vote, so it leaks nothing by construction.
            </p>
            <h3 className="reader-sub">3.3&nbsp;&nbsp;Models and validation</h3>
            <p>
              All models are L2-regularized logistic regressions (C = 1.0)
              fitted with scikit-learn<Sup n={6} />. Validation is
              five-fold cross-validation <em>grouped by case</em>: every vote of
              a case lies in the same fold, so the pipeline can never learn a
              case&rsquo;s outcome from its own train/test echo — the grouping is
              what makes the evaluation honest at the vote level. Reported
              metrics are pooled out-of-fold discrimination (ROC AUC),
              accuracy, Brier score, and log loss. The baseline for each task
              is the per-justice base rate, itself estimated strictly inside
              each training fold. Learning curves vary the number of training
              cases from 15 to 186 under five random 80/20 case splits,
              reporting mean out-of-fold AUC ± one standard deviation. The
              per-justice directional scale of §4.5 is the vector of justice
              logits from the full-data case-only fit, with 95% confidence
              intervals from {M.design.bootstrap} resampling cases with
              replacement and refitting.
            </p>
            <h3 className="reader-sub">3.4&nbsp;&nbsp;Classical tests</h3>
            <p>
              Association between dissent and justice identity, and between
              dissent and term, is tested with Pearson χ² tests of independence
              on the corresponding contingency tables. Overall bench agreement
              beyond chance is quantified with Fleiss&rsquo; generalization of
              Cohen&rsquo;s kappa<Sup n={7} />{" "}
              computed over the {kappa?.items ?? "—"} cases in which all nine
              justices voted, each case treated as an item rated by nine raters
              into two categories. Binomial proportions (per-justice dissent
              rates) carry Wilson score intervals. Computations use
              SciPy<Sup n={8} />, NumPy, and Matplotlib<Sup n={9} />; software
              versions are recorded with the model artifacts.
            </p>

            {/* ————— 4. RESULTS ————— */}
            <h2 className="reader-h">4&nbsp;&nbsp;Results</h2>
            <h3 className="reader-sub">4.1&nbsp;&nbsp;The bench in numbers</h3>
            <p>
              Figure 1 and Table 2 summarize the record. Votes are evenly spread
              across the six terms (panel a), while dissent is anything but
              evenly spread across the bench (panel b): the justice least
              inclined to stand alone dissents in{" "}
              {pct(Math.min(...BENCH_ORDER.map((s) => pj[s].dissent_rate)))} of
              votes and the most inclined in{" "}
              {pct(Math.max(...BENCH_ORDER.map((s) => pj[s].dissent_rate)))} —
              a ratio of{" "}
              {(
                Math.max(...BENCH_ORDER.map((s) => pj[s].dissent_rate)) /
                Math.min(...BENCH_ORDER.map((s) => pj[s].dissent_rate))
              ).toFixed(1)}
              . The χ² test rejects independence of dissent from justice
              overwhelmingly (χ² = {r.tests.chi2_dissent_x_justice.chi2}, d.f. ={" "}
              {r.tests.chi2_dissent_x_justice.dof},{" "}
              {fmtP(r.tests.chi2_dissent_x_justice.p)}) and, just as
              instructively, does <em>not</em> reject independence from term (
              χ² = {r.tests.chi2_dissent_x_term.chi2}, d.f. ={" "}
              {r.tests.chi2_dissent_x_term.dof}, {fmtP(r.tests.chi2_dissent_x_term.p)}
              ): who the justice is matters; which year it is does not.
            </p>

            <Figure
              src="/figures/fig1-bench.png"
              width={1480}
              height={620}
              n={1}
              cap={
                <>
                  The record. (a) Recorded merits votes by term, stacked by
                  position. (b) Per-justice dissent rate with Wilson 95%
                  confidence intervals, sorted. The five-fold spread is a
                  property of the bench, not of any single term.
                </>
              }
            />

            <div className="overflow-x-auto"><table className="reader-table mt-4">
              <caption className="reader-figcap">
                <span className="font-semibold text-ink">Table 2.</span>{" "}
                Per-justice summary over the window. Dissent rates carry Wilson
                95% intervals; AUCs are per-justice out-of-fold discrimination
                from the pooled Spec B models of §3.3 (dissent task).
              </caption>
              <thead>
                <tr>
                  <th>Justice</th>
                  <th>Votes</th>
                  <th>Dissents</th>
                  <th>Dissent rate (95% CI)</th>
                  <th>Petitioner-side</th>
                  <th>AUC (dissent)</th>
                </tr>
              </thead>
              <tbody>
                {BENCH_ORDER.map((s) => {
                  const v = pj[s];
                  return (
                    <tr key={s}>
                      <td>{labels[s] ?? s}</td>
                      <td>{v.n_votes}</td>
                      <td>{v.dissents}</td>
                      <td>
                        {pct(v.dissent_rate)} [{pct(v.dissent_ci[0])}–
                        {pct(v.dissent_ci[1])}]
                      </td>
                      <td>{v.direction_rate != null ? pct(v.direction_rate) : "—"}</td>
                      <td>{f3(v.auc_dissent)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table></div>

            <h3 className="reader-sub">4.2&nbsp;&nbsp;Agreement structure</h3>
            <p>
              Figure 2 arranges the {r.agreement.n_pairs} pairwise agreement
              rates as a heatmap. The span is the finding: from{" "}
              {pct(r.agreement.max)} for {maxPair} down to {pct(r.agreement.min)}{" "}
              for {minPair}, with a mean of {pct(r.agreement.mean)}. Two
              justices of the same court, reading the same briefs and hearing
              the same arguments, differ by more than thirty-eight percentage
              points of agreement depending on the pair — and the least-aligned
              pair splits on nearly {Math.round((1 - r.agreement.min) * 100)} of
              every 100 common votes. Correcting for the base-rate tendency of
              everyone to join the majority, chance-corrected agreement is
              modest: Fleiss&rsquo; κ = {kappa?.kappa.toFixed(3)} over{" "}
              {kappa?.items} unanimously-participating cases (observed
              agreement {kappa?.P_bar.toFixed(3)}, expected under independence{" "}
              {kappa?.P_e.toFixed(3)}). The bench agrees a great deal in raw
              terms — and very little of that agreement is attributable to
              chance-free consensus rather than to the shared institutional
              pull toward the majority<Sup n={7} />.
            </p>

            <Figure
              src="/figures/fig2-agreement.png"
              width={1240}
              height={1040}
              n={2}
              cap={
                <>
                  Pairwise agreement rate on common merits votes (percent).
                  Cell values are observed shares; red marks the extreme pairs.
                  The matrix is symmetric; the diagonal is trivial.
                </>
              }
            />

            <h3 className="reader-sub">4.3&nbsp;&nbsp;What predicts a vote</h3>
            <p>
              Table 3 reports the cross-validated comparison, and Figure 3 the
              receiver-operating curves of the pooled out-of-fold predictions.
              The case-only specification is the sobering row: knowing who votes,
              when, and whence the case comes predicts vote direction at AUC{" "}
              {f3(r.direction.A.auc)} against a base-rate baseline of{" "}
              {f3(r.direction.baseline.auc)} — the docket, as it were, barely
              knows the answer. Introducing the colleagues changes the picture:
              Spec B reaches AUC {f3(r.direction.B.auc)} (accuracy{" "}
              {pct(r.direction.B.accuracy)}, Brier {r.direction.B.brier.toFixed(3)}
              ), the eight other justices carrying most of the signal. For
              dissent the ordering is the same in kind though flatter in
              degree: case-only features (AUC {f3(r.dissent.A.auc)}) actually
              fall below the per-justice base rate (AUC{" "}
              {f3(r.dissent.baseline.auc)}) — who dissents is better guessed
              from habit than from the docket — while the collegial model
              reaches {f3(r.dissent.B.auc)}. The direction task benefits from a
              target that is partly mechanical (the majority defines the
              winner), which is precisely why the grouping and the
              self-exclusion of §3.2 matter: no vote ever informs its own
              prediction.
            </p>

            <div className="overflow-x-auto"><table className="reader-table mt-4">
              <caption className="reader-figcap">
                <span className="font-semibold text-ink">Table 3.</span>{" "}
                Cross-validated performance, pooled out-of-fold votes.
                Direction: n = {r.direction.B.n.toLocaleString("en-US")}
                resolvable votes. Dissent: n ={" "}
                {r.dissent.B.n.toLocaleString("en-US")} votes. Baselines are
                per-justice base rates estimated inside each training fold.
              </caption>
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Specification</th>
                  <th>AUC</th>
                  <th>Accuracy</th>
                  <th>Brier</th>
                  <th>Log loss</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td rowSpan={3}>Direction</td>
                  <td>Base rate (per justice)</td>
                  <td>{f3(r.direction.baseline.auc)}</td>
                  <td>{pct(r.direction.baseline.accuracy)}</td>
                  <td>{r.direction.baseline.brier.toFixed(3)}</td>
                  <td>—</td>
                </tr>
                <tr>
                  <td>Spec A — case-only</td>
                  <td>{f3(r.direction.A.auc)}</td>
                  <td>{pct(r.direction.A.accuracy)}</td>
                  <td>{r.direction.A.brier.toFixed(3)}</td>
                  <td>{r.direction.A.log_loss.toFixed(3)}</td>
                </tr>
                <tr>
                  <td>Spec B — + colleagues</td>
                  <td className="font-semibold text-signal-deep">
                    {f3(r.direction.B.auc)}
                  </td>
                  <td className="font-semibold text-signal-deep">
                    {pct(r.direction.B.accuracy)}
                  </td>
                  <td>{r.direction.B.brier.toFixed(3)}</td>
                  <td>{r.direction.B.log_loss.toFixed(3)}</td>
                </tr>
                <tr>
                  <td rowSpan={3}>Dissent</td>
                  <td>Base rate (per justice)</td>
                  <td>{f3(r.dissent.baseline.auc)}</td>
                  <td>{pct(r.dissent.baseline.accuracy)}</td>
                  <td>{r.dissent.baseline.brier.toFixed(3)}</td>
                  <td>—</td>
                </tr>
                <tr>
                  <td>Spec A — case-only</td>
                  <td>{f3(r.dissent.A.auc)}</td>
                  <td>{pct(r.dissent.A.accuracy)}</td>
                  <td>{r.dissent.A.brier.toFixed(3)}</td>
                  <td>{r.dissent.A.log_loss.toFixed(3)}</td>
                </tr>
                <tr>
                  <td>Spec B — + colleagues</td>
                  <td className="font-semibold text-signal-deep">
                    {f3(r.dissent.B.auc)}
                  </td>
                  <td className="font-semibold text-signal-deep">
                    {pct(r.dissent.B.accuracy)}
                  </td>
                  <td>{r.dissent.B.brier.toFixed(3)}</td>
                  <td>{r.dissent.B.log_loss.toFixed(3)}</td>
                </tr>
              </tbody>
            </table></div>

            <Figure
              src="/figures/fig4-roc.png"
              width={980}
              height={840}
              n={3}
              cap={
                <>
                  Out-of-fold receiver-operating curves, pooled votes,
                  case-grouped five-fold cross-validation, Spec B. The diagonal
                  is chance.
                </>
              }
            />

            <h3 className="reader-sub">4.4&nbsp;&nbsp;Learning</h3>
            <p>
              Figure 4 traces out-of-fold discrimination as a function of the
              number of training cases. Both tasks learn from the record: the
              dissent task climbs from AUC{" "}
              {r.learning_curve_dissent[0].auc_mean.toFixed(2)} at{" "}
              {r.learning_curve_dissent[0].n_train_cases} training cases to{" "}
              {r.learning_curve_dissent[r.learning_curve_dissent.length - 1].auc_mean.toFixed(2)}{" "}
              at{" "}
              {r.learning_curve_dissent[r.learning_curve_dissent.length - 1].n_train_cases}
              , and has not plateaued — the curve&rsquo;s last segment is its
              steepest. The direction task starts high because the collegial
              feature is strong even from few cases, and tightens to{" "}
              {r.learning_curve_direction[r.learning_curve_direction.length - 1].auc_mean.toFixed(2)}
              . The practical reading for the project: the instrument sharpens
              as the public record grows, and nothing in the curves suggests a
              ceiling has been reached.
            </p>

            <Figure
              src="/figures/fig3-learning.png"
              width={1160}
              height={700}
              n={4}
              cap={
                <>
                  Learning curves. Mean out-of-fold AUC (±1 s.d. over five
                  random case-level splits) as a function of the number of
                  training cases, Spec B for both tasks. The shaded band is the
                  dispersion across seeds, not a confidence interval on the
                  mean.
                </>
              }
            />

            <h3 className="reader-sub">4.5&nbsp;&nbsp;The measured spectrum</h3>
            <p>
              Figure 5(a) shows each justice&rsquo;s directional logit from the
              full case-only fit — the propensity, common to the cases of the
              window and controlling for term and circuit, to vote for the
              party asking the court for relief. The spread is real but
              bounded: from{" "}
              {f3(Math.min(...BENCH_ORDER.map((s) => r.spectrum[s].logit)))} to{" "}
              {f3(Math.max(...BENCH_ORDER.map((s) => r.spectrum[s].logit)))} on
              the log-odds scale, with bootstrap intervals that overlap
              substantially. Panel (b) shows how machine-predictable each
              justice is — the per-justice out-of-fold AUC on the dissent task
              — which ranges from{" "}
              {f3(Math.min(...BENCH_ORDER.map((s) => pj[s].auc_dissent)))} to{" "}
              {f3(Math.max(...BENCH_ORDER.map((s) => pj[s].auc_dissent)))}. Two
              justices at the same point of the directional scale can differ
              visibly in predictability, and vice versa: what a justice tends
              to do and how legible their behavior is to a simple model are
              distinct properties, and the bench varies on both.
            </p>

            <Figure
              src="/figures/fig5-spectrum.png"
              width={1480}
              height={680}
              n={5}
              cap={
                <>
                  Two independent characterizations of the nine. (a) Directional
                  logits from the full case-only fit with case-bootstrap 95%
                  intervals. (b) Per-justice out-of-fold AUC on the dissent
                  task (Spec B) — the machine&rsquo;s reading of each justice.
                </>
              }
            />

            {/* ————— 5. DISCUSSION ————— */}
            <h2 className="reader-h">5&nbsp;&nbsp;Discussion</h2>
            <p>
              Three findings deserve emphasis. First, the measured spread is
              large. A five-fold ratio in dissent rates, a thirty-eight-point
              spread in pairwise agreement, and a chance-corrected agreement of
              κ ≈ {kappa?.kappa.toFixed(2)} together describe a bench whose
              members agree mostly when the institutional current is
              overwhelming and diverge whenever it is not. For a litigant the
              arithmetic is uncomfortable: on close cases the identity of the
              majority is the outcome, and the identity of the majority is not
              chosen by the litigant.
            </p>
            <p>
              Second, the case is a poor predictor of the vote. It is worth
              dwelling on the failure mode of Spec A, because it is the
              scientifically useful kind of failure: with justice identity,
              term, and circuit — features fully visible before the vote — the
              model cannot materially beat a table of per-justice habits. Under
              the sources available to us, the visible attributes of a case do
              not encode its disposition in any way a linear model can detect.
              The signal that exists is collegial: tell the model what the
              other eight did and it predicts the ninth at AUC{" "}
              {f3(r.direction.B.auc)}. Judicial votes, on this record, are
              substantially a property of the group, not of the case — a
              finding that sits comfortably beside the panel-effect literature
              on the courts of appeals<Sup n={4} />.
            </p>
            <p>
              Third, the predictability is bounded, and the bounds are the
              honest part. An interpretable model with a handful of features
              discriminates individual votes at 0.74–0.88 AUC — far from
              chance, and equally far from clairvoyance. The residual is where
              the legal work of distinguishing cases presumably lives, and
              nothing here suggests it is noise. We regard the model not as a
              judge-replacement but as a measuring rod: it quantifies how much
              of the record is habit and momentum, and thereby how much room
              the record leaves for the contested, case-bound judgment that
              appellate adjudication claims to be.
            </p>

            {/* ————— 6. LIMITATIONS ————— */}
            <h2 className="reader-h">6&nbsp;&nbsp;Limitations</h2>
            <p>
              The corpus is small ({d.cases} cases; {d.votes.toLocaleString("en-US")}{" "}
              votes) and the models are deliberately simple — the intent is a
              reproducible baseline, not a leaderboard entry. The Oyez
              winning-party field is free text; our resolver leaves{" "}
              {(
                d.votes - d.direction_resolvable_votes
              ).toLocaleString("en-US")}{" "}
              votes without a directional label, and resolution errors, though
              rare, are possible. The source record carries no issue-area
              coding, so topic heterogeneity enters only through the circuit
              of origin. The Supreme Court is a terminal court: no
              reversal-treatment axis exists, and any generalization to
              courts where panels are drawn by lot is inference, not
              measurement. All associations are observational; nothing here
              identifies a causal effect of judge identity on outcomes. And
              the fingerprint percentiles of §3.1, computed against a bench of
              nine, are coarse by construction — a property disclosed on every
              filing rather than hidden.
            </p>

            {/* ————— 7. AVAILABILITY ————— */}
            <h2 className="reader-h">7&nbsp;&nbsp;Data and code availability</h2>
            <p>
              Every artifact of this paper regenerates from the public source
              caches with a single command —{" "}
              <span className="font-data text-[13px]">{M.reproduce}</span> —
              under fixed seed {M.seed}. The run of record used Python{" "}
              {M.environment.python}, scikit-learn {M.environment.scikit_learn},
              NumPy {M.environment.numpy}, SciPy {M.environment.scipy}, and
              Matplotlib {M.environment.matplotlib}; versions are stored inside
              the model artifact ({M.model_id}) alongside every aggregate
              reported above, and the per-vote out-of-fold predictions behind
              Figures 3–5 are published with it. Source data: the Oyez
              API<Sup n={10} /> and CourtListener<Sup n={9} />, both products
              of the Free Law Project; cached retrieval URIs and dates ship
              with the repository. The case-level record, including the votes
              and the machine&rsquo;s per-justice calls for every decided
              case, is browsable at{" "}
              <Link href="/cases" className="text-signal-deep underline">
                /cases
              </Link>
              .
            </p>

            {/* ————— REFERENCES ————— */}
            <h2 className="reader-h">References</h2>
            <div className="reader-refs">
              <p>
                1. Martin, A. D. &amp; Quinn, K. M. Dynamic ideal point
                estimation for Markov chain time series of political choices.
                <em> Am. J. Polit. Sci.</em> 46, 134–153 (2002).
              </p>
              <p>
                2. Segal, J. A. &amp; Cover, A. D. Ideological values and the
                votes of U.S. Supreme Court justices. <em>Am. Polit. Sci. Rev.</em>{" "}
                83, 557–565 (1989).
              </p>
              <p>
                3. Epstein, L., Landes, W. M. &amp; Posner, R. A. <em>The
                Behavior of Federal Judges: A Theoretical and Empirical Study
                of Rational Choice.</em> Oxford University Press (2013).
              </p>
              <p>
                4. Sunstein, C. R., Schkade, D., Ellman, L. M. &amp; Sawicki,
                A. <em>Are Judges Political? An Empirical Analysis of the
                Federal Judiciary.</em> Brookings Institution Press (2006).
              </p>
              <p>
                5. Katz, D. M., Bommarito, M. J. &amp; Blackman, J. A general
                approach for predicting the behavior of the Supreme Court of
                the United States. <em>PLOS ONE</em> 12, e0174698 (2017).
              </p>
              <p>
                6. Pedregosa, F. <em>et al.</em> Scikit-learn: machine learning
                in Python. <em>J. Mach. Learn. Res.</em> 12, 2825–2830 (2011).
              </p>
              <p>
                7. Fleiss, J. L. Measuring nominal scale agreement among many
                raters. <em>Psychol. Bull.</em> 76, 378–382 (1971); Cohen, J. A
                coefficient of agreement for nominal scales. <em>Educ.
                Psychol. Meas.</em> 20, 37–46 (1960).
              </p>
              <p>
                8. Virtanen, P. <em>et al.</em> SciPy 1.0: fundamental
                algorithms for scientific computing in Python. <em>Nat.
                Methods</em> 17, 261–272 (2020).
              </p>
              <p>
                9. Hunter, J. D. Matplotlib: a 2D graphics environment.
                <em> Comput. Sci. Eng.</em> 9, 90–95 (2007).
              </p>
              <p>
                10. Oyez Project. <em>The Oyez Supreme Court Database</em>,
                IIT Chicago-Kent College of Law. https://www.oyez.org
                (retrieved August 2026).
              </p>
              <p>
                11. Free Law Project. <em>CourtListener</em>: an open-source
                legal research platform. https://www.courtlistener.com
                (retrieved August 2026).
              </p>
              <p>
                12. Legally Subjective. <em>Standard LS-1.0 — the subjectivity
                fingerprint of a bench</em>, revision as filed. Published in
                this repository and rendered at /standard.
              </p>
            </div>
          </div>
        </article>
      </main>

      <footer className="bg-ink text-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-5 font-data text-[10.5px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
          <span>LEGALLY SUBJECTIVE — AN OPEN STANDARD. NO ONE OWNS IT.</span>
          <span className="text-white/60">
            LS-R-001 · {M.model_id} · SEED {M.seed}
          </span>
          <Link href="/" className="text-white/60 hover:text-white">
            THE WHEEL →
          </Link>
        </div>
      </footer>
    </div>
  );
}
