#!/usr/bin/env python3
"""Legally Subjective — data validation gate (R3/R9).

Checks that the committed sample is complete, traceable and honest:

  - every raw case has a document, a sha256 and a criminal-gate match;
  - every structured record has: a panel with at least 3 judges, a
    disposition with evidence, a provenance block;
  - rule-vs-LLM disposition agreement is reported (not required —
    disagreements are flags for human review, not errors);
  - no credential strings (ghp_, sk-, api keys) anywhere in the data.

Exits non-zero on any failure: this is the CI gate
(.github/workflows/ci.yml) and the pre-publication check (MANIFEST R3).

Usage:
    python scripts/verify_data.py [--config config.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"gho_[A-Za-z0-9]{36}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*[A-Za-z0-9]{16,}"),
]

VALID_DISPOSITIONS = {"affirmed", "reversed", "vacated", "modified",
                      "dismissed", "remitted", "mixed"}
VALID_CRIME_TYPES = {"violent", "drug", "property", "financial", "sexual",
                     "weapons", "dui_traffic", "other", None}


def check_secrets(paths: list[Path]) -> list[str]:
    errors = []
    for p in paths:
        if not p.is_file():
            continue
        content = p.read_text(encoding="utf-8", errors="ignore")
        for rx in SECRET_PATTERNS:
            m = rx.search(content)
            if m:
                errors.append(f"secret pattern {rx.pattern[:12]}… in {p}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()
    cfg = json.loads((REPO_ROOT / args.config).read_text(encoding="utf-8"))

    cases_path = REPO_ROOT / cfg["paths"]["cases_jsonl"]
    structured_path = REPO_ROOT / cfg["preprocess"]["structured_jsonl"]
    docs_dir = REPO_ROOT / cfg["paths"]["documents_dir"]
    fetch_log_path = REPO_ROOT / cfg["paths"]["fetch_log"]

    errors: list[str] = []
    warnings: list[str] = []

    # ---- raw cases ------------------------------------------------------
    raw_cases = [json.loads(l) for l in
                 cases_path.open(encoding="utf-8")] if cases_path.exists() \
        else []
    if not raw_cases:
        errors.append(f"no raw cases in {cases_path}")

    for raw in raw_cases:
        name = raw.get("case_name", "?")
        doc = REPO_ROOT / raw["document_path"]
        if not doc.exists():
            errors.append(f"{name}: missing document {doc}")
            continue
        import hashlib
        digest = hashlib.sha256(doc.read_bytes()).hexdigest()
        if digest != raw["document_sha256"]:
            errors.append(f"{name}: document sha256 mismatch")
        if not raw.get("criminal_gate", {}).get("matched_keywords"):
            errors.append(f"{name}: criminal gate not matched")
        if not raw.get("document_bytes") or doc.stat().st_size < 1000:
            errors.append(f"{name}: suspiciously small document")

    # ---- structured records ---------------------------------------------
    records = [json.loads(l) for l in
               structured_path.open(encoding="utf-8")] \
        if structured_path.exists() else []
    if not records:
        errors.append(f"no structured records in {structured_path}")

    agreements = 0
    checked = 0
    for rec in records:
        name = rec.get("case_name", "?")
        panel = rec.get("panel", {})
        if len(panel.get("judges", [])) < 3:
            errors.append(f"{name}: panel has fewer than 3 judges")
        if not panel.get("evidence"):
            warnings.append(f"{name}: panel has no evidence line")
        disp = rec.get("disposition", {})
        if disp.get("primary") not in VALID_DISPOSITIONS:
            errors.append(f"{name}: invalid disposition "
                          f"{disp.get('primary')!r}")
        if not disp.get("primary_evidence"):
            errors.append(f"{name}: disposition without evidence")
        if rec.get("crime_type", {}).get("value") not in VALID_CRIME_TYPES:
            errors.append(f"{name}: invalid crime_type")
        prov = rec.get("provenance", {})
        for key in ("courtlistener_url", "document_sha256",
                    "document_channel"):
            if not prov.get(key):
                errors.append(f"{name}: provenance missing {key}")
        if disp.get("agreement") is not None:
            checked += 1
            agreements += 1 if disp["agreement"] else 0
        elif disp.get("llm_check") is not None:
            warnings.append(f"{name}: LLM check present but agreement unset")

    # ---- provenance log ---------------------------------------------------
    if fetch_log_path.exists():
        log = json.loads(fetch_log_path.read_text(encoding="utf-8"))
        statuses = {}
        for entry in log:
            s = str(entry.get("status"))
            statuses[s] = statuses.get(s, 0) + 1
        print(f"fetch log: {len(log)} requests, statuses={statuses}")
    else:
        warnings.append("no fetch log found")

    # ---- secrets scan -----------------------------------------------------
    scan_targets = [cases_path, structured_path, fetch_log_path,
                    REPO_ROOT / "README.md", REPO_ROOT / "config.json"]
    scan_targets += sorted(docs_dir.glob("*")) if docs_dir.exists() else []
    errors += check_secrets(scan_targets)

    # ---- report -----------------------------------------------------------
    print(f"raw cases:        {len(raw_cases)}")
    print(f"structured:       {len(records)}")
    print(f"rule/LLM accord:  {agreements}/{checked}")
    print(f"dispositions:     "
          f"{[r['disposition'].get('primary') for r in records]}")
    print(f"panels:           "
          f"{[len(r['panel']['judges']) for r in records]}")
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    if errors:
        print("\nVALIDATION FAILED")
        return 1
    print("\nVALIDATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
