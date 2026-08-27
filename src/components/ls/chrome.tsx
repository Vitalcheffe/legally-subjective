"use client";

/**
 * The Chrome — permanent telemetry. Black bar, white mono.
 * The site displays its own system state at all times: build, counts,
 * engine state, UTC clock. This is not decoration; it is the product
 * showing you what it currently knows.
 */
import { useEffect, useState } from "react";

export interface ChromeProps {
  build: string;
  judgesScored: number;
  docketsIngested: number;
  engineCycles: number;
  engineLast: string;
  state: "COLD" | "WARM";
  /** Current route, displayed like a terminal path. */
  route: string;
}

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

export function Chrome({
  build,
  judgesScored,
  docketsIngested,
  engineCycles,
  engineLast,
  state,
  route,
}: ChromeProps) {
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
          <span className="text-white/70">LS-1.0</span>
          <span className="hidden text-white/30 sm:inline">·</span>
          <span className="hidden text-white/70 sm:inline">UI-1.0 EXHIBIT</span>
          <span className="hidden text-white/30 md:inline">·</span>
          <span className="hidden text-white/50 md:inline">{route}</span>
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 tabular">
          <span className="hidden text-white/70 sm:inline">BUILD {build}</span>
          <span className="hidden text-white/70 lg:inline">
            ENGINE C{engineCycles.toString().padStart(2, "0")} · {engineLast}
          </span>
          <span className="text-white/70">
            JUDGES {judgesScored.toString().padStart(3, "0")}
          </span>
          <span className="text-white/70">
            DOCKETS {docketsIngested.toString().padStart(3, "0")}
          </span>
          <span className="flex items-center gap-1.5 text-signal-on-ink">
            <span className="inline-block h-[7px] w-[7px] bg-signal-on-ink" />
            {state}
          </span>
          <span>UTC {utc}</span>
        </div>
      </div>
    </header>
  );
}
