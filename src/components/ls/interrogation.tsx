"use client";

/**
 * The Interrogation — the front door of ONE DOOR DOWN.
 *
 * WOULD YOU STILL is fixed. The ending rotates on a fixed 3400ms
 * metronome, by a hard cut — no fade, no slide. State changes are
 * cuts; the only clocks are the clock and the cursor.
 *
 * The order is fixed and deterministic. No shuffling: this house
 * does not do randomness.
 *
 * Every ending is an addressable state: freezing one writes its slug
 * into the URL, so every variant of the question is a shareable link.
 * The tab title carries the question with it.
 */
import { useCallback, useEffect, useRef, useState } from "react";

const METRONOME_MS = 3400;

interface Ending {
  n: string;
  text: string;
  domain: string;
  slug: string;
}

const ENDINGS: Ending[] = [
  { n: "01", text: "BE FREE TONIGHT", domain: "SENTENCING", slug: "be-free-tonight" },
  { n: "02", text: "TUCK YOUR KIDS IN", domain: "CUSTODY", slug: "tuck-your-kids-in" },
  { n: "03", text: "KEEP THE KEYS TO YOUR HOUSE", domain: "EVICTION", slug: "keep-the-keys" },
  { n: "04", text: "BE HOME FOR DINNER", domain: "PRETRIAL RELEASE", slug: "be-home-for-dinner" },
  { n: "05", text: "WALK OUT A CITIZEN", domain: "REMOVAL", slug: "walk-out-a-citizen" },
  { n: "06", text: "KEEP YOUR BUSINESS", domain: "INJUNCTION", slug: "keep-your-business" },
  { n: "07", text: "HAVE A TRIAL AT ALL", domain: "SUMMARY JUDGMENT", slug: "have-a-trial-at-all" },
  { n: "08", text: "BE ALIVE IN TEN YEARS", domain: "CAPITAL CASES", slug: "be-alive-in-ten-years" },
  { n: "09", text: "TAKE THE PLEA", domain: "PLEA COLLOQUY", slug: "take-the-plea" },
  { n: "10", text: "KEEP YOUR LICENSE", domain: "DISCIPLINE", slug: "keep-your-license" },
  { n: "11", text: "GET WHAT YOU’RE OWED", domain: "DAMAGES", slug: "get-what-youre-owed" },
  { n: "12", text: "BE BELIEVED", domain: "PROTECTIVE ORDERS", slug: "be-believed" },
];

type Mode = "AUTO" | "FROZEN";

export interface InterrogationProps {
  justices: number;
  cases: number;
}

export function Interrogation({ justices, cases }: InterrogationProps) {
  const [index, setIndex] = useState(0);
  const [mode, setMode] = useState<Mode>("AUTO");
  const [copied, setCopied] = useState<string | null>(null);
  const indexRef = useRef(0);
  const copyTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* Keep the ref in sync outside of render. */
  useEffect(() => {
    indexRef.current = index;
  }, [index]);

  const cut = useCallback((n: number) => {
    setIndex(((n % ENDINGS.length) + ENDINGS.length) % ENDINGS.length);
  }, []);

  const freezeAt = useCallback(
    (n: number) => {
      setMode("FROZEN");
      cut(n);
    },
    [cut],
  );

  /* The metronome. Fixed interval, hard cut. */
  useEffect(() => {
    if (mode !== "AUTO") return;
    const id = setInterval(() => cut(indexRef.current + 1), METRONOME_MS);
    return () => clearInterval(id);
  }, [mode, cut]);

  /* Addressable state + the tab carries the question. */
  useEffect(() => {
    const e = ENDINGS[index];
    document.title = `WOULD YOU STILL ${e.text} — LEGALLY SUBJECTIVE`;
    if (mode === "FROZEN") {
      window.history.replaceState(null, "", `#${e.slug}`);
    }
  }, [index, mode]);

  /* Restore from a shared link; honor reduced motion. The URL is an
     external system — we sync from it right after mount. */
  useEffect(() => {
    const restore = () => {
      const reduced = window.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;
      const slug = window.location.hash.replace(/^#/, "");
      const found = ENDINGS.findIndex((e) => e.slug === slug);
      if (found >= 0) {
        setMode("FROZEN");
        setIndex(found);
      } else if (reduced) {
        setMode("FROZEN");
      }
    };
    queueMicrotask(restore);
  }, []);

  /* Keyboard: the question is an instrument. */
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      const t = ev.target as HTMLElement | null;
      const onControl =
        t !== null &&
        (t.tagName === "BUTTON" || t.tagName === "A" || t.tagName === "INPUT");
      if (ev.key === "ArrowRight") {
        freezeAt(indexRef.current + 1);
      } else if (ev.key === "ArrowLeft") {
        freezeAt(indexRef.current - 1);
      } else if (ev.key === " " && !onControl) {
        ev.preventDefault();
        setMode((m) => (m === "AUTO" ? "FROZEN" : "AUTO"));
      } else if (/^[0-9]$/.test(ev.key)) {
        const n = ev.key === "0" ? 9 : Number(ev.key) - 1;
        freezeAt(n);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [freezeAt]);

  const copyQuestion = useCallback(async () => {
    const e = ENDINGS[indexRef.current];
    const url = `${window.location.origin}${window.location.pathname}#${e.slug}`;
    const q = `WOULD YOU STILL ${e.text} — IF YOUR JUDGE HAD BEEN ONE DOOR DOWN? ${url}`;
    try {
      await navigator.clipboard.writeText(q);
      setCopied(e.text);
    } catch {
      setCopied("COPY FAILED — USE THE URL BAR");
    }
    if (copyTimer.current) clearTimeout(copyTimer.current);
    copyTimer.current = setTimeout(() => setCopied(null), 2600);
  }, []);

  const current = ENDINGS[index];

  return (
    <section className="border-b border-rule">
      <div className="mx-auto grid w-full max-w-[1600px] lg:grid-cols-[minmax(0,1fr)_420px]">
        {/* ——— THE QUESTION ——— */}
        <div className="flex min-h-[calc(100svh-40px)] flex-col px-6 py-14 sm:px-10 lg:py-16 lg:pl-14">
          <p className="micro">[001] INTERROGATION — ONE DOOR DOWN</p>

          <h1 className="mt-10 font-display font-bold uppercase leading-[0.95] tracking-[-0.03em] text-ink">
            <span className="block text-[clamp(3rem,8.5vw,8.5rem)]">
              Would you still
            </span>
            <span
              aria-live="off"
              className="mt-3 block min-h-[2.1em] text-[clamp(1.7rem,4.6vw,4.4rem)] leading-[1.05] text-signal"
            >
              {current.text}
              <span
                aria-hidden="true"
                className={`cursor ${mode === "FROZEN" ? "frozen" : ""}`}
              />
            </span>
          </h1>

          <p className="mt-7 font-display text-[clamp(0.85rem,1.5vw,1.25rem)] font-medium uppercase tracking-[0.04em] text-ink-2">
            — if your judge had been one door down?
          </p>

          <div className="tabular mt-8 font-data text-[11px] leading-[1.9] tracking-[0.05em] text-ink-2">
            <div>
              [ {current.n} / 12 ] · {mode === "AUTO" ? "ROTATING" : "FROZEN"}
            </div>
            <div className="text-ink-3">
              ← → MOVE · SPACE FREEZE · 1–9 JUMP · CLICK A LINE TO KEEP IT
            </div>
            {copied && (
              <div className="text-signal-deep" role="status">
                COPIED — WOULD YOU STILL {copied}?
              </div>
            )}
          </div>

          {/* ——— THE PORTAL ——— */}
          <div className="mt-auto flex flex-col items-start gap-5 pt-16">
            <p className="font-display text-[clamp(1.05rem,2vw,1.6rem)] font-semibold uppercase tracking-[-0.01em]">
              What do you have to lose?
            </p>
            <div className="flex flex-wrap gap-3">
              <a href={justices > 0 ? "/court/scotus" : "#questions"} className="btn">
                {justices > 0 ? "Open the record →" : "Enter the record →"}
              </a>
              <button type="button" onClick={copyQuestion} className="btn">
                Copy the question
              </button>
            </div>
            <p className="micro normal-case tracking-[0.04em] text-ink-3">
              {justices > 0
                ? `${justices} justices measured on ${cases} decided cases, read from the public record. Nothing here is estimated.`
                : "The record opens when the first judges are measured. Nothing here is estimated."}
            </p>
          </div>
        </div>

        {/* ——— THE TWELVE ENDINGS ——— */}
        <aside className="flex flex-col border-t border-rule px-6 py-14 sm:px-10 lg:border-t-0 lg:border-l lg:py-16 lg:pl-10 lg:pr-10">
          <p className="micro">[002] The twelve endings</p>
          <ol className="mt-6">
            {ENDINGS.map((e, k) => (
              <li key={e.slug}>
                <button
                  type="button"
                  aria-pressed={k === index}
                  onClick={() => freezeAt(k)}
                  className={`grid w-full grid-cols-[32px_1fr] items-baseline gap-x-2 border-b border-l-2 border-hairline py-2.5 pl-3 pr-2 text-left ${
                    k === index
                      ? "border-l-signal bg-row-hover"
                      : "border-l-transparent hover:border-l-signal hover:bg-row-hover"
                  }`}
                >
                  <span
                    className={`tabular font-data text-[11px] font-medium ${
                      k === index ? "text-signal-deep" : "text-ink-3"
                    }`}
                  >
                    {e.n}
                  </span>
                  <span className="min-w-0">
                    <span
                      className={`block font-display text-[13px] font-medium uppercase leading-snug ${
                        k === index ? "text-signal" : "text-ink"
                      }`}
                    >
                      {e.text}
                    </span>
                    <span className="mt-0.5 block font-data text-[9.5px] tracking-[0.06em] whitespace-nowrap text-ink-3 uppercase">
                      {e.domain} · Δ —
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ol>
          <p className="micro mt-6 normal-case leading-relaxed tracking-[0.04em] text-ink-3">
            Twelve things a ruling can take from someone. Click one to keep it
            on screen — and send it to whoever needs to see the question.
          </p>
        </aside>
      </div>

      {/* ——— STATUS BAND — what stands behind the page ——— */}
      <div className="tabular border-t border-hairline px-6 py-3 font-data text-[10.5px] leading-[1.8] tracking-[0.05em] text-ink-2 sm:px-10 lg:px-14">
        BUILT FROM PUBLIC COURT RECORDS · {justices} JUSTICES · {cases} DECIDED
        CASES · NOTHING ON THIS SITE IS INVENTED — IF A NUMBER CAN&apos;T BE
        TRACED TO A PUBLIC FILING, IT DOES NOT APPEAR
      </div>
    </section>
  );
}
