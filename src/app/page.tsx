import { Chrome } from "@/components/ls/chrome";
import { Interrogation } from "@/components/ls/interrogation";
import { getSystemState } from "@/lib/system-state";

/* ————————————————————————————————————————————————
   THE QUESTIONS — the front page for humans.

   Not routes. Not APIs. The questions a person asks when
   a judge is about to decide something that matters to
   them — each answered by a figure from the public record,
   each opening a door that measures.

   Every number below is real and traceable:
   - 56.95% / 95.24%  data/productions/agreement.json (pairs)
   - 25.5% / 4.8%     data/dockets/LS-J-009, LS-J-007 (temperament)
   - 50.1 / 23.4      data/dockets/LS-J-001, LS-J-009 (precedent)
   ———————————————————————————————————————————————— */

interface Question {
  n: string;
  q: string;
  a: React.ReactNode;
  door: string;
  href: string;
}

export default async function Home() {
  const sys = await getSystemState();
  const live = sys.state === "WARM";

  const QUESTIONS: Question[] = [
    {
      n: "01",
      q: "Does it matter which judge you draw?",
      a: (
        <>
          On the cases they decided together, Clarence Thomas and Ketanji Brown
          Jackson voted the same way{" "}
          <strong className="text-signal-deep">56.95%</strong> of the time —
          they split on nearly half of them. John Roberts and Brett Kavanaugh:
          <strong className="text-signal-deep"> 95.24%</strong>. Same court.
          Same cases. Same law. The judge behind the door is part of the
          outcome.
        </>
      ),
      door: "Meet the nine",
      href: "/court/scotus",
    },
    {
      n: "02",
      q: "Do feelings play a role in justice?",
      a: (
        <>
          Nobody can read a judge&apos;s heart. Behavior can be counted. How
          often a justice stands alone in dissent runs from{" "}
          <strong className="text-signal-deep">4.8%</strong> to{" "}
          <strong className="text-signal-deep">25.5%</strong> across this
          bench — a five-fold gap. How heavily they anchor each opinion in
          precedent runs from{" "}
          <strong className="text-signal-deep">23</strong> to{" "}
          <strong className="text-signal-deep">50</strong> cited authorities.
          Different judges are, measurably, different deciders.
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
          Pick any two of the nine. The counterfactual is computed, not
          asserted: where they diverge, by how much, and with what
          uncertainty — all from votes they actually cast on cases they both
          heard. The most divided pair on this Court splits on{" "}
          <strong className="text-signal-deep">43 of every 100</strong>{" "}
          common votes.
        </>
      ),
      door: "Compare two judges",
      href: "/compare/kavanaugh/jackson",
    },
    {
      n: "04",
      q: "Why trust a number about a judge?",
      a: (
        <>
          Because you don&apos;t have to. Every figure on this site carries its
          own receipt: the exact public filing it came from, the date it was
          read, and a fingerprint anyone can re-verify at home. If a number
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
      <Chrome
        justices={sys.judgesScored}
        cases={sys.casesDecided}
        windowLabel={sys.windowLabel}
        state={sys.state}
      />

      <main className="flex-1">
        <Interrogation justices={sys.judgesScored} cases={sys.casesDecided} />

        {/* ——— THE QUESTIONS ——— */}
        <section id="questions" className="scroll-mt-16 border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-16 sm:px-10 lg:px-14 lg:py-20">
            <p className="micro">[003] The questions</p>
            <h2 className="mt-5 font-display text-[clamp(1.9rem,3.6vw,2.9rem)] font-bold uppercase leading-[1.02] tracking-[-0.02em]">
              Ask what a ruling hangs on.
              <br />
              <span className="text-ink-2">The record answers.</span>
            </h2>
            <p className="mt-5 max-w-[62ch] font-display text-[15px] leading-relaxed text-ink-2">
              Four questions people actually ask about judges. No opinions in
              the answers — only counts from{" "}
              {sys.casesDecided} decided cases read off the public record
              {sys.windowLabel ? ` (${sys.windowLabel})` : ""}, Supreme Court
              of the United States.
            </p>

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
              nine public officials publicly did — so that &ldquo;it depends on
              the judge&rdquo; stops being a saying and becomes a number.
            </p>
          </div>
        </section>
      </main>

      {/* ——— FOOTER — the frame of the page ——— */}
      <footer className="bg-ink text-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-5 font-data text-[10.5px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
          <span>LEGALLY SUBJECTIVE — AN OPEN STANDARD. NO ONE OWNS IT.</span>
          <span className="text-white/60">
            SOURCES: COURTLISTENER · OYEZ{sys.windowLabel ? ` · ${sys.windowLabel}` : ""}
          </span>
          <span className="text-white/60">
            EVERY NUMBER TRACES TO A PUBLIC FILING.
          </span>
        </div>
      </footer>
    </div>
  );
}
