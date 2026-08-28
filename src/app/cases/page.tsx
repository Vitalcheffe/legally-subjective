import type { Metadata } from "next";
import Link from "next/link";
import { Chrome } from "@/components/ls/chrome";
import { CaseSearch, type SlimCase } from "@/components/ls/case-search";
import { getSystemState } from "@/lib/system-state";
import { getCases, getResearchState } from "@/lib/research";

/* ————————————————————————————————————————————————
   THE RECORD — every decided case, searchable.

   Function: let anyone find the case that concerns them
   and open it — the votes, the split, the counterfactual,
   and the state of the machine. Result: the wheel's
   numbers resolve to inspectable documents, case by
   case.
   ———————————————————————————————————————————————— */

export const metadata: Metadata = {
  title: "The Record — every decided case, searchable · Legally Subjective",
  description:
    "All 569 decided cases of the frozen corpus (OT2015–2023): votes of the bench, the split, how many doors would have flipped it, and the direction on the record.",
};

export default async function CasesPage() {
  const [sys, all, rs] = await Promise.all([
    getSystemState(),
    getCases(),
    getResearchState(),
  ]);

  const cases: SlimCase[] = (all?.cases ?? [])
    .slice()
    .sort((a, b) => (b.term ?? "").localeCompare(a.term ?? "") || b.docket.localeCompare(a.docket))
    .map((c) => ({
      docket: c.docket,
      name: c.name,
      term: c.term,
      issueArea: c.issue_area,
      split: c.split,
      flip: c.flip_margin,
      unanimous: c.unanimous,
      winner: c.winning_party,
      petitionerWon: c.petitioner_won,
      hay: `${c.name} ${c.docket} ${c.issue_area} ${c.term}`.toLowerCase(),
    }));

  const oneDoor = cases.filter((c) => c.flip === 1).length;
  const nVotes = rs?.corpus.n_votes ?? null;
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
        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14 lg:py-14">
            <p className="micro">[{all?.record_id ?? "—"}] · The record</p>
            <h1 className="mt-5 max-w-5xl font-display text-[clamp(2rem,4.5vw,3.6rem)] font-bold uppercase leading-[1.0] tracking-[-0.02em]">
              Every case. Every vote. On the record.
            </h1>
            <p className="mt-5 max-w-[70ch] text-[15px] leading-[1.75] text-ink-2">
              These are the {cases.length} decided cases behind every number on
              this site — the frozen corpus of the Supreme Court of the United
              States{sys.windowLabel ? ` (${sys.windowLabel})` : ""}. Open one
              and you will see how the bench voted, how close the case came to
              going the other way, and which direction the decision took.
            </p>
            <div className="mt-7 grid grid-cols-2 gap-px border border-rule bg-rule sm:grid-cols-4">
              {[
                ["Decided cases", String(cases.length), "frozen corpus · OT2015–2023"],
                ["Recorded votes", nVotes != null ? nVotes.toLocaleString("en-US") : "—", "thirteen justices · nine terms"],
                [
                  "One door from flipping",
                  String(oneDoor),
                  "cases decided by the single vote that moved",
                ],
                [
                  "The number to beat",
                  b4 ? `${(b4.accuracy * 100).toFixed(1)}%` : "—",
                  `per-justice ideology baseline · ${rs?.state_id ?? "M2"}`,
                ],
              ].map(([k, v, note]) => (
                <div key={k} className="bg-paper px-5 py-5">
                  <p className="font-data text-[10px] tracking-[0.08em] text-ink-3 uppercase">
                    {k}
                  </p>
                  <p className="mt-2 font-data text-[24px] leading-none font-semibold tabular">
                    {v}
                  </p>
                  <p className="mt-2 text-[11px] leading-snug text-ink-3">{note}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <CaseSearch cases={cases} />
          </div>
        </section>

        <section>
          <div className="mx-auto max-w-[1600px] px-6 py-10 sm:px-10 lg:px-14">
            <p className="micro">[002] Where the numbers come from</p>
            <div className="mt-5 flex flex-wrap gap-x-10 gap-y-3 font-data text-[12px] font-medium tracking-[0.05em] uppercase">
              <Link href="/paper" className="text-signal-deep hover:underline">
                The research article →
              </Link>
              <Link href="/standard" className="text-ink-2 hover:text-ink">
                The measurement standard →
              </Link>
              <Link href="/court/scotus" className="text-ink-2 hover:text-ink">
                The bench →
              </Link>
            </div>
            <p className="mt-6 max-w-[70ch] text-[13px] leading-relaxed text-ink-3">
              &ldquo;One door&rdquo; marks the cases a single justice&rsquo;s
              switch would have flipped outright — the closest thing this
              record has to a heartbeat. &ldquo;The number to beat&rdquo; is
              the M2 per-justice ideology baseline: any trained model must
              beat it honestly, on the sealed test, or say it could not. Both
              are documented, with every caveat, in the research article.
            </p>
          </div>
        </section>
      </main>

      <footer className="bg-ink text-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-5 font-data text-[10.5px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
          <span>LEGALLY SUBJECTIVE — AN OPEN STANDARD. NO ONE OWNS IT.</span>
          <span className="text-white/60">
            SOURCES: SCDB · COURTLISTENER{sys.windowLabel ? ` · ${sys.windowLabel}` : ""}
          </span>
          <Link href="/" className="text-white/60 hover:text-white">
            THE WHEEL →
          </Link>
        </div>
      </footer>
    </div>
  );
}
