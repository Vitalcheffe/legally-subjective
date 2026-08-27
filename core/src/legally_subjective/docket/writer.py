"""Docket writer — canonical JSON artifacts per LS-1.0 sec. 4.

Canonicalization: keys sorted lexicographically, UTF-8, compact separators,
no trailing whitespace. The `chain.sha256` is computed over the serialization
of the whole object minus the `chain.sha256` field itself, and written last.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DOCKETS = REPO / "data" / "dockets"


def canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def seal_chain(docket: dict) -> dict:
    """Compute and attach chain.sha256 over the canonical serialization."""
    chain = dict(docket.get("chain") or {})
    chain.pop("sha256", None)
    docket["chain"] = chain
    payload = canonical(docket)
    chain["sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
    docket["chain"] = chain
    return docket


def file_docket(docket: dict) -> Path:
    DOCKETS.mkdir(parents=True, exist_ok=True)
    sealed = seal_chain(docket)
    # verify: the seal must reproduce from the written bytes
    p = DOCKETS / f"{docket['docket']}.json"
    p.write_text(json.dumps(sealed, sort_keys=True, ensure_ascii=False, indent=1))
    reread = json.loads(p.read_text())
    expect = reread["chain"].pop("sha256")
    assert hashlib.sha256(canonical(reread).encode("utf-8")).hexdigest().upper() == expect, "chain seal broken"
    return p
