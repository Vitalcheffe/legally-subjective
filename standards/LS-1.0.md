# The Subjectivity Fingerprint — Standard LS-1.0

**Legally Subjective** · Version 1.0 (Draft for ratification)
Status: DRAFT · Frozen upon first FILED docket

> *The law claims objectivity. Judges are humans. This standard makes the human readable — with its uncertainty in full view.*

---

## 1. Purpose and scope

LS-1.0 defines a compact, verifiable, machine-readable representation of the publicly measurable behavioral tendencies of a legal actor (judge, justice, advocate): the **Subjectivity Fingerprint**.

Design constraints, in order of precedence:

1. **Zero fabrication.** Every value must be traceable to a public source URI. Missing data is rendered as missing — never estimated, imputed, or averaged over.
2. **Uncertainty is a first-class citizen.** Every axis carries its N and a confidence interval. A fingerprint with thin data must LOOK thin.
3. **Determinism.** Same inputs → bit-identical output. Randomness is banned from the pipeline (fixed seeds only, disclosed).
4. **Comparability.** All values are percentiles against a declared reference bench — never absolute scores.

## 2. The six axes

All axes are expressed as an integer percentile 0–99 against the reference bench, with N and a 95% bootstrap confidence interval. An axis with insufficient data is reported as `null` with status `"insufficient-data"`.

| # | Axis | What it measures | Primary signal | Source basis |
|---|------|------------------|----------------|--------------|
| 1 | **Disposition** | Where the actor lands on outcome orientation | Distribution of directional dispositions (affirm / reverse / vacate / remand) in authored opinions | Opinion clusters + docket entries |
| 2 | **Temperament** | Collegial conduct on the bench (proxy) | Separate-opinion behavior: rate of solo dissents vs. joined opinions; seriatim tendency | Opinion relationships (dissent/concurrence joins) |
| 3 | **Precedent** | Relationship to precedent | Median age of authorities cited; citation density per 1,000 words of opinion text | Citations extracted from opinion text |
| 4 | **Reversal** | Durability of the actor's jurisprudence | Treatment of the actor's opinions by reviewing courts (affirmed / reversed / distinguished / criticized) | Citation treatment analysis |
| 5 | **Orality** | Behavior in oral proceedings | Questions per sitting; words per intervention; interruption ratio | Oral argument transcripts |
| 6 | **Exposure** | Public footprint volume | Authored opinions per year; separate writings; public sitting count | Aggregated publication records |

**Declared proxies.** Temperament is a behavioral proxy inferred from public writings — not a psychological assessment. Every docket MUST state this in its `limits` field. Overclaiming is a spec violation.

**Reference bench.** Each docket declares its bench: the population of actors used for percentile normalization (e.g., "US Courts of Appeals, active judges, 2010–2026"). Percentiles without a declared bench are invalid.

**Declared v1 proxies (ratified at first filing).** The reference implementation ships four computed axes and two nulls. Each docket carries the full proxy statement in `axes.<axis>.metric_def`:

| Axis | v1 proxy | Null axes |
|------|----------|-----------|
| Disposition | Petitioner-alignment rate — share of voted merits cases where the actor's side favored the party seeking relief (petitioner/appellant), resolved from the winning-party record | — |
| Temperament | Dissent rate — share of merits votes cast with the minority | — |
| Precedent | Citation density — mean authorities cited per authored lead opinion | — |
| Reversal | — | Not computable: no reviewing court sits above the declared bench; treatment analysis pending citation-depth ingestion |
| Orality | — | Oral-argument transcripts not yet ingested |
| Exposure | Publication rate — authored lead opinions per calendar year of service inside the window | — |

## 3. Computation rules

1. **Ingestion.** Raw records are cached with URI + retrieval timestamp. No live lookups at compute time.
2. **Metric extraction.** Per-axis raw metrics are computed as pure functions of cached records.
3. **Normalization.** Percentile = empirical CDF rank within the reference bench: `pct = 100 · (rank − 0.5) / bench_size` (median-rank convention, ties averaged).
4. **Rank band.** Bootstrap over the actor's decision set: 10,000 resamples, percentile method, seed = `sha256(docket_id + axis_name + standard_version)` truncated to 32 bits. The seed is disclosed in the docket. **What this interval covers is the percentile RANK on the bench, not the measured value** — the field is named `rank_band`, never `ci95`. (Renamed at rev. 1, 2026-08-27 — LS-AUDIT-001 inj. 3: the former label invited readers to believe the measurement was ~10× more precise than it is.)
4bis. **Value interval.** Where the metric is a binomial share (Disposition, Temperament), the docket additionally carries `value_ci95`: the Wilson score interval at 95% of the measured value itself. Means and rates (Precedent, Exposure) carry `null` — no interval without a model of their sampling process, and the docket says so rather than pretending.
5. **Insufficient data.** If N < 30 for an axis (or the bench has < 30 members), the axis is `null`, status `insufficient-data`, and the glyph renders that spoke dashed.
5bis. **Small-bench rule.** A reference bench of ≥ 5 but < 30 members is admissible when: `bench_n` and `small_bench: true` are declared in the docket; the docket's `limits` state the coarse percentile granularity; and the rank band is computed against the fixed bench as described in rule 4. (Adopted before the first FILED docket.)
6. **Rounding.** Percentiles integer; rank band bounds integer; raw metrics kept at full precision internally; Wilson bounds rounded to 4 decimals.

## 4. The Docket JSON (canonical artifact)

One file per subject: `data/dockets/<docket_id>.json`. Immutable once FILED.

```json
{
  "standard": "LS-1.0",
  "docket": "LS-J-004",
  "revision": 0,
  "subject": {
    "name": "Neil M. Gorsuch",
    "role": "associate-justice",
    "court": "supreme-court-of-the-united-states",
    "bench": "scotus-2010-2026"
  },
  "status": "FILED",
  "filed_at": "2026-09-15T00:00:00Z",
  "revision": 1,
  "supersedes": {
    "docket": "LS-J-004",
    "revision": 0,
    "reason": "LS-AUDIT-001 inj.3: 'ci95' (bootstrap band of the percentile rank) renamed 'rank_band'; 'value_ci95' (Wilson 95%) added for binomial-share metrics."
  },
  "axes": {
    "disposition":  { "percentile": 74, "rank_band": [66, 81], "value_ci95": [0.712, 0.768], "n": 1247, "status": "ok",
                      "sources": ["courtlistener://opinion-cluster/..."] },
    "temperament":  { "percentile": 61, "rank_band": [52, 70], "value_ci95": [0.184, 0.241], "n": 412, "status": "ok",
                      "sources": ["courtlistener://opinion-relationship/..."] },
    "precedent":    { "percentile": 88, "rank_band": [80, 93], "value_ci95": null, "n": 1247, "status": "ok",
                      "sources": ["courtlistener://citations/..."] },
    "reversal":     { "percentile": 38, "rank_band": [29, 48], "value_ci95": null, "n": 233, "status": "ok",
                      "sources": ["courtlistener://treatment/..."] },
    "orality":      { "percentile": 79, "rank_band": [70, 86], "value_ci95": null, "n": 96, "status": "ok",
                      "sources": ["oyez://transcript/..."] },
    "exposure":     { "percentile": 22, "rank_band": [15, 31], "value_ci95": null, "n": 15, "status": "ok",
                      "sources": ["courtlistener://docket/..."] }
  },
  "projections": {
    "iterations": 10000,
    "seed": 88421,
    "quantiles": { "p10": null, "p50": null, "p90": null }
  },
  "limits": [
    "Temperament is a collegiality proxy from public writings, not a psychological assessment.",
    "Percentiles are relative to the declared bench, not absolute qualities."
  ],
  "chain": {
    "computed_at": "2026-09-15T00:00:00Z",
    "pipeline": "legally-subjective/1.0.0",
    "sha256": "<hash of the canonical JSON serialization, computed last>"
  }
}
```

**Canonicalization.** Keys sorted lexicographically, UTF-8, no trailing whitespace, `sha256` computed over the serialization excluding the `chain.sha256` field itself.

**Immutability.** A FILED docket never changes. Corrections or recomputations produce `revision + 1` with a `supersedes` field pointing to the prior revision. *(First use: rev. 1, 2026-08-27 — the `ci95` → `rank_band` renaming ordered by the internal audit LS-AUDIT-001; values unchanged to the bit, only the lying label died.)*

## 5. The Glyph (visual identity)

A deterministic radial signature, pure function of `(axes, n, docket_id)`:

1. Six spokes at 60° intervals, length = `percentile/100 · R` (dashed if `insufficient-data`).
2. Spoke endpoints joined by a closed Catmull-Rom spline → the ink contour.
3. Inner ring radius = `log10(n) / log10(max_n) · R/3` — the weight of evidence, visible.
4. Rotation offset = `(int(sha256(docket_id), 16) mod 360)` degrees — the subject's unique tilt. (Draft note: originally mod 60; widened to mod 360 before first filing — 60 discrete values collide on a 9-member bench, 360 does not.)
5. Center: the seal dot (rendered `--seal`) for FILED dockets only.
6. Specimen state (no data yet): the Disposition axis carries an orientation tick — the compass North, marking where reading begins. It is not data; it breaks the hexagon's six-fold symmetry so every subject's tilt is visibly distinct even before their record exists.

No randomness. Two identical axis profiles with different docket IDs yield different tilts. The glyph is SVG, print-safe, and monochrome-compatible.

## 6. Comparison (`v.`)

A `v.` artifact superimposes two dockets: per-axis deltas (signed percentile differences), overlap area of both glyphs, and the union of both chains. Deltas of axes with `insufficient-data` status are `null`. The `v.` inherits the OLDER standard version of the pair and flags any version mismatch.

## 7. Citation format

Bluebook-style:

> *Legally Subjective*, In re Neil M. Gorsuch, Docket LS-J-004 (LS-1.0, filed Sept. 15, 2026).

BibTeX emitted alongside every docket.

## 8. Compliance clause (the zero-fabrication law)

An implementation is LS-1.0-compliant if and only if:

- every non-null value traces to ≥ 1 public source URI, retrievable at audit time;
- the full pipeline is deterministic: re-running the build on identical cached sources reproduces bit-identical dockets;
- missing data is surfaced, never imputed;
- N, CI, seed, and computation date are disclosed on every axis;
- `limits` is non-empty.

Non-compliant implementations MUST NOT use the standard identifier.

## 9. Versioning

LS-1.0 freezes when the first docket is FILED. Any change to formulas, normalization, or schema bumps to LS-1.1+. Filed dockets keep their original standard version forever.

**Freeze record.** Before the first filing, two pre-ratification amendments were adopted: (a) §5.4 rotation widened from mod 60 to mod 360; (b) §2 declared v1 proxies and §3.5bis small-bench rule. The first FILED dockets — the sitting Nine of the Supreme Court of the United States, window OT2020–2026, sources CourtListener and Oyez — carry this version.

---

*Subjectivity, measured. We fabricate nothing.*
