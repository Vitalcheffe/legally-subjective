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
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import torch                                            # noqa: E402
from torch.utils.data import Dataset                    # noqa: E402

from transformers import (GPT2Config, GPT2LMHeadModel,  # noqa: E402
                          Trainer, TrainingArguments)
from peft import LoraConfig, PeftModel, get_peft_model  # noqa: E402

import m3b_state as M                                   # noqa: E402

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


def run(args):
    drive, work = args.drive, args.work
    os.makedirs(work, exist_ok=True)

    fp = M.fingerprint_of(CONFIG)
    es = M.ExpState(drive)
    mode, msg = es.load_or_init(fp, {"config": fp, "data": "fixed", "seed":
                                     SEED}, SEED, "localcpu", [JUDGE],
                                run_id="run_cpu")
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
    trainer = Trainer(model=model, args=targs,
                      train_dataset=Rows(N_SAMPLES, SEED),
                      eval_dataset=Rows(16, SEED + 1),
                      data_collator=collate, callbacks=cbs)
    trainer.train(resume_from_checkpoint=resume_from)
    final_step = trainer.state.global_step
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

    es.mark_done(JUDGE, {"n_train": N_SAMPLES, "n_val": 16,
                         "best_val_loss": es.j(JUDGE)["best_val_loss"]})
    es.prune_ckpts(JUDGE, keep=0)
    es.state["finalized"] = True
    es.state["sessions"][-1]["trained"].append({JUDGE: final_step})
    es.write_report(CONFIG, os.path.join(work, "m3b_report.json"))
    es.save()
    print("RESULT_JSON " + json.dumps(
        {"done": True, "final_step": final_step, "best_step": best_step,
         "finalized": True, "official_before_done": True}))


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
