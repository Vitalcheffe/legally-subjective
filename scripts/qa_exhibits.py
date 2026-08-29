#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LS-EXHIBIT-1.2 QA — prove every exhibit is legible on its paper.

Three gates, all hard failures:

1. STRUCTURAL — each file is one fixed face: the stylesheet must contain
   the face's palette verbatim, and must NOT contain `@media`,
   `prefers-color-scheme`, `var(`, or `f-paper` (a background slab).
   Every class used by an element must exist in the stylesheet.

2. CONTRAST (WCAG 2.1) — the field-measured failure was *text the color
   of the paper*. So text tokens are audited against their paper:
   light face vs #ffffff (GitHub light), dark face vs #0d1117 (GitHub
   dark). Thresholds: text >= 4.5:1; data marks and ink/signal strokes
   >= 3:1; hairlines and the faint matrix bins are reported, not gated
   (decorative rules; the numerals carry the data). Matrix numerals are
   audited against their OWN cell fill, not the paper.

3. RASTER — cairosvg must render every file (renderer-compatibility
   canary: the old var()-based sheets broke non-browser consumers),
   the raster must not be blank, and contact sheets are emitted for
   the VLM art-director pass.

Usage: python3 scripts/qa_exhibits.py
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ls_svg import PALETTES, PAPER  # noqa: E402

ASSETS = os.path.join(os.path.dirname(HERE), "docs", "assets")
SHEETS = os.path.join(os.path.dirname(HERE), "docs", "assets", "qa")
NAMES = ["hero", "corpus-window", "baselines", "sealed", "agreement",
         "the-draw"]

TEXT_CLS = ["f-ink", "f-ink2", "f-ink3", "f-sig"]
MARK_CLS = ["b-ink", "b-d2", "b-d3", "b-sig", "s-ink", "s-sig"]
MTEX = ["m5t", "m4t", "m3t", "m2t", "m1t"]
MFILL = {"m5t": "m5", "m4t": "m4", "m3t": "m3", "m2t": "m2", "m1t": "m1"}


def lum(hexcolor):
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = lin(r), lin(g), lin(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def cls_color(face, cls):
    """Resolve a class to its fill (or stroke for s-*) in a face."""
    p = PALETTES[face]
    if cls.startswith("f-"):
        key = cls[2:]
        return p["ink3"] if key == "ink3" else p[key if key != "ink" else "ink"]
    if cls.startswith("b-"):
        key = cls[2:]
        return p[key if key != "ink" else "d1"]
    if cls.startswith("s-"):
        key = cls[2:]
        return p[key if key != "ink" else "d1"]
    if cls in MFILL or cls in MTEX or cls == "mc":
        return p.get(cls.rstrip("t"), p.get(cls))
    return None


def css_of(svg):
    m = re.search(r"<style>(.*?)</style>", svg, re.S)
    return m.group(1) if m else ""


def rules_of(css):
    out = {}
    for m in re.finditer(r"\.([A-Za-z0-9_-]+)\{([^}]*)\}", css):
        decl = m.group(2)
        fill = re.search(r"fill:\s*(#[0-9a-fA-F]{6}|none)", decl)
        stroke = re.search(r"stroke:\s*(#[0-9a-fA-F]{6})", decl)
        out[m.group(1)] = (fill.group(1) if fill else None,
                           stroke.group(1) if stroke else None)
    return out


def main():
    fails, warns = [], []

    for name in NAMES:
        for face in ("light", "dark"):
            path = os.path.join(ASSETS, "%s.%s.svg" % (name, face))
            if not os.path.exists(path):
                fails.append("MISSING %s" % path)
                continue
            svg = open(path, encoding="utf-8").read()
            css = css_of(svg)
            paper = PAPER[face]
            tag = "%s.%s" % (name, face)

            # --- gate 1: structural ------------------------------------
            for bad in ("@media", "prefers-color-scheme", "var(", "f-paper"):
                if bad in svg:
                    fails.append("%s: contains forbidden %r" % (tag, bad))
            # palette baked in verbatim?
            p = PALETTES[face]
            for key in ("ink", "ink2", "ink3", "hair", "sig"):
                if p[key] not in css:
                    fails.append("%s: token %s=%s not in stylesheet"
                                 % (tag, key, p[key]))
            # every class used by elements must be defined
            defined = set(rules_of(css)) | {"f-none"}
            used = set()
            for m in re.finditer(r'class="([^"]+)"', svg):
                used |= set(m.group(1).split())
            for cls in sorted(used - defined):
                fails.append("%s: element class .%s not defined" % (tag, cls))
            if "viewBox" not in svg:
                fails.append("%s: no viewBox" % tag)

            # --- gate 2: contrast --------------------------------------
            rules = rules_of(css)
            for cls in TEXT_CLS:
                if cls in rules and rules[cls][0]:
                    c = contrast(rules[cls][0], paper)
                    if c < 4.5:
                        fails.append("%s: TEXT .%s %s on paper %s = %.2f:1"
                                     % (tag, cls, rules[cls][0], paper, c))
            for cls in MARK_CLS:
                if cls in rules:
                    col = rules[cls][1] or rules[cls][0]
                    if col and col != "none":
                        c = contrast(col, paper)
                        if c < 3.0:
                            fails.append("%s: MARK .%s %s on paper %s = %.2f:1"
                                         % (tag, cls, col, paper, c))
            # matrix numerals vs their own cell fill
            for tcls in MTEX:
                if tcls in rules and MFILL[tcls] in rules:
                    c = contrast(rules[tcls][0], rules[MFILL[tcls]][0])
                    if c < 4.5:
                        fails.append("%s: CELL .%s on .%s = %.2f:1"
                                     % (tag, tcls, MFILL[tcls], c))
            # report-only: hairline + faint bins
            for cls in ("s-hair", "m1", "m2", "b-d4", "b-d5"):
                if cls in rules:
                    col = rules[cls][1] or rules[cls][0]
                    if col and col != "none":
                        c = contrast(col, paper)
                        warns.append("%s: decor .%s = %.2f:1 on paper"
                                     % (tag, cls, c))

            # --- gate 3: raster ----------------------------------------
            try:
                import cairosvg
                from io import BytesIO
                png = cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                                       background_color=paper,
                                       output_width=1200)
                img_path = os.path.join(SHEETS, "%s.%s.png" % (name, face))
                os.makedirs(SHEETS, exist_ok=True)
                open(img_path, "wb").write(png)
                from PIL import Image
                im = Image.open(BytesIO(png)).convert("RGB")
                # not blank: some pixel must differ from the paper
                pr, pg, pb = (int(paper.lstrip("#")[i:i + 2], 16)
                              for i in (0, 2, 4))
                px = im.getdata()
                n_diff = sum(1 for (r, g, b) in px
                             if abs(r - pr) + abs(g - pg) + abs(b - pb) > 30)
                if n_diff < 5000:
                    fails.append("%s: raster looks blank (%d ink pixels)"
                                 % (tag, n_diff))
                # margin law: ink bounding box keeps breathing room on all
                # four sides (>= 20px at the 1200px raster scale ~= 26
                # viewBox units). Framing is law, not taste. Tolerance of
                # +-2 per channel absorbs cairosvg's background rounding
                # artifact on edge rows/cols of the dark paper.
                def _has_ink(img):
                    for (lo, hi), pv in zip(img.getextrema(), (pr, pg, pb)):
                        if lo < pv - 2 or hi > pv + 2:
                            return True
                    return False

                W_, H_ = im.size
                xmin, xmax, ymin, ymax = W_, -1, H_, -1
                for YY in range(H_):
                    if _has_ink(im.crop((0, YY, W_, YY + 1))):
                        if ymin == H_:
                            ymin = YY
                        ymax = YY
                for XX in range(W_):
                    if _has_ink(im.crop((XX, 0, XX + 1, H_))):
                        if xmin == W_:
                            xmin = XX
                        xmax = XX
                margins = dict(top=ymin, bottom=H_ - 1 - ymax,
                               left=xmin, right=W_ - 1 - xmax)
                for side, m in margins.items():
                    if m < 20:
                        fails.append("%s: margin law violated — %s edge "
                                     "has only %dpx of air (need >=20)"
                                     % (tag, side, m))
            except Exception as e:  # noqa: BLE001
                fails.append("%s: raster failed: %s" % (tag, e))

    # contact sheets for the VLM pass — 2 per face half
    try:
        make_sheets()
    except Exception as e:  # noqa: BLE001
        fails.append("contact sheets failed: %s" % e)

    print("=" * 72)
    for w in warns:
        print("  note  %s" % w)
    print("-" * 72)
    if fails:
        for f in fails:
            print("  FAIL  %s" % f)
        print("%d FAILURES — exhibits NOT fit to file" % len(fails))
        sys.exit(1)
    print("all gates green: structure, WCAG contrast, raster canary")
    print("contact sheets in docs/assets/qa/")
    sys.exit(0)


def make_sheets():
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(SHEETS, exist_ok=True)
    font = ImageFont.truetype(
        os.path.join(HERE, "fonts", "IBMPlexMono-Medium.ttf"), 30)
    halves = [(0, 3), (3, 6)]
    for face in ("light", "dark"):
        paper = PAPER[face]
        pr, pg, pb = (int(paper.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        label_ink = (230, 237, 243) if face == "dark" else (10, 10, 10)
        for hi, (a, b) in enumerate(halves):
            ims = []
            for name in NAMES[a:b]:
                im = Image.open(os.path.join(SHEETS, "%s.%s.png"
                                             % (name, face)))
                ims.append((name, im))
            W = 1200
            LH = 56
            H = sum(im.height + LH + 24 for _, im in ims) + 24
            sheet = Image.new("RGB", (W, H), (pr, pg, pb))
            dr = ImageDraw.Draw(sheet)
            y = 24
            for name, im in ims:
                dr.text((16, y), "// %s.%s.svg" % (name, face),
                        fill=label_ink, font=font)
                y += LH
                sheet.paste(im, ((W - im.width) // 2, y))
                y += im.height + 24
            out = os.path.join(SHEETS, "sheet-%s-%d.png" % (face, hi + 1))
            sheet.save(out, optimize=True)
            print("sheet %s (%dx%d)" % (out, sheet.width, sheet.height))


if __name__ == "__main__":
    main()
