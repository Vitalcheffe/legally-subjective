# Legally Subjective

> **Would you have been guilty with a different judge?**

An open research project measuring whether language models can predict the
outcome of US criminal appeals — and whether the predicted outcome changes
when the simulated judge changes.

> **Disclaimer.** This project is a research simulation. It is not legal
> advice, not a prediction tool for real cases, and its results are
> exploratory, not prescriptive. Every public page of this project carries
> this disclaimer.

**Status: Phase 0–1 (research infrastructure).** The data pipeline is live
and validated on a 5-case sample. No model has been run, so no accuracy
number exists yet — and none will be claimed until it is reproducible by
script.

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
                 feasibility calculations, phase reports
scripts/
  fetch_courtlistener.py   collector: search API + official documents,
                           retry / rate-limit / checkpoint / provenance log
  preprocess.py            formatter: evidence-based structured extraction
  llm_extractor.py         frozen-prompt LLM field extraction
                           (any OpenAI-compatible endpoint)
  verify_data.py           data validation gate (also runs in CI)
  planning/power_analysis.py   McNemar power analysis (seeded, reproducible)
data/
  sample/        5 real NY Appellate Division criminal appeals (2016-2020),
                 with official documents, sha256 and a full fetch log
  structured/    the same 5 cases, structured (panel, disposition,
                 charge, facts — every field with its source evidence)
config.json      all pipeline parameters (no hardcoded data)
```

## Quickstart

```bash
pip install -r requirements.txt

# validate the committed sample (same check as CI)
python scripts/verify_data.py

# collect a fresh 5-case sample (anonymous access works;
# a free CourtListener token raises rate limits — see .env.example)
python scripts/fetch_courtlistener.py --reset

# structure it (deterministic extraction only)
python scripts/preprocess.py

# with LLM enrichment (needs any OpenAI-compatible endpoint)
cp .env.example .env   # fill LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
python scripts/preprocess.py --llm

# sizing math for the experiments
python scripts/planning/power_analysis.py
```

## The 5-case sample (Phase 1)

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
plan: [`docs/phase1_report.md`](docs/phase1_report.md).

## Data sources and attribution

- **Metadata & discovery:** [CourtListener](https://www.courtlistener.com)
  v4 search API, operated by the Nonprofit Free Law Project. Used under
  its public-access terms; anonymous access confirmed in Phase 1.
- **Full texts:** official slip opinions published by the
  **New York State Law Reporting Bureau** (nycourts.gov, Judiciary Law
  § 431), public government documents.
- **Historical note:** the Caselaw Access Project API (case.law), planned
  as the original data source, was sunset on **September 5, 2024**; this
  project pivoted to CourtListener accordingly (see the phase 1 report).

The committed sample is small (5 cases) and attributed; the full
1,000-case dataset will be released with the same provenance format.

## Roadmap

- [x] Phase 0 — precedents, protocol, power analysis, feasibility
- [x] Phase 1 — collector, 5-case sample, structured extraction, CI gate
- [ ] Phase 2 — collect ≥1,000 cases; manual validation on a sample
- [ ] Phase 3 — Experiment A (zero-shot) + prompt calibration
- [ ] Phase 4 — Experiment B (QLoRA fine-tuning on a free Colab T4)
- [ ] Phase 5 — judge profiles, cross-judge counterfactual, bias analysis
- [ ] Phase 6 — public site, reproducible notebook, preprint

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
4. **Rule-based extraction has blind spots.** Older decisions (some
   2011–2015 batches) exist only as scanned PDFs without text layers; the
   pipeline currently requires HTML documents. The fetch log records what
   was skipped and why.
5. **LLM fields are model outputs.** Facts summaries, crime types and
   outcome cross-checks are generated, and can be wrong; that is why the
   rule label stays primary, every field carries evidence, and the sample
   was verified by hand.
6. **Small sample.** Five cases validate the pipeline, nothing else. No
   statistic in this repository describes judicial behavior yet.

## License

Code: MIT (see `LICENSE`). Data: attributed public records as described
above, collected for research and reproducibility.

---

## En résumé (français)

**Legally Subjective** mesure, sur de vraies décisions de justice
américaines, si une IA peut prédire l'issue d'un appel criminel — et si le
verdict prédit change quand on change le juge simulé. La Phase 1 est
terminée : pipeline de collecte (CourtListener + opinions officielles de
l'État de New York), échantillon réel de 5 affaires (2016-2020), extraction
structurée avec preuve pour chaque champ, validation croisée règle/LLM
(5/5), et contrôle automatique en CI. Aucun modèle n'a encore été entraîné :
aucun chiffre de performance n'est affiché, et il n'y en aura pas avant
qu'un script puisse le reproduire. Le protocole complet, les calculs de
puissance statistique et la faisabilité du fine-tuning (Colab gratuit) sont
dans `docs/`. Le manifeste qualité du projet est `docs/MANIFEST.md`.

*Avertissement : simulation par IA à but de recherche — ni conseil juridique,
ni outil de prédiction pour de vraies affaires.*
