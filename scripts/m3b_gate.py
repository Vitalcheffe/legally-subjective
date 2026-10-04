#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M3b : portillon GO/NO-GO objectif (critère X).

Décide, sur des VÉRIFICATIONS (jamais sur des affirmations), si M3b est
scientifiquement terminé et si l'épreuve M4 peut être approchée :

  G1  manifeste d'état présent, schéma attendu ;
  G2  juges attendus EXACTEMENT ceux du corpus (règle MIN_TRAIN_ROWS du
      protocole, recalculée depuis le dépôt) — ni plus, ni moins ;
  G3  tous les juges « done » + adaptateur final INTÈGRE sur le Drive
      (hash par fichier re-vérifiés) ;
  G4  résultats complets (n_train, best_val_loss, last_step >= 1) ;
  G5  sonde §7 + audit anti-mémorisation §7bis présents ;
  G6  finalisation + export final présent, sha256 conforme ;
  G7  journal d'événements cohérent (un JUDGE_COMPLETE par juge,
      RUN_COMPLETE, ERROR toujours résolus ensuite) ;
  G8  scellé M4 INTÈGRE dans le dépôt de référence ET exclu du corpus
      d'entraînement (re-vérification indépendante, dockets normalisés) ;
  G9  empreinte d'expérience re-dérivée du dépôt == empreinte enregistrée
      (configuration + données + seed — déterminisme bout en bout) ;
  G10 versions épinglées enregistrées dans le manifeste (WARN si divergence
      — l'environnement réel prime, il doit être documenté).

Verdict : GO (rc 0) / NO-GO (rc 1) / ERREUR d'exécution (rc 2).
Sortie JSON machine-readable + rapport lisible.

Usage :
  python scripts/m3b_gate.py --root <racine Drive/état> --repo <dépôt>
  python scripts/m3b_gate.py --root ... --repo ... --json out.json
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import m3b_state as M                                       # noqa: E402

SCHEMA_GATE = "m3b-gate/1"
PINNED = {"transformers": "4.49.0", "peft": "0.13.2",
          "bitsandbytes": (">=0.47.0,<0.51")}


def expected_judges(repo, min_rows=8):
    """Règle du protocole (miroir de load_persona + MIN_TRAIN_ROWS) :
    opinions de sortie > 200 signes, tri temporel, >= min_rows."""
    personas = os.path.join(str(repo), "data", "m3", "personas")
    out = {}
    if not os.path.isdir(personas):
        return out, personas
    for name in sorted(os.listdir(personas)):
        p = os.path.join(personas, name, "train.jsonl")
        if not os.path.isfile(p):
            continue
        n = 0
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("output") and len(r["output"]) > 200:
                    n += 1
        out[name] = n
    return {j: n for j, n in out.items() if n >= min_rows}, personas


def sealed_check(repo):
    """Re-vérification INDÉPENDANTE de l'exclusion du scellé (ne fait pas
    confiance à m15_audit : re-parcourt train.jsonl avec les mêmes clés
    canoniques de dockets)."""
    sys.path.insert(0, os.path.join(str(repo), "scripts"))
    try:
        import m3_build_datasets as B
    except Exception as e:
        return None, f"m3_build_datasets importable : {e}"
    stats = json.load(open(os.path.join(str(repo), "data", "processed",
                                        "stats_v1.json"), encoding="utf-8"))
    is_sealed = B.sealed_dockets(stats)          # prédicat canonique
    n_sealed = len(stats["five_four_selection"]["cases"])
    personas = os.path.join(str(repo), "data", "m3", "personas")
    hits, n_rows = [], 0
    for name in sorted(os.listdir(personas)) if os.path.isdir(personas) else []:
        p = os.path.join(personas, name, "train.jsonl")
        if not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                n_rows += 1
                if is_sealed({"docket": r.get("docket", "")}):
                    hits.append((name, r.get("docket")))
    integrity = M.seal_check_from_repo(repo)
    return ({"hits": hits, "n_rows": n_rows, "n_sealed": n_sealed,
             "integrity": integrity},
            None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True,
                    help="racine d'état M3b (Drive monté ou copie)")
    ap.add_argument("--repo", required=True, help="dépôt de référence")
    ap.add_argument("--json", default=None, help="sortie JSON optionnelle")
    args = ap.parse_args()

    checks = []

    def add(cid, ok, detail, severity="FAIL", warn=False):
        checks.append({"id": cid, "ok": bool(ok),
                       "severity": ("WARN" if warn else severity) if not ok
                       else "PASS",
                       "detail": str(detail)})

    root, repo = args.root, args.repo
    st = None
    try:
        st = json.load(open(os.path.join(root, "state.json"),
                            encoding="utf-8"))
    except Exception as e:
        add("G1.manifeste_état", False, f"state.json illisible : {e}")
    if st is None:
        print("NO-GO — manifeste d'état absent/illisible")
        return 1
    add("G1.manifeste_état", st.get("schema") in ("m3b-state/3",
                                                  "m3b-state/2"),
        st.get("schema"))

    # G2 — juges attendus, recalculés depuis le dépôt
    exp, personas_dir = expected_judges(repo, min_rows=8)
    got = set(st.get("judges", {}))
    add("G2.juges_attendus", got == set(exp),
        f"attendus {sorted(exp)} ({sum(exp.values())} opinions) vs "
        f"manifeste {sorted(got)}")

    # G3 — done + adaptateurs intègres
    es = M.ExpState(root)
    es.state = st
    for j in sorted(exp):
        v = st["judges"].get(j, {})
        if v.get("status") != "done":
            add(f"G3.{j}.done", False, f"statut {v.get('status')}")
            continue
        ok, why = es.verify_final_adapter(j)
        add(f"G3.{j}.adaptateur", ok, why)

    # G4 — résultats complets
    rows = {r.get("persona"): r for r in st.get("results", [])}
    for j in sorted(exp):
        r = rows.get(j)
        add(f"G4.{j}.résultat", bool(r) and r.get("n_train") and
            r.get("best_val_loss") is not None and (r.get("last_step") or 0) >= 1,
            r or "absent du rapport")

    # G5 — sonde + audit mémorisation
    add("G5.sonde_§7", bool(st.get("probe")),
        "section probe du manifeste" if st.get("probe") else "absente")
    add("G5.audit_§7bis", bool(st.get("memorization")),
        "section memorization du manifeste" if st.get("memorization")
        else "absente")

    # G6 — finalisation + export
    zf = os.path.join(root, "final", "m3b_adapters_final.zip")
    man = None
    try:
        man = json.load(open(os.path.join(root, "experiment_manifest.json"),
                             encoding="utf-8"))
    except Exception:
        pass
    add("G6.finalisé", st.get("finalized") is True,
        f"finalized={st.get('finalized')}")
    if os.path.isfile(zf) and man:
        az = (man.get("artifacts") or {}).get("final_zip") or {}
        h = M.sha256_file(zf)
        add("G6.export.sha256", h == az.get("sha256"),
            f"{h[:12]}… vs {(az.get('sha256') or '—')[:12]}…")
    else:
        add("G6.export.sha256", False, "export final ou manifeste absent")

    # G7 — journal cohérent
    evts, partial = M.read_events(root)
    jc = {e.get("judge") for e in evts if e["kind"] == "JUDGE_COMPLETE"}
    add("G7.journal.juges", jc == set(exp),
        f"{sorted(jc)} vs {sorted(exp)}")
    add("G7.journal.run_complete",
        any(e["kind"] == "RUN_COMPLETE" for e in evts),
        "événement RUN_COMPLETE présent" if any(e["kind"] == "RUN_COMPLETE"
                                                for e in evts) else
        "jamais émis — finalisation incomplète")
    errs = [e for e in evts if e["kind"] == "ERROR" and e.get("judge")]
    completes = []
    for i, e in enumerate(evts):
        if e["kind"] == "JUDGE_COMPLETE":
            completes.append((e.get("judge"), i))
    unresolved = []
    for i, e in enumerate(errs):
        j = e.get("judge")
        if j and not any(cj == j and ci > i for cj, ci in completes):
            unresolved.append(j)
    add("G7.erreurs_résolues", not unresolved,
        f"erreurs sans complétion postérieure : "
        f"{sorted(set(unresolved)) or 'aucune'}")

    # G8 — scellé intègre + exclu (indépendant)
    sealed, err = sealed_check(repo)
    if err:
        add("G8.scellé", False, err)
    else:
        add("G8.scellé.intégrité", sealed["integrity"].get("ok") is True,
            sealed["integrity"])
        add("G8.scellé.exclu", not sealed["hits"],
            f"{sealed['n_rows']} lignes parcourues, {sealed['n_sealed']} "
            f"scellés, hits : {sealed['hits'] or 'aucun'}")

    # G9 — empreinte re-dérivée
    if man and man.get("protocol"):
        import hashlib
        fp_cfg = M.fingerprint_of(man["protocol"]["sci_config"])
        fp_dat, _ = M.data_fingerprint(
            os.path.join(str(repo), "data", "m3", "personas"), list(exp))
        combined = hashlib.sha256(json.dumps(
            {"cfg": fp_cfg, "data": fp_dat, "seed": man["protocol"]["seed"]},
            sort_keys=True).encode()).hexdigest()
        add("G9.empreinte", combined == st.get("fingerprint"),
            f"re-dérivée {combined[:12]}… vs enregistrée "
            f"{(st.get('fingerprint') or '—')[:12]}…")
    else:
        add("G9.empreinte", False, "manifeste de lignage absent")

    # G10 — versions épinglées (WARN)
    env = (man or {}).get("environment") or st.get("environment") or {}
    for pkg, pin in PINNED.items():
        v = env.get(pkg)
        ok = (v == pin) if pkg != "bitsandbytes" else bool(
            v and v >= "0.47.0" and not v.startswith("0.51"))
        add(f"G10.{pkg}", ok, f"enregistré {v}, épinglé {pin}", warn=True)

    # ---- verdict -----------------------------------------------------------
    fails = [c for c in checks if not c["ok"] and c["severity"] == "FAIL"]
    warns = [c for c in checks if c["ok"] is False and c["severity"] == "WARN"]
    verdict = "GO" if not fails else "NO-GO"

    print("═" * 66)
    print(f"PORTILLON M3b — {verdict}")
    print("═" * 66)
    for c in checks:
        mark = {"PASS": "✓", "FAIL": "✗", "WARN": "!"}[c["severity"]]
        print(f"  [{mark}] {c['id']:28s} {c['detail'][:70]}")
    if warns:
        print(f"  — {len(warns)} avertissement(s) non bloquant(s)")
    print("═" * 66)

    out = {"schema": SCHEMA_GATE, "verdict": verdict,
           "n_checks": len(checks),
           "n_fail": len(fails), "n_warn": len(warns),
           "checks": checks,
           "root": os.path.abspath(root), "repo": os.path.abspath(repo)}
    if args.json:
        tmp = args.json + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, args.json)
        print(f"→ {args.json}")
    return 0 if verdict == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
