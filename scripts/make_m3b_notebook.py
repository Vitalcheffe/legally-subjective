#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Génère notebooks/m3b_qlora_personas.ipynb (v2, architecture durable).

La v1 reprenait au niveau « juge entier » avec zip téléversé à la main —
rédhibitoire pour des sessions Colab d'une heure face à des juges de 4-9 h.
La v2 est générée ici depuis une source unique (ce script) :

  §2bis  montage Drive + clone + état brut affiché dès le boot ;
  §5bis  empreinte scientifique + reprise AUTOMATIQUE (rien à téléverser) ;
  §6     entraînement repreneur intra-juge (VRAI resume Trainer) ;
  §7-§8  audits + export final automatiques, idempotents ;
  §8bis  RESET TOTAL à double confirmation.

Le code de gestion d'état vit dans scripts/m3b_state.py (repo) — le
notebook l'importe depuis le clone ; il est testé par
test_m3b_state.py (98 PASS) et test_m3b_resume_cpu.py (21 PASS, vrai
transformers/peft — c'est ce test qui a révélé le bug transformers
4.46.3/torch≥2.6 et imposé le pin 4.49.0).

Usage : python scripts/make_m3b_notebook.py   (régénère le .ipynb)
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "notebooks",
                   "m3b_qlora_personas.ipynb")

C = []                                    # (type, source)


def md(src):
    C.append(("markdown", src.strip()))


def code(src):
    C.append(("code", src.strip()))


# ------------------------------------------------------------------ titre --
md("""
# M3b — Persona QLoRA : imiter la plume de sept juges (condition B)

**Projet *Legally Subjective*** — prédire les votes d'une Cour suprême à
partir des textes. Ce notebook entraîne la **condition B** du protocole M3 :
des adaptateurs LoRA (QLoRA 4-bit) qui apprennent la voix rédactionnelle de
chaque juge sur ses opinions propres.

**Architecture « indestructible »** — l'entraînement est conçu pour être
interrompu à TOUT instant (session d'une heure, quota, onglet fermé, coupure
réseau) sans perte substantielle de travail :

- toute la vérité de l'expérience vit dans **un seul dossier Google Drive**
  (`legally-subjective-m3b/`, créé automatiquement) — jamais dans le
  filesystem éphémère de Colab ;
- un **checkpoint durable** est promu sur Drive tous les `SAVE_STEPS` pas,
  avec atomicité garantie (fichiers d'abord, manifeste en dernier) ;
- à chaque nouvelle session, la reprise est **100 % automatique** : rien à
  téléverser, rien à fusionner, rien à choisir — rouvrir ce notebook depuis
  son lien GitHub et tout exécuter ;
- après `SOFT_MINUTES` minutes d'entraînement, **arrêt propre** (sauvegarde
  du pas courant puis stop) : la mort brutale devient l'exception ;
- un juge n'est déclaré « terminé » qu'après **rechargement + vérification**
  de son adaptateur final sur Drive.

**La loi no-leak (pré-enregistrée)** : entraînement uniquement sur la fenêtre
`OT2015..OT2019` ; les 50 affaires scellées 5-4 sont exclues de tout
entraînement et de toute validation (réservées au Test Final M4) ; la
validation est **temporelle** (les 15 % d'opinions les plus récentes de
chaque juge, jamais utilisées pour les gradients).

**Mode d'emploi** : *Runtime → Change runtime type → GPU (T4)* → **Tout
exécuter** (Ctrl+F9) → autoriser Google Drive dans la fenêtre qui s'ouvre →
laisser travailler. Quand la session meurt : rouvrir le **même lien GitHub**,
recommencer. C'est tout.
""")

# ------------------------------------------------------------------ §1 -----
md("""
## 1 · Environnement (versions épinglées, exécuter une fois)
""")

code("""
# ⛔ GARDE GPU AVANT TOUT — 2 secondes au lieu de 2 minutes de pip pour
# apprendre qu'il faut changer le runtime. torch est préinstallé sur Colab.
try:
    import torch as _torch_probe
    assert _torch_probe.cuda.is_available(), (
        "GPU requis — ce runtime est CPU-ONLY.\\n"
        "  → Runtime → Change runtime type → T4 GPU\\n"
        "  → puis Runtime → Run all (la machine redémarre : normal,\\n"
        "    rien n'est perdu — rien n'a encore été fait à ce stade).")
    print("GPU visible :", _torch_probe.cuda.get_device_name(0))
    del _torch_probe
except ImportError:
    pass          # torch absent : la garde de la cellule suivante prend le relais

# transformers==4.49.0 (et PAS 4.46.3) : à partir de torch 2.6, le chargement
# de rng_state.pth au resume_from_checkpoint échoue par défaut
# (weights_only=True) — la REPRISE de checkpoint est cassée en 4.46.3 sur
# les torch récents. Bug vérifié par test réel d'intégration CPU ; 4.49.0
# corrige. Ne pas changer ce pin sans re-tester scripts/test_m3b_resume_cpu.py.
# bitsandbytes: PLANCHER >=0.47.0,<0.51 — la 0.45.0 importe triton.ops sans
# garde, module supprimé dans triton>=3.2 (torch 2.11, python 3.13 sur
# Colab 2026) → ModuleNotFoundError à l'import.
# NB : les lignes « ERROR: pip's dependency resolver… » pointant gradio ou
# diffusers (préinstallés Colab) sont ATTENDUES et sans effet ici — paquets
# non utilisés par M3b.
%pip -q install "transformers==4.49.0" "peft==0.13.2" "bitsandbytes>=0.47.0,<0.51" \
               "accelerate==1.2.1" "datasets==3.1.0" "sentencepiece" "protobuf"
import os, sys
import importlib.metadata as _md
print("python", sys.version.split()[0])
""")

code("""
import json, math, os, random, shutil, subprocess, sys, time, zipfile
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
      f"| {torch.cuda.get_device_properties(0).total_memory/1e9:.0f} Go")
""")

# ------------------------------------------------------------------ §2 -----
md("""
## 2 · Configuration

Modèle par défaut : **Qwen2.5-3B-Instruct** (non gated, licence Apache —
reproductible partout). Politiquement neutre : le choix du modèle est un
paramètre *contrôlé* du plan, pas une opinion d'ingénieur.

Les clés `SAVE_STEPS` et `SOFT_MINUTES` sont **opérationnelles** (et
volontairement hors empreinte scientifique) : elles règlent le rythme de
sauvegarde et l'arrêt propre, pas l'expérience. Les modifier en cours de
route ne compromet rien — tout le reste, lui, doit rester strictement
identique d'une session à l'autre (contrôlé en §5bis).
""")

code("""
CONFIG = {
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
    # ---- opérationnel (HORS empreinte scientifique — ajustable librement)
    "SAVE_STEPS": 10,         # checkpoint → Drive tous les 10 pas optimiseur
                              # (≈ 16-37 min de travail T4) : perte maximale
                              # en cas de coupure brutale entre deux saves
    "SOFT_MINUTES": 55,       # arrêt PROPRE après ~55 min d'entraînement ;
                              # si vos sessions vivent nettement plus, monter
                              # la valeur (ex. 240) accélère le global
}
RUN_ID = time.strftime("run_%Y%m%d_%H%M%S")
print("RUN_ID:", RUN_ID)
print(f"durabilité : checkpoint Drive tous les {CONFIG['SAVE_STEPS']} pas | "
      f"arrêt propre à {CONFIG['SOFT_MINUTES']} min")
""")

# ------------------------------------------------------------------ §2bis --
md("""
## 2bis · Le stockage durable — Google Drive

**C'est le cœur de la reprise.** Le filesystem de Colab meurt avec la
session ; Google Drive survit. Toute la vérité de l'expérience vit dans un
seul dossier Drive, créé automatiquement au premier passage :

    MyDrive/legally-subjective-m3b/
      state.json                       manifeste — source de vérité unique
      checkpoints/<juge>/ckpt-<pas>/   points de reprise (hash vérifiés)
      adapters/<juge>/                 adaptateurs finaux, vérifiés avant « done »
      final/m3b_adapters_final.zip     export final (le runner M4 le lit seul)
      log.txt                          journal lisible

**Ne jamais renommer, déplacer ou supprimer ce dossier.** Aucun zip à
conserver, aucune fusion à faire : le système gère sa propre continuité.

Cette cellule clone aussi le dépôt (code + données) : toujours frais, donc
toujours aligné sur ce que vous venez d'ouvrir via le lien GitHub.
""")

code("""
# --- montage Drive : sans stockage durable, aucun entraînement ne démarre --
try:
    from google.colab import drive
    drive.mount("/content/drive")
except Exception as e:
    raise RuntimeError(
        "Montage Drive impossible — sans stockage durable, l'entraînement "
        "ne démarre pas (tout serait perdu à la première coupure). "
        "Autoriser la fenêtre Google qui s'ouvre, puis relancer cette cellule."
    ) from e

DRIVE_ROOT = "/content/drive/MyDrive/legally-subjective-m3b"

# --- dépôt : clone frais (notebook ouvert via le lien GitHub = même code) ---
REPO_PATH = "/content/legally-subjective"
if not os.path.isdir(REPO_PATH):
    !git clone --depth 1 https://github.com/Vitalcheffe/legally-subjective.git {REPO_PATH}
HEAD = subprocess.run(["git", "-C", REPO_PATH, "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
print("dépôt :", HEAD[:12])

# --- gestion d'état durable (scripts/m3b_state.py du dépôt) -----------------
sys.path.insert(0, os.path.join(REPO_PATH, "scripts"))
import m3b_state as M3B

# --- environnement d'exécution CONSIGNÉ (lignage : qui a entraîné, où,
#     avec quelles versions — aucune de ces valeurs n'est inventée) --------
ENV_INFO = {"python": sys.version.split()[0], "torch": torch.__version__,
            "transformers": _md.version("transformers"),
            "peft": _md.version("peft"),
            "bitsandbytes": _md.version("bitsandbytes"),
            "accelerate": _md.version("accelerate"),
            "gpu": (torch.cuda.get_device_name(0)
                    if torch.cuda.is_available() else "cpu"),
            "gpu_mem_gb": (round(
                torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
                if torch.cuda.is_available() else 0)}
print("environnement :", ENV_INFO["gpu"], "|", ENV_INFO["torch"],
      "|", ENV_INFO["transformers"])

# --- scellé M4 re-vérifié DANS LE CLONE : l'entraînement ne démarre
#     jamais dans un état où la chaîne de scellement serait cassée --------
SEAL_CHECK = M3B.seal_check_from_repo(REPO_PATH)
assert SEAL_CHECK.get("ok") is True, (
    "scellé M4 non vérifiable dans le clone — REFUS de démarrer. "
    "Le scellé doit être intègre PENDANT l'entraînement (protocole). "
    f"Diagnostic : {SEAL_CHECK}")
print("scellé M4 intègre dans le clone :",
      str(SEAL_CHECK.get("sealed_sha256"))[:16] + "…",
      f"({SEAL_CHECK.get('n_cases')} affaires scellées)")

# --- statut brut, en lecture seule (la vraie reprise se fait en §5bis) ------
_p = os.path.join(DRIVE_ROOT, "state.json")
if os.path.exists(_p):
    try:
        _es = M3B.ExpState(DRIVE_ROOT)
        _es.state = json.load(open(_p, encoding="utf-8"))
        print(_es.summary())
    except Exception:
        print("state.json présent mais illisible — le §5bis donnera le diagnostic")
else:
    print("AUCUNE EXPÉRIENCE COMMENCÉE — le dossier Drive sera créé en §5bis")
""")

# ------------------------------------------------------------------ §3 -----
md("""
## 3 · Données — acquisition des personas

Les personas viennent du clone fait en §2bis :
`data/m3/personas/<JUGE>/train.jsonl` (format system/instruction/output
produit par `scripts/m3_build_datasets.py`, 477 lignes au total).
""")

code("""
PERSONAS_DIR = os.path.join(REPO_PATH, "data", "m3", "personas")
assert os.path.isdir(PERSONAS_DIR), \
    f"{PERSONAS_DIR} introuvable — le clone du §2bis a-t-il réussi ?"
print(sorted(os.listdir(PERSONAS_DIR)))
""")

code("""
def load_persona(path):
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
    print(f"  {k:14s} {len(v):4d} opinions  ({v[0]['date_filed']} → {v[-1]['date_filed']})")
""")

md("""
### Split temporel (no-leak)
Pour chaque juge : les `(1-VAL_FRACTION)` premières opinions par date pour
les gradients, les plus récentes pour la validation. Les votes de test
(OT2020+) et les scellés ne quittent jamais leurs fichiers séparés.
""")

code("""
def temporal_split(rows, frac=CONFIG["VAL_FRACTION"]):
    if len(rows) < 4:
        return rows, rows[-1:]                    # micro-corpus: 1 ligne de val
    n_val = max(1, round(len(rows) * frac))
    return rows[:-n_val], rows[-n_val:]

splits = {k: temporal_split(v) for k, v in personas.items()}
for k, (tr, va) in splits.items():
    print(f"  {k:14s} train {len(tr):3d} | val {len(va):2d} "
          f"| val à partir de {va[0]['date_filed']}")
""")

# ------------------------------------------------------------------ §4 -----
md("""
## 4 · Tokenisation — budget de séquence honnête
Les opinions dépassent souvent 4 096 tokens. Politique de troncature
**déclarée** : system complet, *fin* de l'instruction (la question y vit),
*début* de l'output (la voix du juge s'y installe dès la première ligne).
Le rapport note chaque ligne tronquée — pas de troncature silencieuse.
""")

code("""
from transformers import AutoTokenizer

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
    print(f"{name:14s} médiane {int(np.median(ls)):5d} | max {max(ls):5d} tokens")
""")

code("""
class PersonaTorch(torch.utils.data.Dataset):
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
    }
""")

# ------------------------------------------------------------------ §5 -----
md("""
## 5 · QLoRA — base 4-bit + adaptateurs par juge
Un chargement de base, sept adaptateurs. r=16/α=32 cible les projections
d'attention et MLP ; checkpointing activé : le T4 respire.
""")

code("""
import bitsandbytes as bnb
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from transformers import (AutoModelForCausalLM, BitsAndBytesConfig,
                          Trainer, TrainingArguments)

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
print("base chargée:", sum(p.numel() for p in base.parameters())/1e9, "Md (4-bit)")
""")

# ------------------------------------------------------------------ §5bis --
md("""
## 5bis · Empreinte scientifique + reprise AUTOMATIQUE

L'empreinte fige la **configuration scientifique** + les **données** + la
**graine**. Reprendre avec une empreinte différente = refus explicite (on ne
mélange pas deux expériences). Les clés opérationnelles (`SAVE_STEPS`,
`SOFT_MINUTES`) sont volontairement hors empreinte.

C'est ici que la reprise se joue : **il n'y a rien à téléverser**. Si un
état cohérent existe sur le Drive, il est chargé ; sinon l'expérience
démarre vierge. Un état incohérent (manifeste illisible avec checkpoints
présents) est un REFUS, jamais un redémarrage silencieux.
""")

code("""
# --- §5bis · empreinte + état ------------------------------------------------
import hashlib
_fp_cfg = M3B.fingerprint_of(CONFIG)          # clés scientifiques seules
_fp_dat, _fp_parts = M3B.data_fingerprint(PERSONAS_DIR, list(personas))
FINGERPRINT = hashlib.sha256(json.dumps(
    {"cfg": _fp_cfg, "data": _fp_dat, "seed": SEED},
    sort_keys=True).encode()).hexdigest()

STATE = M3B.ExpState(DRIVE_ROOT)
MODE, MSG = STATE.load_or_init(FINGERPRINT,
                               {"config": _fp_cfg, "data": _fp_dat},
                               SEED, HEAD, list(personas), run_id=RUN_ID,
                               env=ENV_INFO, seal=SEAL_CHECK)
print(MSG)
assert MODE != "error", ("État incompatible — ne rien contourner : envoyer "
                         "ce message tel quel (règle d'or n°2).")
if not STATE.state["sessions"] or \\
        STATE.state["sessions"][-1].get("run_id") != RUN_ID:
    STATE.state["sessions"].append({"run_id": RUN_ID, "head": HEAD[:12],
                                    "resumed": [], "trained": []})
    STATE.save()

# journal d'événements + preuve de démarrage (sorties RÉELLES, jamais
# fabriquées — elles complètent le manifeste, ne le remplacent pas)
_ev, _ev_partial = STATE.read_events()
print(f"journal d'événements : {len(_ev)} enregistrements"
      + (" — dernière ligne incomplète ignorée (crash)" if _ev_partial else ""))
M3B.evidence_dump(DRIVE_ROOT, "démarrage-session",
                   MSG + "\\njournal : " + str(len(_ev)) + " événements\\n",
                   note="état réel au démarrage de la session",
                   run_id=RUN_ID, head=HEAD)
print("répertoire durable :", DRIVE_ROOT)
""")

# ------------------------------------------------------------------ §6 -----
md("""
## 6 · Entraînement REPRENEUR (le cœur de l'architecture)

Pour chaque juge non terminé :

1. son dernier checkpoint **durable** est rapatrié du Drive vers le local,
   hash vérifié (corruption → génération précédente) ;
2. l'entraînement reprend là où il s'était arrêté — **vrai** resume Trainer :
   poids, optimizer, scheduler et RNG restaurés ;
3. tous les `SAVE_STEPS` pas, le checkpoint est **promu sur Drive**
   (copie atomique, manifeste en dernier) ;
4. au bout de `SOFT_MINUTES` minutes : **arrêt propre** — le pas courant est
   sauvegardé, puis tout s'arrête. Si le runtime vit encore, relancer cette
   cellule rouvre une nouvelle fenêtre, sans rien perdre ;
5. juge terminé : le **meilleur** checkpoint (pas le dernier) devient
   l'adaptateur final — promu sur Drive, **rechargé et vérifié** (forward
   aux logits finis) avant que le juge soit déclaré « done ».

Une coupure à n'importe quel instant coûte au plus `SAVE_STEPS` pas.
Une erreur sur un juge est consignée et le juge suivant est tenté — le juge
en échec sera repris (depuis son checkpoint) à la session suivante.
""")

code("""
# --- §6 · entraînement repreneur ---------------------------------------------
import time as _time
import traceback

CKPT_LOCAL = "/content/ckpt" if os.path.exists("/content") else "./ckpt"
budget_session = M3B.TimeBudgetCallback(CONFIG["SOFT_MINUTES"])

def train_one(name):
    tr_rows, va_rows = splits[name]
    tr_ds, va_ds = PersonaTorch(tr_rows), PersonaTorch(va_rows)
    model = get_peft_model(base, make_lora())
    local_out = os.path.join(CKPT_LOCAL, name)
    resume_from = STATE.restore_ckpt_local(name, local_out)
    if resume_from:
        print(f"  · reprise depuis le pas {STATE.step(name)} (ckpt vérifié)")
    elif STATE.step(name) == 0:
        print("  · départ de zéro")
    else:
        print("  · aucun ckpt récupérable — redépart consigné au journal")
    # ---- statistiques réelles de l'expérience (lignage §XI) ---------------
    _j = STATE.j(name)
    if _j.get("params") is None:
        _j["params"] = {"trainable": int(sum(p.numel() for p in
                                                model.parameters()
                                                if p.requires_grad)),
                        "total": int(sum(p.numel() for p in
                                          model.parameters()))}
    if _j.get("n_tokens_train") is None:
        _j["n_tokens_train"] = int(sum(len(it[0]) for it in tr_ds.items))
    _j["n_train"], _j["n_val"] = len(tr_rows), len(va_rows)
    STATE.save()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    args = TrainingArguments(
        output_dir=local_out,
        per_device_train_batch_size=CONFIG["BATCH"],
        gradient_accumulation_steps=CONFIG["GRAD_ACCUM"],
        num_train_epochs=CONFIG["EPOCHS"], learning_rate=CONFIG["LR"],
        lr_scheduler_type="cosine", warmup_steps=CONFIG["WARMUP"],
        logging_steps=5, eval_strategy="steps", eval_steps=CONFIG["EVAL_EVERY"],
        save_strategy="steps", save_steps=CONFIG["SAVE_STEPS"],
        save_total_limit=None, load_best_model_at_end=False,
        bf16=torch.cuda.is_bf16_supported(), report_to="none", seed=SEED,
        remove_unused_columns=False, dataloader_pin_memory=False)
    trainer = Trainer(model=model, args=args, train_dataset=tr_ds,
                      eval_dataset=va_ds, data_collator=collate,
                      callbacks=[M3B.DriveSyncCallback(STATE, name),
                                 budget_session,
                                 M3B.StatefulEarlyStopping(
                                     STATE, name, CONFIG["PATIENCE"])])
    STATE.set_status(name, "training"); STATE.save()
    STATE.event("START", judge=name, from_step=STATE.step(name))
    _t0 = _time.time()
    trainer.train(resume_from_checkpoint=resume_from)
    final_step, fresh = trainer.state.global_step, None
    _j = STATE.j(name)
    _j["wall_seconds"] = round((_j.get("wall_seconds") or 0)
                              + (_time.time() - _t0), 1)
    _j["steps_total"] = int(trainer.state.max_steps)
    if torch.cuda.is_available():
        _j["max_mem_gb"] = round(
            torch.cuda.max_memory_allocated() / 1e9, 2)
    STATE.save()
    if STATE.step(name) == 0:          # juge trop court pour un seul save
        fresh = os.path.join(CKPT_LOCAL, f"final_{name}")
        model.save_pretrained(fresh)
        print("  · juge ultra-court : adaptateur frais conservé")
    del model, trainer; torch.cuda.empty_cache()
    return final_step, budget_session.stopped_by_budget, fresh

def finalize_judge(name, fresh=None):
    best = STATE.j(name).get("best_step")
    src = None
    for cand in (best, STATE.step(name)):
        if cand:
            d = STATE.ckpt_dir(name) / f"ckpt-{cand}"
            if d.is_dir():
                src = d; break
    tmp = os.path.join(CKPT_LOCAL, f"final_{name}")
    if src is not None:
        if os.path.exists(tmp):
            shutil.rmtree(tmp)
        os.makedirs(tmp)
        for fn in os.listdir(src):        # le meilleur ckpt devient l'adaptateur
            if fn.startswith("adapter_"):
                shutil.copy2(os.path.join(src, fn), os.path.join(tmp, fn))
    else:
        tmp = fresh                        # juge ultra-court
    assert tmp and os.path.isdir(tmp), "aucune source pour l'adaptateur final"
    STATE.promote_final_adapter(name, tmp)
    ok, why = STATE.verify_final_adapter(name)
    assert ok, f"adaptateur {name} invalide : {why}"
    # vérification AVANT « done » : rechargement réel + forward aux logits finis
    m = PeftModel.from_pretrained(base, str(STATE.final_adapter_dir(name)))
    with torch.no_grad():
        p_ids, o_ids = encode_row(personas[name][0])
        ids = torch.tensor([p_ids + o_ids[:16]], device=base.device)
        assert torch.isfinite(m(input_ids=ids).logits).all(), "logits non finis"
    del m; torch.cuda.empty_cache()
    STATE.record_validation(name, "reload_forward", True,
                            "PeftModel rechargé depuis Drive + forward, "
                            "logits finis — AVANT le marquage done")
    STATE.mark_done(name, {"n_train": len(splits[name][0]),
                           "n_val": len(splits[name][1]),
                           "best_val_loss": STATE.j(name).get("best_val_loss"),
                           "last_step": STATE.step(name)})
    STATE.prune_ckpts(name, keep=0)        # le juge est fini : place nette
    STATE.save()

for name in personas:
    if STATE.status(name) == "done":
        print(f"=== {name} — déjà terminé (vérifié), sauté ===")
        continue
    print(f"\\n=== {name} ===")
    try:
        final_step, stopped, fresh = train_one(name)
    except Exception:
        STATE.fail(name, traceback.format_exc(limit=4)); STATE.save()
        print(f"!! {name} en échec — consigné, juge suivant tenté")
        print(traceback.format_exc())
        continue
    if stopped:
        print(f"\\n⏹ budget temps atteint — ARRÊT PROPRE au pas {STATE.step(name)}."
              "\\n  Le runtime est peut-être encore vivant : relancer cette cellule"
              "\\n  (ou Run all) rouvre une fenêtre d'entraînement, sans rien perdre."
              "\\n  Sinon : rouvrir le notebook plus tard, tout reprendra tout seul.")
        break
    finalize_judge(name, fresh)
    STATE.state["sessions"][-1]["trained"].append(name)
    STATE.save()
    _j = STATE.j(name)
    M3B.evidence_dump(
        DRIVE_ROOT, f"juge-{name}-terminé",
        f"{name} TERMINÉ — adaptateur promu sur Drive, hash vérifié, "
        f"rechargé + forward OK\\n"
        f"best_step={_j['best_step']} best_val_loss={_j['best_val_loss']} "
        f"pas={_j['step']} wall={_j.get('wall_seconds')}s "
        f"interruptions={_j.get('interruptions')} reprises={_j.get('resumes')}\\n"
        f"n_train={_j.get('n_train')} tokens={_j.get('n_tokens_train')} "
        f"params entraînables={(_j.get('params') or {}).get('trainable')}\\n",
        note="finalisation réelle du juge sur Colab",
        run_id=RUN_ID, head=HEAD)
    print(f"=== {name} : TERMINÉ, adaptateur vérifié ===")

print("\\n" + STATE.summary())
if STATE.all_done() and not STATE.state.get("finalized"):
    print("\\nTOUS LES JUGES SONT TERMINÉS — les §7, §7bis et §8 qui suivent"
          "\\n(via Run all) réalisent l'audit et l'export final automatiquement.")
""")

# ------------------------------------------------------------------ §7 -----
md("""
## 7 · Contrôle de santé — même affaire, deux plumes
Le test discriminant : la même instruction passée à deux adaptateurs doit
produire deux ouvertures *reconnaissablement différentes* (Thomas ≠ Kagan).
Si les sorties convergent, les adaptateurs n'ont rien appris. Résultat
conservé dans le manifeste Drive (aucune perte si la session meurt après).
""")

code("""
# --- §7 · probe (gardé : ne tourne que lorsque tout est terminé) --------------
if not STATE.all_done():
    print("§7 ignoré : juges incomplets — il s'exécutera quand tout sera fini.")
else:
    import pandas as pd
    ADAPTER_DIR = os.path.join(DRIVE_ROOT, "adapters")     # vérité = Drive

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

    STATE.state["probe"] = {"case": probe_case[:200],
                            "generations": {p: t[:500] for p, t in texts.items()}}
    STATE.save()
    M3B.evidence_dump(
        DRIVE_ROOT, "sonde-deux-plumes",
        "§7 · sonde — même instruction, deux plumes\\n"
        + "\\n".join(f"—— {p} ——\\n{t[:400]}" for p, t in texts.items())
        + "\\n",
        note="sorties réelles des adaptateurs rechargés",
        run_id=RUN_ID, head=HEAD)
    df = pd.DataFrame(STATE.state["results"])
    print("\\n", df.to_string(index=False))
    print(f"\\nval_loss médiane: {df.best_val_loss.median():.3f} "
          "(perte initiale attendue ≈ 3-4 ; en dessous de 2.5 = apprentissage réel)")
""")

md("""
### 7bis · Audit anti-mémorisation — min-k% + cloze (pré-enregistré, M3)

La roadmap exige deux contrôles publiés avec chaque adaptateur :

1. **min-k% prob** — sur un échantillon d'opinions *d'entraînement* : log-probabilité
   moyenne des k = 20 % de tokens les moins probables, mesurée deux fois — base
   seule vs base+adaptateur (même encodage que l'entraînement). Un modèle qui a
   mémorisé du verbatim rend « improbable » le texte exact qu'il a vu : Δ min-20%
   fortement positif + perplexité d'entraînement < 2 ⇒ drapeau.
2. **Cloze** — un span verbatim de 30 caractères est masqué `[...]` dans un
   passage d'une opinion d'entraînement ; le modèle complète en greedy. La
   récupération exacte du span par l'adaptateur, nettement au-dessus de la base,
   est la signature d'une mémorisation mot à mot.

C'est un détecteur, pas un jugement : les drapeaux partent dans le manifeste
(section `memorization`) et la décision appartient au protocole
(`docs/06-ETHIQUE.md`, `docs/04-PROTOCOLE.md`).
""")

code("""
# --- §7bis · audit anti-mémorisation (gardé) ----------------------------------
if not STATE.all_done():
    print("§7bis ignoré : juges incomplets.")
else:
    import random
    rng = random.Random(SEED)
    K_FRAC, N_MINK, N_CLOZE, CLOZE_SPAN, CLOZE_CONT = 0.20, 6, 4, 30, 48
    ADAPTER_DIR = os.path.join(DRIVE_ROOT, "adapters")

    def token_logprobs(model, row):
        \"\"\"(min-k%, moyenne) des log-probs des tokens de sortie — même
        encodage que PersonaTorch (encode_row), sortie bornée à 512 tokens.\"\"\"
        p_ids, o_ids = encode_row(row)
        o_ids = o_ids[:512]
        ids = torch.tensor([p_ids + o_ids], device=base.device)
        with torch.no_grad():
            lg = model(ids).logits[0]
        lp = torch.log_softmax(lg[len(p_ids) - 1: -1].float(), dim=-1)
        tgt = ids[0, len(p_ids):]
        tok_lp = lp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
        k = max(1, int(len(tok_lp) * K_FRAC))
        srt = tok_lp.sort().values
        return srt[:k].mean().item(), tok_lp.mean().item()

    def norm_txt(s):
        return " ".join(s.lower().split())

    def cloze_hits(model, rows):
        \"\"\"rows = [(row, i)] pré-échantillonnées — mêmes masques pour base et
        adaptateur, sinon la comparaison n'a pas de sens.\"\"\"
        hits = []
        for r, i in rows:
            out = r["output"]
            span, pre = out[i: i + CLOZE_SPAN], out[max(0, i - 500): i]
            user = ("Complete the passage marked [...] with the exact original "
                    "wording of this opinion.\\n\\n" + pre + " [...]")
            ids = tok.apply_chat_template(
                [{"role": "system", "content": r["system"]},
                 {"role": "user", "content": user}],
                tokenize=True, add_generation_prompt=True,
                return_tensors="pt").to(base.device)
            with torch.no_grad():
                gen = model.generate(ids, max_new_tokens=24, do_sample=False)
            txt = norm_txt(tok.decode(gen[0][ids.shape[1]:], skip_special_tokens=True))
            hits.append(int(norm_txt(span) in txt))
        return hits

    memo = {}
    for name in personas:
        pool = personas[name]
        rows_m = rng.sample(pool, min(N_MINK, len(pool)))
        rows_c = []
        for r in rng.sample(pool, min(N_CLOZE, len(pool))):
            hi = min(len(r["output"]) - CLOZE_SPAN - CLOZE_CONT, 3000)
            i = rng.randrange(200, hi) if hi > 201 else 200
            rows_c.append((r, i))
        b_min20 = [token_logprobs(base, r) for r in rows_m]
        m = PeftModel.from_pretrained(base, os.path.join(ADAPTER_DIR, name))
        a_min20 = [token_logprobs(m, r) for r in rows_m]
        cb, ca = cloze_hits(base, rows_c), cloze_hits(m, rows_c)
        del m; torch.cuda.empty_cache()
        delta = (sum(a for a, _ in a_min20) / len(a_min20)
                 - sum(b for b, _ in b_min20) / len(b_min20))
        ppl = math.exp(-sum(m_ for _, m_ in a_min20) / len(a_min20))
        flag = ((delta > 1.0 and ppl < 2.0)
                or (sum(ca) - sum(cb) >= 2 and sum(ca) >= 3))
        memo[name] = {
            "min20_base": round(sum(b for b, _ in b_min20) / len(b_min20), 3),
            "min20_adapter": round(sum(a for a, _ in a_min20) / len(a_min20), 3),
            "delta_nats": round(delta, 3),
            "train_ppl": round(ppl, 2),
            "cloze_base_hits": f"{sum(cb)}/{len(cb)}",
            "cloze_adapter_hits": f"{sum(ca)}/{len(ca)}",
            "flag": "memorization_suspect" if flag else "ok",
        }
        print(name, memo[name])

    STATE.state["memorization"] = memo
    STATE.save()
    M3B.evidence_dump(
        DRIVE_ROOT, "audit-anti-mémorisation",
        "§7bis · audit min-k% + cloze\\n"
        + "\\n".join(f"{n}: {json.dumps(v, ensure_ascii=False)}"
                     for n, v in memo.items()) + "\\n",
        note="mesures réelles base vs adaptateur",
        run_id=RUN_ID, head=HEAD)
    print("\\n→ section memorization écrite dans le manifeste Drive")
""")

# ------------------------------------------------------------------ §8 -----
md("""
## 8 · Export FINAL — automatique, idempotent, octet-stable

N'est exécuté que lorsque tout est terminé et audité. Le zip est reconstruit
de façon **déterministe** (métadonnées figées) : deux exports du même état
sont identiques octet par octet — l'idempotence est vérifiable, pas affirmée.

**Rien à télécharger, rien à fusionner** : l'export vit sur le Drive, et le
runner M4 ira le chercher tout seul. Le fichier `m3b_report.json` est DÉRIVÉ
du manifeste (jamais édité à la main).
""")

code("""
# --- §8 · export final (gardé) --------------------------------------------------
if not STATE.all_done():
    print("§8 ignoré : juges incomplets.")
elif not STATE.state.get("probe") or not STATE.state.get("memorization"):
    print("§8 bloqué : §7/§7bis doivent tourner d'abord (Run all le fait).")
else:
    STATE.write_report(CONFIG, "m3b_report.json")        # copie locale (cwd)
    entries = []
    for j in sorted(STATE.state["judges"]):
        d = STATE.final_adapter_dir(j)
        if not d.is_dir():
            continue
        for fn in sorted(os.listdir(d)):
            if os.path.isfile(os.path.join(d, fn)):
                entries.append((os.path.join(d, fn), f"{j}/{fn}"))
    entries.append(("m3b_report.json", "m3b_report.json"))
    M3B.deterministic_write_zip("m3b_adapters_final.zip", entries)
    M3B.promote_file("m3b_adapters_final.zip",
                     os.path.join(DRIVE_ROOT, "final", "m3b_adapters_final.zip"))
    STATE.state["finalized"] = True
    STATE.save()
    _zf = os.path.join(DRIVE_ROOT, "final", "m3b_adapters_final.zip")
    STATE.event("EXPORT", sha256=M3B.sha256_file(_zf),
                size=os.path.getsize(_zf))
    STATE.event("RUN_COMPLETE", judges=len(STATE.state["judges"]),
                sessions=len(STATE.state["sessions"]))

    # ---- manifeste de LIGNAGE : la chaîne complète, re-vérifiable --------
    MANIFEST = M3B.build_experiment_manifest(STATE, CONFIG, ENV_INFO,
                                             REPO_PATH)
    print("manifeste de lignage :", os.path.join(DRIVE_ROOT,
                                                 "experiment_manifest.json"))

    # ---- vérification de chaîne : résultat → prédiction → modèle →
    #      checkpoint → configuration → données → split → commit →
    #      environnement → journal ---------------------------------------
    _links, _lin_ok = M3B.verify_lineage(DRIVE_ROOT, REPO_PATH)
    for _ok, _name, _det in _links:
        print(f"  [{'✓' if _ok else '✗'}] {_name} — {_det}")

    # ---- PORTILLON GO/NO-GO objectif (le verdict, pas une affirmation) --
    print("\\nportillon M3b :")
    _g = subprocess.run([sys.executable,
                         os.path.join(REPO_PATH, "scripts", "m3b_gate.py"),
                         "--root", DRIVE_ROOT, "--repo", REPO_PATH,
                         "--json", os.path.join(DRIVE_ROOT,
                                                "m3b_gate.json")],
                        text=True)

    M3B.evidence_dump(
        DRIVE_ROOT, "finalisation-expérience",
        "EXPÉRIENCE FINALISÉE\\n"
        f"liens de lignage : {sum(1 for o, _, _ in _links if o)}"
        f"/{len(_links)} OK\\n"
        f"zip final sha256={M3B.sha256_file(_zf)[:16]}… "
        f"({os.path.getsize(_zf)/1e6:.0f} Mo)\\n"
        f"portillon : voir m3b_gate.json sur le Drive\\n",
        note="finalisation réelle — chaîne vérifiée + portillon exécuté",
        run_id=RUN_ID, head=HEAD)

    print("\\nEXPORT FINAL :", _zf, f"({os.path.getsize(_zf)/1e6:.0f} Mo)")
    print("Le runner M4 (notebook m4_epreuve_finale) le récupérera TOUT SEUL"
          "\\nsur le Drive — rien à télécharger, rien à déposer.")
""")

# ------------------------------------------------------------------ §8bis --
md("""
## 8bis · RESET TOTAL (dangereux — sur décision explicite uniquement)

Renomme le dossier Drive (`…-DELETED-…`, sauvegarde de dernier recours) ;
l'expérience repartira de zéro au prochain passage en §5bis. Utile seulement
si l'empreinte doit changer délibérément (nouvelle configuration
scientifique). Sinon : **ne pas toucher**.
""")

code("""
# --- §8bis · reset à double confirmation ---------------------------------------
RESET_CONFIRM = ""        # taper exactement : je-veux-tout-effacer
ok, msg = STATE.reset(RESET_CONFIRM)
print(msg)
""")

# ------------------------------------------------------------------ §9 -----
md("""
## 9 · Et ensuite (M4)

1. **Test transparent OT2020-23** (phase T du runner M4) : régression B4 —
   les chiffres attendus sont exacts (0,6366 au niveau vote ; 0,558 au
   niveau affaire) ; répétable sans risque.
2. **Comparaison pré-enregistrée** : B4 (barre métadonnées, 63,7 %),
   M3a-LR/IX/GB (challengers structurés), condition A (zero-shot),
   condition C (RAG) — McNemar exact sur les lignes appariées.
3. **Test final scellé** (phase S) : les 50 affaires 5-4, une seule fois,
   toutes conditions confondues. Le fichier `test_votes.jsonl` de chaque
   persona ne doit JAMAIS être ouvert avant ce moment.

Le runner M4 lit l'export final **directement sur le Drive** — aucun
téléversement manuel. Voir `docs/12-GUIDE-COLAB.md` pour le déroulé complet
et les points de contrôle.
""")

# ------------------------------------------------------------------ dump ---
def main():
    nb = {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python",
                           "name": "python3"},
            "colab": {"provenance": [], "gpuType": "T4",
                      "toc_visible": True},
            "language_info": {"name": "python"},
        },
        "cells": [],
    }
    for typ, src in C:
        lines = src.split("\n")
        cell = {"cell_type": typ, "metadata": {},
                "source": [l + "\n" for l in lines[:-1]] + [lines[-1]]}
        if typ == "code":
            cell["execution_count"] = None
            cell["outputs"] = []
        nb["cells"].append(cell)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"→ {OUT} : {len(C)} cellules")


if __name__ == "__main__":
    main()
