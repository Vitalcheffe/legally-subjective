#!/usr/bin/env python3
"""Block: validate:data — the integrity gate (R3/R9).

Structural integrity failures (missing document, sha mismatch, secrets)
raise and stop the pipeline. Extraction-quality gaps (no disposition,
thin panel) are errors on the hand-verified sample, warnings on the
corpus — see scripts/verify_data.py for the reasoning.

Params:
    mode  "sample" (default) or "corpus"
"""

from __future__ import annotations

from typing import Any

from lib.kernel import Block, BlockError, Context


def _run(ctx: Context, params: dict[str, Any]) -> dict[str, Any]:
    import verify_data

    mode = params.get("mode", "sample")
    report = verify_data.run_checks(ctx.config, mode)
    verify_data.print_report(report)

    if report["errors"]:
        raise BlockError(
            f"{len(report['errors'])} validation error(s) — "
            f"first: {report['errors'][0]}")

    return {
        "status": "ok",
        "summary": (f"{report['structured']} records valid, "
                    f"{report['no_disposition']} flagged for "
                    f"adjudication, {len(report['warnings'])} warnings"),
        "counts": {"raw_cases": report["raw_cases"],
                   "structured": report["structured"],
                   "no_disposition": report["no_disposition"],
                   "no_panel": report["no_panel"],
                   "warnings": len(report["warnings"])},
        "artifacts": [],
    }


BLOCK = Block(
    name="validate:data",
    stage="validate",
    version="0.2.0",
    description=("integrity gate: documents, sha256, provenance, schema, "
                 "secrets — extraction gaps routed to adjudication"),
    run=_run,
)
