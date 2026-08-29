#!/usr/bin/env python3
"""
Legally Subjective — veilleur M1.5.

Attend la libération du quota du token CourtListener (HTTP 429 → Retry-After),
lance scripts/fetch_opinion_texts.py (résumable) jusqu'à complétion, construit
le manifeste SHA-256 des textes d'opinions, puis commit + push (règle du
projet : un commit à chaque unité de travail — le veilleur s'en charge seul).

Conçu pour tourner détaché (nohup/setsid). Journal : tout sur stdout/stderr,
redirigé vers data/raw/opinion_texts/watcher.log par l'appelant.

Usage :  python3 scripts/m15_watcher.py            # boucle complète
         python3 scripts/m15_watcher.py --status   # état sans rien lancer
         python3 scripts/m15_watcher.py --finalize # manifeste + commit, si collecte complète

Note : dans un environnement qui tue les processus d'arrière-plan (sandbox),
lancer plutôt fetch_opinion_texts.py en passes de --budget 500 (~8 min,
résumable sur state.json), puis --finalize.
"""
import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = "/home/z/my-project/legally-subjective"
REPO = os.path.join(ROOT, "repo")
OPINIONS = os.path.join(ROOT, "data", "processed", "corpus_opinions_v1.jsonl.gz")
OUT_DIR = os.path.join(ROOT, "data", "raw", "opinion_texts")
STATE = os.path.join(OUT_DIR, "state.json")
OUT = os.path.join(OUT_DIR, "opinions_text.jsonl")       # drip (texte brut)
OUT_GZ = os.path.join(OUT_DIR, "opinions_text.jsonl.gz")  # batch (gzip propre)
MANIFEST = os.path.join(REPO, "data", "processed", "opinion_texts_manifest.json")
FETCH = os.path.join(REPO, "scripts", "fetch_opinion_texts.py")
FETCH_BATCH = os.path.join(REPO, "scripts", "fetch_opinion_texts_batch.py")
PROBE_URL = "https://www.courtlistener.com/api/rest/v4/opinions/?page_size=1"

MAX_WALL = 20 * 3600      # abandon au bout de 20 h
POLL_S = 300               # sonde du token toutes les 5 min
BUDGET_PER_RUN = 3600      # secondes de collecte par tentative (>= 1 800 opinions)


def log(m):
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {m}", flush=True)


def load_token():
    with open(os.path.join(ROOT, ".env")) as f:
        for line in f:
            if line.startswith("COURTLISTENER_TOKEN="):
                return line.strip().split("=", 1)[1]
    raise SystemExit("COURTLISTENER_TOKEN manquant dans .env")


def probe(tok):
    """Retourne (status, retry_after)."""
    req = urllib.request.Request(
        PROBE_URL,
        headers={"Authorization": f"Token {tok}",
                 "User-Agent": "legally-subjective/0.1 (research)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, 0
    except urllib.error.HTTPError as e:
        return e.code, int(e.headers.get("Retry-After", "300"))
    except Exception as e:  # réseau, DNS…
        return -1, POLL_S


def expected_ids():
    ids = set()
    with gzip.open(OPINIONS, "rt", encoding="utf-8") as f:
        for line in f:
            oid = json.loads(line).get("opinion_id")
            if oid:
                ids.add(oid)
    return ids


def done_ids():
    if not os.path.exists(STATE):
        return set()
    try:
        st = json.load(open(STATE))
        # les ids 404 (missing) comptent comme résolus : ils n'existent plus
        # côté API et le drip ne les acquerrait jamais
        return set(st["done"]) | set(st.get("missing", []))
    except Exception:
        return set()


def build_manifest(exp):
    """Empreinte du fichier produit + statistiques de complétion.
    Lecture ROBUSTE (leçon du 2026-08-29 : des appends gzip interrompus ont
    déjà corrompu le fichier — on relit via le lecteur qui sauve tout)."""
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import fetch_opinion_texts_batch as fb
    records = fb.load_all_records()
    h_records = hashlib.sha256()
    n = 0
    n_text = 0
    for oid in sorted(records):
        line = json.dumps(records[oid], ensure_ascii=False) + "\n"
        h_records.update(line.encode("utf-8"))
        n += 1
        if records[oid].get("plain_text") or records[oid].get("html"):
            n_text += 1
    # empreinte du/des fichiers bruts sur disque
    h_file = hashlib.sha256()
    for path in (OUT, OUT_GZ):
        if os.path.exists(path):
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h_file.update(chunk)
    man = {
        "file": "data/raw/opinion_texts/opinions_text.jsonl[.gz] (hors git, volume)",
        "purpose": "M1.5 — textes d'opinions du Corpus-Monde v1 (l'identité du corpus ne change pas)",
        "n_records": n,
        "n_with_text": n_text,
        "n_expected_ids": len(exp),
        "complete": done_ids() >= exp,
        "sha256_records": h_records.hexdigest(),
        "sha256_files": h_file.hexdigest(),
        "bytes": sum(os.path.getsize(p) for p in (OUT, OUT_GZ)
                     if os.path.exists(p)),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "CourtListener API v4 /opinions/ (token ; lots id__in via "
                  "fetch_opinion_texts_batch.py, repli détail 1 req/opinion)",
    }
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return man


def anti_leak_ok():
    """Aucun secret ne doit apparaître dans l'arbre commité."""
    secrets = []
    with open(os.path.join(ROOT, ".env")) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                v = line.strip().split("=", 1)[1]
                if v:
                    secrets.append(v)
    bad = []
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", ".next", "out")]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "rb") as f:
                    blob = f.read()
            except OSError:
                continue
            for s in secrets:
                if s.encode() in blob:
                    bad.append(p)
    return (not bad), bad


def commit_push():
    ok, bad = anti_leak_ok()
    if not ok:
        log(f"FUITE DE SECRET DÉTECTÉE — commit annulé : {bad}")
        return False
    env = ["git", "-C", REPO, "-c", "user.name=Vitalcheffe",
           "-c", "user.email=Vitalcheffe@users.noreply.github.com"]
    subprocess.run(env + ["add", "data/processed/opinion_texts_manifest.json"], check=False)
    r = subprocess.run(env + ["commit", "-m",
        "m1.5: textes d'opinions collectés — manifeste SHA-256\n\n"
        "1 778 textes d'opinions via l'API authentifiée CourtListener v4\n"
        "(collecte automatique par scripts/m15_watcher.py). L'identité du\n"
        "corpus gelé v1 ne change pas ; la déduplication fine suit en M1.5."],
        check=False, capture_output=True, text=True)
    if r.returncode != 0:
        log(f"commit: {r.stdout.strip()} {r.stderr.strip()}")
        return False
    subprocess.run(env + ["pull", "--rebase", "origin", "main"],
                   check=False, capture_output=True, text=True)
    r = subprocess.run(env + ["push", "origin", "main"],
                       check=False, capture_output=True, text=True)
    if r.returncode != 0:
        log(f"push échoué (commit local conservé) : {r.stderr.strip()[:300]}")
        return False
    log("manifeste commité et poussé")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--finalize", action="store_true",
                    help="manifeste + commit + push, si la collecte est complète")
    args = ap.parse_args()

    exp = expected_ids()
    done = done_ids()
    log(f"attendus : {len(exp)} opinions ; déjà faites : {len(done)}")

    if args.status:
        tok = load_token()
        st, ra = probe(tok)
        log(f"sonde token : HTTP {st}" + (f", Retry-After {ra}s" if st == 429 else ""))
        return

    if args.finalize:
        if done < exp:
            log(f"finalize refusé : {len(exp) - len(done)} opinions manquantes")
            return
        man = build_manifest(exp)
        log(f"manifeste : {man['n_records']} enregistrements "
            f"({man['n_with_plain_text']} avec texte), gz = {man['sha256_gz_file'][:16]}…")
        commit_push()
        log("M1.5 (collecte) : TERMINÉ")
        return

    t0 = time.time()
    while time.time() - t0 < MAX_WALL:
        if done_ids() >= exp:
            break
        tok = load_token()
        st, ra = probe(tok)
        if st == 200:
            remaining = len(exp) - len(done_ids())
            log(f"token libéré — collecte ({remaining} restantes)")
            # le batch (lots id__in) est la voie rapide : 125 req/jour comptent
            # des REQUÊTES, pas des opinions. S'il échoue (exit 2 : filtre ou
            # liste sans texte), repli sur le drip 1 req/opinion.
            r = subprocess.run([sys.executable, FETCH_BATCH], check=False)
            if r.returncode == 2:
                log("batch indisponible — repli drip (1 req/opinion)")
                subprocess.run([sys.executable, FETCH, "--budget", str(BUDGET_PER_RUN)],
                               check=False)
            log(f"fin de passe : {len(done_ids())}/{len(exp)}")
        elif st == 429:
            wait = min(ra + 60, 3600)
            log(f"429 — Retry-After {ra}s ; sommeil {wait}s")
            time.sleep(wait)
            continue
        else:
            log(f"sonde : HTTP {st} ; nouvel essai dans {POLL_S}s")
            time.sleep(POLL_S)
            continue
        time.sleep(30)  # entre deux passes de collecte

    done = done_ids()
    if done < exp:
        log(f"ABANDON : {len(exp) - len(done)} opinions manquantes après "
            f"{(time.time() - t0) / 3600:.1f} h — relancer plus tard")
        return

    man = build_manifest(exp)
    log(f"manifeste : {man['n_records']} enregistrements "
        f"({man['n_with_plain_text']} avec texte), gz = {man['sha256_gz_file'][:16]}…")
    commit_push()
    log("M1.5 (collecte) : TERMINÉ")


if __name__ == "__main__":
    main()
