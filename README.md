# Legally Subjective

> **Would you have been guilty with a different judge?**

An open research project measuring whether language models can predict the
outcome of US criminal appeals — and whether the predicted outcome changes
when the simulated judge changes.

> **Disclaimer.** This project is a research simulation. It is not legal
> advice, not a prediction tool for real cases, and its results are
> exploratory, not prescriptive. Every public page of this project carries
> this disclaimer.

**Status: Phase 7 (delivered — corpus, laboratory, public interface, hardening).**
The research core is built and measured: the Phase 2 corpus (1,387 real
criminal appeals), the Phase 3–4 Behavioral Matrix laboratory (eleven
modules, zero-mock by contract, first blind result **13/16 = 81.2 %
agreement vs the 68.8 % always-affirm baseline**), the Phase 5 institutional
light theme, and since Phase 6 a public read-only interface — **INFINITUM
Mail, « La Boîte de la Cour »** (every decision reads as an email, judges
are contacts, published findings are system reports). Phase 7 secured the
record: the verbatim multi-agent sessions are archived and versioned
in-repo (`data/archive/science/`), the public sandbox is rate-limited, and
every dossier is shareable by public deep link. Human review of the
30-case sample is still pending — honestly.

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
matrix/          the Behavioral Matrix laboratory + INFINITUM Mail, the
                 public interface (Phases 3–6): Next.js 16 +
                 Prisma/SQLite + WebGL — eleven modules of real-data
                 telemetry over the corpus, zero mock by contract
data/
  sample/        5 real NY Appellate Division criminal appeals —
                 the hand-verified golden reference
  corpus/        the Phase 2 full collection (2015–2023 windows),
                 with official documents, sha256 and a full fetch log
  structured/    evidence-based structured records (sample + corpus)
  analysis/      base-rate and other measurements, with CIs
  archive/       the P0 science archive (Phase 7): every multi-agent
                 session VERBATIM (40 runs, failures included), the
                 experiment protocols and ledgers — JSONL + sha256
                 manifest, versioned in git because the live SQLite
                 index is gitignored
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

## The Behavioral Matrix laboratory (Phases 3–7)

`matrix/` is the analysis layer: a French-language institutional console
(warm ivory paper, ink navy — the « Codex » light theme of Phase 5) that
turns the Phase 2 corpus into live telemetry — judge constellations in
WebGL, per-judge deviation matrices with Wilson CIs and z-scores, bias
heatmaps by department and year, a seeded Monte-Carlo verdict simulator
over the real binary outcomes, stylometric spectra computed on the full
official texts, a precedent co-citation mesh, decision timelines,
behavioral radars, and a human-vs-neutral-AI comparison shield whose
multi-agent sessions make real LLM calls on the official case recitals.
The console inherits the zero-mock contract: its SQLite index is built
exclusively by `matrix/scripts/ingest.ts`, which cross-validates itself
against `data/analysis/base_rate_corpus.json` on every run and refuses to
start on a mismatch. See `matrix/README.md`.

Phase 4 turned the console into a laboratory: **module 10 (Laboratoire
expérimental)** runs a zero-shot protocol — seeded stratified sampling
(613-case eligible pool, proportional over department × outcome), blind
multi-agent adjudication (the human decision is never in the prompt),
and exact scoring (Wilson CI, Brier, reliability calibration, exact
McNemar vs the always-affirm baseline). Ingestion gained two rules:
**R1b** (panel completion — a Phase 2 gap was discovered: the 1st/4th
Dept formats omitted the presiding judge from the panel list; 494 seats
healed from the official evidence lines) and **R7** (per-opinion author
attribution: explicit signatures cross-validated against panel
membership, presumed-presiding memoranda surfaced as such — 87 %
coverage). First measured result (n=20 seed=42, 16 scored after an
honestly-archived rate-limit episode + replay): **13/16 = 81.2 % blind
agreement vs 68.8 % for the always-affirm baseline** — the engine beats
the naive predictor by 12.4 points and never falsely affirmed; Brier
0.150 vs 0.215 (exact McNemar p = 0.73, n too small for significance).

Phase 6 gave the project its public face: **INFINITUM Mail — « La Boîte
de la Cour »** (the jmail system applied to the judicial record). The
visitor reads the 1,387 real decisions as an email inbox: panels are
senders, verdicts are labels, judges are contacts, and the measured
findings arrive as system reports. The interface is a finished project
on display — read-only, no button re-runs any analysis. The single
interactive surface is « Composer », the public sandbox: it runs the
same real three-agent deliberation on a user-supplied sample,
ephemerally (zero DB writes, corpus untouched), and reports failures
verbatim.

Phase 7 hardened the whole: the public sandbox is rate-limited per
visitor (sliding window, explicit 429 with the exact wait time — nothing
queued or simulated), every dossier is shareable by public deep link
(`?dossier=nyappdiv-…` opens the real case in the reading pane), and the
scientific record itself is now versioned in git — `data/archive/science/`
carries every multi-agent session verbatim (the 429 failures included),
with sha256 manifest, because the live SQLite index is gitignored.

## Roadmap

- [x] Phase 0 — precedents, protocol, power analysis, feasibility
- [x] Phase 1 — collector, 5-case sample, structured extraction, CI gate
- [x] Phase 2 — corpus at scale: 1,387 cases, base rate measured,
      validation instrument ready (human review: pending, honestly)
- [ ] Phase 2b — full-corpus LLM label verification + human review of
      the 30-case sample
- [x] Phase 3 (console) — Behavioral Matrix: real-data
      telemetry over the corpus (see `matrix/`)
- [x] Phase 3/4 (experiment) — zero-shot protocol engine shipped as
      module 10: seeded stratified sampling, blind multi-agent
      adjudication, Wilson/Brier/calibration/McNemar scoring, R1b panel
      healing + R7 author attribution; first runs archived (n=5: 5/5
      agreement; n=20: engine rate-limit honestly archived, replayable)
- [x] Phase 5 (delivery) — institutional light theme (« Codex »): ivory
      paper, ink navy, verdict semantics reserved for data
- [x] Phase 6 (delivery) — INFINITUM Mail, the public interface (jmail
      system): read-only mailbox over the 1,387 real decisions, judges as
      contacts, findings as system reports; ephemeral public sandbox as
      the only interactive surface
- [x] Phase 7 (delivery) — hardening: science archive versioned in-repo
      (`data/archive/science/`), public sandbox rate-limited per visitor,
      shareable dossier deep links
- [ ] Phase 3 (experiment, ext) — prompt calibration + full-n replay
      once the engine quota allows
- [ ] Phase 4 — Experiment B (QLoRA fine-tuning on a free Colab T4)
- [ ] Phase 5 — judge profiles, cross-judge counterfactual, bias analysis
- [ ] Phase 6 — reproducible notebook, preprint (the public-site half of
      this line shipped early as the Phase 6 delivery above)
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
première mesure concrète de la « loterie des juges ». Le pipeline est
devenu un jeu de construction (noyau + briques auto-découvertes,
`docs/vision.md`) conçu pour ne jamais être fini. La Phase 4 a livré le
laboratoire complet et le premier résultat à l'aveugle : **13/16 = 81,2 %
d'accord** (contre 68,8 % pour la baseline « toujours confirmer »),
sans aucune fausse confirmation. Depuis la Phase 6, le projet a un visage
public — **INFINITUM Mail, « La Boîte de la Cour »** : les 1 387 décisions
se lisent comme une messagerie, en lecture seule, seul « Composer »
lançant une vraie délibération éphémère. La Phase 7 a sécurisé le registre
scientifique (sessions verbatim versionnées dans `data/archive/science/`)
et durci l'accès public (limite de débit explicite, liens de partage).
La revue humaine de 30 cas reste en attente — aucun chiffre ne prétend
décrire le comportement des juges avant elle. Protocole complet, calculs
de puissance et faisabilité du fine-tuning (Colab gratuit) : `docs/`.
Manifeste qualité : `docs/MANIFEST.md`. Rapports : `docs/phase1_report.md`,
`docs/phase2_report.md`, `matrix/README.md`.

*Avertissement : simulation par IA à but de recherche — ni conseil juridique,
ni outil de prédiction pour de vraies affaires.*
