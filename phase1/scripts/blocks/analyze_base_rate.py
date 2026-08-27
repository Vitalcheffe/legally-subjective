#!/usr/bin/env python3
"""Block: analyze:base-rate — the disposition base rate (protocol §4).

Measures the class balance of the dataset — the number the experimental
protocol requires Phase 2 to report (weighted loss, headline-context).
Every estimate carries a Wilson 95% interval; nothing is published
without its uncertainty (MANIFEST R7/R8 spirit).

Population definitions, applied in order and each counted:
  collected     every collected case (raw records)
  extracted     structured records with a disposition extracted
  binary        records with a binary-eligible disposition
                (affirmed vs reversed/vacated) — the modeling population

Params:
    mode  "corpus" (default) or "sample"
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from lib.kernel import Block, Context

_DEPT_RX = re.compile(
    r"(?i)appellate division[,\s]+"
    r"(first|second|third|fourth|1st|2d|2nd|3d|3rd|4th) department")
_DEPT_NORM = {"1st": "1st", "first": "1st", "2d": "2nd", "2nd": "2nd",
              "second": "2nd", "3d": "3rd", "3rd": "3rd",
              "third": "3rd", "4th": "4th", "fourth": "4th"}


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def _department(doc_path: Path) -> str:
    """Department from the opinion's own header ('Appellate Division,
    Second Department') — the search metadata only carries the parent
    court id. Reads the source document; unknown when unreadable."""
    try:
        text = doc_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return "unknown"
    m = _DEPT_RX.search(text)
    if not m:
        return "unknown"
    return _DEPT_NORM[m.group(1).lower()]


def _case_class(case_name: str) -> str:
    """Population composition: NY criminal appeals are 'People v. …';
    'Matter of …' rows are Article 78 / parole-adjacent matters that
    matched the query — counted separately, never silently mixed."""
    if (case_name or "").startswith("People v"):
        return "people_v"
    if (case_name or "").startswith("Matter of"):
        return "matter_of"
    return "other"


def _run(ctx: Context, params: dict[str, Any]) -> dict[str, Any]:
    mode = params.get("mode", "corpus")
    pre = (ctx.config["preprocess"] if mode == "sample"
           else ctx.config["preprocess_corpus"])
    structured_path = ctx.path(pre["structured_jsonl"])
    records = [json.loads(l) for l in structured_path.open(encoding="utf-8")]

    analysis: dict[str, Any] = {
        "dataset": mode,
        "records": len(records),
        "populations": {},
        "composition": {},
        "disposition_distribution": {},
        "binary": {},
        "by_year": {},
        "by_department": {},
        "department_method": ("regex 'Appellate Division, N Department' "
                              "over the opinion header (search metadata "
                              "only carries the parent court id)"),
    }

    composition = Counter(_case_class(r.get("case_name", ""))
                          for r in records)
    analysis["composition"] = {k: composition.get(k, 0)
                               for k in ("people_v", "matter_of", "other")}

    # department per record: the raw case records know the document
    # paths (the structured provenance deliberately does not duplicate
    # them — the schema is frozen by the golden test)
    paths = (ctx.config["paths"] if mode == "sample"
             else ctx.config["paths_corpus"])
    raw_cases_path = ctx.path(paths["cases_jsonl"])
    doc_paths: dict[str, Path] = {}
    if raw_cases_path.exists():
        for line in raw_cases_path.open(encoding="utf-8"):
            raw = json.loads(line)
            doc_paths[f"{raw['court_id']}-{raw['cluster_id']}"] = \
                ctx.path(raw["document_path"])
    for r in records:
        r["_dept"] = _department(doc_paths.get(r["case_id"],
                                                 Path("/nonexistent")))

    extracted = [r for r in records
                 if r["disposition"].get("primary") is not None]
    binary = [r for r in records
              if r["disposition"].get("binary_eligible")]
    analysis["populations"] = {
        "collected": len(records),
        "extracted": len(extracted),
        "binary_eligible": len(binary),
    }

    # full multiclass distribution
    dist = Counter(r["disposition"]["primary"] for r in extracted)
    for value, count in sorted(dist.items(), key=lambda kv: -kv[1]):
        lo, hi = wilson_interval(count, len(extracted))
        analysis["disposition_distribution"][value] = {
            "count": count, "share": round(count / len(extracted), 4),
            "wilson95": [round(lo, 4), round(hi, 4)],
        }

    # binary base rate — the modeling number
    n_aff = sum(1 for r in binary
                if r["disposition"]["binary"] == "affirmed")
    n_rev = len(binary) - n_aff
    lo, hi = wilson_interval(n_aff, len(binary))
    analysis["binary"] = {
        "affirmed": n_aff,
        "reversed_vacated": n_rev,
        "n": len(binary),
        "affirmance_rate": round(n_aff / len(binary), 4) if binary else None,
        "affirmance_rate_wilson95": [round(lo, 4), round(hi, 4)]
        if binary else None,
    }

    # by year and by department (binary rates)
    for key, key_fn in (("by_year", lambda r: r.get("window") or "?"),
                        ("by_department", lambda r: r["_dept"])):
        groups: dict[str, list[dict[str, Any]]] = {}
        for r in binary:
            groups.setdefault(key_fn(r), []).append(r)
        target = analysis[key]
        for g in sorted(groups):
            rows = groups[g]
            aff = sum(1 for r in rows
                      if r["disposition"]["binary"] == "affirmed")
            glo, ghi = wilson_interval(aff, len(rows))
            target[g] = {
                "n": len(rows), "affirmed": aff,
                "affirmance_rate": round(aff / len(rows), 4),
                "wilson95": [round(glo, 4), round(ghi, 4)],
            }

    out_dir = ctx.path(ctx.config.get("analysis", {}).get(
        "output_dir", "data/analysis"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"base_rate_{mode}.json"
    out_path.write_text(json.dumps(analysis, indent=1, ensure_ascii=False),
                        encoding="utf-8")

    b = analysis["binary"]
    print(f"  base rate ({mode}): affirmed {b['affirmed']}/"
          f"{b['n']} = {b['affirmance_rate']:.3f} "
          f"(95% CI {b['affirmance_rate_wilson95'][0]:.3f}–"
          f"{b['affirmance_rate_wilson95'][1]:.3f})")

    return {
        "status": "ok",
        "summary": (f"binary base rate {b['affirmance_rate']:.3f} "
                    f"[{b['affirmance_rate_wilson95'][0]:.3f}, "
                    f"{b['affirmance_rate_wilson95'][1]:.3f}] on n="
                    f"{b['n']}"),
        "counts": {"collected": analysis["populations"]["collected"],
                   "binary_eligible": b["n"],
                   "affirmed": b["affirmed"]},
        "artifacts": [out_path],
    }


BLOCK = Block(
    name="analyze:base-rate",
    stage="analyze",
    version="0.1.0",
    description=("disposition base rate with Wilson CIs — overall, by "
                 "year, by department (the protocol's required Phase 2 "
                 "measurement)"),
    run=_run,
)
