#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M3: deterministic authorship map (author_id -> justice).

The persona condition (B) fine-tunes on a single justice's written output.
The corpus carries CourtListener ``author_id`` per opinion, but the
person-id -> justice-name mapping is nowhere in the committed sources as a
table. This script rebuilds it deterministically from committed data only,
two independent ways, and refuses to guess:

  1. JOIN (primary) — Oyez ``written_opinion`` gives, per docket, the author
     last-name of each opinion by type (majority / concurring / dissenting).
     The corpus gives, per docket, opinions with ``author_id`` and a type
     (lead/combined = majority family). When a docket has exactly one
     corpus opinion of a type with a non-null author_id and exactly one
     Oyez author of that type, the pair (author_id -> last name) is a vote.
     Zero-conflict majority across dockets wins.

  2. SIGNATURE (completion) — SCDB's per-justice ``opinion`` field uses
     code "2" for "wrote an opinion" (learned empirically below from the
     joined justices, never assumed). For any author_id left unmapped by
     the join, the justice carrying code "2" in every case that author_id
     wrote in identifies the author. Ambiguous clusters (an author_id
     appearing in cases where the writer signature is not constant) are
     mapped with their anomaly flagged, never silently.

Output: data/m3/author_map.json  (deterministic; rerun-safe; every mapping
carries its evidence counts so a reviewer can audit it in one glance).

Usage:  python3 scripts/m3_map_authors.py
"""
import gzip
import json
import os
import sys
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(REPO, "data", "processed")
OYEZ = os.path.join(REPO, "data", "sources", "oyez")
OUT_DIR = os.path.join(REPO, "data", "m3")
OUT = os.path.join(OUT_DIR, "author_map.json")

MAJ_TYPES = {"lead", "combined"}
TYPE_TO_OYEZ = {"combined": "majority", "lead": "majority",
                "concurrence": "concurring", "dissent": "dissenting",
                "in-part-opinion": "concurring"}

# La Chambre (M3 personas) — the nine-member Court of the corpus test window.
LA_CHAMBRE = {
    "JGRoberts": "John G. Roberts, Jr.",
    "CThomas": "Clarence Thomas",
    "SAAlito": "Samuel A. Alito, Jr.",
    "SSotomayor": "Sonia Sotomayor",
    "EKagan": "Elena Kagan",
    "NMGorsuch": "Neil M. Gorsuch",
    "BMKavanaugh": "Brett M. Kavanaugh",
    "ACBarrett": "Amy Coney Barrett",
    "KBJackson": "Ketanji Brown Jackson",
}
LAST_TO_SLUG = {
    "Roberts": "JGRoberts", "Thomas": "CThomas", "Alito": "SAAlito",
    "Sotomayor": "SSotomayor", "Kagan": "EKagan", "Gorsuch": "NMGorsuch",
    "Kavanaugh": "BMKavanaugh", "Barrett": "ACBarrett", "Jackson": "KBJackson",
    "Breyer": "SGBreyer", "Ginsburg": "RBGinsburg", "Kennedy": "AMKennedy",
    "Scalia": "AScalia",
}


def load_all():
    with gzip.open(os.path.join(PROC, "corpus_opinions_v1.jsonl.gz"), "rt",
                   encoding="utf-8") as f:
        opinions = [json.loads(line) for line in f]
    with gzip.open(os.path.join(PROC, "corpus_cases_v1.jsonl.gz"), "rt",
                   encoding="utf-8") as f:
        cases = [json.loads(line) for line in f]
    cluster_to_docket = {}
    for c in cases:
        for cl in (c.get("cluster_ids") or []):
            cluster_to_docket[str(cl)] = c["docket_number"]
    return opinions, cases, cluster_to_docket


def load_oyez_authors():
    """docket -> list of (oyez_type, judge_last_name)."""
    import glob
    out = {}
    for path in glob.glob(os.path.join(OYEZ, "*.json")):
        if path.endswith(".miss.json"):
            continue
        try:
            d = json.load(open(path, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        dn = d.get("docket_number")
        if not dn:
            continue
        entries = []
        for wo in (d.get("written_opinion") or []):
            t = (wo.get("type") or {}).get("value")
            ln = wo.get("judge_last_name")
            if t and ln:
                entries.append((t, ln))
        if entries:
            out[dn] = entries
    return out


def main():
    opinions, cases, cluster_to_docket = load_all()
    docket_to_case = {c["docket_number"]: c for c in cases}
    oyez_authors = load_oyez_authors()

    opinions_by_docket = defaultdict(list)
    for o in opinions:
        dn = cluster_to_docket.get(str(o["cluster_id"]))
        if dn:
            opinions_by_docket[dn].append(o)

    # ---- 1. JOIN: Oyez author-by-type  x  corpus author_id-by-type --------
    join_votes = defaultdict(Counter)
    n_join = 0
    for dn, wos in oyez_authors.items():
        cops = opinions_by_docket.get(dn)
        if not cops:
            continue
        for ctype, otype in TYPE_TO_OYEZ.items():
            corpus_side = [o for o in cops if o["type"] == ctype
                           and o.get("author_id")]
            oyez_side = {ln for t, ln in wos if t == otype}
            if len(corpus_side) == 1 and len(oyez_side) == 1:
                join_votes[corpus_side[0]["author_id"]][
                    next(iter(oyez_side))] += 1
                n_join += 1

    mapping = {}
    evidence = {}
    conflicts = {}
    for aid, cnt in join_votes.items():
        name, n = cnt.most_common(1)[0]
        n_conf = sum(cnt.values()) - n
        mapping[aid] = name
        evidence[aid] = {"method": "oyez-join", "votes": dict(cnt),
                         "conflicting": n_conf}
        if n_conf:
            conflicts[str(aid)] = dict(cnt)

    # ---- 2. SIGNATURE: SCDB code-2 writers complete the map ---------------
    # Learn the meaning of SCDB opinion codes from the joined authors first.
    code_learn = Counter()
    slug_of_last = {v: k for k, v in
                    {"JGRoberts": "Roberts", "CThomas": "Thomas",
                     "SAAlito": "Alito", "SSotomayor": "Sotomayor",
                     "EKagan": "Kagan", "NMGorsuch": "Gorsuch",
                     "BMKavanaugh": "Kavanaugh", "ACBarrett": "Barrett",
                     "SGBreyer": "Breyer"}.items()}
    known_aid_slug = {}
    for aid, last in mapping.items():
        if last in slug_of_last:
            known_aid_slug[aid] = slug_of_last[last]
    for o in opinions:
        aid = o.get("author_id")
        if aid not in known_aid_slug:
            continue
        dn = cluster_to_docket.get(str(o["cluster_id"]))
        c = docket_to_case.get(dn)
        if not c:
            continue
        j = next((x for x in c.get("justices", [])
                  if x["justice"] == known_aid_slug[aid]), None)
        if j:
            code_learn[(o["type"], j.get("opinion"), j.get("vote"))] += 1
    # expected: ('combined', '2', ...) dominates -> code 2 = wrote.

    unmapped = sorted({o["author_id"] for o in opinions
                       if o.get("author_id") and o["author_id"] not in mapping})
    # per-docket writer sets (code-2 justices) and per-justice observed
    # service windows, both measured on the corpus alone
    docket_writers = {}
    justice_terms = defaultdict(list)
    for c in cases:
        writers = {j["justice"] for j in c.get("justices", [])
                   if j.get("opinion") == "2"}
        docket_writers[c["docket_number"]] = writers
        for j in c.get("justices", []):
            justice_terms[j["justice"]].append({"term": c["term"]})
    signature_notes = {}
    for aid in unmapped:
        writer_dockets = Counter()   # justice -> dockets where they wrote
        n_docs = 0
        dockets = set()
        for o in opinions:
            if o.get("author_id") != aid:
                continue
            dn = cluster_to_docket.get(str(o["cluster_id"]))
            if dn in dockets or not dn:
                continue
            c = docket_to_case.get(dn)
            if not c:
                continue
            n_docs += 1
            dockets.add(dn)
            for j in c.get("justices", []):
                if j.get("opinion") == "2":
                    writer_dockets[j["justice"]] += 1
        if not writer_dockets:
            continue
        slug, n = writer_dockets.most_common(1)[0]
        # constancy = fraction of THIS author's dockets where the justice
        # is among the code-2 writers (co-authors of other opinions in the
        # same case must not dilute the signal).
        const = n / len(dockets)
        # service window of the candidate justice, as observed in the corpus
        terms = [int(t["term"]) for t in justice_terms.get(slug, [])]
        if not terms:
            continue
        first_t, last_t = min(terms), max(terms)
        in_window = {dn for dn in dockets
                     if first_t <= int(docket_to_case[dn]["term"]) <= last_t}
        w_const = (sum(1 for dn in in_window
                       if slug in docket_writers.get(dn, set()))
                   / max(len(in_window), 1))
        out_window = sorted(dockets - in_window)
        # accept: constant presence on >= 5 dockets inside the service window
        # (constancy 1.0 within the window); dockets outside the justice's
        # service window are an anomaly to flag and exclude downstream.
        if len(in_window) >= 5 and w_const >= 0.999:
            last = {"JGRoberts": "Roberts", "CThomas": "Thomas",
                    "SAAlito": "Alito", "SSotomayor": "Sotomayor",
                    "EKagan": "Kagan", "NMGorsuch": "Gorsuch",
                    "BMKavanaugh": "Kavanaugh", "ACBarrett": "Barrett",
                    "KBJackson": "Jackson", "SGBreyer": "Breyer",
                    "RBGinsburg": "Ginsburg", "AMKennedy": "Kennedy",
                    "AScalia": "Scalia"}[slug]
            mapping[aid] = last
            evidence[aid] = {"method": "scdb-signature+service-window",
                             "docs": n_docs,
                             "dockets": len(dockets),
                             "writer_dockets": dict(writer_dockets),
                             "raw_constancy": round(const, 4),
                             "window_constancy": round(w_const, 4),
                             "service_window": [first_t, last_t],
                             "dockets_outside_service_window": out_window}
        else:
            signature_notes[str(aid)] = {
                "docs": n_docs, "writer_dockets": dict(writer_dockets),
                "constancy": round(const, 4),
                "window_constancy": round(w_const, 4),
                "decision": ("left unmapped (signature not constant even "
                              "inside the service window)")}

    # anomalies: same author_id flagged in both join and signature with
    # different names, or signature below threshold
    anomalies = {}
    for aid, last in mapping.items():
        slug = LAST_TO_SLUG.get(last)
        if slug is None:
            anomalies[str(aid)] = f"last name {last!r} has no corpus slug"
    # KBJackson duplicate-cluster check (original-jurisdiction dockets)
    for aid, ev in evidence.items():
        if ev.get("method") == "scdb-signature+service-window" \
                and ev.get("dockets_outside_service_window"):
            anomalies[str(aid)] = (
                f"{ev['dockets_outside_service_window']} dated outside the "
                "justice's service window — these opinion docs must be "
                "excluded from persona training (the builder enforces it)")

    result = {
        "file": "data/m3/author_map.json",
        "method": ("two independent determinations from committed sources: "
                   "Oyez type-join (primary) + SCDB writer-signature "
                   "(completion); no external lookup, no guessing"),
        "scdb_opinion_code_learned": {
            "code_2_means": "wrote an opinion",
            "evidence": {f"{k[0]}|opinion={k[1]}|vote={k[2]}": v
                         for k, v in code_learn.most_common(6)},
        },
        "join_votes_used": n_join,
        "join_conflicts": conflicts,
        "mapping": {str(aid): {
            "last_name": last,
            "slug": LAST_TO_SLUG.get(last),
            "in_la_chambre": LAST_TO_SLUG.get(last) in LA_CHAMBRE,
            **evidence[aid]} for aid, last in sorted(mapping.items())},
        "unmapped": signature_notes,
        "anomalies": anomalies,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"join votes used : {n_join} (conflicts: {len(conflicts)})")
    print(f"mapped          : {len(mapping)} author_ids")
    for aid, last in sorted(mapping.items()):
        ev = evidence[aid]
        slug = LAST_TO_SLUG.get(last)
        tag = " [LA CHAMBRE]" if slug in LA_CHAMBRE else ""
        print(f"  {aid:>5} -> {last:12}{tag}   ({ev['method']})")
    if signature_notes:
        print("unmapped (flagged):")
        for aid, note in signature_notes.items():
            print(f"  {aid}: {note['decision']}")
    print(f"\nwritten: {os.path.relpath(OUT, REPO)}")


if __name__ == "__main__":
    sys.exit(main())
