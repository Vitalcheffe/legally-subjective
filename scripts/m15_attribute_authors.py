#!/usr/bin/env python3
"""M1.5 attribution d'auteurs par le texte lui-même.

Les 690/1778 author_id du corpus (métadonnées CL) ne couvrent que 39 % des
opinions ; l'index search est aussi pauvre. Mais chaque texte d'opinion
SIGNE son auteur dans ses premières lignes (« JUSTICE THOMAS, delivered... »).
Ce script lit la signature, la valide contre les 690 author_id connus
(précision mesurée, publiée), et produit un fichier d'attribution latéral
— le corpus gelé n'est PAS modifié.

Sortie : data/m15_store/final/authorship.jsonl
  {opinion_id, slug, role, method: "text-signature",
   n_chars_scanned, validated_against_corpus: bool}
"""
import gzip
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS = os.path.join(REPO, "data", "m15_store", "final",
                     "opinion_texts_v2.jsonl.gz")
CORPUS = os.path.join(REPO, "data", "processed", "corpus_opinions_v1.jsonl.gz")
AMAP = os.path.join(REPO, "data", "m3", "author_map.json")
OUT = os.path.join(REPO, "data", "m15_store", "final", "authorship.jsonl")

HEAD_RE = re.compile(
    r"(?:^|\n)\s*(?:JUSTICE|Justice|CHIEF JUSTICE|Chief Justice)\s+"
    r"(?P<name>[A-Z][a-zA-Z]+)"
    r"(?P<filler>[^\n]{0,200}?)\s*(?:,?\s*(?P<role>deliver\w*|concurr\w*|dissent\w*|"
    r"with whom[^,.]*|announc\w*|filed a statement[^,.]*|"
    r"concurring in the judgment[^,.]*)"
    r"[^.]{0,180}\.)",
    re.M)
PER_CURIAM_RE = re.compile(
    r"(?:^|\n)\s*Per Curiam\b.{0,80}?\n", re.M | re.I)
# format slip officiel : « JACKSON, J., delivered the opinion for a
# unanimous Court... » / « ROBERTS, C. J., delivered... » / « THOMAS, J.,
# dissenting. » — le Chief Justice s'écrit « C. J. » avec espaces/points
NAME_J_RE = re.compile(
    r"(?:^|\n)\s*(?P<name>[A-Z][a-zA-Z]+),\s*(?:C\.\s?J\.|CJ\.|J\.)\s*,?\s*"
    r"(?P<role>deliver\w*|concurr\w*|dissent\w*|announc\w*|with whom[^,.]*)",
    re.M)
SCAN_WINDOW = 6000            # l'en-tête vit au début du texte

# garde biographique : un juge n'aute que pendant son service (termes OT).
# Évite les faux positifs du type « JACKSON, J., delivered » cité dans le
# corps d'un texte moderne (Robert H. Jackson, 1941-1954).
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
    last2slug = {}
    for aid_s, v in amap.items():
        last2slug[v["last_name"].lower()] = (v["slug"], int(aid_s))

    corpus = {}
    with gzip.open(CORPUS, "rt") as f:
        for line in f:
            r = json.loads(line)
            corpus[r["opinion_id"]] = r

    rows, n_ok, n_bad, n_none = [], 0, 0, 0
    validated = n_agree = n_disagree = 0
    for line in gzip.open(TEXTS, "rt"):
        t = json.loads(line)
        oid, text = t["opinion_id"], t.get("plain_text") or ""
        # motif A : « JUSTICE THOMAS, dissenting. » (début d'opinion)
        m = HEAD_RE.search(text[:SCAN_WINDOW])
        fmt = "justice-header"
        # motif B : « JACKSON, J., delivered the opinion… » (bloc slip,
        # après le syllabus — fenêtre élargie)
        m2 = NAME_J_RE.search(text[:15000])
        # A est prioritaire (signature dans le vif du texte), sinon B
        pick = m or m2
        if not pick:
            n_none += 1
            continue
        fmt = "justice-header" if m else "slip-name-j"
        last = pick.group("name").lower()
        hit = last2slug.get(last)
        if not hit:
            n_none += 1
            continue
        slug, aid = hit
        # garde de service : la signature doit être compatible avec le
        # terme de l'affaire (sinon c'est une citation d'un juge ancien)
        t_term = corpus.get(oid, {}).get("term")
        lo, hi = SERVICE.get(slug, (1900, 2100))
        if t_term and not (lo <= int(t_term) <= hi):
            n_none += 1
            continue
        per_curiam = bool(PER_CURIAM_RE.search(text[:1500]))
        row = {"opinion_id": oid, "slug": slug, "author_id": aid,
               "justice": pick.group("name"), "role": role_of(pick.group("role") or "", pick.group(0)),
               "method": fmt,
               "per_curiam": per_curiam,
               "corpus_author_id": corpus.get(oid, {}).get("author_id")}
        # validation sur les author_id connus
        c_aid = row["corpus_author_id"]
        if c_aid:
            validated += 1
            if c_aid == aid:
                row["agree"] = True
                n_agree += 1
            else:
                row["agree"] = False
                n_disagree += 1
        rows.append(row)
        n_ok += 1

    with open(OUT + ".tmp", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    os.replace(OUT + ".tmp", OUT)

    print(f"attribués par signature: {n_ok} | sans signature: {n_none}")
    if validated:
        print(f"validation contre corpus (author_id connus): "
              f"{n_agree}/{validated} d'accord "
              f"({100 * n_agree / validated:.1f} %) | {n_disagree} conflits")
        # répartition du gain
        new_attr = sum(1 for r in rows if not r["corpus_author_id"])
        print(f"nouvelles attributions (author_id corpus NULL): {new_attr}")
        from collections import Counter
        print("par juge (toutes):", dict(Counter(r["slug"] for r in rows)))
        print("par juge (nouvelles):",
              dict(Counter(r["slug"] for r in rows if not r["corpus_author_id"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
