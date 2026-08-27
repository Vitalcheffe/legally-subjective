#!/usr/bin/env python3
"""Export the chain-of-custody production: for every FILED docket, the exact
source files, counts, retrieval windows, and a Merkle-style tree hash over
the source cache — so any number on the site can be audited to the byte.

Writes data/productions/custody.json. Deterministic (sorted walks).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "core" / "src"))

from legally_subjective.axes import v1  # noqa: E402

SOURCES = REPO / "data" / "sources"


def tree_hash(paths: list[Path]) -> str:
    """sha256 over sorted (relpath + file sha256) pairs — an audit anchor."""
    h = hashlib.sha256()
    for p in sorted(paths):
        rel = p.relative_to(REPO).as_posix()
        fh = hashlib.sha256(p.read_bytes()).hexdigest()
        h.update(rel.encode())
        h.update(fh.encode())
    return h.hexdigest().upper()


def retrieval_window(paths: list[Path]) -> tuple[str | None, str | None]:
    times: list[str] = []
    for p in paths:
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        t = d.get("__retrieved_at__") if isinstance(d, dict) else None
        if not t and isinstance(d, dict) and "pages" in d:
            ts = [pg.get("retrieved_at") for pg in d["pages"] if pg.get("retrieved_at")]
            times.extend(ts)
            continue
        if t:
            times.append(t)
    return (min(times), max(times)) if times else (None, None)


def main() -> int:
    dockets = sorted((REPO / "data" / "dockets").glob("LS-J-*.json"))
    votes = v1.load_oyez_votes()
    per_slug_cases: dict[str, set[str]] = {}
    for v in votes:
        per_slug_cases.setdefault(v["justice"], set()).add(str(v["docket"]).strip())

    custody: dict[str, dict] = {}
    for dp in dockets:
        d = json.loads(dp.read_text())
        slug = d["subject"]["slug"]
        case_files = sorted(
            (SOURCES / "oyez" / f"{dock}.json" for dock in sorted(per_slug_cases.get(slug, set())))
        )
        judge_dir = SOURCES / "courtlistener" / "judges" / slug
        judge_files = sorted(judge_dir.glob("*.json")) if judge_dir.exists() else []
        index_files = sorted((SOURCES / "courtlistener" / "index").glob("*.json"))
        oyez_first, oyez_last = retrieval_window(case_files)
        cl_first, cl_last = retrieval_window(judge_files + index_files)
        custody[d["docket"]] = {
            "subject": d["subject"]["name"],
            "axes": {
                "disposition": {
                    "system": "oyez",
                    "files": len(case_files),
                    "cache": "data/sources/oyez/<docket>.json",
                    "uri_pattern": "https://api.oyez.org/cases/<term>/<docket>",
                    "retrieved_window": [oyez_first, oyez_last],
                    "tree_sha256": tree_hash(case_files),
                },
                "temperament": {
                    "system": "oyez",
                    "files": len(case_files),
                    "cache": "data/sources/oyez/<docket>.json",
                    "uri_pattern": "https://api.oyez.org/cases/<term>/<docket>",
                    "retrieved_window": [oyez_first, oyez_last],
                    "tree_sha256": tree_hash(case_files),
                },
                "precedent": {
                    "system": "courtlistener",
                    "files": len(judge_files),
                    "cache": f"data/sources/courtlistener/judges/{slug}/opinions__page_NNN.json",
                    "uri_pattern": "https://www.courtlistener.com/api/rest/v4/search/?judge=…&court=scotus&type=o",
                    "retrieved_window": [cl_first, cl_last],
                    "tree_sha256": tree_hash(judge_files),
                },
                "exposure": {
                    "system": "courtlistener",
                    "files": len(judge_files),
                    "cache": f"data/sources/courtlistener/judges/{slug}/opinions__page_NNN.json",
                    "uri_pattern": "https://www.courtlistener.com/api/rest/v4/search/?judge=…&court=scotus&type=o",
                    "retrieved_window": [cl_first, cl_last],
                    "tree_sha256": tree_hash(judge_files),
                },
            },
            "index": {
                "files": len(index_files),
                "cache": "data/sources/courtlistener/index/",
                "retrieved_window": [cl_first, cl_last],
                "tree_sha256": tree_hash(index_files),
            },
            "docket_sha256": d.get("chain", {}).get("sha256"),
        }

    out = {
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "law": "Every non-null value in a FILED docket traces to >= 1 public source URI, cached with retrieval timestamps. Tree hashes cover the exact cache bytes the docket was computed from.",
        "dockets": custody,
    }
    (REPO / "data" / "productions" / "custody.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True)
    )
    print(f"custody.json — {len(custody)} dockets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
