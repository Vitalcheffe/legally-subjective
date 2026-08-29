# Feuille de route

## Où on en est

| Jalon | État | Contenu |
|---|---|---|
| **M1 — Corpus-Monde** | ✅ **gelé (2026-08-28)** | 569 affaires OT2015–2023, 1 778 opinions, votes SCDB, audio, scellé 5-4 |
| **M2 — Baselines** | ✅ **fait** | Classe majoritaire, idéologie par juge, infirmation, accords inter-juges |
| **M1.5 — Nettoyage** | ⏳ **en cours** | Textes d'opinions : collecte API — la physique réelle du token gratuit est maintenant mesurée : 5 req/min, ~55 req/h, **125 req/JOUR** (le drip unitaire ≈ 14 jours a été remplacé par le mode batch `scripts/fetch_opinion_texts_batch.py` : lots `id__in`, ~20 opinions par requête, tout le corpus en ~20 min de quota) ; le site vit déjà sur le corpus (13 fiches LS-J re-mesurées, `scripts/transfuse_v2.py` + `verify_dockets.py`) |
| **M3a — Challenger structuré** | ✅ **fait (2026-08-29, résultat nul)** | LR additif / boosting / interactions juge×domaine : 58,6–60,4 % — aucun ne bat B4 (63,1 % sur les mêmes lignes, McNemar p ≤ 0,047). La barre tient ; le signal restant vit dans le texte. `scripts/m3a_train.py` + `results/m3a_report.md` |
| **M3 — Entraînement (LLM)** | ⏳ | Personas QLoRA (9 juges) sur Colab/Kaggle gratuits — attend la fin de M1.5 (chemin critique confirmé par M3a) |
| **M4 — Épreuve Finale** | ⏳ | Une seule passe sur les 50 affaires scellées |

## M1.5 — Nettoyage (prochaine étape)

1. **Collecte des textes** : `scripts/fetch_opinion_texts_batch.py`
   (lots `id__in`, ~89 requêtes au total — repli unitaire via
   `scripts/fetch_opinion_texts.py`). La limite journalière du token
   (125 req) compte des requêtes, pas des opinions. Les textes
   complètent le corpus sans en changer l'identité — la règle M1 reste
   gelée.
2. **Déduplication** : les *slip opinions* ré-ingérés plusieurs fois par
   CourtListener sont fusionnés par similarité (ratio ≥ 0,95 sur le texte
   normalisé) ; on conserve l'exemplaire le plus propre.
3. **Normalisation** : en-têtes de *slip opinion*, numéros de page, notes de
   bas de page signalées mais conservées, encodage uniforme.
4. **Découpe temporelle par juge** : pour chaque juge, date de coupure =
   2 ans avant la fin du corpus ; tout ce qui précède = train, le reste =
   test futur. Vérification automatique : zéro fuite documentée dans un
   journal d'audit.

## M3a — Le challenger structuré (fait, résultat nul)

Question opérationnelle : *peut-on entraîner maintenant ?* Réponse
double, archivée dans `results/m3a_report.md` :

1. **Conditions structurées** — les données sont complètes depuis le gel
   du corpus : entraînées le 2026-08-29. Trois challengers (LR additif,
   boosting, interactions juge×domaine), fenêtres pré-décision
   uniquement, scellées exclues de tout split, CV groupé par affaire,
   McNemar contre B4 recalculé sur les mêmes lignes. **Aucun ne bat la
   barre** (58,6–60,4 % contre 63,1 %). Résultat nul, publié tel quel.
2. **Conditions LLM A/B/C** — impossible avant la fin de M1.5
   (112/1 778 textes au 2026-08-29). M3a confirme que c'est LE chemin
   critique : ce qui reste de signal est dans le texte.

## M3 — Entraînement (Colab/Kaggle, 0 €)

- Base : Llama 3 8B, quantification 4 bits (bitsandbytes), QLoRA r=16-64.
- 9 adapters (La Chambre) : Roberts, Thomas, Alito, Sotomayor, Kagan,
  Gorsuch, Kavanaugh, Barrett, Jackson. Le corpus de Jackson (OT2022–2023
  seulement) est notoirement petit — le protocole prévoit un rapport de
  puissance (fenêtre plus courte, mise en garde explicite dans les résultats).
- 1-3 epochs, early stopping, ~10 sessions GPU gratuites au total.
- Audits anti-mémorisation : min-k% prob + cloze, publiés avec chaque adapter.
- Publication : adapters sur Hugging Face, notebook Colab dans `notebooks/`.

## M4 — Épreuve Finale

Voir `docs/04-PROTOCOLE.md`. Une seule passe, quatre conditions, les 50
affaires scellées, publication des résultats quelles qu'ils soient.

## Ensuite (idées, rien de promis)

- Condition multimodale : la plaidoirie **audio** (98,6 % de couverture) comme
  entrée supplémentaire.
- Matrice d'accord modèle-vs-juge : le persona B prédit-il le vote des
  *autres* juges mieux que son propre juge ? (mesure de style vs substance)
- Extension du corpus vers les cours d'appel fédérales (le pipeline est déjà
  générique — il suffit de changer `court_id`).

## Journal des versions

- **v1.0 (2026-08-28)** : gel du Corpus-Monde + baselines M2 + scellé 5-4.
  Sources : bulk CourtListener 2026-06-30 + API recherche v4 (2026-08-28) +
  SCDB 2025_01. Empreintes dans `data/processed/stats_v1.json`.
