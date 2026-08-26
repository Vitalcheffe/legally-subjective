# MANIFESTE — Constitution du projet Legally Subjective

> « Est-ce que vous auriez été coupable avec un autre juge ? »

Ce document est la constitution du projet. Il encode tout ce que l'expérience
des projets précédents a enseigné, sous forme de règles non négociables. Tout
commit qui viole une de ces règles est un bug, même si le code fonctionne.

## 1. Mission

Legally Subjective mesure, sur de vraies décisions de justice américaines :

1. **RQ1 — Prédiction.** Un LLM peut-il prédire l'issue d'un appel criminel
   (confirmé / infirmé) à partir du seul texte de la décision ?
2. **RQ2 — Apprentissage.** Un modèle fine-tuné sur des centaines d'affaires
   passées bat-il le même modèle vierge (zero-shot) ?
3. **RQ3 — Contrefactuel.** Le verdict prédit change-t-il selon le juge
   simulé ? (L'expérience croisée : « l'affaire du juge X jugée par le
   profil du juge Y ».)
4. **RQ4 — Transmission des biais.** Le modèle vierge reproduit-il les biais
   des juges ? Le modèle qui apprend les amplifie-t-il ou les corrige-t-il ?

Public visé : publication académique (arXiv), outil public, vidéo de
vulgarisation. Niveau d'exigence : celui des précédents analysés dans
`docs/precedents.md` (COMPAS/ProPublica, Gender Shades, Moral Machine).

## 2. Rôles

- **Amine (ingénierie)** : pipeline de données, modèles, infrastructure.
- **Partenaire droit** : relecture et validation de toute interprétation
  juridique avant publication. Une affirmation juridique non validée ne
  sort pas.

## 3. Règles de qualité — R1 à R10

Chaque règle existe parce qu'une erreur équivalente a déjà coûté cher.

- **R1 — Zéro mock data.** Toute donnée provient d'une source publique
  réelle et traçable (API ou document officiel). Aucune donnée inventée,
  même « pour tester ». Les tests utilisent des extraits réels.
- **R2 — Zéro donnée hardcodée.** Endpoints, requêtes, filtres, fenêtres de
  dates, seuils : tout vit dans `config.json` ou dans les arguments CLI.
  Le code ne contient aucun paramètre déguisé en constante.
- **R3 — README honnête.** Aucun chiffre publié qui ne soit reproductible
  par script. Le statut affiché reflète la phase réelle. Pas de badge
  d'accuracy tant qu'il n'y a pas d'accuracy.
- **R4 — Historique git propre.** Commits atomiques, messages
  conventionnels, chaque commit raconte une étape compréhensible. Pas de
  commit fourre-tout, pas d'historique réécrit après push.
- **R5 — Pas de AI slop.** Prose naturelle et sobre, pas de mot-valise, pas
  d'emoji-décoration. Le code est documenté, typé, et se lit comme écrit
  par quelqu'un qui comprend ce qu'il écrit.
- **R6 — Limitations honnêtes.** Au moins cinq limitations réelles,
  documentées, visibles. Une limitation cachée est un mensonge différé.
- **R7 — Disclaimer permanent.** « Simulation par IA, pas une prédiction
  juridique. Résultats exploratoires, non prescriptifs. » — visible sur
  chaque rendu public (README, site, notebook, vidéo).
- **R8 — Preuve exigée.** Tout champ extrait automatiquement embarque sa
  preuve (`evidence` : la phrase source) et sa méthode. Un chiffre sans
  preuve est une opinion.
- **R9 — Reproductibilité.** Chaque étape est relançable depuis zéro :
  scripts + config + journal de provenance (`FETCH_LOG`). Un résultat qu'on
  ne peut pas régénérer n'existe pas.
- **R10 — Validation humaine.** Tout échantillon est vérifié à la main
  avant d'être étendu à l'échelle. Le partenaire droit valide la partie
  juridique avant toute publication.

## 4. Principes de communication

- **Sous-promettre, sur-livrer.** Les claims restent sobres ; les preuves
  sont écrasantes. On ne promet jamais ce que les données n'ont pas encore
  montré.
- **La question d'accroche** : « Est-ce que vous auriez été coupable avec
  un autre juge ? » — posée avec le disclaimer, toujours.
- **Chiffre-vedette** : il sortira des données (expérience croisée), pas
  d'un brainstorm. On ne l'invente pas, on le découvre.
- On ne survend jamais la fiabilité de l'IA : on montre des intervalles de
  confiance, des limitations, et on laisse les chiffres parler.

## 5. Phases

| Phase | Contenu | Statut |
|---|---|---|
| 0 | Précédents, positionnement, protocole, calculs | terminé |
| 1 | Accès APIs vérifiés, échantillon de 5 cas réels, pipeline preprocessing | terminé |
| 2 | Collecte 1000 affaires (train/test), validation manuelle par échantillon | à venir |
| 3 | Expérience A (zero-shot) + calibration de prompt | à venir |
| 4 | Expérience B (QLoRA sur Colab T4) | à venir |
| 5 | Profilage des juges + expérience croisée + analyse de biais | à venir |
| 6 | Site interactif, notebook public, préprint arXiv, vidéo | à venir |

## 6. Gates avant publication publique

Aucune ligne ne devient publique tant que :

- [ ] le notebook tourne sur Colab T4 gratuit du premier coup ;
- [ ] le README ne ment sur aucun chiffre (vérifié par script) ;
- [ ] zéro mock data, zéro donnée hardcodée (audit R1/R2) ;
- [ ] la section Limitations compte au moins cinq items honnêtes ;
- [ ] le partenaire droit a relu et validé la partie juridique ;
- [ ] un humain non technique peut suivre le notebook et utiliser le site ;
- [ ] le disclaimer R7 est visible sur chaque page publique ;
- [ ] l'historique git est propre et lisible (R4).

## 7. Décisions fondatrices

- **Nom** : Legally Subjective.
- **Juridiction pilote** : New York, Appellate Division (appels criminels).
  Choix justifié dans `docs/protocol.md` (volume, qualité des documents
  officiels, identification des panels de juges).
- **Source primaire de données** : CourtListener (API de recherche, accès
  anonyme confirmé) + documents officiels du New York State Law Reporting
  Bureau. L'API du Caselaw Access Project (case.law), prévue initialement,
  a été fermée le 5 septembre 2024 — pivot documenté dans
  `docs/phase1_report.md`.
- **Étiquette de prédiction** : l'issue de l'appel (confirmé / infirmé /
  annulé…), extraite du texte officiel, avec preuve — pas la « culpabilité »
  au premier degré, qui n'est pas observable sur des décisions d'appel.
