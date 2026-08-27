#!/usr/bin/env python3
"""Block: validate:select-human-sample — the R10 instrument.

Draws a stratified sample of cases for human review (the project
constitution's rule R10: every dataset is hand-verified on a sample
before conclusions scale). Stratification is by (year × binary
disposition) so the review covers the modeling population, not just
the majority class.

Outputs:
    data/validation/<mode>_validation_sample.jsonl   machine-readable
    data/validation/<mode>_worksheet.md              human-fillable

The worksheet is the review instrument: each row shows the extracted
disposition and its evidence sentence; the reviewer writes
agree / disagree + a note. `validate:human-agreement` (planned) will
score completed worksheets.

Params:
    mode  "corpus" (default) or "sample"
    n     sample size (default from config "validation")
    seed  reproducible draw (default from config)
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from typing import Any

from lib.kernel import Block, Context


def _run(ctx: Context, params: dict[str, Any]) -> dict[str, Any]:
    mode = params.get("mode", "corpus")
    vcfg = ctx.config.get("validation", {})
    n = int(params.get("n", vcfg.get("n", 30)))
    seed = int(params.get("seed", vcfg.get("seed", 20260826)))

    pre = (ctx.config["preprocess"] if mode == "sample"
           else ctx.config["preprocess_corpus"])
    structured_path = ctx.path(pre["structured_jsonl"])
    records = [json.loads(l) for l in structured_path.open(encoding="utf-8")]

    # stratify the modeling population: binary-eligible records only
    pool = [r for r in records if r["disposition"].get("binary_eligible")]
    strata: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in pool:
        strata[(r.get("window") or "?",
                r["disposition"]["binary"])].append(r)

    rng = random.Random(seed)
    picked: list[dict[str, Any]] = []
    # round 1: proportional allocation by largest remainder
    quotas = {}
    total = len(pool)
    if total:
        raw = {k: len(v) / total * n for k, v in strata.items()}
        quotas = {k: int(q) for k, q in raw.items()}
        remaining = n - sum(quotas.values())
        for k in sorted(raw, key=lambda k: raw[k] % 1, reverse=True):
            if remaining <= 0:
                break
            if quotas[k] < len(strata[k]):
                quotas[k] += 1
                remaining -= 1
    for key in sorted(quotas):
        rows = sorted(strata[key],
                      key=lambda r: r["case_id"])
        picked.extend(rng.sample(rows, min(quotas[key], len(rows))))
    picked.sort(key=lambda r: (r.get("window") or "", r["case_id"]))

    out_dir = ctx.path(vcfg.get("output_dir", "data/validation"))
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_path = out_dir / f"{mode}_validation_sample.jsonl"
    with sample_path.open("w", encoding="utf-8") as fh:
        for r in picked:
            row = {
                "case_id": r["case_id"],
                "case_name": r["case_name"],
                "date_filed": r["date_filed"],
                "window": r.get("window"),
                "courtlistener_url": r["provenance"]["courtlistener_url"],
                "extracted_disposition": r["disposition"]["primary"],
                "disposition_evidence":
                    r["disposition"]["primary_evidence"],
                "panel": [j["name"] for j in r["panel"]["judges"]],
                "human_verdict": "",
                "human_note": "",
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    worksheet_path = out_dir / f"{mode}_worksheet.md"
    lines = [
        f"# Human validation worksheet — {mode} dataset",
        "",
        f"Stratified draw: n={len(picked)}, seed={seed}, stratified by "
        "(year × binary disposition).",
        "For each row: open the source (link), read the decretal "
        "paragraph, and write",
        "`agree` or `disagree` (+ note) in the verdict column. A "
        "disagreement is a finding,",
        "not a nuisance — it feeds the adjudication queue "
        "(docs/MANIFEST.md R10).",
        "",
        "| # | case | date | extracted | verdict | note |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(picked, 1):
        lines.append(
            f"| {i} | [{r['case_name']}]({r['provenance']['courtlistener_url']}) "  # noqa: E501
            f"| {r['date_filed']} | {r['disposition']['primary']} | ☐ | |")
    lines += [
        "",
        "---",
        "",
        "Evidence sentences (quote-verified, one per case):",
        "",
    ]
    for i, r in enumerate(picked, 1):
        ev = (r["disposition"]["primary_evidence"] or "").replace("|", "\\|")
        lines.append(f"{i}. **{r['case_name']}** — «{ev}»")
    worksheet_path.write_text("\n".join(lines), encoding="utf-8")

    n_strata = len(strata)
    return {
        "status": "ok",
        "summary": (f"{len(picked)} cases drawn from {n_strata} strata "
                    f"(seed {seed}) → human review pending"),
        "counts": {"sampled": len(picked), "strata": n_strata,
                   "pool": len(pool)},
        "artifacts": [sample_path, worksheet_path],
    }


BLOCK = Block(
    name="validate:select-human-sample",
    stage="validate",
    version="0.1.0",
    description="stratified human-review sample + fillable worksheet "
                "(constitution rule R10)",
    run=_run,
)
