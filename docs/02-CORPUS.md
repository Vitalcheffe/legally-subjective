# Corpus-Monde v1 — la règle, les chiffres, les failles

## La règle (gelée le 2026-08-28)

Une affaire entre dans le Corpus-Monde v1 si et seulement si :

1. **Cour** : Supreme Court of the United States ;
2. **Plaidée** : date de plaidoirie entre le 2015-10-01 et le 2024-06-30 —
   source SCDB (`dateArgument`, édition 2025_01) *ou* CourtListener
   (`docket.date_argued`) ;
3. **Décision dans la fenêtre** : au moins une grappe d'opinions CourtListener
   datée (`dateFiled`) entre le 2015-10-01 et le 2024-07-31 ;
4. **Identité d'affaire** : jetons de docket normalisés (les dockets dupliqués
   de CourtListener se recollent en une seule affaire).

Cela couvre **9 mandats** : OT2015 à OT2023.

## Les chiffres

| Indicateur | Valeur |
|---|---|
| Affaires | **569** |
| Opinions (inventaire) | **1 778** |
| Avec votes SCDB | 547 (96,1 %) |
| Décisions 5-4 | 79 (SCDB en recense 80) |
| Avec plaidoirie audio + transcription | 561 (98,6 %) |
| Groupes fantômes écartés | 26 |

Par mandat (affaires / opinions / 5-4) :

| Mandat | Affaires | Opinions | 5-4 |
|---|---|---|---|
| OT2015 | 72 | 294 | 0 |
| OT2016 | 69 | 247 | 3 |
| OT2017 | 65 | 235 | 18 |
| OT2018 | 72 | 265 | 18 |
| OT2019 | 60 | 263 | 11 |
| OT2020 | 56 | 130 | 7 |
| OT2021 | 62 | 86 | 11 |
| OT2022 | 55 | 117 | 7 |
| OT2023 | 58 | 141 | 4 |

L'absence de 5-4 en OT2015 est **réelle** : après le décès du juge Scalia
(février 2016), le mandatum a produit des égalités 4-4 et des décisions
déséquilibrées, presque aucune décision 5-4 stricte (vérifié sur SCDB).

## Architecture des données

```
Corpus-Monde v1
├── data/processed/corpus_cases_v1.jsonl.gz      569 lignes, 1 par affaire
│     • identité (docket, nom, dates, mandat)
│     • grappes CourtListener (cluster_ids, canonique)
│     • SCDB fusionné (votes, direction, disposition, rédacteur)
│     • inventaire opinions + plaidoiries audio
├── data/processed/corpus_opinions_v1.jsonl.gz   1 778 lignes (inventaire)
├── data/processed/corpus_justices_v1.jsonl.gz   ~5 000 lignes juge×affaire
└── data/processed/stats_v1.json                 règle + stats + scellement
```

## Provenance (empreintes SHA-256)

Chaque source est identifiée par son URL, sa date et son SHA-256 dans
`data/processed/stats_v1.json` (champ `source_sha256`) :

| Source | Empreinte (début) |
|---|---|
| `dockets-2026-06-30.csv.bz2` (bulk CourtListener) | `1396df61…` |
| `opinion-clusters-2026-06-30.csv.bz2` (bulk) | `bddbd5ca…` |
| `oral-arguments-2026-06-30.csv.bz2` (bulk) | `4abc95c3…` |
| `SCDB_2025_01_justiceCentered_Citation.csv.zip` | `c7a41b1e…` |
| Résultats de recherche v4 (collecte du 2026-08-28) | voir stats_v1.json |

## Les failles connues (transparence totale)

1. **Le bulk `opinion-clusters` de CourtListener ne couvre pas les grappes
   SCOTUS postérieures à ~2015.** Les métadonnées de grappes récentes
   proviennent donc de l'API de recherche v4 (accès anonyme), collectée le
   2026-08-28. La chose est consignée ; quiconque rejette cette source peut
   reconstruire avec les mêmes scripts.
2. **Les fichiers bulk du 2026-06-30 sont tronqués à la fin côté S3** (pas de
   marqueur de fin bzip2). L'impact documenté : dernière tranche
   indécompressable (≈ 0,1-1,5 % selon le fichier), sans effet sur le corpus —
   vérifié par la couverture SCDB (547/555 affaires plaidées couvertes).
3. **22 affaires sans votes SCDB** : essentiellement des requêtes *in forma
   pauperis* plaidées que SCDB ne code pas. Elles restent dans le corpus pour
   l'entraînement textuel ; elles sont exclues des analyses de votes.
4. **8 affaires SCDB sans contrepartie corpus** (listées dans stats_v1.json) :
   5 compétences d'origine + 3 affaires aux grappes introuvables par recherche.
5. **Doublons d'opinions** : CourtListener stocke souvent le même *slip
   opinion* en plusieurs exemplaires (sha1 différents). L'inventaire M1 les
   garde tous ; la déduplication de texte se fait au nettoyage (M1.5) par
   similarité — la bonne couche pour ça.

## Le scellement des 50 affaires 5-4

Parmi les 79 décisions 5-4, 50 sont tirées par échantillonnage aléatoire
déterministe (Random Mersenne-Twister, graine = SHA-256 de la liste triée des
identifiants). La liste est scellée par SHA-256 dans `stats_v1.json`
(`five_four_selection.sealed_sha256`). Ces 50 affaires forment le jeu de
l'Épreuve Finale — évalué une seule fois (`docs/04-PROTOCOLE.md`).
