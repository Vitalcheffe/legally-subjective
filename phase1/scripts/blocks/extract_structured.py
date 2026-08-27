#!/usr/bin/env python3
"""Block: extract:structured — evidence-based field extraction.

Deterministic rules (panel, disposition, charge, trial judges, facts
recital) plus optional LLM enrichment, exactly as the standalone
`preprocess.py` CLI — same code path, same frozen prompt, same schema.

Params:
    mode            "sample" (default) or "corpus"
    llm_fields_file optional path to offline LLM fields JSON
    use_llm         bool — call an OpenAI-compatible endpoint directly
"""

from __future__ import annotations

import json
from typing import Any

from lib.kernel import Block, Context


def _run(ctx: Context, params: dict[str, Any]) -> dict[str, Any]:
    import preprocess

    mode = params.get("mode", "sample")
    kwargs: dict[str, Any] = {}
    if params.get("llm_fields_file"):
        kwargs["llm_fields_file"] = params["llm_fields_file"]
    if params.get("use_llm"):
        kwargs["use_llm"] = True
    preprocess.run(ctx.config, mode, **kwargs)

    pre = (ctx.config["preprocess"] if mode == "sample"
           else ctx.config["preprocess_corpus"])
    out_path = ctx.path(pre["structured_jsonl"])
    records = [json.loads(l) for l in out_path.open(encoding="utf-8")] \
        if out_path.exists() else []
    with_disp = sum(1 for r in records
                    if r["disposition"].get("primary") is not None)
    return {
        "status": "ok",
        "summary": (f"{len(records)} records, {with_disp} with a "
                    f"disposition ({mode})"),
        "counts": {"records": len(records),
                   "with_disposition": with_disp},
        "artifacts": [out_path],
    }


BLOCK = Block(
    name="extract:structured",
    stage="extract",
    version="0.2.0",
    description=("evidence-based structured extraction: panel, "
                 "disposition, charge, trial judges, facts (+ optional "
                 "LLM fields)"),
    run=_run,
)
