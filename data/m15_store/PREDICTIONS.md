# Prédictions avant exécution de la clôture API — 2026-08-29 ~18:55 UTC

Écrites AVANT l'ouverture de la fenêtre de quota (reset ~22:03 UTC).
Elles seront comparées aux résultats réels dans le worklog — c'est
l'exercice « calculer, prévoir et simuler » demandé.

## Fetch
- Requêtes nécessaires : 18 (lots de 100) si `id__in`+`page_size=100`
  passent ; sinon ~89 (page_size plafonné à 20). Budget 118 couvre les deux.
- Ids retournés par l'API : ≥ 1760/1778 (les clusters supprimés/fusionnés
  côté CL expliqueraient les manquants ; prédiction : < 20 perdus).
- Ids avec au moins un champ texte : ≥ 1750. Les opinions SCOTUS ont
  presque toutes un texte Harvard/Lawbox.

## Merge
- Couverture finale attendue : > 98 % (≥ 1740/1778).
- Source dominante : `api:plain_text` (~60-70 %), puis `api:xml_harvard`
  et `api:html` (~25-35 %), reliquat `legacy:*` (< 5 %).
- La couverture par terme doit devenir quasi uniforme ; les gros trous
  actuels (OT2015 : 6/294, OT2016 : 13/247) doivent se remplir.

## Personas (rebuild après merge)
- Lignes train totales : de 156 → **550-750** (×4-5).
- Épaississement : Thomas 45→~180+, Alito 27→~130+, Roberts 11→~90,
  Sotomayor 17→~90, Kagan 21→~70, Gorsuch 22→~90 (service OT2017+),
  Kavanaugh 13→~40 (service OT2018+).
- Barrett et Jackson restent à 0 lignes train — CORRECT par construction
  (leur service commence OT2020+, hors fenêtre train ≤ 2019 ; power
  report obligatoire).
- L'augmentation par segments slip (+92) devient marginale en proportion
  (et redondante : mêmes textes que l'API, elle doit rester ≤ +5 net).

## Risques identifiés (et mitigations en place)
1. `page_size=100` refusé → pagination suivie automatiquement, budget tient.
2. `id__in` refusé (400) → repli documenté `--batch-size 20` (voie du
   roadmap : 89 requêtes).
3. Fenêtre de quota roulante qui se referme en cours de route → le script
   sauve l'état à chaque lot et sort proprement (Throttled), reprise où
   il s'était arrêté.
4. Textes API de qualité inégale (OCR) → `n_chars` + stats par source
   permettront de le constater et de documenter.
