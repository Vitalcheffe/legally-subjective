#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legally Subjective — M1.5 voie B, v3 : LE SCAN SEGMENTÉ REPRENABLE.

La vérité du terrain (mesurée, session 2, 2026-08-29) :
  1. Rien ne survit à un appel d'outil shell — le sandbox tue le groupe de
     processus à la fin de l'appel (même setsid). Le docstring de
     bulk_download.py le disait : « Reprenable d'un appel d'outil à
     l'autre ». C'est une CONTRAINTE STRUCTURANTE du poste.
  2. L'API CourtListener refuse l'anonymat (401), le site web met un
     bot-check (202), supremecourt.gov a tué ses vieilles URLs (404).
     Seul le bucket bulk S3 est ouvert, anonyme, en Range requests.
  3. S3 throttle à ~2,25 Mo/s PAR CONNEXION ; 8 connexions // = 18 Mo/s.
  4. bz2 décompresse à 30 Mo/s (le regex de scan ne coûte rien).
  5. Le bulk n'est trié par RIEN d'exploitable (ni id, ni date, ni
     local_path) : il faut TOUT scanner.

Le fichier bz2 est une suite de BLOCS indépendants (magic 48 bits
0x314159265359) alignés au BIT. Un segment peut donc démarrer sur
n'importe quelle frontière de bloc après RÉPARATION : on recalcule le flux
comme si un en-tête 'BZh9' précédait le bloc (décalage de bits par
arithmétique entière, VALIDÉ empiriquement : le flux réparé décompresse en
suffixe exact du flux complet).

Découpage : 107 segments de 512 Mo + 32 Mo de recouvrement amont (une
ligne peut s'étendre sur la frontière ; les doublons sont éliminés au
fusion par opinion_id — réextraire une ligne identique est sans effet).

Chaque appel shell traite N rounds de 2 segments (2 processus fils, un par
cœur) puis SORT PROPREMENT. L'état vit sur disque :
  segments.json            — quels segments sont faits (réécriture atomique)
  seg_NNN.found.jsonl      — records trouvés par segment (append idempotent)
  bulk_scan_progress.log   — journal lisible

Usage :
  python3 scripts/m15_bulk_segments.py --rounds 4    # ~8 segments par appel
  python3 scripts/m15_bulk_segments.py --merge       # fusionne à tout moment
"""
import argparse
import bz2
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(REPO, "data", "processed", "corpus_opinions_v1.jsonl.gz")
OUT_DIR = os.path.join(REPO, "data", "raw", "opinion_texts")
SEGMENTS = os.path.join(OUT_DIR, "segments.json")
PROGRESS = os.path.join(OUT_DIR, "bulk_scan_progress.log")
MERGED = os.path.join(OUT_DIR, "opinions_text.jsonl.gz")

BULK_URL = ("https://com-courtlistener-storage.s3.amazonaws.com"
            "/bulk-data/opinions-2026-06-30.csv.bz2")
SEG = 512 * 1024 * 1024          # segment de travail
SLACK = 32 * 1024 * 1024         # recouvrement amont (lignes frontalières)
DL_CHUNK = 32 * 1024 * 1024      # plage par requête Range
DL_CONNS = 4                     # connexions // par processus fils

ROWSTART = re.compile(rb'\n"(\d{1,8})",')
ROWTAIL = re.compile(rb',\"(\d{5,9})\"\n')
PT_END = re.compile(rb'\",(?:\"\",)*\"[<{]')

MAGIC = 0x314159265359
MAGIC_PATTERNS = []              # les 8 rotations, calculées au démarrage
for _r in range(8):
    _p = ((MAGIC << _r) & 0xFFFFFFFFFFFF) | (MAGIC >> (48 - _r)) if _r else MAGIC
    MAGIC_PATTERNS.append(_p.to_bytes(6, "big"))


def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(PROGRESS, "a") as f:
        f.write(line + "\n")


def load_targets():
    import gzip
    t = {}
    with gzip.open(CORPUS, "rt", encoding="utf-8") as g:
        for line in g:
            r = json.loads(line)
            t[int(r["opinion_id"])] = {
                "sha1": r.get("sha1"),
                "cluster_id": r.get("cluster_id"),
                "author_id": r.get("author_id"),
            }
    return t


# ---------------------------------------------------------------- téléchargement
def fetch_range(A, B, retries=6):
    """[A, B) en octets, avec retries agressifs."""
    req = urllib.request.Request(BULK_URL, headers={
        "Range": f"bytes={A}-{B-1}",
        "User-Agent": "legally-subjective/0.1 (research)"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            time.sleep(min(2 ** attempt, 30))
            log(f"    dl[{A//1024//1024}Mo] essai {attempt+1}: {e}")
    return b""


def download_stream(A, B):
    """Générateur ORDONNÉ de chunks de [A, B), pré-téléchargés par
    DL_CONNS threads en avance (le téléchargement chevauche la
    décompression — c'est le pipeline qui divise le mur par deux)."""
    import queue as _q
    spans = [(a, min(a + DL_CHUNK, B)) for a in range(A, B, DL_CHUNK)]
    results = [None] * len(spans)
    next_need = [0]
    lock = threading.Lock()
    cv = threading.Condition(lock)

    def worker():
        while True:
            with lock:
                i = next_need[0] + 0
                # prend la première plage non réclamée ET pas trop loin devant
                while i < len(spans) and (results[i] is not None or
                                          i - next_need[0] > DL_CONNS * 2):
                    i += 1
                if i >= len(spans):
                    return
                results[i] = b"PENDING"
            a, b = spans[i]
            try:
                data = fetch_range(a, b)
            except Exception as e:  # noqa: BLE001
                with lock:
                    results[i] = ("ERR", str(e))
                return
            with lock:
                results[i] = data
                cv.notify_all()

    for _ in range(DL_CONNS):
        threading.Thread(target=worker, daemon=True).start()

    for k in range(len(spans)):
        with lock:
            while results[k] is None or results[k] == b"PENDING":
                cv.wait(timeout=1.0)
                if isinstance(results[k], tuple):
                    raise RuntimeError(f"téléchargement segment: {results[k][1]}")
            data = results[k]
            next_need[0] = k + 1
            results[k] = None            # libère la mémoire
        yield data


# ---------------------------------------------------------------- réparation bz2
def find_magic(data):
    """Première magie de bloc BYTE-ALIGNÉE (pattern exact, rotation 0).

    Pourquoi seulement la rotation 0 : une magie non alignée (s≠0) est
    bordée par des bits du bloc PRÉCÉDENT — aucune rotation 48 bits n'est
    visible byte-aligned (les hits r≠0 sont du bruit, testé : échec).
    Un segment de 512 Mo contient ~3 700 blocs de ~140 Ko ; ~1/8 sont
    alignés → la première magie alignée vit à ≤ ~1,2 Mo du début du
    segment, très loin sous le recouvrement de 32 Mo. Retourne l'offset
    BIT (= 8 × offset octet), ou None."""
    i = data.find(MAGIC_PATTERNS[0])
    return 8 * i if i != -1 else None


class BitShiftReader:
    """Convertit le flux bz2 original, dont le premier bloc utile commence
    au bit p (p = 8*skip + s), en flux standalone : b'BZh9' + bits[p:].

    Démonstration : l'octet de sortie C_m = (B_m << s | B_{m+1} >> (8-s))
    & 0xFF — chaque octet de sortie mélange l'octet courant et le suivant.
    On garde donc UN octet en attente entre deux chunks. Vérifié
    empiriquement : le flux réparé décompresse en suffixe exact du flux
    complet (test du 2026-08-29 sur first1m.bz2).
    """
    def __init__(self, p, first):
        self.s = p % 8
        self.skip = p // 8
        self.first = first
        self.pend = None            # dernier octet du chunk précédent
        self.to_skip = self.skip    # octets encore à sauter (multi-chunks)

    def feed(self, chunk):
        if self.to_skip:
            if len(chunk) <= self.to_skip:
                self.to_skip -= len(chunk)
                return b""
            chunk = chunk[self.to_skip:]
            self.to_skip = 0
        if self.pend is not None:
            chunk = self.pend + chunk
        self.pend = chunk[-1:]
        if len(chunk) < 2:
            return b""
        if self.s == 0:
            out = chunk[:-1]
        else:
            n = int.from_bytes(chunk, "big")
            L = len(chunk)
            out_int = (n << self.s) & ((1 << (8 * L)) - 1)
            out = out_int.to_bytes(L, "big")[:-1]
        if self.first:
            self.first = False
            return b"BZh9" + out
        return out

    def flush(self):
        if self.pend is None:
            return b""
        b = self.pend
        self.pend = None
        if self.s == 0:
            return b
        return ((b[0] << self.s) & 0xFF).to_bytes(1, "big")


# ---------------------------------------------------------------- extraction
def extract(buf, start, oid, tgt):
    end = -1
    tries = 0
    for m in ROWTAIL.finditer(buf, start):
        tries += 1
        if tries > 60:
            break
        if int(m.group(1)) == tgt["cluster_id"]:
            end = m.end() - 1
            break
    if end == -1:
        return None, "cluster_absent"
    row = buf[start:end]
    parts = row.split(b'","', 11)
    if len(parts) < 12:
        return None, "prefixe_court"
    if parts[7].decode("utf-8", "replace") != tgt["sha1"]:
        return None, "sha1_differe"
    if parts[0] != b'"' + str(oid).encode():
        return None, "id_incohérent"
    rest = parts[11]
    m2 = PT_END.search(rest)
    if not m2:
        return None, "fin_pt_introuvable"
    pt = rest[:m2.start()].decode("utf-8", "replace")
    try:
        pages = int(parts[8] or 0) or None
    except ValueError:
        pages = None
    return {
        "opinion_id": oid,
        "plain_text": pt[:2000000],
        "html": "",
        "sha1": tgt["sha1"],
        "type": re.sub(r"^[0-9]+", "",
                       parts[6].decode("utf-8", "replace")) or None,
        "author_id": tgt["author_id"],
        "cluster_id": tgt["cluster_id"],
        "per_curiam": parts[4] == b"t",
        "page_count": pages,
        "download_url": parts[9].decode("utf-8", "replace") or None,
        "author_str": parts[3].decode("utf-8", "replace"),
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, "ok"


# ---------------------------------------------------------------- segment
def scan_buffer(buf, targets, found):
    for m in ROWSTART.finditer(buf):
        oid = int(m.group(1))
        if oid not in targets:
            continue
        rec, _ = extract(buf, m.start() + 1, oid, targets[oid])
        if rec:
            found[oid] = rec


def process_segment(seg_id, targets, total):
    A = max(0, seg_id * SEG - SLACK)
    B = min((seg_id + 1) * SEG, total)
    t0 = time.time()

    # premier chunk pour trouver la magie alignée (elle vit dans le 1er Mo)
    stream = download_stream(A, B)
    try:
        first_data = next(stream)
    except StopIteration:
        log(f"segment {seg_id:3d} : vide — ignoré")
        return {}

    p = find_magic(first_data)
    if p is None:
        log(f"segment {seg_id:3d} : AUCUNE magie alignée dans le 1er chunk "
            "(anomalie) — segment ignoré, à reprendre")
        return {}
    reader = BitShiftReader(p, first=True)
    dec = bz2.BZ2Decompressor()
    found = {}
    rej = {}
    scanned = 0
    ndl = 1
    t1 = time.time()
    tail = b""

    def feed(chunk):
        nonlocal tail, scanned
        sb = reader.feed(chunk)
        if not sb:
            return False
        try:
            out = dec.decompress(sb)
        except (OSError, ValueError):
            return True                  # fin de stream / footer
        if out:
            buf = tail + out
            cut = max(0, len(buf) - 4 * 1024 * 1024)
            if cut > 0:
                for m in ROWSTART.finditer(buf[:cut]):
                    _scan_one(buf, m, targets, found, rej)
                scanned += cut
                tail = buf[cut:]
            else:
                tail = buf
        return dec.eof

    ended = feed(first_data)
    if not ended:
        for chunk in stream:
            ndl += 1
            if feed(chunk):
                break
    if tail:
        for m in ROWSTART.finditer(tail):
            _scan_one(tail, m, targets, found, rej)
        scanned += len(tail)

    dt = time.time() - t1
    t_all = time.time() - t0
    segfile = os.path.join(OUT_DIR, f"seg_{seg_id:03d}.found.jsonl")
    with open(segfile, "w", encoding="utf-8") as f:
        for oid in sorted(found):
            f.write(json.dumps(found[oid], ensure_ascii=False) + "\n")
    log(f"segment {seg_id:3d} : {ndl} plages en {t_all:.0f}s — "
        f"{scanned/1e9:.2f} Go scannés ({scanned/1e6/dt:.0f} Mo/s) — "
        f"{len(found)} opinion(s)" +
        (f", rejets {rej}" if rej else ""))
    return found


def _scan_one(buf, m, targets, found, rej):
    oid = int(m.group(1))
    if oid not in targets:
        return
    rec, why = extract(buf, m.start() + 1, oid, targets[oid])
    if rec:
        found[oid] = rec
    else:
        rej[why] = rej.get(why, 0) + 1


# ---------------------------------------------------------------- état
def load_state(total):
    if os.path.exists(SEGMENTS):
        return json.load(open(SEGMENTS))
    return {"total": total, "seg": SEG, "done": {}}


def save_state(st):
    tmp = SEGMENTS + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f)
    os.replace(tmp, SEGMENTS)


def merge(targets):
    """Fusionne tous les seg_*.found.jsonl → opinions_text.jsonl.gz."""
    found = {}
    files = sorted(f for f in os.listdir(OUT_DIR)
                   if re.match(r"seg_\d+\.found\.jsonl$", f))
    for fn in files:
        for line in open(os.path.join(OUT_DIR, fn), encoding="utf-8"):
            r = json.loads(line)
            found[r["opinion_id"]] = r
    tmp = MERGED + ".tmp"
    import gzip
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        for oid in sorted(found):
            f.write(json.dumps(found[oid], ensure_ascii=False) + "\n")
    os.replace(tmp, MERGED)
    missing = sorted(set(targets) - set(found))
    log(f"FUSION : {len(found)}/{len(targets)} — manquants {len(missing)} "
        f"→ {missing[:15]}{'…' if len(missing) > 15 else ''}")
    return found, missing


# ---------------------------------------------------------------- main
def head_total():
    req = urllib.request.Request(BULK_URL, method="HEAD", headers={
        "User-Agent": "legally-subjective/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers["Content-Length"])


def run_rounds(rounds, targets, total, budget_s=520):
    st = load_state(total)
    nseg = (total + SEG - 1) // SEG
    t0 = time.time()
    rnd = 0
    while rnd < rounds:
        todo = [i for i in range(nseg) if str(i) not in st["done"]]
        if not todo:
            log("TOUS LES SEGMENTS SONT FAITS.")
            break
        elapsed = time.time() - t0
        if elapsed > budget_s * 0.55:      # un round ≈ 200-260s : marge
            log(f"budget : {elapsed:.0f}s écoulés — sortie propre avant "
                f"le timeout de l'appel shell")
            break
        pair = todo[:2]
        rnd += 1
        log(f"round {rnd} : segments {pair} (reste {len(todo)})")
        procs = []
        for seg_id in pair:
            procs.append(subprocess.Popen(
                [sys.executable, os.path.abspath(__file__),
                 "--seg", str(seg_id)],
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT))
        for p in procs:
            p.wait()
        for seg_id, p in zip(pair, procs):
            st["done"][str(seg_id)] = {"rc": p.returncode,
                                       "ts": time.strftime("%H:%M:%S")}
        save_state(st)
        f, _ = merge(targets)
        log(f"avancement cumulé : {len(f)}/{len(targets)} "
            f"({100*len(f)/len(targets):.1f}%)")
    return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--seg", type=int, default=None)
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    targets = load_targets()

    if args.seg is not None:
        total = head_total()
        process_segment(args.seg, targets, total)
        return

    if args.merge:
        merge(targets)
        return

    total = head_total()
    log(f"scan segmenté : {total/1e9:.2f} Go, segments de {SEG/1e6:.0f} Mo, "
        f"{len(targets)} cibles")
    run_rounds(args.rounds, targets, total)


if __name__ == "__main__":
    main()
