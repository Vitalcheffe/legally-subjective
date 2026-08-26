#!/usr/bin/env python3
"""Legally Subjective — data validation gate (R3/R9).

Checks that the committed datasets are complete, traceable and honest:

  - every raw case has a document, a sha256 and a criminal-gate match;
  - every structured record has: a panel, a disposition with evidence, a
    provenance block;
  - rule-vs-LLM disposition agreement is reported (not required —
    disagreements are flags for human review, not errors);
  - no credential strings (ghp_, sk-, api keys) anywhere in the data.

Two severity levels, mapped to the project's honesty rules:

  structural integrity (always an ERROR) — document present, sha256
  match, criminal gate, provenance fields, valid schema values. A
  violation means the dataset is not what it claims to be.

  extraction quality (sample: ERROR / corpus: WARNING) — panel size,
  disposition found. The 5-case sample was hand-verified (R10), so a
  defect there is a regression. The corpus is a raw dataset at scale:
  extraction gaps are expected, flagged, and routed to the human
  adjudication queue — hiding them behind a green checkmark would be
  the actual failure (R6).

Exits non-zero on any error: this is the CI gate
(.github/workflows/ci.yml) and the pre-publication check (MANIFEST R3).

Usage:
    python scripts/verify_data.py [--config config.json]
        [--mode sample|corpus]
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


def dataset_paths(cfg: dict, mode: str) -> tuple[Path, Path, Path, Path]:
    """(cases_jsonl, structured_jsonl, documents_dir, fetch_log) for the
    requested mode."""
    paths = cfg["paths"] if mode == "sample" else cfg["paths_corpus"]
    pre = cfg["preprocess"] if mode == "sample" else cfg["preprocess_corpus"]
    return (REPO_ROOT / paths["cases_jsonl"],
            REPO_ROOT / pre["structured_jsonl"],
            REPO_ROOT / paths["documents_dir"],
            REPO_ROOT / paths["fetch_log"])


def run_checks(cfg: dict, mode: str = "sample") -> dict:
    """Validate one dataset mode. Returns a report dict; the CLI turns
    errors into a non-zero exit code."""
    cases_path, structured_path, docs_dir, fetch_log_path = \
        dataset_paths(cfg, mode)
    strict_extraction = mode == "sample"

    errors: list[str] = []
    warnings: list[str] = []

    def flag(message: str) -> None:
        """Extraction-quality issue: error for the verified sample,
        warning (adjudication flag) for the corpus."""
        (errors if strict_extraction else warnings).append(message)

    # ---- raw cases ------------------------------------------------------
    raw_cases = [json.loads(l) for l in
                 cases_path.open(encoding="utf-8")] if cases_path.exists() \
        else []
    if not raw_cases:
        errors.append(f"no raw cases in {cases_path}")

    import hashlib
    for raw in raw_cases:
        name = raw.get("case_name", "?")
        doc = REPO_ROOT / raw["document_path"]
        if not doc.exists():
            errors.append(f"{name}: missing document {doc}")
            continue
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
    no_disposition = 0
    no_panel = 0
    for rec in records:
        name = rec.get("case_name", "?")
        panel = rec.get("panel", {})
        if len(panel.get("judges", [])) < 3:
            no_panel += 1
            flag(f"{name}: panel has fewer than 3 judges")
        if not panel.get("evidence"):
            warnings.append(f"{name}: panel has no evidence line")
        disp = rec.get("disposition", {})
        if disp.get("primary") is None:
            no_disposition += 1
            flag(f"{name}: no disposition extracted — adjudication queue")
        elif disp.get("primary") not in VALID_DISPOSITIONS:
            errors.append(f"{name}: invalid disposition "
                          f"{disp.get('primary')!r}")
        if disp.get("primary") is not None and not disp.get(
                "primary_evidence"):
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
    log_summary = None
    if fetch_log_path.exists():
        log = json.loads(fetch_log_path.read_text(encoding="utf-8"))
        statuses: dict[str, int] = {}
        for entry in log:
            s = str(entry.get("status"))
            statuses[s] = statuses.get(s, 0) + 1
        log_summary = {"requests": len(log), "statuses": statuses}
    else:
        warnings.append("no fetch log found")

    # ---- secrets scan -----------------------------------------------------
    scan_targets = [cases_path, structured_path, fetch_log_path,
                    REPO_ROOT / "README.md", REPO_ROOT / "config.json"]
    scan_targets += sorted(docs_dir.glob("*")) if docs_dir.exists() else []
    errors += check_secrets(scan_targets)

    return {
        "mode": mode,
        "raw_cases": len(raw_cases),
        "structured": len(records),
        "agreements": agreements,
        "checked": checked,
        "no_disposition": no_disposition,
        "no_panel": no_panel,
        "errors": errors,
        "warnings": warnings,
        "fetch_log": log_summary,
    }


def print_report(report: dict) -> None:
    print(f"mode:             {report['mode']}")
    print(f"raw cases:        {report['raw_cases']}")
    print(f"structured:       {report['structured']}")
    print(f"rule/LLM accord:  {report['agreements']}/{report['checked']}")
    print(f"no disposition:   {report['no_disposition']} "
          f"(adjudication queue)")
    print(f"thin panels:      {report['no_panel']}")
    if report["fetch_log"]:
        s = report["fetch_log"]
        print(f"fetch log:        {s['requests']} requests, "
              f"statuses={s['statuses']}")
    for w in report["warnings"]:
        print(f"WARN  {w}")
    for e in report["errors"]:
        print(f"ERROR {e}")
    if report["errors"]:
        print("\nVALIDATION FAILED")
    else:
        print("\nVALIDATION PASSED")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--mode", choices=["sample", "corpus"],
                        default="sample",
                        help="which dataset to validate (default: sample)")
    args = parser.parse_args()
    cfg = json.loads((REPO_ROOT / args.config).read_text(encoding="utf-8"))
    report = run_checks(cfg, args.mode)
    print_report(report)
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
