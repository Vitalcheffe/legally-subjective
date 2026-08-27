import { Chrome } from "@/components/ls/chrome";
import { Interrogation } from "@/components/ls/interrogation";
import { getSystemState } from "@/lib/system-state";

/* ————————————————————————————————————————————————
   THE MAP — the URL doctrine of Legally Subjective.
   Seven URLs. Each one computes. Nothing else ships.
   A URL that computes nothing does not exist.
   ———————————————————————————————————————————————— */

const MAP: Array<{
  route: string;
  name: string;
  fn: string;
  state: "LIVE" | "PENDING DATA";
  href?: string;
}> = [
  {
    route: "/",
    name: "The Interrogation",
    fn: "Asks the one question. Converts a visitor into a query. Shows the live state of the record — build, counts, clock.",
    state: "LIVE",
  },
  {
    route: "/judge/{id}",
    name: "The Case File",
    fn: "One judge. Six axes, percentiles against the bench, confidence intervals, N. The docket list that built the score.",
    state: "PENDING DATA",
  },
  {
    route: "/court/{id}",
    name: "The Bench",
    fn: "One court, ranked judge by judge, sortable by axis. The spread per axis — proof the bench is not uniform.",
    state: "PENDING DATA",
  },
  {
    route: "/compare/{a}/{b}",
    name: "The Other Door",
    fn: "Two judges. The quantified counterfactual: what changes — in numbers with intervals — when the door changes.",
    state: "PENDING DATA",
  },
  {
    route: "/docket/{id}",
    name: "The Chain of Custody",
    fn: "Every number on this site, traced to the filed document it came from. Click any figure, arrive at the primary record.",
    state: "PENDING DATA",
  },
  {
    route: "/standard",
    name: "The Norm",
    fn: "LS-1.0 itself — the computation, public and replicable. The spec this site obeys, rendered from the repository file.",
    state: "LIVE",
    href: "/standard",
  },
  {
    route: "/api/*",
    name: "The Interface",
    fn: "Canonical JSON for machines. Versioned, cached, deterministic. The standard is only real if machines can consume it.",
    state: "PENDING DATA",
  },
];

export default async function Home() {
  const sys = await getSystemState();

  return (
    <div className="flex min-h-screen flex-col bg-paper font-display text-ink">
      <Chrome
        build={sys.build}
        judgesScored={sys.judgesScored}
        docketsIngested={sys.docketsIngested}
        engineCycles={sys.engineCycles}
        engineLast={sys.engineLast}
        state={sys.state}
        route="/"
      />

      <main className="flex-1">
        <Interrogation
          judgesScored={sys.judgesScored}
          docketsIngested={sys.docketsIngested}
        />

        {/* ——— THE MAP ——— */}
        <section id="map" className="scroll-mt-16 border-b border-rule">
          <div className="mx-auto max-w-[1600px] px-6 py-16 sm:px-10 lg:px-14 lg:py-20">
            <p className="micro">[003] The map</p>
            <h2 className="mt-5 font-display text-[clamp(1.9rem,3.6vw,2.9rem)] font-bold uppercase leading-[1.02] tracking-[-0.02em]">
              Seven URLs. Each one computes.
              <br />
              <span className="text-ink-2">Nothing else ships.</span>
            </h2>

            <div className="mt-10 border-t border-rule">
              {MAP.map((r) => {
                const row = (
                  <>
                    <span className="tabular font-data text-[13px] font-semibold">
                      {r.route}
                    </span>
                    <span className="font-display text-[15px] font-semibold uppercase tracking-[0.01em]">
                      {r.name}
                    </span>
                    <span className="text-[13px] leading-relaxed text-ink-2">
                      {r.fn}
                    </span>
                    <span
                      className={`font-data text-[10px] font-medium tracking-[0.08em] uppercase sm:justify-self-end ${
                        r.state === "LIVE" ? "text-signal-deep" : "text-ink-3"
                      }`}
                    >
                      {r.state === "LIVE" ? "■ LIVE" : "○ PENDING DATA"}
                    </span>
                  </>
                );
                const cls =
                  "grid grid-cols-1 gap-x-8 gap-y-1.5 border-b border-hairline py-4 sm:grid-cols-[180px_190px_1fr_120px] sm:items-baseline";
                return r.href ? (
                  <a key={r.route} href={r.href} className={`${cls} hover:bg-row-hover`}>
                    {row}
                  </a>
                ) : (
                  <div key={r.route} className={cls}>
                    {row}
                  </div>
                );
              })}
            </div>

            <p className="micro mt-7 normal-case leading-relaxed tracking-[0.04em] text-ink-3">
              A URL that computes nothing does not ship. No about page. No
              blog. No team. No press kit. The presentation is the data —
              the four data routes open when the first dockets are FILED,
              and not one day before.
            </p>
          </div>
        </section>
      </main>

      {/* ——— FOOTER — the frame of the page ——— */}
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
