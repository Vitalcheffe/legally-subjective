#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3b — runner CPU du test d'intégration réel (transformers + peft).

Miroir CPU de la cellule §6 du notebook : VRAI Trainer, VRAI modèle LoRA
(tiny GPT2, aucun téléchargement), VRAIS callbacks de m3b_state. Exécuté
en sous-processus par test_m3b_resume_cpu.py pour pouvoir mourir
brutalement (os._exit) au milieu d'un pas d'entraînement réel.

Modes :
  full     — entraîne tout, finalise (adaptateur + rapport + done) ;
  kill-at K— meurt brutalement quand le VRAI global_step atteint K ;
  budget M — TimeBudget M minutes → arrêt propre (save puis stop) ;
  resume   — reprend depuis l'état Drive et termine.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import torch                                            # noqa: E402
from torch.utils.data import Dataset                    # noqa: E402
import time                                             # noqa: E402

from transformers import (GPT2Config, GPT2LMHeadModel,  # noqa: E402
                          Trainer, TrainingArguments)
from peft import LoraConfig, PeftModel, get_peft_model  # noqa: E402

import m3b_state as M                                   # noqa: E402


def _ver(name):
    import importlib.metadata as im
    try:
        return im.version(name)
    except im.PackageNotFoundError:
        return None

SEED = 42
JUDGE = "AA"
N_SAMPLES, SEQ, BATCH, ACCUM = 128, 48, 4, 2
EPOCHS, SAVE_EVERY, EVAL_EVERY = 3, 8, 8
TOTAL_STEPS = EPOCHS * (N_SAMPLES // (BATCH * ACCUM))          # 48
CONFIG = {"MODEL_ID": "tiny-gpt2-cpu", "MAX_LEN": SEQ,
          "INSTR_KEEP": 16, "LORA_R": 8, "LORA_ALPHA": 16,
          "LORA_DROPOUT": 0.05, "LR": 5e-4, "EPOCHS": EPOCHS,
          "BATCH": BATCH, "GRAD_ACCUM": ACCUM, "EVAL_EVERY": EVAL_EVERY,
          "PATIENCE": 99, "WARMUP": 2, "VAL_FRACTION": 0.1,
          "MIN_TRAIN_ROWS": 8, "PERSONAS_GARDÉES": None}


class Tok:                                   # encodeur factice déterministe
    pad = 0


class Rows(Dataset):
    def __init__(self, n, seed):
        g = torch.Generator().manual_seed(seed)
        self.items = []
        for _ in range(n):
            ids = torch.randint(4, 256, (SEQ,), generator=g)
            self.items.append((ids, ids.clone()))

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        ids, lab = self.items[i]
        return {"input_ids": ids, "labels": lab}


def collate(batch):
    return {"input_ids": torch.stack([b["input_ids"] for b in batch]),
            "labels": torch.stack([b["labels"] for b in batch])}


def build_model():
    torch.manual_seed(SEED)
    cfg = GPT2Config(vocab_size=256, n_positions=SEQ, n_embd=64,
                     n_layer=2, n_head=4)
    base = GPT2LMHeadModel(cfg)
    lora = LoraConfig(r=CONFIG["LORA_R"], lora_alpha=CONFIG["LORA_ALPHA"],
                      lora_dropout=CONFIG["LORA_DROPOUT"], bias="none",
                      task_type="CAUSAL_LM", target_modules=["c_attn"])
    return base, get_peft_model(base, lora)


class KillAtStep(M._callback_base()):
    """Mort brutale injectée à un VRAI pas du VRAI Trainer."""

    def __init__(self, step):
        self.step = step

    def on_step_end(self, args, state, control, **kwargs):
        if state.global_step >= self.step:
            print(f"[runner] MORT BRUTALE au pas réel {state.global_step}",
                  flush=True)
            os._exit(9)


def make_pilot_repo(work):
    """Jeu synthétique déterministe + scellé factice VALIDE — le runner
    est un test d'intégration MÉCANIQUE (tiny GPT2), pas une réplique
    scientifique : tout est étiqueté « pilot » dans le manifeste."""
    personas = os.path.join(work, "pilot_repo", "data", "m3", "personas",
                            JUDGE)
    os.makedirs(personas, exist_ok=True)
    with open(os.path.join(personas, "train.jsonl"), "w") as f:
        for i in range(64):
            f.write(json.dumps({"system": "s", "instruction": f"instr {i}",
                                "output": "o" * 220,
                                "date_filed": "2019-01-01"}) + "\n")
    cases = [f"2{i:02d}-00{i}" for i in range(50)]
    stats = {"five_four_selection": {
        "cases": cases,
        "sealed_sha256": hashlib.sha256(
            json.dumps(cases).encode()).hexdigest()}}
    p = os.path.join(work, "pilot_repo", "data", "processed")
    os.makedirs(p, exist_ok=True)
    with open(os.path.join(p, "stats_v1.json"), "w") as f:
        json.dump(stats, f)
    return os.path.join(work, "pilot_repo")


def run(args):
    drive, work = args.drive, args.work
    os.makedirs(work, exist_ok=True)
    repo = make_pilot_repo(work)

    # empreinte — MIROIR EXACT de la cellule §5bis du notebook
    fp_cfg = M.fingerprint_of(CONFIG)
    fp_dat, _ = M.data_fingerprint(
        os.path.join(repo, "data", "m3", "personas"), [JUDGE])
    fp = hashlib.sha256(json.dumps(
        {"cfg": fp_cfg, "data": fp_dat, "seed": SEED},
        sort_keys=True).encode()).hexdigest()

    env = {"python": sys.version.split()[0], "torch": torch.__version__,
           "transformers": _ver("transformers"), "peft": _ver("peft"),
           "gpu": "cpu-pilot",
           "note": "intégration CPU — tiny GPT2, données synthétiques"}
    seal = M.seal_check_from_repo(repo)

    es = M.ExpState(drive)
    mode, msg = es.load_or_init(fp, {"config": fp_cfg, "data": fp_dat},
                                SEED, "localcpu", [JUDGE],
                                run_id="run_cpu", env=env, seal=seal)
    print(f"[runner] mode={mode}")
    if mode == "error":
        print("RESULT_JSON " + json.dumps({"refused": True}))
        return

    es.clean_tmp()
    if not es.state.get("sessions"):
        es.state.setdefault("sessions", []).append(
            {"run_id": "run_cpu", "resumed": [], "trained": []})
    es.save()

    if es.status(JUDGE) == "done":
        print(f"[runner] {JUDGE} déjà fait — sauté")
        rep = es.write_report(CONFIG, os.path.join(work, "m3b_report.json"))
        print("RESULT_JSON " + json.dumps({"skipped": True,
                                           "finalized": es.state["finalized"]}))
        return

    local_out = os.path.join(work, "ckpt", JUDGE)
    resume_from = es.restore_ckpt_local(JUDGE, local_out)
    resume_step = 0
    if resume_from:
        ts = json.load(open(os.path.join(resume_from, "trainer_state.json")))
        resume_step = ts["global_step"]
        print(f"[runner] reprise réelle depuis le pas {resume_step}")

    base, model = build_model()
    n_trainable = sum(p.numel() for p in model.parameters()
                      if p.requires_grad)
    n_total = sum(p.numel() for p in model.parameters())
    j_rec = es.j(JUDGE)
    if j_rec.get("params") is None:
        j_rec["params"] = {"trainable": int(n_trainable),
                           "total": int(n_total)}
    j_rec["n_tokens_train"] = int(N_SAMPLES * SEQ)
    j_rec["steps_total"] = TOTAL_STEPS
    es.save()
    targs = TrainingArguments(
        output_dir=local_out,
        per_device_train_batch_size=BATCH,
        gradient_accumulation_steps=ACCUM,
        num_train_epochs=EPOCHS, learning_rate=CONFIG["LR"],
        lr_scheduler_type="cosine", warmup_steps=CONFIG["WARMUP"],
        logging_steps=4, eval_strategy="steps", eval_steps=EVAL_EVERY,
        save_strategy="steps", save_steps=SAVE_EVERY,
        save_total_limit=None, load_best_model_at_end=False,
        report_to="none", seed=SEED, remove_unused_columns=False,
        dataloader_pin_memory=False, use_cpu=True)

    sync = M.DriveSyncCallback(es, JUDGE)
    budget = M.TimeBudgetCallback(args.budget_minutes)
    es_cb = M.StatefulEarlyStopping(es, JUDGE, CONFIG["PATIENCE"])
    cbs = [sync, budget, es_cb]
    if args.mode == "kill-at":
        cbs.append(KillAtStep(args.kill_step))

    es.set_status(JUDGE, "training")
    es.save()
    es.event("START", judge=JUDGE, from_step=resume_step,
             total_steps=TOTAL_STEPS)
    t0 = time.time()
    trainer = Trainer(model=model, args=targs,
                      train_dataset=Rows(N_SAMPLES, SEED),
                      eval_dataset=Rows(16, SEED + 1),
                      data_collator=collate, callbacks=cbs)
    trainer.train(resume_from_checkpoint=resume_from)
    final_step = trainer.state.global_step
    j_rec["wall_seconds"] = round((j_rec.get("wall_seconds") or 0)
                                  + (time.time() - t0), 1)
    es.save()
    print(f"[runner] entraînement terminé au pas {final_step}")

    if budget.stopped_by_budget:
        es.state["sessions"][-1]["trained"].append({JUDGE: final_step})
        es.save()
        print("RESULT_JSON " + json.dumps(
            {"budget_stopped": True, "final_step": final_step,
             "official_step": es.step(JUDGE)}))
        return

    # ---- finalisation (miroir exact du notebook) ------------------------
    best_step = es.j(JUDGE).get("best_step") or final_step
    src = es.ckpt_dir(JUDGE) / f"ckpt-{best_step}"
    if not src.is_dir():
        src = es.ckpt_dir(JUDGE) / f"ckpt-{es.j(JUDGE)['ckpt']['step']}"
    tmp_final = os.path.join(work, "final_adapter")
    import shutil
    if os.path.exists(tmp_final):
        shutil.rmtree(tmp_final)
    os.makedirs(tmp_final)
    for fn in os.listdir(src):
        if fn.startswith("adapter_"):
            shutil.copy2(os.path.join(src, fn),
                         os.path.join(tmp_final, fn))
    es.promote_final_adapter(JUDGE, tmp_final)
    ok, why = es.verify_final_adapter(JUDGE)
    assert ok, f"adaptateur final invalide : {why}"

    # vérification avant de déclarer « done » : RECHARGEMENT réel
    base2, _ = build_model()
    reloaded = PeftModel.from_pretrained(base2, es.final_adapter_dir(JUDGE))
    with torch.no_grad():
        out = reloaded(input_ids=torch.randint(4, 256, (1, SEQ)))
    assert torch.isfinite(out.logits).all(), "logits non finis — adaptateur"
    es.record_validation(JUDGE, "reload_forward", True,
                         "PeftModel.from_pretrained + forward, logits finis")

    es.mark_done(JUDGE, {"n_train": N_SAMPLES, "n_val": 16,
                         "best_val_loss": es.j(JUDGE)["best_val_loss"],
                         "last_step": final_step})
    es.prune_ckpts(JUDGE, keep=0)
    es.state["sessions"][-1]["trained"].append({JUDGE: final_step})

    # ---- §7 pilote : sonde RÉELLE (génération greedy du modèle rechargé) --
    base3, _ = build_model()
    m3 = PeftModel.from_pretrained(base3, es.final_adapter_dir(JUDGE))
    m3.eval()
    with torch.no_grad():
        gen = m3.generate(input_ids=torch.randint(4, 256, (1, 8)),
                          max_new_tokens=12, do_sample=False)
    probe_txt = "".join(chr(int(x) % 128 + 32) for x in gen[0][8:].tolist())
    es.state["probe"] = {
        "case": "pilote-synthétique",
        "generations": {JUDGE: f"(greedy, 12 tokens) {probe_txt}"}}
    es.save()
    print(f"[runner] §7 pilote : sonde générée ({len(probe_txt)} caractères)")

    # ---- §7bis pilote : audit min-k% RÉEL base vs adaptateur --------------
    rows_probe = Rows(4, SEED + 7)
    K = 0.20

    def min20(model):
        vals = []
        for i in range(len(rows_probe)):
            ids, _ = rows_probe.items[i]
            ids = ids.unsqueeze(0)
            with torch.no_grad():
                lg = model(ids).logits[0]
            lp = torch.log_softmax(lg[:-1].float(), dim=-1)
            tgt = ids[0, 1:]
            tok_lp = lp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
            k = max(1, int(len(tok_lp) * K))
            vals.append(tok_lp.sort().values[:k].mean().item())
        return sum(vals) / len(vals)

    b_min, a_min = min20(base3), min20(m3)
    memo = {JUDGE: {
        "min20_base": round(b_min, 3), "min20_adapter": round(a_min, 3),
        "delta_nats": round(a_min - b_min, 3),
        "cloze_base_hits": "0/0", "cloze_adapter_hits": "0/0",
        "flag": "ok",
        "note": "pilote CPU — min-k% réel, cloze non applicable "
                "(données synthétiques aléatoires)"}}
    es.state["memorization"] = memo
    es.save()
    print(f"[runner] §7bis pilote : min-20% base={b_min:.3f} "
          f"adaptateur={a_min:.3f}")
    del m3, base3

    es.write_report(CONFIG, os.path.join(work, "m3b_report.json"))

    # ---- export final + manifeste + lignage (miroir exact du §8) --------
    zpath = os.path.join(work, "m3b_adapters_final.zip")
    d = es.final_adapter_dir(JUDGE)
    entries = [(os.path.join(d, fn), f"{JUDGE}/{fn}")
               for fn in sorted(os.listdir(d)) if os.path.isfile(
                   os.path.join(d, fn))]
    entries.append((os.path.join(work, "m3b_report.json"),
                    "m3b_report.json"))
    M.deterministic_write_zip(zpath, entries)
    M.promote_file(zpath, es.root / "final" / "m3b_adapters_final.zip")
    es.state["finalized"] = True
    es.save()
    zf = es.root / "final" / "m3b_adapters_final.zip"
    es.event("EXPORT", sha256=M.sha256_file(zf), size=zf.stat().st_size)
    es.event("RUN_COMPLETE", judges=1,
             sessions=len(es.state.get("sessions", [])))
    man = M.build_experiment_manifest(es, CONFIG, env, repo)
    links, lin_ok = M.verify_lineage(drive, repo)
    for o, name, detail in links:
        print(f"  [{'OK' if o else '!!'}] {name} — {detail}")
    M.evidence_dump(
        drive, "pilote-cpu-final",
        "PILOTE CPU FINALISÉ (tiny GPT2, données synthétiques)\n"
        f"pas finaux : {final_step}, best : {best_step}\n"
        f"chaîne de lignage : {sum(1 for o, _, _ in links if o)}"
        f"/{len(links)} liens vérifiés\n"
        f"zip sha256={M.sha256_file(zf)[:16]}…\n",
        note="intégration réelle transformers+peft — chaîne complète",
        run_id="run_cpu", head="localcpu")
    print("RESULT_JSON " + json.dumps(
        {"done": True, "final_step": final_step, "best_step": best_step,
         "finalized": True, "official_before_done": True,
         "lineage_ok": lin_ok, "manifest": man.get("schema")}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drive", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--mode", default="full",
                    choices=["full", "kill-at", "budget", "resume"])
    ap.add_argument("--kill-step", type=int, default=20)
    ap.add_argument("--budget-minutes", type=float, default=0)
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
