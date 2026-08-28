#!/usr/bin/env python3
"""Collecte complémentaire : dockets SCDB plaidés absents de la collecte CL
(CourtListener n'a pas toujours la date de plaidoirie sur le bon docket
dupliqué). Interroge l'API de recherche pour ces numéros."""
import csv
import gzip
import json
import os
import re
import time
import urllib.parse
import urllib.request

ROOT = "/home/z/my-project/legally-subjective"
RAW = os.path.join(ROOT, "data", "raw")
SCDB = os.path.join(RAW, "scdb", "SCDB_2025_01_justiceCentered_Citation.csv")
OUT = os.path.join(RAW, "corpus_search_results.jsonl.gz")
BASE = "https://www.courtlistener.com/api/rest/v4/search/"
UA = {"User-Agent": "legally-subjective/0.1 (research; corpus collection)"}


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def norm_tokens(d):
    if not d:
        return frozenset()
    d = re.sub(r"^no\.?\s+", "", d.strip().rstrip("."), flags=re.I)
    d = re.sub(r"orig\.?$", "original", d, flags=re.I)
    d = re.sub(r"(\d+)O(\d+)", r"\1 \2 original", d)  # SCDB '22O141' -> '22 141 original'
    return frozenset(t.upper().replace("ORIG", "ORIGINAL") for t in re.split(r"[^0-9A-Za-z]+", d) if t)


def scdb_date(s):
    if not s:
        return None
    try:
        m, d, y = s.split("/")
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except ValueError:
        return None


def search(docket, page=1):
    q = urllib.parse.quote(f'"{docket}"')
    url = f"{BASE}?court=scotus&type=o&q={q}&page_size=20&page={page}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    # dockets déjà interrogés (état de la collecte principale)
    state = json.load(open(os.path.join(RAW, "_segment_work", "search_corpus.state.json")))
    already = set(state["done"])

    # CL dockets plaidés fenêtre (tous ids/numéros)
    cl_argued_tokens = set()
    with gzip.open(os.path.join(RAW, "scotus_dockets.jsonl.gz"), "rt") as f:
        for line in f:
            r = json.loads(line)
            da = r.get("date_argued")
            if da and "2015-10-01" <= da <= "2024-06-30":
                tk = norm_tokens(r.get("docket_number"))
                if tk:
                    cl_argued_tokens.add(tk)

    # SCDB plaidés fenêtre dont les jetons ne sont pas dans cl_argued_tokens
    todo = []
    seen_tokens = set()
    with open(SCDB, encoding="latin-1") as f:
        for row in csv.DictReader(f):
            if not row.get("dateArgument"):
                continue
            da = scdb_date(row["dateArgument"])
            if not (da and "2015-10-01" <= da <= "2024-06-30"):
                continue
            cid = row["caseId"]
            if cid in seen_tokens:
                continue
            seen_tokens.add(cid)
            for d in re.split(r"[;,]", row["docket"]):
                tk = norm_tokens(d)
                if tk and tk not in cl_argued_tokens and tk not in seen_tokens:
                    seen_tokens.add(tk)
                    # numéro brut SCDB pour la requête de recherche
                    todo.append({"docket_number": d.strip(), "tokens": tk,
                                 "scdb_case_id": cid, "scdb_name": row["caseName"][:50],
                                 "date_argued": da})
                    break
    log(f"{len(todo)} dockets SCDB à interroger en plus")

    # les originaux SCDB '22O141' : requête sur la partie numérique
    fixed_todo = []
    for t in todo:
        q = t["docket_number"]
        m = re.match(r"^(\d+)O(\d+)$", q)
        if m:
            q = f"{m.group(2)}, Original"
        t["search_query"] = q
        fixed_todo.append(t)

    n_clusters = 0
    with gzip.open(OUT, "at", encoding="utf-8") as fout:
        for t in fixed_todo:
            try:
                d = search(t["search_query"])
            except Exception as e:  # noqa: BLE001
                log(f"ERREUR {t['search_query']} : {e}")
                time.sleep(3)
                continue
            kept = []
            for r in d.get("results", []):
                if t["tokens"].issubset(norm_tokens(r.get("docketNumber", ""))):
                    kept.append(r)
            for c in kept:
                if not any(x.get("cluster_id") == c.get("cluster_id") for x in kept[:kept.index(c)]):
                    fout.write(json.dumps({
                        "query_docket": t["docket_number"],
                        "docket_id_argued": None,
                        "date_argued": t["date_argued"],
                        "docket_case_name": t["scdb_name"],
                        "cluster": c}, ensure_ascii=False) + "\n")
                    n_clusters += 1
            log(f"  {t['search_query']:>18} ({t['scdb_case_id']}) -> {len(kept)} grappes")
            time.sleep(0.75)
    log(f"TERMINÉ : {n_clusters} grappes supplémentaires")


if __name__ == "__main__":
    main()
