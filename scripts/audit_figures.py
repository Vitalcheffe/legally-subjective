# -*- coding: utf-8 -*-
"""Figures du rapport d'instruction Légalement Subjective.
Toutes les donnees proviennent du depot (agreement.json, dockets, model.json)
et ont ete recalculees par le juge (voir Annexe B du rapport).
"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm

for fp in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
    if os.path.exists(fp):
        fm.fontManager.addfont(fp)

import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = "/home/z/my-project/scripts/audit_figs"
os.makedirs(OUT, exist_ok=True)

# Palette cascade (seed 20260827) — voir rapport, Annexe B
ACCENT = "#1f6c93"
ACCENT2 = "#c33e54"
HEADER = "#3f5763"
MUTED = "#747a7d"
BORDER = "#b2c3cc"
TEXTC = "#1d1f20"


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BORDER)
    ax.spines["bottom"].set_color(BORDER)
    ax.tick_params(colors=MUTED, labelsize=9)
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_color(TEXTC)


# ------------------------------------------------------------------
# FIGURE 1 — Foret des IC : l'ecart vedette de la roue sous incertitude
# Donnees : dockets LS-J-*, axe disposition (petitioner-alignment)
# ------------------------------------------------------------------
JUSTICES = [
    ("Ketanji Brown Jackson", 0.5811, 148),
    ("Sonia Sotomayor", 0.5956, 225),
    ("Clarence Thomas", 0.5973, 226),
    ("Elena Kagan", 0.6106, 226),
    ("Samuel A. Alito", 0.6143, 223),
    ("Amy Coney Barrett", 0.6558, 215),
    ("Neil M. Gorsuch", 0.6696, 224),
    ("John G. Roberts", 0.6814, 226),
    ("Brett M. Kavanaugh", 0.6858, 226),
]

fig, ax = plt.subplots(figsize=(7.4, 4.4), constrained_layout=True)
names, vals, errs, lows, highs = [], [], [], [], []
for name, p, n in JUSTICES:
    ci = 1.96 * math.sqrt(p * (1 - p) / n) * 100
    names.append(name)
    vals.append(p * 100)
    errs.append(ci)
    lows.append(p * 100 - ci)
    highs.append(p * 100 + ci)

ypos = list(range(len(names)))[::-1]
colors = [ACCENT2 if nm in ("Ketanji Brown Jackson", "Brett M. Kavanaugh") else HEADER
          for nm in names]
ax.errorbar(vals, ypos, xerr=errs, fmt="o", markersize=5.5, ecolor=BORDER,
            elinewidth=1.6, capsize=3.5, capthick=1.6, mfc="white", mec=HEADER,
            zorder=3)
for y, v, c in zip(ypos, vals, colors):
    ax.plot([v], [y], "o", color=c, markersize=5.5, zorder=4)

ax.set_yticks(ypos)
ax.set_yticklabels(names, fontsize=9.5)
ax.set_xlim(46, 78)
ax.set_xlabel("Part des votes favorables a la partie qui demande (%, IC 95 %)", fontsize=9.5, color=TEXTC)
ax.grid(True, axis="x", linestyle="--", alpha=0.2, linewidth=0.5)

# zone de chevauchement Jackson / Kavanaugh
ax.axvspan(highs[0] if False else lows[-1], highs[0], color=ACCENT2, alpha=0.06, zorder=1)
ax.annotate(
    "zone de chevauchement\ndes deux extremes",
    xy=((lows[-1] + highs[0]) / 2, ypos[4]),
    fontsize=8.5, color=ACCENT2, ha="center",
    xytext=((lows[-1] + highs[0]) / 2, ypos[4] - 1.15),
    arrowprops=dict(arrowstyle="-", color=ACCENT2, lw=0.7),
)
for nm, v, y in zip(names, vals, ypos):
    ax.text(77.6, y, f"{v:.1f}", fontsize=8.5, color=MUTED, va="center", ha="left")

style_ax(ax)
fig.savefig(os.path.join(OUT, "fig1_forest.png"), dpi=200, facecolor="white")
plt.close(fig)

# ------------------------------------------------------------------
# FIGURE 2 — Courbe de puissance de la gate de Phase 1 (n = 400)
# Approximation : test Z a deux proportions, alpha = 0,05 bilatéral,
# p ~ 0,80 (base rate affirmed). McNemar apparié serait plus puissant ;
# le roadmap n'en spécifie aucun.
# ------------------------------------------------------------------
import statistics

N = 400
P = 0.80
SIGMA = math.sqrt(2 * P * (1 - P) / N)  # ecart-type de la difference (pts fraction)
ZALPHA = 1.96


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


deltas = [d / 100 for d in range(0, 160, 5)]
powers = [phi(d / SIGMA - ZALPHA) * 100 for d in deltas]

fig, ax = plt.subplots(figsize=(7.4, 3.9), constrained_layout=True)
ax.plot([d * 100 for d in deltas], powers, color=ACCENT, linewidth=2.4)
ax.fill_between([d * 100 for d in deltas], powers, color=ACCENT, alpha=0.08)
ax.axhline(80, color=MUTED, linewidth=0.8, linestyle=":")
ax.text(13.5, 81.5, "convention 80 %", fontsize=8.5, color=MUTED)

pw5 = phi(0.05 / SIGMA - ZALPHA) * 100
ax.plot([5], [pw5], "o", color=ACCENT2, markersize=7, zorder=5)
ax.annotate(
    f"seuil de la gate : 5 points\npuissance = {pw5:.0f} %",
    xy=(5, pw5), xytext=(6.4, 26),
    fontsize=9, color=ACCENT2,
    arrowprops=dict(arrowstyle="->", color=ACCENT2, lw=0.9),
)
ax.set_xlabel("Écart réel B − A (points de précision)", fontsize=9.5, color=TEXTC)
ax.set_ylabel("Probabilité de franchir\nla gate (%)", fontsize=9.5, color=TEXTC)
ax.set_xlim(0, 15)
ax.set_ylim(0, 100)
ax.grid(True, linestyle="--", alpha=0.2, linewidth=0.5)
style_ax(ax)
fig.savefig(os.path.join(OUT, "fig2_power.png"), dpi=200, facecolor="white")
plt.close(fig)

# ------------------------------------------------------------------
# FIGURE 3 — Resultats reels du modele : A vs B vs baseline
# Donnees : data/productions/model.json (seed 20260827)
# ------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.4, 3.6), constrained_layout=True)

# (a) AUC
labels = ["A\ndossier seul", "B\n+ collegues", "baseline\nhasard/dossier"]
direction = [0.540, 0.877, 0.510]
dissent = [0.614, 0.737, 0.633]
x = [0, 1, 2]
w = 0.36
ax1.bar([i - w / 2 for i in x], direction, width=w, color=ACCENT, label="direction")
ax1.bar([i + w / 2 for i in x], dissent, width=w, color=HEADER, label="dissidence")
for i, v in zip(x, direction):
    ax1.text(i - w / 2, v + 0.015, f"{v:.2f}".replace(".", ","), ha="center", fontsize=8, color=TEXTC)
for i, v in zip(x, dissent):
    ax1.text(i + w / 2, v + 0.015, f"{v:.2f}".replace(".", ","), ha="center", fontsize=8, color=TEXTC)
ax1.set_xticks(x)
ax1.set_xticklabels(labels, fontsize=8.5)
ax1.set_ylim(0.4, 1.0)
ax1.set_ylabel("AUC", fontsize=9.5, color=TEXTC)
ax1.legend(loc="upper left", bbox_to_anchor=(0, 1.14), ncol=2, frameon=False, fontsize=8.5)
ax1.set_title("(a)", fontsize=9, color=MUTED, loc="left")
ax1.grid(True, axis="y", linestyle="--", alpha=0.2, linewidth=0.5)
style_ax(ax1)

# (b) dissidence : accuracy vs baseline "jamais dissident"
labels2 = ["baseline\njamais dissident", "A\ndossier seul", "B\n+ collegues"]
acc = [0.841, 0.840, 0.834]
cols = [MUTED, ACCENT, HEADER]
bars = ax2.bar([0, 1, 2], acc, width=0.55, color=cols)
for i, v in enumerate(acc):
    ax2.text(i, v + 0.0012, f"{v*100:.1f} %".replace(".", ","), ha="center", fontsize=8.5, color=TEXTC)
ax2.set_xticks([0, 1, 2])
ax2.set_xticklabels(labels2, fontsize=8.5)
ax2.set_ylim(0.80, 0.85)
ax2.set_ylabel("Précision (dissidence)", fontsize=9.5, color=TEXTC)
ax2.set_title("(b)", fontsize=9, color=MUTED, loc="left")
ax2.annotate(
    "le modele B perd\ncontre la piece de monnaie",
    xy=(2, 0.834), xytext=(1.18, 0.812),
    fontsize=8.5, color=ACCENT2,
    arrowprops=dict(arrowstyle="->", color=ACCENT2, lw=0.9),
)
ax2.grid(True, axis="y", linestyle="--", alpha=0.2, linewidth=0.5)
style_ax(ax2)

fig.savefig(os.path.join(OUT, "fig3_ab.png"), dpi=200, facecolor="white")
plt.close(fig)

print("FIGURES OK:", sorted(os.listdir(OUT)))
print(f"puissance a 5 points = {pw5:.1f} %")
