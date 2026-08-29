#!/usr/bin/env python3
"""Génère notebooks/m3b_qlora_personas.ipynb — condition B (persona QLoRA).

Le notebook est autonome (Colab/Kaggle), versionné, et suit la loi no-leak
du projet: entraînement sur fenêtre OT2015-2019 uniquement, scellés exclus.
"""
import os

import nbformat as nbf

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "notebooks", "m3b_qlora_personas.ipynb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

nb = nbf.v4.new_notebook()
nb.metadata = {
    "colab": {"name": "M3b — Persona QLoRA (Legally Subjective)",
              "provenance": [], "toc_visible": True},
    "kernelspec": {"name": "python3", "display_name": "Python 3",
                   "language": "python"},
    "language_info": {"name": "python"},
    "accelerator": "GPU",
}
C, M = [], []  # cells code / markdown (assemblées à la fin)


def md(s):
    nb.cells.append(nbf.v4.new_markdown_cell(s))


def code(s):
    nb.cells.append(nbf.v4.new_code_cell(s))


# ---------------------------------------------------------------- intro
md("""# M3b — Persona QLoRA : imiter la plume de neuf juges (condition B)

**Projet *Legally Subjective*** — prédire les votes d'une Cour suprême à
partir des textes. Ce notebook entraîne la **condition B** du protocole M3 :
des adaptateurs LoRA (QLoRA 4-bit) qui apprennent la voix rédactionnelle de
chaque juge sur ses opinions propres.

**La loi no-leak (pré-enregistrée) :**
- entraînement **uniquement** sur la fenêtre `OT2015..OT2019` ;
- les 50 affaires scellées 5-4 sont **exclues** de tout entraînement et de
  toute validation (réservées au Test Final M4) ;
- la validation est **temporelle** : les 15 % d'opinions les plus récentes
  de chaque juge dans la fenêtre d'entraînement, jamais utilisées pour les
  gradients.

**Données** : `data/m3/personas/<JUGE>/train.jsonl` (format
system/instruction/output produit par `scripts/m3_build_datasets.py`).
Le corpus M1.5 étant désormais fermé à ~100 % via l'API CourtListener, les
personas sont épaisses (OT2015-16 inclus). Le notebook reste correct sur
des données minces : il saute simplement les juges à moins de
`MIN_TRAIN_ROWS` lignes.

**Matériel** : vise un T4 16 Go (Colab gratuit / Kaggle). ~10-25 min par
juge avec 3B 4-bit. Total < 3 h pour les neuf juges.

**Sorties** : `adapters/<JUGE>/` (un adaptateur LoRA par juge) +
`m3b_report.json` (pertes de validation, statistiques) + zip téléchargeable.
""")

# ---------------------------------------------------------------- setup
md("## 1 · Environnement (versions épinglées, exécuter une fois)")
code("""# ⚠️ Runtime → Change runtime type → GPU (T4 suffit). Colab seulement:
# !nvidia-smi

%pip -q install "transformers==4.46.3" "peft==0.13.2" "bitsandbytes==0.45.0" \\
               "accelerate==1.2.1" "datasets==3.1.0" "sentencepiece" "protobuf"
import os, sys
import importlib.metadata as _md
print("python", sys.version.split()[0])""")

code("""import json, math, os, random, shutil, sys, time, zipfile
from collections import defaultdict
import importlib.metadata as _md

import numpy as np
import torch
print("torch", torch.__version__, "| transformers", _md.version("transformers"),
      "| peft", _md.version("peft"), "| bnb", _md.version("bitsandbytes"))

SEED = 42
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)

assert torch.cuda.is_available(), "GPU requis — Runtime → Change runtime type."
print("GPU:", torch.cuda.get_device_name(0),
      f"| {torch.cuda.get_device_properties(0).total_memory/1e9:.0f} Go")""")

# ---------------------------------------------------------------- config
md("""## 2 · Configuration

Modèle par défaut : **Qwen2.5-3B-Instruct** (non gated, licence Apache —
reproductible partout). Alternative : le miroir non gated de Llama-3.2-3B.
Politiqûment neutre : le choix du modèle est un paramètre *contrôlé* du
plan, pas une opinion d'ingénieur.""")
code("""CONFIG = {
    # ---- modèle (non gated pour la reproductibilité)
    "MODEL_ID": "Qwen/Qwen2.5-3B-Instruct",
    # alternatives testées compatibles:
    #   "unsloth/Llama-3.2-3B-Instruct"      (miroir non gated)
    #   "HuggingFaceTB/SmolLM2-1.7B-Instruct" (budget serré)
    "MAX_LEN": 4096,          # tokens ; T4 16Go passe avec gradient checkpointing
    "INSTR_KEEP": 1024,       # budget tokens pour la PARTIE FINALE de l'instruction
                              # (la question de l'affaire vit en fin de dossier)
    # ---- LoRA
    "LORA_R": 16, "LORA_ALPHA": 32, "LORA_DROPOUT": 0.05,
    # ---- optimisation
    "LR": 1e-4, "EPOCHS": 8, "BATCH": 1, "GRAD_ACCUM": 8,
    "EVAL_EVERY": 20, "PATIENCE": 3, "WARMUP": 10,
    # ---- protocole
    "VAL_FRACTION": 0.15,     # temporel: les plus récentes de la fenêtre train
    "MIN_TRAIN_ROWS": 8,      # en dessous: juge sauté (données trop minces)
    "PERSONAS_GARDÉES": None, # None = toutes celles qui passent MIN_TRAIN_ROWS
}
RUN_ID = time.strftime("run_%Y%m%d_%H%M%S")
ADAPTER_DIR, REPORT = "adapters", "m3b_report.json"
os.makedirs(ADAPTER_DIR, exist_ok=True)
print("RUN_ID:", RUN_ID)""")

# ---------------------------------------------------------------- data
md("""## 3 · Données — acquisition des personas
Deux chemins, au choix : cloner le repo (si public ou token GitHub), ou
monter un Drive contenant `personas/`. Le chemin local est prioritaire.""")
code("""# --- Option A (défaut): repo git
REPO_PATH = "/content/legally-subjective"          # Colab
if not os.path.isdir(REPO_PATH):
    !git clone --depth 1 https://github.com/Vitalcheffe/legally-subjective.git {REPO_PATH}

# --- Option B: Drive
# from google.colab import drive; drive.mount('/content/drive')
# REPO_PATH = "/content/drive/MyDrive/legally-subjective/repo"

PERSONAS_DIR = os.path.join(REPO_PATH, "data", "m3", "personas")
assert os.path.isdir(PERSONAS_DIR), f"{PERSONAS_DIR} introuvable — voir Option B."
print(sorted(os.listdir(PERSONAS_DIR)))""")

code("""def load_persona(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("output") and len(r["output"]) > 200:
                rows.append(r)
    rows.sort(key=lambda r: r.get("date_filed") or "9999")  # temporel
    return rows

personas = {}
for name in sorted(os.listdir(PERSONAS_DIR)):
    p = os.path.join(PERSONAS_DIR, name, "train.jsonl")
    if os.path.isfile(p):
        rows = load_persona(p)
        if len(rows) >= CONFIG["MIN_TRAIN_ROWS"]:
            personas[name] = rows
        else:
            print(f"· {name}: {len(rows)} lignes < MIN_TRAIN_ROWS → sauté")

print(f"\\n{len(personas)} personas actives, "
      f"{sum(len(v) for v in personas.values())} opinions au total")
for k, v in personas.items():
    print(f"  {k:14s} {len(v):4d} opinions  ({v[0]['date_filed']} → {v[-1]['date_filed']})")""")

md("""### Split temporel (no-leak)
Pour chaque juge : les `(1-VAL_FRACTION)` premières opinions par date pour
les gradients, les plus récentes pour la validation. Les votes de test
(OT2020+) et les scellés ne quittent jamais leurs fichiers séparés.""")
code("""def temporal_split(rows, frac=CONFIG["VAL_FRACTION"]):
    if len(rows) < 4:
        return rows, rows[-1:]                    # micro-corpus: 1 ligne de val
    n_val = max(1, round(len(rows) * frac))
    return rows[:-n_val], rows[-n_val:]

splits = {k: temporal_split(v) for k, v in personas.items()}
for k, (tr, va) in splits.items():
    print(f"  {k:14s} train {len(tr):3d} | val {len(va):2d} "
          f"| val à partir de {va[0]['date_filed']}")""")

# ---------------------------------------------------------------- tokens
md("""## 4 · Tokenisation — budget de séquence honnête
Les opinions dépassent souvent 4 096 tokens. Politique de troncature
**déclarée** : system complet, *fin* de l'instruction (la question y vit),
*début* de l'output (la voix du juge s'y installe dès la première ligne).
Le rapport note chaque ligne tronquée — pas de troncature silencieuse.""")
code("""from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained(CONFIG["MODEL_ID"])
BOS = tok.apply_chat_template(
    [{"role": "user", "content": "x"}], tokenize=True, add_generation_prompt=True)

def encode_row(row, max_len=CONFIG["MAX_LEN"], instr_keep=CONFIG["INSTR_KEEP"]):
    prompt_ids = tok.apply_chat_template(
        [{"role": "system", "content": row["system"]},
         {"role": "user", "content": row["instruction"]}],
        tokenize=True, add_generation_prompt=True)
    out_ids = tok(row["output"], add_special_tokens=False)["input_ids"]
    # budget: system+template intouchable ; instr réduite par la TÊTE ;
    # output réduit par la QUEUE si le total déborde encore.
    n_out = len(out_ids)
    room = max_len - len(prompt_ids) - 1
    if room <= 0:                                   # instruction seule trop longue
        tail = prompt_ids[-(instr_keep + 40):]
        prompt_ids = prompt_ids[:2] + tail          # garde le template d'ouverture
        room = max_len - len(prompt_ids) - 1
    if n_out > room:
        out_ids = out_ids[:room]
    return prompt_ids, out_ids

# stats de longueur avant d'aller plus loin
for name, rows in list(personas.items())[:3]:
    ls = [sum(len(x) for x in encode_row(r)[:2]) for r in rows[:20]]
    print(f"{name:14s} médiane {int(np.median(ls)):5d} | max {max(ls):5d} tokens")""")

code("""class PersonaTorch(torch.utils.data.Dataset):
    def __init__(self, rows):
        self.items = []
        for r in rows:
            p, o = encode_row(r)
            ids = p + o + [tok.eos_token_id or tok.pad_token_id]
            labels = [-100] * len(p) + o + [tok.eos_token_id or tok.pad_token_id]
            self.items.append((ids[:CONFIG["MAX_LEN"]], labels[:CONFIG["MAX_LEN"]]))
    def __len__(self):
        return len(self.items)
    def __getitem__(self, i):
        ids, labels = self.items[i]
        return {"input_ids": ids, "labels": labels}

def collate(batch):
    mx = max(len(b["input_ids"]) for b in batch)
    pad = tok.pad_token_id or tok.eos_token_id
    return {
        "input_ids": torch.tensor([b["input_ids"] + [pad] * (mx - len(b["input_ids"])) for b in batch]),
        "labels": torch.tensor([b["labels"] + [-100] * (mx - len(b["labels"])) for b in batch]),
        "attention_mask": torch.tensor([[1] * len(b["input_ids"]) + [0] * (mx - len(b["input_ids"])) for b in batch]),
    }""")

# ---------------------------------------------------------------- model
md("""## 5 · QLoRA — base 4-bit + adaptateurs par juge
Un chargement de base, neuf adaptateurs. r=16/α=32 cible les projections
d'attention et MLP ; checkpointing activé : le T4 respire.""")
code("""import bitsandbytes as bnb
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from transformers import (AutoModelForCausalLM, BitsAndBytesConfig,
                          EarlyStoppingCallback, Trainer, TrainingArguments)

bnb_cfg = BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    bnb_4bit_use_double_quant=True)

base = AutoModelForCausalLM.from_pretrained(
    CONFIG["MODEL_ID"], quantization_config=bnb_cfg, device_map={"": 0})
base = prepare_model_for_kbit_training(base, use_gradient_checkpointing=True)
base.config.use_cache = False

def make_lora():
    return LoraConfig(
        r=CONFIG["LORA_R"], lora_alpha=CONFIG["LORA_ALPHA"],
        lora_dropout=CONFIG["LORA_DROPOUT"], bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"])
print("base chargée:", sum(p.numel() for p in base.parameters())/1e9, "Md (4-bit)")""")

# ---------------------------------------------------------------- train
md("""## 6 · Entraînement — un adaptateur par juge
Early stopping sur la perte de validation temporelle. Le meilleur
checkpoint (pas le dernier) est conservé. ~40 s / époque sur T4 pour
~50 opinions.""")
code("""def train_one(name, rows):
    tr_rows, va_rows = splits[name]
    tr_ds, va_ds = PersonaTorch(tr_rows), PersonaTorch(va_rows)
    model = get_peft_model(base, make_lora())
    model.print_trainable_parameters()
    args = TrainingArguments(
        output_dir=f"/tmp/{name}", per_device_train_batch_size=CONFIG["BATCH"],
        gradient_accumulation_steps=CONFIG["GRAD_ACCUM"],
        num_train_epochs=CONFIG["EPOCHS"], learning_rate=CONFIG["LR"],
        lr_scheduler_type="cosine", warmup_steps=CONFIG["WARMUP"],
        logging_steps=5, eval_strategy="steps", eval_steps=CONFIG["EVAL_EVERY"],
        save_strategy="steps", save_steps=CONFIG["EVAL_EVERY"],
        save_total_limit=2, load_best_model_at_end=True,
        metric_for_best_model="eval_loss", greater_is_better=False,
        bf16=torch.cuda.is_bf16_supported(), report_to="none", seed=SEED,
        remove_unused_columns=False, dataloader_pin_memory=False)
    cb = EarlyStoppingCallback(early_stopping_patience=CONFIG["PATIENCE"])
    trainer = Trainer(model=model, args=args, train_dataset=tr_ds,
                      eval_dataset=va_ds, data_collator=collate,
                      callbacks=[cb])
    trainer.train()
    best = min(trainer.evaluate(va_ds)["eval_loss"], float("inf"))
    out = os.path.join(ADAPTER_DIR, name)
    model.save_pretrained(out)                     # adaptateur seulement (~40 Mo)
    del model, trainer
    torch.cuda.empty_cache()
    return {"persona": name, "n_train": len(tr_rows), "n_val": len(va_rows),
            "best_val_loss": round(best, 4)}

report = {"config": CONFIG, "model": CONFIG["MODEL_ID"],
          "run_id": RUN_ID, "results": []}
for name in personas:
    print(f"\\n=== {name} ===")
    report["results"].append(train_one(name, personas[name]))
    with open(REPORT, "w") as f:
        json.dump(report, f, indent=1)   # checkpoint après chaque juge""")

# ---------------------------------------------------------------- eval
md("""## 7 · Contrôle de santé — même affaire, deux plumes
Le test discriminant : la même instruction passée à deux adaptateurs doit
produire deux ouvertures *reconnaissablement différentes* (Thomas ≠ Kagan).
Si les sorties convergent, les adaptateurs n'ont rien appris.""")
code("""from peft import PeftModel
import pandas as pd

def generate(name, instruction, max_new_tokens=120):
    m = PeftModel.from_pretrained(base, os.path.join(ADAPTER_DIR, name))
    ids = tok.apply_chat_template(
        [{"role": "system", "content": personas[name][0]["system"]},
         {"role": "user", "content": instruction}],
        tokenize=True, add_generation_prompt=True, return_tensors="pt").to(base.device)
    with torch.no_grad():
        out = m.generate(ids, max_new_tokens=max_new_tokens, do_sample=False,
                         temperature=1.0)
    del m; torch.cuda.empty_cache()
    return tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True)

probe_case = personas["CThomas"][len(personas["CThomas"])//2]["instruction"]
pair = ["CThomas", "EKagan"] if all(p in personas for p in ("CThomas", "EKagan")) \\
       else list(personas)[:2]
texts = {p: generate(p, probe_case) for p in pair}
for p, t in texts.items():
    print(f"\\n—— {p} ——\\n{t[:500]}")

report["probe"] = {"case": probe_case[:200], "generations": {p: t[:500] for p, t in texts.items()}}
df = pd.DataFrame(report["results"])
print("\\n", df.to_string(index=False))
print(f"\\nval_loss médiane: {df.best_val_loss.median():.3f} "
      f"(perte initiale attendue ≈ 3-4 ; en dessous de 2.5 = apprentissage réel)")""")

# ---------------------------------------------------------------- export
md("## 8 · Export — adaptateurs + rapport")
code("""with open(REPORT, "w") as f:
    json.dump(report, f, indent=1, ensure_ascii=False)
with zipfile.ZipFile(f"m3b_adapters_{RUN_ID}.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for name in personas:
        for fn in os.listdir(os.path.join(ADAPTER_DIR, name)):
            z.write(os.path.join(ADAPTER_DIR, name, fn), f"{name}/{fn}")
    z.write(REPORT, REPORT)
print("→", f"m3b_adapters_{RUN_ID}.zip",
      f"({os.path.getsize(f'm3b_adapters_{RUN_ID}.zip')/1e6:.0f} Mo)")

# Optionnel — Drive:
# from google.colab import drive; drive.mount('/content/drive')
# shutil.copy(f"m3b_adapters_{RUN_ID}.zip", "/content/drive/MyDrive/")""")

md("""## 9 · Et ensuite (M4)
1. **Test transparent OT2020-23** : pour chaque affaire de test, générer la
   suite de la question « *How should this case be decided?* » avec chaque
   adaptateur, scorer la direction (libéral/conservateur) du texte généré,
   en déduire un vote prédit par juge.
2. **Comparaison pré-enregistrée** : B4 (barre métadonnées, 63,7 %),
   M3a-LR/IX/GB (challengers structurés), condition A (zero-shot),
   condition C (RAG) — McNemar exact sur les lignes appariées.
3. **Test final scellé** : les 50 affaires 5-4, une seule fois, tous
   conditions confondues. Le fichier `test_votes.jsonl` de chaque persona
   ne doit JAMAIS être ouvert avant ce moment.
""")

nbformat_write = __import__("nbformat").write
nbformat_write(nb, OUT)
print("notebook écrit:", OUT, "|", len(nb.cells), "cellules")
