#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test de l'outil de fusion d'états parallèles M3b (LS-17).

Scénarios (tous sur simulateur réel, sous-processus) :
  T1  racines disjointes (w0: AA+BB, w1: CC) → fusion : propriétaires
      corrects, empreinte identique, statuts union, sessions concaténées ;
  T2  conflit volontaire (w2 reprend AA et l'arrête par budget au pas 20,
      moins avancé que w0) → la fusion garde w0/AA, consigne le conflit ;
  T3  reprise après fusion : une session sur l'état fusionné entraîne DD
      (le seul restant) puis finalise — lignage + portillon GO ;
  T4  REFUS : fusion d'une racine à empreinte différente (config mutée) ;
  T5  journal fusionné : tri chronologique, événement MERGE présent,
      événements des deux racines conservés ;
  T6  idempotence de relecture : ExpState relit la racine fusionnée en
      mode resume (pas fresh, pas error).

Chaque contrôle = vérification réelle sur fichiers.
"""

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SIM = os.path.join(REPO, "scripts", "m3b_sim_session.py")
MERGE = os.path.join(REPO, "scripts", "m3b_state_merge.py")
BASE = "/tmp/m3b_merge_test"

NPASS = NFAIL = 0


def check(cond, name, detail=""):
    global NPASS, NFAIL
    if cond:
        NPASS += 1
        print(f"  PASS  {name}")
    else:
        NFAIL += 1
        print(f"  FAIL  {name}  {detail}")


def sim(drive, local, extra=()):
    r = subprocess.run([sys.executable, SIM, "--drive", drive,
                        "--local", local, *extra],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit(f"simulateur en échec sur {drive}")
    for line in r.stdout.splitlines():
        if line.startswith("RESULT_JSON "):
            return json.loads(line[len("RESULT_JSON "):])
    raise SystemExit("RESULT_JSON absent")


def main():
    shutil.rmtree(BASE, ignore_errors=True)
    os.makedirs(BASE)

    print("T1 · racines disjointes")
    a = sim(f"{BASE}/w0", f"{BASE}/w0_loc", ("--judges", "AA,BB"))
    check(a["statuses"]["AA"] == "done" and a["statuses"]["BB"] == "done",
          "T1.w0_possède_AA_BB", json.dumps(a["statuses"]))
    c = sim(f"{BASE}/w1", f"{BASE}/w1_loc", ("--judges", "CC"))
    check(c["statuses"]["CC"] == "done" and c["statuses"]["AA"] == "pending",
          "T1.w1_possède_CC_uniquement", json.dumps(c["statuses"]))
    check(a.get("steps", {}).get("AA") == 120, "T1.w0_AA_pas_120")

    # empreintes identiques malgré les sous-ensembles différents
    st_a = json.load(open(f"{BASE}/w0/state.json"))
    st_c = json.load(open(f"{BASE}/w1/state.json"))
    check(st_a["fingerprint"] == st_c["fingerprint"],
          "T1.empreintes_identiques",
          f"{st_a['fingerprint'][:10]} vs {st_c['fingerprint'][:10]}")

    r = subprocess.run([sys.executable, MERGE,
                        "--roots", f"{BASE}/w0", f"{BASE}/w1",
                        "--out", f"{BASE}/merged"],
                       capture_output=True, text=True, timeout=300)
    check(r.returncode == 0, "T1.fusion_rc0", r.stdout[-300:])
    m = json.load(open(f"{BASE}/merged/state.json"))
    check(m["judges"]["AA"]["status"] == "done"
          and m["judges"]["CC"]["status"] == "done"
          and m["judges"]["DD"]["status"] == "pending",
          "T1.statuts_union", json.dumps({k: v["status"]
                                          for k, v in m["judges"].items()}))
    check(os.path.isdir(f"{BASE}/merged/adapters/AA")
          and os.path.isdir(f"{BASE}/merged/adapters/CC")
          and not os.path.isdir(f"{BASE}/merged/adapters/DD"),
          "T1.artefacts_propriétaires")
    check(len(m["sessions"]) == 2, "T1.sessions_concaténées",
          str(len(m["sessions"])))

    print("T2 · conflit volontaire (AA moins avancé ailleurs)")
    # w2 : reprend AA depuis ZÉRO dans une NOUVELLE racine, budget → pas 20
    w2 = sim(f"{BASE}/w2", f"{BASE}/w2_loc",
             ("--judges", "AA", "--budget-minutes", "0.0001"))
    # budget quasi nul → arrêt au premier pas ; AA reste "training" pas<120
    r2 = subprocess.run([sys.executable, MERGE,
                         "--roots", f"{BASE}/merged", f"{BASE}/w2",
                         "--out", f"{BASE}/merged2"],
                        capture_output=True, text=True, timeout=300)
    check(r2.returncode == 0, "T2.fusion_rc0", r2.stdout[-300:])
    rep2 = json.load(open(f"{BASE}/merged2/merge_report.json"))
    check(any(cf["judge"] == "AA" for cf in rep2["conflicts"]),
          "T2.conflit_consigné", json.dumps(rep2["conflicts"]))
    m2 = json.load(open(f"{BASE}/merged2/state.json"))
    check(m2["judges"]["AA"]["status"] == "done"
          and m2["judges"]["AA"].get("step") == 120,
          "T2.AA_garde_le_plus_avancé",
          f"step={m2['judges']['AA'].get('step')}")

    print("T3 · reprise + finalisation SUR l'état fusionné")
    f3 = sim(f"{BASE}/merged2", f"{BASE}/fin_loc")          # entraîne DD + finalise
    check(f3["statuses"]["DD"] == "done", "T3.DD_terminé",
          json.dumps(f3["statuses"]))
    check(f3.get("finalized") is True, "T3.finalisé")
    check(f3.get("lineage_ok") is True, "T3.lignage_ok")

    gate = subprocess.run(
        [sys.executable, os.path.join(REPO, "scripts", "m3b_gate.py"),
         "--root", f"{BASE}/merged2", "--repo", f"{BASE}/repo",
         "--json", f"{BASE}/merged2/gate.json"],
        capture_output=True, text=True, timeout=300)
    # NB : le simulateur n'exécute PAS les sondes §7/§7bis (seul le pilote
    # réel le fait) → G5 sonde/audit absent est le SEUL échec attendu.
    # Tout le reste (manifeste, juges, adaptateurs, résultats, export,
    # journal, scellé, empreinte) doit être vert : c'est ça qui prouve que
    # la fusion est équivalente à un état mono-processus.
    g = json.load(open(f"{BASE}/merged2/gate.json")) \
        if os.path.isfile(f"{BASE}/merged2/gate.json") else {"checks": []}
    # NB : le simulateur n'exécute PAS les sondes §7/§7bis (seul le pilote
    # réel le fait) → G5 sonde/audit absent est le SEUL échec attendu.
    # G10 (pins versions) est de sévérité WARN — non bloquant par design.
    # G4.DD : cas limite ULTRA-COURT pré-enregistré (3 pas < SAVE_STEPS=10
    # → jamais de checkpoint ni d'eval → last_step=0, best_val_loss=None).
    # Avec les 7 vrais juges (≥ 21 pas), cette branche ne peut PAS être
    # atteinte — divergence documentée, non masquée.
    allowed = ("sonde", "audit", "§7", "G4.DD.résultat")
    unexpected = [c["id"] for c in g.get("checks", [])
                  if not c.get("ok") and c.get("severity") == "FAIL"
                  and not any(a in c["id"] for a in allowed)]
    check(not unexpected, "T3.portillon_sans_échec_inattendu",
          f"échecs inattendus : {unexpected} | verdict={g.get('verdict')}")
    gchk = {c["id"]: c.get("ok") for c in g.get("checks", [])}
    check(gchk.get("G2.juges_attendus"), "T3.juges_attendus_retrouvés",
          "G2 doit retrouver les 4 juges du mini-repo")
    check(gchk.get("G8.scellé.intégrité") and gchk.get("G8.scellé.exclu"),
          "T3.scellé_vérifié_sur_fusion")
    check(gchk.get("G9.empreinte"), "T3.empreinte_re_dérivée_identique",
          "G9 re-dérive l'empreinte depuis le dépôt — doit matcher")
    check(gchk.get("G6.export.sha256"), "T3.export_vérifié_sur_fusion")

    print("T4 · REFUS d'empreintes différentes")
    sim(f"{BASE}/w_mut", f"{BASE}/w_mut_loc", ("--mutate-config",))
    r4 = subprocess.run([sys.executable, MERGE,
                         "--roots", f"{BASE}/w0", f"{BASE}/w_mut",
                         "--out", f"{BASE}/never"],
                        capture_output=True, text=True, timeout=120)
    check(r4.returncode != 0 and "REFUS" in (r4.stdout + r4.stderr),
          "T4.refus_f1", (r4.stdout + r4.stderr)[-200:])
    check(not os.path.exists(f"{BASE}/never/state.json"),
          "T4.aucun_état_fabriqué")

    print("T5 · journal fusionné")
    evts = [json.loads(l) for l in open(f"{BASE}/merged2/events.jsonl")]
    tss = [e["ts"] for e in evts]
    check(tss == sorted(tss), "T5.tri_chronologique")
    check(any(e["kind"] == "MERGE" for e in evts), "T5.événement_MERGE_présent")
    kinds = {e["kind"] for e in evts}
    check({"START", "CHECKPOINT", "JUDGE_COMPLETE"} <= kinds,
          "T5.fusion_sans_perte", str(sorted(kinds)))

    print("T6 · relecture ExpState de l'état fusionné")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "m3b_state", os.path.join(REPO, "scripts", "m3b_state.py"))
    M = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M)
    st2 = json.load(open(f"{BASE}/merged/state.json"))
    es = M.ExpState(f"{BASE}/merged")
    _head = (st2.get("code") or {}).get("head_initial") or "t6"
    mode, _ = es.load_or_init(st2["fingerprint"],
                              st2.get("fingerprint_parts"),
                              st2.get("seed"), _head,
                              list(st2["judges"]), run_id="t6")
    check(mode == "resume", "T6.mode_resume", mode)

    print("=" * 60)
    print(f"FUSION D'ÉTATS : {NPASS} PASS / {NFAIL} FAIL")
    return 0 if NFAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
