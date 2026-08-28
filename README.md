# Legally Subjective

> **Subjectivity, measured.** — Mesurer le plafond de prévisibilité des décisions
> de la Cour suprême des États-Unis, avec des données publiques et un budget de
> zéro euro.

[![Statut](https://img.shields.io/badge/M1-corpus_gelé-brightgreen)](docs/07-ROADMAP.md)
[![Licence code](https://img.shields.io/badge/code-MIT-blue)](LICENSE)
[![Licence données](https://img.shields.io/badge/données-CC_BY_4.0-blue)](LICENSE)
[![Coût](https://img.shields.io/badge/coût-0_€_pour_toujours-success)](docs/00-VISION.md)

## La question

Un modèle de langage peut-il prédire la décision d'un juge à partir du dossier,
sans connaître le verdict ? Et si on lui apprend le « style » d'un juge
précis — son persona — devient-il meilleur sur **les affaires futures** de ce
juge ? Deux résultats sont publiez-zéro-euro :

1. **Oui** : le persona est extractible des textes publics → la subjectivité
   judiciaire est en partie mesurable, quantifiable, reproductible.
2. **Non** : le persona n'apporte rien au-delà du style → l'essentiel de la
   décision n'est pas dans les données publiques.

Dans les deux cas, la mesure elle-même est le résultat.

## Ce qu'il y a dans ce dépôt (M1+M2)

| Élément | Contenu |
|---|---|
| `data/processed/corpus_cases_v1.jsonl.gz` | **Corpus-Monde v1 gelé** : 569 affaires plaidées de la Cour suprême (OT2015–OT2023), métadonnées CourtListener + votes SCDB fusionnés |
| `data/processed/corpus_opinions_v1.jsonl.gz` | Inventaire de 1 778 opinions (majorités, dissidences, concurrences) |
| `data/processed/corpus_justices_v1.jsonl.gz` | ~5 000 lignes juge×affaire : vote, opinion, direction (SCDB 2025_01) |
| `data/processed/stats_v1.json` | Règle du corpus, statistiques, **50 décisions 5-4 scellées** (SHA-256) |
| `data/raw/provenance/` | SHA-256 de chaque source brute + prédicats de filtre exacts |
| `results/m2_baselines.{json,md}` | Baselines statistiques M2 avec intervalles de confiance Wilson 95 % |
| `scripts/` | Toute la chaîne de collecte et de construction, reproductible |

### Le corpus en trois chiffres

- **569 affaires** plaidées, 9 mandats (OT2015–OT2023), 96,1 % avec votes SCDB
- **79 décisions 5-4** ; 50 d'entre elles sont scellées pour l'Épreuve Finale
- **98,6 %** des affaires ont leur plaidoirie audio + transcription (pipeline
  prêt pour les conditions multimodales)

### Les baselines à battre (M2, jeu de test OT2020–2023)

| Baseline | Précision | IC 95 % |
|---|---|---|
| Classe majoritaire | 43,6 % | [37,2 ; 50,1] |
| Toujours conservateur | 56,4 % | [49,9 ; 62,8] |
| Toujours infirmer | 54,9 % | [47,9 ; 61,7] |
| Idéologie par juge (vote) | 63,7 % | [62,3 ; 65,0] |
| Idéologie par juge (affaire) | 55,8 % | [49,3 ; 62,2] |

Détail : [`results/m2_baselines.md`](results/m2_baselines.md)

## Les quatre conditions de l'expérience

| Condition | Description |
|---|---|
| **A — Zéro-coup** | Llama 3 8B, invité à décider à partir du dossier, sans aucun apprentissage propre |
| **B — Persona** | le même modèle, affiné QLoRA sur les opinions **passées** d'un juge ; testé sur ses affaires **futures** |
| **C — Contexte** | le même modèle + récupération d'opinions antérieures similaires (RAG) |
| **D — Statistique** | les baselines ci-dessus |

**Le test décisif** : B > A sur des affaires futures jamais vues ⟹ le persona
est extractible. B = A ⟹ la personnalité du juge n'est pas dans les données
publiques. Les deux issues sont des résultats.

## Reproduire

```bash
git clone https://github.com/Vitalcheffe/legally-subjective.git
cd legally-subjective
# vérifier l'intégrité du corpus
python3 - <<'EOF'
import gzip, json
stats = json.load(open('data/processed/stats_v1.json'))
print(stats['n_cases'], 'affaires |', stats['n_opinions'], 'opinions')
print('scellé 5-4 :', stats['five_four_selection']['sealed_sha256'])
EOF
```

La chaîne complète de reconstruction (téléchargements bulk → filtres → corpus)
est documentée dans [`docs/05-REPRODUCTIBILITE.md`](docs/05-REPRODUCTIBILITE.md).

## Principes

- **Zéro euro, pour toujours** : Colab/Kaggle gratuits, données publiques,
  aucun service payant.
- **Amateur, sérieusement** : jouable, critiquable, vérifiable par n'importe
  qui — et assez rigoureux pour intéresser un chercheur.
- **Provenance totale** : chaque fichier a son SHA-256, chaque règle son
  prédicat, chaque exception sa note.
- **Pas de commercialisation** : ni produit, ni paywall, ni donnée privée.

## Documentation

| Document | Contenu |
|---|---|
| [`docs/00-VISION.md`](docs/00-VISION.md) | La question, l'éthique, le positionnement |
| [`docs/01-METHODOLOGIE.md`](docs/01-METHODOLOGIE.md) | Les quatre conditions, le test décisif |
| [`docs/02-CORPUS.md`](docs/02-CORPUS.md) | La règle du corpus, ses statistiques, ses failles connues |
| [`docs/03-BASELINES.md`](docs/03-BASELINES.md) | Les baselines M2 et leur lecture |
| [`docs/04-PROTOCOLE.md`](docs/04-PROTOCOLE.md) | L'Épreuve Finale : scellement, pré-enregistrement |
| [`docs/05-REPRODUCTIBILITE.md`](docs/05-REPRODUCTIBILITE.md) | Reconstruire tout, vérifier les hachages |
| [`docs/06-ETHIQUE.md`](docs/06-ETHIQUE.md) | Données publiques, contre-factuels étiquetés |
| [`docs/07-ROADMAP.md`](docs/07-ROADMAP.md) | Où on en est, où on va |
| [`docs/08-LIMITES.md`](docs/08-LIMITES.md) | Ce que ce projet ne peut pas prouver |

## Citer

```bibtex
@software{harch_el_korane_2026_legally,
  author = {Amine Harch el Korane},
  title = {Legally Subjective: Subjectivity, measured},
  year = {2026},
  url = {https://github.com/Vitalcheffe/legally-subjective},
}
```

## Sources des données

- [CourtListener](https://www.courtlistener.com) (Free Law Project) — dockets,
  opinions, plaidoiries, transcriptions. Fichiers bulk du 2026-06-30 + API v4.
- [Supreme Court Database (SCDB)](http://scdb.wustl.edu) — votes par juge,
  directions de décision, édition 2025_01.
- Toutes les données sont publiques ; voir `data/raw/provenance/` pour les
  empreintes exactes.
