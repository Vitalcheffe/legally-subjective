#!/usr/bin/env python3
"""m4_metrics.py — noyau statistique de l'Épreuve Finale (M4).

Les métriques de la passe unique sont fixées ICI, avant toute exécution
sur le jeu scellé (discipline de pré-enregistrement, docs/04-PROTOCOLE.md) :

  * exactitude + intervalle de Wilson (IC 95 %) ;
  * bootstrap non paramétrique (10 000 itérations, graine fixe documentée)
    sur l'exactitude et sur la différence appariée entre deux conditions ;
  * test de McNemar EXACT (binomial, bilatéral) — LE test décisif B vs A ;
  * calibration : ECE, Brier, courbe de fiabilité ;
  * log-loss (clampée), F1 macro.

Stdlib uniquement, déterminisme complet (graine = empreinte du scellé,
 déjà utilisée pour le tirage des 50 affaires). Le rapport de l'épreuve ne
 doit dépendre d'aucune bibliothèque externe — ici comme ailleurs dans le
 protocole, zéro dépendance qui pourrait périr.
"""

import math
import random

Z95 = 1.959963984540054  # quantile 0,975 de la loi normale
BOOT_N = 10_000
BOOT_SEED = 0x8a400f4af9abb546  # même graine que le tirage du scellé


# ------------------------------------------------------------ intervalles --

def wilson(k, n, z=Z95):
    """IC de Wilson pour une proportion k/n. n=0 → (0, 0)."""
    if n <= 0:
        return 0.0, 0.0
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def bootstrap_ci(labels, preds, stat=None, n_boot=BOOT_N, seed=BOOT_SEED,
                 alpha=0.05):
    """IC bootstrap percentile pour une statistique quelconque.

    stat : fonction (labels, preds) -> float ; par défaut l'exactitude.
    Graine fixe → le rapport est reproductible au bit près.
    """
    if stat is None:
        stat = accuracy
    n = len(labels)
    if n == 0:
        return 0.0, 0.0, 0.0
    point = stat(labels, preds)
    if n_boot <= 0:
        return point, point, point
    rng = random.Random(seed)
    vals = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        lb = [labels[i] for i in idx]
        pb = [preds[i] for i in idx]
        vals.append(stat(lb, pb))
    vals.sort()
    lo = vals[int(round((alpha / 2) * n_boot)) - 1] if n_boot > 1 else vals[0]
    hi = vals[min(n_boot - 1, int(round((1 - alpha / 2) * n_boot)))]
    return max(0.0, min(point, lo)), min(1.0, max(point, hi)), point


def bootstrap_paired_diff(labels, preds_a, preds_b, n_boot=BOOT_N,
                          seed=BOOT_SEED, alpha=0.05):
    """IC bootstrap de la différence appariée exactitude(A) - exactitude(B).

    Complète McNemar : le test dit *si*, l'intervalle dit *de combien*.
    """
    def diff(lb, pa):
        return accuracy(lb, pa) - accuracy(lb, preds_b)

    # la statistique doit être recalculée sur l'échantillon repliqué pour
    # CHAQUE bras — on passe donc par un resampling commun des indices.
    n = len(labels)
    if n == 0:
        return 0.0, 0.0, 0.0
    point = accuracy(labels, preds_a) - accuracy(labels, preds_b)
    rng = random.Random(seed)
    vals = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        lb = [labels[i] for i in idx]
        pa = [preds_a[i] for i in idx]
        pb = [preds_b[i] for i in idx]
        vals.append(accuracy(lb, pa) - accuracy(lb, pb))
    vals.sort()
    lo = vals[int(round((alpha / 2) * n_boot)) - 1] if n_boot > 1 else vals[0]
    hi = vals[min(n_boot - 1, int(round((1 - alpha / 2) * n_boot)))]
    return lo, hi, point


# ------------------------------------------------------------- décisions --

def accuracy(labels, preds):
    if not labels:
        return 0.0
    return sum(1 for y, p in zip(labels, preds) if y == p) / len(labels)


def mcnemar_exact(n01, n10):
    """McNemar exact (binomial bilatéral) sur la table de discordance.

    n01 = A juste & B faux ; n10 = A faux & B juste (ou l'inverse — le
    test est symétrique). p petit → la différence est significative.
    """
    b, c = int(n01), int(n10)
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def mcnemar_table(labels, preds_a, preds_b):
    """Construit la table de discordance (n01, n10) entre deux conditions."""
    n01 = n10 = 0
    for y, pa, pb in zip(labels, preds_a, preds_b):
        if pa == y and pb != y:
            n01 += 1
        elif pa != y and pb == y:
            n10 += 1
    return n01, n10


def f1_macro(labels, preds):
    """F1 macro sur l'union des classes observées et prédites."""
    classes = set(labels) | set(preds)
    if not classes:
        return 0.0
    f1s = []
    for c in sorted(classes):
        tp = sum(1 for y, p in zip(labels, preds) if y == c and p == c)
        fp = sum(1 for y, p in zip(labels, preds) if y != c and p == c)
        fn = sum(1 for y, p in zip(labels, preds) if y == c and p != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return sum(f1s) / len(f1s)


# ---------------------------------------------------------- probabiliste --

def _clamp(p, eps=1e-15):
    return min(1 - eps, max(eps, p))


def log_loss(probs, labels):
    """Log-loss moyenne sur des probabilités binaires (clampées)."""
    if not probs:
        return 0.0
    return -sum(math.log(_clamp(p if y == 1 else 1 - p))
                for p, y in zip(probs, labels)) / len(probs)


def brier(probs, labels):
    if not probs:
        return 0.0
    return sum((p - y) ** 2 for p, y in zip(probs, labels)) / len(probs)


def reliability(probs, labels, bins=10):
    """Courbe de fiabilité : [(borne_inf, n, p_moyen, taux_observé)]."""
    out = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        pts = [(p, y) for p, y in zip(probs, labels)
               if (lo <= p < hi) or (i == bins - 1 and p == 1.0)]
        if pts:
            out.append((lo, len(pts),
                        sum(p for p, _ in pts) / len(pts),
                        sum(y for _, y in pts) / len(pts)))
    return out


def ece(probs, labels, bins=10):
    """Expected Calibration Error (pondérée par la taille de bac)."""
    n = len(probs)
    if n == 0:
        return 0.0
    total = 0.0
    for _, cnt, p_mean, obs in reliability(probs, labels, bins):
        total += (cnt / n) * abs(p_mean - obs)
    return total


# ------------------------------------------------------------ assemblage --

def condition_report(labels, preds, probs=None, n_boot=BOOT_N,
                      seed=BOOT_SEED):
    """Rapport statistique complet d'une condition de l'Épreuve."""
    k = sum(1 for y, p in zip(labels, preds) if y == p)
    n = len(labels)
    wlo, whi = wilson(k, n)
    blo, bhi, point = bootstrap_ci(labels, preds, n_boot=n_boot, seed=seed)
    rep = {
        "n": n, "correct": k, "accuracy": round(accuracy(labels, preds), 4),
        "wilson95": [round(wlo, 4), round(whi, 4)],
        "bootstrap95": [round(blo, 4), round(bhi, 4)],
        "bootstrap_iters": n_boot, "bootstrap_seed_hex":
            hex(seed) if isinstance(seed, int) else str(seed),
        "f1_macro": round(f1_macro(labels, preds), 4),
    }
    if probs is not None:
        rep.update({
            "log_loss": round(log_loss(probs, labels), 4),
            "brier": round(brier(probs, labels), 4),
            "ece": round(ece(probs, labels), 4),
        })
    return rep


def paired_report(labels, preds_a, preds_b, n_boot=BOOT_N, seed=BOOT_SEED):
    """Comparaison appariée B vs A — le test décisif du protocole."""
    n01, n10 = mcnemar_table(labels, preds_a, preds_b)
    p = mcnemar_exact(n01, n10)
    dlo, dhi, dpoint = bootstrap_paired_diff(labels, preds_a, preds_b,
                                             n_boot=n_boot, seed=seed)
    return {
        "n01_a_juste_b_faux": n01, "n10_a_faux_b_juste": n10,
        "mcnemar_p_exact": round(p, 6),
        "diff_accuracy": round(dpoint, 4),
        "diff_bootstrap95": [round(dlo, 4), round(dhi, 4)],
        "decision_alpha_0.05": "significatif" if p < 0.05 else "non significatif",
    }


if __name__ == "__main__":
    print(__doc__.strip().splitlines()[0])
    print("module de métriques — tests : python scripts/test_m4_metrics.py")
