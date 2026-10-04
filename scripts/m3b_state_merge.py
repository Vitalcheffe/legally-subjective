#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3b — fusion d'états parallèles (workers Kaggle LS-17).

Pourquoi : l'exécution Kaggle peut entraîner plusieurs juges EN PARALLÈLE
(1 processus par GPU), chacun avec sa PROPRE racine d'état — aucun écritage
partagé, aucune course, aucune perte. Cette outil fusionne ces racines en
UNE SEULE racine officielle, de façon DÉTERMINISTE et vérifiable.

Règles de fusion (pré-enregistrées ici, avant toute utilisation réelle) :

  F1  les empreintes d'expérience doivent être IDENTIQUES entre racines —
      deux expériences différentes ne se fusionnent jamais (REFUS) ;
  F2  seed, config, data (empreintes partielles) : identiques — pris tels
      quels ; une divergence = REFUS ;
  F3  par juge : la racine qui « possède » le juge est celle au statut le
      plus avancé (done > training > pending), puis au pas le plus haut ;
      si DEUX racines ont un pas > 0 sur le même juge sans qu'aucune ne
      l'ait terminé, la plus avancée gagne et l'écart est CONSIGNÉ dans le
      journal (événement MERGE, champ conflicts) — jamais silencieux ;
  F4  artefacts par juge (checkpoints/<juge>/, adapters/<juge>/) : copiés
      depuis la racine propriétaire UNIQUEMENT ;
  F5  sessions : concaténation des listes, triées par run_id (les run_id
      sont horodatés — le tri est chronologique) ;
  F6  journal events.jsonl : concaténation, tri stable par horodatage ;
  F7  preuves evidence/ : conservées par racine source (sous-dossier
      evidence/<nom-de-racine>/) — rien n'est mélangé ni perdu ;
  F8  résultats (mark_done) : union par juge ;
  F9  l'idempotence de re-fusion n'est PAS garantie (la fusion est un
      événement unique consigné) — les sources fusionnées sont enregistrées
      dans state["merge_sources"] ;
  F10 un MERGE event est écrit dans le journal fusionné (sources, juges,
      conflits éventuels).

Sortie : rapport de fusion (JSON) + racine fusionnée exploitable par le
portillon/le lignage comme n'importe quel état mono-processus.

Usage :
  python scripts/m3b_state_merge.py --roots RACINE1 RACINE2 [...] \
       --out RACINE_FUSIONNÉE [--repo CHEMIN_DÉPÔT]
"""

import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import m3b_state as M                                     # noqa: E402

RANK = {"done": 3, "training": 2, "pending": 1}


def load_state(root):
    p = os.path.join(root, "state.json")
    if not os.path.isfile(p):
        raise SystemExit(f"racine sans state.json : {root}")
    st = json.load(open(p, encoding="utf-8"))
    if not isinstance(st.get("judges"), dict) or not st.get("fingerprint"):
        raise SystemExit(f"state.json incohérent : {root}")
    return st


def owner_rank(st, judge):
    sec = st["judges"].get(judge) or {}
    status = sec.get("status") or "pending"
    step = int(sec.get("step") or 0)
    return (RANK.get(status, 0), step)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default=None)
    args = ap.parse_args()

    if len(args.roots) < 2:
        raise SystemExit("fusion : au moins deux racines requises")
    if os.path.abspath(args.out) in [os.path.abspath(r) for r in args.roots]:
        raise SystemExit("la sortie ne peut pas être une des sources")

    states = {r: load_state(r) for r in args.roots}

    # ---- F1/F2 : identité d'expérience ---------------------------------
    fps = {r: st["fingerprint"] for r, st in states.items()}
    if len(set(fps.values())) != 1:
        raise SystemExit(f"REFUS F1 — empreintes différentes : "
                         f"{json.dumps({os.path.basename(r): f[:12] for r, f in fps.items()})}")
    ref = states[args.roots[0]]
    for r, st in states.items():
        for k in ("seed", "fingerprint_parts", "schema"):
            if st.get(k) != ref.get(k):
                raise SystemExit(f"REFUS F2 — {k} divergent entre "
                                 f"{args.roots[0]} et {r}")
    judges_ref = set(ref["judges"])
    for r, st in states.items():
        if set(st["judges"]) != judges_ref:
            raise SystemExit(f"REFUS F2 — listes de juges divergentes ({r})")

    # ---- F3 : propriétaire par juge ------------------------------------
    owners, conflicts = {}, []
    for j in sorted(judges_ref):
        cand = [(owner_rank(states[r], j), r) for r in args.roots]
        cand.sort(reverse=True)
        best_rank, best_root = cand[0]
        others = [(owner_rank(states[r], j), r) for r in args.roots
                  if r != best_root and owner_rank(states[r], j)[1] > 0]
        if others:
            conflicts.append({
                "judge": j,
                "kept": {"root": os.path.basename(best_root),
                         "status": states[best_root]["judges"][j].get("status"),
                         "step": owner_rank(states[best_root], j)[1]},
                "dropped": [{"root": os.path.basename(r), "step": rk[1]}
                            for rk, r in others]})
        owners[j] = best_root

    # ---- construction de la racine fusionnée ---------------------------
    out = args.out
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)

    merged = json.loads(json.dumps(ref))          # copie profonde de la ref
    merged["judges"] = {}
    merged["results"] = []
    merged["sessions"] = []
    merged["probe"] = None
    merged["memorization"] = None
    merged["finalized"] = False

    for j, r in owners.items():
        merged["judges"][j] = states[r]["judges"][j]
        # artefacts F4 : checkpoints + adaptateurs du propriétaire
        for sub in ("checkpoints", "adapters"):
            src = os.path.join(r, sub, j)
            if os.path.isdir(src):
                dst = os.path.join(out, sub, j)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copytree(src, dst)
        # F8 : ligne de résultats du propriétaire (clé « persona » ou
        # « judge » selon le générateur — les deux sont acceptées)
        for row in states[r].get("results") or []:
            if isinstance(row, dict) and row.get("persona", row.get("judge")) == j:
                merged["results"].append(row)
                break
        # état finalisé partiel ?
        if states[r].get("finalized"):
            merged["finalized"] = True
        if states[r].get("probe"):
            merged["probe"] = states[r]["probe"]
        if states[r].get("memorization"):
            merged["memorization"] = states[r]["memorization"]

    # F5 : sessions concaténées, tri chronologique par run_id
    all_sessions = []
    for r in args.roots:
        all_sessions.extend(states[r].get("sessions") or [])
    merged["sessions"] = sorted(all_sessions, key=lambda s: s.get("run_id", ""))
    merged["run_id"] = max((s.get("run_id", "") for s in merged["sessions"]),
                           default=ref.get("run_id"))

    # environnements/seal vus : union ordonné (traçabilité multi-sessions)
    merged["environments_seen"] = []
    merged["seal_checks"] = []
    seen_env, seen_seal = set(), set()
    for r in sorted(args.roots, key=lambda x: x):
        for e in states[r].get("environments_seen") or []:
            key = json.dumps(e, sort_keys=True)
            if key not in seen_env:
                seen_env.add(key)
                merged["environments_seen"].append(e)
        for s in states[r].get("seal_checks") or []:
            key = json.dumps(s, sort_keys=True)
            if key not in seen_seal:
                seen_seal.add(key)
                merged["seal_checks"].append(s)

    # F7 : preuves par racine source
    for r in args.roots:
        src = os.path.join(r, "evidence")
        if os.path.isdir(src):
            dst = os.path.join(out, "evidence", os.path.basename(r.rstrip("/")))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copytree(src, dst)

    merged["merge_sources"] = [os.path.basename(r.rstrip("/"))
                               for r in args.roots]

    # ---- écriture atomique du manifeste fusionné ------------------------
    M.atomic_write_json(os.path.join(out, "state.json"), merged)

    # F6 : journal concaténé, tri stable par horodatage
    lines = []
    for r in args.roots:
        p = os.path.join(r, "events.jsonl")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                lines.extend(l.rstrip("\n") for l in f if l.strip())
    lines.sort(key=lambda l: (json.loads(l).get("ts", ""),))
    with open(os.path.join(out, "events.jsonl"), "w", encoding="utf-8") as f:
        for l in lines:
            f.write(l + "\n")
        f.flush()
        os.fsync(f.fileno())

    # F10 : événement MERGE dans le journal fusionné
    es = M.ExpState(out)
    es.state = merged
    es.event("MERGE", sources=merged["merge_sources"],
             judges=len(merged["judges"]),
             conflicts=len(conflicts))

    # ---- rapport de fusion ------------------------------------------------
    report = {
        "schema": "m3b-state-merge/1",
        "roots": merged["merge_sources"],
        "fingerprint": merged["fingerprint"],
        "owners": {j: os.path.basename(r.rstrip("/"))
                   for j, r in owners.items()},
        "conflicts": conflicts,
        "n_sessions": len(merged["sessions"]),
        "n_events": len(lines),
        "statuses": {j: merged["judges"][j].get("status")
                     for j in sorted(merged["judges"])},
        "finalized": merged["finalized"],
    }
    M.atomic_write_json(os.path.join(out, "merge_report.json"), report)

    print(f"fusion : {len(args.roots)} racines → {out}")
    print(f"  empreinte : {merged['fingerprint'][:16]}… (identique partout)")
    print(f"  statuts   : {report['statuses']}")
    if conflicts:
        print(f"  ⚠ {len(conflicts)} conflit(s) tranché(s) au pas le plus "
              f"avancé et consigné(s) : {json.dumps(conflicts, ensure_ascii=False)}")
    print(f"  sessions  : {report['n_sessions']} | événements : {report['n_events']}")

    # contrôle : l'état fusionné doit être RELISIBLE par ExpState
    es2 = M.ExpState(out)
    _head = (merged.get("code") or {}).get("head_initial") or "merged"
    mode, msg = es2.load_or_init(merged["fingerprint"],
                                 merged.get("fingerprint_parts"),
                                 merged.get("seed"), _head,
                                 list(merged["judges"]),
                                 run_id="merge-check")
    print(f"  relecture : mode={mode} ({msg[:70]}…)")
    if mode == "error":
        print("ÉCHEC — l'état fusionné n'est pas relisible proprement")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
