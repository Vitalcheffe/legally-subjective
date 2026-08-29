#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Paper figures — Legally Subjective (M2 + M3a), publication grade.

Generates four vector PDF figures from the frozen corpus and the M2/M3a
results. Style: grayscale ink + one signal red (#e4002b), 300 dpi-safe
vector output, English labels, generous margins, no chartjunk.
"""
import json
import os
import re
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
fm.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FIG = os.path.join(REPO, "paper", "figures")
os.makedirs(FIG, exist_ok=True)

INK = "#0a0a0a"
INK2 = "#595959"
INK3 = "#8c8c8c"
HAIR = "#d9d9d9"
SIG = "#e4002b"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": INK2,
    "axes.linewidth": 0.8,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "figure.dpi": 150,
})


def load():
    d = {}
    with open(os.path.join(REPO, "data", "productions", "cases.json")) as f:
        d["cases"] = json.load(f)["cases"]
    with open(os.path.join(REPO, "data", "productions", "agreement.json")) as f:
        d["pairs"] = json.load(f)["pairs"]
    with open(os.path.join(REPO, "results", "m2_baselines.json")) as f:
        d["m2"] = json.load(f)
    with open(os.path.join(REPO, "results", "m3a_report.json")) as f:
        d["m3a"] = json.load(f)
    with open(os.path.join(REPO, "data", "processed", "stats_v1.json")) as f:
        d["stats"] = json.load(f)

    def nums(s):
        if not isinstance(s, str):
            return set()
        return set(re.findall(r"\d+-\d+", s.replace("–", "-").replace("—", "-")))

    sealed_raw = d["stats"]["five_four_selection"]["cases"]
    sealed_nums = set()
    for s in sealed_raw:
        sealed_nums |= nums(s)
    sealed_norm = {s.strip().rstrip(".").replace("–", "-") for s in sealed_raw}
    d["f54"] = [c for c in d["cases"]
                if c.get("n_maj") == 5 and c.get("n_min") == 4]
    d["by_term"] = dict(sorted(Counter(c["term"] for c in d["cases"]).items()))
    d["f54_by_term"] = dict(sorted(Counter(c["term"] for c in d["f54"]).items()))
    return d


def fig_corpus(d):
    cases = sorted(d["cases"], key=lambda c: (c["term"], c["docket"]))
    terms = sorted(d["by_term"].keys())
    fig, ax = plt.subplots(figsize=(6.9, 2.35), constrained_layout=True)
    gap, tw = 3.0, 0.38
    per = [d["by_term"][t] for t in terms]
    total_w = sum(p * tw for p in per) + gap * (len(terms) - 1)
    x = -total_w / 2
    tick_h = 1.0
    for ti, t in enumerate(terms):
        w = per[ti] * tw
        n54 = d["f54_by_term"].get(t, 0)
        for c in [c for c in cases if c["term"] == t]:
            is54 = c.get("n_maj") == 5 and c.get("n_min") == 4
            ax.bar(x, tick_h, width=tw * 0.62, bottom=0,
                   color=SIG if is54 else INK2, linewidth=0)
            x += tw
        ax.text(x - w / 2 - tw / 2, -0.18, "OT%s" % t, ha="center",
                va="top", fontsize=8, color=INK2)
        ax.text(x - w / 2 - tw / 2, -0.42, "%d · %d" % (per[ti], n54),
                ha="center", va="top", fontsize=7, color=INK3)
        x += gap
    ax.set_xlim(-total_w / 2 - 12, total_w / 2 + 12)
    ax.set_ylim(-1.75, 1.12)
    ax.axis("off")
    # legend — its own line well below the term counts, left-aligned at x = 0
    ly = -1.42
    ax.bar(0, 0.34, width=1.6, bottom=ly, color=INK2, linewidth=0)
    ax.text(2.4, ly + 0.17, "argued case (%d)" % len(cases),
            va="center", fontsize=8, color=INK2)
    ax.bar(26, 0.34, width=1.6, bottom=ly, color=SIG, linewidth=0)
    ax.text(28.4, ly + 0.17, "decided 5\u20134 (%d)" % len(d["f54"]),
            va="center", fontsize=8, color=INK2)
    fig.savefig(os.path.join(FIG, "fig1_corpus.pdf"))
    plt.close(fig)
    print("fig1_corpus.pdf")


def fig_baselines(d):
    m2 = d["m2"]
    rows = [
        ("B1 majority class (liberal)", m2["B1_majority_class"]["accuracy"],
         m2["B1_majority_class"]["accuracy_ic95"]),
        ("B4c per-justice ideology, case",
         m2["B4_justice_ideology"]["case_accuracy"],
         m2["B4_justice_ideology"]["case_accuracy_ic95"]),
        ("B2 always conservative",
         m2["B2_always"]["toujours_conservateur"]["accuracy"],
         m2["B2_always"]["toujours_conservateur"]["ic95"]),
        ("B3 always reverse",
         m2["B3_petitioner_wins"]["accuracy"],
         m2["B3_petitioner_wins"]["ic95"]),
        ("B4 per-justice ideology, vote",
         m2["B4_justice_ideology"]["vote_accuracy"],
         m2["B4_justice_ideology"]["vote_accuracy_ic95"]),
    ]
    fig, ax = plt.subplots(figsize=(6.9, 2.4), constrained_layout=True)
    ys = np.arange(len(rows))[::-1]
    for y, (label, acc, ci) in zip(ys, rows):
        is_sig = label.startswith("B4 per-justice")
        color = SIG if is_sig else INK
        lo, hi = ci[0] * 100, ci[1] * 100
        ax.plot([lo, hi], [y, y], color=color, lw=1.8,
                solid_capstyle="butt", zorder=2)
        ax.plot([lo, lo], [y - 0.16, y + 0.16], color=color, lw=1.8, zorder=2)
        ax.plot([hi, hi], [y - 0.16, y + 0.16], color=color, lw=1.8, zorder=2)
        ax.plot(acc * 100, y, "o", color=color, ms=5, zorder=3)
        ax.text(hi + 1.2, y, "%.1f" % (acc * 100), va="center",
                fontsize=8.5, color=color,
                fontweight="bold" if is_sig else "normal")
    ax.axvline(50, color=HAIR, lw=0.8, zorder=1)
    ax.text(50, len(rows) - 0.35, "coin flip", fontsize=7, color=INK3,
            ha="center", va="bottom")
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    ax.set_xlim(30, 78)
    ax.set_xticks([30, 40, 50, 60, 70])
    ax.set_xticklabels(["%d%%" % v for v in (30, 40, 50, 60, 70)])
    ax.set_xlabel("correct votes on the test window OT2020\u20132023 "
                  "(Wilson 95% CI)", fontsize=8.5)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(left=False)
    fig.savefig(os.path.join(FIG, "fig2_baselines.pdf"))
    plt.close(fig)
    print("fig2_baselines.pdf")


def fig_agreement(d):
    pairs = d["pairs"]
    names = sorted({k.split("|")[0] for k in pairs} |
                   {k.split("|")[1] for k in pairs})

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
    M = np.full((N, N), np.nan)
    for k, v in pairs.items():
        a, b = k.split("|")
        M[pos[a], pos[b]] = v["agree"]
        M[pos[b], pos[a]] = v["agree"]

    fig, ax = plt.subplots(figsize=(6.9, 5.6), constrained_layout=True)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("ink", ["#ffffff", "#0a0a0a"])
    cmap.set_bad("#f2f2f0")
    im = ax.imshow(M, cmap=cmap, vmin=0.5, vmax=1.0, aspect="equal")

    for i in range(N):
        for j in range(N):
            if np.isnan(M[i, j]):
                continue
            v = M[i, j]
            tcol = "white" if v > 0.78 else INK
            ax.text(j, i, "%.0f" % (v * 100), ha="center", va="center",
                    fontsize=7, color=tcol)
    # red outlines for extremes
    lo_k = min(pairs, key=lambda k: pairs[k]["agree"])
    hi_k = max(pairs, key=lambda k: pairs[k]["agree"])
    for k in (lo_k, hi_k):
        a, b = k.split("|")
        for (r, c) in ((pos[a], pos[b]), (pos[b], pos[a])):
            ax.add_patch(plt.Rectangle((c - 0.5, r - 0.5), 1, 1,
                                       fill=False, edgecolor=SIG, lw=2.0))
    ax.set_xticks(range(N))
    ax.set_xticklabels([j.capitalize() for j in order], rotation=45,
                       ha="right", fontsize=8)
    ax.set_yticks(range(N))
    ax.set_yticklabels([j.capitalize() for j in order], fontsize=8)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.62, pad=0.02)
    cb.set_label("vote agreement on common cases (n \u2265 50)", fontsize=8)
    cb.ax.tick_params(labelsize=7.5)
    cb.outline.set_visible(False)
    fig.savefig(os.path.join(FIG, "fig3_agreement.pdf"))
    plt.close(fig)
    print("fig3_agreement.pdf")


def fig_m3a(d):
    m3a = d["m3a"]
    rows = [
        ("M3a-LR additive", m3a["models"]["M3a-LR"]["test_acc_b4_rows"],
         m3a["models"]["M3a-LR"]["test_ic95_b4_rows"],
         m3a["models"]["M3a-LR"]["mcnemar_vs_b4"]["p_exact"]),
        ("M3a-GB boosting", m3a["models"]["M3a-GB"]["test_acc_b4_rows"],
         m3a["models"]["M3a-GB"]["test_ic95_b4_rows"],
         m3a["models"]["M3a-GB"]["mcnemar_vs_b4"]["p_exact"]),
        ("M3a-IX interactions", m3a["models"]["M3a-IX"]["test_acc_b4_rows"],
         m3a["models"]["M3a-IX"]["test_ic95_b4_rows"],
         m3a["models"]["M3a-IX"]["mcnemar_vs_b4"]["p_exact"]),
        ("B4 per-justice ideology", m3a["B4_same_rows"]["acc"],
         m3a["B4_same_rows"]["ic95"], None),
    ]
    fig, ax = plt.subplots(figsize=(6.9, 2.3), constrained_layout=True)
    ys = np.arange(len(rows))[::-1]
    for y, (label, acc, ci, p) in zip(ys, rows):
        is_sig = label.startswith("B4")
        color = SIG if is_sig else INK
        lo, hi = ci[0] * 100, ci[1] * 100
        ax.plot([lo, hi], [y, y], color=color, lw=1.8, zorder=2)
        ax.plot([lo, lo], [y - 0.16, y + 0.16], color=color, lw=1.8)
        ax.plot([hi, hi], [y - 0.16, y + 0.16], color=color, lw=1.8)
        ax.plot(acc * 100, y, "o", color=color, ms=5, zorder=3)
        lab = "%.1f" % (acc * 100)
        if p is not None:
            lab += "  (p = %.3f)" % p
        ax.text(hi + 1.0, y, lab, va="center", fontsize=8, color=color,
                fontweight="bold" if is_sig else "normal")
    ax.axvline(50, color=HAIR, lw=0.8, zorder=1)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    ax.set_xlim(48, 80)
    ax.set_xticks([50, 55, 60, 65, 70])
    ax.set_xticklabels(["%d%%" % v for v in (50, 55, 60, 65, 70)])
    ax.set_xlabel("correct votes on the common rows (n = 1522, sealed "
                  "excluded), Wilson 95% CI \u2014 McNemar exact vs B4",
                  fontsize=8.5)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(left=False)
    fig.savefig(os.path.join(FIG, "fig4_m3a.pdf"))
    plt.close(fig)
    print("fig4_m3a.pdf")


if __name__ == "__main__":
    d = load()
    fig_corpus(d)
    fig_baselines(d)
    fig_agreement(d)
    fig_m3a(d)
    print("all figures -> paper/figures/")
