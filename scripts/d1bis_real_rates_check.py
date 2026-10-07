#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Derivation + validation of the per-seat actual liberal-vote rates on the
transparent window (n = 211 casefiles), used by paper_figures_d1bis.py.

Method: join data/m3/casefiles (window=test, 211 dockets) with the frozen
corpus data/processed/corpus_cases_v1.jsonl.gz (per-justice SCDB vote
directions: 1 = conservative, 2 = liberal), using the canonical docket
key of the frozen M4 builder (scripts/m4_scoring.py::canon_docket).

VALIDATION (fail-safe): the arm-N predictions of
results/a1_e1_predictions.json are re-scored against the joined truth;
the per-justice accuracies must reproduce EXACTLY the arm-N accuracies
published in results/a1_e1_decomposition.json (supplements). Any
mismatch aborts with a non-zero exit code.

Inter-run rule (docs/16-D1BIS-VERROUILLAGE-RESULTATS.md): these rates
belong to the E1 window; phase-T values are quoted as published and
never mixed with E1-internal numbers.
"""
import glob
import gzip
import json
import os
import re
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_OF = {"1": "conservative", "2": "liberal"}


def canon_docket(s):
    s = (s or "").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", s).strip().rstrip(".")


def main():
    test = {}
    for f in glob.glob(os.path.join(REPO, "data/m3/casefiles/*.json")):
        d = json.load(open(f))
        if d.get("window") == "test":
            test[canon_docket(d["docket"])] = True
    votes = {}
    with gzip.open(os.path.join(REPO, "data/processed",
                                "corpus_cases_v1.jsonl.gz"), "rt",
                   encoding="utf-8") as fh:
        for line in fh:
            c = json.loads(line)
            key = canon_docket(c.get("docket_number"))
            v = {}
            for j in c.get("justices") or []:
                dcode = DIR_OF.get(j.get("direction"))
                if dcode:
                    v[j["justice"]] = dcode
            if v:
                votes[key] = v
    per = defaultdict(lambda: [0, 0])
    for key in test:
        for jus, direction in votes.get(key, {}).items():
            per[jus][1] += 1
            if direction == "liberal":
                per[jus][0] += 1
    rates = {j: l / t for j, (l, t) in per.items() if t >= 20}

    # validation against the published E1 arm-N accuracies
    e1 = json.load(open(os.path.join(REPO, "results",
                                     "a1_e1_decomposition.json")))
    published = e1["supplements_non_preinscrits"][
        "accuracy_vote_par_juge_par_bras"]["N"]
    preds = json.load(open(os.path.join(REPO, "results",
                                        "a1_e1_predictions.json"))
                      )["predictions"]["N"]
    pred_by = {canon_docket(p["docket"]): p["vote"] for p in preds}
    ok = True
    for jus, pub in published.items():
        k = n = 0
        for key in test:
            pv = pred_by.get(key)
            truth = votes.get(key, {}).get(jus)
            if pv and truth:
                n += 1
                k += (pv == truth)
        recomputed = k / n
        match = abs(recomputed - pub["accuracy"]) < 5e-5
        ok &= match
        print(f"  {jus:14s} N-acc recomputed {recomputed:.4f} "
              f"vs published {pub['accuracy']:.4f}  "
              f"{'MATCH' if match else 'MISMATCH'}")
    if not ok:
        print("VALIDATION FAILED - do not use these rates")
        return 1
    print("\nActual liberal-vote rates, transparent window (n = 211):")
    for j, r in sorted(rates.items(), key=lambda x: -x[1]):
        print(f"  {j:14s} {r:.4f}  ({per[j][0]}/{per[j][1]})")
    print("\nVALIDATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
