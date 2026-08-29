#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LS-EXHIBIT-1.1 — regenerate the six README exhibits as adaptive SVGs.

Every exhibit:
  * is a PURE CHART — no page chrome, no title block, no footer stamp;
    the README supplies the words, the exhibit supplies the graphic;
  * has a TRANSPARENT background — it lives on the reader's paper
    (GitHub light or dark), never on a slab of its own;
  * follows the reader's color scheme automatically (CSS variables +
    prefers-color-scheme media query, inside the SVG);
  * is CENTERED with generous empty margins on all four sides;
  * is drawn entirely from the REAL data in this repository (never
    hand-typed), text rendered as paths (no font dependency).

Usage:  python3 scripts/make_exhibits.py
Output: docs/assets/{hero,corpus-window,baselines,sealed,agreement,the-draw}.svg
"""
import hashlib
import json
import math
import os
import re
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from ls_svg import Svg  # noqa: E402

ASSETS = os.path.join(REPO, "docs", "assets")

# ---------------------------------------------------------------- data ----


def load_data():
    d = {}
    with open(os.path.join(REPO, "data", "productions", "cases.json")) as f:
        d["cases"] = json.load(f)["cases"]
    with open(os.path.join(REPO, "data", "processed", "stats_v1.json")) as f:
        d["stats"] = json.load(f)
    with open(os.path.join(REPO, "data", "productions", "agreement.json")) as f:
        d["agreement"] = json.load(f)["pairs"]

    justices = []
    for i in range(1, 14):
        with open(os.path.join(REPO, "data", "dockets", "LS-J-%03d.json" % i)) as f:
            dj = json.load(f)
        disp = dj["axes"]["disposition"]
        toks = [t.strip(",") for t in dj["subject"]["name"].split()]
        toks = [t for t in toks if t.rstrip(".") not in ("Jr", "Sr", "II", "III")]
        last = toks[-1].upper()
        justices.append({
            "docket": dj["docket"],
            "name": dj["subject"]["name"],
            "slug": dj["subject"]["slug"],
            "last": last,
            "value": disp["value"],
            "ci": disp["value_ci95"],
            "n": disp["n"],
        })
    d["justices"] = justices

    # sealed vs open 5-4 (sub-docket aware matching — validated: 29 + 50)
    def nums(s):
        if not isinstance(s, str):
            return set()
        return set(re.findall(r"\d+-\d+", s.replace("–", "-").replace("—", "-")))

    sealed_raw = d["stats"]["five_four_selection"]["cases"]
    sealed_nums = set()
    for s in sealed_raw:
        sealed_nums |= nums(s)
    sealed_norm = {s.strip().rstrip(".").replace("–", "-") for s in sealed_raw}
    f54 = [c for c in d["cases"]
           if c.get("n_maj") == 5 and c.get("n_min") == 4]
    open54, sealed54 = [], []
    for c in f54:
        cd = c["docket"]
        hit = (nums(cd) & sealed_nums) or (cd in sealed_norm) or (cd == "No.142")
        (sealed54 if hit else open54).append(c)
    d["f54"] = f54
    d["open54"], d["sealed54"] = open54, sealed54
    d["by_term"] = dict(sorted(Counter(c["term"] for c in d["cases"]).items()))
    d["f54_by_term"] = dict(sorted(Counter(c["term"] for c in f54).items()))
    with open(os.path.join(REPO, "results", "m2_baselines.json")) as f:
        d["m2"] = json.load(f)
    return d


def last_name(slug):
    return slug.upper()


# ------------------------------------------------------- 1. THE BENCH -----

def exhibit_hero(d):
    W, H = 1560, 900
    s = Svg(W, H)
    js = d["justices"]

    # scale: 25 % .. 85 % over x 360 .. 1220
    X0, X1 = 360.0, 1220.0
    V0, V1 = 25.0, 85.0

    def x(v):
        return X0 + (v - V0) / (V1 - V0) * (X1 - X0)

    top, rh = 92.0, 55.0
    plot_bottom = top + len(js) * rh

    # grid
    for gv in (30, 40, 50, 60, 70, 80):
        s.line(x(gv), top - 26, x(gv), plot_bottom, cls="s-hair", sw=1)
        lab = "%d%%" % gv if gv == 50 else str(gv)
        cls = "f-ink3"
        s.text(x(gv), plot_bottom + 34, lab, font="mono500", size=15,
               cls=cls, anchor="middle")
    # coin-flip reference
    s.line(x(50), top - 26, x(50), plot_bottom, cls="s-ink", sw=1)
    s.text(x(50) + 10, top - 40, "COIN FLIP", font="mono500", size=13,
           cls="f-ink3", tracking=2)

    for i, j in enumerate(js):
        y = top + i * rh + rh / 2
        # row baseline hairline
        s.line(X0 - 330, y + rh / 2 - 4, X1 + 240, y + rh / 2 - 4,
               cls="s-hair", sw=1)
        # docket id + name
        s.text(X0 - 330, y + 4, j["docket"], font="mono400", size=14,
               cls="f-ink3", tracking=1)
        s.text(X0 - 22, y + 5, j["last"], font="mono600", size=17,
               anchor="end", tracking=1)
        # Wilson interval
        lo, hi = j["ci"]
        s.line(x(lo * 100), y, x(hi * 100), y, cls="s-ink", sw=2)
        # caps
        s.line(x(lo * 100), y - 7, x(lo * 100), y + 7, cls="s-ink", sw=2)
        s.line(x(hi * 100), y - 7, x(hi * 100), y + 7, cls="s-ink", sw=2)
        # point estimate
        s.circle(x(j["value"] * 100), y, 5.5, cls="b-ink")
        # value ± half-width · n
        half = max(j["value"] - lo, hi - j["value"])
        txt = "%.1f ±%.1f" % (j["value"] * 100, half * 100)
        s.text(X1 + 26, y + 5, txt, font="mono600", size=17)
        s.text(X1 + 26 + s.text_w(txt, "mono600", 17) + 26, y + 5,
               "· %d" % j["n"], font="mono400", size=15, cls="f-ink3")

    # axis title (chart-internal)
    s.text((X0 + X1) / 2, plot_bottom + 78,
           "PETITIONER-ALIGNMENT RATE — SHARE OF VOTES FAVORING THE PARTY "
           "SEEKING RELIEF, WILSON 95 % INTERVALS",
           font="mono500", size=14, cls="f-ink3", anchor="middle", tracking=2)
    s.save(os.path.join(ASSETS, "hero.svg"))


# -------------------------------------------------- 2. THE CORPUS WINDOW --

def exhibit_corpus(d):
    W, H = 1560, 300
    s = Svg(W, H)
    cases = sorted(d["cases"], key=lambda c: (c["term"], c["docket"]))
    terms = sorted(d["by_term"].keys())

    # group ticks per term with a gap between terms
    gap, tw = 16.0, 2.05
    per = [d["by_term"][t] for t in terms]
    total_w = sum(p * tw for p in per) + gap * (len(terms) - 1)
    x = (W - total_w) / 2.0
    tick_top, tick_h = 96.0, 84.0
    f54_terms = d["f54_by_term"]

    for ti, t in enumerate(terms):
        w = per[ti] * tw
        # term group underline
        s.line(x, tick_top + tick_h + 14, x + w - tw, tick_top + tick_h + 14,
               cls="s-hair", sw=1)
        n54 = f54_terms.get(t, 0)
        s.text(x + w / 2 - tw / 2, tick_top + tick_h + 44, "OT%s" % t,
               font="mono600", size=15, anchor="middle", tracking=1)
        s.text(x + w / 2 - tw / 2, tick_top + tick_h + 66,
               "%d · %d" % (per[ti], n54),
               font="mono400", size=13, cls="f-ink3", anchor="middle")
        # ticks
        for c in [c for c in cases if c["term"] == t]:
            is54 = c.get("n_maj") == 5 and c.get("n_min") == 4
            cls = "b-sig" if is54 else "b-d3"
            s.rect(x, tick_top, tw * 0.62, tick_h, cls=cls)
            x += tw
        x += gap

    # legend — centered under the strip
    ly = tick_top + tick_h + 118
    s.rect(W / 2 - 320, ly - 12, 4, 18, cls="b-d3")
    s.text(W / 2 - 302, ly + 2, "ARGUED CASES — %d" % len(cases),
           font="mono500", size=14, cls="f-ink2", tracking=1.5)
    s.rect(W / 2 + 66, ly - 12, 4, 18, cls="b-sig")
    s.text(W / 2 + 84, ly + 2, "DECIDED 5–4 — %d" % len(d["f54"]),
           font="mono500", size=14, cls="f-ink2", tracking=1.5)
    s.save(os.path.join(ASSETS, "corpus-window.svg"))


# ------------------------------------------------------- 3. THE BAR -------

def exhibit_baselines(d):
    m2 = d["m2"]
    rows = [
        ("B1 · MAJORITY CLASS (LIBERAL PRIOR)",
         m2["B1_majority_class"]["accuracy"],
         m2["B1_majority_class"]["accuracy_ic95"], False),
        ("B4c · PER-JUSTICE IDEOLOGY, CASE LEVEL",
         m2["B4_justice_ideology"]["case_accuracy"],
         m2["B4_justice_ideology"]["case_accuracy_ic95"], False),
        ("B2 · ALWAYS CONSERVATIVE",
         m2["B2_always"]["toujours_conservateur"]["accuracy"],
         m2["B2_always"]["toujours_conservateur"]["ic95"], False),
        ("B3 · ALWAYS REVERSE THE COURT BELOW",
         m2["B3_petitioner_wins"]["accuracy"],
         m2["B3_petitioner_wins"]["ic95"], False),
        ("B4 · PER-JUSTICE IDEOLOGY, VOTE LEVEL",
         m2["B4_justice_ideology"]["vote_accuracy"],
         m2["B4_justice_ideology"]["vote_accuracy_ic95"], True),
    ]
    W, H = 1560, 480
    s = Svg(W, H)
    X0, X1 = 620.0, 1220.0
    V0, V1 = 30.0, 75.0

    def x(v):
        return X0 + (v - V0) / (V1 - V0) * (X1 - X0)

    top, rh = 84.0, 62.0
    plot_bottom = top + len(rows) * rh

    for gv in (40, 50, 60, 70):
        s.line(x(gv), top - 24, x(gv), plot_bottom, cls="s-hair", sw=1)
        s.text(x(gv), plot_bottom + 32, str(gv), font="mono500", size=15,
               cls="f-ink3", anchor="middle")
    s.line(x(50), top - 24, x(50), plot_bottom, cls="s-ink", sw=1)
    s.text(x(50) + 10, top - 38, "COIN FLIP", font="mono500", size=13,
           cls="f-ink3", tracking=2)

    for i, (label, acc, ci, is_sig) in enumerate(rows):
        y = top + i * rh + rh / 2
        s.line(X0 - 600, y + rh / 2 - 4, X1 + 250, y + rh / 2 - 4,
               cls="s-hair", sw=1)
        lab_cls = "f-sig" if is_sig else "f-ink"
        s.text(X0 - 22, y + 5, label, font="mono600", size=16,
               anchor="end", cls=lab_cls, tracking=0.5)
        lo, hi = ci
        cls_l = "s-sig" if is_sig else "s-ink"
        s.line(x(lo * 100), y, x(hi * 100), y, cls=cls_l, sw=2.5)
        s.line(x(lo * 100), y - 8, x(lo * 100), y + 8, cls=cls_l, sw=2.5)
        s.line(x(hi * 100), y - 8, x(hi * 100), y + 8, cls=cls_l, sw=2.5)
        s.circle(x(acc * 100), y, 6, cls=("b-sig" if is_sig else "b-ink"))
        val = "%.1f" % (acc * 100)
        s.text(X1 + 26, y + 6, val, font="mono600", size=19,
               cls=("f-sig" if is_sig else "f-ink"))
        if is_sig:
            s.text(X1 + 26 + s.text_w(val, "mono600", 19) + 22, y + 5,
                   "← THE BAR TO BEAT", font="mono500", size=14,
                   cls="f-sig", tracking=1.5)

    s.text((X0 + X1) / 2, plot_bottom + 76,
           "SHARE OF CORRECT VOTES ON THE TEST WINDOW OT2020–2023, "
           "WILSON 95 % INTERVALS",
           font="mono500", size=14, cls="f-ink3", anchor="middle", tracking=2)
    s.save(os.path.join(ASSETS, "baselines.svg"))


# ------------------------------------------------------- 4. THE LOCK ------

def exhibit_sealed(d):
    cells = sorted(d["f54"], key=lambda c: (c["term"], c["docket"]))
    sealed_ids = {id(c) for c in d["sealed54"]}
    W = 1560
    cols, cw, ch, gx, gy = 10, 118.0, 56.0, 10.0, 10.0
    grid_w = cols * cw + (cols - 1) * gx
    n = len(cells)
    rows = (n + cols - 1) // cols
    top = 84.0
    H = int(top + rows * (ch + gy) + 96)
    s = Svg(W, H)
    x0 = (W - grid_w) / 2.0

    for i, c in enumerate(cells):
        r, col = divmod(i, cols)
        cx = x0 + col * (cw + gx)
        cy = top + r * (ch + gy)
        sealed = id(c) in sealed_ids
        if sealed:
            s.rect(cx, cy, cw, ch, cls="b-sig")
        else:
            s.rect(cx, cy, cw, ch, cls="s-hair", sw=1.2)
            dk = c["docket"]
            fs = 15 if len(dk) <= 12 else 12.5
            s.text(cx + cw / 2, cy + ch / 2 + 5, dk, font="mono500",
                   size=fs, cls="f-ink2", anchor="middle")

    ly = top + rows * (ch + gy) + 30
    # legend, centered
    s.rect(W / 2 - 344, ly - 12, 26, 18, cls="s-hair", sw=1.2)
    s.text(W / 2 - 306, ly + 2, "FILED — %d LEGIBLE" % len(d["open54"]),
           font="mono500", size=14, cls="f-ink2", tracking=1.5)
    s.rect(W / 2 + 66, ly - 12, 26, 18, cls="b-sig")
    s.text(W / 2 + 104, ly + 2,
           "SEALED — %d, SHA-256 FROZEN" % len(d["sealed54"]),
           font="mono500", size=14, cls="f-ink2", tracking=1.5)
    s.save(os.path.join(ASSETS, "sealed.svg"))


# ----------------------------------------------------- 5. THE AGREEMENT ---

MATRIX_STYLE = """.mc{stroke:var(--hair);stroke-width:1}
.m5{fill:#0a0a0a}.m5t{fill:#ffffff}
.m4{fill:#404040}.m4t{fill:#ffffff}
.m3{fill:#737373}.m3t{fill:#ffffff}
.m2{fill:#a6a6a6}.m2t{fill:#0a0a0a}
.m1{fill:#d4d4d4}.m1t{fill:#0a0a0a}
@media (prefers-color-scheme:dark){
.m5{fill:#8b949e}.m5t{fill:#0d1117}
.m4{fill:#6e7681}.m4t{fill:#0d1117}
.m3{fill:#484f58}.m3t{fill:#e6edf3}
.m2{fill:#21262d}.m2t{fill:#e6edf3}
.m1{fill:#161b22}.m1t{fill:#e6edf3}}"""


def exhibit_agreement(d):
    pairs = d["agreement"]
    names = sorted({k.split("|")[0] for k in pairs} |
                   {k.split("|")[1] for k in pairs})

    # data-driven order: mean agreement with the conservative anchor block
    def block_agree(j):
        vals = []
        for other in ("thomas", "alito"):
            if other == j:
                continue
            for k, v in pairs.items():
                a, b = k.split("|")
                if {a, b} == {j, other}:
                    vals.append(v["agree"])
        return sum(vals) / len(vals) if vals else 0.5

    order = sorted(names, key=block_agree, reverse=True)
    pos = {j: i for i, j in enumerate(order)}
    N = len(order)

    W = 1560
    cell, gp = 68.0, 3.0
    grid = N * cell + (N - 1) * gp
    lab_w = 190.0
    x0 = (W - grid) / 2.0 + 60
    top = 128.0
    H = int(top + grid + 118)
    s = Svg(W, H, style_extra=MATRIX_STYLE)

    def bin_cls(v):
        """agreement -> (fill class, text class), contrast-safe in both modes"""
        if v >= 0.90:
            return "m5", "m5t"
        if v >= 0.80:
            return "m4", "m4t"
        if v >= 0.70:
            return "m3", "m3t"
        if v >= 0.60:
            return "m2", "m2t"
        return "m1", "m1t"

    # column labels (rotated -45, reading up-left)
    for j in order:
        cx = x0 + pos[j] * (cell + gp) + cell / 2
        s.text(x0 + pos[j] * (cell + gp) + cell / 2, top - 14,
               j.upper(), font="mono600", size=14, anchor="start",
               cls="f-ink2", tracking=1,
               rotate=(-45, cx, top - 14))
    # row labels
    for j in order:
        y = top + pos[j] * (cell + gp) + cell / 2 + 5
        s.text(x0 - 18, y, j.upper(), font="mono600", size=14,
               anchor="end", cls="f-ink2", tracking=1)

    extremes = []
    for k, v in pairs.items():
        a, b = k.split("|")
        for i, j in ((a, b), (b, a)):
            r, c = pos[i], pos[j]
            cx = x0 + c * (cell + gp)
            cy = top + r * (cell + gp)
            if i == j:
                continue
            fc, tc = bin_cls(v["agree"])
            s.rect(cx, cy, cell, cell, cls=fc + " mc")
            s.text(cx + cell / 2, cy + cell / 2 + 5, "%.0f" % (v["agree"] * 100),
                   font="mono600", size=14.5, cls=tc,
                   anchor="middle")
            extremes.append((v["agree"], k, cx, cy))

    # diagonal — self cells carry no pair
    for j in order:
        p = pos[j]
        s.rect(x0 + p * (cell + gp), top + p * (cell + gp), cell, cell,
               cls="b-ink mc")

    # outline the closest and widest pairs in signal red
    extremes.sort()
    marks = [extremes[0]]  # widest
    marks.append(max(extremes))  # closest
    seen = set()
    for ag, k, cx, cy in marks:
        if k in seen:
            continue
        seen.add(k)
        s.rect(cx - 3, cy - 3, cell + 6, cell + 6, cls="s-sig", sw=3)

    ly = top + grid + 52
    w_id, c_id = extremes[0][1].split("|")
    b_id, _ = max(extremes)[1].split("|")
    legend1 = "OUTLINED — CLOSEST: %s · %s  %.1f%%   WIDEST: %s · %s  %.1f%%" % (
        w_id.upper(), c_id.upper(), extremes[0][0] * 100,
        b_id.upper(), max(extremes)[1].split("|")[1].upper(),
        max(extremes)[0] * 100)
    s.text(W / 2, ly, legend1, font="mono500", size=15, cls="f-ink2",
           anchor="middle", tracking=1)
    s.text(W / 2, ly + 30,
           "VOTE-LEVEL AGREEMENT ON COMMON CASES, n ≥ 50 — ORDERED BY MEAN "
           "AGREEMENT WITH THE CONSERVATIVE BLOCK",
           font="mono500", size=13, cls="f-ink3", anchor="middle", tracking=1.5)
    s.save(os.path.join(ASSETS, "agreement.svg"))


# -------------------------------------------------------- 6. THE DRAW -----

def exhibit_draw(d):
    js = d["justices"]
    # deterministic, documented draw
    seed_hex = hashlib.sha256(
        b"LS-EXHIBIT-1.1|THE-DRAW|bench-13").hexdigest()
    seed = int(seed_hex[:8], 16)
    rng = random.Random(seed)
    idx = rng.randrange(len(js))
    winner = js[idx]

    W, H = 1560, 1080
    s = Svg(W, H)
    cx, cy = W / 2, 560.0
    R, r_in = 380.0, 258.0
    n = len(js)
    seg = 2 * math.pi / n

    # wheel segments
    for i in range(n):
        a0 = -math.pi / 2 + i * seg
        a1 = a0 + seg
        x0, y0 = cx + R * math.cos(a0), cy + R * math.sin(a0)
        x1, y1 = cx + R * math.cos(a1), cy + R * math.sin(a1)
        x2, y2 = cx + r_in * math.cos(a1), cy + r_in * math.sin(a1)
        x3, y3 = cx + r_in * math.cos(a0), cy + r_in * math.sin(a0)
        if i == idx:
            s.raw('<path class="b-sig" d="M %.3f %.3f A %.3f %.3f 0 0 1 '
                  '%.3f %.3f L %.3f %.3f A %.3f %.3f 0 0 0 %.3f %.3f Z"/>'
                  % (x0, y0, R, R, x1, y1, x2, y2, r_in, r_in, x3, y3))
        else:
            s.raw('<path class="f-none s-hair" stroke-width="1" d="M %.3f '
                  '%.3f A %.3f %.3f 0 0 1 %.3f %.3f L %.3f %.3f A %.3f '
                  '%.3f 0 0 0 %.3f %.3f Z"/>'
                  % (x0, y0, R, R, x1, y1, x2, y2, r_in, r_in, x3, y3))
    # spokes
    for i in range(n):
        a0 = -math.pi / 2 + i * seg
        s.line(cx + r_in * math.cos(a0), cy + r_in * math.sin(a0),
               cx + R * math.cos(a0), cy + R * math.sin(a0), cls="s-hair", sw=1)

    # names radiating outside
    for i, j in enumerate(js):
        am = -math.pi / 2 + (i + 0.5) * seg
        nx = cx + (R + 44) * math.cos(am)
        ny = cy + (R + 44) * math.sin(am)
        ang = math.degrees(am)
        if ang > 90 or ang < -90:
            ang += 180
        cls = "f-sig" if i == idx else "f-ink"
        fnt = "mono600" if i == idx else "mono500"
        s.text(nx, ny, j["last"], font=fnt, size=17, cls=cls,
               anchor="middle", tracking=2, rotate=(ang, nx, ny))

    # center receipt
    s.text(cx, cy - 58, "YOU DREW", font="mono500", size=15, cls="f-ink3",
           anchor="middle", tracking=6)
    s.text(cx, cy - 6, winner["last"], font="grotesk700", size=54,
           cls="f-sig", anchor="middle")
    half = max(winner["value"] - winner["ci"][0],
               winner["ci"][1] - winner["value"])
    s.line(cx - 90, cy + 28, cx + 90, cy + 28, cls="s-sig", sw=2)
    s.text(cx, cy + 64, "%.0f ±%.0f · %d VOTES" % (winner["value"] * 100,
           half * 100, winner["n"]), font="mono600", size=19,
           anchor="middle")
    s.text(cx, cy + 96, winner["docket"], font="mono400", size=14,
           cls="f-ink3", anchor="middle", tracking=2)

    s.save(os.path.join(ASSETS, "the-draw.svg"))
    print("draw seed: %s -> index %d -> %s" % (seed_hex[:16], idx,
                                               winner["last"]))


# ---------------------------------------------------------------- main ----

if __name__ == "__main__":
    d = load_data()
    exhibit_hero(d)
    exhibit_corpus(d)
    exhibit_baselines(d)
    exhibit_sealed(d)
    exhibit_agreement(d)
    exhibit_draw(d)
    print("all exhibits regenerated")
