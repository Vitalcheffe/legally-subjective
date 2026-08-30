#!/usr/bin/env python3
"""M1.5 extra — segments d'opinions séparées dans les documents pluriels.

texts.jsonl.gz ne garde que le segment MAJORITAIRE de chaque document ;
les opinions séparées (dissidences, concordances) qui vivent dans les
mêmes PDF sont perdues. Ce script re-parcourt les documents bruts,
segmente par signature de juge, et émet un (slug, role, docket, texte)
par segment — dédupliqué par sha256.

Sortie : data/m15_store/storage/segments.jsonl
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m15_storage_harvest import (CDN, CASES, DOCS_DIR, HEAD_RE,  # noqa: E402
                                 clean_docket, clean_text, extract_text)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "data", "m15_store", "storage", "segments.jsonl")
AMAP = os.path.join(REPO, "data", "m3", "author_map.json")

SERVICE = {
    "JGRoberts": (2005, 2035), "CThomas": (1991, 2035),
    "SAAlito": (2006, 2035), "SSotomayor": (2009, 2035),
    "EKagan": (2010, 2035), "NMGorsuch": (2017, 2035),
    "BMKavanaugh": (2018, 2035), "ACBarrett": (2020, 2035),
    "KBJackson": (2022, 2035), "SGBreyer": (1994, 2022),
    "RBGinsburg": (1993, 2020), "AMKennedy": (1988, 2018),
}


def role_of(frag, full=""):
    f = ((frag or "") + " " + (full or ""))[:400].lower()
    if "dissent" in f and "concurr" in f:
        return "concurrence-dissent"
    if "dissent" in f:
        return "dissent"
    if "concurr" in f:
        return "concurrence"
    if "statement" in f:
        return "statement"
    return "lead"


def main():
    amap = json.load(open(AMAP))["mapping"]
    last2slug = {v["last_name"].lower(): v["slug"] for v in amap.values()}

    # cluster → docket + terme (via fichier cases)
    cl2info = {}
    import gzip
    with gzip.open(CASES, "rt") as f:
        for line in f:
            c = json.loads(line)
            dk = clean_docket(c.get("docket_number"))
            for cid in c.get("cluster_ids", []):
                cl2info[cid] = (dk, int(c["term"]))

    # index : opinion_id → (cluster_id, docket)
    idx = {}
    for l in open(os.path.join(os.path.dirname(OUT), "index.jsonl")):
        r = json.loads(l)
        if r["opinion_id"]:
            idx[r["opinion_id"]] = (r["cluster_id"], r["docket"])

    # corpus = univers pré-enregistré gelé : un segment n'existe que si
    # son opinion source est DANS le corpus (les clusters 2025-26 vus par
    # le search sont hors univers) ET décidé avant OT2020 pour servir au
    # train (garde anti-fuite, la date réelle gouverne)
    import gzip
    OPINIONS = os.path.join(REPO, "data", "processed",
                            "corpus_opinions_v1.jsonl.gz")
    corpus_date = {}
    with gzip.open(OPINIONS, "rt") as f:
        for line in f:
            r = json.loads(line)
            corpus_date[r["opinion_id"]] = r.get("date_filed")

    seen, rows = set(), []
    for fn in sorted(glob.glob(os.path.join(DOCS_DIR, "*.*"))):
        if fn.endswith((".fail", ".tmp")):
            continue
        oid_s = os.path.splitext(os.path.basename(fn))[0]
        if not oid_s.isdigit():
            continue
        oid = int(oid_s)
        if oid not in corpus_date:
            continue                    # hors corpus gelé (clusters récents)
        meta = idx.get(oid)
        if not meta:
            continue
        cluster_id, docket = meta
        info = cl2info.get(cluster_id)
        term = info[1] if info else None
        raw = clean_text(extract_text(fn))
        if not raw:
            continue
        matches = list(HEAD_RE.finditer(raw))
        if len(matches) < 2:
            continue                        # doc mono-opinion : déjà servi
        # segments : de chaque signature à la suivante
        for i, m in enumerate(matches):
            last = m.group('name').lower()
            slug = last2slug.get(last)
            if not slug:
                continue
            lo, hi = SERVICE.get(slug, (1900, 2100))
            if term and not (lo <= term <= hi):
                continue                    # citation d'un juge ancien
            seg = raw[m.start():
                      matches[i + 1].start() if i + 1 < len(matches)
                      else len(raw)]
            if len(seg) < 2000:             # trop court pour entraîner
                continue
            h = hashlib.sha256(" ".join(seg.split())[:8000].encode()).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            rows.append({"slug": slug, "role": role_of(m.group("role"), m.group(0)),
                         "docket": docket, "term": term,
                         "source_opinion": oid,
                         "date_filed": corpus_date.get(oid),
                         "n_chars": len(seg),
                         "text": seg})

    with open(OUT + ".tmp", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(OUT + ".tmp", OUT)

    from collections import Counter
    print(f"{len(rows)} segments séparés uniques → {OUT}")
    print("par juge:", dict(Counter(r['slug'] for r in rows)))
    print("par rôle:", dict(Counter(r['role'] for r in rows)))
    train = [r for r in rows if r["term"] and r["term"] <= 2019]
    print(f"dans fenêtre train (≤OT2019): {len(train)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
