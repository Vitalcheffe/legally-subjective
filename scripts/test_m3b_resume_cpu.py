#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3b — test d'intégration RÉEL de la reprise (transformers + peft, CPU).

Différence avec test_m3b_state.py (boucle factice) : ici le VRAI
transformers.Trainer tourne avec les VRAIS callbacks de m3b_state, sur un
vrai modèle LoRA (tiny GPT2 construit localement, zéro téléchargement).
Les sessions sont de vrais sous-processus, tués brutalement en plein pas
d'entraînement réel.

Points d'intégration à risque, vérifiés ici :
  1. DriveSyncCallback.on_save est appelé APRÈS l'écriture du checkpoint
     (le promote trouve bien les fichiers) ;
  2. resume_from_checkpoint sur un checkpoint promu puis rapatrié par
     restore_ckpt_local restaure l'état et termine au BON total de pas ;
  3. TimeBudgetCallback : should_save + should_training_stop → le Trainer
     sauvegarde le pas courant PUIS s'arrête (pas l'inverse) ;
  4. StatefulEarlyStopping lit les vrais metrics eval_loss ;
  5. La finalisation recharge le meilleur checkpoint et l'adaptateur
     final se vérifie par un vrai forward.

Auto-skip propre si torch/transformers/peft sont absents (politique
CI stdlib) : le test complet vit côté atelier, pas dans le portillon.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "m3b_cpu_runner.py")

NPASS = NFAIL = 0


def check(cond, name, detail=""):
    global NPASS, NFAIL
    if cond:
        NPASS += 1
        print(f"  PASS  {name}")
    else:
        NFAIL += 1
        print(f"  FAIL  {name}  {detail}")


def pick_python():
    """Le venv muni de torch, ou l'interpréteur courant s'il l'a déjà."""
    venv = "/home/z/my-project/.venvs/m3b/bin/python"
    if os.path.isfile(venv):
        return venv
    try:
        import torch                                   # noqa: F401
        import transformers                            # noqa: F401
        import peft                                    # noqa: F401
        return sys.executable
    except ImportError:
        return None


def session(py, drive, work, mode="full", kill_step=20, budget=0):
    cmd = [py, RUNNER, "--drive", drive, "--work", work, "--mode", mode]
    if mode == "kill-at":
        cmd += ["--kill-step", str(kill_step)]
    if mode == "budget":
        cmd += ["--budget-minutes", str(budget)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    out = r.stdout + (r.stderr[-3000:] if r.stderr else "")
    js = None
    for line in reversed((r.stdout or "").splitlines()):
        if line.startswith("RESULT_JSON "):
            js = json.loads(line[len("RESULT_JSON "):])
            break
    return r.returncode, out, js


def state_of(drive):
    return json.load(open(os.path.join(drive, "state.json"),
                          encoding="utf-8"))


def fresh():
    base = tempfile.mkdtemp(prefix="m3b_cpu_")
    return base, os.path.join(base, "drive"), os.path.join(base, "work")


def main():
    py = pick_python()
    if py is None:
        print("SKIP — torch/transformers/peft absents (test atelier, "
              "pas CI). Installer .venvs/m3b pour l'exécuter.")
        return 0

    print("\n=== R1 · session complète de bout en bout ===")
    base, drive, work = fresh()
    rc, out, js = session(py, drive, work, mode="full")
    check(rc == 0, "R1.rc0", out[-600:])
    check(js and js.get("done") and js.get("finalized"), "R1.done_finalized",
          str(js))
    check(js and js.get("final_step") == 48, "R1.total_48pas",
          str(js and js.get("final_step")))
    st = state_of(drive)
    check(st["judges"]["AA"]["status"] == "done", "R1.statut_done")
    check(os.path.isfile(os.path.join(drive, "adapters", "AA",
                                      "adapter_model.safetensors")),
          "R1.adaptateur_final")
    rep = json.load(open(os.path.join(drive, "m3b_report.json")))
    check(rep["results"][0]["verified"] is True, "R1.rapport_vérifié")

    print("\n=== R2 · mort brutale en plein pas réel, puis reprise ===")
    base, drive, work = fresh()
    rc1, out1, _ = session(py, drive, work, mode="kill-at", kill_step=20)
    check(rc1 == 9, "R2.mort_rc9", f"rc={rc1}")
    st = state_of(drive)
    check(st["judges"]["AA"]["status"] == "training", "R2.training")
    check(st["judges"]["AA"]["step"] == 16, "R2.dernier_pas_durable_16",
          str(st["judges"]["AA"]["step"]))
    import m3b_state as MS
    ok, why = MS.ExpState(drive).verify_drive_entry(
        st["judges"]["AA"]["ckpt"], "AA")
    check(ok, "R2.ckpt16_intègre", why)
    rc2, out2, js2 = session(py, drive, work, mode="resume")
    check(rc2 == 0, "R2.session2_rc0", out2[-600:])
    check("reprise réelle depuis le pas 16" in out2, "R2.resume_16")
    check(js2 and js2.get("final_step") == 48, "R2.finit_à_48",
          str(js2 and js2.get("final_step")))
    check(js2 and js2.get("finalized"), "R2.finalized")

    print("\n=== R3 · budget temps → arrêt PROPRE (save PUIS stop) ===")
    base, drive, work = fresh()
    rc, out, js = session(py, drive, work, mode="budget", budget=0.004)
    check(rc == 0, "R3.rc0", out[-600:])
    check(js and js.get("budget_stopped") is True, "R3.arrêt_budget")
    check(js and js["official_step"] == js["final_step"],
          "R3.ckpt==pas_d'arrêt", str(js))
    st = state_of(drive)
    check(st["judges"]["AA"]["status"] == "training", "R3.pas_finalisé")
    rc2, out2, js2 = session(py, drive, work, mode="resume")
    check(rc2 == 0 and js2 and js2.get("finalized"), "R3.termine_ensuite",
          out2[-600:])
    check(f"reprise réelle depuis le pas {js['final_step']}" in out2
          if js else False, "R3.reprise_au_pas_exact")

    print("\n=== R4 · re-exécution sur état finalisé (idempotence) ===")
    rc, out, js = session(py, drive, work, mode="resume")
    check(rc == 0 and js and js.get("skipped"), "R4.sauté_sans_rien_casser",
          str(js))

    print("\n════════════════════════════════════════════════")
    print(f"INTÉGRATION RÉELLE : {NPASS} PASS / {NFAIL} FAIL")
    print("════════════════════════════════════════════════")
    return 1 if NFAIL else 0


if __name__ == "__main__":
    sys.exit(main())
