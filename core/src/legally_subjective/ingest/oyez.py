"""Oyez API client — public case detail with per-justice votes.

The Oyez case detail (https://api.oyez.org/cases/<term>/<docket>) is the
primary source for voting behavior:

- decisions[0].description — the disposition sentence ("... is reversed")
- decisions[0].votes[]     — one record per justice:
    member.name / member.last_name / member.identifier
    vote                    — "majority" | "minority" | other
    opinion_type            — majority | concurrence | special concurrence |
                              dissent | second dissent | none
    joining                 — justice whose opinion they joined (joiners)

URL mechanics (verified 2026-08-27): unknown term/docket pairs fall back to
a generic 30-case list — detected and recorded as a MISS, never as data.
Term derivation: SCOTUS terms start the first Monday of October; a case
filed in Jan–Sep belongs to the previous year's term.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.oyez.org"
UA = "legally-subjective/1.0 (open standard; contact: https://legallysubjective.org)"
REPO = Path(__file__).resolve().parents[4]
CACHE = REPO / "data" / "sources" / "oyez"

MAX_RETRIES = 3
MERITS_DOCKET = re.compile(r"^\d{2}-\d{3,4}$")


def is_merits_docket(docket: str | None) -> bool:
    """Merits dockets look like '25-197'. Emergency applications ('26A124')
    and originals ('22o138') are excluded — they carry no merits votes."""
    return bool(docket and MERITS_DOCKET.match(docket.strip()))


def term_candidates(date_filed: str) -> list[int]:
    """Candidate Oyez terms for a case filed on `date_filed` (YYYY-MM-DD)."""
    year, month = int(date_filed[:4]), int(date_filed[5:7])
    term = year if month >= 10 else year - 1
    return [term, term - 1, term + 1]


def _get(url: str, timeout: int = 30) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                last_err = e
            else:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
        time.sleep(2.0 * attempt)
    raise RuntimeError(f"Oyez fetch failed after {MAX_RETRIES} attempts: {url} ({last_err})")


def fetch_case(docket: str, date_filed: str, sleep: float = 0.35) -> dict | None:
    """Fetch one case by docket + filing date. Returns the case dict or None
    on miss. Cache-first: an existing cache file is returned without network.
    Misses are cached too (a miss is a fact — it stays a miss)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    hit_file = CACHE / f"{docket}.json"
    miss_file = CACHE / f"{docket}.miss.json"
    if hit_file.exists():
        return json.loads(hit_file.read_text())
    if miss_file.exists():
        return None

    for term in term_candidates(date_filed):
        url = f"{API}/cases/{term}/{urllib.parse.quote(docket)}"
        data = _get(url)
        if isinstance(data, dict) and data.get("name"):
            data["__source_uri__"] = url
            data["__retrieved_at__"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            hit_file.write_text(json.dumps(data, ensure_ascii=False))
            time.sleep(sleep)
            return data
    miss_file.write_text(
        json.dumps(
            {
                "docket": docket,
                "date_filed": date_filed,
                "tried_terms": term_candidates(date_filed),
                "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "reason": "oyez-fallback-list (case not indexed under tried terms)",
            },
            indent=1,
        )
    )
    return None


def load_cached_cases() -> list[dict]:
    """All cached Oyez case details, ordered by docket for determinism."""
    out: list[dict] = []
    if not CACHE.exists():
        return out
    for f in sorted(CACHE.glob("*.json")):
        if f.name.endswith(".miss.json"):
            continue
        out.append(json.loads(f.read_text()))
    return out
