# Contribuer

Ce projet vit par ses vérificateurs. Vous n'avez pas besoin d'être juriste ni
chercheur pour contribuer — juste rigoureux.

## Les contributions les plus utiles (par ordre)

1. **Vérifier les chiffres.** Reprenez `results/m2_baselines.json`, refaites
   tourner `scripts/m2_baselines.py`, comparez. Signalez tout écart.
2. **Casser la chaîne de données.** Un docket mal joint, un doublon non
   détecté, une affaire SCDB manquante : chaque faille documentée rend la
   mesure plus honnête. La liste des failles connues est dans
   `docs/02-CORPUS.md` et `docs/08-LIMITES.md`.
3. **Répliquer avec d'autres yeux.** Refaites le corpus avec les scripts du
   `docs/05-REPRODUCTIBILITE.md` sur votre machine, comparez les empreintes.
4. **Améliorer les scripts.** Ils sont volontairement courts et sans
   dépendances ; gardez-les ainsi.

## Règles du dépôt

- Une modification de donnée = un prédicat + un SHA-256, jamais « à la main ».
- Un changement de règle du corpus = une nouvelle version (v1 -> v2), la v1
  reste dans l'historique git.
- Les contributions qui touchent le scellé des 50 affaires seront refusées
  (voir `docs/04-PROTOCOLE.md`).

## Signaler un problème

Ouvrez une *issue* avec : ce que vous avez fait, ce que vous attendiez, ce que
vous avez obtenu, et si possible le SHA-256 du fichier concerné.
