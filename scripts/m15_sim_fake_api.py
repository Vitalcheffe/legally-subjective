#!/usr/bin/env python3
"""Simulation: fabrique des réponses API v4 réalistes pour valider le merge
AVANT d'ouvrir la fenêtre de quota réelle. Cas couverts :
  A. plain_text natif         (voie royale)
  B. html seul                (strip requis)
  C. xml_harvard seul         (strip XML)
  D. tous champs textes vides (retomber sur le store legacy)
  E. id hors corpus           (doit être ignoré)
  F. legacy + API texte       (priorité API)
Écrit dans /tmp/simrepo/data/m15_store/api/.
"""
import gzip
import json
import os

SIM = "/tmp/simrepo"
API_DIR = os.path.join(SIM, "data", "m15_store", "api")
CORPUS = os.path.join(SIM, "data", "processed", "corpus_opinions_v1.jsonl.gz")
os.makedirs(API_DIR, exist_ok=True)

# charger le corpus pour choisir de vrais ids
recs = {}
with gzip.open(CORPUS, "rt") as f:
    for line in f:
        r = json.loads(line)
        recs[r["opinion_id"]] = r

# ids legacy avec texte (pour D et F)
legacy_with_text = set()
with gzip.open(os.path.join(SIM, "data", "raw", "opinion_texts",
                            "opinions_text.jsonl.gz"), "rt") as f:
    for line in f:
        legacy_with_text.add(json.loads(line).get("opinion_id")
                             or json.loads(line).get("id"))

ids = sorted(recs)
id_A1, id_A2 = ids[0], ids[1]
id_B, id_C = ids[2], ids[3]
id_D = next(i for i in ids if i in legacy_with_text)          # API vide + legacy
id_F = next(i for i in ids if i in legacy_with_text and i != id_D)
id_E = 999999999                                              # hors corpus


def rec(oid, **text):
    r = {"resource_uri": f"https://www.courtlistener.com/api/rest/v4/opinions/{oid}/",
         "id": oid, "cluster_id": recs.get(oid, {}).get("cluster_id", 1),
         "author": recs.get(oid, {}).get("author_id"),
         "per_curiam": recs.get(oid, {}).get("per_curiam", False),
         "sha1": recs.get(oid, {}).get("sha1", "0" * 40),
         "page_count": 12, "download_url": "", "local_path": "",
         "extracted_by_ocr": False, "created_by": 1,
         "date_modified": "2026-01-01T00:00:00Z"}
    for k in ("plain_text", "html", "xml_harvard", "html_lawbox",
              "html_columbia", "html_anonymous_2020"):
        r[k] = text.get(k, "")
    return r


records = [
    rec(id_A1, plain_text="OPINION OF THE COURT (simulation A1).\n"
                          "We granted certiorari to resolve a narrow question."),
    rec(id_A2, plain_text="SIMULATION A2. " + "The judgment below is affirmed. " * 30),
    rec(id_B, html="<html><head><style>body{font:12px}</style></head><body>"
                   "<p>SIMULATION B, paragraphe un.</p>"
                   "<p>Paragraphe deux avec <em>mise en italique</em>.</p>"
                   "<script>alert('x')</script></body></html>"),
    rec(id_C, xml_harvard='<?xml version="1.0" encoding="utf-8"?><opinion>'
                           '<p>SIMULATION C, texte Harvard XML.</p>'
                           '<p>Deuxième &lt;paragraphe&gt; avec entités.</p></opinion>'),
    rec(id_D),                                     # aucun texte côté API
    rec(id_E, plain_text="SIMULATION E — id hors corpus, ne doit jamais ressortir."),
    rec(id_F, plain_text="SIMULATION F (API doit gagner sur le legacy)."),
]
with open(os.path.join(API_DIR, "resp_0000.json"), "w") as f:
    json.dump({"requested": [r["id"] for r in records], "count": len(records),
               "records": records}, f)

print(f"7 enregistrements simulés → {API_DIR}/resp_0000.json")
print(f"  A plain_text : {id_A1}, {id_A2}")
print(f"  B html seul  : {id_B}")
print(f"  C xml seul   : {id_C}")
print(f"  D vide+legac : {id_D} (legacy={id_D in legacy_with_text})")
print(f"  E hors corpus: {id_E}")
print(f"  F API>legacy : {id_F} (legacy={id_F in legacy_with_text})")
