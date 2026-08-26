# Behavioral Matrix — cognitive analysis console

> **Console d'analyse cognitive judiciaire** over the legally-subjective
> corpus: 1,387 real NY Appellate Division criminal appeals (2015–2023),
> collected and validated by the Phase 2 pipeline.

A Next.js 16 + Prisma/SQLite + three.js/WebGL + Recharts application.
French-language mission-control UI, aerospace-terminal aesthetic, ten
modules of real-data telemetry.

## The zero-mock contract

This console is structurally incapable of displaying fabricated data:

- **Every number** is computed from the SQLite index, which is populated
  exclusively by `scripts/ingest.ts` from the validated corpus
  (`data/structured/corpus_structured.jsonl` + the official opinion
  documents). The ingestion re-validates itself against
  `data/analysis/base_rate_corpus.json` and exits non-zero on any
  mismatch (records, binary split, per-year, per-department).
- **No hard-coded judges or cases.** No `Math.random()` anywhere in the
  UI. The only stochastic component is the seeded bootstrap of module 04
  (Monte-Carlo over REAL observed outcomes — mulberry32, seed = FNV-1a
  hash of the filter, fully reproducible).
- **Missing data produces honest states**: "EN ATTENTE DE FLUX DE
  DONNÉES RÉELLES" or an explicit error, never a placeholder value.
- **The multi-agent engine (module 09)** makes real LLM calls
  (z-ai-web-dev-sdk backend binding). Sessions that fail are archived as
  errors with the verbatim failure — no simulated reasoning.

## Modules

| Code | Module | Real data source |
|------|--------|------------------|
| 00 | Synoptique de mission | corpus counts, base rate + Wilson CI |
| 01 | Carte neuro-cognitive (WebGL) | co-panel graph, 147 judges, 5,748 seats |
| 02 | Matrice des écarts | per-judge rates, z-scores, deviation flags |
| 03 | Carte thermique des biais | dept×year and judge×year rate matrices |
| 04 | Simulateur Monte-Carlo | seeded bootstrap over filtered real outcomes |
| 05 | Spectre stylométrique | lexical telemetry on full opinion texts |
| 06 | Graphe de jurisprudence (WebGL) | regex-extracted citations, co-citation mesh |
| 07 | Chronologie cognitive | monthly volume/rate telemetry, month-of-year proxy |
| 08 | Radar de déviation | 6-axis percentiles among eligible judges |
| 09 | Bouclier humain vs IA | real LLM sessions vs real human dispositions |

## Ingestion rules (documented determinism)

- **R1** Judge identity = normalized surname of the official panel line
  (junk tokens `P.J./J.P./JJ/AND/Department` dropped, casing and suffixes
  normalized; raw variants preserved in the index).
- **R2** Department = byte-identical regex to the repo's
  `analyze_base_rate` block — the index always agrees with the validated
  analysis; unmatched stays `unknown`.
- **R3** Opinion text = document HTML minus `<script>/<style>`, tags
  stripped, entities decoded.
- **R4** Stylometry (tokens, sentences, TTR, punitive/rehabilitative
  lexicons) computed on R3 text; lexicons documented in the script.
- **R5** Cited authorities = deterministic regex (NY case citations +
  statutory references).
- **R6** Cross-validation vs `base_rate_corpus.json` on every run.

## Quickstart

```bash
cd matrix
bun install                 # or pnpm/npm install
cp .env.example .env
bun run db:push             # create the SQLite schema
bun scripts/ingest.ts       # build the index from ../data (validates itself)
bun run dev                 # http://localhost:3000
```

The ingestion prints a PASS/FAIL table; it must print `ALL CHECKS
PASSED` before the console is trustworthy.

## Honest limitations (inherited + specific)

- Panel-level aggregation: the pipeline does not extract per-opinion
  authorship, so judge rates are the rates of panels the judge sat on
  (documented in the UI of modules 01/02/08).
- Stylometry is aggregated by department/year for the same reason.
- Module 07's month-of-year view is a chronobiological PROXY (filing
  dates, not hearing times).
- Module 09's Δ_humain measures model-vs-human divergence on one case;
  it is not proof of bias.

Research disclaimer: exploratory analytics on public legal documents.
Not legal advice, not a prediction tool for real cases.
