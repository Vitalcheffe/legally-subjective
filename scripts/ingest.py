#!/usr/bin/env python3
"""LS ingest driver — phases:

  index   enumerate SCOTUS clusters since 2020-10-01 (CourtListener /search/)
  oyez    fetch per-case voting detail for every merits docket (Oyez API)
  judges  fetch per-justice lead-opinion pages (CourtListener /search/ judge=)

All fetches are cache-first and resume-safe: re-run until "complete".
Every phase writes a small state file under data/sources/ recording URIs and
retrieval timestamps. Zero fabrication: nothing is estimated, only cached.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "core" / "src"))

from legally_subjective.ingest import courtlistener as cl  # noqa: E402
from legally_subjective.ingest import oyez  # noqa: E402

WINDOW_START = "2020-10-01"  # first Monday of OT2020 — the declared bench window

# The Nine — CourtListener /search/ `judge=` matches the LEAD author string.
# NB: CL's own data contains "Elana Kagan" (sic) and "Samuel Alito".
THE_NINE = [
    ("roberts", "John G. Roberts"),
    ("thomas", "Clarence Thomas"),
    ("alito", "Samuel Alito"),
    ("sotomayor", "Sonia Sotomayor"),
    ("kagan", "Elana Kagan"),
    ("gorsuch", "Neil Gorsuch"),
    ("kavanaugh", "Brett Kavanaugh"),
    ("barrett", "Amy Coney Barrett"),
    ("jackson", "Ketanji Brown Jackson"),
]

SOURCES = REPO / "data" / "sources"
INDEX_DIR = SOURCES / "courtlistener" / "index"
JUDGES_DIR = SOURCES / "courtlistener" / "judges"
OYEZ_DIR = SOURCES / "oyez"


def phase_index() -> int:
    """Enumerate every SCOTUS cluster in the window; keep one record per
    cluster_id (search can return duplicate rows for multi-opinion clusters)."""
    print(f"[index] enumerating SCOTUS clusters filed after {WINDOW_START} …")
    results = cl.search_all_pages(
        INDEX_DIR,
        label="scotus_window",
        court="scotus",
        type="o",
        stat_Precedential="on",
        filed_after=WINDOW_START,
    )
    clusters: dict[str, dict] = {}
    for r in results:
        cid = r.get("cluster_id")
        if cid is None:
            continue
        cur = clusters.get(str(cid))
        if cur is None or (r.get("dateArgued") and not cur.get("dateArgued")):
            clusters[str(cid)] = {
                "cluster_id": cid,
                "caseName": r.get("caseName"),
                "docketNumber": r.get("docketNumber"),
                "docket_id": r.get("docket_id"),
                "dateFiled": r.get("dateFiled"),
                "dateArgued": r.get("dateArgued"),
                "judge": r.get("judge"),  # lead author string (or Per Curiam)
                "court_id": r.get("court_id"),
                "absolute_url": r.get("absolute_url"),
            }
    out = {
        "window_start": WINDOW_START,
        "source": "courtlistener:/api/rest/v4/search/?court=scotus&type=o&stat_Precedential=on&filed_after=" + WINDOW_START,
        "clusters": sorted(clusters.values(), key=lambda c: (c.get("dateFiled") or "", str(c.get("cluster_id")))),
    }
    (INDEX_DIR / "index.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    merits = [c for c in out["clusters"] if oyez.is_merits_docket(c.get("docketNumber"))]
    print(f"[index] {len(out['clusters'])} clusters · {len(merits)} merits dockets · index.json written")
    return 0


def phase_oyez(max_requests: int) -> int:
    """Fetch Oyez detail for each merits docket not yet cached."""
    idx = json.loads((INDEX_DIR / "index.json").read_text())
    todos: list[dict] = []
    seen: set[str] = set()
    for c in idx["clusters"]:
        d = (c.get("docketNumber") or "").strip()
        if oyez.is_merits_docket(d) and d not in seen:
            seen.add(d)
            if not (OYEZ_DIR / f"{d}.json").exists() and not (OYEZ_DIR / f"{d}.miss.json").exists():
                todos.append({"docket": d, "dateFiled": c.get("dateFiled")})
    total, done = len(seen), len(seen) - len(todos)
    print(f"[oyez] merits dockets: {total} unique · {done} cached · {len(todos)} to fetch")
    n = 0
    for t in todos:
        if n >= max_requests:
            print(f"[oyez] budget reached ({max_requests}) — re-run to continue")
            return 0
        oyez.fetch_case(t["docket"], t["dateFiled"] or "")
        n += 1
        if n % 25 == 0:
            print(f"[oyez] {n}/{len(todos)} fetched …")
    hits = len(list(OYEZ_DIR.glob("*.json"))) - len(list(OYEZ_DIR.glob("*.miss.json")))
    misses = len(list(OYEZ_DIR.glob("*.miss.json")))
    print(f"[oyez] complete — {hits} case files · {misses} recorded misses")
    return 0


def phase_judges(max_requests: int) -> int:
    """Per-justice lead-opinion pages (citations live in `opinions[].cites`)."""
    n = 0
    for slug, judge_str in THE_NINE:
        d = JUDGES_DIR / slug
        done_pages = len(list(d.glob("*.json"))) if d.exists() else 0
        before = time.time()
        pages = cl.search_all_pages(
            d,
            label="opinions",
            court="scotus",
            type="o",
            judge=judge_str,
            filed_after=WINDOW_START,
        )
        n += len(list(d.glob("*.json"))) - done_pages if d.exists() else 0
        authors = set()
        for r in pages:
            for op in r.get("opinions", []):
                if op.get("author_id") is not None:
                    authors.add(op["author_id"])
        print(
            f"[judges] {judge_str:<22} {len(pages):>3} lead opinions · "
            f"author_ids={sorted(authors)} · {time.time()-before:.0f}s"
        )
        if n >= max_requests:
            print(f"[judges] budget reached ({max_requests}) — re-run to continue")
            return 0
    print("[judges] complete")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["index", "oyez", "judges", "all"], default="all")
    ap.add_argument("--max-requests", type=int, default=250, help="network budget for this run")
    args = ap.parse_args()
    if args.phase in ("index", "all"):
        phase_index()
    if args.phase in ("oyez", "all"):
        phase_oyez(args.max_requests)
    if args.phase in ("judges", "all"):
        phase_judges(args.max_requests)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
