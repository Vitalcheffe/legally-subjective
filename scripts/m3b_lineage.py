#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M3b : remontée de la chaîne de preuve (CLI).

La question à laquelle ce outil répond (cahier des charges, ajout final) :

    « Prouve-moi que ce résultat vient bien de cette expérience précise. »

La réponse est une chaîne dont CHAQUE maillon est re-calculé, jamais cru :

    résultat (m3b_report.json)
      → adaptateurs (hash par fichier)
        → checkpoints (manifeste, génération, repli)
          → configuration (empreinte re-dérivée du manifeste)
            → données (sha256 par juge, re-lus du dépôt)
              → split temporel (gelé octet par octet)
                → commit (head_initial + gel du protocole + m4-freeze)
                  → environnement (consigné par session)
                    → journal (events.jsonl, chronologie complète)

Sortie : liste des maillons ✓/✗ + verdict global. rc 0 si intègre.

Usage :
  python scripts/m3b_lineage.py --root <racine état> --repo <dépôt>
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import m3b_state as M                                       # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True,
                    help="racine d'état M3b (Drive monté ou copie locale)")
    ap.add_argument("--repo", required=True, help="dépôt de référence")
    ap.add_argument("--json", default=None, help="sortie JSON optionnelle")
    args = ap.parse_args()

    if not os.path.isfile(os.path.join(args.root, "state.json")):
        print(f"NO-GO — aucun état dans {args.root}")
        return 2

    links, ok_all = M.verify_lineage(args.root, args.repo)
    print("═" * 70)
    print("CHAÎNE DE PREUVE M3b — remontée complète, chaque hash recalculé")
    print("═" * 70)
    n_ok = 0
    for ok, name, detail in links:
        print(f"  [{'✓' if ok else '✗'}] {name:34s} {detail[:60]}")
        n_ok += bool(ok)
    print("─" * 70)
    print(f"VERDICT : {n_ok}/{len(links)} maillons — "
          f"{'CHAÎNE INTÈGRE' if ok_all else 'CHAÎNE ROMPUE'}")
    if not ok_all:
        print("  → ne JAMAIS utiliser ces artefacts avant explication "
              "et réparation ; voir events.jsonl et log.txt.")
    print("═" * 70)

    if args.json:
        out = {"ok": ok_all, "n_links": len(links), "n_ok": n_ok,
               "links": [{"ok": o, "name": n, "detail": d}
                         for o, n, d in links],
               "root": os.path.abspath(args.root),
               "repo": os.path.abspath(args.repo)}
        tmp = args.json + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, args.json)
        print(f"→ {args.json}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
