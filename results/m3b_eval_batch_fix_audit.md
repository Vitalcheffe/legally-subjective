# M3b — Audit du rituel de réparation : batch d'évaluation

*Généré le 2026-10-05T12:01:56.134283+00:00 — décision préalable : REPRENDRE (correctif d'infrastructure d'évaluation).*

## VERDICT : **GO S2**

| Porte GO S2 | État |
|---|---|
| 1_diff_minimal | ✅ PASS |
| 2_fingerprint_identique | ✅ PASS |
| 3_freeze_12_12 | ✅ PASS |
| 4_leakage_14_14 | ✅ PASS |
| 5_batteries | ✅ PASS |
| 6_checkpoints_rechargeables | ✅ PASS |
| 7_micro_test_évaluation_réelle | ✅ PASS |
| 8_oom_éliminé | ✅ PASS |
| 9_quota_suffisant | ✅ PASS |

## 1. État avant

- s1 (kernel Kaggle) : 233 min, commit `7ff7ffd60356`, empreinte `fa2c16441a70238e…`
- Kavanaugh **done 16/16** (aucune évaluation déclenchée : 16 < 20) — adaptateur promu et validé par reload
- EKagan 10/40, NMGorsuch 10/32, SAAlito 10/64 : **OOM à la première évaluation (pas 20)** — 52 pas durables exploitables, 27 pas perdus
- JGRoberts 6/32 arrêté par budget temps ; CThomas et SSotomayor non commencés

## 2. Cause racine

per_device_eval_batch_size jamais fixé dans TrainingArguments → défaut HuggingFace = 8.
à MAX_LEN=4096 sur T4 15,6 Go (14,56 Gio utilisables), la passe d'évaluation réclame 8,00 GiB d'un coup (scaled_dot_product_attention) avec seulement 7,04 Gio libres.
- Preuve par artefact : training_args.bin des checkpoints s1 (dé-sérialisé, transformers 4.49.0) : per_device_eval_batch_size = 8, per_device_train_batch_size = 1
- Preuve par log : torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 8.00 GiB. — NMGorsuch 22:54:41Z, SAAlito 01:03:01Z, EKagan 00:23:19Z
- Déterminisme : les 3 juges évalués sont tombés au MÊME point (première évaluation, pas 20) ; Kavanaugh (16 pas, aucune évaluation) a terminé normalement — la cause est strictement l'évaluation

## 3. Correctif et diff exact

- Commit `960279ec1aca` — UNE ligne : per_device_eval_batch_size=1, ajoutée à l'appel TrainingArguments de la cellule §6 train_one — même ligne dans le générateur make_m3b_notebook.py (chaîne de régénération)
- Gel du protocole régénéré par le rituel officiel `--je-change-le-protocole` (consigné) : avant 11/1 (le FAIL = exactement la ligne), après **12/12**

```diff
commit 960279ec1acabe23d9bbf58bb53b01aacf247138
Author: Vitalcheffe <vitalcheffe@users.noreply.github.com>
Date:   Mon Oct 5 09:13:56 2026 +0000

    m3b : correctif évaluation — per_device_eval_batch_size=1 (OOM T4 déterministe)
    
    s1 (kernel legally-subjective-m3b-s1, 2026-10-04→05, 233 min) : 3 échecs OOM
    déterministes (NMGorsuch, SAAlito, EKagan) à la PREMIÈRE évaluation
    (EVAL_EVERY=20) : per_device_eval_batch_size héritait du défaut HF (=8),
    jamais fixé — preuve relue dans training_args.bin des checkpoints s1
    (per_device_eval_batch_size=8). À MAX_LEN=4096 sur T4 15,6 Go, la passe
    d'évaluation réclame 8,00 GiB d'un coup (scaled_dot_product_attention,
    7,04 Go libres) → torch.OutOfMemoryError. BMKavanaugh (16 pas < 20 :
    aucune évaluation déclenchée) a terminé normalement et son adaptateur a
    été validé par reload — la cause est strictement l'infrastructure
    d'évaluation, pas l'entraînement.
    
    Correctif (UNE ligne, infrastructure d'évaluation, hors protocole) :
    - notebooks/m3b_qlora_personas.ipynb (cellule §6 train_one) : +1 ligne
    - scripts/make_m3b_notebook.py (générateur — chaîne de régénération) :
      même ligne à l'identique
    - results/protocol_m3b_freeze.json : gel régénéré par le RITUEL OFFICIEL
      --je-change-le-protocole ; seul fragment divergent = training_args
      (11→12 lignes) ; les 10 autres fragments restent octet-identiques
      (constat documenté : 11 PASS / 1 FAIL avant régénération, le FAIL
      étant exactement la ligne ajoutée)
    
    Invariance scientifique prouvée :
    - per_device_eval_batch_size ∉ SCI_KEYS (m3b_state.py inchangé)
    - empreinte d'expérience identique avant/après ET identique à s1 :
      fa2c1644… / cfg 83fee411… / data fe6defeb… (cellules réelles
      exécutées : imports→config→personas_dir→load_persona→§5bis)
    - mêmes datasets, mêmes splits, mêmes hashs de données, 7 mêmes juges
    
    Batteries re-passées sur l'arbre corrigé :
    - freeze 12/12 PASS ; leakage 14/14 verdict PASS (m15_audit)
    - test_m3b_state 143/0 ; test_m3b_merge 25/0
    - test_m3b_resume_cpu 30/0 (vrai transformers/peft CPU)
    - test_m3b_notebook_flow 25/0 ; validate_notebook 31 cellules/0 erreur
    - lignage : manifeste construit + chaîne re-calculée — maillons
      intégrité tous ✓ (L1/L2 schémas, L3 empreinte ×3, L4 adaptateur
      Kavanaugh, L5 dernière ligne journal, L7 scellé M4) ; maillons ✗ =
      uniquement l'état connu non-terminé (juges incomplets, pas d'export §8)
    
    Compatibilité checkpoints s1 vérifiée fichier par fichier :
    - 32/32 fichiers manifestés re-hachés conformes (EKagan ckpt-10,
      JGRoberts ckpt-6, NMGorsuch ckpt-10, SAAlito ckpt-10)
    - chargements réels (safetensors/torch/json) : 504 tenseurs LoRA,
      504 params optimiseur, scheduler/rng/trainer_state intacts
    - adaptateur promu BMKavanaugh rechargé (504 tenseurs, r=16, alpha=32)
    
    Audit complet du rituel de réparation : results/m3b_eval_batch_fix_audit.json/.md
---
 data/m15_store/clean/audit_leak_journal.json | 2 +-
 data/m15_store/clean/audit_leak_journal.md   | 2 +-
 notebooks/m3b_qlora_personas.ipynb           | 1 +
 results/protocol_m3b_freeze.json             | 6 +++---
 scripts/make_m3b_notebook.py                 | 1 +
 5 files changed, 7 insertions(+), 5 deletions(-)

diff --git a/data/m15_store/clean/audit_leak_journal.json b/data/m15_store/clean/audit_leak_journal.json
index 1106b79..e5ae47f 100644
--- a/data/m15_store/clean/audit_leak_journal.json
+++ b/data/m15_store/clean/audit_leak_journal.json
@@ -1,5 +1,5 @@
 {
- "generated_at": "2026-10-04T17:37:23.693134+00:00",
+ "generated_at": "2026-10-05T09:02:07.724567+00:00",
  "scope": "M1.5 étape 4 — zéro fuite, dédup, hygiène, pré-décision",
  "summary": {
   "checks_total": 14,
diff --git a/data/m15_store/clean/audit_leak_journal.md b/data/m15_store/clean/audit_leak_journal.md
index a3ebdf5..5545c65 100644
--- a/data/m15_store/clean/audit_leak_journal.md
+++ b/data/m15_store/clean/audit_leak_journal.md
@@ -1,6 +1,6 @@
 # Journal d'audit zéro-fuite — M1.5.4
 
-Généré : 2026-10-04T17:37:23.693134+00:00  
+Généré : 2026-10-05T09:02:07.724567+00:00  
 Verdict : **PASS** (14 contrôles, 0 échec(s))
 
 | Contrôle | Verdict | Détail |
diff --git a/notebooks/m3b_qlora_personas.ipynb b/notebooks/m3b_qlora_personas.ipynb
index f031a2c..94725b7 100644
--- a/notebooks/m3b_qlora_personas.ipynb
+++ b/notebooks/m3b_qlora_personas.ipynb
@@ -595,6 +595,7 @@
     "    args = TrainingArguments(\n",
     "        output_dir=local_out,\n",
     "        per_device_train_batch_size=CONFIG[\"BATCH\"],\n",
+    "        per_device_eval_batch_size=1,  # fix OOM T4 : défaut HF=8 × 4096 tok = alloc 8 Go, évaluation impossible\n",
     "        gradient_accumulation_steps=CONFIG[\"GRAD_ACCUM\"],\n",
     "        num_train_epochs=CONFIG[\"EPOCHS\"], learning_rate=CONFIG[\"LR\"],\n",
     "        lr_scheduler_type=\"cosine\", warmup_steps=CONFIG[\"WARMUP\"],\n",
diff --git a/results/protocol_m3b_freeze.json b/results/protocol_m3b_freeze.json
index ee7b574..dfed881 100644
--- a/results/protocol_m3b_freeze.json
+++ b/results/protocol_m3b_freeze.json
@@ -31,8 +31,8 @@
    "n_lines": 22
   },
   "training_args": {
-   "sha256": "9915371decf6ad1b47e6355cae27f13f0cb498a8af88281a5cf2402e8cac6318",
-   "n_lines": 11
+   "sha256": "c0771e1ccfc31e9adc352cf4ed68444f376fa9ea835a729a21d387e93dfb9df9",
+   "n_lines": 12
   },
   "eval_probe": {
    "sha256": "1a8c9022fea661e19625673abc531495e651ddf26dda7e18626292682f917b89",
@@ -55,7 +55,7 @@
   "dataset": "class PersonaTorch(torch.utils.data.Dataset):\n    def __init__(self, rows):\n        self.items = []\n        for r in rows:\n            p, o = encode_row(r)\n            ids = p + o + [tok.eos_token_id or tok.pad_token_id]\n            labels = [-100] * len(p) + o + [tok.eos_token_id or tok.pad_token_id]\n            self.items.append((ids[:CONFIG[\"MAX_LEN\"]], labels[:CONFIG[\"MAX_LEN\"]]))\n    def __len__(self):\n        return len(self.items)\n    def __getitem__(self, i):\n        ids, labels = self.items[i]\n        return {\"input_ids\": ids, \"labels\": labels}\n\ndef collate(batch):\n    mx = max(len(b[\"input_ids\"]) for b in batch)\n    pad = tok.pad_token_id or tok.eos_token_id\n    return {\n        \"input_ids\": torch.tensor([b[\"input_ids\"] + [pad] * (mx - len(b[\"input_ids\"])) for b in batch]),\n        \"labels\": torch.tensor([b[\"labels\"] + [-100] * (mx - len(b[\"labels\"])) for b in batch]),\n        \"attention_mask\": torch.tensor([[1] * len(b[\"input_ids\"]) + [0] * (mx - len(b[\"input_ids\"])) for b in batch]),\n    }",
   "qlora_base": "import bitsandbytes as bnb\nfrom peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training\nfrom transformers import (AutoModelForCausalLM, BitsAndBytesConfig,\n                          Trainer, TrainingArguments)\n\nbnb_cfg = BitsAndBytesConfig(\n    load_in_4bit=True, bnb_4bit_quant_type=\"nf4\",\n    bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,\n    bnb_4bit_use_double_quant=True)\n\nbase = AutoModelForCausalLM.from_pretrained(\n    CONFIG[\"MODEL_ID\"], quantization_config=bnb_cfg, device_map={\"\": 0})\nbase = prepare_model_for_kbit_training(base, use_gradient_checkpointing=True)\nbase.config.use_cache = False\n\ndef make_lora():\n    return LoraConfig(\n        r=CONFIG[\"LORA_R\"], lora_alpha=CONFIG[\"LORA_ALPHA\"],\n        lora_dropout=CONFIG[\"LORA_DROPOUT\"], bias=\"none\", task_type=\"CAUSAL_LM\",\n        target_modules=[\"q_proj\", \"k_proj\", \"v_proj\", \"o_proj\",\n                        \"gate_proj\", \"up_proj\", \"down_proj\"])\nprint(\"base chargée:\", sum(p.numel() for p in base.parameters())/1e9, \"Md (4-bit)\")",
   "lora_targets": "import bitsandbytes as bnb\nfrom peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training\nfrom transformers import (AutoModelForCausalLM, BitsAndBytesConfig,\n                          Trainer, TrainingArguments)\n\nbnb_cfg = BitsAndBytesConfig(\n    load_in_4bit=True, bnb_4bit_quant_type=\"nf4\",\n    bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,\n    bnb_4bit_use_double_quant=True)\n\nbase = AutoModelForCausalLM.from_pretrained(\n    CONFIG[\"MODEL_ID\"], quantization_config=bnb_cfg, device_map={\"\": 0})\nbase = prepare_model_for_kbit_training(base, use_gradient_checkpointing=True)\nbase.config.use_cache = False\n\ndef make_lora():\n    return LoraConfig(\n        r=CONFIG[\"LORA_R\"], lora_alpha=CONFIG[\"LORA_ALPHA\"],\n        lora_dropout=CONFIG[\"LORA_DROPOUT\"], bias=\"none\", task_type=\"CAUSAL_LM\",\n        target_modules=[\"q_proj\", \"k_proj\", \"v_proj\", \"o_proj\",\n                        \"gate_proj\", \"up_proj\", \"down_proj\"])\nprint(\"base chargée:\", sum(p.numel() for p in base.parameters())/1e9, \"Md (4-bit)\")",
-  "training_args": "    args = TrainingArguments(\n        output_dir=local_out,\n        per_device_train_batch_size=CONFIG[\"BATCH\"],\n        gradient_accumulation_steps=CONFIG[\"GRAD_ACCUM\"],\n        num_train_epochs=CONFIG[\"EPOCHS\"], learning_rate=CONFIG[\"LR\"],\n        lr_scheduler_type=\"cosine\", warmup_steps=CONFIG[\"WARMUP\"],\n        logging_steps=5, eval_strategy=\"steps\", eval_steps=CONFIG[\"EVAL_EVERY\"],\n        save_strategy=\"steps\", save_steps=CONFIG[\"SAVE_STEPS\"],\n        save_total_limit=None, load_best_model_at_end=False,\n        bf16=torch.cuda.is_bf16_supported(), report_to=\"none\", seed=SEED,\n        remove_unused_columns=False, dataloader_pin_memory=False)",
+  "training_args": "    args = TrainingArguments(\n        output_dir=local_out,\n        per_device_train_batch_size=CONFIG[\"BATCH\"],\n        per_device_eval_batch_size=1,  # fix OOM T4 : défaut HF=8 × 4096 tok = alloc 8 Go, évaluation impossible\n        gradient_accumulation_steps=CONFIG[\"GRAD_ACCUM\"],\n        num_train_epochs=CONFIG[\"EPOCHS\"], learning_rate=CONFIG[\"LR\"],\n        lr_scheduler_type=\"cosine\", warmup_steps=CONFIG[\"WARMUP\"],\n        logging_steps=5, eval_strategy=\"steps\", eval_steps=CONFIG[\"EVAL_EVERY\"],\n        save_strategy=\"steps\", save_steps=CONFIG[\"SAVE_STEPS\"],\n        save_total_limit=None, load_best_model_at_end=False,\n        bf16=torch.cuda.is_bf16_supported(), report_to=\"none\", seed=SEED,\n        remove_unused_columns=False, dataloader_pin_memory=False)",
   "eval_probe": "\n    def generate(name, instruction, max_new_tokens=120):",
   "memo_audit": "    K_FRAC, N_MINK, N_CLOZE, CLOZE_SPAN, CLOZE_CONT = 0.20, 6, 4, 30, 48",
   "sci_keys": "SCI_KEYS = (\"MODEL_ID\", \"MAX_LEN\", \"INSTR_KEEP\", \"LORA_R\", \"LORA_ALPHA\",\n            \"LORA_DROPOUT\", \"LR\", \"EPOCHS\", \"BATCH\", \"GRAD_ACCUM\",\n            \"EVAL_EVERY\", \"PATIENCE\", \"WARMUP\", \"VAL_FRACTION\",\n            \"MIN_TRAIN_ROWS\", \"PERSONAS_GARDÉES\")"
diff --git a/scripts/make_m3b_notebook.py b/scripts/make_m3b_notebook.py
index dc6804b..788c90e 100644
--- a/scripts/make_m3b_notebook.py
+++ b/scripts/make_m3b_notebook.py
@@ -540,6 +540,7 @@ def train_one(name):
     args = TrainingArguments(
         output_dir=local_out,
         per_device_train_batch_size=CONFIG["BATCH"],
+        per_device_eval_batch_size=1,  # fix OOM T4 : défaut HF=8 × 4096 tok = alloc 8 Go, évaluation impossible
         gradient_accumulation_steps=CONFIG["GRAD_ACCUM"],
         num_train_epochs=CONFIG["EPOCHS"], learning_rate=CONFIG["LR"],
         lr_scheduler_type="cosine", warmup_steps=CONFIG["WARMUP"],
```

## 4. Invariance scientifique

- `per_device_eval_batch_size` ∈ SCI_KEYS ? **False (non)**
- Empreinte s1 enregistrée : `fa2c16441a70238e00fd1ddc…`
- Avant correctif : `fa2c16441a70238e00fd1ddc…`
- Après correctif : `fa2c16441a70238e00fd1ddc…`
- Invariance avant/après : **True** ; identité avec s1 : **True** (cfg `83fee411da55…`, data `fe6defebabc0…`, seed 42, 7 mêmes juges)

## 5. Batteries (arbre corrigé)

- Gel 12/12 **PASS** · fuite 14/14 **PASS** · state **143/0** · merge **25/0** · reprise CPU **30/0** · flow notebook **25/0** · validation **31 cellules/0 erreur**
- Lignage : maillons d'intégrité ✓ (empreinte recalculée ×3, adaptateur Kavanaugh, scellé M4) ; les maillons ✗ reflètent l'état non-terminé connu

## 6. Compatibilité des checkpoints s1

- 39/39 fichiers re-hachés conformes (EKagan ckpt-10, JGRoberts ckpt-6, NMGorsuch ckpt-10, SAAlito ckpt-10)
- Chargements réels (safetensors/torch) : 4 checkpoints + adaptateur promu — 504 tenseurs LoRA, 504 params optimiseur, scheduler/rng/trainer_state intacts
- `training_args.bin` s1 (preuve du défaut) : per_device_eval_batch_size = 8

## 7. Réparations d'infrastructure annexes

- **Resynchronisation du runner** (commit 8866c0a) : le run 4 du micro-test a révélé que le runner du repo avait 6 correctifs d'infrastructure de retard sur le source kernel réellement exécuté en s1 (dérive de provenance) — resynchronisé sur le source éprouvé (aucun impact scientifique)
- GitHub restauré (token utilisateur) : commits orphelins 55462bb..7ff7ffd récupérés depuis l'archive dataset, puis correctif + runner poussés

## 8. Micro-test GPU (Kaggle, T4×2 réel)

- Session : 94.1 min, outcomes `{'w0': 0, 'w1': 0}`, commit `8866c0a0b39e`
- Design : LE RUNNER officiel lui-même en mode « aperçu s2 » — EKagan (w0) et NMGorsuch (w1) repris depuis leurs ckpt-10, l'évaluation IN-TRAINING du pas 20 (l'événement exact qui tuait s1) s'est déclenchée avec eval batch 1
- Évaluations complètes : [{"checkpoint": "m3b_state_w0/checkpoints/EKagan/ckpt-20", "step": 20, "eval_loss": 1.7252482175827026, "epoch": 3.762}, {"checkpoint": "m3b_state_w1/checkpoints/NMGorsuch/ckpt-20", "step": 20, "eval_loss": 1.768828272819519, "epoch": 4.727}]
- **Aucune OOM, val_loss produites, checkpoints ckpt-20 sauvegardés, arrêt propre (rc 0)**

## 9. Quota Kaggle (mesures API directes)

- 30 h/fenêtre, refresh **2026-10-10T00:00Z**
- 08:27Z : 5 h 26 m 42 s consommées / **24 h 33 m 18 s restantes** (identique à l'UI)
- 12:00Z (après micro-test) : 7 h 10 m 27 s consommées / **22 h 49 m restantes**
- Comportement 2 GPU : **une session T4×2 = 1× son wall** (double preuve : arithmétique des 4 premières sessions à la demi-seconde + run final contrôlé de 94,1 min)

## 10. Budget recalculé (mesures réelles s1)

- Cadence mesurée : 4.7–6.4 min/pas (moyenne pondérée 6.0 ; l'estimation « 5,87 » est la borne basse observée)
- Reste à faire : 332 pas (384 au total, 52 durables faits, 27 perdus en OOM s1)
- Scénarios : optimiste 19.6 h · central 21.9 h · prudent 25.6 h (entraînement 2 workers parallèles + finalize)
- L'ancien budget « 4,5 semaines à ~6 h/semaine » est **OBSOLÈTE** : tout tient dans la fenêtre courante (optimiste/central) ou avec un report mineur après le refresh du 10 octobre (prudent)

## 11. Conditions pour s2

- monter la sortie du kernel s1 (racines d'état) comme source du kernel s2 — PAS la sortie du micro-test (celle-ci est une branche d'audit ; ses pas sont du calcul de vérification, pas de la production)
- alternative documentée : monter la sortie du micro-test ferait gagner ~20 pas (~2 h) mais mélangerait vérification et production — déconseillé pour la propreté du lignage
- affectation recommandée : w0 = CThomas, JGRoberts, EKagan (176 pas) ; w1 = SSotomayor, SAAlito, NMGorsuch (156 pas) ; sessions ≤ 8 h ; finalize en session séparée

## 12. Règle absolue respectée

s2 n'a PAS été lancé dans cette tâche. Cette tâche était exclusivement : CORRIGER → PROUVER → TESTER → AUDITER → DÉCIDER.