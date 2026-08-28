"use client";

/**
 * THE DRAW — the front door. One page, one question, one number,
 * one button.
 *
 * You don't pick your judge. A hallway you never see does. This is
 * that hallway, as an instrument: spin the bench, a justice falls on
 * you, and the real number from the public record lands with them.
 *
 * THE ONE EXCEPTION TO THE HOUSE RULE ON RANDOMNESS: everywhere else
 * this site is deterministic, because data must not be shuffled for
 * effect. Here the randomness IS the finding. The draw is arbitrary;
 * that arbitrariness is what the visitor must feel in the body. The
 * wheel doesn't decorate the message — it is the message.
 *
 * Numbers shown are real: the disposition rate measured on the
 * justice's recorded votes (see their docket for the receipt).
 */
import { useCallback, useEffect, useState } from "react";
import type { JusticeDraw } from "@/lib/justices";

const STAKES = [
  "YOUR FREEDOM",
  "YOUR KIDS",
  "YOUR HOUSE",
  "YOUR CITIZENSHIP",
  "YOUR BUSINESS",
  "YOUR DAY IN COURT",
  "YOUR LIFE",
  "YOUR PLEA",
  "YOUR LICENSE",
  "WHAT YOU'RE OWED",
  "TO BE BELIEVED",
  "YOUR VOTE",
];

const STAKE_MS = 1900;
const FLASH_MS = 85;

type Phase = "IDLE" | "FLASH" | "LANDED";

/** Uniform draw from the bench — the lottery, honestly uniform. */
function drawIndex(n: number): number {
  if (n <= 0) return 0;
  const buf = new Uint32Array(1);
  crypto.getRandomValues(buf);
  return buf[0] % n;
}

function pct(v: number): number {
  return Math.round(v * 100);
}

export interface DrawProps {
  bench: JusticeDraw[];
  windowLabel: string;
  casesDecided: number;
}

export function Draw({ bench, windowLabel, casesDecided }: DrawProps) {
  const [phase, setPhase] = useState<Phase>("IDLE");
  const [landed, setLanded] = useState<JusticeDraw | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [stake, setStake] = useState(0);
  const [spins, setSpins] = useState(0);

  /* The stake line rotates while idle — the twelve things a ruling
     can take. Hard cuts, fixed metronome. */
  useEffect(() => {
    if (phase !== "IDLE") return;
    const id = setInterval(() => setStake((s) => (s + 1) % STAKES.length), STAKE_MS);
    return () => clearInterval(id);
  }, [phase]);

  const land = useCallback(
    (j: JusticeDraw) => {
      setLanded(j);
      setPhase("LANDED");
      setSpins((n) => n + 1);
      window.history.replaceState(null, "", `#you-drew-${j.slug}`);
      /* LS-AUDIT-001 inj. 1 & 12: the tab title carries the interval and
         the count — what gets screenshotted carries its own doubt. */
      document.title = `YOU DREW ${j.stamp} — ${pct(j.forTheAsking)} ±${j.pm} OUT OF 100 · ${j.votes} VOTES · LEGALLY SUBJECTIVE`;
    },
    [],
  );

  const spin = useCallback(() => {
    if (bench.length === 0) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const winner = bench[drawIndex(bench.length)];
    if (reduced) {
      land(winner);
      return;
    }
    /* The flash: hard cuts through the names, then a dead stop.
       No easing. No fade. The stop is the event. */
    setPhase("FLASH");
    setLanded(null);
    const cuts = 14 + (drawIndex(9) + 2); // 16–24 cuts — the wheel's own length
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      if (i >= cuts) {
        clearInterval(id);
        setFlash(null);
        land(winner);
      } else {
        setFlash(bench[i % bench.length].stamp);
      }
    }, FLASH_MS);
  }, [bench, land]);

  /* Restore a shared draw: #you-drew-kavanaugh lands frozen.
     The URL is an external system — sync from it after mount. */
  useEffect(() => {
    const restore = () => {
      const h = window.location.hash.replace(/^#/, "");
      if (!h.startsWith("you-drew-")) return;
      const j = bench.find((b) => b.slug === h.slice("you-drew-".length));
      if (j) {
        setLanded(j);
        setPhase("LANDED");
      }
    };
    queueMicrotask(restore);
  }, [bench]);

  /* The tab carries the draw — with its interval and its count
     (LS-AUDIT-001 inj. 1: a screenshot must not survive without its ±).
     Re-asserted on every landed change — Next.js re-applies static
     metadata after hydration and would otherwise overwrite the restore
     path. The draw wins the race. */
  useEffect(() => {
    if (phase === "LANDED" && landed) {
      const t = `YOU DREW ${landed.stamp} — ${pct(landed.forTheAsking)} ±${landed.pm} OUT OF 100 · ${landed.votes} VOTES · LEGALLY SUBJECTIVE`;
      document.title = t;
      const id = setTimeout(() => {
        document.title = t;
      }, 80);
      return () => clearTimeout(id);
    }
  }, [phase, landed]);

  if (bench.length === 0) {
    return (
      <section className="flex min-h-[calc(100svh-40px)] flex-col items-start justify-center px-6 py-16 sm:px-10 lg:px-14">
        <p className="micro">[001] THE DRAW</p>
        <h1 className="mt-6 font-display text-[clamp(2.2rem,6vw,5.5rem)] font-bold uppercase leading-[0.95] tracking-[-0.03em]">
          The bench is empty.
        </h1>
        <p className="mt-6 max-w-[52ch] font-display text-[15px] leading-relaxed text-ink-2">
          No dockets are FILED yet. The wheel cannot spin on numbers that
          do not exist — it will open the moment the first judge is
          measured from the public record.
        </p>
      </section>
    );
  }

  const benchSorted = [...bench].sort((a, b) => b.forTheAsking - a.forTheAsking);
  const lowest = benchSorted[benchSorted.length - 1];
  const highest = benchSorted[0];
  const rank = benchSorted.findIndex((j) => j.slug === landed?.slug) + 1;

  return (
    <section className="relative flex min-h-[calc(100svh-40px)] flex-col border-b border-rule">
      {/* minimal masthead — one line, no telemetry */}
      <div className="absolute inset-x-0 top-0 z-10">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-6 pt-4 font-data text-[11px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
          <a href="/" className="font-semibold tracking-[0.12em]">
            LEGALLY SUBJECTIVE
          </a>
          <span className="flex items-center gap-1.5 text-signal-deep">
            <span className="inline-block h-[7px] w-[7px] bg-signal-deep" />
            REAL DATA · {casesDecided} CASES
          </span>
        </div>
      </div>

      {/* ——— IDLE: the question ——— */}
      {phase === "IDLE" && (
        <div className="mx-auto flex w-full max-w-[1100px] flex-1 flex-col justify-center px-6 py-24 sm:px-10">
          <p className="micro">[001] THE DRAW</p>
          <h1 className="mt-8 font-display font-bold uppercase leading-[0.93] tracking-[-0.03em] text-ink">
            <span className="block text-[clamp(2.6rem,7.5vw,7rem)]">
              You don&apos;t pick
            </span>
            <span className="block text-[clamp(2.6rem,7.5vw,7rem)]">
              your judge.
            </span>
          </h1>
          <p className="mt-8 font-display text-[clamp(1.25rem,3vw,2.4rem)] font-bold uppercase leading-[1.05] tracking-[-0.01em] text-signal">
            Tonight it&apos;s{" "}
            <span className="border-b-4 border-signal">
              {STAKES[stake]}
            </span>
            <span className="cursor" />
          </p>
          <p className="mt-7 max-w-[58ch] font-display text-[15.5px] leading-[1.7] text-ink-2">
            A hallway you will never see decides who decides you. Same law,
            same cases — {bench.length} doors, and behind each one a
            measurably different decider. Every number you land on arrives
            with its vote count and its honest ± — the doubt is printed on
            the chip, not left in the pocket. Spin it. Feel the floor move.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={spin}
              className="btn border-2 border-ink px-8 py-4 text-[15px]"
            >
              SPIN THE BENCH ↻
            </button>
            <span className="font-data text-[11px] tracking-[0.05em] text-ink-3">
              {bench.length} DOORS · {casesDecided} DECIDED CASES
              {windowLabel ? ` · ${windowLabel}` : ""}
            </span>
          </div>
        </div>
      )}

      {/* ——— FLASH: the wheel ——— */}
      {phase === "FLASH" && (
        <div className="mx-auto flex w-full max-w-[1100px] flex-1 flex-col items-start justify-center px-6 py-24 sm:px-10">
          <p className="micro">[001] THE DRAW · SPINNING</p>
          <div
            className="mt-8 min-h-[1.2em] w-full font-display font-bold uppercase leading-[0.93] tracking-[-0.03em] text-ink"
            aria-live="off"
          >
            <span className="block text-[clamp(2.6rem,7.5vw,7rem)]">
              {flash ?? "—"}
            </span>
          </div>
          <p className="mt-8 font-data text-[11px] tracking-[0.05em] text-ink-3">
            THE HALLWAY DECIDES ·
          </p>
        </div>
      )}

      {/* ——— LANDED: the verdict ——— */}
      {phase === "LANDED" && landed && (
        <div className="mx-auto flex w-full max-w-[1100px] flex-1 flex-col justify-center px-6 py-20 sm:px-10">
          <p className="micro">
            [001] THE DRAW · DRAW #{spins.toString().padStart(2, "0")} ·{" "}
            {STAKES[stake]}
          </p>

          {/* the stamp */}
          <div className="mt-8 inline-flex w-fit rotate-[-1.2deg] bg-signal px-5 py-2.5 font-display text-[clamp(1.2rem,2.6vw,2rem)] font-bold uppercase tracking-[0.02em] text-white">
            YOU DREW {landed.stamp}
          </div>

          {/* LS-AUDIT-001 inj. 5 — the short-record flag, driven by the
              docket's own service-years data, never by a hard-coded name. */}
          {landed.shortMandate && (
            <p className="mt-4 inline-flex w-fit items-center gap-2 border-2 border-signal-deep px-4 py-2 font-data text-[11px] font-bold tracking-[0.08em] uppercase text-signal-deep">
              <span className="inline-block h-[7px] w-[7px] bg-signal-deep" />
              Short record — {landed.serviceYears} terms in this window vs{" "}
              {landed.benchMaxYears} for the rest of the bench · fewer votes,
              wider interval, and first-term drift is documented in the
              literature. Read this door with extra humility.
            </p>
          )}

          {/* the number — with its interval at the scale of the number
              itself (LS-AUDIT-001 inj. 1 & 12: the ± is the brand) */}
          <div className="mt-6 flex flex-wrap items-end gap-x-5 gap-y-1">
            <span className="tabular font-display text-[clamp(4.5rem,13vw,11rem)] font-bold uppercase leading-[0.85] tracking-[-0.04em] text-signal">
              {pct(landed.forTheAsking)}
            </span>
            <span className="tabular font-display text-[clamp(2rem,5.5vw,4.6rem)] font-bold uppercase leading-[0.85] tracking-[-0.02em] text-signal-deep">
              ±{landed.pm}
            </span>
            <span className="pb-3 font-display text-[clamp(1.3rem,3vw,2.4rem)] font-bold uppercase leading-none text-ink">
              out of 100
            </span>
            <span className="pb-3.5 font-data text-[clamp(0.9rem,1.6vw,1.15rem)] font-semibold tracking-[0.06em] text-ink-2">
              · {landed.votes} VOTES
            </span>
          </div>
          <p className="mt-2 font-data text-[11.5px] tracking-[0.05em] text-ink-3">
            95% INTERVAL {Math.round(landed.ciLo * 100)}–
            {Math.round(landed.ciHi * 100)} (WILSON) — THE COUNT AND ITS DOUBT
            TRAVEL TOGETHER, INCLUDING IN YOUR SCREENSHOT.
          </p>

          <p className="mt-7 max-w-[64ch] font-display text-[clamp(1rem,1.7vw,1.3rem)] leading-[1.6] text-ink">
            When a person stood before this court and asked for relief —
            their freedom, their kids, their home, their stay —{" "}
            <strong>{landed.name}</strong> voted their way{" "}
            <strong className="text-signal-deep">
              {pct(landed.forTheAsking)} times in 100
            </strong>
            , give or take <strong>{landed.pm}</strong> — the honest width of
            a count made on {landed.votes} recorded votes
            {windowLabel ? `, ${windowLabel}` : ""}. Not an opinion. A
            count — with its interval.
          </p>

          {/* the counterfactual — every door with its count (inj. 1) */}
          <div className="mt-8 grid max-w-[760px] grid-cols-1 gap-px border border-ink bg-hairline sm:grid-cols-3">
            <div className="bg-paper px-5 py-4">
              <p className="micro">Same bench, lowest door</p>
              <p className="tabular mt-2 font-display text-[1.6rem] font-bold leading-none">
                {pct(lowest.forTheAsking)}
                <span className="text-signal-deep"> ±{lowest.pm}</span>
                <span className="ml-2 font-data text-[11px] font-medium tracking-[0.05em] text-ink-3">
                  {lowest.stamp} · {lowest.votes} VOTES
                </span>
              </p>
            </div>
            <div className="bg-paper px-5 py-4">
              <p className="micro">Your door&apos;s rank</p>
              <p className="tabular mt-2 font-display text-[1.6rem] font-bold leading-none">
                {rank} <span className="text-[1rem]">of {bench.length}</span>
                <span className="ml-2 font-data text-[11px] font-medium tracking-[0.05em] text-ink-3">
                  BY FOR-THE-ASKING
                </span>
              </p>
            </div>
            <div className="bg-paper px-5 py-4">
              <p className="micro">Highest door</p>
              <p className="tabular mt-2 font-display text-[1.6rem] font-bold leading-none">
                {pct(highest.forTheAsking)}
                <span className="text-signal-deep"> ±{highest.pm}</span>
                <span className="ml-2 font-data text-[11px] font-medium tracking-[0.05em] text-ink-3">
                  {highest.stamp} · {highest.votes} VOTES
                </span>
              </p>
            </div>
          </div>
          <p className="mt-4 max-w-[64ch] font-display text-[14px] leading-[1.65] text-ink-2">
            Same cases. Same law. The doors run from{" "}
            {pct(lowest.forTheAsking)} to {pct(highest.forTheAsking)} — and
            each of those counts carries ±{lowest.pm}–±{highest.pm} points
            of its own, so read the spread with those widths in mind. The
            hallway, not the merits, moved you{" "}
            {pct(landed.forTheAsking) - pct(lowest.forTheAsking) >= 0
              ? `up ${pct(landed.forTheAsking) - pct(lowest.forTheAsking)}`
              : `down ${pct(lowest.forTheAsking) - pct(landed.forTheAsking)}`}{" "}
            points. Spin again and watch a different door do it differently.
          </p>

          <div className="mt-10 flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={spin}
              className="btn border-2 border-signal bg-signal px-8 py-4 text-[15px] text-white hover:bg-signal-deep hover:border-signal-deep"
            >
              SPIN AGAIN ↻
            </button>
            <a href={`/judge/${landed.docket}`} className="btn">
              See this judge&apos;s full record →
            </a>
            <a href={`/docket/${landed.docket}`} className="btn border-ink-3">
              The receipt for this number
            </a>
          </div>

          <p className="micro mt-8 max-w-[72ch] normal-case leading-relaxed tracking-[0.02em] text-ink-3">
            Honest limits: the public record does not break this down by
            crime type — this is the overall rate across every merits case
            the bench heard together. The ± is the sampling width of the
            count itself (Wilson, 95%); it does not cover case-to-case
            variation, which is larger. This is a real measurement of real
            votes, not a prediction of any case. Full method:{" "}
            <a href="/standard" className="underline decoration-hairline underline-offset-4 hover:decoration-signal">
              the standard
            </a>
            .
          </p>
        </div>
      )}
    </section>
  );
}
