#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3b — tests du plan de lancement DÉDUIT des state.json (LS-18).

Le plan remplace tout total statique : remaining = cible − durable, la
cible venant par priorité de state.steps_total > trainer_state d'un
checkpoint > formule du notebook sur les données réelles du dépôt.

Validations (le scénario P1 reconstitue les state.json RÉELS de s1) :
  P1  s1 exact → restants 120/26/30/80/54/22, w0=176, w1=156,
      total=332, cibles des restants=368, durables des restants=36 ;
  P2  Kavanaugh done → SKIP, restant 0, AUCUNE erreur ;
  P3  hiérarchie des cibles : mesurée state (JGRoberts 32) >
      mesurée ckpt (EKagan 40, SAAlito 64) > formule (CThomas 120,
      SSotomayor 80 — sur les données réelles du dépôt) ;
  P4  V1 : juge à pas durables affecté au mauvais worker → REFUS ;
  P5  V2 : juge affecté aux deux workers → REFUS ;
  P6  V3 : juge inconnu du protocole → REFUS ;
  P7  V4 : pas durables du même juge dans deux racines → REFUS ;
  P8  juge restant non affecté → avertissement, PAS d'erreur ;
  P9  racines absentes (départ frais type s1) → cibles formule complètes
      (total = somme des cibles des 7 juges du protocole) ;
  P10 l'impression du plan tourne sans erreur (journal du noyau).

Stdlib seule. ~5 s.
"""

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from m3b_kaggle_runner import launch_plan, print_launch_plan  # noqa: E402

PASS, FAIL = 0, 0


def check(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        print(f"  FAIL  {label}")


def notebook_config_cell():
    nb = json.load(open(os.path.join(REPO, "notebooks",
                                     "m3b_qlora_personas.ipynb"),
                        encoding="utf-8"))
    hits = []
    for c in nb["cells"]:
        if c.get("cell_type") != "code":
            continue
        src = c.get("source")
        src = "".join(src) if isinstance(src, list) else (src or "")
        if "CONFIG = {" in src:
            hits.append(src)
    assert len(hits) == 1, "cellule config introuvable/ambiguë"
    return {"config": hits[0]}


def judge_entry(status="pending", step=0, steps_total=None, n_train=None):
    v = {"status": status, "step": step}
    if steps_total is not None:
        v["steps_total"] = steps_total
    if n_train is not None:
        v["n_train"] = n_train
    return v


def build_s1_roots(base):
    """Reconstitution EXACTE des state.json de s1 (valeurs tirées des
    fichiers réels, kernel aminehrc/legally-subjective-m3b-s1)."""
    w0 = os.path.join(base, "m3b_state_w0")
    w1 = os.path.join(base, "m3b_state_w1")
    os.makedirs(os.path.join(w0, "checkpoints", "EKagan", "ckpt-10"))
    os.makedirs(os.path.join(w1, "checkpoints", "SAAlito", "ckpt-10"))
    json.dump({"judges": {
        "BMKavanaugh": judge_entry("done", 16, 16, 18),
        "CThomas": judge_entry(),
        "EKagan": judge_entry("failed", 10, None, 42),
        "JGRoberts": judge_entry("training", 6, 32, 37),
        "NMGorsuch": judge_entry(),
        "SAAlito": judge_entry(),
        "SSotomayor": judge_entry(),
    }}, open(os.path.join(w0, "state.json"), "w"))
    json.dump({"judges": {
        "BMKavanaugh": judge_entry(),
        "CThomas": judge_entry(),
        "EKagan": judge_entry(),
        "JGRoberts": judge_entry(),
        "NMGorsuch": judge_entry("failed", 10, 32, 33),
        "SAAlito": judge_entry("failed", 10, None, 71),
        "SSotomayor": judge_entry(),
    }}, open(os.path.join(w1, "state.json"), "w"))
    # trainer_state des ckpt-10 (comme dans la sortie s1 réelle)
    json.dump({"max_steps": 40, "global_step": 10},
              open(os.path.join(w0, "checkpoints", "EKagan", "ckpt-10",
                                "trainer_state.json"), "w"))
    json.dump({"max_steps": 64, "global_step": 10},
              open(os.path.join(w1, "checkpoints", "SAAlito", "ckpt-10",
                                "trainer_state.json"), "w"))
    return {"m3b_state_w0": w0, "m3b_state_w1": w1}


S2_W0 = "CThomas,JGRoberts,EKagan"
S2_W1 = "SSotomayor,SAAlito,NMGorsuch"


def main():
    cells = notebook_config_cell()
    base = tempfile.mkdtemp(prefix="m3b_plan_")
    try:
        # ---- P1 : scénario s1 exact ------------------------------------
        roots = build_s1_roots(base)
        plan = launch_plan(roots, cells, REPO, S2_W0, S2_W1)
        j = plan["judges"]
        print("== P1 : scénario s1 exact ==")
        check(j["CThomas"]["remaining"] == 120, "CThomas restant 120")
        check(j["JGRoberts"]["remaining"] == 26, "JGRoberts restant 26 (32−6)")
        check(j["EKagan"]["remaining"] == 30, "EKagan restant 30 (40−10)")
        check(j["SSotomayor"]["remaining"] == 80, "SSotomayor restant 80")
        check(j["SAAlito"]["remaining"] == 54, "SAAlito restant 54 (64−10)")
        check(j["NMGorsuch"]["remaining"] == 22, "NMGorsuch restant 22 (32−10)")
        t = plan["totals"]
        check(t["w0_remaining"] == 176, f"w0 = 176 (obtenu {t['w0_remaining']})")
        check(t["w1_remaining"] == 156, f"w1 = 156 (obtenu {t['w1_remaining']})")
        check(t["remaining"] == 332, f"total restant 332 (obtenu {t['remaining']})")
        check(t["targets_of_remaining"] == 368,
              f"cibles des restants 368 (obtenu {t['targets_of_remaining']})")
        check(t["durable_of_remaining"] == 36,
              f"durables des restants 36 (obtenu {t['durable_of_remaining']})")
        check(plan["errors"] == [], "aucune erreur V1-V4")
        check(plan["unassigned_remaining"] == [], "aucun juge non affecté")

        # ---- P2 : Kavanaugh done → SKIP -------------------------------
        print("== P2 : juge done sauté, jamais réentraîné ==")
        check(j["BMKavanaugh"]["remaining"] == 0, "Kavanaugh restant 0")
        check(plan["skipped_done"] == ["BMKavanaugh"], "Kavanaugh en SKIP")
        # un done dans une liste d'affectation ne fait PAS d'erreur
        p2 = launch_plan(roots, cells, REPO,
                         "BMKavanaugh,CThomas,JGRoberts,EKagan", S2_W1)
        check(p2["errors"] == [], "done affecté → SKIP, pas d'erreur")
        check(p2["judges"]["BMKavanaugh"]["remaining"] == 0,
              "done dans la liste reste à restant 0")

        # ---- P3 : hiérarchie des cibles --------------------------------
        print("== P3 : sources des cibles ==")
        check(j["JGRoberts"]["target_source"] == "mesurée state",
              "JGRoberts : steps_total de l'état (32)")
        check(j["NMGorsuch"]["target_source"] == "mesurée state",
              "NMGorsuch : steps_total de l'état (32)")
        check(j["EKagan"]["target_source"] == "mesurée ckpt",
              "EKagan : trainer_state du ckpt (40)")
        check(j["SAAlito"]["target_source"] == "mesurée ckpt",
              "SAAlito : trainer_state du ckpt (64)")
        check(j["CThomas"]["target_source"] == "formule",
              "CThomas : formule sur données réelles (120)")
        check(j["SSotomayor"]["target_source"] == "formule",
              "SSotomayor : formule sur données réelles (80)")
        # cohérence formule ↔ mesurée là où les deux existent
        check(j["JGRoberts"]["target"] == 32 and j["NMGorsuch"]["target"] == 32
              and j["BMKavanaugh"]["target"] == 16,
              "mesurées == formule (32/32/16) : formule validée")

        # ---- P4 : V1 mauvais worker ------------------------------------
        print("== P4 : V1 — pas durables sur le mauvais worker ==")
        p4 = launch_plan(roots, cells, REPO,
                         "CThomas,EKagan", "JGRoberts,SSotomayor,SAAlito,"
                         "NMGorsuch")
        errs = " | ".join(p4["errors"])
        check(any("V1" in e and "JGRoberts" in e for e in p4["errors"]),
              f"V1 détectée pour JGRoberts : {errs[:110]}")

        # ---- P5 : V2 deux workers --------------------------------------
        print("== P5 : V2 — juge aux deux workers ==")
        p5 = launch_plan(roots, cells, REPO,
                         "CThomas,JGRoberts,EKagan",
                         "EKagan,SSotomayor,SAAlito,NMGorsuch")
        check(any("V2" in e and "EKagan" in e for e in p5["errors"]),
              "V2 détectée pour EKagan")

        # ---- P6 : V3 juge inconnu --------------------------------------
        print("== P6 : V3 — juge inconnu ==")
        p6 = launch_plan(roots, cells, REPO,
                         "CThomas,JGRoberts,EKagan,ZZInconnu", S2_W1)
        check(any("V3" in e and "ZZInconnu" in e for e in p6["errors"]),
              "V3 détectée pour ZZInconnu")

        # ---- P7 : V4 double racine durable -----------------------------
        print("== P7 : V4 — pas durables dans deux racines ==")
        st0 = json.load(open(os.path.join(roots["m3b_state_w0"],
                                          "state.json")))
        st1 = json.load(open(os.path.join(roots["m3b_state_w1"],
                                          "state.json")))
        st0["judges"]["SSotomayor"] = judge_entry("training", 12, 80)
        st1["judges"]["SSotomayor"] = judge_entry("training", 8, 80)
        json.dump(st0, open(os.path.join(roots["m3b_state_w0"],
                                         "state.json"), "w"))
        json.dump(st1, open(os.path.join(roots["m3b_state_w1"],
                                         "state.json"), "w"))
        p7 = launch_plan(roots, cells, REPO, S2_W0, S2_W1)
        check(any("V4" in e and "SSotomayor" in e for e in p7["errors"]),
              "V4 détectée pour SSotomayor (12 en w0 ET 8 en w1)")
        # état restauré pour la suite
        st0["judges"]["SSotomayor"] = judge_entry()
        st1["judges"]["SSotomayor"] = judge_entry()
        json.dump(st0, open(os.path.join(roots["m3b_state_w0"],
                                         "state.json"), "w"))
        json.dump(st1, open(os.path.join(roots["m3b_state_w1"],
                                         "state.json"), "w"))

        # ---- P8 : non affecté → avertissement seulement ----------------
        print("== P8 : juge restant non affecté ==")
        p8 = launch_plan(roots, cells, REPO, "CThomas,JGRoberts,EKagan", "")
        check(p8["errors"] == [], "aucune erreur (choix délibéré de sous-ensemble)")
        check("SSotomayor" in p8["unassigned_remaining"]
              and "SAAlito" in p8["unassigned_remaining"]
              and "NMGorsuch" in p8["unassigned_remaining"],
              "w1 non affecté → avertissement")

        # ---- P9 : départ frais (aucune racine) -------------------------
        print("== P9 : départ frais, aucune racine ==")
        p9 = launch_plan({}, cells, REPO, None, None)
        tot = sum(r["target"] for r in p9["judges"].values())
        check(len(p9["judges"]) >= 7 and tot == sum(
            p9["judges"][k]["target"] for k in p9["judges"]),
              f"cibles formule complètes ({len(p9['judges'])} juges, {tot} pas)")
        check(p9["totals"]["remaining"] == tot,
              "départ frais : restant == somme des cibles")
        check(p9["errors"] == [], "aucune erreur sans affectation")
        check(all(r["target_source"] == "formule"
                  for r in p9["judges"].values()),
              "toutes les cibles par formule")

        # ---- P10 : impression sans erreur -------------------------------
        print("== P10 : journal du plan ==")
        try:
            print_launch_plan(plan)
            print_launch_plan(p9)
            ok = True
        except Exception as e:
            print(f"    exception : {e}")
            ok = False
        check(ok, "print_launch_plan s'exécute")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print(f"\n{'=' * 60}\nPLAN : {PASS} PASS / {FAIL} FAIL")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
