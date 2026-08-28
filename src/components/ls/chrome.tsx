"use client";

/**
 * The Chrome — the permanent strip. Black bar, white mono.
 * What a human needs to know at all times: what this site does,
 * how much real court record is behind it, that it is live, and
 * what time it is. No build hashes. No engine cycles. No routes.
 */
import { useEffect, useState } from "react";

export interface ChromeProps {
  /** Justices measured — from the FILED dockets. */
  justices: number;
  /** Decided cases actually read from the public record. */
  cases: number;
  /** Court-record window, e.g. "OCT 2020 — AUG 2026". */
  windowLabel: string;
  /** WARM: the record exists. COLD: not yet. */
  state: "COLD" | "WARM";
}

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

export function Chrome({ justices, cases, windowLabel, state }: ChromeProps) {
  const [utc, setUtc] = useState("--:--:--");

  useEffect(() => {
    const tick = () => {
      const d = new Date();
      setUtc(
        `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`,
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="sticky top-0 z-50 bg-ink text-white">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-6 gap-y-1 px-6 py-2.5 font-data text-[11px] font-medium tracking-[0.06em] sm:px-10 lg:px-14">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <a href="/" className="font-semibold tracking-[0.12em]">
            LEGALLY SUBJECTIVE
          </a>
          <span className="text-white/30">·</span>
          <span className="hidden text-white/70 sm:inline">
            DO JUDGES DIFFER? WE COUNT.
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 tabular">
          {justices > 0 && (
            <span className="text-white/70">
              {justices} JUSTICES · {cases} CASES
              {windowLabel ? ` · ${windowLabel}` : ""}
            </span>
          )}
          <a
            href="/paper"
            className="hidden text-white/50 transition-colors hover:text-white md:inline"
            title="The research article — method, figures, code"
          >
            THE SCIENCE
          </a>
          <span
            className="flex items-center gap-1.5 text-signal-on-ink"
            title={
              state === "WARM"
                ? "Measured from public court records"
                : "The record is being built"
            }
          >
            <span className="inline-block h-[7px] w-[7px] bg-signal-on-ink" />
            {state === "WARM" ? "LIVE" : "BUILDING"}
          </span>
          <span>UTC {utc}</span>
        </div>
      </div>
    </header>
  );
}
