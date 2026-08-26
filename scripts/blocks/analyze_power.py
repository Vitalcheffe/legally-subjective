#!/usr/bin/env python3
"""Block: analyze:power — the pre-registered statistical sizing.

Re-runs the McNemar power analysis that sized the train/test splits
(protocol §2.3). Seeded and reproducible; see
scripts/planning/power_analysis.py for the authoritative implementation.

Params: none (the pre-registered scenarios are the point).
"""

from __future__ import annotations

from typing import Any

from lib.kernel import Block, Context


def _run(ctx: Context, params: dict[str, Any]) -> dict[str, Any]:
    import importlib.util
    import sys
    from pathlib import Path

    # import the planning module by path (it lives outside the scripts/
    # package root, under scripts/planning/)
    mod_path = Path(__file__).resolve().parent.parent / \
        "planning" / "power_analysis.py"
    spec = importlib.util.spec_from_file_location("power_analysis",
                                                  mod_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["power_analysis"] = module
    spec.loader.exec_module(module)
    module.main()

    return {
        "status": "ok",
        "summary": "pre-registered power analysis re-run (McNemar, "
                   "20k simulations, seed 20260826)",
        "counts": {},
        "artifacts": [],
    }


BLOCK = Block(
    name="analyze:power",
    stage="analyze",
    version="0.1.0",
    description="McNemar power analysis for A vs B experiment sizing "
                "(seeded, pre-registered)",
    run=_run,
)
