#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simulateur de sessions M3b — miroir exact de la boucle du notebook,
exécutable en sous-processus pour INJECTER DES MORTS BRUTALES (os._exit)
au milieu de l'entraînement ou d'une copie Drive.

Utilisé par scripts/test_m3b_state.py (scénarios A-L du cahier des
charges). La logique de conduite ci-dessous est celle de la cellule §6
du notebook m3b_qlora_personas.ipynb v2 — même ordre, mêmes gardes.

CLI :
  python m3b_sim_session.py --drive DIR --local DIR [--action train|none]
      [--kill-at-step N]              # mort brutale au pas N (aucune save)
      [--kill-before-save N]          # mort juste AVANT la sauvegarde du pas N
      [--kill-during-copy N]          # mort pendant la promotion Drive du pas N
      [--budget-minutes X]            # soft deadline (arrêt propre)
      [--corrupt-official N]          # tronque optimizer.pt du ckpt officiel N
      [--delete-state]                # supprime state.json (scénario I)
      [--point-state-to N]            # falsifie le pas officiel (scénario J)
      [--mutate-config]               # change la config scientifique
"""

import argparse
import json
import os
import shutil
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import m3b_state as M                                    # noqa: E402

# ------------------------------------------------------------- constants --
JUDGES = {"AA": 140, "BB": 60, "CC": 30, "DD": 3}  # DD : trop court
                                               # pour un seul save (cas limite)
SAVE_STEPS, EVAL_STEPS, PATIENCE = 10, 20, 3
CONFIG = {"MODEL_ID": "fake/tiny-model", "MAX_LEN": 512, "INSTR_KEEP": 128,
          "LORA_R": 16, "LORA_ALPHA": 32, "LORA_DROPOUT": 0.05,
          "LR": 1e-4, "EPOCHS": 8, "BATCH": 1, "GRAD_ACCUM": 8,
          "EVAL_EVERY": EVAL_STEPS, "PATIENCE": PATIENCE, "WARMUP": 10,
          "VAL_FRACTION": 0.15, "MIN_TRAIN_ROWS": 8,
          "PERSONAS_GARDÉES": None}

OPT_SIZE = int(os.environ.get("SIM_OPT_MB", "4")) * 1024 * 1024
ADP_SIZE = 2 * 1024 * 1024


def loss_fn(step):
    """Trajectoire : baisse jusqu'au pas 60 puis remonte (early stopping
    doit se déclencher à la 3e eval dégradée = pas 120)."""
    return 3.0 - 0.02 * step if step <= 60 else 1.8 + 0.01 * (step - 60)


# ------------------------------------------------------------- artefacts --
def write_ckpt(local_out, step, judge):
    d = os.path.join(local_out, f"checkpoint-{step}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "optimizer.pt"), "wb") as f:
        f.write(os.urandom(OPT_SIZE))
    for fn in ("scheduler.pt", "rng_state.pth"):
        with open(os.path.join(d, fn), "wb") as f:
            f.write(os.urandom(4096))
    with open(os.path.join(d, "adapter_model.safetensors"), "wb") as f:
        f.write(os.urandom(ADP_SIZE))
    with open(os.path.join(d, "adapter_config.json"), "w") as f:
        json.dump({"r": 16, "judge": judge}, f)
    with open(os.path.join(d, "trainer_state.json"), "w") as f:
        json.dump({"global_step": step, "judge": judge}, f)
    return d


def make_personas(root):
    for j in JUDGES:
        d = os.path.join(root, "personas", j)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "train.jsonl"), "w") as f:
            f.write(json.dumps({"system": "s", "instruction": "i",
                                "output": "o" * 300, "date_filed": "2019-01-01"}) + "\n")
    return os.path.join(root, "personas")


# ------------------------------------------------------------ conduite ----
def run_session(args):
    drive = args.drive
    local = args.local
    os.makedirs(local, exist_ok=True)
    personas_dir = make_personas(os.path.dirname(local) or ".")

    config = dict(CONFIG)
    if args.mutate_config:
        config["EPOCHS"] = 3                      # changement SCIENTIFIQUE

    fp = M.fingerprint_of(config)
    dfp, _ = M.data_fingerprint(personas_dir, JUDGES)
    parts = {"config": fp, "data": dfp, "seed": 42}

    es = M.ExpState(drive)
    mode, msg = es.load_or_init(fp, parts, 42, "deadbeef", list(JUDGES),
                                run_id="run_sim")
    out = {"mode": mode, "msg": msg, "judges": {}}
    print(f"[session] mode={mode}")
    print(msg)
    if mode == "error":
        out["refused"] = True
        return out

    # scénario I : supprimer le manifeste APRÈS init (simule une perte)
    if args.delete_state:
        os.remove(es.path)
        if es.bak.exists():
            os.remove(es.bak)
        es2 = M.ExpState(drive)
        mode2, msg2 = es2.load_or_init(fp, parts, 42, "deadbeef",
                                       list(JUDGES), run_id="run_sim")
        out["mode_after_delete"] = mode2
        print(f"[session] après suppression du manifeste : {mode2}")
        return out

    # scénario J : falsifier le pas officiel du premier juge
    if args.point_state_to:
        first = sorted(JUDGES)[0]
        es.j(first)["ckpt"]["step"] = int(args.point_state_to)
        es.save()

    es.clean_tmp()

    # scénario H : corruption du checkpoint officiel du premier juge non
    # terminé — injectée AVANT toute restauration.
    if args.corrupt_official:
        for judge in sorted(JUDGES):
            e = es.j(judge).get("ckpt")
            if e and es.status(judge) != "done":
                p = es.ckpt_dir(judge) / f"ckpt-{e['step']}" / "optimizer.pt"
                if p.is_file():
                    with open(p, "r+b") as f:
                        f.write(b"CORRUPTED")
                    print(f"[session] corruption injectée : {p}")
                break

    if args.action == "train":
        es.state.setdefault("sessions", []).append(
            {"run_id": "run_sim", "resumed": [], "trained": []})
        es.save()
    else:
        return out

    budget_hit = False
    budget = M.TimeBudgetCallback(args.budget_minutes)   # UNE fois par SESSION
    for judge in sorted(JUDGES):
        if es.status(judge) == "done":
            print(f"[session] {judge} — déjà fait, sauté")
            out["judges"][judge] = "skipped"
            continue

        # -- reprise : ckpt officiel -> copie locale vérifiée -----------
        local_out = os.path.join(local, judge)
        resume_from = es.restore_ckpt_local(judge, local_out)
        resume_step = 0
        if resume_from:
            resume_step = json.load(open(
                os.path.join(resume_from, "trainer_state.json")))["global_step"]
            es.state["sessions"][-1]["resumed"].append(
                {judge: resume_step})
            print(f"[session] {judge} reprend au pas {resume_step}")
        else:
            print(f"[session] {judge} démarre de zéro")

        # -- callbacks RÉELS (ceux du notebook) --------------------------
        sync = M.DriveSyncCallback(es, judge)
        es_cb = M.StatefulEarlyStopping(es, judge, PATIENCE)

        kill = {"at": args.kill_at_step, "before_save": args.kill_before_save,
                "during_copy": args.kill_during_copy}

        def ckpt_writer(step, judge=judge, local_out=local_out, kill=kill,
                        es=es, sync=sync):
            if kill["before_save"] == step:
                print(f"[session] MORT BRUTALE avant la sauvegarde du pas {step}")
                sys.stdout.flush()
                os._exit(9)
            d = write_ckpt(local_out, step, judge)
            if kill["during_copy"] == step:
                # tue le processus DÈS l'apparition du .tmp (déterministe :
                # la mort tombe PENDANT la copie Drive)
                target = es.ckpt_dir(judge)
                def _killer():
                    while True:
                        if os.path.isdir(target):
                            for p in os.listdir(target):
                                if p.startswith(".tmp-"):
                                    print(f"[session] MORT BRUTALE pendant "
                                          f"la promotion du pas {step} "
                                          f"({p} partiel)")
                                    sys.stdout.flush()
                                    os._exit(9)
                        time.sleep(0.002)
                threading.Thread(target=_killer, daemon=True).start()
            return d

        def step_hook(step):
            if kill["at"] == step:
                print(f"[session] MORT BRUTALE au pas {step}")
                sys.stdout.flush()
                os._exit(9)

        es.set_status(judge, "training")
        es.save()
        runner = M.FakeRun([sync, budget, es_cb], JUDGES[judge],
                           SAVE_STEPS, EVAL_STEPS, loss_fn,
                           output_dir=local_out)
        runner.step_hook = step_hook
        last, reason = runner.run(resume_step=resume_step,
                                  ckpt_writer=ckpt_writer)
        print(f"[session] {judge} : pas {last} ({reason})")

        # juge trop court pour un seul save : adapter frais en mémoire
        fresh_adapter = None
        if es.step(judge) == 0:
            fresh_adapter = os.path.join(local, f"final_{judge}")
            if os.path.exists(fresh_adapter):
                shutil.rmtree(fresh_adapter)
            os.makedirs(fresh_adapter)
            with open(os.path.join(fresh_adapter,
                                   "adapter_model.safetensors"), "wb") as f:
                f.write(b"FRESH" + os.urandom(ADP_SIZE))
            with open(os.path.join(fresh_adapter,
                                   "adapter_config.json"), "w") as f:
                json.dump({"r": 16, "judge": judge}, f)
            print(f"[session] {judge} : aucun checkpoint n'a jamais été "
                  "promu (juge ultra-court) — adaptateur frais conservé")

        if budget.stopped_by_budget:
            budget_hit = True
            out["judges"][judge] = f"budget-stop@{last}"
            es.state["sessions"][-1]["trained"].append({judge: last})
            es.save()
            print("[session] budget épuisé — arrêt propre, rien n'est finalisé")
            break

        # -- finalisation du juge (miroir du notebook) -------------------
        best_step = es.j(judge).get("best_step") or last
        src = es.ckpt_dir(judge) / f"ckpt-{best_step}"
        if not src.is_dir() and es.j(judge).get("ckpt"):
            src = es.ckpt_dir(judge) / f"ckpt-{es.j(judge)['ckpt']['step']}"
        if not src.is_dir():
            src = None
        tmp_final = os.path.join(local, f"final_{judge}")
        if os.path.exists(tmp_final) and src is not None:
            shutil.rmtree(tmp_final)
        if src is not None:
            os.makedirs(tmp_final)
            for fn in os.listdir(src):
                if fn.startswith("adapter_"):
                    shutil.copy2(os.path.join(src, fn),
                                 os.path.join(tmp_final, fn))
        else:                     # juge ultra-court : adaptateur frais
            tmp_final = fresh_adapter
        es.promote_final_adapter(judge, tmp_final)
        ok, why = es.verify_final_adapter(judge)
        assert ok, f"adaptateur final invalide : {why}"
        es.mark_done(judge, {"n_train": 10, "n_val": 2,
                             "best_val_loss": es.j(judge)["best_val_loss"]})
        es.prune_ckpts(judge, keep=0)             # ckpts du juge terminé
        es.state["sessions"][-1]["trained"].append({judge: last})
        es.save()
        out["judges"][judge] = f"done@{last}/{reason}"
        print(f"[session] {judge} finalisé (best={best_step})")

    # -- finalisation globale (miroir §8 du notebook) ---------------------
    if es.all_done() and (not es.state.get("finalized")
                          or args.action == "export"):
        rep = es.write_report(config, os.path.join(local, "m3b_report.json"))
        final_dir = es.root / "final"
        os.makedirs(final_dir, exist_ok=True)
        zpath = os.path.join(local, "m3b_adapters_final.zip")
        entries = []
        for j in sorted(JUDGES):
            d = es.final_adapter_dir(j)
            for fn in sorted(os.listdir(d)):
                entries.append((os.path.join(d, fn), f"{j}/{fn}"))
        entries.append((os.path.join(local, "m3b_report.json"),
                        "m3b_report.json"))
        M.deterministic_write_zip(zpath, entries)
        M.promote_file(zpath, final_dir / "m3b_adapters_final.zip")
        es.state["finalized"] = True
        es.save()
        out["finalized"] = True
        print("[session] EXPÉRIENCE FINALISÉE — export final écrit")
    elif es.state.get("finalized") and args.action == "train":
        out["already_finalized"] = True
        print("[session] déjà finalisée — rien à refaire")

    for j in sorted(JUDGES):
        out["judges"].setdefault(j, es.status(j))
    out["statuses"] = {j: es.status(j) for j in JUDGES}
    out["steps"] = {j: es.step(j) for j in JUDGES}
    out["budget_hit"] = budget_hit
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drive", required=True)
    ap.add_argument("--local", required=True)
    ap.add_argument("--action", default="train",
                    choices=["train", "none", "export"])
    ap.add_argument("--kill-at-step", type=int, default=None)
    ap.add_argument("--kill-before-save", type=int, default=None)
    ap.add_argument("--kill-during-copy", type=int, default=None)
    ap.add_argument("--budget-minutes", type=float, default=0)
    ap.add_argument("--corrupt-official", action="store_true")
    ap.add_argument("--delete-state", action="store_true")
    ap.add_argument("--point-state-to", type=int, default=None)
    ap.add_argument("--mutate-config", action="store_true")
    args = ap.parse_args()
    out = run_session(args)
    print("RESULT_JSON " + json.dumps(out))


if __name__ == "__main__":
    main()
