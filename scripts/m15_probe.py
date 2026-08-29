#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sondeur de densité : où vivent nos 1778 opinions dans le bulk 54,56 Go ?

8 segments consécutifs sans un seul hit → le fichier est organisé par lots.
Au lieu de scander 40 Go aveuglément : 1 échantillon de 8 Mo tous les
~1,5 Go, décompression réparée, comptage des candidats dont l'id est dans
le corpus. ~25 sondes × ~3 s = ~1 min pour cartographier la bande SCOTUS.
Sortie : data/raw/opinion_texts/probes.json (densité par segment).
"""
import bz2
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m15_bulk_segments import (BULK_URL, SEG, SLACK, ROWSTART,  # noqa: E402
                               find_magic, BitShiftReader, load_targets,
                               head_total, fetch_range)


def probe(A, size, targets):
    data = fetch_range(A, A + size)
    p = find_magic(data)
    if p is None:
        return None
    rd = BitShiftReader(p, first=True)
    dec = bz2.BZ2Decompressor()
    hits = 0
    out_n = 0
    for off in range(0, len(data), 4 * 1024 * 1024):
        sb = rd.feed(data[off: off + 4 * 1024 * 1024])
        if not sb:
            continue
        try:
            out = dec.decompress(sb)
        except (OSError, ValueError):
            break
        if out:
            out_n += len(out)
            for m in ROWSTART.finditer(out):
                if int(m.group(1)) in targets:
                    hits += 1
        if dec.eof:
            break
    return {"A_gb": round(A / 1e9, 3), "decomp_mb": round(out_n / 1e6, 1),
            "hits": hits}


def main():
    targets = load_targets()
    total = head_total()
    nseg = (total + SEG - 1) // SEG
    print(f"total {total/1e9:.2f} Go, {nseg} segments — sondage…")
    results = []
    t0 = time.time()
    for seg_id in range(0, nseg, 3):            # 1 sonde / 3 segments
        A = seg_id * SEG + 40 * 1024 * 1024     # au cœur du segment
        r = probe(A, 8 * 1024 * 1024, targets)
        if r:
            results.append({"seg": seg_id, **r})
            print(f"  seg {seg_id:3d} @{r['A_gb']:.2f}Go : {r['hits']} hits "
                  f"({r['decomp_mb']:.0f} Mo décomp.)")
        if time.time() - t0 > 400:              # budget appel shell
            print("  (budget atteint — sondes restantes au prochain appel)")
            break
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "data", "raw", "opinion_texts", "probes.json")
    # fusionne avec sondes précédentes si reprise
    if os.path.exists(out):
        old = {r["seg"]: r for r in json.load(open(out))}
        for r in results:
            old[r["seg"]] = r
        results = sorted(old.values())
    with open(out, "w") as f:
        json.dump(results, f)
    hot = [r["seg"] for r in results if r["hits"] > 0]
    print(f"SONDES CHAUDES (≥1 hit) : {hot}")


if __name__ == "__main__":
    main()
