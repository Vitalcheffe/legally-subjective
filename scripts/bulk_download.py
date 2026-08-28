#!/usr/bin/env python3
"""Téléchargeur résumable par plages parallèles : sauve le fichier bulk compressé
sur disque. Reprenable d'un appel d'outil à l'autre (état dans .ranges.json)."""
import argparse
import concurrent.futures as cf
import json
import os
import sys
import time
import urllib.request

BASE_S3 = "https://com-courtlistener-storage.s3.amazonaws.com/bulk-data"
BULK = "/home/z/my-project/legally-subjective/data/raw/_bulk"
RANGE_MB = 16
WORKERS = 10

os.makedirs(BULK, exist_ok=True)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def head_size(url):
    req = urllib.request.Request(url, method="HEAD",
                                 headers={"User-Agent": "legally-subjective/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers["Content-Length"])


def fetch_range(url, start, end, out_path):
    req = urllib.request.Request(url, headers={
        "User-Agent": "legally-subjective/0.1 (research)",
        "Range": f"bytes={start}-{end}"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = resp.read()
                if len(data) != end - start + 1:
                    raise RuntimeError(f"plage incomplète {len(data)} != {end-start+1}")
                with open(out_path, "r+b") as f:
                    f.seek(start)
                    f.write(data)
                return len(data)
        except Exception as e:  # noqa: BLE001
            if attempt == 4:
                raise
            time.sleep(2 * (attempt + 1))
    return 0


def download(fname, budget_s):
    url = f"{BASE_S3}/{fname}"
    out_path = os.path.join(BULK, fname)
    state_path = os.path.join(BULK, fname + ".ranges.json")

    total = head_size(url)
    if not os.path.exists(out_path) or os.path.getsize(out_path) != total:
        with open(out_path, "wb") as f:
            f.truncate(total)
        done = []
    else:
        done = json.load(open(state_path))["done"] if os.path.exists(state_path) else []

    done_set = set(done)
    ranges = [(s, min(s + RANGE_MB * 1024 * 1024, total) - 1)
              for s in range(0, total, RANGE_MB * 1024 * 1024)]
    todo = [(s, e) for s, e in ranges if s not in done_set]
    log(f"{fname} : {total/1e9:.2f} Go | {len(ranges)} plages | restantes: {len(todo)}")

    t0 = time.time()
    downloaded = 0
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(fetch_range, url, s, e, out_path): s for s, e in todo}
        for fut in cf.as_completed(futs):
            start = futs[fut]
            n = fut.result()
            downloaded += n
            done.append(start)
            with open(state_path + ".tmp", "w") as f:
                json.dump({"done": done}, f)
            os.replace(state_path + ".tmp", state_path)
            el = time.time() - t0
            if int(el) % 30 < 1:
                log(f"  {downloaded/1e9:.2f} Go téléchargés | {len(done)}/{len(ranges)} plages | "
                    f"{downloaded/1e6/max(el,1):.0f} Mo/s")
            if time.time() - t0 > budget_s:
                log(f"  budget écoulé — {len(done)}/{len(ranges)} plages faites (reprendre au prochain appel)")
                for f2 in futs:
                    f2.cancel()
                break

    if len(done) >= len(ranges):
        log(f"TERMINÉ : {fname} complet ({total/1e9:.2f} Go)")
        os.remove(state_path)
        return True
    return False


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("fname")
    ap.add_argument("--budget", type=int, default=480, help="secondes max")
    a = ap.parse_args()
    ok = download(a.fname, a.budget)
    sys.exit(0 if ok else 1)
