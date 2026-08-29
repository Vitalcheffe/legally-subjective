# -*- coding: utf-8 -*-
"""LS-EXHIBIT-1.2 — the two-file adaptive SVG engine.

Renders exhibit-grade SVG charts for GitHub READMEs:

* **No background** — the SVG is transparent; it lives on whatever paper
  the reader has (GitHub light, GitHub dark, a printed PDF).
* **Two faces, two files, one <picture>** — each exhibit is written twice:
  ``name.light.svg`` (dark ink, for light papers) and ``name.dark.svg``
  (light ink, for dark papers). The README picks the face with

    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="…dark.svg">
      <img src="…light.svg" alt="…" width="100%">
    </picture>

  so **the page** — github.com, which knows the reader's theme — chooses
  the file. Why not one file with an internal `prefers-color-scheme`
  media query? Because GitHub serves README images through its camo
  proxy inside an ``<img>`` context, and an SVG rendered as an image is
  an isolated document: its internal media query does **not** follow the
  page's color scheme (measured in the field, 2026-08-29: the dark face
  never fired on GitHub; ink #0a0a0a on GitHub dark #0d1117 — invisible
  text). The ``<picture>`` mechanism is the one GitHub itself documents.
* **No CSS variables, no media queries** — every face is a fixed,
  statically-resolved palette baked into a plain ``<style>`` block, so the
  file renders identically in every SVG consumer (browser, camo, cairosvg,
  resvg, print pipelines).
* **No page chrome** — no kicker, no title, no footer stamp. The README
  supplies the words; the exhibit supplies the graphic. Everything that
  remains is centered, with generous empty margins on all four sides.
* **Text as paths** — every string is shaped with HarfBuzz and drawn as
  SVG paths (uharfbuzz + fontTools), so the typography (Space Grotesk /
  IBM Plex Mono, SIL OFL) renders identically everywhere, with zero
  font dependency, zero CSP risk, zero fallback drift.

Design tokens follow docs/10-VISUAL-GUIDE.md (LS-EXHIBIT-1.0, amended
1.1 and 1.2): one ink, one signal red, 1px rules, no radius, no shadow,
no gradient. Every text token is held at WCAG AA (>= 4.5:1) against its
target paper — light face against #ffffff, dark face against #0d1117
(GitHub dark); matrix numerals against their own cell fill.
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

# The two faces. Targets: GitHub light paper #ffffff / GitHub dark paper
# #0d1117. Amendment 1.2 lifts the tertiary ink and the light hairline to
# WCAG AA (see docs/10-VISUAL-GUIDE.md §VII): ink3 light #8c8c8c -> #6e7379
# (3.4:1 -> 4.8:1), ink3 dark #6e7681 -> #768390 (4.1:1 -> 4.9:1), hair
# light #e3e3e3 -> #d0d7de (GitHub's own border token, closer to the dark
# face's 1.6:1), dark matrix m4 #6e7681 -> #768390 so the in-cell numeral
# clears AA against its own fill. Signal red keeps its perceptual weight
# per face: #e4002b on white (4.9:1) -> #ff4d6a on #0d1117 (5.9:1).
PALETTES = {
    "light": dict(
        ink="#0a0a0a", ink2="#595959", ink3="#6e7379", hair="#d0d7de",
        d1="#0a0a0a", d2="#404040", d3="#737373", d4="#a6a6a6",
        d5="#d4d4d4", sig="#e4002b",
        m5="#0a0a0a", m5t="#ffffff", m4="#404040", m4t="#ffffff",
        m3="#737373", m3t="#ffffff", m2="#a6a6a6", m2t="#0a0a0a",
        m1="#d4d4d4", m1t="#0a0a0a",
    ),
    "dark": dict(
        ink="#e6edf3", ink2="#8b949e", ink3="#768390", hair="#30363d",
        d1="#e6edf3", d2="#c9d1d9", d3="#8b949e", d4="#6e7681",
        d5="#484f58", sig="#ff4d6a",
        m5="#8b949e", m5t="#0d1117", m4="#768390", m4t="#0d1117",
        m3="#484f58", m3t="#e6edf3", m2="#21262d", m2t="#e6edf3",
        m1="#161b22", m1t="#e6edf3",
    ),
}

# tokens a text class may never fail against its paper
PAPER = {"light": "#ffffff", "dark": "#0d1117"}


def style(face):
    """The fixed stylesheet of one face. No vars, no media queries."""
    p = PALETTES[face]
    return """.f-ink{fill:%(ink)s}.f-ink2{fill:%(ink2)s}.f-ink3{fill:%(ink3)s}
.f-sig{fill:%(sig)s}.f-none{fill:none}
.b-ink{fill:%(d1)s}.b-d2{fill:%(d2)s}.b-d3{fill:%(d3)s}
.b-d4{fill:%(d4)s}.b-d5{fill:%(d5)s}.b-sig{fill:%(sig)s}
.s-ink{stroke:%(d1)s;fill:none}.s-hair{stroke:%(hair)s;fill:none}
.s-sig{stroke:%(sig)s;fill:none}
.mc{stroke:%(hair)s;stroke-width:1}
.m5{fill:%(m5)s}.m5t{fill:%(m5t)s}.m4{fill:%(m4)s}.m4t{fill:%(m4t)s}
.m3{fill:%(m3)s}.m3t{fill:%(m3t)s}.m2{fill:%(m2)s}.m2t{fill:%(m2t)s}
.m1{fill:%(m1)s}.m1t{fill:%(m1t)s}
line,path,rect,circle{shape-rendering:geometricPrecision}""" % p


class Svg:
    """A single exhibit document, renderable in either face."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.el = []

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
    def render(self, face="light"):
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
            'role="img">\n<style>\n%s\n</style>\n%s\n</svg>\n'
            % (self.w, self.h, style(face), "\n".join(self.el))
        )

    def save(self, path, face="light"):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.render(face))
        # byte size report
        print("wrote %s  (%.1f KB)" % (path, os.path.getsize(path) / 1024.0))

    def save_both(self, assets_dir, name):
        """Write the exhibit as both faces — name.light.svg + name.dark.svg."""
        self.save(os.path.join(assets_dir, name + ".light.svg"), face="light")
        self.save(os.path.join(assets_dir, name + ".dark.svg"), face="dark")


# ---------------------------------------------------------------- helpers

def wilson_lo_hi(value, ci):
    """value/ci are proportions; returns (lo, hi)."""
    return (value - ci[0], ci[1] - value)
