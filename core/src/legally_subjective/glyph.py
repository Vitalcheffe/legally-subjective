"""LEGALLY SUBJECTIVE — The Glyph (Standard LS-1.0, §5).

Deterministic radial signature. Pure function of (axes, n, docket_id).
No randomness. Ever. Same inputs → bit-identical SVG path.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

R = 100.0  # rayon de référence, unités SVG


def _tilt_degrees(docket_id: str) -> float:
    """Rotation offset: (int(sha256(docket_id), 16) mod 60) − 30 degrés."""
    digest = hashlib.sha256(docket_id.encode("utf-8")).hexdigest()
    return float((int(digest, 16) % 60) - 30)


def _catmull_rom(points: list[tuple[float, float]], samples: int = 24) -> str:
    """Contour fermé Catmull-Rom → path SVG lissé."""
    n = len(points)
    if n < 3:
        raise ValueError("glyph requires at least 3 spokes")
    path: list[str] = []
    for i in range(n):
        p0 = points[(i - 1) % n]
        p1 = points[i]
        p2 = points[(i + 1) % n]
        p3 = points[(i + 2) % n]
        for j in range(samples):
            t = j / samples
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            path.append(f"L{x:.2f},{y:.2f}" if path else f"M{x:.2f},{y:.2f}")
    return " ".join(path) + " Z"


AXIS_ORDER = ("disposition", "temperament", "precedent", "reversal", "orality", "exposure")


@dataclass(frozen=True)
class Glyph:
    """The Subjectivity Fingerprint glyph — SVG-ready, print-safe."""

    docket_id: str
    axes: dict[str, int | None]  # percentile 0–99, ou None si insufficient-data
    n: int
    max_n: int = 10_000

    def spokes(self) -> list[tuple[float, float, bool]]:
        tilt = math.radians(_tilt_degrees(self.docket_id))
        out = []
        for i, axis in enumerate(AXIS_ORDER):
            angle = tilt + i * (2 * math.pi / len(AXIS_ORDER)) - math.pi / 2
            value = self.axes.get(axis)
            if value is None:
                out.append((0.0, 0.0, True))  # rayon 0 + dashed
                continue
            r = (value / 100.0) * R
            out.append((r * math.cos(angle), r * math.sin(angle), False))
        return out

    def path(self) -> str:
        solid = [(x, y) for x, y, dashed in self.spokes() if not dashed]
        return _catmull_rom(solid if len(solid) >= 3 else [(x, y) for x, y, _ in self.spokes()])

    def inner_ring_radius(self) -> float:
        """Le poids de la preuve, visible : log10(n)/log10(max_n) · R/3."""
        if self.n <= 0:
            return 0.0
        return (math.log10(self.n) / math.log10(self.max_n)) * (R / 3.0)

    def svg(self) -> str:
        """SVG autonome, encre sur papier, monochrome-compatible."""
        ring = self.inner_ring_radius()
        return (
            f'<svg viewBox="{-R-12} {-R-12} {2*R+24} {2*R+24}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="Subjectivity Fingerprint {self.docket_id}">'
            f'<path d="{self.path()}" fill="none" stroke="var(--seal)" stroke-width="2.5" stroke-linejoin="round"/>'
            f'<circle cx="0" cy="0" r="{ring:.2f}" fill="none" stroke="var(--ink-2)" stroke-width="1" opacity="0.5"/>'
            f'<circle cx="0" cy="0" r="3" fill="var(--seal)"/>'
            f"</svg>"
        )
