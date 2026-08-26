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
from collections import Counter
from typing import Any

from lib.kernel import Block, Context


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def _department(court_id: str) -> str:
    """nyappdiv_1 → 1st Dept, …"""
    mapping = {"nyappdiv_1": "1st", "nyappdiv_2": "2nd",
               "nyappdiv_3": "3rd", "nyappdiv_4": "4th"}
    return mapping.get(court_id or "", "unknown")


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
        "disposition_distribution": {},
        "binary": {},
        "by_year": {},
        "by_department": {},
    }

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
    for key, extract_key in (("by_year", "window"),
                             ("by_department", None)):
        groups: dict[str, list[dict[str, Any]]] = {}
        for r in binary:
            g = r[extract_key] if extract_key else \
                _department(r["court"]["id"])
            groups.setdefault(g, []).append(r)
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
