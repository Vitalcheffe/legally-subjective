#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — complete the Oyez window for M3 case files.

The committed Oyez sources cover OT2020+ only (they were collected for the
old site). The persona training window (OT2015..OT2019) was never fetched —
which is why data/m3 case files fell back to metadata-only on the train
side. The Oyez API is public and unauthenticated, so this script fills the
gap without touching any token budget:

  * iterates corpus cases with term <= 2019 whose normalized docket has no
    entry under data/sources/oyez/ (idempotent — rerun skips what exists);
  * the fifty sealed dockets are NOT fetched: their case files are never
    built (M4-only), so their sources are not needed — keeping them out is
    one more wall between us and the sealed set;
  * writes the same shape as the existing sources: <docket>.json with
    __source_uri__ / __retrieved_at__ provenance stamps, <docket>.miss.json
    for confirmed misses (404 / empty) so reruns don't re-ask;
  * sleeps politely (~0.7 s) — the whole gap is a few hundred requests.

Usage:  python3 scripts/fetch_oyez_window.py [--sleep 0.7] [--limit N]
"""
import argparse
import glob
import gzip
import json
import os
import re
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(REPO, "data", "processed")
OYEZ = os.path.join(REPO, "data", "sources", "oyez")
UA = {"User-Agent": "legally-subjective/1.0 (research; github:Vitalcheffe)"}


def norm_docket(s):
    if not isinstance(s, str):
        return ""
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = re.sub(r"\bno\.?\s*", "", s, flags=re.I)
    s = re.sub(r"[^0-9\-]", "", s)
    return s.strip("-.")


def nums(s):
    if not isinstance(s, str):
        return set()
    return set(re.findall(r"\d+-\d+", s.replace("–", "-").replace("—", "-")))


def have_already():
    done = set()
    for p in glob.glob(os.path.join(OYEZ, "*.json")):
        b = os.path.basename(p)
        if b.endswith(".miss.json"):
            done.add(norm_docket(b[: -len(".miss.json")]))
        else:
            done.add(norm_docket(b[: -len(".json")]))
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sleep", type=float, default=0.7)
    ap.add_argument("--limit", type=int, default=0,
                    help="max fetches this run (0 = all)")
    ap.add_argument("--until-term", type=int, default=2019)
    args = ap.parse_args()

    with gzip.open(os.path.join(PROC, "corpus_cases_v1.jsonl.gz"), "rt",
                   encoding="utf-8") as f:
        cases = [json.loads(line) for line in f]
    stats = json.load(open(os.path.join(PROC, "stats_v1.json"),
                           encoding="utf-8"))
    sealed_nums = set()
    for s in stats["five_four_selection"]["cases"]:
        sealed_nums |= nums(s)

    done = have_already()
    todo = []
    for c in cases:
        if int(c["term"]) > args.until_term:
            continue
        nd = norm_docket(c["docket_number"])
        if not nd or nd in done:
            continue
        if nums(c["docket_number"]) & sealed_nums:
            continue  # never fetch the sealed set
        todo.append((c["term"], c["docket_number"].strip(), nd))
    if args.limit:
        todo = todo[:args.limit]

    print(f"to fetch: {len(todo)} (already present: {len(done)})")
    ok = miss = err = 0
    for i, (term, raw_dn, nd) in enumerate(todo, 1):
        out = os.path.join(OYEZ, f"{nd}.json")
        miss_path = os.path.join(OYEZ, f"{nd}.miss.json")
        uri = f"https://api.oyez.org/cases/{term}/{nd}"
        try:
            req = urllib.request.Request(uri, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            if not (d.get("facts_of_the_case") or d.get("question")):
                raise ValueError("empty case body")
            d["__source_uri__"] = uri
            d["__retrieved_at__"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            tmp = out + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp, out)
            ok += 1
        except Exception as e:              # noqa: BLE001 — logged, never fatal
            code = getattr(e, "code", None)
            if code == 404:
                with open(miss_path, "w", encoding="utf-8") as f:
                    json.dump({"docket": nd, "term": term,
                               "miss": "404",
                               "__retrieved_at__": time.strftime(
                                   "%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                              f)
                    f.write("\n")
                miss += 1
            else:
                err += 1
                print(f"  [{i}/{len(todo)}] {nd}: {e} (will retry next run)")
                time.sleep(2)
        if i % 25 == 0:
            print(f"  [{i}/{len(todo)}] ok={ok} miss={miss} err={err}")
        time.sleep(args.sleep)
    print(f"done: ok={ok} miss(404)={miss} err={err}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
