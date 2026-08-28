#!/usr/bin/env python3
"""
Legally Subjective — figures du papier (LS-R-002), générées depuis les
productions réelles : results/m2_baselines.json et le corpus gelé.
Style : la palette du site (UI-1.0 EXHIBIT) — papier blanc, encre noire,
UNE couleur signal. Aucune valeur n'est dessinée à la main.
"""
import gzip
import json
import os

import matplotlib.font_manager as fm
fm.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(REPO, "results")
PROC = os.path.join(REPO, "data", "processed")
FIGS = os.path.join(REPO, "public", "figures")

INK = "#0a0a0a"
INK2 = "#595959"
INK3 = "#8c8c8c"
PAPER = "#ffffff"
PAPER2 = "#f7f7f5"
HAIR = "#e3e3e3"
SIGNAL = "#e4002b"

plt.rcParams.update({
    "font.sans-serif": ["DejaVu Sans"],
    "font.family": "sans-serif",
    "axes.unicode_minus": False,
    "text.color": INK,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "axes.linewidth": 0.8,
    "font.size": 9,
})

BENCH = [
    ("Roberts", "JGRoberts"), ("Scalia", "AScalia"), ("Kennedy", "AMKennedy"),
    ("Thomas", "CThomas"), ("Ginsburg", "RBGinsburg"), ("Breyer", "SGBreyer"),
    ("Alito", "SAAlito"), ("Sotomayor", "SSotomayor"), ("Kagan", "EKagan"),
    ("Gorsuch", "NMGorsuch"), ("Kavanaugh", "BMKavanaugh"),
    ("Barrett", "ACBarrett"), ("Jackson", "KBJackson"),
]


def fig_baselines():
    m2 = json.load(open(os.path.join(RES, "m2_baselines.json")))
    rows = [
        ("B1 — majority class (liberal)", m2["B1_majority_class"]["accuracy"],
         m2["B1_majority_class"]["accuracy_ic95"]),
        ("B2 — always conservative", m2["B2_always"]["toujours_conservateur"]["accuracy"],
         m2["B2_always"]["toujours_conservateur"]["ic95"]),
        ("B3 — always reverse", m2["B3_petitioner_wins"]["accuracy"],
         m2["B3_petitioner_wins"]["ic95"]),
        ("B4 — ideology, case level", m2["B4_justice_ideology"]["case_accuracy"],
         m2["B4_justice_ideology"]["case_accuracy_ic95"]),
        ("B4 — ideology, vote level", m2["B4_justice_ideology"]["vote_accuracy"],
         m2["B4_justice_ideology"]["vote_accuracy_ic95"]),
    ]
    rows = rows[::-1]
    fig, ax = plt.subplots(figsize=(7.0, 3.2), dpi=200, constrained_layout=True)
    ys = range(len(rows))
    for i, (name, acc, ic) in enumerate(rows):
        color = SIGNAL if name.startswith("B4 — ideology, vote") else INK
        ax.plot([ic[0] * 100, ic[1] * 100], [i, i], color=color, lw=1.4, solid_capstyle="butt")
        ax.plot([ic[0] * 100, ic[0] * 100], [i - 0.14, i + 0.14], color=color, lw=1.4)
        ax.plot([ic[1] * 100, ic[1] * 100], [i - 0.14, i + 0.14], color=color, lw=1.4)
        ax.plot([acc * 100], [i], "o", color=color, ms=5.5)
        ax.annotate(f"{acc * 100:.1f}%", (acc * 100, i), xytext=(0, 7),
                    textcoords="offset points", ha="center",
                    fontsize=8.5, fontweight="bold", color=color)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    ax.set_xlabel("accuracy on the OT2020–2023 test split, % (Wilson 95% CI)", fontsize=8.5)
    ax.set_xlim(35, 75)
    ax.set_ylim(-0.6, len(rows) - 0.3)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color=HAIR, lw=0.7)
    ax.set_axisbelow(True)
    ax.axvline(50, color=INK3, lw=0.8, ls=(0, (4, 3)))
    ax.annotate("chance", (50.4, len(rows) - 0.55), fontsize=7.5, color=INK3)
    fig.savefig(os.path.join(FIGS, "fig1-baselines.png"), facecolor=PAPER)
    plt.close(fig)
    print("fig1-baselines.png")


def fig_agreement():
    m2 = json.load(open(os.path.join(RES, "m2_baselines.json")))
    b5 = m2["B5_agreement"]
    key_of = {k: n for n, k in BENCH}
    n = len(BENCH)
    M = [[float("nan")] * n for _ in range(n)]
    for pk, v in b5.items():
        a, b = pk.split("|")
        if a not in key_of or b not in key_of:
            continue
        ia, ib = list(key_of).index(a), list(key_of).index(b)
        M[ia][ib] = v["agreement"] * 100
        M[ib][ia] = v["agreement"] * 100
    fig, ax = plt.subplots(figsize=(7.0, 6.2), dpi=200, constrained_layout=True)
    ax.imshow(M, cmap="Greys", vmin=50, vmax=100)
    ax.set_xticks(range(n))
    ax.set_xticklabels([x[0] for x in BENCH], rotation=45, ha="right", fontsize=7.5)
    ax.set_yticks(range(n))
    ax.set_yticklabels([x[0] for x in BENCH], fontsize=7.5)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i in range(n):
        for j in range(n):
            if i == j:
                ax.text(j, i, "—", ha="center", va="center", fontsize=7, color=INK3)
            else:
                v = M[i][j]
                if v == v:
                    dark = v >= 72
                    ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                            fontsize=6.4, color="white" if dark else INK2,
                            fontweight="bold" if v <= 56 or v >= 94 else "normal")
    ax.set_title("vote agreement, % of common coded-direction cases (n ≥ 50 per pair)",
                 fontsize=8.5, color=INK2, pad=10)
    fig.savefig(os.path.join(FIGS, "fig2-agreement.png"), facecolor=PAPER)
    plt.close(fig)
    print("fig2-agreement.png")


def fig_balance():
    m2 = json.load(open(os.path.join(RES, "m2_baselines.json")))
    b0 = m2["B0_class_balance"]
    terms = sorted(b0.keys())
    cons = [b0[t]["conservative"] for t in terms]
    lib = [b0[t]["liberal"] for t in terms]
    fig, ax = plt.subplots(figsize=(7.0, 3.0), dpi=200, constrained_layout=True)
    x = range(len(terms))
    w = 0.38
    ax.bar([i - w / 2 for i in x], cons, width=w, color=INK, label="conservative")
    ax.bar([i + w / 2 for i in x], lib, width=w, color=SIGNAL, label="liberal")
    for i, (c, l) in enumerate(zip(cons, lib)):
        ax.annotate(str(c), (i - w / 2, c), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=7, color=INK2)
        ax.annotate(str(l), (i + w / 2, l), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=7, color=INK2)
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"OT{t}" for t in terms], fontsize=8.5)
    ax.set_ylabel("decided cases with coded direction", fontsize=8.5)
    ax.set_ylim(0, max(cons + lib) + 7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=HAIR, lw=0.7)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2, frameon=False,
              fontsize=8.5)
    ax.annotate("training split ends", (4.5, max(cons + lib) * 0.92),
                fontsize=7.5, color=INK3, ha="center")
    ax.axvline(4.5, color=INK3, lw=0.8, ls=(0, (4, 3)))
    fig.savefig(os.path.join(FIGS, "fig3-balance.png"), facecolor=PAPER)
    plt.close(fig)
    print("fig3-balance.png")


if __name__ == "__main__":
    os.makedirs(FIGS, exist_ok=True)
    fig_baselines()
    fig_agreement()
    fig_balance()
