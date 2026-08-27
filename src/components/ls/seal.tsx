/**
 * The Seal — § in a ring of ink. Beats ONCE on mount. Never loops.
 * (Boss's law: the wax presses one time, then the room is still.)
 */
"use client";

import { useEffect, useState } from "react";

export function Seal({ size = 34, className }: { size?: number; className?: string }) {
  const [beat, setBeat] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setBeat(true), 350);
    return () => clearTimeout(t);
  }, []);

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full border-[2.5px] border-seal select-none ${className ?? ""}`}
      style={{
        width: size,
        height: size,
        animation: beat ? "seal-beat 600ms cubic-bezier(0.2, 0, 0, 1) 1 ease-out" : undefined,
      }}
      aria-hidden="true"
    >
      <span
        className="font-display leading-none text-seal"
        style={{ fontSize: size * 0.62, transform: "translateY(-2%)" }}
      >
        §
      </span>
    </span>
  );
}
