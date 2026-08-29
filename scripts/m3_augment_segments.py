#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legally Subjective — M3 augmentation : les segments PDF slip comme lignes
d'entraînement persona.

Pourquoi : le builder (m3_build_datasets.py) ne crée de lignes d'entraînement
que pour les opinions avec author_id NON NUL — or 1088/1778 opinions du
corpus (ère Harvard-XML : 'lead'/'dissent'/'concurrence') n'ont pas
d'author_id. Les segments extraits des PDFs slip de supremecourt.gov
(scripts/m15_slip_fetch.py) portent la JUSTICE lue dans l'en-tête du texte
(« JUSTICE THOMAS, dissenting ») : c'est l'attribution qui manquait.

La loi no-leak s'applique AUX SEGMENTS comme aux opinions :
  * fenêtre train stricte (term ≤ 2019) ;
  * les cinquante scellées exclues (mêmes règles que le builder, importées
    du builder lui-même — aucune divergence possible) ;
  * dockets hors fenêtre de service exclus (règle outlawed du builder) ;
  * vraies opinions seulement (≥ 3 000 signes), pas de per curiam anonyme.

Dédoublonnage : un segment n'entre pas si le persona a déjà une ligne pour
la même affaire et la même famille de type (lead/combined ≈ lead ;
dissent ; concurrence).

Usage : python3 scripts/m3_augment_segments.py   (après m3_build_datasets)
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import m3_build_datasets as B                     # noqa: E402
from m3_build_datasets import (PERSONA_SYSTEM, CASEFILE_INSTRUCTION,  # noqa: E402
                               TRAIN_END, LA_CHAMBRE, M3)

SEGMENTS = os.path.join(REPO, "data", "raw", "opinion_texts",
                        "slip_found.jsonl")

ROLE_FAM = {
    "lead": {"lead", "combined", "per-curiam"},
    "dissent": {"dissent"},
    "concurrence": {"concurrence"},
    "concurrence-dissent": {"in-part-opinion"},
}


def norm_docket(s):
    s = re.sub(r"^No\.?\s*", "", (s or "").strip())
    return s.replace("–", "-").replace("—", "-").rstrip(".").strip().lower()


def main():
    if not os.path.exists(SEGMENTS):
        print("aucun segment — relancer m15_slip_fetch.py extract")
        return
    cases, opinions, stats, amap = B.load_corpus()
    is_sealed = B.sealed_dockets(stats)
    outlawed = set()
    for ev in amap["mapping"].values():
        outlawed.update(ev.get("dockets_outside_service_window") or [])

    case_by_dn = {}
    for c in cases:
        case_by_dn[norm_docket(c.get("docket_number"))] = c

    slug_of_last = {}
    for aid, v in amap["mapping"].items():
        slug_of_last[v["last_name"].lower()] = v["slug"]

    # garde-fou anti-fausse-attribution : les votants Oyez de l affaire.
    # Un segment dont la « justice » n a pas siégé dans l affaire est un
    # artefact de segmentation (ex : syllabus attribué à Jackson dans
    # Lozman 17-21 — testé et rejeté ici).
    import glob
    oyez_members = {}
    for path in glob.glob(os.path.join(REPO, "data", "sources", "oyez",
                                       "*.json")):
        if path.endswith(".miss.json"):
            continue
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        dk = norm_docket(d.get("docket_number") or "")
        if not dk:
            continue
        members = set()
        for dec in d.get("decisions") or []:
            for v in dec.get("votes") or []:
                ln = (v.get("member") or {}).get("last_name")
                if ln:
                    members.add(ln.lower())
        if members:
            oyez_members[dk] = members

    segments = []
    for line in open(SEGMENTS, encoding="utf-8"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("role") == "full-pdf" or not r.get("plain_text"):
            continue
        j = (r.get("justice") or "").strip().lower()
        if j in ("per_curiam", "(pdf-validé)", "", "?"):
            continue
        if len(r["plain_text"]) < 3000:
            continue
        segments.append(r)

    manifest = json.load(open(os.path.join(M3, "manifest.json"),
                              encoding="utf-8"))
    n_added = 0
    for slug in LA_CHAMBRE:
        pdir = os.path.join(M3, "personas", slug)
        train_path = os.path.join(pdir, "train.jsonl")
        rows = [json.loads(l) for l in open(train_path, encoding="utf-8")] \
            if os.path.exists(train_path) else []
        have = {(norm_docket(r.get("docket")))
                for r in rows}
        have_fam = {(norm_docket(r.get("docket")), r.get("type"))
                    for r in rows}
        name = manifest["personas"].get(slug, {}).get("name", slug)
        added = 0
        for seg in segments:
            if slug_of_last.get(seg["justice"].lower()) != slug:
                continue
            dn = norm_docket(seg["case_docket"])
            c = case_by_dn.get(dn)
            if not c or is_sealed(c) or dn in outlawed:
                continue
            members = oyez_members.get(dn)
            if members and seg["justice"].lower() not in members:
                continue          # artefact de segmentation
            term = int(c["term"])
            if term > TRAIN_END:
                continue
            fam = ROLE_FAM.get(seg["role"], set())
            if any(hf[0] == dn and hf[1] in fam for hf in have_fam):
                continue
            row = {
                "opinion_id": seg.get("opinion_id"),
                "docket": c["docket_number"],
                "type": seg["role"],
                "date_filed": seg.get("term"),
                "system": PERSONA_SYSTEM.format(name=name),
                "instruction": CASEFILE_INSTRUCTION.format(
                    title=c.get("case_name"), docket=dn, term=term,
                    lower="record below",
                    parties=c.get("case_name"),
                    question="record below",
                    facts="record below",
                    posture="record below"),
                "output": seg["plain_text"][:120000],
                "source": "supremecourt.gov slip PDF (segment lié par juge)",
            }
            rows.append(row)
            have_fam.add((dn, seg["role"]))
            added += 1
        with open(train_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        if slug in manifest.get("personas", {}):
            manifest["personas"][slug]["train_text_rows"] = len(rows)
            manifest["personas"][slug]["slip_segment_rows"] = added
        n_added += added
        print(f"  {slug:12s} : +{added:3d} segments → {len(rows)} lignes train")

    manifest.setdefault("opinion_texts", {})
    manifest["opinion_texts"]["segment_channel"] = {
        "added": n_added,
        "note": "segments PDF slip liés par en-tête de juge (voie C)",
    }
    with open(os.path.join(M3, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(f"AUGMENT : +{n_added} lignes d entraînement persona au total")


if __name__ == "__main__":
    main()
