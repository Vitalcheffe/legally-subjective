# Behavioral Matrix — cognitive analysis console

> **Console d'analyse cognitive judiciaire** over the legally-subjective
> corpus: 1,387 real NY Appellate Division criminal appeals (2015–2023),
> collected and validated by the Phase 2 pipeline.

A Next.js 16 + Prisma/SQLite + three.js/WebGL + Recharts application.
French-language mission-control UI, aerospace-terminal aesthetic, eleven
modules of real-data telemetry — including a full experimental protocol
engine (Phase 4).

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
- **The experimental protocol engine (module 10)** draws a seeded stratified
  sample of real cases, has the multi-agent engine render blind verdicts
  (the human decision is never shown to the agents), and scores them with
  exact statistics (Wilson, Brier, calibration buckets, exact McNemar).
  Engine rate-limit failures are retried with backoff, then archived
  verbatim and re-playable — never faked.

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
| 10 | Laboratoire expérimental | seeded stratified zero-shot protocol · Wilson · Brier · calibration · exact McNemar |

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
- **R1b** Panel completion (Phase 4 discovery): for the 1st/4th Dept formats
  the Phase 2 corpus omits the presiding judge from `panel.judges[]` even
  though the official panel evidence line carries him with the `J.P.`/
  `P.J.` title. The presiding surname is re-extracted from the evidence
  line and added as a presiding seat when absent (494 records healed —
  real official-panel data, not inference).
- **R7** Author attribution (Phase 4): `explicit` for signed opinions
  ("NAME, J." body signature, cross-validated against panel membership),
  `presumed-presiding` for unsigned memoranda (NY LRB convention, surfaced
  as presumed in the UI), `per-curiam` and `unresolved` recorded honestly
  as null. Coverage: 1,206/1,387 opinions (87 %).

## Phase 4 — the experimental protocol (module 10)

The console is now a laboratory, not just an observatory:

- **Inclusion criteria (RCT-style, documented in the UI)**: binary-eligible
  real case + official recital excerpt ≥ 120 chars (the agents need the
  real facts; the exclusion is surfaced, not hidden). Pool: 613 of the
  1,111 binary cases.
- **Seeded stratified sampling**: proportional allocation over department ×
  binary outcome, Fisher-Yates draw seeded by FNV-1a(`sample:<seed>:<N>`) —
  same seed = same sample, bit for bit.
- **Blind adjudication**: Prosecutor → Defender → AI-Judge deliberate on
  the official recital; the human disposition is never part of the prompt.
- **Scoring**: agreement + Wilson 95 % CI, 2×2 confusion matrix, Brier score
  vs a base-rate predictor, reliability-diagram calibration buckets, exact
  McNemar test vs the always-affirm baseline, per-department agreement.
- **Resilience**: engine 429s are retried with backoff (20 s/45 s); if the
  quota is exhausted the failures are archived verbatim and a REPLAY
  button re-queues them once the window resets.

First validation run (n=5, seed 42): 5/5 agreement, Brier 0.004 (vs 0.160
for the base-rate predictor). First n=20 run hit the engine rate limit
after 5 sessions — 15 verbatim 429 errors archived, replayable. Both
behaviors are by design: no data is ever invented.

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

- ~~Panel-level aggregation~~ — **solved in Phase 4**: R7 extracts
  per-opinion authorship (87 % coverage); module 02 exposes an ÉCRITS
  (authored) column separating the writing judge from panel presence.
  The remaining 13 % are honestly recorded as unresolved/per-curiam.
- Stylometry is aggregated by department/year (author-level stylometry is
  now possible via R7 and planned as an extension).
- Module 07's month-of-year view is a chronobiological PROXY (filing
  dates, not hearing times).
- Module 09's Δ_humain measures model-vs-human divergence on one case;
  it is not proof of bias.
- Module 10's protocol measures agreement/calibration on cases with an
  extractable recital; it does not claim the AI reasons like a judge —
  only that its verdicts are statistically comparable on this corpus.

Research disclaimer: exploratory analytics on public legal documents.
Not legal advice, not a prediction tool for real cases.
