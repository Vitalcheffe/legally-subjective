# L'Épreuve Finale — protocole scellé

## Principe

Une seule passe d'évaluation, sur un jeu scellé, dont le contenu est connu
d'avance par personne — pas même nous. Tout ce qui est mesuré sur le jeu
scellé avant le gel définitif est consigné. C'est la discipline minimale d'un
pré-enregistrement : on écrit la règle avant de regarder le résultat.

## Le jeu scellé

- **50 décisions 5-4** tirées des 79 du corpus (échantillonnage aléatoire
  déterministe, graine = SHA-256 de la liste triée, voir `stats_v1.json`).
- Liste scellée par SHA-256 :
  `five_four_selection.sealed_sha256` = empreinte de la liste des 50 dockets.
- Les 50 affaires sont **exclues de tout entraînement, réglage d'hyperparamètres
  ou sélection de prompt**. Le mot d'ordre : *on ne touche pas au scellé*.

## Ce qui est mesuré, une seule fois

Pour chaque condition (A zéro-coup, B persona, C contexte, D statistique) :

1. la **décision par affaire** (direction conservateur/libéral + disposition
   confirme/infirme) ;
2. le **vote par juge** pour les 9 juges siégeants (lorsque SCDB fournit la
   vérité terrain) ;
3. la **calibration** : probabilité prédite vs issue réelle (diagramme de
   fiabilité) ;
4. pour B uniquement : la comparaison appariée contre A (test de McNemar,
   α = 0,05) — c'est LE test décisif du projet.

## Ordre d'exécution (inébranlable)

1. Gel du corpus et du scellé (fait — M1).
2. Nettoyage des textes M1.5 (déduplication, normalisation) sur les affaires
   NON scellées.
3. Entraînement des personas B sur les fenêtres temporelles strictes.
4. Réglage de tout ce qui doit l'être sur une fenêtre de validation ≠ scellé.
5. **Une seule exécution** des quatre conditions sur les 50 affaires scellées.
6. Publication des résultats, quels qu'ils soient, avec les intervalles et les
   codes d'échec.

## Ce qui compte comme tricherie (et est exclu)

- Évaluer, même « pour voir », une condition sur le scellé avant l'étape 5.
- Ajuster un prompt, un seuil ou un hyperparamètre après avoir vu un résultat
  sur le scellé.
- Exclure une affaire scellée sans cause documentée indépendante (p. ex. une
  donnée manquante constatée avant tout envoi au modèle).

## Pré-enregistrement

Le présent document, joint au SHA-256 du scellé et à la version du corpus,
constitue le pré-enregistrement. À l'étape 5, l'horodatage du dépôt GitHub et
l'archive Zenodo du corpus (à créer) complètent la chaîne de preuve.

## Addendum — pré-inscription de l'analyse (ajouté avant toute évaluation
scellée ; implémenté dans `scripts/m4_scoring.py`, prouvé par
`scripts/test_m4_machinery.py`, appliqué par
`notebooks/m4_epreuve_finale.ipynb`)

Le protocole fixe ce qui est mesuré ; cet addendum fixe **comment** —
avant le premier résultat, pour qu'aucun choix d'analyse ne puisse être
motivé par le résultat :

1. **Test décisif** : McNemar exact bilatéral (binomial sur les paires
   discordantes), condition B contre condition A, α = 0,05 — au niveau
   affaire (primaire) et au niveau vote (secondaire).
2. **Strates** : les 50 affaires se répartissent en 20 « futures »
   (OT2020+, postérieures à toute la fenêtre d'entraînement) et 30
   « entrelacées » (OT2015-2019, contemporaines de l'entraînement mais
   exclues de celui-ci). McNemar rapporté global ET par strate. La
   strate entrelacée est structurellement favorable à B (entraînement
   postérieur à la décision) : l'interprétation honnête privilégie la
   strate future.
3. **A et C par juge** : ces conditions n'ont pas d'information par
   juge — leur prédiction d'affaire est répliquée aux neuf sièges pour
   l'appareillage au niveau vote. C'est précisément le signal que B
   doit dépasser.
4. **B par juge** : une requête par juge ; vote d'affaire = majorité
   des neuf ; p_affaire = moyenne des p_libéral.
5. **Disposition** : A/C par l'analyste neutre ; B par le persona
   Roberts (pré-inscrit) ; D = toujours « reverse » (règle B3). Vérité
   SCDB : 2 = affirmé, 4 = infirmé, le reste regroupé « annulé/autre ».
6. **Égalité de majorité** : prédiction exclue avec code d'échec
   (« tie »), jamais tranchée arbitrairement.
7. **Calibration** : p_libéral issu du scoring contraint (log-probs de
   séquence des mots-candidats), diagramme de fiabilité à 5 bandes
   égales + ECE, aux niveaux affaire et vote.
8. **Condition D à l'épreuve** : ajustement B4 **strict** — direction
   modale par juge sur la fenêtre train, affaires scellées exclues de
   l'ajustement. La régression publique (0,6366) utilise l'ancienne
   convention M2 (scellées incluses, égalités tranchées par ordre
   d'insertion) et sert uniquement de preuve de fidélité du code.
9. **Condition C** : récupération de k = 5 opinions antérieures les
   plus similaires (TF-IDF 1-2 grammes sur la question présentée), pool
   = fenêtre train stricte, scellées et affaires sœurs exclues, date
   strictement antérieure à la décision de la cible, extrait de 900
   caractères par opinion.
10. **Sièges sans adaptateur** : mode dégradé pré-inscrit au rapport de
    puissance M3 (base + prompt persona, étiqueté
    `persona=base-prompt-only`).
11. **Gardes d'exécution** : le runner (a) clone le dépôt au tag
    `m4-freeze`, (b) recalcule le scellé et refuse toute divergence,
    (c) re-exécute la porte de pré-vol dans le clone, (d) écrit et
    hache les prédictions AVANT de lire la moindre vérité terrain,
    (e) pose un verrou (`m4_exam.lock`) qui interdit toute seconde
    exécution sauf bris délibéré, consigné dans le rapport.

## Après l'Épreuve

Les résultats alimentent : le dépôt de reproductibilité (ce repo), l'article
de recherche (rédigé pour un public amateur-éclairé), et la discussion
publique. Les contre-factuels de l'Arbre des Mondes (conditions alternatives
simulées) sont étiquetés **« fiction »** en toutes lettres — voir
`docs/06-ETHIQUE.md`.
