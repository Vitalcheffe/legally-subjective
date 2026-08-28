/**
 * The Subjectivity Fingerprint Glyph — Standard LS-1.0, §5.
 * Deterministic radial signature. Pure function of (axes, n, docket_id).
 * No randomness — same inputs produce bit-identical SVG, server and client.
 *
 * SPECIMEN mode: when no real axes exist yet, the glyph renders its
 * "awaiting data" state — dashed contour at full radius. Never fabricated.
 */
import { sha256hex } from "@/lib/sha256";

const R = 100;
export const AXIS_ORDER = [
  "disposition",
  "temperament",
  "precedent",
  "reversal",
  "orality",
  "exposure",
] as const;

export type AxisValue = number | null; // percentile 0–99, or null = insufficient data
export type Axes = Partial<Record<(typeof AXIS_ORDER)[number], AxisValue>>;

function tiltDegrees(docketId: string): number {
  const digest = sha256hex(docketId);
  const big = BigInt(`0x${digest}`);
  return Number(big % 360n);
}

function catmullRomPath(points: Array<[number, number]>, samples = 20): string {
  const n = points.length;
  if (n < 3) return "";
  const parts: string[] = [];
  for (let i = 0; i < n; i++) {
    const p0 = points[(i - 1 + n) % n];
    const p1 = points[i];
    const p2 = points[(i + 1) % n];
    const p3 = points[(i + 2) % n];
    for (let j = 0; j < samples; j++) {
      const t = j / samples;
      const t2 = t * t;
      const t3 = t2 * t;
      const x =
        0.5 *
        (2 * p1[0] +
          (-p0[0] + p2[0]) * t +
          (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
          (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3);
      const y =
        0.5 *
        (2 * p1[1] +
          (-p0[1] + p2[1]) * t +
          (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
          (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3);
      parts.push(`${parts.length === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`);
    }
  }
  return `${parts.join(" ")} Z`;
}

export interface GlyphProps {
  docketId: string;
  /** Pass null for SPECIMEN (no data yet). */
  axes: Axes | null;
  /** Number of underlying records — drives the inner evidence ring. */
  n?: number;
  maxN?: number;
  className?: string;
  strokeWidth?: number;
}

export function Glyph({
  docketId,
  axes,
  n = 0,
  maxN = 10_000,
  className,
  strokeWidth = 2.5,
}: GlyphProps) {
  const tilt = (tiltDegrees(docketId) * Math.PI) / 180;
  const isSpecimen = axes === null;

  const spokes = AXIS_ORDER.map((axis, i) => {
    const angle = tilt + (i * 2 * Math.PI) / AXIS_ORDER.length - Math.PI / 2;
    const value = axes?.[axis];
    if (value == null) {
      // insufficient-data: spoke rendered dashed at full radius
      return {
        x: R * Math.cos(angle),
        y: R * Math.sin(angle),
        dashed: true,
      };
    }
    const r = (value / 100) * R;
    return { x: r * Math.cos(angle), y: r * Math.sin(angle), dashed: false };
  });

  const solid = spokes.filter((s) => !s.dashed);
  const hasData = solid.length >= 3;
  const contour = hasData
    ? catmullRomPath(solid.map((s) => [s.x, s.y] as [number, number]))
    : catmullRomPath(spokes.map((s) => [s.x, s.y] as [number, number]));

  // Evidence ring: log10(n)/log10(maxN) · R/3 — the weight of proof, visible.
  const ring = n > 0 ? (Math.log10(n) / Math.log10(maxN)) * (R / 3) : 0;

  return (
    <svg
      viewBox={`${-R - 14} ${-R - 14} ${(R + 14) * 2} ${(R + 14) * 2}`}
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label={`Subjectivity Fingerprint ${docketId}${isSpecimen ? " (specimen, no data yet)" : ""}`}
    >
      {/* spokes */}
      {spokes.map((s, i) => (
        <line
          key={i}
          x1={0}
          y1={0}
          x2={s.x}
          y2={s.y}
          stroke="var(--ink-2)"
          strokeWidth={0.75}
          strokeDasharray={s.dashed ? "3 4" : undefined}
          opacity={s.dashed ? 0.45 : 0.3}
        />
      ))}
      {/* contour */}
      <path
        d={contour}
        fill="none"
        stroke="var(--signal)"
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
        strokeDasharray={hasData ? undefined : "5 6"}
        opacity={hasData ? 1 : 0.55}
      />
      {/* evidence ring */}
      {ring > 1 && (
        <circle cx={0} cy={0} r={ring} fill="none" stroke="var(--ink-2)" strokeWidth={1} opacity={0.5} />
      )}
      {/* orientation tick — reading start (Disposition axis). Not data:
          a compass North. Breaks the hexagon's six-fold symmetry so every
          specimen tilt is visibly distinct. */}
      {isSpecimen && (
        <line
          x1={(R + 7) * Math.cos(tilt - Math.PI / 2)}
          y1={(R + 7) * Math.sin(tilt - Math.PI / 2)}
          x2={(R + 15) * Math.cos(tilt - Math.PI / 2)}
          y2={(R + 15) * Math.sin(tilt - Math.PI / 2)}
          stroke="var(--signal)"
          strokeWidth={2}
        />
      )}
      {/* center seal dot — FILED only. Specimen: hollow. */}
      <circle
        cx={0}
        cy={0}
        r={3}
        fill={hasData ? "var(--signal)" : "none"}
        stroke="var(--signal)"
        strokeWidth={1.5}
        opacity={hasData ? 1 : 0.7}
      />
    </svg>
  );
}
