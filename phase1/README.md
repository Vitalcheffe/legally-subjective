# Phase 1 — Étage 1 du Projet Manhattan : le socle

Le dataset de l'expérience **Modèle A (vierge) vs Modèle B (qui apprend)**.
Voir la roadmap complète : [`archives/manhattan-roadmap.md`](../archives/manhattan-roadmap.md).

## Contenu

| Chemin | Rôle |
|---|---|
| `scripts/fetch_courtlistener.py` | le collecteur — appels criminels réels depuis CourtListener v4 + slip opinions NY, gate criminelle, checkpoint, FETCH_LOG |
| `scripts/preprocess.py` + `scripts/blocks/` + `scripts/lib/` | le preprocessing déterministe — panel, disposition, charge, juges du procès, récit des faits (aucun LLM requis) |
| `scripts/tests/test_golden_sample.py` | le test de régression doré — 5 affaires vérifiées à la main (R10), l'extraction doit les reproduire exactement |
| `data/corpus/` | 1 677 affaires collectées : index `cases.jsonl`, documents HTML sources (sha256), `FETCH_LOG.json` (chaque requête HTTP) |
| `data/sample/` | l'échantillon stratifié initial (5 affaires, vérifiées à la main) |
| `data/structured/` | extraction structurée complète (`corpus_structured.jsonl`, 1 677 enregistrements) + l'échantillon doré |
| `data/analysis/base_rate_corpus.json` | statistiques réelles du corpus (base rates par disposition, intervalles de Wilson) |
| `dataset/` | **le dataset A/B livré** : `train.jsonl` (600), `test.jsonl` (400), `split_report.json` |
| `colab/manhattan_stage1_ab.ipynb` | l'expérience complète sur Colab T4 : A zero-shot vs B QLoRA, gate ±5 points |
| `config.json` | configuration du collecteur (fenêtres 2015-2025, cibles, gate criminelle) |

## Provenance

Restauré depuis la branche `origin/archive/pre-rebuild` (collecte initiale du
2026-08-26 : 1 387 affaires), étendu le 2026-08-27 (+290 affaires, fenêtres
2024-2025). Source : CourtListener API v4 (recherche) et CourtListener
Storage / NY State Law Reporting Bureau (documents). Chaque affaire porte
ses URI, son sha256 et l'horodatage de récupération.

## Reproduire

    cd phase1
    python3 scripts/tests/test_golden_sample.py    # concordance 5/5
    python3 scripts/fetch_courtlistener.py --mode corpus --dry-run
    python3 scripts/preprocess.py --mode corpus
    cd .. && python3 scripts/phase1_build_dataset.py

Puis ouvrir `colab/manhattan_stage1_ab.ipynb` dans Google Colab (T4) pour
l'expérience A vs B. Dépendances : `requests` (collecte), stdlib (le reste).

## Règles de sanitisation du texte livré (R1-R5)

Le texte donné au modèle est « l'affaire telle qu'un lecteur la voit AVANT
la décision » : décret coupé au premier « Ordered that » (R1), panel retiré
— bloc d'en-tête et ligne de concurrence (R2/R2b), verdicts en ligne retirés
(R3), **gate anti-fuite : toute occurrence résiduelle d'un mot de verdict
exclut l'affaire — zéro fuite par construction, vérifiée sur chaque texte**
(R4), longueur ≥ 200 caractères (R5). Détails et mesures :
`dataset/split_report.json`.
