# Legally Subjective

> **Would you have been guilty with a different judge?**

An open research project measuring whether language models can predict the
outcome of US criminal appeals — and whether the predicted outcome changes
when the simulated judge changes.

> **Disclaimer.** This project is a research simulation. It is not legal
> advice, not a prediction tool for real cases, and its results are
> exploratory, not prescriptive. Every public page of this project carries
> this disclaimer.

**Status: Phase 2 (dataset at scale).** The data pipeline is a
construction set (kernel + blocks, see `docs/vision.md`): source,
extract, validate, analyze. Over a thousand real criminal appeals are
collected, structured with evidence, and validated; the disposition
base rate is measured with confidence intervals. No model has been
run yet — no accuracy number exists, and none will be claimed until a
script reproduces it.

## Research questions

1. **RQ1 — Prediction.** Can an LLM predict the outcome of a criminal
   appeal (affirmed / reversed) from the opinion's facts and arguments?
2. **RQ2 — Learning.** Does fine-tuning on past appeals from the same
   court beat the zero-shot baseline?
3. **RQ3 — The counterfactual.** Does the predicted outcome change when
   the model is conditioned on a different judge's profile? ("The judge
   lottery", measured.)
4. **RQ4 — Bias transmission.** Does a virgin model already reproduce
   judicial leniency patterns by crime type — and does fine-tuning amplify
   or correct them?

The full pre-registered design — dataset, splits, models, metrics,
statistical tests, and the power analysis that sized the test split — is in
[`docs/protocol.md`](docs/protocol.md). Prior work and positioning are in
[`docs/precedents.md`](docs/precedents.md).

## Repository layout

```
docs/            manifest (quality gates), protocol, precedents,
                 feasibility, vision (the infinite construction set),
                 phase reports
scripts/
  lib/kernel.py            the Lego base plate: Block, Context, runner
  blocks/                  the bricks — auto-discovered capabilities
                           (source, extract, validate, analyze)
  run_pipeline.py          execute a named pipeline from config.json
  fetch_courtlistener.py   collector CLI (checkpoint, provenance log)
  preprocess.py            extraction CLI (deterministic + LLM)
  verify_data.py           validation gate CLI (also runs in CI)
  tests/                   golden regression test (the sample invariant)
  planning/power_analysis.py   McNemar power analysis (seeded)
matrix/          the Behavioral Matrix console (Phase 3): Next.js 16 +
                 Prisma/SQLite + WebGL — ten modules of real-data
                 telemetry over the corpus, zero mock by contract
data/
  sample/        5 real NY Appellate Division criminal appeals —
                 the hand-verified golden reference
  corpus/        the Phase 2 full collection (2015–2023 windows),
                 with official documents, sha256 and a full fetch log
  structured/    evidence-based structured records (sample + corpus)
  analysis/      base-rate and other measurements, with CIs
  validation/    human-review instruments (R10): samples + worksheets
config.json      all pipeline parameters and named pipelines (no
                 hardcoded data)
```

## Quickstart

```bash
pip install -r requirements.txt

# the golden invariant: the block pipeline must reproduce the
# hand-verified sample exactly (this also runs in CI)
python scripts/tests/test_golden_sample.py

# validate the committed datasets (same checks as CI)
python scripts/verify_data.py --mode sample
python scripts/verify_data.py --mode corpus

# see every available block and pipeline
python scripts/run_pipeline.py --list

# re-run the full corpus processing: extract → validate →
# base-rate analysis → human-review sample
python scripts/run_pipeline.py corpus-process

# collect a fresh 5-case sample (anonymous access works;
# a free CourtListener token raises rate limits — see .env.example)
python scripts/fetch_courtlistener.py --mode sample --reset

# with LLM enrichment (needs any OpenAI-compatible endpoint)
cp .env.example .env   # fill LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
python scripts/preprocess.py --mode sample --llm

# sizing math for the experiments
python scripts/planning/power_analysis.py
```

Adding a capability = dropping one module in `scripts/blocks/` — the
registry picks it up automatically. The worked example and the growth
protocol are in `docs/vision.md`.

## The 5-case sample (Phase 1) — the golden reference

All cases are real, published decisions of the New York Supreme Court,
Appellate Division, collected via the CourtListener search API and the
official NY slip opinions, with every HTTP request logged:

| case | date | panel | disposition (rule-extracted, LLM-confirmed) |
|---|---|---|---|
| People v. Rodriguez | 2016-01-07 | Tom, J.P. + 3 | affirmed |
| People v. Janelle | 2017-01-11 | Leventhal, J.P. + 3 | reversed |
| People v. Baxter | 2018-01-11 | Garry, P.J. + 4 | affirmed |
| People v. Alexander | 2019-01-09 | Balkin, J.P. + 3 | reversed |
| People v. Lawrence | 2020-01-02 | Lynch, J.P. + Devine + 3 | reversed |

Rule-based and LLM-based disposition extraction agreed on 5/5 cases. Each
label carries the exact sentence it was extracted from (open
`data/structured/sample_structured.jsonl` and look at `disposition.
primary_evidence`). Details, raw outputs and deviations from the original
plan: [`docs/phase1_report.md`](docs/phase1_report.md). The sample is
now the invariant of the golden regression test: any code path that
stops reproducing it fails the build.

## The corpus (Phase 2)

**1,387 real criminal appeals, 2015–2023**, same query, same gates,
same evidence discipline — 1,571 logged HTTP requests, every document
committed with its sha256, CI-validated end to end. Of those,
**1,231 carry an extracted disposition and 1,111 are binary-eligible**
(affirmed vs reversed/vacated) — enough for the pre-registered
600/400 split with 111 cases left for prompt calibration.

The protocol-required measurement, reproducible via
`python scripts/run_pipeline.py corpus-process`:

- **Base rate: 855/1,111 = 77.0% affirmed** (Wilson 95% CI
  [74.4%, 79.3%]) — the majority baseline any model must beat, and
  the class weighting for fine-tuning.
- **By department** (the first measured glimpse of the "judge
  lottery"): 2nd Dept affirms 62.4% [57.0, 67.5] vs 4th Dept
  88.0% [83.4, 91.6] — a 25.6-point spread on non-overlapping
  intervals. Different panels judging different dockets; the
  cross-judge experiment (RQ3) exists to take this apart.
- Validation status, honestly: rule-vs-LLM agreement 23/25 = 92% on a
  stratified 30-case sample (5 LLM-unknown flagged); **human review
  pending** — instrument ready in `data/validation/`.

Full yield tables, engineering decisions (Cloudflare-locked official
channel, cursor pagination, window amendment) and new limitations:
[`docs/phase2_report.md`](docs/phase2_report.md).

## Data sources and attribution

- **Metadata & discovery:** [CourtListener](https://www.courtlistener.com)
  v4 search API, operated by the Nonprofit Free Law Project. Used under
  its public-access terms; anonymous access confirmed in Phase 1.
- **Full texts:** official slip opinions published by the
  **New York State Law Reporting Bureau** (nycourts.gov, Judiciary Law
  § 431), public government documents. The corpus uses CourtListener's
  public archival copies (byte-stable) because the official host serves
  Cloudflare-instrumented responses — every case records both URLs and
  the channel actually used.
- **Historical note:** the Caselaw Access Project API (case.law), planned
  as the original data source, was sunset on **September 5, 2024**; this
  project pivoted to CourtListener accordingly (see the phase 1 report).

The committed datasets (5-case sample + 1,387-case corpus) are fully
attributed, with per-request provenance logs.

## The Behavioral Matrix console (Phase 3)

`matrix/` is the analysis layer: a French-language mission-control
console (aerospace-terminal aesthetic) that turns the Phase 2 corpus
into live telemetry — judge constellations in WebGL, per-judge
deviation matrices with Wilson CIs and z-scores, bias heatmaps by
department and year, a seeded Monte-Carlo verdict simulator over the
real binary outcomes, stylometric spectra computed on the full official
texts, a precedent co-citation mesh, decision timelines, behavioral
radars, and a human-vs-neutral-AI comparison shield whose multi-agent
sessions make real LLM calls on the official case recitals. The console
inherits the zero-mock contract: its SQLite index is built exclusively
by `matrix/scripts/ingest.ts`, which cross-validates itself against
`data/analysis/base_rate_corpus.json` on every run and refuses to start
on a mismatch. See `matrix/README.md`.

## Roadmap

- [x] Phase 0 — precedents, protocol, power analysis, feasibility
- [x] Phase 1 — collector, 5-case sample, structured extraction, CI gate
- [x] Phase 2 — corpus at scale: 1,387 cases, base rate measured,
      validation instrument ready (human review: pending, honestly)
- [ ] Phase 2b — full-corpus LLM label verification + human review of
      the 30-case sample
- [x] Phase 3 (console) — Behavioral Matrix: ten modules of real-data
      telemetry over the corpus (see `matrix/`)
- [ ] Phase 3 (experiment) — Experiment A (zero-shot) + prompt calibration
- [ ] Phase 4 — Experiment B (QLoRA fine-tuning on a free Colab T4)
- [ ] Phase 5 — judge profiles, cross-judge counterfactual, bias analysis
- [ ] Phase 6 — public site, reproducible notebook, preprint
- [ ] beyond — the extension slots of `docs/vision.md`: OCR unlocks
      2011–2014, one source brick per new jurisdiction, one extractor
      pattern per new field. The project is designed never to finish.

## Limitations

Honest and visible, per the project constitution (`docs/MANIFEST.md`, R6):

1. **Appellate outcomes are not guilt.** The label is the disposition of an
   appeal (affirmed/reversed), not first-instance guilt; a reversal can
   mean a procedural error, not innocence. Public communication must never
   conflate the two.
2. **One jurisdiction.** New York Appellate Division only, for now: one
   procedural regime, one state's practice. Generalization is untested.
3. **Demographics are limited to what the text states.** Defendant gender
   is extracted only when explicit; race/ethnicity is generally absent
   from opinions and is never inferred from names — bias analysis on race
   is therefore out of scope until a defensible source exists.
4. **Rule-based extraction has blind spots.** 156 corpus cases (11.3%)
   yielded no disposition formula and are flagged for human
   adjudication — excluded from the modeling population, visibly
   counted, never silently dropped. Older decisions (2011–2014) exist
   only as scanned PDFs; unlocking them is the OCR extension slot.
5. **LLM fields are model outputs.** Facts summaries, crime types and
   outcome cross-checks are generated, and can be wrong; that is why the
   rule label stays primary, every field carries evidence, and the
   corpus-level agreement (92% on the stratified sample) is reported
   with its disagreements, not hidden.
6. **Labels are not yet human-validated at corpus scale.** The
   30-case stratified review is drawn, LLM-cross-checked, and waiting
   for a human — until then, every corpus statistic describes the
   dataset, not judicial behavior. The Phase 1 "5/5 agreement" was a
   small-sample result; the honest corpus-scale number is 92% with
   open cases.
7. **The department spread is not an effect estimate.** The
   25.6-point 2nd-vs-4th gap mixes different dockets with different
   panels; it motivates the cross-judge experiment, it does not
   anticipate its result.

## License

Code: MIT (see `LICENSE`). Data: attributed public records as described
above, collected for research and reproducibility.

---

## En résumé (français)

**Legally Subjective** mesure, sur de vraies décisions de justice
américaines, si une IA peut prédire l'issue d'un appel criminel — et si le
verdict prédit change quand on change le juge simulé. La Phase 2 est
terminée : **1 387 appels criminels réels** (New York, Appellate
Division, 2015–2023) collectés avec provenance complète (1 571 requêtes
journalisées), extraits avec preuve par champ, validés par la CI.
La mesure exigée par le protocole est faite : **taux de confirmation
77,0 % [74,4 % ; 79,3 %]**, et un écart brut de 25,6 points entre le
2e et le 4e département (62,4 % contre 88,0 % de confirmations) — la
première mesure concrète de la « loterie des juges ». La revue humaine
de 30 cas (échantillon stratifié, contre-vérifié par LLM à 92 %) est
prête et en attente — aucun chiffre ne prétend décrire le comportement
des juges avant elle. Le pipeline est devenu un jeu de construction
(noyau + briques auto-découvertes, `docs/vision.md`) conçu pour ne
jamais être fini : OCR des années scannées, autres États, autres
champs, expériences A/B/C/D — chaque extension est une brique. Aucun
modèle n'a encore été entraîné : aucun chiffre de performance n'est
affiché, et il n'y en aura pas avant qu'un script puisse le
reproduire. Protocole complet, calculs de puissance et faisabilité du
fine-tuning (Colab gratuit) : `docs/`. Manifeste qualité :
`docs/MANIFEST.md`. Rapports : `docs/phase1_report.md`,
`docs/phase2_report.md`.

*Avertissement : simulation par IA à but de recherche — ni conseil juridique,
ni outil de prédiction pour de vraies affaires.*
