import { Seal } from "@/components/ls/seal";
import { Glyph } from "@/components/ls/glyph";
import { RotatingLine } from "@/components/ls/rotating-line";
import { Reveal } from "@/components/ls/reveal";

/* ————————————————————————————————————————————————
   The data of the page — all public facts, zero fabrication.
   ———————————————————————————————————————————————— */

const ROTATING_OPTIONS = [
  "be free tonight?",
  "tuck them in tonight?",
  "hear them call you Dad on Sundays?",
  "hold the keys to your house?",
  "make it home for dinner?",
  "be allowed to vote?",
  "recognize your own life?",
];

const LOSSES = [
  {
    loss: "MY FREEDOM",
    court: "CRIMINAL",
    question: "Would you still be free tonight?",
  },
  {
    loss: "MY KIDS",
    court: "FAMILY",
    question: "Would they still call you Dad on Sundays?",
  },
  {
    loss: "MY HOME",
    court: "CIVIL",
    question: "Would you still hold the keys?",
  },
  {
    loss: "MY COUNTRY",
    court: "IMMIGRATION",
    question: "Would you make it home for dinner?",
  },
  {
    loss: "MY WORK",
    court: "COMMERCIAL",
    question: "Would your life's work still be yours?",
  },
  {
    loss: "MY VOTE",
    court: "RIGHTS",
    question: "Would you still be allowed to speak?",
  },
];

/* The Nine — public record. Seating per court protocol: Chief center,
   seniority alternating right/left of the bench. */
const BENCH: Array<{ docket: string; name: string; role: string }> = [
  { docket: "LS-J-008", name: "Amy Coney Barrett", role: "Associate Justice" },
  { docket: "LS-J-006", name: "Neil M. Gorsuch", role: "Associate Justice" },
  { docket: "LS-J-004", name: "Sonia Sotomayor", role: "Associate Justice" },
  { docket: "LS-J-002", name: "Clarence Thomas", role: "Associate Justice" },
  { docket: "LS-J-001", name: "John G. Roberts, Jr.", role: "Chief Justice" },
  { docket: "LS-J-003", name: "Samuel A. Alito, Jr.", role: "Associate Justice" },
  { docket: "LS-J-005", name: "Elena Kagan", role: "Associate Justice" },
  { docket: "LS-J-007", name: "Brett M. Kavanaugh", role: "Associate Justice" },
  { docket: "LS-J-009", name: "Ketanji Brown Jackson", role: "Associate Justice" },
];

const AXES: Array<{ name: string; text: string }> = [
  { name: "Disposition", text: "Where the actor lands on outcome orientation." },
  { name: "Temperament", text: "Collegial conduct on the bench, read from public writings." },
  { name: "Precedent", text: "The age and weight of the authorities they rely on." },
  { name: "Reversal", text: "How long their jurisprudence survives review." },
  { name: "Orality", text: "How they behave while counsel is speaking." },
  { name: "Exposure", text: "The volume of their public footprint." },
];

/* ————————————————————————————————————————————————
   The page
   ———————————————————————————————————————————————— */

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink">
      {/* ——— MASTHEAD ——— */}
      <header className="border-b border-line">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-6 py-5">
          <div className="flex items-center gap-3">
            <Seal size={34} />
            <div className="leading-tight">
              <div className="font-data text-[13px] font-medium tracking-wordmark uppercase">
                Legally Subjective
              </div>
              <div className="font-data text-[10px] tracking-[0.14em] text-ink-2 uppercase">
                In re: Everyone · Docket No. LS-0001
              </div>
            </div>
          </div>
          <div className="hidden items-center gap-6 sm:flex">
            <nav className="font-data text-[11px] tracking-[0.14em] text-ink-2 uppercase">
              <a href="#loss" className="px-2 transition-colors hover:text-seal">
                The Losses
              </a>
              <a href="#bench" className="px-2 transition-colors hover:text-seal">
                The Bench
              </a>
              <a href="#standard" className="px-2 transition-colors hover:text-seal">
                The Standard
              </a>
              <a href="#record" className="px-2 transition-colors hover:text-seal">
                The Record
              </a>
            </nav>
          </div>
          <div className="font-display text-sm italic text-ink-2">Subjectivity, measured.</div>
        </div>
      </header>

      <main className="flex-1">
        {/* ——— HERO — THE QUESTION ——— */}
        <section className="relative border-b border-line">
          {/* Pleading-paper margin: the numbered lines of a court filing */}
          <div
            aria-hidden="true"
            className="absolute top-0 bottom-0 left-10 hidden w-8 flex-col justify-evenly border-r border-line py-16 pl-4 lg:flex"
          >
            {Array.from({ length: 22 }, (_, i) => (
              <span key={i} className="font-data text-[10px] text-ink-2/50 tabular">
                {i + 1}
              </span>
            ))}
          </div>

          <div className="mx-auto flex w-full max-w-5xl flex-col items-start px-6 py-24 sm:py-32 lg:pl-24">
            <Reveal>
              <p className="mb-8 font-data text-[11px] tracking-[0.22em] text-ink-2 uppercase">
                In the matter of: your life
              </p>
            </Reveal>

            <Reveal delayMs={80}>
              <h1 className="font-display max-w-4xl text-[clamp(2.6rem,7vw,5.25rem)] leading-[1.04] font-medium tracking-[-0.01em] text-balance">
                Would you still
                <br />
                <span className="font-normal text-seal italic">
                  <RotatingLine options={ROTATING_OPTIONS} />
                </span>
              </h1>
            </Reveal>

            <Reveal delayMs={200}>
              <p className="mt-8 max-w-xl text-[17px] leading-[1.65] text-ink-2">
                You don&rsquo;t pick your judge. A wheel does — and one door down,
                in the next chamber, sits another one. Same case. Same law.
                A different life. We measure the difference.
              </p>
            </Reveal>

            <Reveal delayMs={320}>
              <div className="mt-10 flex flex-wrap items-center gap-4">
                <a
                  href="#record"
                  className="border border-seal bg-seal px-7 py-3.5 font-data text-[12px] tracking-[0.18em] text-paper uppercase transition-colors hover:bg-seal-deep hover:border-seal-deep"
                >
                  See the record
                </a>
                <a
                  href="#loss"
                  className="border border-ink px-7 py-3.5 font-data text-[12px] tracking-[0.18em] uppercase transition-colors hover:border-seal hover:text-seal"
                >
                  What do you have to lose?
                </a>
              </div>
            </Reveal>

            <Reveal delayMs={420}>
              <p className="mt-12 font-data text-[10px] tracking-[0.16em] text-ink-2/70 uppercase">
                Standard LS-1.0 (draft) · Zero fabrication · AGPL-3.0
              </p>
            </Reveal>
          </div>
        </section>

        {/* ——— THE LOSS PORTAL ——— */}
        <section id="loss" className="border-b border-line">
          <div className="mx-auto w-full max-w-6xl px-6 py-20 sm:py-28">
            <Reveal>
              <div className="mb-12 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="mb-3 font-data text-[11px] tracking-[0.22em] text-ink-2 uppercase">
                    Exhibit A — The stakes
                  </p>
                  <h2 className="font-display text-[clamp(2rem,4.5vw,3.25rem)] leading-tight font-medium">
                    What do you have to lose?
                  </h2>
                </div>
                <p className="max-w-xs text-sm leading-relaxed text-ink-2">
                  Every court touches a different thing you can&rsquo;t replace.
                  Pick yours. That is where the wheel spins.
                </p>
              </div>
            </Reveal>

            <div className="grid grid-cols-1 gap-px border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
              {LOSSES.map((l, i) => (
                <Reveal key={l.loss} delayMs={i * 60}>
                  <a
                    href="#bench"
                    className="group flex h-full flex-col justify-between gap-10 bg-card p-6 transition-colors duration-300 hover:bg-sand/60 sm:p-8"
                  >
                    <div>
                      <div className="mb-6 flex items-center justify-between">
                        <span className="font-data text-[11px] tracking-[0.2em] font-medium uppercase">
                          {l.loss}
                        </span>
                        <span className="font-data text-[10px] tracking-[0.14em] text-ink-2 uppercase">
                          {l.court}
                        </span>
                      </div>
                      <p className="font-display text-xl leading-snug text-ink-2 italic transition-colors duration-300 group-hover:text-seal sm:text-2xl">
                        {l.question}
                      </p>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="stamp inline-block -rotate-3 border border-seal px-2 py-0.5 font-data text-[9px] tracking-[0.2em] text-seal uppercase">
                        In chambers
                      </span>
                      <span className="font-data text-[11px] text-ink-2 transition-transform duration-300 group-hover:translate-x-1">
                        →
                      </span>
                    </div>
                  </a>
                </Reveal>
              ))}
            </div>

            <Reveal delayMs={120}>
              <p className="mt-6 font-data text-[10px] tracking-[0.14em] text-ink-2/70 uppercase">
                &ldquo;In chambers&rdquo; — analysis in progress. Nothing opens until the record is real.
              </p>
            </Reveal>
          </div>
        </section>

        {/* ——— THE BENCH ——— */}
        <section id="bench" className="border-b border-line bg-sand/40">
          <div className="mx-auto w-full max-w-6xl px-6 py-20 sm:py-28">
            <Reveal>
              <div className="mb-14 text-center">
                <p className="mb-3 font-data text-[11px] tracking-[0.22em] text-ink-2 uppercase">
                  Exhibit B — The Nine
                </p>
                <h2 className="font-display text-[clamp(2rem,4.5vw,3.25rem)] leading-tight font-medium">
                  The Court, measured.
                </h2>
                <p className="mx-auto mt-4 max-w-xl text-sm leading-relaxed text-ink-2">
                  Seated per protocol. One fingerprint each, built from their
                  public record. The docket opens when the first real data is filed.
                </p>
              </div>
            </Reveal>

            <div className="grid grid-cols-3 gap-x-4 gap-y-10 sm:gap-x-6 lg:grid-cols-9">
              {BENCH.map((j, i) => (
                <Reveal key={j.docket} delayMs={i * 50}>
                  <a
                    href="#record"
                    className="group flex flex-col items-center text-center"
                    aria-label={`In re ${j.name}, docket ${j.docket} — in chambers`}
                  >
                    <div className="relative w-full max-w-[110px]">
                      <Glyph
                        docketId={j.docket}
                        axes={null}
                        className="h-auto w-full transition-transform duration-500 group-hover:scale-[1.06]"
                        strokeWidth={3}
                      />
                    </div>
                    <p className="mt-4 font-data text-[9px] tracking-[0.12em] text-ink-2 uppercase tabular">
                      {j.docket}
                    </p>
                    <p className="mt-1.5 font-display text-[13px] leading-tight font-medium sm:text-sm">
                      {j.name}
                    </p>
                    <p className="mt-1 font-data text-[8.5px] tracking-[0.1em] text-ink-2/80 uppercase">
                      {j.role === "Chief Justice" ? "Chief" : "Assoc."}
                    </p>
                  </a>
                </Reveal>
              ))}
            </div>

            <Reveal delayMs={150}>
              <div className="mx-auto mt-16 max-w-lg border border-line bg-card px-8 py-6 text-center">
                <p className="font-display text-[15px] leading-relaxed text-ink-2 italic">
                  &ldquo;No public data on this point. We fabricate nothing.&rdquo;
                </p>
                <p className="mt-3 font-data text-[9.5px] tracking-[0.16em] text-ink-2/70 uppercase">
                  Every number will trace to a public source · CourtListener ingestion
                  pending
                </p>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ——— THE STANDARD ——— */}
        <section id="standard" className="border-b border-line">
          <div className="mx-auto grid w-full max-w-6xl gap-14 px-6 py-20 sm:py-28 lg:grid-cols-2 lg:items-center">
            <Reveal>
              <div>
                <p className="mb-3 font-data text-[11px] tracking-[0.22em] text-ink-2 uppercase">
                  Exhibit C — The format
                </p>
                <h2 className="font-display mb-6 text-[clamp(2rem,4.5vw,3.25rem)] leading-tight font-medium">
                  Six axes. One fingerprint.
                </h2>
                <p className="mb-10 max-w-md text-[15px] leading-relaxed text-ink-2">
                  A Subjectivity Fingerprint is not a score. It is a position —
                  where this judge sits among their own bench, on six measured
                  tendencies, each carrying its sample size and its confidence.
                  The doubt is printed on the card.
                </p>
                <dl className="divide-y divide-line border-y border-line">
                  {AXES.map((a) => (
                    <div key={a.name} className="flex items-baseline gap-5 py-3.5">
                      <dt className="w-32 shrink-0 font-data text-[11px] tracking-[0.14em] font-medium uppercase">
                        {a.name}
                      </dt>
                      <dd className="text-sm leading-relaxed text-ink-2">{a.text}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            </Reveal>

            <Reveal delayMs={140}>
              <figure className="relative mx-auto w-full max-w-[420px]">
                <div className="border border-line bg-card p-10">
                  <div className="mb-6 flex items-center justify-between">
                    <span className="font-data text-[9px] tracking-[0.16em] text-ink-2 uppercase tabular">
                      Specimen — LS-1.0
                    </span>
                    <span className="font-data text-[9px] tracking-[0.16em] text-ink-2/70 uppercase">
                      N = 0
                    </span>
                  </div>
                  <Glyph docketId="LS-SPECIMEN" axes={null} className="mx-auto h-auto w-full max-w-[280px]" />
                  <figcaption className="mt-6 text-center">
                    <p className="font-data text-[9.5px] tracking-[0.16em] text-ink-2/80 uppercase">
                      The format itself — no subject, no data, nothing invented
                    </p>
                  </figcaption>
                </div>
                <p className="mt-4 text-center font-data text-[10px] tracking-[0.14em] text-ink-2/70 uppercase">
                  Percentiles against a declared bench · never absolute scores
                </p>
              </figure>
            </Reveal>
          </div>
        </section>

        {/* ——— THE RECORD ——— */}
        <section id="record">
          <div className="mx-auto w-full max-w-4xl px-6 py-20 sm:py-28">
            <Reveal>
              <div className="text-center">
                <p className="mb-3 font-data text-[11px] tracking-[0.22em] text-ink-2 uppercase">
                  Exhibit D — The method
                </p>
                <h2 className="font-display text-[clamp(2rem,4.5vw,3.25rem)] leading-tight font-medium">
                  Not a prediction. A record.
                </h2>
              </div>
            </Reveal>

            <div className="mt-14 grid gap-px border border-line bg-line sm:grid-cols-3">
              {[
                {
                  n: "I",
                  t: "Every number traces",
                  d: "Each value carries its source URI, its sample size, and the date it was computed. Click any figure, arrive at the primary record.",
                },
                {
                  n: "II",
                  t: "Missing is rendered missing",
                  d: "No imputation, no averaging over gaps, no invented judges. When the record is thin, the card looks thin — on purpose.",
                },
                {
                  n: "III",
                  t: "Re-runnable by anyone",
                  d: "The engine is open and deterministic. Clone the repository, replay the build on the same sources, get the same dockets to the bit.",
                },
              ].map((c, i) => (
                <Reveal key={c.n} delayMs={i * 80}>
                  <div className="flex h-full flex-col bg-card p-8">
                    <span className="font-display mb-5 text-2xl text-seal italic">{c.n}.</span>
                    <h3 className="mb-3 font-data text-[12px] tracking-[0.14em] font-medium uppercase">
                      {c.t}
                    </h3>
                    <p className="text-sm leading-relaxed text-ink-2">{c.d}</p>
                  </div>
                </Reveal>
              ))}
            </div>

            <Reveal delayMs={160}>
              <p className="mt-12 text-center font-display text-lg leading-relaxed text-ink-2 italic">
                One door down, a different judge — and your whole life.
                <br />
                The courthouse already knows. Now you can read it.
              </p>
            </Reveal>
          </div>
        </section>
      </main>

      {/* ——— FOOTER ——— */}
      <footer className="mt-auto border-t border-line">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center gap-6 px-6 py-10 sm:flex-row sm:justify-between">
          <div className="flex items-center gap-3">
            <Seal size={26} />
            <div className="leading-tight">
              <div className="font-data text-[11px] tracking-wordmark font-medium uppercase">
                Legally Subjective
              </div>
              <div className="font-data text-[9px] tracking-[0.14em] text-ink-2 uppercase">
                Docket No. LS-0001 · Standard LS-1.0 (draft)
              </div>
            </div>
          </div>
          <p className="font-display text-sm text-ink-2 italic">We fabricate nothing.</p>
          <div className="font-data text-[9px] tracking-[0.14em] text-ink-2/70 uppercase">
            AGPL-3.0 · A public window, read-only
          </div>
        </div>
      </footer>
    </div>
  );
}
