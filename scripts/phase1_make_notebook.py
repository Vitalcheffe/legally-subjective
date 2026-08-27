#!/usr/bin/env python3
"""Generate phase1/colab/manhattan_stage1_ab.ipynb — the Etage 1 notebook.

Model A (zero-shot Llama 3 8B) vs Model B (QLoRA fine-tuned on the 600
real NY Appellate Division criminal appeals), evaluated on the same 400
held-out cases. Runs on a free Colab T4 (16 GB).
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "phase1" / "colab" / \
    "manhattan_stage1_ab.ipynb"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source":
            source.strip().splitlines(keepends=True)}


def code(source: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": source.strip().splitlines(keepends=True)}


cells = []

cells.append(md("""
# MANHATTAN — Étage 1 : le socle
## Modèle A (juge vierge) vs Modèle B (juge qui apprend)

L'expérience fondatrice du **Projet Manhattan du Droit** : un modèle de langage
peut-il prédire l'issue d'un appel criminel réel, et l'apprentissage de 600
affaires passées améliore-t-il cette prédiction ?

**Données** — 1 000 appels criminels réels de la Supreme Court de l'État de
New York, Appellate Division (2015-2025), collectés depuis CourtListener et
le NY Law Reporting Bureau (phase1/ du dépôt
`Vitalcheffe/legally-subjective`). Chaque affaire porte : le dossier vu AVANT
la décision (texte sanitisé — décret retiré, verdict retiré, panel retiré :
règles R1-R5 documentées dans `phase1/dataset/split_report.json`) et le
verdict binaire réel (AFFIRMED vs REVERSED/VACATED) extrait par le pipeline
déterministe vérifié sur échantillon doré.

**Méthode**
- **Modèle A** : Llama 3 8B Instruct, NON entraîné. 400 prédictions
  indépendantes. Le juge qui arrive le premier jour : il a lu la loi, il n'a
  jamais jugé.
- **Modèle B** : le même modèle de base, fine-tuné en QLoRA (rank 16,
  lr 2e-4, 3 époques) sur les 600 affaires d'entraînement AVEC leurs vrais
  verdicts. Puis testé sur les 400 affaires jamais vues.
- **Gate de sortie** : si B bat A de plus de 5 points d'accuracy,
  l'apprentissage fonctionne. Sinon, résultat négatif honnête — les
  résultats négatifs publient aussi.

**Exécution** : `Exécution > Modifier le type d'exécution > T4 GPU`
(~40-70 min au total). Aucun résultat n'est pré-calculé : tout ce que
affiche ce notebook est mesuré sur votre session.
"""))

cells.append(code("""
!pip install -q "transformers==4.44.2" "peft==0.12.0" \\
    "bitsandbytes==0.43.1" "accelerate==0.33.0"
"""))

cells.append(code("""
import json, re, random, os, sys, time
from pathlib import Path

SEED = 20260827                      # même graine que le split
REPO = "https://github.com/Vitalcheffe/legally-subjective.git"

# --- dataset -----------------------------------------------------------
if not Path("legally-subjective").exists():
    !git clone --depth 1 -q {REPO}

def load(name):
    rows = [json.loads(l) for l in
            Path(f"legally-subjective/phase1/dataset/{name}.jsonl")
            .open(encoding="utf-8")]
    for r in rows:                       # label lisible pour le modèle
        r["label"] = "REVERSED" if r["verdict"] == "reversed_vacated" else "AFFIRMED"
    return rows

train, test = load("train"), load("test")
base = sum(r["label"] == "AFFIRMED" for r in test) / len(test)
print(f"train: {len(train)} | test: {len(test)}")
print(f"base rate (toujours prédire AFFIRMED): {base:.4f}")
"""))

cells.append(md("""
## Modèle A — le juge vierge (zero-shot)

Llama 3 8B en 4-bit, aucun entraînement. On lui donne le dossier tel qu'un
lecteur le voit avant la décision, et on demande un verdict.

*Note : `meta-llama/Meta-Llama-3-8B-Instruct` est un modèle à accès
conditionné sur Hugging Face (accepter la licence, puis coller un token dans
le secret `HF_TOKEN` côté Colab). Le miroir `NousResearch/Meta-Llama-3-8B-Instruct`
est identique et non conditionné — utilisé ici par défaut.*
"""))

cells.append(code("""
MODEL_ID = "NousResearch/Meta-Llama-3-8B-Instruct"   # miroir non conditionné
# MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct"   # officiel (nécessite HF_TOKEN)

import torch
from transformers import (AutoModelForCausalLM, AutoTokenizer,
                           BitsAndBytesConfig, set_seed)
set_seed(SEED)
torch.manual_seed(SEED)

bnb = BitsAndBytesConfig(load_in_4bit=True,
                         bnb_4bit_quant_type="nf4",
                         bnb_4bit_compute_dtype=torch.bfloat16)
tok = AutoTokenizer.from_pretrained(MODEL_ID)
tok.pad_token = tok.eos_token
model_a = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, quantization_config=bnb, device_map="auto")
model_a.eval()
print("Modèle A chargé (4-bit NF4).")
"""))

cells.append(code("""
MAX_CHARS = 6000      # limite documentée ; médiane du corpus = 1 164 chars

PROMPT = (
    "You are reading the record of a criminal appeal before the Appellate "
    "Division of the New York State Supreme Court. The deciding panel's "
    "identity has been removed. Based only on this record, predict the "
    "outcome of the appeal. Answer with exactly one word:\\n"
    "AFFIRMED - the lower court judgment will be upheld\\n"
    "REVERSED - the judgment will be reversed, vacated or modified\\n\\n"
    "CASE RECORD:\\n{text}\\n\\nOutcome:"
)

def build_prompt(row):
    return PROMPT.format(text=row["text"][:MAX_CHARS])

@torch.no_grad()
def predict(model, rows, tag):
    out, truncated = [], 0
    for i, row in enumerate(rows):
        if len(row["text"]) > MAX_CHARS:
            truncated += 1
        msgs = [{"role": "user", "content": build_prompt(row)}]
        ids = tok.apply_chat_template(
            msgs, add_generation_prompt=True, return_tensors="pt").to(model.device)
        gen = model.generate(ids, max_new_tokens=6, do_sample=False,
                             pad_token_id=tok.eos_token_id)
        ans = tok.decode(gen[0][ids.shape[1]:], skip_special_tokens=True)
        m = re.search(r"\\b(AFFIRMED|REVERSED)\\b", ans.upper())
        out.append(m.group(1) if m else None)
        if (i + 1) % 50 == 0:
            print(f"  [{tag}] {i+1}/{len(rows)}")
    return out, truncated

t0 = time.time()
pred_a, trunc_a = predict(model_a, test, "A")
print(f"Modèle A : {time.time()-t0:.0f}s | réponses non parsées : "
      f"{sum(p is None for p in pred_a)} | textes tronqués : {trunc_a}")
"""))

cells.append(md("""
## Modèle B — le juge qui apprend (QLoRA)

Fine-tuning LoRA (rank 16, alpha 32, lr 2e-4, 3 époques) sur les 600
affaires d'entraînement avec leurs vrais verdicts. La perte porte uniquement
sur le verdict (les tokens du dossier sont masqués) : le modèle apprend à
décider, pas à réciter.
"""))

cells.append(code("""
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

model_b = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, quantization_config=bnb, device_map="auto")
prepare_model_for_kbit_training(model_b)
lora = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"])
model_b = get_peft_model(model_b, lora)
model_b.print_trainable_parameters()
"""))

cells.append(code("""
LR, EPOCHS, ACC, MAXLEN = 2e-4, 3, 8, 2048

def encode(row):
    msgs = [{"role": "user", "content": build_prompt(row)}]
    prompt = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                     tokenize=False)
    full = prompt + row["label"] + tok.eos_token
    p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
    f_ids = tok(full, add_special_tokens=False)["input_ids"][:MAXLEN]
    labels = [-100] * min(len(p_ids), len(f_ids)) + f_ids[len(p_ids):]
    return {"input_ids": f_ids, "labels": labels}

random.Random(SEED).shuffle(train)
examples = [encode(r) for r in train]

def collate(batch):
    L = max(len(b["input_ids"]) for b in batch)
    pad = tok.eos_token_id
    return {"input_ids": torch.tensor(
                [b["input_ids"] + [pad] * (L - len(b["input_ids"]))
                 for b in batch]),
            "labels": torch.tensor(
                [b["labels"] + [-100] * (L - len(b["labels"]))
                 for b in batch]),
            "attention_mask": torch.tensor(
                [[1] * len(b["input_ids"]) + [0] * (L - len(b["input_ids"]))
                 for b in batch])}

from torch.utils.data import DataLoader
loader = DataLoader(examples, batch_size=1, shuffle=False, collate_fn=collate)
opt = torch.optim.AdamW((p for p in model_b.parameters() if p.requires_grad),
                        lr=LR)

model_b.train()
step = 0
for epoch in range(EPOCHS):
    tot = 0.0
    for i, batch in enumerate(loader):
        batch = {k: v.to(model_b.device) for k, v in batch.items()}
        loss = model_b(**batch).loss
        (loss / ACC).backward()
        tot += loss.item()
        if (i + 1) % ACC == 0:
            opt.step(); opt.zero_grad(); step += 1
            if step % 20 == 0:
                print(f"époque {epoch+1} | étape {step} | perte {tot/ACC:.4f}")
                tot = 0.0
    print(f"— fin époque {epoch+1} —")
model_b.eval()
print("Entraînement terminé.")
"""))

cells.append(code("""
t0 = time.time()
pred_b, trunc_b = predict(model_b, test, "B")
print(f"Modèle B : {time.time()-t0:.0f}s | réponses non parsées : "
      f"{sum(p is None for p in pred_b)} | textes tronqués : {trunc_b}")
"""))

cells.append(md("""
## Le verdict de l'expérience — A vs B
"""))

cells.append(code("""
def evaluate(preds, name):
    ok = sum((p == r["label"]) for p, r in zip(preds, test) if p)
    acc = ok / len(test)
    unparsed = sum(p is None for p in preds)
    # matrice de confusion + biais par catégorie de crime
    cm = {}
    for p, r in zip(preds, test):
        if not p: continue
        k = (r["label"], p)
        cm[k] = cm.get(k, 0) + 1
    by_cat = {}
    for p, r in zip(preds, test):
        if not p: continue
        c = r.get("crime_category", "unstated")
        by_cat.setdefault(c, [0, 0])
        by_cat[c][0] += (p == r["label"]); by_cat[c][1] += 1
    print(f"\\n=== {name} ===")
    print(f"accuracy : {acc:.4f}  (base rate {base:.4f})")
    print(f"non parsés : {unparsed}")
    print("matrice (réel -> prédit) :", cm)
    print("par catégorie de crime :")
    for c, (n, d) in sorted(by_cat.items()):
        print(f"  {c:10s} {n:3d}/{d:<3d} = {n/d:.3f}")
    return {"accuracy": acc, "unparsed": unparsed, "confusion": cm,
            "by_crime_category": {c: {"correct": n, "n": d}
                                  for c, (n, d) in by_cat.items()}}

res_a = evaluate(pred_a, "MODÈLE A — le juge vierge")
res_b = evaluate(pred_b, "MODÈLE B — le juge qui apprend")

delta = (res_b["accuracy"] - res_a["accuracy"]) * 100
print("\\n" + "=" * 60)
print(f"ÉCART B - A : {delta:+.1f} points d'accuracy")
if delta > 5:
    print("GATE PASSÉ — l'apprentissage de cas passés améliore la "
          "prédiction. L'étage 2 (profilage par juge) est fondé.")
else:
    print("GATE NON PASSÉ — résultat négatif honnête : on documente, "
          "les résultats négatiques publient aussi.")
"""))

cells.append(code("""
# --- persistance : rapporter les résultats au dépôt --------------------
report = {
    "experiment": "MANHATTAN stage 1 — Model A (zero-shot) vs Model B (QLoRA)",
    "model": MODEL_ID,
    "seed": SEED,
    "dataset": {"train": len(train), "test": len(test),
                "base_rate_affirmed": round(base, 4),
                "source": "phase1/dataset (NY Appellate Division criminal "
                          "appeals 2015-2025, CourtListener)"},
    "model_a": res_a,
    "model_b": res_b,
    "delta_accuracy_points": round(delta, 1),
    "gate_passed": bool(delta > 5),
}
Path("results_stage1.json").write_text(json.dumps(report, indent=1))
print(json.dumps(report, indent=1)[:1200])
print("\\n→ results_stage1.json écrit dans /content — téléchargez-le et "
      "collez-le dans la conversation (ou ouvrez un PR dans "
      "phase1/results/) pour l'intégrer au dossier de recherche.")
"""))

nb = {
    "nbformat": 4,
    "nbformat_minor": 0,
    "metadata": {
        "colab": {"provenance": [], "gpuType": "T4"},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
        "accelerator": "GPU",
    },
    "cells": cells,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"notebook written: {OUT} ({len(cells)} cells)")
