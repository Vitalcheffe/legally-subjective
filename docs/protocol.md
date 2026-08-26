# Experimental Protocol — Legally Subjective

Status: pre-registered design (Phase 0). The statistical sizing below was
computed *before* any model run, with
`scripts/planning/power_analysis.py` (McNemar power, 20,000 simulations,
seed 20260826). Any deviation from this protocol after seeing results will
be documented explicitly.

## 1. Research questions

- **RQ1 (prediction):** can an LLM predict the outcome of a US criminal
  appeal (affirmed / reversed) from the opinion's facts and arguments?
- **RQ2 (learning):** does fine-tuning on past appeals from the same court
  improve over the zero-shot baseline?
- **RQ3 (counterfactual):** does the predicted outcome change when the
  model is conditioned on the profile of a different judge?
- **RQ4 (bias transmission):** does the virgin model already show
  judge-like leniency patterns by crime type, and does fine-tuning amplify
  or correct them?

## 2. Data

### 2.1 Source and scope

- **Court:** New York Supreme Court, Appellate Division (criminal appeals).
  Chosen because (a) volume — thousands of published criminal appeals per
  decade, (b) official slip opinions with full text are public web
  documents, (c) each opinion names its judging panel, which RQ3 requires,
  (d) a single jurisdiction keeps procedure comparable.
- **Discovery:** CourtListener v4 search API, query `"judgment of
  conviction"`, court `nyappdiv`, filed 2010-01-01 → 2020-12-31. A live
  probe (Aug 2026) returned 2,363 published opinions for the sub-window
  2012–2018 alone, so the full decade comfortably exceeds the target.
- **Primary text:** official slip opinions of the NY State Law Reporting
  Bureau (public documents), reached via the `download_url` recorded by
  CourtListener.
- **Unit:** one case = one appellate decision (cluster). Duplicates
  removed by cluster id.

### 2.2 Label

The predicted variable is the **appellate disposition** extracted from the
official text, normalized to:

- binary: `affirmed` vs `reversed-or-vacated` (primary),
- multiclass (secondary): affirmed / reversed / vacated / modified /
  remanded-only / mixed.

A disposition is extracted by rule (last disposition formula in the
opinion) AND verified by the LLM extractor; disagreements are flagged for
human adjudication (R10). Every label stores its evidence sentence (R8).
An important honesty note: this label measures the *appeal's outcome*, not
first-degree guilt — an appellate reversal does not mean innocence, and the
public framing must never conflate the two.

### 2.3 Splits

Original draft (from the project brief): 800 train / 200 test. The power
analysis below says 200 test cases only detects large effects. **Revised:**

| Design | train | test | power for +10 pp | power for +5 pp |
|---|---|---|---|---|
| draft | 800 | 200 | 0.87 | 0.37 |
| **primary** | **600** | **400** | **0.99** | **0.70** |
| extended (if collectable) | 800 | 600 | 1.00 | 0.87 |

Decision: collect **≥1,000** cases; assign 600/400 by default, 800/600 if
≥1,400 usable cases are collected. A single accuracy on 400 test cases
carries a ±4.5–4.8 pp CI (see table 2 of the script output); every
reported number will carry its interval.

Stratification: split blocked by (year, department, disposition class) so
both splits track the joint distribution. Judge overlap between splits is
allowed (RQ3 needs judges with many cases), and panel composition is
recorded so judge-level leakage can be measured later.

## 3. Experiment A — zero-shot baseline ("the virgin judge")

- Model: an open-weights instruction-tuned LLM (Mistral-7B-Instruct or
  Llama-3-8B-Instruct), greedy decoding (temperature 0), identical prompt
  across cases, no memory between cases.
- Input: case facts and procedural history (structured extraction), masked
  of the outcome; the model never sees disposition text.
- Output (JSON): predicted disposition + confidence + one-paragraph
  rationale.
- **Prompt calibration is itself measured:** 5 candidate prompts on 50
  calibration cases (held out from both splits), pick by macro-F1; the
  winning prompt is frozen before the test evaluation. No prompt tuning on
  test data.

## 4. Experiment B — fine-tuned ("the judge with experience")

- Same base model as A. Method: QLoRA (4-bit NFQ base, LoRA r=16 on all
  attention + MLP projections), 3 epochs, lr 1e-4 cosine, batch 8 by
  gradient accumulation, seq len 2048, seed fixed.
- Training pairs: (masked facts + charge + procedural history) →
  (disposition + concise rationale), drawn from the train split only.
- Class balance: weighted loss by disposition frequency (affirmed cases
  dominate NY App. Div. criminal appeals; the exact base rate is measured
  in Phase 2 and reported).
- Feasibility on a free Colab T4: see `docs/feasibility.md` (computed
  memory budget ≈ 7 GB / 16 GB; ≈ 1–2 h wall-clock including model
  download).

## 5. Experiments C (RQ3) and D (RQ4)

- **C — cross-judge counterfactual:** for each judge with ≥ 20 authored or
  joined opinions in the dataset, build a profile (affirmance rate by
  crime type, sentence-modification rate, reversal-vacatur rate, with
  CIs). Then re-run A/B on test cases with the prompt conditioned on a
  *different* judge's profile ("you are Justice X, whose past decisions
  show …"). Measure the **judge-swap sensitivity**: share of cases whose
  predicted disposition flips under a different simulated judge. This is
  the number behind the public hook, reported with its CI and sliced by
  crime type.
- **D — bias transmission:** compare leniency patterns (predicted
  affirmance rate by crime type / victim gender when explicitly stated in
  the facts) between A and B. If B's gaps exceed A's, fine-tuning imported
  human priors — the strongest possible result. All demographic slicing is
  restricted to attributes *explicitly stated in the opinion text*;
  inferring race or gender from names is methodologically forbidden (see
  Limitations).

## 6. Statistical procedure (fixed in advance)

1. Primary comparison A vs B: McNemar test on paired predictions
   (sizing above). Report b (B fixes) and c (B breaks) separately.
2. Every headline number: point estimate + 95% CI (bootstrap 10k for
   sliced metrics).
3. Multiple comparisons across crime types: Holm correction.
4. Judge-swap sensitivity: permutation test (labels of judge profiles
   permuted) to show the effect is not prompt noise.
5. No other tests will be claimed as confirmatory; anything exploratory is
   labeled as such.

## 7. Ethics and safety

- Permanent disclaimer on every artifact: *simulation by AI, not legal
  advice; exploratory, not prescriptive.*
- Public court records only; no attempt to de-anonymize any individual.
- Demographics only when stated in the source text (R8 evidence
  attached); no inference from names.
- The dataset and code are released for research reproducibility; the
  models carry a research-only notice.
- The partenaire-droit reviews all legal interpretation before publication
  (MANIFEST R10).
