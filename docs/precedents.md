# Phase 0 — Precedents, Related Work, and Positioning

Status: complete. Every fact below was re-verified against public sources in
August 2026. Links are the primary sources.

## 1. The three projects that changed the conversation

### 1.1 ProPublica — *Machine Bias* / COMPAS (2016)

ProPublica analyzed COMPAS, a recidivism-risk algorithm used in US courts
and sentencing decisions. Using ~7,000 defendants from Broward County, FL,
they showed the tool flagged Black defendants as future criminals at almost
**twice the false-positive rate of white defendants** (44.9% vs 23.5%),
while white defendants were misclassified as low-risk more often.

- Why it landed: one simple question ("is the algorithm racist?"), real
  data obtained by FOIA, a single quantified finding that could not be
  un-seen, and a newsroom with reach behind it.
- Lesson for us: **a killer stat beats a thousand words — and it must be
  extracted from real data, not asserted.**

Sources: propublica.org/article/machine-bias-risk-assessments-in-criminal-sentencing

### 1.2 Gender Shades — Buolamwini & Gebru (2018)

A controlled benchmark of commercial facial-analysis systems (IBM, Microsoft,
Face++) showed error rates of **up to 34.7% for darker-skinned women versus
below 1% for lighter-skinned men**. Published at FAT* (now FAccT); it led
IBM and Microsoft to publish error-rate breakdowns and improve their
systems, and it seeded the Algorithmic Justice League.

- Why it landed: a benchmark anyone could understand, a stark visual gap,
  and a researcher who owned the question.
- Lesson for us: **stratified error reporting (by group) is the finding.**
  Report every metric sliced, not just the aggregate.

Sources: Buolamwini & Gebru, *Gender Shades*, PMLR 81:77-91, 2018.

### 1.3 The Moral Machine — MIT (2018)

An interactive site collected ~**40 million decisions in 233 countries and
regions** on autonomous-vehicle moral dilemmas. Published in *Nature*
(Awad et al., 2018), it remains the reference for "ask the public, at
scale, about a moral question."

- Why it landed: the experiment *was* the demo. Participation was the
  virality.
- Lesson for us: **the interactive artifact (site) is not marketing — it is
  part of the scientific instrument.**

## 2. The academic line we stand on: verdict prediction

| Work | Court / data | Task | Reported result |
|---|---|---|---|
| Katz, Bommarito & Blackman (2017), *PLOS ONE* | US Supreme Court (SCDB) | predict case outcome | ~70% accuracy at the case level |
| Chalkidis et al. (2019), *Artif. Intell. Law* | European Court of Human Rights (11k cases) | predict violated articles | F1 ≈ 0.70–0.85 depending on article |
| CAIL2018 (Xiao et al., 2018) | Chinese criminal cases (2.6M+) | legal judgment prediction | the benchmark that made LJP a field |
| COMPAS analyses (2016–) | US sentencing data | recidivism risk | bias findings above |

Public structured datasets that already exist:

- `AUEB-NLP/ecthr_cases` (Hugging Face) — 11k ECtHR cases, factual text +
  binary violation labels per article.
- CAIL2018 and successors — Chinese, charge + article prediction.
- `coastalcph/fairlex` — fairness benchmarks over several legal datasets.
- US Supreme Court Database (SCDB) — ~250 expert-coded variables per case,
  including individual justices' votes.

What **does not exist** anywhere in this list — verified by search in
August 2026:

1. a **US appellate criminal** dataset pairing full opinion text with
   outcome **and the identity of the judging panel**;
2. the **counterfactual judge-swap experiment** (re-decide case X under
   the profile of judge Y);
3. the **A-vs-B bias transmission test** (does fine-tuning on a judge's
   corpus import the judge's biases into a virgin model?).

That intersection is our contribution.

## 3. The 2024–2026 data landscape (what changed)

- **The Caselaw Access Project API was sunset on September 5, 2024.**
  All use restrictions on CAP data were lifted at the same time, but the
  programmatic API and search tool are gone (case.law confirms this on its
  homepage and /about). Any plan written against `api.case.law` (including
  our original draft protocol) is obsolete.
- **CourtListener (Free Law Project)** absorbed CAP corpus coverage and is
  now the reference free access point. Its v4 **search** endpoint works
  anonymously; its REST object endpoints require a free API token.
- Official state reporters remain the cleanest primary sources. New York
  publishes official slip opinions (NY State Law Reporting Bureau) as
  public web documents — full text, panel of judges included.

Our pipeline is therefore: **CourtListener search (metadata) → official
slip opinions (full text) → structured extraction with evidence.** Verified
live in Phase 1; see `docs/phase1_report.md`.

## 4. Positioning — one sentence

> Prior work asks "can a model predict a court outcome?"; we ask
> "**does the outcome depend on which judge you draw — and can a model
> trained on a specific judge import their biases?**", on real US criminal
> appeals, with every extracted field carrying its source evidence.

The public hook: *"Would you have been guilty with a different judge?"*
— always paired with the mandatory disclaimer (simulation by AI, not legal
advice; exploratory, not prescriptive).

## 5. What "as rigorous as the precedents" means concretely

- Real, public, attributable data (R1) — with a provenance log.
- Metrics sliced by subgroup (Gender Shades lesson).
- A pre-registered protocol with a power analysis before running the
  models (`docs/protocol.md`) — not post-hoc.
- An interactive artifact as part of the instrument (Moral Machine lesson).
- Limitations section with real limitations (≥ 5), written before anyone
  asks (MANIFEST R6).
