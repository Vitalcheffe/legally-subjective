#!/usr/bin/env python3
"""Block: source:courtlistener — the collector.

Collects real criminal-appeal cases from the CourtListener v4 search
API plus official/courtlistener documents. All behavior (windows,
gates, channel preference, targets) comes from config.json; this block
only selects the dataset mode.

Params:
    mode  "sample" (default) or "corpus"
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from lib.kernel import Block, Context


def _run(ctx: Context, params: dict[str, Any]) -> dict[str, Any]:
    import fetch_courtlistener as collector

    mode = params.get("mode", "sample")
    args = argparse.Namespace(dry_run=False, reset=False,
                              max_runtime_minutes=None)
    collector.run(mode, ctx.config, args)

    paths = (ctx.config["paths"] if mode == "sample"
             else ctx.config["paths_corpus"])
    cases_path = ctx.path(paths["cases_jsonl"])
    n = sum(1 for _ in cases_path.open(encoding="utf-8")) \
        if cases_path.exists() else 0
    return {
        "status": "ok",
        "summary": f"{n} cases collected ({mode})",
        "counts": {"cases": n, "mode": mode},
        "artifacts": [cases_path],
    }


BLOCK = Block(
    name="source:courtlistener",
    stage="source",
    version="0.2.0",
    description=("collect real criminal-appeal cases + documents "
                 "(CourtListener search, NY slip opinions / archival "
                 "copies)"),
    run=_run,
)
