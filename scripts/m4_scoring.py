#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M4 : la pré-inscription de l'analyse, en code.

Tout ce que l'Épreuve Finale mesurera est décidé ICI, avant toute
évaluation scellée (docs/04-PROTOCOLE.md). Ce module est importé à la
fois par le notebook de l'épreuve (notebooks/m4_epreuve_finale.ipynb,
côté Colab) et par le test local de machinerie
(scripts/test_m4_machinery.py, données synthétiques) — une seule
implémentation, zéro divergence entre le test et l'examen.

Contenu de la pré-inscription :

  * McNemar exact bilatéral (binomial, n = b + c) — LE test décisif
    (condition B vs condition A, α = 0,05) ;
  * intervalles de Wilson 95 % (une décimale max dans le rapport) ;
  * κ de Cohen non pondéré contre la classe majoritaire observée ;
  * le mapping de disposition SCDB → {affirm, reverse, vacate/other} ;
  * le vote d'affaire = majorité des votes prédits des juges siégeants
    (9 voix demandées ; égalité impossible, mais code d'échec « tie »
    prévu par prudence) ;
  * la calibration par bandes égales [0,.2) … [.8,1] + ECE ;
  * la condition D recalculée selon la règle B4 de M2 (direction modale
    par juge sur la fenêtre train, vote d'affaire = majorité simulée,
    disposition = toujours « reverse ») — avec le test de régression :
    sans exclusion du scellé, elle DOIT reproduire le B4 publié
    (0,6366 en exactitude de vote) ;
  * les strates pré-inscrites : « futur » (OT2020+, postérieure à toute
    la fenêtre d'entraînement) et « entrelacée » (OT2015-2019) — McNemar
    global ET stratifié ;
  * p_affaire(libéral) = moyenne des p_libéral des juges interrogés ;
  * code d'échec pour toute affaire sans vérité terrain SCDB
    (1 sans direction, 1-2 sans disposition) : exclue des métriques
    correspondantes, listée dans failure_codes, jamais silencieusement.

Ce module ne contient AUCUNE valeur de vérité terrain scellée : il ne
fait que définir les fonctions qui la liront au moment de l'épreuve.
"""
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

# ----------------------------------------------------------------- maths --

def wilson(k, n, z=1.96):
    """Intervalle de confiance Wilson à 95 % pour une proportion."""
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def mcnemar_exact(b, c):
    """McNemar exact bilatéral : P(|X - n/2| >= |b - n/2|), X ~ B(n, .5).

    b = bonnes pour B / mauvaises pour A ; c = l'inverse ; n = b + c.
    Retourne (p_value, n, b, c) — p = 1.0 si n = 0 (aucune paire
    discordante : les conditions sont indiscernables sur ces lignes)."""
    n = b + c
    if n == 0:
        return 1.0, 0, b, c
    lo = min(b, c)
    tail = sum(math.comb(n, k) for k in range(0, lo + 1)) / (2 ** n)
    return round(min(1.0, 2 * tail), 6), n, b, c


def cohens_kappa(y, pred):
    """κ de Cohen non pondéré sur étiquettes catégorielles."""
    if not y:
        return None
    labels = sorted(set(y) | set(pred))
    n = len(y)
    po = sum(1 for a, b in zip(y, pred) if a == b) / n
    cnt_y = Counter(y)
    cnt_p = Counter(pred)
    pe = sum(cnt_y[l] * cnt_p[l] for l in labels) / (n * n)
    if pe >= 1.0:
        return None if po < 1.0 else 1.0
    return round((po - pe) / (1 - pe), 4)


def softmax_two(logp_a, logp_b):
    """softmax sur deux log-probabilités de séquence (choix contraints)."""
    m = max(logp_a, logp_b)
    ea, eb = math.exp(logp_a - m), math.exp(logp_b - m)
    return ea / (ea + eb), eb / (ea + eb)


def majority_vote(votes):
    """Majorité des votes prédits ; None si égalité (code « tie »).

    votes : itérable de 'conservative'/'liberal' (ou None si un juge
    n'a pas pu être interrogé — les None ne comptent pas)."""
    vals = [v for v in votes if v is not None]
    if not vals:
        return None
    top = Counter(vals).most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return None
    return top[0][0]


def calibration_bins(p_list, y_list, edges=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0)):
    """Diagramme de fiabilité : bandes égales + ECE."""
    bins = []
    n = len(p_list)
    ece = 0.0
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        idx = [j for j, p in enumerate(p_list)
               if (lo <= p < hi) or (i == len(edges) - 2 and p == hi)]
        if not idx:
            bins.append({"bin": [lo, hi], "n": 0,
                         "mean_p": None, "mean_y": None})
            continue
        mp = sum(p_list[j] for j in idx) / len(idx)
        my = sum(y_list[j] for j in idx) / len(idx)
        ece += len(idx) / n * abs(mp - my)
        bins.append({"bin": [lo, hi], "n": len(idx),
                     "mean_p": round(mp, 4), "mean_y": round(my, 4)})
    return {"bins": bins, "ece": round(ece, 4), "n": n}


# ----------------------------------------------------------- vérités SCDB --

# SCDB caseDisposition : 2 = confirmé (affirm) ; 4 = infirmé (reverse) ;
# 1, 3, 5, 6, 7 = annulé/rejeté/autres → regroupés « vacate/other »
# (pré-inscrit ; la note M2 sur le codage non fiable de party_winning
# s'applique : on n'utilise JAMAIS party_winning).
DISPOSITION_MAP = {"2": "affirm", "4": "reverse"}
DISPOSITION_OTHER = "vacate/other"


def map_disposition(code):
    if code in DISPOSITION_MAP:
        return DISPOSITION_MAP[code]
    return DISPOSITION_OTHER if code else None


DIR_OF = {"1": "conservative", "2": "liberal"}


def canon_docket(s):
    """Clé canonique de docket (identique au builder corrigé M4)."""
    s = (s or "").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", s).strip().rstrip(".")


def stratum_of(term):
    """Strate pré-inscrite : futur (OT2020+) vs entrelacé (OT2015-2019)."""
    return "future" if int(term) >= 2020 else "interleaved"


def sealed_representatives(cases, sealed_list):
    """La liste scellée gouverne : 50 entrées = 50 affaires.

    Une entrée peut être un docket consolidé (« 18–422; 18–726 » — Rucho)
    dont l'affaire sœur (« No. 18–726. » — Lamone) existe séparément au
    corpus : la règle d'exclusion l'attrape aussi (correct — les deux sont
    exclues de l'entraînement), mais l'ÉPREUVE évalue les 50 ENTRÉES, pas
    les cousins qu'elles entraînent. Représentante = première occurrence
    du corpus couvrant l'entrée (égalité de chaîne, de clé canonique, ou
    jeton de docket partagé — la même relation de couverture que la
    porte de pré-vol R1.3). Ordre = celui de la liste scellée (triée,
    déterministe)."""
    def toks(s):
        return set(re.findall(r"\d+-\d+",
                              (s or "").replace("\u2013", "-")
                              .replace("\u2014", "-")))

    out = []
    for entry in sealed_list:
        # rang 1 : égalité de chaîne / de clé canonique (l'affaire
        # principale du docket consolidé porte littéralement l'entrée) ;
        # rang 2 : partage du PREMIER jeton de l'entrée (docket principal
        # — « 18–422; 18–726 » désigne Rucho, pas la sœur Lamone) ;
        # rang 3 : n'importe quel jeton partagé. Corpus en ordre stable.
        rep = next((c for c in cases
                    if (c.get("docket_number") or "") == entry
                    or canon_docket(c.get("docket_number"))
                    == canon_docket(entry)), None)
        if rep is None:
            et = toks(entry)
            if et:
                first = sorted(et)[0]
                cands = [c for c in cases if toks(c.get("docket_number")) & et]
                rep = next((c for c in cands if first in toks(
                    c.get("docket_number"))), None) or (cands or [None])[0]
        out.append((entry, rep))
    return out


def load_truth(cases, is_sealed, want="sealed", train_end=2019,
               include_sealed=False, dedup=True, sealed_list=None):
    """Vérité terrain par affaire — lecture brute du corpus gelé.

    want='sealed' : les 50 ENTRÉES de la liste scellée (via
    sealed_representatives — exige sealed_list) ; la clé canonique
    déduplique et l'entrée gouverne. want='test' : la fenêtre transparente
    OT2020+ ; include_sealed=True reproduit EXACTEMENT le jeu de test de
    M2 (régression B4 — scellées non exclues, pas de déduplication :
    dedup=False) ; le mode honnête du notebook transparent utilise
    include_sealed=False.

    Retourne une liste triée par docket canonique :

      {docket, term, stratum, direction, disposition, disposition_code,
       votes: {justice: 'conservative'|'liberal'}}
    """
    if want == "test" and not dedup and not include_sealed:
        raise ValueError("dedup=False n'a de sens que pour la régression M2 "
                         "(include_sealed=True)")
    if want == "sealed" and not sealed_list:
        raise ValueError("want='sealed' exige sealed_list (la liste des 50)")
    out, seen = [], set()
    if want == "sealed":
        picked = [rep for _, rep in sealed_representatives(cases,
                                                          sealed_list)]
    else:
        picked = cases
    for c in picked:
        if want == "sealed":
            pass                     # déjà couvert par la liste
        else:
            sealed = bool(is_sealed(c))
            if sealed and not include_sealed:
                continue
            if int(c["term"]) <= train_end:
                continue
        key = canon_docket(c.get("docket_number"))
        if dedup and key in seen:
            continue
        seen.add(key)
        sc = c.get("scdb") or {}
        votes = {}
        for j in c.get("justices") or []:
            d = DIR_OF.get(j.get("direction"))
            if d:
                votes[j["justice"]] = d
        out.append({
            "docket": c.get("docket_number"),
            "case_name": c.get("case_name"),
            "term": int(c["term"]),
            "stratum": stratum_of(c["term"]),
            "direction": DIR_OF.get(sc.get("decision_direction")),
            "disposition": map_disposition(sc.get("case_disposition")),
            "disposition_code": sc.get("case_disposition"),
            "votes": votes,
        })
    return sorted(out, key=lambda r: canon_docket(r["docket"]))


# ------------------------------------------------------------- condition D --

def fit_condition_d(cases, train_end=2019, exclude_sealed=None,
                    min_votes=20):
    """Règle B4 exacte de M2 : direction modale par juge sur la fenêtre
    train. exclude_sealed=None reproduit le B4 publié (régression) ;
    exclude_sealed=fonction → ajustement strict (scellées exclues),
    la variante utilisée pour l'épreuve scellée."""
    tally = defaultdict(Counter)
    for c in cases:
        if int(c["term"]) > train_end:
            continue
        if exclude_sealed is not None and exclude_sealed(c):
            continue
        for j in c.get("justices") or []:
            d = j.get("direction")
            if d in ("1", "2"):
                tally[j["justice"]][d] += 1
    fit = {}
    for jus, cnt in tally.items():
        total = sum(cnt.values())
        if total < min_votes:
            continue
        modal = "1" if cnt["1"] >= cnt["2"] else "2"
        fit[jus] = {
            "modal": DIR_OF[modal],
            "p_liberal": round(cnt["2"] / total, 4),
            "n_votes": total,
        }
    return fit


def condition_d_predict(cases, fit, target="test", is_sealed=None,
                        train_end=2019, include_sealed=False, dedup=True,
                        sealed_list=None):
    """Applique l'ajustement D : vote par juge = direction modale ;
    vote d'affaire = majorité simulée ; disposition = toujours « reverse »
    (règle B3, pré-inscrite) ; p_libéral du juge = part libérale train.

    target='test' (fenêtre transparente) ou 'sealed' (les 50 ENTRÉES de
    la liste scellée, via sealed_representatives) — paramètres miroir de
    load_truth : mêmes critères, même déduplication, pour un appareillage
    parfait."""
    if target == "sealed" and not sealed_list:
        raise ValueError("target='sealed' exige sealed_list")
    if target == "sealed":
        picked = [rep for _, rep in sealed_representatives(cases,
                                                          sealed_list)]
    else:
        picked = cases
    out, seen = [], set()
    for c in picked:
        if target != "sealed":
            sealed = bool(is_sealed(c)) if is_sealed else False
            if sealed and not include_sealed:
                continue
            if int(c["term"]) <= train_end:
                continue
        key = canon_docket(c.get("docket_number"))
        if dedup and key in seen:
            continue
        seen.add(key)
        votes, ps = {}, {}
        for j in c.get("justices") or []:
            if j.get("direction") in ("1", "2") and j["justice"] in fit:
                votes[j["justice"]] = fit[j["justice"]]["modal"]
                ps[j["justice"]] = fit[j["justice"]]["p_liberal"]
        maj = majority_vote(list(votes.values()))
        p_case = round(sum(ps.values()) / len(ps), 4) if ps else None
        out.append({
            "docket": c.get("docket_number"),
            "votes": votes,
            "direction": maj,
            "p_liberal": p_case,
            "p_votes": ps,
            "disposition": "reverse",
            "condition": "D",
        })
    return sorted(out, key=lambda r: canon_docket(r["docket"]))


# ------------------------------------------------------------- scoring ----

def score_direction(preds, truths, key="docket"):
    """Exactitude de direction au niveau affaire, appareillée par docket.

    preds/truths : listes de dicts avec 'direction' (ou 'votes' pour le
    niveau vote). Retourne (k, n, acc, ic95, exclis) — les affaires sans
    vérité ou sans prédiction sont exclues et comptées."""
    tmap = {canon_docket(t[key]): t for t in truths}
    k = n = 0
    excluded = []
    y, p = [], []
    for pr in preds:
        t = tmap.get(canon_docket(pr[key]))
        if t is None or t.get("direction") is None:
            excluded.append({"docket": pr[key], "code": "no_truth_direction"})
            continue
        if pr.get("direction") is None:
            excluded.append({"docket": pr[key], "code": "tie_or_missing"})
            continue
        n += 1
        k += int(pr["direction"] == t["direction"])
        y.append(t["direction"])
        p.append(pr["direction"])
    maj = Counter(y).most_common(1)[0][0] if y else None
    return {
        "k": k, "n": n, "accuracy": round(k / n, 4) if n else None,
        "ic95": wilson(k, n),
        "kappa_vs_majority_class": cohens_kappa(y, p) if y else None,
        "majority_class": maj,
        "excluded": excluded,
    }


def score_votes(preds, truths):
    """Exactitude de vote au niveau juge, appareillée (docket, juge)."""
    tmap = {canon_docket(t["docket"]): t for t in truths}
    k = n = 0
    per_justice = defaultdict(lambda: [0, 0])
    pairs_b = []          # (docket, justice) pour McNemar appareillé
    for pr in preds:
        t = tmap.get(canon_docket(pr["docket"]))
        if not t:
            continue
        for jus, v in (pr.get("votes") or {}).items():
            truth_v = (t.get("votes") or {}).get(jus)
            if truth_v is None or v is None:
                continue
            n += 1
            ok = int(v == truth_v)
            k += ok
            per_justice[jus][1] += 1
            per_justice[jus][0] += ok
            pairs_b.append((canon_docket(pr["docket"]), jus, bool(ok)))
    return {
        "k": k, "n": n, "accuracy": round(k / n, 4) if n else None,
        "ic95": wilson(k, n),
        "per_justice": {j: {"k": v[0], "n": v[1],
                            "accuracy": round(v[0] / v[1], 4) if v[1]
                            else None}
                        for j, v in sorted(per_justice.items())},
        "_pairs": pairs_b,
    }


def score_disposition(preds, truths):
    tmap = {canon_docket(t["docket"]): t for t in truths}
    k = n = 0
    excluded = []
    conf = Counter()
    for pr in preds:
        t = tmap.get(canon_docket(pr["docket"]))
        if t is None or t.get("disposition") is None:
            excluded.append({"docket": pr["docket"],
                             "code": "no_truth_disposition"})
            continue
        if pr.get("disposition") is None:
            excluded.append({"docket": pr["docket"], "code": "no_prediction"})
            continue
        n += 1
        k += int(pr["disposition"] == t["disposition"])
        conf[(t["disposition"], pr["disposition"])] += 1
    return {
        "k": k, "n": n, "accuracy": round(k / n, 4) if n else None,
        "ic95": wilson(k, n),
        "confusion_true_pred": {f"{a}|{b}": c for (a, b), c
                                in sorted(conf.items())},
        "excluded": excluded,
    }


def score_calibration(preds, truths):
    """Calibration affaire : p_libéral prédit vs direction réelle ;
    et calibration vote : p_libéral par juge vs vote réel."""
    tmap = {canon_docket(t["docket"]): t for t in truths}
    pc, yc, pv, yv = [], [], [], []
    for pr in preds:
        t = tmap.get(canon_docket(pr["docket"]))
        if not t:
            continue
        if t.get("direction") is not None and pr.get("p_liberal") is not None:
            pc.append(pr["p_liberal"])
            yc.append(1.0 if t["direction"] == "liberal" else 0.0)
        for jus, p in (pr.get("p_votes") or {}).items():
            tv = (t.get("votes") or {}).get(jus)
            if tv is not None and p is not None:
                pv.append(p)
                yv.append(1.0 if tv == "liberal" else 0.0)
    return {
        "case_level": calibration_bins(pc, yc),
        "vote_level": calibration_bins(pv, yv),
    }


def mcnemar_paired_pairs(pairs_a, pairs_b):
    """McNemar sur paires (docket, juge) → (ok_a, ok_b).

    pairs_* : listes [(docket, justice, ok)] (niveau vote) ou
    [(docket, None, ok)] (niveau affaire)."""
    amap = {(d, j): ok for d, j, ok in pairs_a}
    b = c = 0
    for d, j, ok_b in pairs_b:
        ok_a = amap.get((d, j))
        if ok_a is None:
            continue
        if ok_b and not ok_a:
            b += 1
        elif ok_a and not ok_b:
            c += 1
    p, n, _, _ = mcnemar_exact(b, c)
    return {"b": b, "c": c, "n": n, "p_value": p,
            "significant_at_005": bool(p is not None and p < 0.05)}


# --------------------------------------------------------------- rapport --

def canonical_hash(obj):
    """sha256 du JSON canonique (tri des clés) — empreinte d'objet."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False,
                   separators=(",", ":")).encode()).hexdigest()


def pairs_of(preds, truths, level="case"):
    """[(docket, justice|None, ok)] pour une condition donnée."""
    tmap = {canon_docket(t["docket"]): t for t in truths}
    out = []
    for pr in preds:
        t = tmap.get(canon_docket(pr["docket"]))
        if not t:
            continue
        if level == "case":
            if t.get("direction") is None or pr.get("direction") is None:
                continue
            out.append((canon_docket(pr["docket"]), None,
                        pr["direction"] == t["direction"]))
        else:
            for jus, v in (pr.get("votes") or {}).items():
                tv = (t.get("votes") or {}).get(jus)
                if tv is None or v is None:
                    continue
                out.append((canon_docket(pr["docket"]), jus, v == tv))
    return out


def strata_split(truths):
    out = defaultdict(list)
    for t in truths:
        if t.get("direction") is not None:
            out[t["stratum"]].append(t)
    return dict(out)


def build_report(phase, predictions, truths, pinned=None, extra=None):
    """Le squelette complet du rapport m4_report.json — une seule
    implémentation, partagée entre le test synthétique local et
    l'épreuve réelle sur Colab."""
    conds = {}
    for cname, preds in predictions.items():
        conds[cname] = {
            "case_direction": {k: v for k, v
                               in score_direction(preds, truths).items()},
            "votes": {k: v for k, v in score_votes(preds, truths).items()
                      if not k.startswith("_")},
            "disposition": score_disposition(preds, truths),
            "calibration": score_calibration(preds, truths),
        }
    mcn = {}
    if "A" in conds and "B" in conds:
        mcn["case_direction"] = mcnemar_paired_pairs(
            pairs_of(predictions["A"], truths, "case"),
            pairs_of(predictions["B"], truths, "case"))
        mcn["vote"] = mcnemar_paired_pairs(
            pairs_of(predictions["A"], truths, "vote"),
            pairs_of(predictions["B"], truths, "vote"))
        strata = strata_split(truths)
        mcn["strata"] = {}
        for sname, sub in strata.items():
            mcn["strata"][sname] = {
                "case_direction": mcnemar_paired_pairs(
                    pairs_of(predictions["A"], sub, "case"),
                    pairs_of(predictions["B"], sub, "case")),
                "n_cases": len(sub),
            }
    report = {
        "schema": "m4-report/1",
        "phase": phase,
        "pinned": pinned or {},
        "conditions": conds,
        "mcnemar_B_vs_A": mcn,
        "n_truth_cases": len(truths),
    }
    if extra:
        report.update(extra)
    report["report_sha256"] = canonical_hash(
        {k: v for k, v in report.items() if k != "report_sha256"})
    return report
