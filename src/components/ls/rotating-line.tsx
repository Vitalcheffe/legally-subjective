/**
 * The Rotating Question — the "WOULD YOU STILL" loop.
 * Each option holds ~3.2s, then gives way with a single quiet rise-and-fade.
 * The hold is long on purpose: panic needs time to land. The motion is
 * minimal on purpose: the room stays still; only the sentence changes.
 * Respects prefers-reduced-motion (static first option).
 */
"use client";

import { useEffect, useRef, useState } from "react";

export interface RotatingLineProps {
  options: string[];
  intervalMs?: number;
  className?: string;
}

export function RotatingLine({ options, intervalMs = 3200, className }: RotatingLineProps) {
  const [index, setIndex] = useState(0);
  const [visible, setVisible] = useState(true);
  const prefersReduced = useRef(false);

  useEffect(() => {
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      prefersReduced.current = true;
      return;
    }
    const id = setInterval(() => {
      setVisible(false);
      const t = setTimeout(() => {
        setIndex((i) => (i + 1) % options.length);
        setVisible(true);
      }, 420);
      return () => clearTimeout(t);
    }, intervalMs);
    return () => clearInterval(id);
  }, [options.length, intervalMs]);

  return (
    <span
      className={`inline-block transition-all duration-[420ms] ease-[cubic-bezier(0.2,0,0,1)] ${
        visible ? "translate-y-0 opacity-100" : "translate-y-[0.18em] opacity-0"
      } ${className ?? ""}`}
      aria-live="polite"
    >
      {options[index]}
    </span>
  );
}
