#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D1-bis paper figures (M4 primary result + E1 + E2 + E3), publication grade.

Five figures for the results section of the manuscript:

  fig5_m4_primary.pdf        Figure 1 - sealed 5-4 exam, conditions A/B/C/D
  fig6_ideological_dial.pdf  Figure 2 - actual vs simulated liberal-vote dial
  fig7_prompt_vs_adapter.pdf Figure 3 - E1 causal decomposition (prompt/adapter)
  fig8_e2_distinctiveness.pdf Figure 4 - E2 stylistic distinctiveness x fidelity
  fig9_e3_autocoherence.pdf  Figure 5 - E3 auto-probe (own liberal lead opinions)

Style: matches scripts/paper_figures.py (grayscale ink + one signal red
#e4002b, DejaVu Sans, vector PDF, English labels, no chartjunk).

DATA PROVENANCE (all frozen, published artifacts):
  - results/m4_report.json          phase S (sealed 50), commit f6145a5
  - results/a1_e1_decomposition.json E1 arms N/P/A, commit e418579 (tag
    a1-freeze lineage); artifact arm "A" (bio prompt + adapter) is
    displayed as "B" because it is byte-identical to M4 condition B;
    arm "N" is the condition-A scheme (neutral, vote replicated).
  - results/a1_e3_autocoherence.json E3 probe, commit e418579
  - docs/15-ASYMETRIE-PHASE1-PREENREGISTREMENT.md section 1.1 (phase-S
    per-seat dial, published) and section 3 (E2 table, frozen)
  - Actual liberal-vote rates on the transparent window (n = 211):
    derived from data/processed/corpus_cases_v1.jsonl.gz joined with
    data/m3/casefiles (window=test); derivation validated EXACTLY
    against the E1 supplements arm-N per-justice accuracies (see
    scripts/d1bis_real_rates_check.py, committed alongside).
    Inter-run rule (docs/16): E1-internal numbers only for arm
    comparisons; phase-T values are quoted as published, never mixed.

Deltas: dPN = prompt effect (P - N), dBP = adapter effect (B - P),
dBN = combined personalization effect (B - N).
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
fm.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FIG = os.path.join(REPO, "paper", "figures")
DL = "/home/z/my-project/download/figures_d1bis"
os.makedirs(FIG, exist_ok=True)
os.makedirs(DL, exist_ok=True)

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
    "legend.frameon": False,
    "legend.fontsize": 7,
})

LIBERALS = {"SSotomayor", "EKagan", "KBJackson"}
DISPLAY = {"CThomas": "Thomas", "SAAlito": "Alito", "JGRoberts": "Roberts",
           "BMKavanaugh": "Kavanaugh", "NMGorsuch": "Gorsuch",
           "SSotomayor": "Sotomayor", "EKagan": "Kagan",
           "ACBarrett": "Barrett", "KBJackson": "Jackson"}

# ---------------------------------------------------------------- data ----
M4 = json.load(open(os.path.join(REPO, "results", "m4_report.json")))
E1 = json.load(open(os.path.join(REPO, "results",
                                 "a1_e1_decomposition.json")))
E3 = json.load(open(os.path.join(REPO, "results", "a1_e3_autocoherence.json")))

# Phase-S per-seat dial, published in docs/15 section 1.1 (frozen):
# {seat: (actual liberal rate, persona B predicted liberal rate, n votes)}
DIAL_S = {
    "CThomas":     (0.163, 0.000, 49),
    "SAAlito":     (0.163, 0.000, 49),
    "BMKavanaugh": (0.308, 0.103, 39),
    "ACBarrett":   (0.200, 0.150, 20),
    "NMGorsuch":   (0.354, 0.042, 48),
    "JGRoberts":   (0.367, 0.000, 49),
    "KBJackson":   (0.778, 0.444, 9),
    "SSotomayor":  (0.857, 0.184, 49),
    "EKagan":      (0.837, 0.041, 49),
}

# Actual per-seat liberal-vote rate on the transparent window (n = 211),
# derived from the frozen corpus (see docstring); validated exactly
# against E1 supplements arm-N accuracies.
REAL_W = {
    "SSotomayor":  0.6716,   # 137/204
    "EKagan":      0.6618,   # 135/204
    "KBJackson":   0.6600,   # 66/100
    "NMGorsuch":   0.4406,   # 89/202
    "ACBarrett":   0.4197,   # 81/193
    "BMKavanaugh": 0.4020,   # 82/204
    "JGRoberts":   0.3971,   # 81/204
    "CThomas":     0.3465,   # 70/202
    "SAAlito":     0.3200,   # 64/200
}
ORDER_W = ["SSotomayor", "EKagan", "KBJackson", "NMGorsuch", "ACBarrett",
           "BMKavanaugh", "JGRoberts", "CThomas", "SAAlito"]

# E1 arm liberal-vote rates (measures, single run, seed 271828, n = 211)
ARM_N = {j: E1["measures"][j]["N"]["rate_liberal"] for j in ORDER_W}
ARM_P = {j: E1["measures"][j]["P"]["rate_liberal"] for j in ORDER_W}
ADAPTED = [j for j in ORDER_W
           if E1["measures"][j].get("A") is not None]
ARM_B = {j: E1["measures"][j]["A"]["rate_liberal"] for j in ADAPTED}

# E2 table, frozen in docs/15 section 3:
# {seat: (distinctiveness z, B_acc phase S, training lines)}
E2 = {
    "EKagan":      (0.24, 0.2041, 50),
    "JGRoberts":   (0.17, 0.6327, 43),
    "BMKavanaugh": (0.11, 0.7436, 21),
    "SSotomayor":  (-0.06, 0.2449, 95),
    "SAAlito":     (-0.07, 0.8367, 83),
    "NMGorsuch":   (-0.08, 0.6875, 39),
    "CThomas":     (-0.32, 0.8367, 146),
}

# E3 probe (real-liberal + lead-authored train cases) and by-real-vote
PROBE = {j: E3["per_judge"][j]["probe_real_liberal_and_lead_author"]
         for j in E3["per_judge"]}
BYRV = {j: E3["per_judge"][j]["by_real_vote"] for j in E3["per_judge"]}

COND_LABELS = ["A\nzero-shot", "B\npersona", "C\nRAG", "D\nprior"]

# ------------------------------------------------------- overlap checker --
from matplotlib.patches import Patch
from matplotlib.text import Annotation, Text
from matplotlib.transforms import Bbox


def _shrink(bb, px=1.5):
    if bb is None or bb.width <= 2 * px + 2 or bb.height <= 2 * px + 2:
        return None
    return Bbox.from_extents(bb.x0 + px, bb.y0 + px, bb.x1 - px, bb.y1 - px)


def check_overlaps(fig, name):
    """Programmatic zero-overlap check: texts x texts, texts x patches,
    legend x everything. Patch x patch is not checked (bars may touch).
    For annotations, only the TEXT bbox is measured (a leader line may
    legitimately pass between two labels without touching them).
    Returns the number of violations (printed in detail)."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    W, H = fig.canvas.get_width_height()
    n_viol = 0
    for ax in fig.axes:
        texts = [t for t in ax.texts if t.get_text().strip()]
        if ax.title.get_text().strip():
            texts.append(ax.title)
        pt = getattr(ax, "_panel_title", None)
        if pt is not None and pt.get_text().strip():
            texts.append(pt)
        for lbl in (ax.xaxis.label, ax.yaxis.label):
            if lbl is not None and lbl.get_text().strip():
                texts.append(lbl)
        # only tick labels whose tick lies inside the view limits
        # (the locator may propose out-of-range ticks that are never drawn)
        xmin, xmax = ax.get_xlim()
        for tick, lbl in zip(ax.get_xticks(), ax.get_xticklabels()):
            if lbl.get_text().strip() and xmin <= tick <= xmax:
                texts.append(lbl)
        ymin, ymax = ax.get_ylim()
        for tick, lbl in zip(ax.get_yticks(), ax.get_yticklabels()):
            if lbl.get_text().strip() and ymin <= tick <= ymax:
                texts.append(lbl)
        items = []
        for t in texts:
            if isinstance(t, Annotation):
                bb = Text.get_window_extent(t, renderer)
            else:
                bb = t.get_window_extent(renderer)
            bb = _shrink(bb)
            if bb is not None:
                items.append(("text:" + t.get_text()[:22].replace("\n", "/"),
                              bb))
        for p in ax.patches:
            bb = _shrink(p.get_window_extent(renderer))
            if bb is not None:
                items.append(("patch", bb))
        leg = ax.get_legend()
        if leg is not None:
            bb = _shrink(leg.get_window_extent(renderer))
            if bb is not None:
                items.append(("legend", bb))
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                (n1, b1), (n2, b2) = items[i], items[j]
                if n1 == "patch" and n2 == "patch":
                    continue  # adjacent grouped bars may touch by design
                if b1.overlaps(b2):
                    n_viol += 1
                    print(f"  !! OVERLAP [{name}] {n1}  <->  {n2}")
        for n, bb in items:
            if bb.x0 < 0 or bb.y0 < 0 or bb.x1 > W or bb.y1 > H:
                n_viol += 1
                print(f"  !! CLIPPED [{name}] {n} bbox={bb.extents} "
                      f"canvas={W}x{H}")
    # cross-axes check: panel titles must not run into the next panel
    ttl = [getattr(ax, "_panel_title", None) for ax in fig.axes]
    ttl = [(ax_i, t) for ax_i, t in enumerate(ttl)
           if t is not None and t.get_text().strip()]
    for i in range(len(ttl)):
        for j in range(i + 1, len(ttl)):
            b1 = ttl[i][1].get_window_extent(renderer)
            b2 = ttl[j][1].get_window_extent(renderer)
            if b1.overlaps(b2):
                n_viol += 1
                print(f"  !! TITLE CROSS-OVERLAP [{name}] "
                      f"panel {ttl[i][0]} <-> panel {ttl[j][0]}")
    return n_viol


def save_fig(fig, stem, checks=True):
    n_viol = check_overlaps(fig, stem) if checks else 0
    pdf = os.path.join(FIG, stem + ".pdf")
    png = os.path.join(DL, stem + ".png")
    fig.savefig(pdf, facecolor="white")
    fig.savefig(png, dpi=300, facecolor="white")
    plt.close(fig)
    kb = os.path.getsize(pdf) / 1024
    tag = "OK " if n_viol == 0 else f"{n_viol} OVERLAP(S)"
    print(f"  [{tag}] {stem}.pdf ({kb:.0f} KB) + {stem}.png")
    return n_viol


def panel_title(ax, s):
    t = ax.set_title(s, loc="left", fontsize=9, fontweight="bold", pad=7)
    ax._panel_title = t  # loc='left' titles are NOT in ax.title
    return t


def marker_of(ax, seat, color=INK, filled=None, ms=5.2, zorder=5):
    """Filled marker for liberal seats, open for conservative seats."""
    if filled is None:
        filled = seat in LIBERALS
    ax.plot([], [], marker="o", ms=ms, mew=1.0,
            mfc=color if filled else "white", mec=color, zorder=zorder)

# ---------------------------------------------------------------- fig 5 ---
def fig5_m4_primary():
    """Figure 1 - primary result on the sealed 5-4 exam."""
    conds = ["A", "B", "C", "D"]
    mc = M4["mcnemar_B_vs_A"]
    fig = plt.figure(figsize=(7.2, 2.6), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.05, 1.25],
                          wspace=0.08)

    def cond_data(c, key):
        d = M4["conditions"][c]
        return (d[key]["accuracy"], d[key]["k"], d[key]["n"],
                d[key]["ic95"])

    def draw_bars(ax, key, title, mc_l1, mc_l2, mc_y):
        accs, ks, ns, los, his = [], [], [], [], []
        for c in conds:
            a, k, n, (lo, hi) = cond_data(c, key)
            accs.append(a); ks.append(k); ns.append(n)
            los.append(a - lo); his.append(hi - a)
        x = np.arange(4)
        colors = [INK2, SIG, INK3, "white"]
        for i, c in enumerate(conds):
            if c == "D":
                ax.bar(x[i], accs[i], width=0.62, facecolor="white",
                       edgecolor=INK2, linewidth=1.1, zorder=3)
            else:
                ax.bar(x[i], accs[i], width=0.62, color=colors[i],
                       linewidth=0, zorder=3)
        ax.errorbar(x, accs, yerr=[los, his], fmt="none", ecolor=INK,
                    elinewidth=1.0, capsize=3.2, capthick=1.0, zorder=4)
        for i in range(4):
            ax.text(x[i], accs[i] + his[i] + 0.028, f"{accs[i]*100:.1f}",
                    ha="center", va="bottom", fontsize=8,
                    fontweight="bold" if conds[i] == "B" else "normal",
                    color=INK if conds[i] != "B" else SIG, zorder=6)
        labels = [COND_LABELS[i].split("\n")[0] +
                  "\n" + COND_LABELS[i].split("\n")[1] +
                  f"\n{ks[i]}/{ns[i]}" for i in range(4)]
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_ylim(0, 1.15)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["0", ".25", ".50", ".75", "1.0"],
                           fontsize=7.5)
        # McNemar bracket between A and B + compact two-line note
        ax.plot([0, 0, 1, 1], [mc_y - 0.016, mc_y, mc_y, mc_y - 0.016],
                color=INK2, lw=0.8, zorder=5)
        ax.text(0.72, mc_y + 0.024, mc_l1 + "\n" + mc_l2, ha="center",
                va="bottom", fontsize=6.6, color=INK2, zorder=6,
                linespacing=1.45)
        panel_title(ax, title)

    ax = fig.add_subplot(gs[0])
    draw_bars(ax, "case_direction",
              "(a) Case direction (sealed)",
              "B vs A (primary)",
              f"b={mc['case_direction']['b']}, c={mc['case_direction']['c']}"
              f" - p = {mc['case_direction']['p_value']:.2f}",
              0.90)
    ax.set_ylabel("accuracy")

    ax = fig.add_subplot(gs[1])
    draw_bars(ax, "votes",
              "(b) Vote accuracy (sealed)",
              "B vs A (secondary)",
              f"b={mc['vote']['b']}, c={mc['vote']['c']}"
              f" - p = {mc['vote']['p_value']:.3f}",
              0.92)

    # (c) ECE, case-level (vote-level values quoted in the caption:
    # A .226 / B .169 / C .137 / D .094)
    ax = fig.add_subplot(gs[2])
    x = np.arange(4)
    ece_case = [M4["conditions"][c]["calibration"]["case_level"]["ece"]
                for c in conds]
    for i, c in enumerate(conds):
        if c == "D":
            ax.bar(x[i], ece_case[i], width=0.62, facecolor="white",
                   edgecolor=INK2, linewidth=1.1, zorder=3)
        else:
            ax.bar(x[i], ece_case[i], width=0.62,
                   color=[INK2, SIG, INK3][i], linewidth=0, zorder=3)
        ax.text(x[i], ece_case[i] + 0.008, f"{ece_case[i]:.3f}",
                ha="center", va="bottom", fontsize=7.2,
                color=SIG if c == "B" else INK2,
                fontweight="bold" if c == "B" else "normal", zorder=6)
    ax.set_xticks(x)
    ax.set_xticklabels([l.split("\n")[0] for l in COND_LABELS], fontsize=7.5)
    ax.set_ylim(0, 0.26)
    ax.set_yticks([0, 0.1, 0.2])
    ax.set_yticklabels(["0", ".1", ".2"], fontsize=7.5)
    ax.set_ylabel("ECE (case level)")
    ax.text(0.03, 0.97, "lower is better", transform=ax.transAxes,
            ha="left", va="top", fontsize=6.8, color=INK3, style="italic")
    panel_title(ax, "(c) Calibration error (ECE)")
    return save_fig(fig, "fig5_m4_primary")


# ---------------------------------------------------------------- fig 6 ---
def fig6_ideological_dial():
    """Figure 2 - the ideological dial: sealed scatter + window chain."""
    fig = plt.figure(figsize=(6.9, 3.4), constrained_layout=True)
    fig.get_layout_engine().set(rect=(0, 0.115, 1, 0.885))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.38], wspace=0.06)

    # (a) sealed exam scatter: actual vs persona-predicted liberal rate
    ax = fig.add_subplot(gs[0])
    ax.plot([0, 0.95], [0, 0.95], ls=(0, (4, 3)), lw=0.9, color=INK3,
            zorder=2)
    ax.text(0.845, 0.845, "y = x", rotation=45, fontsize=6.5, color=INK3,
            ha="center", va="bottom")
    offsets = {
        "CThomas": (0.034, 0.026, "left", "bottom"),
        "SAAlito": (-0.034, 0.026, "right", "bottom"),
        "BMKavanaugh": (0.0, 0.062, "center", "bottom"),
        "ACBarrett": (-0.034, 0.0, "right", "center"),
        "JGRoberts": (0.034, 0.018, "left", "bottom"),
        "KBJackson": (-0.034, 0.0, "right", "center"),
        "SSotomayor": (-0.034, 0.0, "right", "center"),
        "EKagan": (-0.034, 0.0, "right", "center"),
    }
    for seat, (real, pred, n) in DIAL_S.items():
        lib = seat in LIBERALS
        ax.plot(real, pred, marker="o",
                ms=6.5 if lib else 5.4, mew=1.1,
                mfc=INK if lib else "white", mec=INK if lib else INK2,
                zorder=5)
        if seat == "NMGorsuch":
            # crowded cluster: thin leader line to the free mid-right zone
            ax.annotate("Gorsuch", xy=(real, pred), xycoords="data",
                        xytext=(0.47, 0.115), textcoords="data",
                        ha="left", va="center", fontsize=7, color=INK2,
                        zorder=6,
                        arrowprops=dict(arrowstyle="-", color=INK3,
                                        lw=0.7, shrinkA=0, shrinkB=5.0))
            continue
        dx, dy, ha, va = offsets[seat]
        lbl = DISPLAY[seat] + (" (n=9)" if seat == "KBJackson" else "")
        ax.text(real + dx, pred + dy, lbl, ha=ha, va=va, fontsize=7,
                color=INK if lib else INK2,
                fontweight="bold" if seat in ("EKagan", "SSotomayor")
                else "normal", zorder=6)
    ax.text(0.03, 0.965, "all nine seats vote more\nconservatively than reality",
            transform=ax.transAxes, ha="left", va="top", fontsize=7,
            color=INK2, style="italic")
    ax.set_xlim(0, 0.95)
    ax.set_ylim(0, 0.95)
    ax.set_xlabel("actual liberal-vote rate")
    ax.set_ylabel("persona B liberal-vote rate")
    ax.set_xticks([0, 0.25, 0.5, 0.75])
    ax.set_yticks([0, 0.25, 0.5, 0.75])
    panel_title(ax, "(a) Sealed exam (n = 49-50)")

    # (b) transparent window: the chain real -> N -> P -> B per seat
    ax = fig.add_subplot(gs[1])
    ypos = {s: 8 - i for i, s in enumerate(ORDER_W)}
    for seat in ORDER_W:
        y = ypos[seat]
        real, n_, p_, b_ = REAL_W[seat], ARM_N[seat], ARM_P[seat], None
        xs = [real, n_, p_]
        b_exists = seat in ARM_B
        if b_exists:
            xs.append(ARM_B[seat])
        ax.plot([real] + xs[1:], [y] * (1 + len(xs[1:])), ls=(0, (1, 2)),
                color=HAIR, lw=0.9, zorder=2)
        ax.plot(real, y, marker="D", ms=6.0, mfc=INK, mec=INK, zorder=5)
        ax.plot(n_, y, marker="o", ms=5.0, mfc="white", mec=INK3, mew=1.1,
                zorder=4)
        ax.plot(p_, y, marker="^", ms=5.6, mfc=INK2, mec=INK2, zorder=4)
        if b_exists:
            ax.plot(ARM_B[seat], y, marker="s", ms=5.2, mfc=SIG, mec=SIG,
                    zorder=6)
        else:  # degraded seats: persona arm = biographical prompt
            ax.plot(p_, y, marker="s", ms=5.2, mfc="white", mec=SIG,
                    mew=1.2, zorder=6)
    ax.set_yticks([ypos[s] for s in ORDER_W])
    ax.set_yticklabels([DISPLAY[s] + (" *" if s not in ARM_B else "")
                        for s in ORDER_W], fontsize=7.5)
    for tick, seat in zip(ax.get_yticklabels(), ORDER_W):
        if seat in LIBERALS:
            tick.set_color(INK)
        else:
            tick.set_color(INK2)
    ax.set_xlim(0, 0.74)
    ax.set_ylim(-0.7, 8.8)
    ax.set_xticks([0, 0.25, 0.5])
    ax.xaxis.grid(True, alpha=0.10, color=INK3)
    ax.set_axisbelow(True)
    handles = [
        plt.Line2D([], [], marker="D", ms=5.5, mfc=INK, mec=INK, ls=""),
        plt.Line2D([], [], marker="o", ms=4.8, mfc="white", mec=INK3,
                   mew=1.1, ls=""),
        plt.Line2D([], [], marker="^", ms=5.4, mfc=INK2, mec=INK2, ls=""),
        plt.Line2D([], [], marker="s", ms=4.8, mfc=SIG, mec=SIG, ls=""),
    ]
    ax.legend(handles, ["actual record", "N - neutral (= cond. A)",
                        "P - bio prompt only", "B - persona (= cond. B)"],
              loc="upper center", bbox_to_anchor=(0.5, -0.075), ncol=2,
              columnspacing=1.1, handlelength=1.4)
    ax.text(0.5, -0.335, "* no adapter trained: persona arm = biographical "
            "prompt (degraded mode)", transform=ax.transAxes, ha="center",
            va="top", fontsize=6.4, color=INK3)
    panel_title(ax, "(b) Transparent window: liberal-vote rate")
    return save_fig(fig, "fig6_ideological_dial")

# ---------------------------------------------------------------- fig 7 ---
def fig7_prompt_vs_adapter():
    """Figure 3 - E1 causal decomposition of the dial."""
    fig = plt.figure(figsize=(6.9, 3.1), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, wspace=0.06)
    ypos = {s: 8 - i for i, s in enumerate(ORDER_W)}

    def dot_panel(ax, values, title, note, xlim, na_seats=()):
        ax.axvline(0, color=INK2, lw=0.9, zorder=2)
        for seat, v in values.items():
            y = ypos[seat]
            ax.plot([0, v], [y, y], color=HAIR, lw=1.1, zorder=3)
            lib = seat in LIBERALS
            is_kagan = seat == "EKagan"
            ax.plot(v, y, marker="o", ms=5.6 if not is_kagan else 6.2,
                    mew=1.1,
                    mfc=SIG if is_kagan else (INK if lib else "white"),
                    mec=SIG if is_kagan else (INK if lib else INK2),
                    zorder=5)
        for seat in na_seats:
            ax.text(0.012, ypos[seat], "no adapter", va="center", ha="left",
                    fontsize=6.2, color=INK3, style="italic")
        ax.set_xlim(*xlim)
        ax.set_ylim(-0.7, 9.7)
        ax.set_yticks([ypos[s] for s in ORDER_W])
        ax.set_yticklabels([DISPLAY[s] for s in ORDER_W], fontsize=7.5)
        for tick, seat in zip(ax.get_yticklabels(), ORDER_W):
            tick.set_color(SIG if seat == "EKagan" else
                           (INK if seat in LIBERALS else INK2))
        ax.xaxis.grid(True, alpha=0.10, color=INK3)
        ax.set_axisbelow(True)
        ax.set_xlabel("Δ liberal-vote rate", fontsize=8)
        if note:
            ax.text(0.035, 0.985, note, transform=ax.transAxes, ha="left",
                    va="top", fontsize=6.6, color=INK2, linespacing=1.5)
        panel_title(ax, title)

    dPN = {s: E1["measures"][s]["delta_P_minus_N"]["rate_liberal"]
           for s in ORDER_W}
    dBP = {s: E1["measures"][s]["delta_A_minus_P"]["rate_liberal"]
           for s in ADAPTED}
    dBN = {s: (E1["measures"][s]["A"]["rate_liberal"] -
               E1["measures"][s]["N"]["rate_liberal"])
           for s in ADAPTED}
    # prompt-only seats: combined effect = prompt effect
    for s in ORDER_W:
        if s not in dBN:
            dBN[s] = dPN[s]

    ax = fig.add_subplot(gs[0])
    dot_panel(ax, dPN, "(a) Prompt effect",
              "(ii) pre-registered prediction\n"
              "Sotomayor +.39 holds; Kagan -.06 falsified", (-0.17, 0.46))
    ax = fig.add_subplot(gs[1])
    dot_panel(ax, dBP, "(b) Adapter effect",
              "(iii) pre-registered - confirmed\n"
              "Kagan -.028, Sotomayor -.014", (-0.055, 0.135),
              na_seats=("ACBarrett", "KBJackson"))
    ax = fig.add_subplot(gs[2])
    # combined: open markers for prompt-only seats
    ax.axvline(0, color=INK2, lw=0.9, zorder=2)
    for seat in ORDER_W:
        y = ypos[seat]
        v = dBN[seat]
        prompt_only = seat not in ADAPTED
        ax.plot([0, v], [y, y], color=HAIR, lw=1.1, zorder=3)
        lib = seat in LIBERALS
        is_kagan = seat == "EKagan"
        ax.plot(v, y, marker="o", ms=6.2 if is_kagan else 5.6, mew=1.1,
                mfc=SIG if is_kagan else (INK if lib else "white"),
                mec=SIG if is_kagan else
                (INK if (lib or prompt_only) else INK2),
                zorder=5)
    ax.text(0.97, 0.985, "open markers = prompt-only seats",
            transform=ax.transAxes, ha="right", va="top", fontsize=6.6,
            color=INK2)
    ax.set_xlim(-0.17, 0.46)
    ax.set_ylim(-0.7, 9.7)
    ax.set_yticks([ypos[s] for s in ORDER_W])
    ax.set_yticklabels([])
    ax.xaxis.grid(True, alpha=0.10, color=INK3)
    ax.set_axisbelow(True)
    ax.set_xlabel("Δ liberal-vote rate", fontsize=8)
    panel_title(ax, "(c) Combined effect")
    return save_fig(fig, "fig7_prompt_vs_adapter")


# ---------------------------------------------------------------- fig 8 ---
def fig8_e2_distinctiveness():
    """Figure 4 - E2: stylistic distinctiveness x persona fidelity."""
    fig = plt.figure(figsize=(6.9, 3.1), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, wspace=0.10)

    # (a) distinctiveness (z) vs persona fidelity
    ax = fig.add_subplot(gs[0])
    xs = [v[0] for v in E2.values()]
    ys = [v[1] for v in E2.values()]
    z = np.polyfit(xs, ys, 1)
    xl = np.linspace(-0.40, 0.32, 50)
    ax.plot(xl, np.poly1d(z)(xl), ls=(0, (4, 3)), lw=1.1, color=SIG,
            zorder=3)
    off = {"EKagan": (0.024, 0.0, "left"), "JGRoberts": (0.014, 0.0, "left"),
           "BMKavanaugh": (0.014, 0.0, "left"),
           "SSotomayor": (0.014, 0.0, "left"),
           "SAAlito": (-0.016, 0.0, "right"),
           "NMGorsuch": (0.014, 0.0, "left"),
           "CThomas": (0.014, 0.0, "left")}
    for seat, (x, y, _) in E2.items():
        is_kagan = seat == "EKagan"
        ax.plot(x, y, marker="o", ms=6.2 if is_kagan else 5.4, mew=1.1,
                mfc=SIG if is_kagan else INK,
                mec=SIG if is_kagan else INK, zorder=5)
        dx, dy, ha = off[seat]
        ax.text(x + dx, y + dy, DISPLAY[seat], ha=ha, va="center",
                fontsize=7,
                color=SIG if is_kagan else INK2,
                fontweight="bold" if is_kagan else "normal", zorder=6)
    ax.text(0.04, 0.05,
            "pre-registered: ρ > 0\n"
            "observed: ρ = -0.72 (n = 7)\n"
            "prediction FALSIFIED",
            transform=ax.transAxes, ha="left", va="bottom", fontsize=6.2,
            color=INK2, linespacing=1.5,
            bbox=dict(facecolor="white", edgecolor=HAIR, linewidth=0.8,
                      boxstyle="round,pad=0.28"))
    ax.set_xlim(-0.45, 0.35)
    ax.set_ylim(0.10, 0.95)
    ax.set_xlabel("stylistic distinctiveness (composite z)")
    ax.set_ylabel("persona vote fidelity (B, phase S)")
    panel_title(ax, "(a) Distinctiveness x fidelity")

    # (b) training volume vs persona fidelity
    ax = fig.add_subplot(gs[1])
    xs = [v[2] for v in E2.values()]
    ys = [v[1] for v in E2.values()]
    z = np.polyfit(xs, ys, 1)
    xl = np.linspace(15, 155, 50)
    ax.plot(xl, np.poly1d(z)(xl), ls=(0, (4, 3)), lw=1.1, color=INK3,
            zorder=3)
    off = {"EKagan": (4, 0.0, "left"), "JGRoberts": (-4, 0.0, "right"),
           "BMKavanaugh": (4, 0.0, "left"), "SSotomayor": (4, 0.0, "left"),
           "SAAlito": (4, 0.0, "left"), "NMGorsuch": (4, 0.0, "left"),
           "CThomas": (-4, 0.0, "right")}
    for seat, (_, y, v) in E2.items():
        ax.plot(v, y, marker="o", ms=5.4, mfc=INK, mec=INK, zorder=5)
        dx, dy, ha = off[seat]
        ax.text(v + dx, y + dy, DISPLAY[seat], ha=ha, va="center",
                fontsize=7, color=INK2, zorder=6)
    ax.text(0.05, 0.97, "training volume: ρ = +0.14",
            transform=ax.transAxes, ha="left", va="top", fontsize=6.8,
            color=INK2,
            bbox=dict(facecolor="white", edgecolor=HAIR, linewidth=0.8,
                      boxstyle="round,pad=0.28"))
    ax.set_xlim(10, 160)
    ax.set_ylim(0.10, 0.95)
    ax.set_xlabel("persona training lines")
    ax.set_ylabel("persona vote fidelity (B, phase S)")
    panel_title(ax, "(b) Training volume x fidelity")
    return save_fig(fig, "fig8_e2_distinctiveness")


# ---------------------------------------------------------------- fig 9 ---
def fig9_e3_autocoherence():
    """Figure 5 - E3 auto-probe: the persona on the judge's own cases."""
    fig = plt.figure(figsize=(6.9, 3.3), constrained_layout=True)
    fig.get_layout_engine().set(rect=(0, 0.10, 1, 0.90))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.12], wspace=0.14)

    order = sorted(PROBE.keys(),
                   key=lambda j: -PROBE[j]["persona_liberal_rate"])
    ypos = {s: len(order) - 1 - i for i, s in enumerate(order)}

    # (a) probe bars
    ax = fig.add_subplot(gs[0])
    for seat in order:
        pr = PROBE[seat]
        n, rate = pr["n"], pr["persona_liberal_rate"]
        k = round(rate * n)
        y = ypos[seat]
        is_kagan = seat == "EKagan"
        ax.barh(y, rate, height=0.62, zorder=3,
                color=SIG if is_kagan else INK2, linewidth=0)
        ax.text(rate + 0.018, y, f"{k}/{n}", va="center", ha="left",
                fontsize=7, color=SIG if is_kagan else INK2,
                fontweight="bold" if is_kagan else "normal", zorder=6)
    ax.axvline(1.0, ls=(0, (4, 3)), lw=1.0, color=INK2, zorder=4)
    ax.text(0.995, len(order) - 0.28, "reality: liberal by construction",
            ha="right", va="bottom", fontsize=6.4, color=INK2,
            style="italic")
    ax.axvline(0.5, ls=(0, (1, 2)), lw=0.9, color=INK3, zorder=4)
    ax.set_yticks([ypos[s] for s in order])
    ax.set_yticklabels([DISPLAY[s] for s in order], fontsize=7.5)
    for tick, seat in zip(ax.get_yticklabels(), order):
        tick.set_color(SIG if seat == "EKagan" else INK2)
    ax.set_xlim(0, 1.06)
    ax.set_ylim(-0.55, len(order) + 0.45)
    ax.set_xlabel("persona liberal-vote rate", fontsize=8)
    ax.xaxis.grid(True, alpha=0.10, color=INK3)
    ax.set_axisbelow(True)
    panel_title(ax, "(a) Own liberal lead opinions (train)")
    ax.text(0.985, 0.03, "Kagan: 3/21 (14%)", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=6.8, color=SIG,
            fontweight="bold")

    # (b) persona liberal rate by the judge's actual vote
    ax = fig.add_subplot(gs[1])
    for seat in order:
        y = ypos[seat]
        lib = BYRV[seat]["liberal"]["persona_liberal_rate"]
        cons = BYRV[seat]["conservative"]["persona_liberal_rate"]
        is_kagan = seat == "EKagan"
        col = SIG if is_kagan else INK
        ax.plot([lib, cons], [y, y], color=HAIR, lw=1.1, zorder=3)
        ax.plot(lib, y, marker="o", ms=5.6, mfc=col, mec=col, zorder=5)
        ax.plot(cons, y, marker="s", ms=5.0, mfc="white", mec=col,
                mew=1.1, zorder=5)
        if is_kagan:
            ax.text(cons + 0.018, y, "inverted", va="center", ha="left",
                    fontsize=6.6, color=SIG, style="italic", zorder=6)
    ax.set_yticks([ypos[s] for s in order])
    ax.set_yticklabels([])
    ax.set_xlim(0, 0.66)
    ax.set_ylim(-0.55, len(order) + 0.45)
    ax.xaxis.grid(True, alpha=0.10, color=INK3)
    ax.set_axisbelow(True)
    handles = [plt.Line2D([], [], marker="o", ms=5.2, mfc=INK, mec=INK,
                          ls=""),
               plt.Line2D([], [], marker="s", ms=4.8, mfc="white",
                          mec=INK, mew=1.1, ls="")]
    ax.legend(handles, ["judge actually voted liberal",
                        "judge actually voted conservative"],
              loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=2,
              fontsize=6.6, columnspacing=1.2, handlelength=1.4)
    panel_title(ax, "(b) By the judge's actual vote")
    return save_fig(fig, "fig9_e3_autocoherence")


# ------------------------------------------------------------------ main --
def main():
    print("D1-bis paper figures")
    total = 0
    total += fig5_m4_primary()
    total += fig6_ideological_dial()
    total += fig7_prompt_vs_adapter()
    total += fig8_e2_distinctiveness()
    total += fig9_e3_autocoherence()
    if total:
        print(f"TOTAL: {total} overlap violation(s) - FIX REQUIRED")
        return 1
    print("All figures rendered, zero overlap violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


