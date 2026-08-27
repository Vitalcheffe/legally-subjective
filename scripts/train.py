#!/usr/bin/env python3
"""LS-M-001 — the science pipeline behind Legally Subjective.

Trains and evaluates interpretable statistical models of individual voting
behavior on the U.S. Supreme Court, ENTIRELY from the cached public record
(data/sources/) — no network, no fabricated numbers, deterministic seed.

What it does (in order):
  1. Loads every recorded merits vote (Oyez cache) + case metadata.
  2. Two prediction tasks:
       DIRECTION — will justice j side with the party seeking relief?
       DISSENT  — will justice j stand with the minority?
     Two feature specifications:
       Spec A "case-only"   — justice identity, term, originating circuit.
       Spec B "+colleagues" — adds bench momentum measured on the OTHER
                              eight justices only (self excluded — no leakage).
  3. GroupKFold(5) cross-validation GROUPED BY CASE (all votes of a case sit
     in the same fold; a case can never be half-train, half-test).
  4. Learning curves (AUC vs number of training cases, 5 seeds, mean ± sd).
  5. Per-justice out-of-fold AUC — "how machine-predictable is this judge".
  6. Per-justice direction logits from the full case-only fit, with
     case-bootstrap 95% CIs (1,000 resamples).
  7. Classical tests: chi-square (dissent x justice, dissent x term),
     Fleiss' kappa (bench agreement beyond chance).
  8. Emits: data/productions/model.json  (every aggregate, fully traceable)
           data/productions/cases.json   (per-case record + OOF predictions)
           public/figures/fig1..fig5.png (journal-grade figures)

Reproduce with:  python scripts/train.py
Seed:            20260827 (fixed, disclosed)
"""
from __future__ import annotations

import json
import math
import re
import sys
import platform
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as sps
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve, brier_score_loss, log_loss
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core" / "src"))
from legally_subjective.axes.v1 import load_oyez_votes, THE_NINE  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OYEZ_DIR = REPO / "data" / "sources" / "oyez"
PROD = REPO / "data" / "productions"
FIGS = REPO / "public" / "figures"
SEED = 20260827
N_FOLDS = 5
N_BOOTSTRAP = 1000
Z = 1.959963984540054  # two-sided 95%

INK, SIGNAL, GRAY, HAIR = "#0A0A0A", "#E4002B", "#8C8C8C", "#E3E3E3"

SLUGS = [s for s, _, _ in THE_NINE]
NAMES = {s: n for s, n, _ in THE_NINE}

# ------------------------------------------------------------------ utilities

def wilson_ci(k: int, n: int) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + Z * Z / n
    center = (p + Z * Z / (2 * n)) / denom
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


_ORD = {"First": "1st", "Second": "2nd", "Third": "3rd", "Fourth": "4th",
        "Fifth": "5th", "Sixth": "6th", "Seventh": "7th", "Eighth": "8th",
        "Ninth": "9th", "Tenth": "10th", "Eleventh": "11th"}


def circuit_short(name: str | None) -> str:
    if not name:
        return "n/a"
    m = re.search(r"for the ([A-Za-z ]+) Circuit", name)
    if m:
        d = m.group(1).strip()
        if d == "District of Columbia":
            return "D.C. Cir."
        if d == "Federal":
            return "Fed. Cir."
        return f"{_ORD.get(d, d)} Cir."
    if "District Court" in name:
        return "U.S. Dist. Ct."
    if "Court of Appeals" in name:
        return "U.S. Ct. App."
    if "Supreme Court" in name:
        return "St. Sup. Ct."
    return name[:24] + ("…" if len(name) > 24 else "")


def strip_html(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ------------------------------------------------------------------ 1. load

def load_cases() -> dict[str, dict]:
    """Case metadata keyed by docket, from the Oyez cache."""
    cases: dict[str, dict] = {}
    for f in sorted(OYEZ_DIR.glob("*.json")):
        if f.name.endswith(".miss.json"):
            continue
        j = json.loads(f.read_text())
        d = j.get("docket_number")
        if not d or not (j.get("decisions") or []):
            continue
        lc = j.get("lower_court")
        lc_name = lc.get("name") if isinstance(lc, dict) else None
        decided = None
        for tl in j.get("timeline") or []:
            if tl.get("event") == "Decided":
                dates = tl.get("dates") or []
                if dates:
                    decided = dates[0]
        dec = j["decisions"][0]
        cases[str(d)] = {
            "docket": str(d),
            "name": j.get("name"),
            "term": j.get("term"),
            "decided": decided,
            "circuit": circuit_short(lc_name),
            "question": strip_html(j.get("question"))[:600],
            "first_party": strip_html(j.get("first_party")) if isinstance(j.get("first_party"), str) else str(j.get("first_party") or ""),
            "second_party": strip_html(j.get("second_party")) if isinstance(j.get("second_party"), str) else str(j.get("second_party") or ""),
            "winning_party_display": dec.get("winning_party"),
            "decision_type": dec.get("decision_type"),
            "href": j.get("__source_uri__"),
        }
    return cases


def build_rows() -> list[dict]:
    """One row per (case, justice) recorded vote, with targets + features."""
    votes = load_oyez_votes()
    case_meta = load_cases()
    by_case: dict[str, list[dict]] = defaultdict(list)
    for v in votes:
        by_case[str(v["docket"])].append(v)

    rows: list[dict] = []
    for docket, vs in sorted(by_case.items()):
        meta = case_meta.get(docket, {})
        n_maj = sum(1 for v in vs if v["vote"] == "majority")
        n_min = sum(1 for v in vs if v["vote"] == "minority")
        # direction per justice: 1 = sided with the party seeking relief
        dirs = {v["justice"]: (1 if ((v["petitioner_won"] and v["vote"] == "majority")
                                      or (v["petitioner_won"] is False and v["vote"] == "minority")) else 0)
                for v in vs if v["petitioner_won"] is not None}
        for v in vs:
            others_maj = sum(1 for o in vs if o["justice"] != v["justice"] and o["vote"] == "majority")
            others_n = sum(1 for o in vs if o["justice"] != v["justice"])
            odirs = [dirs[o["justice"]] for o in vs if o["justice"] != v["justice"] and o["justice"] in dirs]
            bench_lean = ((sum(odirs) - (len(odirs) - sum(odirs))) / len(odirs)) if odirs else 0.0
            rows.append({
                "docket": docket,
                "justice": v["justice"],
                "term": str(meta.get("term") or v.get("term") or ""),
                "circuit": meta.get("circuit", "n/a"),
                "y_dissent": 1 if v["vote"] == "minority" else 0,
                "y_direction": dirs.get(v["justice"]) if v["petitioner_won"] is not None else None,
                "petitioner_won": v["petitioner_won"],
                "vote": v["vote"],
                "n_maj_others": others_maj / 8.0,
                "bench_lean_others": bench_lean,
                "case_split": (n_maj, n_min),
                "meta": meta,
            })
    return rows


# ------------------------------------------------------------------ 2. features

def design_matrix(rows: list[dict], spec: str, circuits: list[str], terms: list[str]):
    """Spec A: justice + term + circuit. Spec B: + bench signals (self-excluded)."""
    X, keep = [], []
    for r in rows:
        x = [1.0 if r["justice"] == s else 0.0 for s in SLUGS]
        x += [1.0 if r["term"] == t else 0.0 for t in terms]
        x += [1.0 if r["circuit"] == c else 0.0 for c in circuits]
        if spec == "B":
            x += [r["n_maj_others"], r["bench_lean_others"]]
        X.append(x)
        keep.append(True)
    return np.array(X), np.array(keep)


def evaluate(rows: list[dict], y: np.ndarray, spec: str, circuits: list[str],
             terms: list[str], groups: np.ndarray) -> dict:
    """GroupKFold(N_FOLDS) by case -> pooled out-of-fold probabilities."""
    X, _ = design_matrix(rows, spec, circuits, terms)
    gkf = GroupKFold(n_splits=N_FOLDS)
    oof = np.full(len(rows), np.nan)
    for tr, te in gkf.split(X, y, groups):
        if len(np.unique(y[tr])) < 2:
            continue
        m = LogisticRegression(penalty="l2", C=1.0, max_iter=2000, random_state=SEED)
        m.fit(X[tr], y[tr])
        oof[te] = m.predict_proba(X[te])[:, 1]
    mask = ~np.isnan(oof)
    p, yy = oof[mask], y[mask]
    preds = (p >= 0.5).astype(int)
    return {
        "oof": oof,
        "auc": float(roc_auc_score(yy, p)),
        "accuracy": float((preds == yy).mean()),
        "brier": float(brier_score_loss(yy, p)),
        "log_loss": float(log_loss(yy, np.clip(p, 1e-9, 1 - 1e-9))),
        "n": int(mask.sum()),
    }


def baseline_per_justice(rows: list[dict], y: np.ndarray, groups: np.ndarray,
                         key: str) -> dict:
    """Per-justice base-rate score computed strictly inside each train fold."""
    gkf = GroupKFold(n_splits=N_FOLDS)
    oof = np.full(len(rows), np.nan)
    just = np.array([r["justice"] for r in rows])
    for tr, te in gkf.split(np.zeros(len(rows)), y, groups):
        rates = {}
        for s in SLUGS:
            m = just[tr] == s
            rates[s] = y[tr][m].mean() if m.sum() else y[tr].mean()
        oof[te] = np.array([rates[j] for j in just[te]])
    mask = ~np.isnan(oof)
    p, yy = oof[mask], y[mask]
    return {
        "auc": float(roc_auc_score(yy, p)),
        "accuracy": float(((p >= 0.5).astype(int) == yy).mean()),
        "brier": float(brier_score_loss(yy, p)),
        "n": int(mask.sum()),
    }


def learning_curve(rows: list[dict], y: np.ndarray, spec: str, circuits: list[str],
                   terms: list[str], fractions: list[float], reps: int = 5) -> list[dict]:
    """AUC vs number of training cases; random case-level 80/20 split per rep."""
    X, _ = design_matrix(rows, spec, circuits, terms)
    docket_codes = pd_factor(rows)
    rng = np.random.RandomState(SEED)
    out = []
    n_total_cases = len(set(docket_codes))
    for f in fractions:
        aucs = []
        for rep in range(reps):
            perm = rng.permutation(n_total_cases)
            n_train_cases = max(5, int(round(f * 0.8 * n_total_cases)))
            train_cases = set(perm[:n_train_cases].tolist())
            tr = np.array([d in train_cases for d in docket_codes])
            te = ~tr
            if len(np.unique(y[te])) < 2 or len(np.unique(y[tr])) < 2:
                continue
            m = LogisticRegression(penalty="l2", C=1.0, max_iter=2000,
                                   random_state=SEED + rep)
            m.fit(X[tr], y[tr])
            p = m.predict_proba(X[te])[:, 1]
            aucs.append(roc_auc_score(y[te], p))
        out.append({
            "n_train_cases": int(n_train_cases),
            "fraction": round(f, 2),
            "auc_mean": float(np.mean(aucs)),
            "auc_std": float(np.std(aucs)),
            "reps": len(aucs),
        })
    return out


def pd_factor(rows: list[dict]) -> np.ndarray:
    dockets = sorted({r["docket"] for r in rows})
    idx = {d: i for i, d in enumerate(dockets)}
    return np.array([idx[r["docket"]] for r in rows])


# ------------------------------------------------------------------ 3. stats

def fleiss_kappa(rows: list[dict]) -> dict | None:
    """Fleiss' kappa over cases where all nine justices voted (binary rating)."""
    by_case: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_case[r["docket"]].append(r)
    items = [vs for vs in by_case.values() if len(vs) == 9]
    if not items:
        return None
    n, k = 9, 2
    p_j = np.zeros(k)
    P_i = []
    for vs in items:
        n_yes = sum(r["y_dissent"] for r in vs)
        n_no = n - n_yes
        p_j[1] += n_yes
        p_j[0] += n_no
        P_i.append((n_no * (n_no - 1) + n_yes * (n_yes - 1)) / (n * (n - 1)))
    p_j /= len(items) * n
    P_bar = float(np.mean(P_i))
    P_e = float((p_j ** 2).sum())
    kappa = (P_bar - P_e) / (1 - P_e) if P_e < 1 else 0.0
    return {"kappa": round(kappa, 4), "P_bar": round(P_bar, 4),
            "P_e": round(P_e, 4), "items": len(items), "raters": n}


def chi2_dissent(rows: list[dict], key: str) -> dict:
    levels = sorted({r[key] for r in rows})
    table = np.array([[sum(1 for r in rows if r[key] == lv and r["y_dissent"] == 0),
                       sum(1 for r in rows if r[key] == lv and r["y_dissent"] == 1)]
                      for lv in levels])
    chi2, p, dof, _ = sps.chi2_contingency(table)
    return {"chi2": round(float(chi2), 2), "p": float(p), "dof": int(dof),
            "levels": len(levels)}


# ------------------------------------------------------------------ 4. figures

def style_matplotlib():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 8.5,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.8,
        "xtick.color": INK, "ytick.color": INK,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.dpi": 200,
        "legend.frameon": False,
    })


def fig1(rows, per_justice):
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 3.1), constrained_layout=True)
    # (a) votes by term, majority vs dissent
    terms = sorted({r["term"] for r in rows})
    maj = [sum(1 for r in rows if r["term"] == t and r["y_dissent"] == 0) for t in terms]
    dis = [sum(1 for r in rows if r["term"] == t and r["y_dissent"] == 1) for t in terms]
    x = np.arange(len(terms))
    a.bar(x, maj, width=0.62, color="#d4d4d4", label="with majority")
    a.bar(x, dis, width=0.62, bottom=maj, color=SIGNAL, label="in dissent")
    for i, (m, d) in enumerate(zip(maj, dis)):
        a.text(i, m + d + 6, str(m + d), ha="center", fontsize=7.5, color=INK)
    a.set_xticks(x, [f"OT{t[2:]}" for t in terms])
    a.set_ylabel("recorded votes")
    a.set_title("(a)  Recorded votes by term", fontsize=9, loc="left", color=INK)
    a.legend(loc="upper left", fontsize=7.5)
    a.set_ylim(0, max(m + d for m, d in zip(maj, dis)) * 1.18)
    # (b) per-justice dissent rate + Wilson CI
    order = sorted(SLUGS, key=lambda s: per_justice[s]["dissent_rate"])
    ys = np.arange(len(order))
    for i, s in enumerate(order):
        pj = per_justice[s]
        lo, hi = pj["dissent_ci"]
        a_err = [[pj["dissent_rate"] - lo], [hi - pj["dissent_rate"]]]
        b.errorbar(pj["dissent_rate"], i, xerr=a_err, fmt="o", ms=4.5,
                   color=INK, ecolor=GRAY, elinewidth=1, capsize=2)
        b.text(hi + 0.008, i, f'{pj["dissent_rate"]*100:.1f}%', va="center",
               fontsize=7.5, color=INK)
    b.set_yticks(ys, [NAMES[s].split(",")[0].split()[-1] for s in order])
    b.set_xlabel("share of votes cast in dissent (95% CI)")
    b.set_xlim(0, 0.34)
    b.set_title("(b)  Dissent rate by justice", fontsize=9, loc="left", color=INK)
    fig.savefig(FIGS / "fig1-bench.png")
    plt.close(fig)


def fig2():
    agree = json.loads((PROD / "agreement.json").read_text())
    M = np.eye(9)
    for key, v in agree["pairs"].items():
        a, b = key.split("|")
        i, j = SLUGS.index(a), SLUGS.index(b)
        M[i, j] = M[j, i] = v["agree"]
    fig, ax = plt.subplots(figsize=(6.2, 5.2), constrained_layout=True)
    ax.imshow(M, cmap="Greys", vmin=0.5, vmax=1.0)
    for i in range(9):
        for j in range(9):
            v = M[i, j]
            extreme = (i != j) and (v == M[~np.eye(9, dtype=bool)].min() or v == M[~np.eye(9, dtype=bool)].max())
            ax.text(j, i, f"{v*100:.1f}", ha="center", va="center", fontsize=7.6,
                    color=SIGNAL if extreme else ("white" if v > 0.87 else INK),
                    fontweight="bold" if extreme else "normal")
    labels = [NAMES[s].split(",")[0].split()[-1] for s in SLUGS]
    ax.set_xticks(range(9), labels, rotation=45, ha="right")
    ax.set_yticks(range(9), labels)
    ax.set_title("Pairwise agreement rate on common votes (%)", fontsize=9.5,
                 loc="left", color=INK)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    fig.savefig(FIGS / "fig2-agreement.png")
    plt.close(fig)


def fig3(lc_dir, lc_dis):
    fig, ax = plt.subplots(figsize=(5.8, 3.5), constrained_layout=True)
    for lc, color, label in ((lc_dir, INK, "direction task"),
                             (lc_dis, SIGNAL, "dissent task")):
        x = [p["n_train_cases"] for p in lc]
        m = np.array([p["auc_mean"] for p in lc])
        s = np.array([p["auc_std"] for p in lc])
        ax.plot(x, m, "-o", ms=3.5, color=color, label=label)
        ax.fill_between(x, m - s, m + s, color=color, alpha=0.14, linewidth=0)
    ax.axhline(0.5, color=GRAY, linewidth=0.9, linestyle=(0, (4, 3)))
    ax.text(ax.get_xlim()[1] * 0.985, 0.507, "chance", fontsize=7.5,
            color=GRAY, ha="right", va="bottom")
    ax.set_xlabel("number of training cases (out-of-fold AUC, 5 seeds)")
    ax.set_ylabel("ROC AUC")
    ax.set_ylim(0.45, 1.0)
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title("Learning curves — the model improves as the record grows",
                 fontsize=9.5, loc="left", color=INK)
    fig.savefig(FIGS / "fig3-learning.png")
    plt.close(fig)


def fig4(res, y_dir, y_dis):
    fig, ax = plt.subplots(figsize=(4.9, 4.2), constrained_layout=True)
    for (oof, y, color, label) in (
        (res["direction"]["B"]["oof"], y_dir, INK, f'direction · Spec B (AUC {res["direction"]["B"]["auc"]:.3f})'),
        (res["dissent"]["B"]["oof"], y_dis, SIGNAL, f'dissent · Spec B (AUC {res["dissent"]["B"]["auc"]:.3f})'),
    ):
        mask = ~np.isnan(oof)
        fpr, tpr, _ = roc_curve(y[mask], oof[mask])
        ax.plot(fpr, tpr, color=color, linewidth=1.6, label=label)
    ax.plot([0, 1], [0, 1], color=GRAY, linewidth=0.9, linestyle=(0, (4, 3)))
    ax.set_xlabel("false positive rate")
    ax.set_ylabel("true positive rate")
    ax.legend(loc="lower right", fontsize=7.5)
    ax.set_title("Out-of-fold ROC — pooled votes, GroupKFold(5) by case",
                 fontsize=9.5, loc="left", color=INK)
    fig.savefig(FIGS / "fig4-roc.png")
    plt.close(fig)


def fig5(spectrum, per_justice):
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 3.4), constrained_layout=True,
                               gridspec_kw={"width_ratios": [1.5, 1]})
    order = sorted(SLUGS, key=lambda s: spectrum[s]["logit"])
    xs = np.arange(len(order))
    for i, s in enumerate(order):
        sp = spectrum[s]
        lo, hi = sp["ci"]
        a.errorbar(sp["logit"], i, xerr=[[sp["logit"] - lo], [hi - sp["logit"]]],
                   fmt="o", ms=4.5, color=INK, ecolor=GRAY, elinewidth=1, capsize=2)
    a.axvline(0, color=HAIR, linewidth=1)
    a.set_yticks(xs, [NAMES[s].split(",")[0].split()[-1] for s in order])
    a.set_xlabel("direction logit (case-only fit, bootstrap 95% CI)")
    a.set_title("(a)  Propensity to side with the party seeking relief",
                fontsize=9, loc="left", color=INK)
    order2 = sorted(SLUGS, key=lambda s: per_justice[s]["auc_dissent"])
    for i, s in enumerate(order2):
        v = per_justice[s]["auc_dissent"]
        b.plot([0.5, v], [i, i], color=HAIR, linewidth=1.4)
        b.plot(v, i, "o", ms=4.5, color=SIGNAL if v == max(per_justice[x]["auc_dissent"] for x in SLUGS) else INK)
        b.text(v + 0.012, i, f"{v:.2f}", va="center", fontsize=7.5, color=INK)
    b.set_yticks(np.arange(len(order2)),
                 [NAMES[s].split(",")[0].split()[-1] for s in order2])
    b.axvline(0.5, color=GRAY, linewidth=0.9, linestyle=(0, (4, 3)))
    b.set_xlim(0.45, 1.02)
    b.set_xlabel("out-of-fold ROC AUC (dissent task)")
    b.set_title("(b)  How predictable each justice is", fontsize=9, loc="left", color=INK)
    fig.savefig(FIGS / "fig5-spectrum.png")
    plt.close(fig)


# ------------------------------------------------------------------ main

def main():
    rng = np.random.RandomState(SEED)
    rows = build_rows()
    PROD.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    style_matplotlib()

    # ---- dataset aggregates (all real counts)
    n_votes = len(rows)
    n_cases = len({r["docket"] for r in rows})
    terms = sorted({r["term"] for r in rows})
    circuit_counts = Counter(r["circuit"] for r in rows)
    circuits = sorted([c for c, n in circuit_counts.items() if n >= 24])
    for r in rows:
        if r["circuit"] not in circuits:
            r["circuit"] = "OTHER"

    y_dis = np.array([r["y_dissent"] for r in rows], dtype=float)
    dir_mask = np.array([r["y_direction"] is not None for r in rows])
    y_dir = np.array([r["y_direction"] if r["y_direction"] is not None else np.nan
                      for r in rows], dtype=float)
    groups = pd_factor(rows)

    per_justice = {}
    for s in SLUGS:
        vr = [r for r in rows if r["justice"] == s]
        k = sum(r["y_dissent"] for r in vr)
        per_justice[s] = {
            "name": NAMES[s],
            "n_votes": len(vr),
            "dissents": int(k),
            "dissent_rate": k / len(vr) if vr else 0.0,
            "dissent_ci": wilson_ci(k, len(vr)),
            "direction_rate": (lambda d: (sum(d) / len(d)) if d else None)(
                [r["y_direction"] for r in vr if r["y_direction"] is not None]),
        }

    print(f"[data] {n_votes} votes · {n_cases} cases · terms {terms[0]}–{terms[-1]}")
    print(f"[data] circuits kept: {circuits}")

    # ---- models
    res = {"direction": {}, "dissent": {}}
    rows_dir = [r for r in rows if r["y_direction"] is not None]
    y_dir_c = np.array([r["y_direction"] for r in rows_dir], dtype=float)
    groups_dir = pd_factor(rows_dir)

    for spec in ("A", "B"):
        res["direction"][spec] = evaluate(rows_dir, y_dir_c, spec, circuits, terms, groups_dir)
        res["dissent"][spec] = evaluate(rows, y_dis, spec, circuits, terms, groups)
    res["direction"]["baseline"] = baseline_per_justice(rows_dir, y_dir_c, groups_dir, "direction")
    res["dissent"]["baseline"] = baseline_per_justice(rows, y_dis, groups, "dissent")

    print(f"[model] direction  A={res['direction']['A']['auc']:.3f}  "
          f"B={res['direction']['B']['auc']:.3f}  base={res['direction']['baseline']['auc']:.3f}")
    print(f"[model] dissent    A={res['dissent']['A']['auc']:.3f}  "
          f"B={res['dissent']['B']['auc']:.3f}  base={res['dissent']['baseline']['auc']:.3f}")

    # ---- learning curves
    fractions = [0.08, 0.15, 0.25, 0.40, 0.60, 0.80, 1.00]
    lc_dir = learning_curve(rows_dir, y_dir_c, "B", circuits, terms, fractions)
    lc_dis = learning_curve(rows, y_dis, "B", circuits, terms, fractions)

    # ---- per-justice out-of-fold AUC
    for s in SLUGS:
        idx = np.array([r["justice"] == s for r in rows])
        p = res["dissent"]["B"]["oof"][idx]
        yj = y_dis[idx]
        m = ~np.isnan(p)
        per_justice[s]["auc_dissent"] = float(roc_auc_score(yj[m], p[m]))
        idx_d = np.array([r["justice"] == s for r in rows_dir])
        pd_ = res["direction"]["B"]["oof"][idx_d]
        yd = y_dir_c[idx_d]
        md = ~np.isnan(pd_)
        per_justice[s]["auc_direction"] = float(roc_auc_score(yd[md], pd_[md]))

    # ---- spectrum: full case-only fit, justice logits + case bootstrap CI
    # (roberts indicator dropped as the reference level; each justice's logit
    #  = intercept + own coefficient — an L2-regularized directional scale)
    X_full, _ = design_matrix(rows_dir, "A", circuits, terms)
    X_ref = X_full[:, 1:]
    m = LogisticRegression(penalty="l2", C=1.0, max_iter=2000, random_state=SEED)
    m.fit(X_ref, y_dir_c)
    logits = {s: float(m.intercept_[0] + (m.coef_[0][i - 1] if i > 0 else 0.0))
              for i, s in enumerate(SLUGS)}
    # case bootstrap with replacement — cases resampled as whole cases,
    # votes weighted by their case's multiplicity in the resample
    case_codes = pd_factor(rows_dir)
    n_cases_dir = len(set(case_codes.tolist()))
    row_case_index = {c: i for i, c in enumerate(sorted(set(case_codes.tolist())))}
    boot: dict[str, list[float]] = {s: [] for s in SLUGS}
    rs = np.random.RandomState(SEED)
    for b in range(N_BOOTSTRAP):
        pick = rs.choice(n_cases_dir, size=n_cases_dir, replace=True)
        mult = Counter(pick.tolist())
        w = np.array([mult[row_case_index[c]] for c in case_codes], dtype=float)
        if len(np.unique(y_dir_c[w > 0])) < 2:
            continue
        mb = LogisticRegression(penalty="l2", C=1.0, max_iter=2000, random_state=SEED)
        mb.fit(X_ref, y_dir_c, sample_weight=w)
        for i, s in enumerate(SLUGS):
            boot[s].append(float(mb.intercept_[0] + (mb.coef_[0][i - 1] if i > 0 else 0.0)))
    spectrum = {}
    for s in SLUGS:
        arr = np.array(boot[s])
        spectrum[s] = {"logit": logits[s],
                       "ci": [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))]}

    # ---- classical tests
    tests = {
        "chi2_dissent_x_justice": chi2_dissent(rows, "justice"),
        "chi2_dissent_x_term": chi2_dissent(rows, "term"),
        "fleiss_kappa": fleiss_kappa(rows),
    }
    print(f"[tests] chi2 justice p={tests['chi2_dissent_x_justice']['p']:.2e} · "
          f"kappa={tests['fleiss_kappa']['kappa'] if tests['fleiss_kappa'] else None}")

    # ---- figures
    fig1(rows, per_justice)
    fig2()
    fig3(lc_dir, lc_dis)
    fig4(res, y_dir_c, y_dis)
    fig5(spectrum, per_justice)

    # ---- cases.json (record pages + search)
    by_docket: dict[str, list[dict]] = defaultdict(list)
    for i, r in enumerate(rows):
        r["_oof_dissent"] = res["dissent"]["B"]["oof"][i]
        by_docket[r["docket"]].append(r)
    dir_oof_index = {(r["docket"], r["justice"]): i for i, r in enumerate(rows_dir)}
    cases_out = []
    for docket, rs_ in sorted(by_docket.items()):
        meta = rs_[0]["meta"]
        n_maj, n_min = rs_[0]["case_split"]
        # votes needed to flip the winner outright; None when the recorded
        # split is irregular (majority <= minority — an Oyez data quirk)
        flip = ((n_maj - n_min) // 2 + 1) if n_maj > n_min else None
        votes = {}
        model = {}
        for r in rs_:
            votes[r["justice"]] = r["vote"]
            model[r["justice"]] = {
                "p_dissent": None if np.isnan(r["_oof_dissent"]) else round(float(r["_oof_dissent"]), 4),
                "p_direction": None,
                "actual_direction": r["y_direction"],
            }
        # direction OOF lives in rows_dir — reindex
        for r in rs_:
            j = dir_oof_index.get((r["docket"], r["justice"]))
            if j is not None:
                v = res["direction"]["B"]["oof"][j]
                model[r["justice"]]["p_direction"] = None if np.isnan(v) else round(float(v), 4)
        cases_out.append({
            "docket": docket,
            "name": meta.get("name"),
            "term": meta.get("term"),
            "decided": meta.get("decided"),
            "circuit": meta.get("circuit"),
            "question": meta.get("question"),
            "first_party": meta.get("first_party"),
            "second_party": meta.get("second_party"),
            "winning_party": meta.get("winning_party_display"),
            "petitioner_won": rs_[0]["petitioner_won"],
            "split": f"{n_maj}–{n_min}",
            "n_maj": n_maj, "n_min": n_min,
            "flip_margin": flip,
            "unanimous": n_min == 0,
            "votes": votes,
            "model": model,
        })

    # ---- model.json
    def clean(d):
        if isinstance(d, dict):
            return {k: clean(v) for k, v in d.items() if k != "oof"}
        if isinstance(d, (np.floating, np.integer)):
            return float(d)
        return d

    agree = json.loads((PROD / "agreement.json").read_text())
    pairs = [v["agree"] for v in agree["pairs"].values() if v["agree"] is not None]
    agreement_stats = {
        "n_pairs": len(pairs),
        "min": min(pairs), "max": max(pairs),
        "mean": float(np.mean(pairs)),
        "min_pair": min(agree["pairs"], key=lambda k: agree["pairs"][k]["agree"] or 1),
        "max_pair": max(agree["pairs"], key=lambda k: agree["pairs"][k]["agree"] or 0),
    }

    model_json = {
        "model_id": "LS-M-001",
        "trained_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "seed": SEED,
        "reproduce": "python scripts/train.py",
        "environment": {
            "python": platform.python_version(),
            "scikit_learn": __import__("sklearn").__version__,
            "numpy": np.__version__,
            "scipy": __import__("scipy").__version__,
            "matplotlib": matplotlib.__version__,
        },
        "dataset": {
            "votes": n_votes, "cases": n_cases, "terms": terms,
            "justices": len(SLUGS),
            "dissent_votes": int(y_dis.sum()),
            "dissent_rate": float(y_dis.mean()),
            "direction_resolvable_votes": int(dir_mask.sum()),
            "direction_rate": float(np.nanmean(y_dir)),
            "circuits": circuits,
        },
        "design": {
            "cv": f"GroupKFold({N_FOLDS}) grouped by case — all votes of a case share one fold",
            "model": "L2 logistic regression (C=1.0, scikit-learn)",
            "spec_A": "case-only: justice identity + term + originating circuit (one-hot)",
            "spec_B": "Spec A + bench signals measured on the other eight justices only "
                      "(share in majority; net direction lean) — self excluded, no leakage",
            "baselines": "per-justice base rate computed strictly inside each training fold",
            "bootstrap": f"{N_BOOTSTRAP} case resamples for per-justice logits",
        },
        "results": {
            "direction": {
                "A": clean(res["direction"]["A"]),
                "B": clean(res["direction"]["B"]),
                "baseline": res["direction"]["baseline"],
            },
            "dissent": {
                "A": clean(res["dissent"]["A"]),
                "B": clean(res["dissent"]["B"]),
                "baseline": res["dissent"]["baseline"],
            },
            "learning_curve_direction": lc_dir,
            "learning_curve_dissent": lc_dis,
            "per_justice": per_justice,
            "spectrum": spectrum,
            "tests": tests,
            "agreement": agreement_stats,
        },
        "figures": [f"/figures/{f}" for f in
                    ["fig1-bench.png", "fig2-agreement.png", "fig3-learning.png",
                     "fig4-roc.png", "fig5-spectrum.png"]],
    }

    (PROD / "model.json").write_text(json.dumps(model_json, indent=1))
    (PROD / "cases.json").write_text(json.dumps({
        "n_cases": len(cases_out),
        "model_id": "LS-M-001",
        "cases": cases_out,
    }, indent=1))

    print(f"[out] model.json + cases.json ({len(cases_out)} cases) + 5 figures")
    print("[out] done — every number above is recomputable from data/sources/")


if __name__ == "__main__":
    main()
