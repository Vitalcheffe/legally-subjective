# Legally Subjective (English)

> **Subjectivity, measured.** — Measuring the upper bound of predictability
> in U.S. Supreme Court decisions, using public data and a zero-euro budget.

[English readme — the primary documentation is in French.](README.md)

## The question

Can a language model predict a judge's decision from the case file alone,
without the verdict? And if we teach it one specific judge's *style* — their
persona — does it get better on that judge's **future** cases? Both outcomes
publish:

1. **Yes** — the persona is extractible from public text; judicial
   subjectivity leaves a measurable footprint.
2. **No** — the personality is not in the data; the measure itself is the
   contribution.

## What's in this repository (M1+M2)

| Item | Content |
|---|---|
| `data/processed/corpus_cases_v1.jsonl.gz` | **Frozen Corpus-Monde v1**: 569 argued Supreme Court cases (OT2015–2023), CourtListener metadata + SCDB votes fused |
| `data/processed/corpus_opinions_v1.jsonl.gz` | Inventory of 1,778 opinions |
| `data/processed/corpus_justices_v1.jsonl.gz` | ~5,000 justice×case vote rows |
| `data/processed/stats_v1.json` | Corpus rule, statistics, **50 sealed 5-4 cases** |
| `data/raw/provenance/` | SHA-256 of every raw source + exact filter predicates |
| `results/m2_baselines.{json,md}` | M2 statistical baselines with Wilson 95% intervals |
| `scripts/` | The full, reproducible collection and build chain |
| `src/`, `public/`, `prisma/` | **The site** (Next.js): THE DRAW storefront, the questions, /paper, /standard, case pages and judge comparisons |

### Baselines to beat (test set OT2020–2023)

| Baseline | Accuracy | 95% CI |
|---|---|---|
| Majority class | 43.6% | [37.2; 50.1] |
| Always conservative | 56.4% | [49.9; 62.8] |
| Always reverse | 60.1% | [51.8; 67.9] |
| Per-justice ideology (vote) | 63.7% | [61.3; 65.9] |
| Per-justice ideology (case) | 55.8% | [49.3; 62.2] |

## Principles

- **Zero euros, forever**: free Colab/Kaggle GPUs, public data, no paid
  services.
- **Amateur, seriously**: playable and checkable by anyone; rigorous enough
  for a researcher.
- **Total provenance**: every file hashable, every rule a predicate, every
  exception documented.
- **No commercialization**.

## Documentation

`docs/00-VISION.md` through `docs/09-RESSOURCES.md` (in French — the project's
working language). `docs/05-REPRODUCTIBILITE.md` contains the full rebuild
chain. `docs/09-RESSOURCES.md` maps public legal data sources across
jurisdictions, for replication or extension.

## Run the site locally

```bash
npm ci
npm run dev        # http://localhost:3000
```

Note: the site displays the sealed record of the audited experiment
(LS-J-001…009, 237 decided cases); the frozen research corpus v1 (569
cases) lives in `data/processed/`. The site will be rewired to the new
corpus once M3 training produces its results.

## Data sources

- [CourtListener](https://www.courtlistener.com) (Free Law Project)
- [Supreme Court Database](http://scdb.wustl.edu) (SCDB 2025_01)

## Cite

```bibtex
@software{harch_el_korane_2026_legally,
  author = {Amine Harch el Korane},
  title = {Legally Subjective: Subjectivity, measured},
  year = {2026},
  url = {https://github.com/Vitalcheffe/legally-subjective},
}
```
