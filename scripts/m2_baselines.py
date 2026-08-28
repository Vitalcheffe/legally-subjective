#!/usr/bin/env python3
"""
Legally Subjective — M2 : baselines statistiques sur le Corpus-Monde v1.

Baselines calculées (toutes avec intervalles de confiance Wilson à 95 %) :
  B0. Équilibre des classes — direction de décision SCDB (1 conservateur,
      2 libéral) par mandat
  B1. Classe majoritaire — prédire la direction modale du train
      (OT2015..OT2019), évaluée sur le test (OT2020..OT2023)
  B2. Toujours-libéral / toujours-conservateur sur le test
  B3. « Le pétitionnaire gagne » (proxy d'inversion) sur le test
  B4. Idéologie par juge — prédire la direction du vote de chaque juge par sa
      direction modale du train ; vote d'affaire = vote majoritaire simulé
  B5. Accord inter-juges (matrice) + kappa de Cohen pour B1

Sorties : results/m2_baselines.json + results/m2_baselines.md
"""
import gzip
import json
import math
import os
from collections import Counter, defaultdict

ROOT = "/home/z/my-project/legally-subjective"
PROC = os.path.join(ROOT, "data", "processed")
RES = os.path.join(ROOT, "results")
os.makedirs(RES, exist_ok=True)

TRAIN_END_TERM = "2019"  # OT2015..OT2019 = train ; OT2020..OT2023 = test


def wilson(k, n, z=1.96):
    """Intervalle de confiance Wilson à 95 % pour une proportion."""
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - h) / d, 4), round((c + h) / d, 4)]


def kappa(a, b):
    """Kappa de Cohen entre deux listes d'étiquettes."""
    labels = set(a) | set(b)
    po = sum(1 for x, y in zip(a, b) if x == y) / len(a)
    pa = Counter(a)
    pb = Counter(b)
    pe = sum(pa[l] / len(a) * pb[l] / len(b) for l in labels)
    if pe == 1:
        return None
    return round((po - pe) / (1 - pe), 4)


def main():
    cases = [json.loads(l) for l in gzip.open(
        os.path.join(PROC, "corpus_cases_v1.jsonl.gz"), "rt", encoding="utf-8")]

    # ---------- B0 : équilibre des classes ----------
    by_term_dir = defaultdict(Counter)
    for c in cases:
        sc = c.get("scdb")
        if sc and sc.get("decision_direction") in ("1", "2"):
            by_term_dir[c.get("term")][sc["decision_direction"]] += 1
    class_balance = {t: {"conservative": v["1"], "liberal": v["2"],
                         "p_conservative": round(v["1"] / (v["1"] + v["2"]), 3)
                         if (v["1"] + v["2"]) else None}
                     for t, v in sorted(by_term_dir.items())}

    # séparation train/test
    def direction(c):
        sc = c.get("scdb")
        return sc.get("decision_direction") if sc and sc.get("decision_direction") in ("1", "2") else None

    train = [c for c in cases if c.get("term") and c["term"] <= TRAIN_END_TERM]
    test = [c for c in cases if c.get("term") and c["term"] > TRAIN_END_TERM]
    train_dir = [d for d in (direction(c) for c in train) if d]
    test_dir = [d for d in (direction(c) for c in test) if d]
    train_labels = [c["case_name"] for c in train if direction(c)]
    test_labels = [c["case_name"] for c in test if direction(c)]

    modal = Counter(train_dir).most_common(1)[0][0]
    n_correct = sum(1 for d in test_dir if d == modal)

    # ---------- B1 : classe majoritaire ----------
    b1 = {
        "train_terms": "OT2015..OT2019", "test_terms": "OT2020..OT2023",
        "modal_direction": "conservateur" if modal == "1" else "libéral",
        "train_n": len(train_dir), "test_n": len(test_dir),
        "accuracy": round(n_correct / len(test_dir), 4),
        "accuracy_ic95": wilson(n_correct, len(test_dir)),
    }

    # ---------- B2 : toujours-X ----------
    b2 = {}
    for lbl, key in [("toujours_conservateur", "1"), ("toujours_liberal", "2")]:
        k = sum(1 for d in test_dir if d == key)
        b2[lbl] = {"accuracy": round(k / len(test_dir), 4), "ic95": wilson(k, len(test_dir))}

    # ---------- B3 : toujours inverser (confirmation vs infirmation) ----------
    disp = [c for c in test if c.get("scdb") and c["scdb"].get("case_disposition") in ("2", "4")]
    k_rev = sum(1 for c in disp if c["scdb"]["case_disposition"] == "4")
    b3 = {"n": len(disp), "accuracy": round(k_rev / len(disp), 4), "ic95": wilson(k_rev, len(disp)),
          "note": "caseDisposition SCDB : 2=confirmé, 4=infirmé ; prédire « infirmé » "
                  "(code partyWinning écarté : codage non fiable dans SCDB 2025_01)"}

    # ---------- B4 : idéologie par juge ----------
    # votes par juge : direction du vote (vote=1 majoritaire/2 minoritaire ;
    # direction = 1 conservateur/2 libéral du VOTE du juge)
    justice_train = defaultdict(Counter)   # justice -> direction du vote
    for c in train:
        for j in c.get("justices", []):
            if j.get("direction") in ("1", "2"):
                justice_train[j["justice"]][j["direction"]] += 1
    justice_modal = {j: Counter(v).most_common(1)[0][0] for j, v in justice_train.items()
                     if sum(v.values()) >= 20}

    j_correct = j_total = 0
    case_correct = case_total = 0
    per_justice = {}
    for c in test:
        votes = {}
        for j in c.get("justices", []):
            if j.get("direction") in ("1", "2") and j["justice"] in justice_modal:
                pred = justice_modal[j["justice"]]
                votes[j["justice"]] = pred
                j_total += 1
                j_correct += (pred == j["direction"])
                per_justice.setdefault(j["justice"], [0, 0])
                per_justice[j["justice"]][1] += 1
                per_justice[j["justice"]][0] += (pred == j["direction"])
        # vote d'affaire simulé : direction majoritaire des votes prédits
        if votes:
            vals = list(votes.values())
            maj = Counter(vals).most_common(1)[0][0]
            d = direction(c)
            if d:
                case_total += 1
                case_correct += (maj == d)
    b4 = {
        "n_justices": len(justice_modal),
        "vote_accuracy": round(j_correct / j_total, 4),
        "vote_accuracy_ic95": wilson(j_correct, j_total),
        "case_accuracy": round(case_correct / case_total, 4),
        "case_accuracy_ic95": wilson(case_correct, case_total),
        "per_justice": {j: {"n": v[1], "accuracy": round(v[0] / v[1], 4),
                            "ic95": wilson(v[0], v[1])}
                        for j, v in sorted(per_justice.items())},
        "note": "prédiction du vote de chaque juge par sa direction modale du train ; "
                "l'affaire = majorité des votes prédits",
    }

    # ---------- B5 : accord inter-juges ----------
    pair = defaultdict(lambda: [0, 0])   # (a, b) -> [accords, total]
    for c in cases:
        dirs = {j["justice"]: j["direction"] for j in c.get("justices", [])
                if j.get("direction") in ("1", "2")}
        js = sorted(dirs)
        for i, a in enumerate(js):
            for b in js[i + 1:]:
                key = (a, b)
                pair[key][1] += 1
                pair[key][0] += (dirs[a] == dirs[b])
    agreement = {f"{a}|{b}": {"n": t, "agreement": round(k / t, 4), "ic95": wilson(k, t)}
                 for (a, b), (k, t) in sorted(pair.items()) if t >= 50}

    # kappa de Cohen pour B1 (étiquettes prédites = modal vs réelles)
    b1["kappa"] = kappa([modal] * len(test_dir), test_dir)

    results = {
        "corpus": "Corpus-Monde v1 (569 affaires, OT2015..OT2023)",
        "split": {"train": "OT2015..OT2019", "test": "OT2020..OT2023"},
        "B0_class_balance": class_balance,
        "B1_majority_class": b1,
        "B2_always": b2,
        "B3_petitioner_wins": b3,
        "B4_justice_ideology": b4,
        "B5_agreement": agreement,
    }
    with open(os.path.join(RES, "m2_baselines.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # ---------- markdown ----------
    md = ["# M2 — Baselines statistiques (Corpus-Monde v1)", "",
          f"Répartition : entraînement OT2015..OT2019 ({b1['train_n']} affaires étiquetées), "
          f"test OT2020..OT2023 ({b1['test_n']} affaires étiquetées).",
          "Toutes les précisions sont accompagnées d'un intervalle de confiance Wilson à 95 %.", "",
          "## Direction de la décision (SCDB decisionDirection : 1 conservateur, 2 libéral)", "",
          "| Mandat | Conservateur | Libéral | % conservateur |", "|---|---|---|---|"]
    for t, v in class_balance.items():
        md.append(f"| OT{t} | {v['conservative']} | {v['liberal']} | "
                  f"{round(v['p_conservative'] * 100, 1) if v['p_conservative'] is not None else '—'} % |")
    md += ["", "## Résultats des baselines (jeu de test)", "",
           "| Baseline | Précision | IC 95 % |", "|---|---|---|",
           f"| B1 Classe majoritaire ({b1['modal_direction']}) | {b1['accuracy']*100:.1f} % | "
           f"[{b1['accuracy_ic95'][0]*100:.1f}, {b1['accuracy_ic95'][1]*100:.1f}] % |",
           f"| B2 Toujours conservateur | {b2['toujours_conservateur']['accuracy']*100:.1f} % | "
           f"[{b2['toujours_conservateur']['ic95'][0]*100:.1f}, "
           f"{b2['toujours_conservateur']['ic95'][1]*100:.1f}] % |",
           f"| B2 Toujours libéral | {b2['toujours_liberal']['accuracy']*100:.1f} % | "
           f"[{b2['toujours_liberal']['ic95'][0]*100:.1f}, "
           f"{b2['toujours_liberal']['ic95'][1]*100:.1f}] % |",
           f"| B3 Toujours infirmer | {b3['accuracy']*100:.1f} % | "
           f"[{b3['ic95'][0]*100:.1f}, {b3['ic95'][1]*100:.1f}] % |",
           f"| B4 Idéologie par juge (vote) | {b4['vote_accuracy']*100:.1f} % | "
           f"[{b4['vote_accuracy_ic95'][0]*100:.1f}, {b4['vote_accuracy_ic95'][1]*100:.1f}] % |",
           f"| B4 Idéologie par juge (affaire) | {b4['case_accuracy']*100:.1f} % | "
           f"[{b4['case_accuracy_ic95'][0]*100:.1f}, {b4['case_accuracy_ic95'][1]*100:.1f}] % |",
           "", f"Kappa de Cohen (B1) : {b1['kappa']}", "",
           "## Accord inter-juges (direction du vote, n >= 50)", "",
           "| Paire | Accord | IC 95 % |", "|---|---|---|"]
    for k, v in agreement.items():
        a, b = k.split("|")
        md.append(f"| {a} — {b} | {v['agreement']*100:.1f} % | "
                  f"[{v['ic95'][0]*100:.1f}, {v['ic95'][1]*100:.1f}] % |")
    with open(os.path.join(RES, "m2_baselines.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(json.dumps({k: v for k, v in results.items() if k.startswith(("B1", "B2", "B3"))},
                     indent=2, ensure_ascii=False)[:1500])
    print("B4 vote:", b4["vote_accuracy"], "affaire:", b4["case_accuracy"])
    print("-> results/m2_baselines.json + .md")


if __name__ == "__main__":
    main()
