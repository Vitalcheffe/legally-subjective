# M2 — les baselines statistiques, et comment les lire

## Le protocole

Répartition temporelle, jamais aléatoire :

- **Entraînement** : OT2015..OT2019 (304 affaires étiquetées en direction)
- **Test** : OT2020..OT2023 (225 affaires étiquetées)

L'étiquette principale est la **direction de la décision** (SCDB
`decisionDirection` : 1 = conservateur, 2 = libéral). Chaque précision est
donnée avec son intervalle de confiance **Wilson à 95 %** — jamais de chiffre
nu. Une précision sans intervalle est une opinion.

## Résultats

| Baseline | Précision | IC 95 % |
|---|---|---|
| B1 Classe majoritaire (libérale, apprise du train) | 43,6 % | [37,2 ; 50,1] |
| B2 Toujours conservateur | 56,4 % | [49,9 ; 62,8] |
| B2 Toujours libéral | 43,6 % | [37,2 ; 50,1] |
| B3 Toujours infirmer | 60,1 % | [51,8 ; 67,9] |
| B4 Idéologie par juge — vote | 63,7 % | [62,3 ; 65,0] |
| B4 Idéologie par juge — affaire | 55,8 % | [49,3 ; 62,2] |

Kappa de Cohen pour B1 : **0,0** (la classe majoritaire a basculé entre le
train et le test).

## Lecture

1. **Le tribunal a changé sous nos pieds.** Le jeu d'entraînement est à
   majorité libérale, le jeu de test à majorité conservatrice — c'est le
   phénomène bien documenté du virage à droite de la Cour après 2020. La
   baseline « classe majoritaire » échoue exactement là où un modèle qui
   *apprend* le tribunal devrait réussir : détecter le changement. Toute
   condition B ou C qui ne bat pas « toujours conservateur » (56,4 %) n'a
   rien appris du texte.

2. **La meilleure baseline naïve est idéologique, pas textuelle.** Prédire le
   vote de chaque juge par sa direction modale passée atteint 63,7 % au niveau
   du vote — mais seulement 55,8 % au niveau de l'affaire (l'agrégation en
   majorité simulée dégrade). C'est le plafond de la paresse : connaître les
   juges sans lire les dossiers.

3. **Le pari à battre pour les conditions A/B/C est donc :
   60,1 %** (toujours infirmer) au niveau affaire, et **63,7 %** au
   niveau vote. Un modèle de langage qui lit le dossier et fait moins bien
   que ces deux chiffres a été distancé par une table de fréquences. Notez
   que « toujours infirmer » bat « toujours conservateur » : le tribunal
   infirme beaucoup — c'est l'effet de sélection du certiorari.

4. **Ce que ça ne dit pas.** Ces baselines ignorent le contenu des dossiers.
   Elles ne disent rien du risque de sur-apprentissage temporel, et elles
   reposent sur le codage SCDB (voir `docs/08-LIMITES.md` sur ses
   bizarreries de codage, p. ex. `partyWinning` presque toujours à 1 dans
   l'édition 2025_01 — raison pour laquelle la baseline « pétitionnaire
   gagne » a été écartée).

## Matrice d'accord inter-juges

La matrice complète (accord sur la direction du vote, n ≥ 50, avec IC) est
dans `results/m2_baselines.json` (clé `B5_agreement`). Elle alimente les
figures de « blocs » du tribunal et servira de référence pour les personas :
un adapter dont les prédictions s'écartent de la matrice d'accord de son juge
davantage que le juge réel ne s'écarte de lui-même est suspect.

## Reproduire

```bash
python3 scripts/m2_baselines.py
# -> results/m2_baselines.json + results/m2_baselines.md
```

Le script lit le corpus gelé ; aucune donnée externe n'est requise.
