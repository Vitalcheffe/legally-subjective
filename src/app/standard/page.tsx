import { readFile } from "fs/promises";
import path from "path";
import ReactMarkdown from "react-markdown";
import { Chrome } from "@/components/ls/chrome";
import { Glyph } from "@/components/ls/glyph";
import { getSystemState } from "@/lib/system-state";

/**
 * /standard — THE NORM.
 * This URL has one function: render the actual LS-1.0 standard from the
 * repository, with its build hash. The page IS the file. If the file is
 * missing, the page says so — it substitutes nothing.
 */
export default async function StandardPage() {
  const sys = await getSystemState();

  let md: string;
  try {
    md = await readFile(
      path.join(process.cwd(), "standards", "LS-1.0.md"),
      "utf8",
    );
  } catch {
    md =
      "# LS-1.0\n\nThe standard file is not present on this system. Nothing is substituted for it.";
  }

  return (
    <div className="flex min-h-screen flex-col bg-paper font-display text-ink">
      <Chrome
        build={sys.build}
        judgesScored={sys.judgesScored}
        docketsIngested={sys.docketsIngested}
        engineCycles={sys.engineCycles}
        engineLast={sys.engineLast}
        state={sys.state}
        route="/standard"
      />

      <main className="flex-1">
        {/* ——— HEADER ——— */}
        <section className="border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-14 sm:px-10 lg:px-14 lg:py-16">
            <div className="flex flex-wrap items-baseline justify-between gap-4">
              <p className="micro">[001] The norm</p>
              <a
                href="/"
                className="font-data text-[11px] font-medium tracking-[0.08em] text-ink-2 uppercase hover:text-signal-deep"
              >
                ← Back to the interrogation
              </a>
            </div>
            <h1 className="mt-5 font-display text-[clamp(2.2rem,5vw,4.2rem)] font-bold uppercase leading-[0.98] tracking-[-0.025em]">
              The standard,
              <br />
              <span className="text-ink-2">not our word.</span>
            </h1>
            <p className="tabular mt-6 max-w-2xl font-data text-[11px] leading-[1.9] tracking-[0.05em] text-ink-2">
              RENDERED FROM standards/LS-1.0.md IN THIS REPOSITORY · SHA-256{" "}
              {sys.build} · THE PAGE IS THE FILE — IF THE FILE CHANGES, THE
              PAGE CHANGES. NOTHING IS TRANSCRIBED BY HAND.
            </p>
          </div>
        </section>

        {/* ——— SPEC + RAIL ——— */}
        <section className="border-b border-rule">
          <div className="mx-auto grid max-w-[1600px] gap-14 px-6 py-14 sm:px-10 lg:grid-cols-[minmax(0,1fr)_300px] lg:px-14 lg:py-16">
            <article className="spec max-w-[72ch]">
              <ReactMarkdown
                components={{
                  h1: () => null,
                  h2: ({ children }) => (
                    <h2 className="mt-14 border-b border-rule pb-3 font-display text-[22px] font-bold uppercase tracking-[-0.01em] first:mt-0">
                      {children}
                    </h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="mt-9 font-display text-[16px] font-semibold uppercase tracking-[0.01em]">
                      {children}
                    </h3>
                  ),
                  p: ({ children }) => (
                    <p className="mt-5 text-[14.5px] leading-[1.75] text-ink">
                      {children}
                    </p>
                  ),
                  strong: ({ children }) => (
                    <strong className="font-semibold">{children}</strong>
                  ),
                  ol: ({ children }) => (
                    <ol className="mt-5 list-decimal space-y-2.5 pl-6 text-[14.5px] leading-[1.75] marker:font-data marker:text-ink-2">
                      {children}
                    </ol>
                  ),
                  ul: ({ children }) => (
                    <ul className="mt-5 list-disc space-y-2.5 pl-6 text-[14.5px] leading-[1.75] marker:font-data marker:text-ink-2">
                      {children}
                    </ul>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className="mt-7 border-l-2 border-signal pl-5 text-[15px] leading-[1.7] text-ink-2 italic">
                      {children}
                    </blockquote>
                  ),
                  table: ({ children }) => (
                    <div className="mt-7 overflow-x-auto border border-hairline">
                      <table className="tabular w-full border-collapse font-data text-[11px] leading-[1.6]">
                        {children}
                      </table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className="border-b border-rule px-3 py-2.5 text-left font-semibold tracking-[0.06em] uppercase">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="border-b border-hairline px-3 py-2.5 align-top text-ink-2">
                      {children}
                    </td>
                  ),
                  code: ({ children }) => (
                    <code className="border border-hairline bg-paper-2 px-1.5 py-0.5 font-data text-[12px]">
                      {children}
                    </code>
                  ),
                  pre: ({ children }) => (
                    <pre className="mt-7 overflow-x-auto border border-hairline bg-paper-2 p-5 font-data text-[11px] leading-[1.7]">
                      {children}
                    </pre>
                  ),
                  hr: () => <hr className="mt-12 border-hairline" />,
                }}
              >
                {md}
              </ReactMarkdown>
            </article>

            {/* ——— THE RAIL — specimen + provenance ——— */}
            <aside className="lg:sticky lg:top-20 lg:self-start">
              <p className="micro">[002] Specimen — LS-1.0 §5</p>
              <div className="mt-5 border border-rule p-8">
                <Glyph
                  docketId="LS-SPECIMEN"
                  axes={null}
                  className="mx-auto h-auto w-full max-w-[200px]"
                  strokeWidth={2.5}
                />
                <p className="micro mt-6 normal-case leading-relaxed tracking-[0.04em] text-ink-3">
                  The format itself. No subject, no data, nothing invented —
                  dashed contour at full radius, awaiting the first FILED
                  docket.
                </p>
              </div>
              <dl className="mt-6 space-y-3 border-t border-rule pt-6 font-data text-[10.5px] leading-[1.7] tracking-[0.05em]">
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-3 uppercase">Version</dt>
                  <dd className="text-right">1.0 — DRAFT</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-3 uppercase">Status</dt>
                  <dd className="text-right">FROZEN ON FIRST FILED DOCKET</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-3 uppercase">Build</dt>
                  <dd className="tabular text-right">{sys.build}</dd>
                </div>
                <div>
                  <dt className="text-ink-3 uppercase">SHA-256</dt>
                  <dd className="tabular mt-1 border border-hairline bg-paper-2 p-3 text-[9.5px] leading-[1.8] break-all">
                    {sys.standardHash || "NOT FOUND"}
                  </dd>
                </div>
              </dl>
            </aside>
          </div>
        </section>
      </main>

      <footer className="bg-ink text-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 py-5 font-data text-[10.5px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
          <span>LEGALLY SUBJECTIVE — AN OPEN STANDARD. NO ONE OWNS IT.</span>
          <span className="text-white/60">
            LS-1.0 · UI-1.0 EXHIBIT · AGPL-3.0
          </span>
          <span className="text-white/60">
            THE INTERFACE IS INDIFFERENT. THAT IS WHY IT IS ADMISSIBLE.
          </span>
        </div>
      </footer>
    </div>
  );
}
