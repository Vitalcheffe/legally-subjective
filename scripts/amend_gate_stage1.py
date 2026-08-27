#!/usr/bin/env python3
"""LS-AUDIT-001 inj. 2 — amend the Phase 1 gate BEFORE the first GPU run.

Adds to the Colab notebook:
  - the third arm: the majority-class baseline (the "always AFFIRMED" idiot),
  - the exact McNemar paired test between A and B on the same 400 cases,
  - the paired CI on the difference B − A,
  - the pre-registered amended gate rule (must also beat the baseline).

Also updates the verdict markdown cell and the persisted report fields.
"""
import json
from pathlib import Path

NB = Path("phase1/colab/manhattan_stage1_ab.ipynb")
nb = json.loads(NB.read_text())

# ————————————————————————————————————————————————
# Cell 10 — the markdown describing the verdict. Pre-registered rule.
# ————————————————————————————————————————————————
nb["cells"][10]["source"] = [
    "## Le verdict de l'expérience — A vs B (règle pré-enregistrée, amendée avant tout GPU)\n",
    "\n",
    "**Amendement LS-AUDIT-001 inj. 2, enregistré AVANT le premier run**\n",
    "(après le run, la même modification s'appellerait une fraude de convenance).\n",
    "\n",
    "L'expérience oppose maintenant **trois** joueurs, pas deux :\n",
    "\n",
    "1. **Modèle A** — le juge vierge (zero-shot) ;\n",
    "2. **Modèle B** — le juge qui apprend (QLoRA sur 600 affaires) ;\n",
    "3. **La ligne de base** — l'idiot utile qui répond toujours « AFFIRMED »\n",
    "   (la classe majoritaire de l'entraînement ; ~80 % sur ce corpus).\n",
    "\n",
    "La **règle de décision complète**, pré-enregistrée :\n",
    "\n",
    "- la différence B − A est testée par **McNemar exact apparié**\n",
    "  (les deux modèles jugent les MÊMES 400 affaires) ;\n",
    "- un **intervalle à 95 %** est rapporté sur B − A ;\n",
    "- la gate n'est franchie que si **les trois conditions** tiennent :\n",
    "  1. `accuracy(B) − accuracy(A) > 5 points`,\n",
    "  2. `p(McNemar) < 0,05`,\n",
    "  3. `accuracy(B) > accuracy(ligne de base)`.\n",
    "\n",
    "Toute autre issue est un **résultat négatif honnête** : documenté,\n",
    "publié, et la phase suivante n'est pas fondée. La fenêtre pour cet\n",
    "amendement se referme au premier lancement GPU — c'est déjà écrit."
]

# ————————————————————————————————————————————————
# Cell 11 — the evaluation code. Baseline arm + McNemar + paired CI.
# ————————————————————————————————————————————————
nb["cells"][11]["source"] = [
    "from math import sqrt\n",
    "\n",
    "def evaluate(preds, name):\n",
    "    ok = sum((p == r[\"label\"]) for p, r in zip(preds, test) if p)\n",
    "    acc = ok / len(test)\n",
    "    unparsed = sum(p is None for p in preds)\n",
    "    cm = {}\n",
    "    for p, r in zip(preds, test):\n",
    "        if not p: continue\n",
    "        k = (r[\"label\"], p)\n",
    "        cm[k] = cm.get(k, 0) + 1\n",
    "    by_cat = {}\n",
    "    for p, r in zip(preds, test):\n",
    "        if not p: continue\n",
    "        c = r.get(\"crime_category\", \"unstated\")\n",
    "        by_cat.setdefault(c, [0, 0])\n",
    "        by_cat[c][0] += (p == r[\"label\"]); by_cat[c][1] += 1\n",
    "    print(f\"\\n=== {name} ===\")\n",
    "    print(f\"accuracy : {acc:.4f}  (base rate {base:.4f})\")\n",
    "    print(f\"non parsés : {unparsed}\")\n",
    "    print(\"matrice (réel -> prédit) :\", cm)\n",
    "    print(\"par catégorie de crime :\")\n",
    "    for c, (n, d) in sorted(by_cat.items()):\n",
    "        print(f\"  {c:10s} {n:3d}/{d:<3d} = {n/d:.3f}\")\n",
    "    return {\"accuracy\": acc, \"unparsed\": unparsed, \"confusion\": cm,\n",
    "            \"by_crime_category\": {c: {\"correct\": n, \"n\": d}\n",
    "                                  for c, (n, d) in by_cat.items()}}\n",
    "\n",
    "# --- LS-AUDIT-001 inj. 2 : le troisième joueur, l'idiot utile --------\n",
    "# Ligne de base = classe majoritaire de l'ENTRAÎNEMENT (jamais du test)\n",
    "# appliquée à toutes les affaires. Sur ce corpus : « toujours AFFIRMED ».\n",
    "majority = \"AFFIRMED\" if sum(r[\"label\"] == \"AFFIRMED\" for r in train) > len(train)/2 else \"REVERSED\"\n",
    "pred_base = [majority] * len(test)\n",
    "res_base = evaluate(pred_base, \"LIGNE DE BASE — toujours \" + majority)\n",
    "\n",
    "res_a = evaluate(pred_a, \"MODÈLE A — le juge vierge\")\n",
    "res_b = evaluate(pred_b, \"MODÈLE B — le juge qui apprend\")\n",
    "\n",
    "# --- McNemar exact apparié : A vs B sur les MÊMES affaires ------------\n",
    "# b = A juste & B faux ; c = A faux & B juste ; test binomial exact sur\n",
    "# les paires discordantes. Les non-parsés sont écartés des deux côtés.\n",
    "paired = [(pa, pb, r[\"label\"]) for pa, pb, r in zip(pred_a, pred_b, test)\n",
    "          if pa is not None and pb is not None]\n",
    "b_ = sum(1 for pa, pb, y in paired if pa == y and pb != y)   # B perd\n",
    "c_ = sum(1 for pa, pb, y in paired if pa != y and pb == y)   # B gagne\n",
    "n_disc = b_ + c_\n",
    "try:\n",
    "    from scipy.stats import binomtest\n",
    "    mcnemar_p = binomtest(min(b_, c_), n_disc, 0.5).pvalue * 1 if n_disc else 1.0\n",
    "    mcnemar_p = min(1.0, 2 * binomtest(min(b_, c_), max(n_disc,1), 0.5).pvalue / 1) if False else mcnemar_p\n",
    "except Exception:\n",
    "    from math import comb\n",
    "    m = min(b_, c_)\n",
    "    tail = sum(comb(n_disc, k) for k in range(0, m + 1)) / (2 ** n_disc) if n_disc else 1.0\n",
    "    mcnemar_p = min(1.0, 2 * tail)\n",
    "\n",
    "# --- IC apparié à 95 % sur la différence B − A (Wald sur paires) ------\n",
    "n_p = len(paired)\n",
    "d = (c_ - b_) / n_p                       # acc(B) − acc(A) sur les paires\n",
    "se = sqrt(max(b_ + c_ - (b_ - c_) ** 2 / n_p, 0)) / n_p\n",
    "ci_lo, ci_hi = d - 1.96 * se, d + 1.96 * se\n",
    "\n",
    "delta = (res_b[\"accuracy\"] - res_a[\"accuracy\"]) * 100\n",
    "beats_base = res_b[\"accuracy\"] > res_base[\"accuracy\"]\n",
    "\n",
    "print(\"\\n\" + \"=\" * 60)\n",
    "print(f\"ÉCART B - A : {delta:+.1f} points d'accuracy\")\n",
    "print(f\"McNemar exact (apparié) : b={b_}, c={c_}, p = {mcnemar_p:.4f}\")\n",
    "print(f\"IC 95 % sur B - A (apparié) : [{ci_lo*100:+.1f}, {ci_hi*100:+.1f}] points\")\n",
    "print(f\"B vs ligne de base : {res_b['accuracy']:.4f} vs {res_base['accuracy']:.4f} \"\n",
    "      f\"→ {'B BAT la base' if beats_base else 'B NE BAT PAS la base'}\")\n",
    "print(\"=\" * 60)\n",
    "\n",
    "# --- la gate pré-enregistrée (inj. 2) : TROIS conditions --------------\n",
    "gate_points = delta > 5\n",
    "gate_paired = mcnemar_p < 0.05\n",
    "if gate_points and gate_paired and beats_base:\n",
    "    verdict = \"GATE PASSÉE (les trois conditions) — l'apprentissage de cas \"\n",
    "    verdict += \"passés améliore la prédiction ET bat l'idiot. Étage 2 fondé.\"\n",
    "elif delta <= 5 and not (gate_paired and beats_base):\n",
    "    verdict = \"GATE NON PASSÉE — résultat négatif honnête : on documente, \"\n",
    "    verdict += \"les résultats négatifs publient aussi.\"\n",
    "else:\n",
    "    verdict = \"GATE PARTIELLE — l'écart existe mais ne satisfait pas les \"\n",
    "    verdict += \"trois conditions pré-enregistrées : documenté comme tel, \"\n",
    "    verdict += \"sans réinterprétation post-hoc.\"\n",
    "print(verdict)"
]

# ————————————————————————————————————————————————
# Cell 12 — the persisted report gains the new fields.
# ————————————————————————————————————————————————
src12 = "".join(nb["cells"][12]["source"])
if "mcnemar" not in src12:
    # insert the new measured fields into the report dict, right after the
    # res_a/res_b lines if present, else at the dict's opening.
    anchor = '"model_a": res_a,'
    if anchor in src12:
        src12 = src12.replace(
            anchor,
            anchor + '\n    "baseline_majority": res_base,\n'
                     '    "gate_rule": "B-A>5pts AND McNemar p<0.05 AND B>baseline (pre-registered, LS-AUDIT-001 inj.2)",\n'
                     '    "mcnemar_b": b_, "mcnemar_c": c_, "mcnemar_p": mcnemar_p,\n'
                     '    "delta_ci95": [ci_lo, ci_hi],\n'
                     '    "verdict": verdict,',
        )
    else:
        # fallback: prepend after first '{' of the report literal
        idx = src12.find("report = {")
        src12 = src12[: idx + len("report = {")] + '\n    "baseline_majority": res_base,\n    "gate_rule": "B-A>5pts AND McNemar p<0.05 AND B>baseline (pre-registered, LS-AUDIT-001 inj.2)",\n    "mcnemar_b": b_, "mcnemar_c": c_, "mcnemar_p": mcnemar_p,\n    "delta_ci95": [ci_lo, ci_hi],\n    "verdict": verdict,' + src12[idx + len("report = {"):]
    nb["cells"][12]["source"] = src12.splitlines(keepends=True)

NB.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
print("NOTEBOOK AMENDED — baseline arm, exact McNemar, paired CI, pre-registered 3-condition gate.")
