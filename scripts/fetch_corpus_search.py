#!/usr/bin/env python3
"""
Legally Subjective — collecte du corpus par l'API de recherche CourtListener
(accès anonyme, lenteur maîtrisée, reprise sur état).

Pour chaque docket plaidé de la fenêtre (issu du bulk dockets), interroge
/search/?court=scotus&type=o&q="<docket>" et conserve TOUTES les grappes
(clusters) dont le docketNumber correspond exactement (en jetons).

Sortie : data/raw/corpus_search_results.jsonl.gz (une ligne par cluster)
État : data/raw/_segment_work/search_corpus.state.json
"""
import gzip
import json
import os
import re
import time
import urllib.parse
import urllib.request

ROOT = "/home/z/my-project/legally-subjective"
RAW = os.path.join(ROOT, "data", "raw")
WORK = os.path.join(ROOT, "data", "raw", "_segment_work")
OUT = os.path.join(RAW, "corpus_search_results.jsonl.gz")
BASE = "https://www.courtlistener.com/api/rest/v4/search/"
UA = {"User-Agent": "legally-subjective/0.1 (research; corpus collection)"}
PACE = 0.75
WIN_START, WIN_END = "2015-10-01", "2024-06-30"


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def norm_docket(d):
    if not d:
        return set()
    d = re.sub(r"^no\.?\s+", "", d.strip().rstrip("."), flags=re.I)
    return {t.upper() for t in re.split(r"[^0-9A-Za-z]+", d) if t}


def docket_tokens_match(target, field):
    """Strict : TOUS les jetons du docket cible doivent être présents dans le champ."""
    tt = norm_docket(target)
    ft = norm_docket(field)
    return bool(tt) and tt.issubset(ft)


def search(docket, page=1):
    q = urllib.parse.quote(f'"{docket}"')
    url = f"{BASE}?court=scotus&type=o&q={q}&page_size=20&page={page}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    os.makedirs(WORK, exist_ok=True)

    # 1. dockets plaidés de la fenêtre
    window = []
    with gzip.open(os.path.join(RAW, "scotus_dockets.jsonl.gz"), "rt") as f:
        for line in f:
            r = json.loads(line)
            da = r.get("date_argued")
            if da and WIN_START <= da <= WIN_END:
                window.append({"docket_number": (r.get("docket_number") or "").strip(),
                               "docket_id": r["id"], "date_argued": da,
                               "case_name": r.get("case_name", "")})
    window.sort(key=lambda x: (x["date_argued"], x["docket_number"]))
    log(f"{len(window)} dockets plaidés à interroger")

    # 2. état
    state_path = os.path.join(WORK, "search_corpus.state.json")
    done = set()
    if os.path.exists(state_path):
        done = set(json.load(open(state_path))["done"])

    # 3. boucle avec reprise
    fout = gzip.open(OUT, "at", encoding="utf-8") if os.path.exists(OUT) else \
        gzip.open(OUT, "wt", encoding="utf-8")
    n_new = 0
    clusters_total = 0
    t0 = time.time()
    try:
        for i, w in enumerate(window):
            dk = w["docket_number"]
            if dk in done:
                continue
            if time.time() - t0 > 420:  # marge avant la fin de l'appel d'outil
                log(f"budget écoulé — {len(done)}/{len(window)} dockets faits")
                break
            clusters = []
            try:
                d = search(dk)
                for r in d.get("results", []):
                    if docket_tokens_match(dk, r.get("docketNumber", "")):
                        clusters.append(r)
                # deuxième page si la première est pleine de faux positifs
                if len(d.get("results", [])) == 20:
                    time.sleep(PACE)
                    d2 = search(dk, page=2)
                    for r in d2.get("results", []):
                        if docket_tokens_match(dk, r.get("docketNumber", "")):
                            clusters.append(r)
            except Exception as e:  # noqa: BLE001
                log(f"ERREUR docket {dk} : {e} — nouvelle tentative plus tard")
                time.sleep(3)
                continue
            # déduplication par cluster_id
            seen = set()
            uniq = []
            for c in clusters:
                if c.get("cluster_id") not in seen:
                    seen.add(c.get("cluster_id"))
                    uniq.append(c)
            for c in uniq:
                rec = {"query_docket": dk, "docket_id_argued": w["docket_id"],
                       "date_argued": w["date_argued"], "docket_case_name": w["case_name"],
                       "cluster": c}
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                clusters_total += 1
            n_new += 1
            done.add(dk)
            with open(state_path + ".tmp", "w") as fs:
                json.dump({"done": sorted(done)}, fs)
            os.replace(state_path + ".tmp", state_path)
            if n_new % 25 == 0:
                el = time.time() - t0
                log(f"{len(done)}/{len(window)} dockets | {clusters_total} grappes | "
                    f"{el:.0f}s | {el/max(n_new,1):.1f}s/docket")
            time.sleep(PACE)
    finally:
        fout.close()
    log(f"terminé pour cet appel : {n_new} nouveaux dockets, {clusters_total} grappes ; "
        f"total {len(done)}/{len(window)}")


if __name__ == "__main__":
    main()
