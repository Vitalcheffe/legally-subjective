#!/usr/bin/env python3
"""
Filtre segmenté résumable pour fichiers bulk CourtListener (.csv.bz2).

Principe : les fichiers bzip2 sont constitués de blocs indépendants précédés de
la magie 48 bits 0x314159265359. Aux positions où cette magie est alignée sur un
octet, on peut démarrer un pseudo-flux « BZh9 + octets » que libbz2 décompresse
proprement. On découpe donc le fichier en unités SEGMENTÉES sur ces frontières,
chaque unité étant un décompresseur frais => point de reprise entre appels.

Intégrité : les unités sont traitées DANS L'ORDRE. La queue partielle (octets
après le dernier '\\n' de l'unité k) est préfixée à la sortie décompressée de
l'unité k+1. La concaténation reconstitue EXACTEMENT le flux décompressé
d'origine — aucune ligne perdue, aucune dupliquée.

Modes :
  scan      : frontières alignées -> <file>.ranges.json
  process   : unités dans l'ordre, reprise sur .state.json, budget temps
  finalize  : assemble, hache la source, écrit le JSONL.gz final + provenance
"""
import argparse
import base64
import bz2
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
import sys
import time

csv.field_size_limit(100 * 1024 * 1024)

BLOCK_MAGIC = bytes.fromhex("314159265359")
ROOT = "/home/z/my-project/legally-subjective"
RAW = os.path.join(ROOT, "data", "raw")
BULK = os.path.join(RAW, "_bulk")
WORK = os.path.join(RAW, "_segment_work")
PROV = os.path.join(RAW, "provenance")

os.makedirs(WORK, exist_ok=True)
os.makedirs(PROV, exist_ok=True)


def log(tag, msg):
    print(f"[{time.strftime('%H:%M:%S')}] [{tag}] {msg}", flush=True)


def seg_id(path):
    return os.path.basename(path).replace(".csv.bz2", "")


def scan_blocks(path):
    """Positions (alignées octet) de la magie de bloc, plus 0 et la taille."""
    total = os.path.getsize(path)
    positions = [0]
    with open(path, "rb") as f:
        base = 0
        prev_tail = b""
        while True:
            chunk = f.read(64 * 1024 * 1024)
            if not chunk:
                break
            data = prev_tail + chunk
            start = 0
            while True:
                i = data.find(BLOCK_MAGIC, start)
                if i == -1:
                    break
                pos = base + i - len(prev_tail)
                if pos > 0:
                    positions.append(pos)
                start = i + 1
            prev_tail = data[-5:]
            base += len(chunk)
    positions.append(total)
    positions = sorted(set(positions))
    with open(path + ".ranges.json", "w") as f:
        json.dump({"positions": positions, "total": total}, f)
    log("scan", f"{os.path.basename(path)} : {len(positions)} frontières alignées")
    return positions


def build_units(positions, target_bytes=16 * 1024 * 1024):
    """Regroupe les frontières en unités de travail d'au moins target octets.
    Chaque unité démarre sur une frontière alignée => pseudo-flux valide."""
    units = []
    total = positions[-1]
    start = positions[0]
    for p in positions[1:-1]:
        if p - start >= target_bytes:
            units.append((start, p))
            start = p
    if start < total:
        units.append((start, total))
    return units


def process(path, keep_columns, prefilter, budget_s, pf_set=None, pf_key=None):
    name = seg_id(path)
    ranges = json.load(open(path + ".ranges.json"))["positions"]
    units = build_units(ranges)
    n_units = len(units)
    state_path = os.path.join(WORK, name + ".state.json")
    if os.path.exists(state_path):
        state = json.load(open(state_path))
    else:
        state = {"next_unit": 0, "tail_b64": None, "done": False,
                 "rows_total": 0, "rows_kept": 0, "header": None}
    if state["done"]:
        log(name, "process : déjà terminé")
        return

    tail = base64.b64decode(state["tail_b64"]) if state["tail_b64"] else b""
    t0 = time.time()
    rows_total = state.get("rows_total", 0)
    rows_kept = state.get("rows_kept", 0)
    header = state.get("header")
    keep_idx = [header.index(c) for c in keep_columns] if header else []
    pf_col = prefilter[0] if prefilter else pf_key
    pf_idx = header.index(pf_col) if (header and pf_col) else None
    if pf_set is None and prefilter:
        pf_set = {prefilter[1]}
    u = state["next_unit"]

    with open(path, "rb") as f:
        while u < n_units:
            if time.time() - t0 > budget_s:
                log(name, f"budget écoulé : unité suivante = {u}/{n_units}")
                break
            start, end = units[u]
            f.seek(start)
            raw = f.read(end - start)
            stream = (b"BZh9" if start > 0 else b"") + raw
            try:
                out = bz2.BZ2Decompressor().decompress(stream)
            except OSError as e:
                log(name, f"unité {u} indécompressable ({e}) — source tronquée à la fin ; "
                          f"arrêt à {start:,} octets ({start/units[-1][1]*100:.2f} % du fichier)")
                state["done"] = True
                state["tail_b64"] = None
                state["note"] = f"source tronquée : unité {u} invalide, arrêt à {start:,} octets"
                with open(state_path + ".tmp", "w") as fs:
                    json.dump(state, fs)
                os.replace(state_path + ".tmp", state_path)
                break
            if tail:
                out = tail + out
            last_nl = out.rfind(b"\n")
            if last_nl == -1:
                tail, out = out, b""
            else:
                tail, out = out[last_nl + 1:], out[:last_nl + 1]

            chunk_out = os.path.join(WORK, f"{name}.u{u:04d}.jsonl.gz")
            n_rows = n_kept = 0
            with gzip.open(chunk_out, "wt", encoding="utf-8", compresslevel=6) as fo:
                lines = [l.decode("utf-8", errors="replace") for l in out.split(b"\n")[:-1]]
                for row in csv.reader(lines):
                    if header is None:
                        header = row
                        keep_idx = [header.index(c) for c in keep_columns]
                        if pf_col:
                            pf_idx = header.index(pf_col)
                        continue
                    if not row:
                        continue
                    n_rows += 1
                    if pf_idx is not None and pf_set is not None:
                        if pf_idx >= len(row) or row[pf_idx] not in pf_set:
                            continue
                    rec = {keep_columns[i]: (row[keep_idx[i]] if keep_idx[i] < len(row) else "")
                           for i in range(len(keep_columns))}
                    fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n_kept += 1
            rows_total += n_rows
            rows_kept += n_kept
            u += 1
            state = {"next_unit": u, "tail_b64": base64.b64encode(tail).decode(),
                     "rows_total": rows_total, "rows_kept": rows_kept,
                     "done": u >= n_units, "header": header}
            with open(state_path + ".tmp", "w") as fs:
                json.dump(state, fs)
            os.replace(state_path + ".tmp", state_path)
            if u % 10 == 0 or u == n_units:
                el = time.time() - t0
                log(name, f"unité {u}/{n_units} | {units[u-1][1]/1e9:.2f}/"
                          f"{units[-1][1]/1e9:.2f} Go | {rows_total:,} lignes | "
                          f"{rows_kept:,} gardées | {el:.0f}s")

    log(name, f"process stop : {rows_total:,} lignes vues, {rows_kept:,} gardées, "
              f"prochaine unité {state['next_unit']}/{n_units}")


def finalize(path, out_name, keep_columns, source_url, predicate_desc):
    name = seg_id(path)
    ranges = json.load(open(path + ".ranges.json"))["positions"]
    units = build_units(ranges)
    n_units = len(units)
    state = json.load(open(os.path.join(WORK, name + ".state.json")))
    if not state["done"]:
        sys.exit(f"[{name}] process incomplet ({state['next_unit']}/{n_units}) — relancer process")

    out_path = os.path.join(RAW, out_name)
    sha_comp = hashlib.sha256()
    comp_bytes = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(8 * 1024 * 1024)
            if not b:
                break
            sha_comp.update(b)
            comp_bytes += len(b)

    rows_kept = 0
    with gzip.open(out_path, "wt", encoding="utf-8", compresslevel=6) as fo:
        for u in range(n_units):
            chunk = os.path.join(WORK, f"{name}.u{u:04d}.jsonl.gz")
            if not os.path.exists(chunk):
                log(name, f"unité {u} absente (source tronquée) — ignorée")
                continue
            with gzip.open(chunk, "rt", encoding="utf-8") as fi:
                for line in fi:
                    fo.write(line)
                    rows_kept += 1
        tail = base64.b64decode(state["tail_b64"]) if state["tail_b64"] else b""
        if tail.strip():
            log(name, f"queue finale non vide ({len(tail)} octets) — ligne ajoutée")
            fo.write(tail.decode("utf-8", errors="replace") + "\n")
            rows_kept += 1

    prov = {
        "source_url": source_url,
        "source_file": os.path.basename(path),
        "sha256_compressed": sha_comp.hexdigest(),
        "bytes_compressed": comp_bytes,
        "rows_seen": state.get("rows_total", 0),
        "rows_kept": state.get("rows_kept", 0),
        "keep_columns": keep_columns,
        "filter": predicate_desc,
        "finished_at": dt.datetime.now(dt.UTC).isoformat(),
        "output": out_name,
        "output_bytes": os.path.getsize(out_path),
        "method": "segmented pseudo-stream bz2 (frontières de bloc alignées, "
                  "recousues dans l'ordre — flux identique à bzcat)",
    }
    with open(os.path.join(PROV, name + ".done.json"), "w") as f:
        json.dump(prov, f, indent=2, ensure_ascii=False)
    with open(out_path + ".sha256", "w") as f:
        f.write(hashlib.sha256(open(out_path, "rb").read()).hexdigest() + "  " + out_name + "\n")
    log(name, f"FINALISÉ : {prov['rows_kept']:,} lignes -> {out_name} "
              f"({prov['output_bytes']/1e6:.1f} Mo) ; SHA-256 source {sha_comp.hexdigest()[:16]}…")
    for u in range(n_units):
        try:
            os.remove(os.path.join(WORK, f"{name}.u{u:04d}.jsonl.gz"))
        except OSError:
            pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["scan", "process", "finalize"])
    ap.add_argument("--file", required=True)
    ap.add_argument("--keep-cols", default="")
    ap.add_argument("--prefilter", default="", help="colonne=valeur")
    ap.add_argument("--prefilter-file", default="", help="jsonl.gz pour filtre par ensemble")
    ap.add_argument("--prefilter-key", default="", help="clé extraite du fichier jsonl.gz")
    ap.add_argument("--prefilter-col", default="", help="colonne du CSV à tester (défaut = la clé)")
    ap.add_argument("--budget", type=int, default=480)
    ap.add_argument("--out", default="")
    ap.add_argument("--url", default="")
    ap.add_argument("--desc", default="")
    a = ap.parse_args()

    keep = [c for c in a.keep_cols.split(",") if c]
    pf = tuple(a.prefilter.split("=", 1)) if a.prefilter else None
    pf_set = None
    if a.prefilter_file:
        import gzip as _gz
        pf_set = set()
        with _gz.open(a.prefilter_file, "rt", encoding="utf-8") as f:
            for line in f:
                pf_set.add(str(json.loads(line).get(a.prefilter_key, "")))
        log("prefilter", f"{len(pf_set):,} clés chargées depuis {a.prefilter_file}")

    if a.mode == "scan":
        scan_blocks(a.file)
    elif a.mode == "process":
        process(a.file, keep, pf, a.budget, pf_set=pf_set,
                pf_key=(a.prefilter_col or a.prefilter_key or None))
    else:
        finalize(a.file, a.out, keep, a.url, a.desc)
