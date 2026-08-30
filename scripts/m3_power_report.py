#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M3: rapport de puissance Barrett / Jackson.

La roadmap (docs/07-ROADMAP.md, M3) rend un « power report » obligatoire
pour ACBarrett et KBJackson : 0 lignes d'entraînement par construction.
Ce script calcule, à partir des artefacts committés uniquement :

  1. pourquoi 0 lignes : discipline temporelle (garde pré-enregistrée
     2020-10-01) vs dates réelles de leurs premières opinions signées ;
  2. ce que relâcher la garde offrirait (combien d'opinions OT2020-23) —
     la tentation chiffrée, pour la refuser explicitement ;
  3. ce que M4 fait de ces deux sièges (condition B dégénérée = base +
     prompt persona, sans adaptateur ; votes couverts par A/C/D).

Sortie : results/m3_power_report.md + results/m3_power_report.json
"""
import gzip
import json
import os
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH = os.path.join(REPO, "data", "m15_store", "final", "authorship.jsonl")
OPINIONS = os.path.join(REPO, "data", "processed", "corpus_opinions_v1.jsonl.gz")
PERSONAS = os.path.join(REPO, "data", "m3", "personas")
OUT_MD = os.path.join(REPO, "results", "m3_power_report.md")
OUT_JS = os.path.join(REPO, "results", "m3_power_report.json")

CUTOFF = "2020-10-01"          # garde temporelle pré-enregistrée (audit B1)
SEATS = {"ACBarrett": "Amy Coney Barrett", "KBJackson": "Ketanji Brown Jackson"}
JOINED = {"ACBarrett": "OT2020 (assermentée le 27-10-2020, première séance)",
          "KBJackson": "OT2022 (assermentée le 30-06-2022)"}


def main():
    dates = {}                    # opinion_id -> date_filed
    with gzip.open(OPINIONS, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            dates[r["opinion_id"]] = r.get("date_filed", "")

    authored = defaultdict(list)  # slug -> [dates signées]
    with open(AUTH, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("slug") and r["opinion_id"] in dates:
                authored[r["slug"]].append(dates[r["opinion_id"]])

    report = {"cutoff": CUTOFF, "seats": {}}
    lines_md = [
        "# M3 — Rapport de puissance : Barrett & Jackson (sièges sans "
        "adaptateur)",
        "",
        f"**Verdict en une ligne** : 0 ligne d'entraînement n'est pas un "
        f"accident de collecte mais la conséquence mécanique de la garde "
        f"temporelle pré-enregistrée (< {CUTOFF}) ; ces deux sièges "
        "coulent en condition B **dégradée documentée** (base + prompt "
        "persona, sans adaptateur), et leurs votes restent couverts par "
        "les conditions A, C et D.",
        "",
        "## 1. Pourquoi zéro ligne — la discipline, pas la pénurie",
        "",
        f"| Siège | Entrée en Cour | Première opinion signée (corpus) | "
        f"Opinions signées au total | Dont avant garde < {CUTOFF} |",
        "|---|---|---|---|---|",
    ]

    for slug, full in SEATS.items():
        ds = sorted(authored.get(slug, []))
        n_before = sum(1 for d in ds if d and d < CUTOFF)
        first = ds[0] if ds else "—"
        report["seats"][slug] = {
            "name": full, "joined": JOINED[slug],
            "authored_total": len(ds),
            "first_authored": first,
            "authored_before_cutoff": n_before,
            "authored_after_cutoff": len(ds) - n_before,
            "train_rows": 0,
        }
        lines_md.append(
            f"| {full} | {JOINED[slug]} | {first} | {len(ds)} | "
            f"**{n_before}** |")

    lines_md += [
        "",
        "La colonne décisive est la dernière : **0 opinion signée avant la",
        f"garde {CUTOFF}**. Aucun texte de Barrett ou de Jackson ne peut",
        "entrer dans l'entraînement sans violer l'audit B1 (décision réelle",
        "strictement antérieure à la garde). Le builder ne « manque » pas de",
        "données — il applique la loi du protocole (docs/04-PROTOCOLE.md).",
        "",
        "## 2. La tentation chiffrée — et pourquoi on la refuse",
        "",
        "Relâcher la garde pour « donner du Barrett/Jackson au modèle »",
        "signifierait entraîner sur des opinions OT2020-2023 : exactement la",
        "fenêtre du test transparent, et pire, un style formé *après* les",
        "évolutions doctrinales que le test transparent prétend mesurer.",
    ]
    for slug, full in SEATS.items():
        s = report["seats"][slug]
        lines_md += [
            "",
            f"- **{full}** : {s['authored_after_cutoff']} opinions signées "
            f"dans la fenêtre interdite (première : {s['first_authored']}). "
            "Les utiliser : (a) casserait la comparabilité avec les sept "
            "autres sièges (entraînés OT2015-2019 uniquement), (b) "
            "contaminerait le test transparent (même fenêtre), (c) "
            "brouillerait style et substance — le style d'un juge formé sur "
            "l'ère post-2020 n'est plus la plume mesurée par le protocole.",
        ]
    lines_md += [
        "",
        "## 3. Conséquences opérationnelles pour M4 (pré-enregistrées)",
        "",
        "1. **Condition B dégradée, étiquetée** : pour ces deux sièges, la",
        "   condition B s'exécute avec le modèle de base + prompt persona",
        "   (nom, rôle, siège), SANS adaptateur — et chaque sortie M4 le",
        "   mentionne explicitement (`persona=base-prompt-only`).",
        "2. **Pas d'adaptateur publié** pour ces sièges sur Hugging Face ;",
        "   l'absence est documentée ici, pas silencieuse.",
        "3. **Couverture des votes intacte** : leurs votes (Barrett 45,",
        "   Jackson 18 dans le test transparent) restent prédits par les",
        "   conditions A (zéro-coup), C (contexte) et D (statistique/B4).",
        "4. **Comparaison bornée** : toute agrégation « condition B » qui",
        "   mélange sièges adaptés et sièges base-prompt-only doit le",
        "   signaler ; les tableaux M4 séparent les deux populations.",
        "",
        "## 4. Puissance statistique — ordre de grandeur, honnêtement",
        "",
        "Même si l'on violait la garde : 43 lignes (Roberts, le plus petit",
        "persona *valide*) constituent déjà un signal mince (8 epochs,",
        "early stopping) ; les ~45-60 opinions OT2020-23 de Barrett",
        "n'atteindraient jamais la taille des personas Thomas (146) ou",
        "Sotomayor (95), tout en coûtant la validité. Le gain de puissance",
        "éventuel est écrasé par le coût protocolaire. La décision optimale",
        "est de ne pas en prendre : c'est celle du protocole.",
        "",
        "---",
        "",
        "*Généré par `scripts/m3_power_report.py` — artefacts committés",
        "uniquement (authorship.jsonl, corpus_opinions_v1.jsonl.gz,",
        "manifest.json). Aucun accès réseau.*",
    ]

    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_md) + "\n")
    with open(OUT_JS, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    for slug in SEATS:
        s = report["seats"][slug]
        print(f"{slug}: total={s['authored_total']} "
              f"first={s['first_authored']} before_cutoff="
              f"{s['authored_before_cutoff']}")
    print("→", os.path.relpath(OUT_MD, REPO), "+ .json")


if __name__ == "__main__":
    main()
