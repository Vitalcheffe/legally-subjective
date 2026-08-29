#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legally Subjective — M1.5 binding v2 : Oyez sait qui a écrit quoi.

Le problème : 340 segments de texte extraits des PDFs slip restent non liés
à un opinion_id, car 1088/1778 opinions du corpus n'ont pas d'author_id
(les 'lead'/'dissent'/'concurrence' de l'ère Harvard-XML).

La solution locale : data/sources/oyez/<docket>.json → decisions[].votes[] →
{member.last_name, vote, opinion_type} — Oyez enregistre QUI a délivré
l'opinion de la Cour et qui a écrit chaque concurrence/dissidence.

Stratégie de binding par affaire :
  1. auteurs connus : corpus author_id → last_name (author_map.json)
  2. auteurs Oyez   : opinion_type 'majority' → lead/combined/per-curiam ;
     'concurrence'/'special concurrence' → concurrence ; 'dissent' → dissent
  3. pour chaque segment (justice, rôle depuis l'en-tête du texte) :
     candidats = opinions non liées de l'affaire dont (type ↔ rôle) ET
     (auteur corpus == justice OU auteur Oyez == justice). Si un seul → lié.
  4. ramasse-miettes : 1 segment non lié + 1 opinion non liée → liés.
  5. ré-écriture du store (les records sha1-or ne sont JAMAIS écrasés).

Usage : python3 scripts/m15_bind.py
"""
import glob
import gzip
import json
import os
import re
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPINIONS = os.path.join(REPO, "data", "processed", "corpus_opinions_v1.jsonl.gz")
AUTHOR_MAP = os.path.join(REPO, "data", "m3", "author_map.json")
OYEZ = os.path.join(REPO, "data", "sources", "oyez")
OUT_DIR = os.path.join(REPO, "data", "raw", "opinion_texts")
MATCH = os.path.join(OUT_DIR, "slip_match.json")
FOUND = os.path.join(OUT_DIR, "slip_found.jsonl")
STORE = os.path.join(OUT_DIR, "opinions_text.jsonl.gz")

ROLE_FAM = {
    "lead": {"lead", "combined"},
    "dissent": {"dissent"},
    "concurrence": {"concurrence"},
    "concurrence-dissent": {"in-part-opinion"},
}
OYE2TYPE = {
    "majority": {"lead", "combined", "per-curiam"},
    "concurrence": {"concurrence"},
    "special concurrence": {"concurrence"},
    "dissent": {"dissent"},
    "dissent-in-part": {"in-part-opinion"},
}


def norm_docket(s):
    s = re.sub(r"^No\.?\s*", "", (s or "").strip())
    return s.replace("–", "-").replace("—", "-").rstrip(".").strip().lower()


def main():
    amap = json.load(open(AUTHOR_MAP))["mapping"]
    id2last = {int(k): v["last_name"] for k, v in amap.items()}

    # corpus opinions : oid → {type, author, cluster}
    ops = {}
    with gzip.open(OPINIONS, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            ops[r["opinion_id"]] = {
                "type": r.get("type"),
                "author": id2last.get(r.get("author_id"))
                if r.get("author_id") else None,
                "cluster": r.get("cluster_id"),
            }

    # Oyez : docket normalisé → {type-family → [last names]}
    oyez_writers = {}
    for path in glob.glob(os.path.join(OYEZ, "*.json")):
        if path.endswith(".miss.json"):
            continue
        try:
            d = json.load(open(path))
        except Exception:  # noqa: BLE001
            continue
        dk = norm_docket(d.get("docket_number") or "")
        if not dk:
            continue
        wr = {}
        for dec in d.get("decisions") or []:
            for v in dec.get("votes") or []:
                ot = (v.get("opinion_type") or "").strip().lower()
                last = (v.get("member") or {}).get("last_name")
                if not last or ot not in OYE2TYPE:
                    continue
                for t in OYE2TYPE[ot]:
                    wr.setdefault(t, set()).add(last)
        if wr:
            # convertit les sets en listes (json-friendly)
            oyez_writers[dk] = {k: sorted(v) for k, v in wr.items()}

    matched = json.load(open(MATCH))
    segs_by_case = {}
    for line in open(FOUND, encoding="utf-8"):
        r = json.loads(line)
        segs_by_case.setdefault(r["case_docket"], []).append(r)

    store = {}
    with gzip.open(STORE, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            store[r["opinion_id"]] = r
    # les sha1-or (role=full-pdf) ne se touchent pas
    gold = {r["opinion_id"] for r in store.values()
            if r.get("provenance", "").startswith("supremecourt") and
            r.get("sha1")}

    n_bound = 0
    new_records = []
    for m in matched:
        dk = norm_docket(m["docket_raw"])
        oyez = oyez_writers.get(dk, {})
        segs = [s for s in segs_by_case.get(m["docket_raw"], [])
                if s.get("opinion_id") is None and s.get("role") != "full-pdf"]
        unbound_ops = [oid for oid in m["opinion_ids"]
                       if oid not in store]
        if not segs or not unbound_ops:
            continue

        def author_candidates(oid):
            """auteurs possibles : corpus d'abord, Oyez en secours."""
            o = ops[oid]
            cands = set()
            if o["author"]:
                cands.add(o["author"].lower())
            for t in ROLE_FAM.values() if False else ():
                pass
            # Oyez : pour le type de l opinion, qui écrit ce genre ?
            fam = {o["type"]} if o["type"] else set()
            # lead/combined partagent la famille majority
            if o["type"] in ("lead", "combined", "per-curiam"):
                fam |= {"lead", "combined", "per-curiam"}
            for t in fam:
                for ln in oyez.get(t, []):
                    cands.add(ln.lower())
            return cands

        used_seg = set()
        for i, seg in enumerate(segs):
            justice = (seg.get("justice") or "").lower()
            role = seg.get("role")
            fam = ROLE_FAM.get(role, set())
            # 3) correspondance (rôle, auteur)
            best = None
            for oid in unbound_ops:
                if oid in store or oid in [r["opinion_id"] for r in new_records
                                           if r.get("opinion_id")]:
                    continue
                o = ops[oid]
                if o["type"] and o["type"] not in fam and role != "lead":
                    continue
                acs = author_candidates(oid)
                if justice in acs:
                    best = oid
                    break
            # rôle seul si un seul candidat de la famille
            if best is None:
                cands = [oid for oid in unbound_ops
                         if oid not in store and
                         oid not in [r["opinion_id"] for r in new_records
                                     if r.get("opinion_id")] and
                         (ops[oid]["type"] in fam if ops[oid]["type"] else True)]
                if len(cands) == 1:
                    best = cands[0]
            if best is not None:
                new_records.append({
                    "opinion_id": best,
                    "plain_text": seg["plain_text"],
                    "html": "",
                    "sha1": seg.get("pdf_sha1"),
                    "type": ops[best]["type"],
                    "author_id": None,
                    "cluster_id": ops[best]["cluster"],
                    "per_curiam": seg.get("lead_author_code") == "PC",
                    "page_count": None,
                    "download_url": seg.get("pdf_url"),
                    "author_str": seg.get("justice"),
                    "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                time.gmtime()),
                    "provenance": "supremecourt.gov slip PDF (oyez-bound)",
                })
                n_bound += 1
                used_seg.add(i)

        # 4) ramasse-miettes : 1 segment restant + 1 opinion restante
        rest_seg = [s for i, s in enumerate(segs) if i not in used_seg]
        rest_ops = [oid for oid in unbound_ops
                    if oid not in store and
                    oid not in [r["opinion_id"] for r in new_records
                                if r.get("opinion_id")]]
        if len(rest_seg) == 1 and len(rest_ops) == 1:
            seg = rest_seg[0]
            new_records.append({
                "opinion_id": rest_ops[0],
                "plain_text": seg["plain_text"],
                "html": "", "sha1": seg.get("pdf_sha1"),
                "type": ops[rest_ops[0]]["type"],
                "author_id": None, "cluster_id": ops[rest_ops[0]]["cluster"],
                "per_curiam": seg.get("lead_author_code") == "PC",
                "page_count": None, "download_url": seg.get("pdf_url"),
                "author_str": seg.get("justice"),
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime()),
                "provenance": "supremecourt.gov slip PDF (unique-bound)",
            })
            n_bound += 1

    for r in new_records:
        store[r["opinion_id"]] = r
    tmp = STORE + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        for oid in sorted(store):
            f.write(json.dumps(store[oid], ensure_ascii=False) + "\n")
    os.replace(tmp, STORE)
    print(f"BIND v2 : +{n_bound} opinions liées (Oyez/unique) → store "
          f"{len(store)}/1778")
    # segments encore non liés (pour info)
    n_unbound = sum(1 for dk, ss in segs_by_case.items()
                    for s in ss if s.get("opinion_id") is None
                    and s.get("role") != "full-pdf")
    print(f"segments restants non liés : {n_unbound}")


if __name__ == "__main__":
    main()
