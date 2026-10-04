#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M4 : test de machinerie, SANS GPU, SANS modèle,
SANS jamais toucher aux valeurs de vérité terrain scellées.

Trois étages :

  1. MATHS PURES — McNemar exact (vérifié contre scipy.stats.binomtest),
     Wilson, softmax, majorité, κ, calibration. Valeurs connues.
  2. RÉGRESSION B4 — la condition D recodée dans m4_scoring doit
     reproduire EXACTEMENT le B4 publié de M2 (0,6366 en exactitude de
     vote sur la fenêtre test transparente, scellées incluses comme dans
     M2, sans déduplication). C'est la preuve de fidélité de
     l'implémentation.
  3. BOUT-EN-BOUT SYNTHÉTIQUE — prédictions aléatoires (graine fixe) sur
     la fenêtre transparente RÉELLE (structure de dossiers + vérités
     transparentes, rien de scellé) → build_report complet → vérification
     du schéma, des exclusions, du déterminisme et des comptages
     recomptés indépendamment dans ce test.

Les affaires scellées ne sont vérifiées qu'en STRUCTURE (50 affaires,
strates 20/30, disponibilité de vérité) — aucun score, aucune valeur.

Exit 0 = machinerie prête pour l'épreuve.
"""
import json
import math
import random
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import m4_scoring as S   # noqa: E402

REPO = "/".join(__file__.rsplit("/", 2)[:1])
FAILURES = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"
          + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


# ------------------------------------------------------------------ 1 ----
print("== 1. maths pures ==")

# McNemar exact vs scipy (binomtest est DÉJÀ bilatéral — ne pas le
# re-multiplier ; b=8, c=2 → 0.109375 ; b=10, c=1 → 0.0117 ; etc.)
from scipy.stats import binomtest   # noqa: E402
for b, c in [(8, 2), (10, 1), (12, 1), (3, 3), (0, 0), (1, 0), (25, 6)]:
    p, n, _, _ = S.mcnemar_exact(b, c)
    ref = binomtest(min(b, c), n, 0.5).pvalue if n else 1.0
    check(f"mcnemar_exact({b},{c})", abs(p - round(ref, 6)) < 1e-6,
          f"p={p} vs scipy={round(ref, 6)}")

# Wilson 95 % : k=50, n=100 → [0.4038, 0.5964] (valeur de référence)
w = S.wilson(50, 100)
check("wilson(50,100)", abs(w[0] - 0.4038) < 5.1e-4
      and abs(w[1] - 0.5964) < 5.1e-4, str(w))
check("wilson(0,0)", S.wilson(0, 0) == [None, None])

# softmax contraint : 2:1 en log-prob → p ≈ 0.731
pa, pb = S.softmax_two(math.log(2), math.log(1))
check("softmax_two(2:1)", abs(pa - 2 / 3) < 1e-9, f"p={pa:.4f}")

# majorité + égalité
check("majority_vote", S.majority_vote(
    ["liberal", "conservative", "liberal"]) == "liberal")
check("majority_vote_tie", S.majority_vote(
    ["liberal", "conservative"]) is None)
check("majority_vote_empty", S.majority_vote([None, None]) is None)

# κ de Cohen : prédiction parfaite → 1.0 ; (y=[a,a,b,b], p=[a,b,a,b])
check("kappa_perfect", S.cohens_kappa(["a", "a"], ["a", "a"]) == 1.0)
check("kappa_known", S.cohens_kappa(
    ["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0)

# calibration : parfaitement calibré → ECE ≈ 0 par construction
cal = S.calibration_bins([0.25] * 40 + [0.75] * 40,
                         [1] * 10 + [0] * 30 + [1] * 30 + [0] * 10)
check("calibration_bins_ece", cal["ece"] < 0.01 and cal["n"] == 80,
      f"ECE={cal['ece']}")
check("calibration_bins_counts",
      cal["bins"][1]["n"] == 40 and cal["bins"][3]["n"] == 40)

# disposition SCDB : 2→affirm, 4→reverse, autres→vacate/other
check("disposition_map",
      S.map_disposition("2") == "affirm"
      and S.map_disposition("4") == "reverse"
      and S.map_disposition("3") == "vacate/other"
      and S.map_disposition(None) is None)

# hash canonique déterministe
h1 = S.canonical_hash({"b": 1, "a": 2})
h2 = S.canonical_hash({"a": 2, "b": 1})
check("canonical_hash", h1 == h2 and len(h1) == 64)


# ------------------------------------------------------------------ 2 ----
print("\n== 2. régression B4 (fidélité à M2) ==")
import m3_build_datasets as B   # noqa: E402

cases, opinions, stats, amap = B.load_corpus()
is_sealed = B.sealed_dockets(stats)

fit = S.fit_condition_d(cases, train_end=2019, exclude_sealed=None)
preds_m2 = S.condition_d_predict(cases, fit, target="test",
                                 include_sealed=True, dedup=False)
truth_m2 = S.load_truth(cases, is_sealed, want="test", include_sealed=True,
                        dedup=False)
sv = S.score_votes(preds_m2, truth_m2)
b4_published = json.load(open(
    f"{REPO}/results/m2_baselines.json"))["B4_justice_ideology"]
check("b4_vote_accuracy_regression",
      sv["accuracy"] == round(b4_published["vote_accuracy"], 4),
      f"recodé {sv['accuracy']} vs publié {b4_published['vote_accuracy']} "
      f"({sv['k']}/{sv['n']})")

# régression au niveau affaire : M2 tranchait les égalités de majorité par
# l'ordre d'insertion du Counter (4-4 après récusations) ; l'épreuve
# pré-inscrite les EXCLUT (code « tie »). On recode donc le geste exact de
# M2 pour cette vérification, et on vérifie AUSSI notre règle propre.
from collections import Counter   # noqa: E402
tmap_m2 = {S.canon_docket(t["docket"]): t for t in truth_m2}
k_m2 = n_m2 = 0
for pr in preds_m2:
    t = tmap_m2.get(S.canon_docket(pr["docket"]))
    if not t or t.get("direction") is None or not pr.get("votes"):
        continue
    maj_m2 = Counter(list(pr["votes"].values())).most_common(1)[0][0]
    n_m2 += 1
    k_m2 += int(maj_m2 == t["direction"])
check("b4_case_accuracy_regression_m2rule",
      round(k_m2 / n_m2, 4) == round(b4_published["case_accuracy"], 4)
      or round(k_m2 / n_m2, 3) == round(b4_published["case_accuracy"], 3),
      f"règle M2 {k_m2}/{n_m2} = {round(k_m2 / n_m2, 4)} vs publié "
      f"{b4_published['case_accuracy']}")
sd = S.score_direction(preds_m2, truth_m2)
check("b4_case_n_delta_tie",
      abs(sd["n"] - n_m2) <= 1 and abs(sd["k"] - k_m2) <= 1,
      f"notre règle {sd['k']}/{sd['n']} vs M2 {k_m2}/{n_m2} "
      "(l'écart = l'affaire à égalité 4-4, exclue chez nous)")

# ajustement STRICT (scellées exclues) : l'fit doit différer légèrement,
# preuve que l'exclusion est bien effective
fit_strict = S.fit_condition_d(cases, train_end=2019,
                               exclude_sealed=is_sealed)
n_strict = sum(v["n_votes"] for v in fit_strict.values())
n_loose = sum(v["n_votes"] for v in fit.values())
check("fit_strict_excludes_sealed", n_strict < n_loose,
      f"{n_strict} votes strict vs {n_loose} votes M2")


# ------------------------------------------------------------------ 3 ----
print("\n== 3. bout-en-bout synthétique (fenêtre transparente réelle) ==")
truth_T = S.load_truth(cases, is_sealed, want="test", include_sealed=False,
                       dedup=True)
check("truth_transparente_non_vide", len(truth_T) > 180,
      f"{len(truth_T)} affaires transparentes non scellées")

rng = random.Random(20260904)


def fake_predictions(truths, condition):
    """Prédictions synthétiques : votes/pièces aléatoires, structure
    exacte de l'épreuve (docket, votes, p_votes, direction, p_liberal,
    disposition). Aucune valeur de vérité n'est lue ici."""
    preds = []
    for t in truths:
        votes, pv = {}, {}
        for j in ("JGRoberts", "CThomas", "SAAlito", "SSotomayor",
                  "EKagan", "NMGorsuch", "BMKavanaugh", "ACBarrett",
                  "KBJackson"):
            if rng.random() < 0.9:               # 10 % de juge absent
                votes[j] = rng.choice(["conservative", "liberal"])
                pv[j] = round(rng.random(), 4)
        tie = rng.random() < 0.03                 # 3 % de prédictions nulles
        preds.append({
            "docket": t["docket"],
            "condition": condition,
            "votes": votes,
            "p_votes": pv,
            "direction": None if tie else S.majority_vote(
                list(votes.values())),
            "p_liberal": round(sum(pv.values()) / len(pv), 4) if pv
            else None,
            "disposition": rng.choice(
                ["affirm", "reverse", "vacate/other", None]),
        })
    return preds


preds_A = fake_predictions(truth_T, "A")
preds_B = fake_predictions(truth_T, "B")
report = S.build_report("T", {"A": preds_A, "B": preds_B,
                              "D": preds_m2},
                        truths=truth_T,
                        pinned={"tag": "test-synthétique"},
                        extra={"degraded": ["ACBarrett: "
                                            "persona=base-prompt-only"]})

# schéma
check("report_schema", report["schema"] == "m4-report/1"
      and report["phase"] == "T"
      and set(report["conditions"]) == {"A", "B", "D"}
      and "mcnemar_B_vs_A" in report and report["n_truth_cases"]
      == len(truth_T))

# McNemar présent et auto-cohérent (b + c <= paires communes)
mv = report["mcnemar_B_vs_A"]["vote"]
check("mcnemar_vote_present", 0 <= mv["b"] and mv["b"] + mv["c"] <=
      len(S.pairs_of(preds_A, truth_T, "vote")), str(mv))

# recomptage INDÉPENDANT de l'exactitude de direction de A
tmap = {S.canon_docket(t["docket"]): t for t in truth_T}
k = n = 0
for pr in preds_A:
    t = tmap.get(S.canon_docket(pr["docket"]))
    if t and t.get("direction") and pr.get("direction"):
        n += 1
        k += int(pr["direction"] == t["direction"])
sd_a = report["conditions"]["A"]["case_direction"]
check("score_direction_recompte", sd_a["k"] == k and sd_a["n"] == n,
      f"{sd_a['k']}/{sd_a['n']} vs recompté {k}/{n}")

# exclusions bien comptées (ties + affaires sans vérité)
n_excl = len(sd_a["excluded"])
check("exclusions_comptées", n_excl >= sum(
    1 for pr in preds_A if pr["direction"] is None
    and tmap.get(S.canon_docket(pr["docket"]))
    and tmap[S.canon_docket(pr["docket"])].get("direction")),
      f"{n_excl} exclues, codes: "
      f"{sorted({e['code'] for e in sd_a['excluded']})})")

# déterminisme : deux appels → empreinte identique
report2 = S.build_report("T", {"A": preds_A, "B": preds_B, "D": preds_m2},
                         truths=truth_T,
                         pinned={"tag": "test-synthétique"},
                         extra={"degraded": ["ACBarrett: "
                                             "persona=base-prompt-only"]})
check("report_deterministe",
      report["report_sha256"] == report2["report_sha256"],
      report["report_sha256"][:20] + "…")

# ------------------------------------------------------- scellé : STRUCTURE --
print("\n== 4. scellé — structure seulement (aucune valeur lue) ==")
sealed_sha = stats["five_four_selection"]["sealed_sha256"]
import hashlib   # noqa: E402
recomputed = hashlib.sha256(
    json.dumps(sorted(stats["five_four_selection"]["cases"]))
    .encode()).hexdigest()
check("sceau_intègre", recomputed == sealed_sha, sealed_sha[:20] + "…")

truth_S = S.load_truth(cases, is_sealed, want="sealed",
                       sealed_list=stats["five_four_selection"]["cases"])
n_dir = sum(1 for t in truth_S if t["direction"])
n_disp = sum(1 for t in truth_S if t["disposition"])
n_votes = sum(len(t["votes"]) for t in truth_S)
n_fut = sum(1 for t in truth_S if t["stratum"] == "future")
check("sceau_structure",
      len(truth_S) == 50 and n_dir == 49 and n_disp == 49
      and n_votes >= 400 and n_fut == 20,
      f"{len(truth_S)} affaires | direction {n_dir} | disposition "
      f"{n_disp} | votes {n_votes} | futures {n_fut}/"
      f"{len(truth_S) - n_fut} entrelacées")

# l'ajustement strict D prédit les 50 sans en lire les issues
preds_D_sealed = S.condition_d_predict(
    cases, fit_strict, target="sealed", is_sealed=is_sealed,
    sealed_list=stats["five_four_selection"]["cases"])
check("d_strict_couvre_scellé",
      len(preds_D_sealed) == 50
      and all(p["disposition"] == "reverse" for p in preds_D_sealed),
      f"{len(preds_D_sealed)} prédictions D, disposition=reverse "
      "(règle B3)")


# ------------------------------------------------------------------ fin --
print()
if FAILURES:
    print(f"ÉCHECS ({len(FAILURES)}) : {FAILURES}")
    sys.exit(1)
print("MACHINERIE M4 : PRÊTE — maths vérifiées, B4 reproduit "
      "(0,6366 / 0,558), rapport synthétique complet et déterministe.")
