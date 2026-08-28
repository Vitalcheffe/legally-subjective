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

## Après l'Épreuve

Les résultats alimentent : le dépôt de reproductibilité (ce repo), l'article
de recherche (rédigé pour un public amateur-éclairé), et la discussion
publique. Les contre-factuels de l'Arbre des Mondes (conditions alternatives
simulées) sont étiquetés **« fiction »** en toutes lettres — voir
`docs/06-ETHIQUE.md`.
