#!/usr/bin/env python3
"""Golden regression test — the sample is the invariant.

The 5-case sample was hand-verified (R10) and committed. Whatever
refactor the pipeline goes through (blocks, kernel, CLI moves), running
extraction on the sample must reproduce the committed records exactly,
modulo fields that are intrinsically per-run (timestamps) or that come
from LLM enrichment (not re-run here — the deterministic half is what
this test pins).

Run:  python scripts/tests/test_golden_sample.py   (exit 0 = pass)
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS.parent


def strip_volatile(record: dict) -> dict:
    """Remove per-run and LLM-dependent fields; keep everything else."""
    rec = copy.deepcopy(record)
    rec["extraction"].pop("extracted_at", None)
    rec["extraction"].pop("llm_backend", None)
    d = rec["disposition"]
    d.pop("llm_check", None)
    d.pop("agreement", None)
    rec["facts"]["summary"] = None
    rec["crime_type"] = {"value": None, "method": "not_extracted"}
    rec["defendant_gender"] = {"value": None, "method": "not_extracted"}
    return rec


def main() -> int:
    committed_path = REPO_ROOT / "data/structured/sample_structured.jsonl"
    committed = [json.loads(l) for l in
                 committed_path.open(encoding="utf-8")]

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "golden_structured.jsonl"
        cfg = json.loads((REPO_ROOT / "config.json").read_text(
            encoding="utf-8"))
        cfg["preprocess"]["structured_jsonl"] = str(out)
        cfg_path = Path(tmp) / "cfg.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

        # run extraction through the BLOCK path (not the CLI) so this
        # test exercises the block system itself
        code = subprocess.run(
            [sys.executable, "-c",
             "import sys, json; sys.path.insert(0, "
             f"{json.dumps(str(SCRIPTS))});\n"
             "from lib.kernel import Context, run_block\n"
             "import blocks.extract_structured as b\n"
             "cfg = json.loads(open(sys.argv[1], encoding='utf-8').read())\n"
             "run_block(b.BLOCK, Context(cfg), {'mode': 'sample'})",
             str(cfg_path)],
            capture_output=True, text=True, cwd=str(REPO_ROOT))
        if code.returncode != 0:
            print("FAIL: block execution errored\n" + code.stderr[-2000:])
            return 1
        if not out.exists():
            print("FAIL: no output written")
            return 1
        fresh = [json.loads(l) for l in out.open(encoding="utf-8")]

    if len(fresh) != len(committed):
        print(f"FAIL: {len(fresh)} records vs {len(committed)} committed")
        return 1

    mismatches = 0
    for a, b in zip(committed, fresh):
        sa, sb = strip_volatile(a), strip_volatile(b)
        if sa != sb:
            mismatches += 1
            print(f"MISMATCH: {a.get('case_name')}")
            for key in sa:
                if sa.get(key) != sb.get(key):
                    print(f"  field {key}: committed={sa.get(key)!r} "
                          f"fresh={sb.get(key)!r}")
    if mismatches:
        print(f"\nGOLDEN TEST FAILED ({mismatches}/{len(committed)} "
              f"records differ)")
        return 1

    print(f"GOLDEN TEST PASSED — block extraction reproduces the "
          f"committed sample ({len(committed)} records, deterministic "
          f"fields identical)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
