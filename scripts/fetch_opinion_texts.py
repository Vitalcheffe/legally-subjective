#!/usr/bin/env python3
"""
Legally Subjective — collecte des TEXTES d'opinions via l'API authentifiée
CourtListener (v4). À exécuter APRÈS le gel du corpus (M1) ; nécessite le token
dans .env (COURTLISTENER_TOKEN) — jamais commité.

Pour chaque opinion unique de corpus_opinions_v1.jsonl.gz (~1 800), récupère :
  GET /api/rest/v4/opinions/{id}/  ->  plain_text (ou html en repli)

Lenteur maîtrisée (1 requête/s + reprise sur état) ; sorties :
  data/raw/opinion_texts/opinions_text.jsonl.gz

Usage :  python3 fetch_opinion_texts.py [--budget 500] [--page-check]
         python3 fetch_opinion_texts.py --budget 540 --wait-on-429
                 (mode quota : le token gratuit est limité — 5 req/min ET un
                 quota glissé à l'heure ; le script dort le Retry-After et
                 continue au lieu de s'arrêter)
         python3 fetch_opinion_texts.py --pace 75 --budget 3600
                 (pacing proactif : une requête toutes les 75 s, débit optimal
                 sous le quota horaire sans jamais payer un 429)
"""
import argparse
import gzip
import json
import os
import time
import urllib.error
import urllib.request

ROOT = "/home/z/my-project/legally-subjective"
OPINIONS = os.path.join(ROOT, "data", "processed", "corpus_opinions_v1.jsonl.gz")
OUT_DIR = os.path.join(ROOT, "data", "raw", "opinion_texts")
OUT = os.path.join(OUT_DIR, "opinions_text.jsonl.gz")
STATE = os.path.join(OUT_DIR, "state.json")
BASE = "https://www.courtlistener.com/api/rest/v4/opinions/"


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def load_token():
    env = os.path.join(ROOT, ".env")
    if os.path.exists(env):
        for line in open(env):
            line = line.strip()
            if line.startswith("COURTLISTENER_TOKEN="):
                return line.split("=", 1)[1]
    return os.environ.get("COURTLISTENER_TOKEN", "")


def fetch(op_id, token):
    req = urllib.request.Request(BASE + str(op_id) + "/", headers={
        "Authorization": f"Token {token}",
        "User-Agent": "legally-subjective/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    token = load_token()
    if not token:
        raise SystemExit("COURTLISTENER_TOKEN manquant (.env)")
    os.makedirs(OUT_DIR, exist_ok=True)

    # opinion ids à récupérer
    ids = []
    with gzip.open(OPINIONS, "rt", encoding="utf-8") as f:
        for line in f:
            oid = json.loads(line).get("opinion_id")
            if oid:
                ids.append(oid)
    ids = sorted(set(ids))
    log(f"{len(ids)} opinions à récupérer")

    done = set()
    if os.path.exists(STATE):
        done = set(json.load(open(STATE))["done"])

    mode = "at" if os.path.exists(OUT) else "wt"
    n = 0
    t0 = time.time()
    with gzip.open(OUT, mode, encoding="utf-8") as fout:
        for oid in ids:
            if oid in done:
                continue
            if time.time() - t0 > args.budget:
                log(f"budget écoulé — {len(done)}/{len(ids)} opinions faites")
                break
            try:
                d = fetch(oid, token)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    ra = int(e.headers.get("Retry-After", "60"))
                    if args.wait_on_429:
                        log(f"429 — Retry-After {ra}s ; attente et poursuite (mode quota)")
                        time.sleep(ra + 1)
                        try:
                            d = fetch(oid, token)
                        except urllib.error.HTTPError as e2:
                            if e2.code == 429:
                                log(f"429 persistant après attente — arrêt propre")
                                break
                            raise
                    else:
                        log(f"429 — Retry-After {ra}s ; arrêt propre de cet appel")
                        break
                else:
                    log(f"opinion {oid} : HTTP {e.code}")
                    time.sleep(1)
                    continue
            rec = {
                "opinion_id": oid,
                "plain_text": d.get("plain_text") or "",
                "html": (d.get("html") or "")[:500000] if not d.get("plain_text") else "",
                "sha1": d.get("sha1"), "type": d.get("type"),
                "author_id": d.get("author_id"), "cluster_id": d.get("cluster_id"),
                "per_curiam": d.get("per_curiam"), "page_count": d.get("page_count"),
                "download_url": d.get("download_url"),
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
            done.add(oid)
            with open(STATE + ".tmp", "w") as fs:
                json.dump({"done": sorted(done)}, fs)
            os.replace(STATE + ".tmp", STATE)
            if n % 25 == 0:
                log(f"{len(done)}/{len(ids)} | {time.time()-t0:.0f}s")
            time.sleep(max(args.pace, 1.0))
    log(f"fin d'appel : +{n} opinions (total {len(done)}/{len(ids)})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=500)
    ap.add_argument("--wait-on-429", action="store_true",
                    help="dormir le Retry-After et poursuivre (token gratuit limité à 5 req/min)")
    ap.add_argument("--pace", type=float, default=1.0,
                    help="secondes entre requêtes (75 = débit optimal sous le quota horaire du token gratuit)")
    args = ap.parse_args()
    main()
