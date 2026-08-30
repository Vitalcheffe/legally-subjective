# M3 — Rapport de puissance : Barrett & Jackson (sièges sans adaptateur)

**Verdict en une ligne** : 0 ligne d'entraînement n'est pas un accident de collecte mais la conséquence mécanique de la garde temporelle pré-enregistrée (< 2020-10-01) ; ces deux sièges coulent en condition B **dégradée documentée** (base + prompt persona, sans adaptateur), et leurs votes restent couverts par les conditions A, C et D.

## 1. Pourquoi zéro ligne — la discipline, pas la pénurie

| Siège | Entrée en Cour | Première opinion signée (corpus) | Opinions signées au total | Dont avant garde < 2020-10-01 |
|---|---|---|---|---|
| Amy Coney Barrett | OT2020 (assermentée le 27-10-2020, première séance) | 2021-03-04 | 46 | **0** |
| Ketanji Brown Jackson | OT2022 (assermentée le 30-06-2022) | 2023-04-19 | 22 | **0** |

La colonne décisive est la dernière : **0 opinion signée avant la
garde 2020-10-01**. Aucun texte de Barrett ou de Jackson ne peut
entrer dans l'entraînement sans violer l'audit B1 (décision réelle
strictement antérieure à la garde). Le builder ne « manque » pas de
données — il applique la loi du protocole (docs/04-PROTOCOLE.md).

## 2. La tentation chiffrée — et pourquoi on la refuse

Relâcher la garde pour « donner du Barrett/Jackson au modèle »
signifierait entraîner sur des opinions OT2020-2023 : exactement la
fenêtre du test transparent, et pire, un style formé *après* les
évolutions doctrinales que le test transparent prétend mesurer.

- **Amy Coney Barrett** : 46 opinions signées dans la fenêtre interdite (première : 2021-03-04). Les utiliser : (a) casserait la comparabilité avec les sept autres sièges (entraînés OT2015-2019 uniquement), (b) contaminerait le test transparent (même fenêtre), (c) brouillerait style et substance — le style d'un juge formé sur l'ère post-2020 n'est plus la plume mesurée par le protocole.

- **Ketanji Brown Jackson** : 22 opinions signées dans la fenêtre interdite (première : 2023-04-19). Les utiliser : (a) casserait la comparabilité avec les sept autres sièges (entraînés OT2015-2019 uniquement), (b) contaminerait le test transparent (même fenêtre), (c) brouillerait style et substance — le style d'un juge formé sur l'ère post-2020 n'est plus la plume mesurée par le protocole.

## 3. Conséquences opérationnelles pour M4 (pré-enregistrées)

1. **Condition B dégradée, étiquetée** : pour ces deux sièges, la
   condition B s'exécute avec le modèle de base + prompt persona
   (nom, rôle, siège), SANS adaptateur — et chaque sortie M4 le
   mentionne explicitement (`persona=base-prompt-only`).
2. **Pas d'adaptateur publié** pour ces sièges sur Hugging Face ;
   l'absence est documentée ici, pas silencieuse.
3. **Couverture des votes intacte** : leurs votes (Barrett 45,
   Jackson 18 dans le test transparent) restent prédits par les
   conditions A (zéro-coup), C (contexte) et D (statistique/B4).
4. **Comparaison bornée** : toute agrégation « condition B » qui
   mélange sièges adaptés et sièges base-prompt-only doit le
   signaler ; les tableaux M4 séparent les deux populations.

## 4. Puissance statistique — ordre de grandeur, honnêtement

Même si l'on violait la garde : 43 lignes (Roberts, le plus petit
persona *valide*) constituent déjà un signal mince (8 epochs,
early stopping) ; les ~45-60 opinions OT2020-23 de Barrett
n'atteindraient jamais la taille des personas Thomas (146) ou
Sotomayor (95), tout en coûtant la validité. Le gain de puissance
éventuel est écrasé par le coût protocolaire. La décision optimale
est de ne pas en prendre : c'est celle du protocole.

---

*Généré par `scripts/m3_power_report.py` — artefacts committés
uniquement (authorship.jsonl, corpus_opinions_v1.jsonl.gz,
manifest.json). Aucun accès réseau.*
