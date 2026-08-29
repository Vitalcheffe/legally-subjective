# -*- coding: utf-8 -*-
"""LS-EXHIBIT-1.1 — the adaptive SVG engine.

Renders exhibit-grade SVG charts for GitHub READMEs:

* **No background** — the SVG is transparent; it lives on whatever paper
  the reader has (GitHub light, GitHub dark, a printed PDF).
* **Two faces, one file** — ink colors are CSS variables with a
  `prefers-color-scheme: dark` override, so the exhibit follows the
  reader's dark/light mode automatically.
* **No page chrome** — no kicker, no title, no footer stamp. The README
  supplies the words; the exhibit supplies the graphic. Everything that
  remains is centered, with generous empty margins on all four sides.
* **Text as paths** — every string is shaped with HarfBuzz and drawn as
  SVG paths (uharfbuzz + fontTools), so the typography (Space Grotesk /
  IBM Plex Mono, SIL OFL) renders identically everywhere, with zero
  font dependency, zero CSP risk, zero fallback drift.

Design tokens follow docs/10-VISUAL-GUIDE.md (LS-EXHIBIT-1.0): one ink,
one signal red, 1px rules, no radius, no shadow, no gradient.
"""
import math
import os
import threading

import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

FONTS = {
    # key -> (filename, family for instanced statics)
    "grotesk400": "SpaceGrotesk-400.ttf",
    "grotesk500": "SpaceGrotesk-500.ttf",
    "grotesk700": "SpaceGrotesk-700.ttf",
    "mono400": "IBMPlexMono-Regular.ttf",
    "mono500": "IBMPlexMono-Medium.ttf",
    "mono600": "IBMPlexMono-SemiBold.ttf",
}

_lock = threading.Lock()
_cache = {}      # (key) -> dict(ttfont, face, hbfont, upem, glyphset)
_shaped = {}     # (key, text, size, tracking) -> (path_d, width)


def _load(key):
    with _lock:
        if key in _cache:
            return _cache[key]
        path = os.path.join(FONT_DIR, FONTS[key])
        blob = hb.Blob.from_file_path(path)
        face = hb.Face(blob)
        hbfont = hb.Font(face)
        tt = TTFont(path)
        entry = {
            "tt": tt,
            "hb": hbfont,
            "upem": tt["head"].unitsPerEm,
            "gs": tt.getGlyphSet(),
        }
        _cache[key] = entry
        return entry


def shape(key, text, size, tracking=0.0):
    """Shape `text` at `size` px with optional tracking (px between glyphs).

    Returns (path_d, advance_width) where path_d is a single SVG path
    drawn on the baseline at origin (0, 0), y-up already flipped to SVG
    coordinates (baseline = y 0, ascenders negative y).
    """
    ck = (key, text, size, tracking)
    if ck in _shaped:
        return _shaped[ck]
    if not text:
        return ("", 0.0)
    e = _load(key)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(e["hb"], buf)
    infos, poss = buf.glyph_infos, buf.glyph_positions
    s = size / e["upem"]
    parts = []
    pen_x = 0.0
    for i, (info, pos) in enumerate(zip(infos, poss)):
        if i > 0:
            pen_x += tracking / s  # tracking in px -> font units
        gname = e["tt"].getGlyphName(info.codepoint)
        spen = SVGPathPen(e["gs"])
        tpen = TransformPen(
            spen,
            (s, 0, 0, -s,
             s * (pen_x + pos.x_offset),
             -s * pos.y_offset),
        )
        e["gs"][gname].draw(tpen)
        d = spen.getCommands()
        if d:
            parts.append(d)
        pen_x += pos.x_advance
    width = s * pen_x
    if tracking and len(infos) > 1:
        width -= tracking  # optical width: no trailing gap
    out = (" ".join(parts), width)
    _shaped[ck] = out
    return out


def width(key, text, size, tracking=0.0):
    return shape(key, text, size, tracking)[1]


# ---------------------------------------------------------------- document

STYLE = """:root{--ink:#0a0a0a;--ink2:#595959;--ink3:#8c8c8c;--hair:#e3e3e3;
--d1:#0a0a0a;--d2:#404040;--d3:#737373;--d4:#a6a6a6;--d5:#d4d4d4;--sig:#e4002b}
@media (prefers-color-scheme:dark){:root{--ink:#e6edf3;--ink2:#8b949e;
--ink3:#6e7681;--hair:#30363d;--d1:#e6edf3;--d2:#c9d1d9;--d3:#8b949e;
--d4:#6e7681;--d5:#484f58;--sig:#ff4d6a}}
.f-ink{fill:var(--ink)}.f-ink2{fill:var(--ink2)}.f-ink3{fill:var(--ink3)}
.f-sig{fill:var(--sig)}.f-paper{fill:#ffffff}.f-none{fill:none}
.b-ink{fill:var(--d1)}.b-d2{fill:var(--d2)}.b-d3{fill:var(--d3)}
.b-d4{fill:var(--d4)}.b-d5{fill:var(--d5)}.b-sig{fill:var(--sig)}
.s-ink{stroke:var(--ink);fill:none}.s-hair{stroke:var(--hair);fill:none}
.s-sig{stroke:var(--sig);fill:none}
line,path,rect,circle{shape-rendering:geometricPrecision}"""


class Svg:
    """A single exhibit document."""

    def __init__(self, w, h, style_extra=""):
        self.w, self.h = w, h
        self.el = []
        self.style_extra = style_extra

    # --- primitives -----------------------------------------------------
    def text(self, x, y, s, font="mono400", size=16, cls="f-ink",
             anchor="start", tracking=0.0, rotate=None):
        """Draw text as paths. (x, y) = anchor point on the baseline."""
        s = str(s)
        d, tw = shape(font, s, size, tracking)
        if not d:
            return 0.0
        if anchor == "middle":
            x -= tw / 2.0
        elif anchor == "end":
            x -= tw
        tr = []
        if rotate:
            tr.append("rotate(%.4f %.4f %.4f)" % (rotate[0], rotate[1], rotate[2]))
        tr.append("translate(%.3f %.3f)" % (x, y))
        self.el.append(
            '<path class="%s" transform="%s" d="%s"/>' % (cls, " ".join(tr), d)
        )
        return tw

    def text_w(self, s, font="mono400", size=16, tracking=0.0):
        return width(font, str(s), size, tracking)

    def line(self, x1, y1, x2, y2, cls="s-hair", sw=1):
        self.el.append(
            '<line class="%s" stroke-width="%s" x1="%.3f" y1="%.3f" '
            'x2="%.3f" y2="%.3f"/>' % (cls, sw, x1, y1, x2, y2)
        )

    def rect(self, x, y, w, h, cls="b-ink", sw=None):
        s = '<rect class="%s" x="%.3f" y="%.3f" width="%.3f" height="%.3f"' % (
            cls, x, y, w, h)
        if sw is not None:
            s += ' stroke-width="%s"' % sw
        self.el.append(s + "/>")

    def circle(self, cx, cy, r, cls="b-ink", sw=None):
        s = '<circle class="%s" cx="%.3f" cy="%.3f" r="%.3f"' % (cls, cx, cy, r)
        if sw is not None:
            s += ' stroke-width="%s"' % sw
        self.el.append(s + "/>")

    def group(self, transform, body):
        self.el.append('<g transform="%s">%s</g>' % (transform, body))
        return self

    def raw(self, markup):
        self.el.append(markup)

    # --- output ---------------------------------------------------------
    def render(self):
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
            'role="img">\n<style>\n%s\n%s\n</style>\n%s\n</svg>\n'
            % (self.w, self.h, STYLE, self.style_extra, "\n".join(self.el))
        )

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.render())
        # byte size report
        print("wrote %s  (%.1f KB)" % (path, os.path.getsize(path) / 1024.0))


# ---------------------------------------------------------------- helpers

def wilson_lo_hi(value, ci):
    """value/ci are proportions; returns (lo, hi)."""
    return (value - ci[0], ci[1] - value)
