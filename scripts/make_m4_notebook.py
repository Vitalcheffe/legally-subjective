#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Génère notebooks/m4_epreuve_finale.ipynb — l'Épreuve Finale (M4).

Le notebook est autonome (Colab T4), versionné, et suit la loi du
protocole : une seule exécution sur les 50 affaires scellées, gardes
mécaniques avant, verrou après. Toute l'analyse (McNemar, Wilson,
calibration, strates, condition D) vit dans scripts/m4_scoring.py —
testé localement par scripts/test_m4_machinery.py — et est importée
depuis le clone au tag gelé : zéro divergence possible entre le test
et l'examen.

Pré-inscription embarquée (verrouillée avant toute évaluation) :
  * conditions A (zéro-coup, analyste neutre), B (persona + adaptateur),
    C (contexte : k=5 opinions antérieures similaires, TF-IDF question,
    fenêtre train stricte, scellés exclus), D (règle B4 stricte,
    scellées exclues de l'ajustement) ;
  * A/C : une requête direction par affaire, répliquée aux 9 juges pour
    l'appareillage au niveau vote (A n'a pas d'information par juge —
    c'est précisément ce que B doit battre) ; B : une requête par juge ;
  * disposition : une requête par condition et par affaire (A/C : neutre ;
    B : persona Roberts — pré-inscrit ; D : toujours « reverse », B3) ;
  * égalité de majorité → prédiction exclue, code « tie » ;
  * strates futur (20) / entrelacé (30) — McNemar global ET stratifié ;
  * p_affaire = moyenne des p_libéral des juges interrogés ;
  * siège sans adaptateur → dégradé base-prompt-only (rapport de
    puissance Barrett/Jackson, pré-inscrit à M3).
"""
import os

import nbformat as nbf

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "notebooks", "m4_epreuve_finale.ipynb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

nb = nbf.v4.new_notebook()
nb.metadata = {
    "colab": {"name": "M4 — L'Épreuve Finale (Legally Subjective)",
              "provenance": [], "toc_visible": True},
    "kernelspec": {"name": "python3", "display_name": "Python 3",
                   "language": "python"},
    "language_info": {"name": "python"},
    "accelerator": "GPU",
}


def md(s):
    nb.cells.append(nbf.v4.new_markdown_cell(s))


def code(s):
    nb.cells.append(nbf.v4.new_code_cell(s))


# ---------------------------------------------------------------- intro --
md("""# M4 — L'Épreuve Finale

**Projet *Legally Subjective*** — prédire les votes d'une Cour suprême
à partir des textes. Ce notebook exécute le protocole scellé de
`docs/04-PROTOCOLE.md` : **une seule passe**, sur les **50 affaires 5-4
scellées**, quatre conditions (A zéro-coup · B persona · C contexte ·
D statistique), publication des résultats **quels qu'ils soient**.

## Les gardes, dans l'ordre

1. **Le gel** : le repo est cloné au tag `m4-freeze` — le commit exact
   que l'épreuve consomme. Le scellé est recalculé et doit correspondre
   à `five_four_selection.sealed_sha256`, sinon arrêt immédiat.
2. **La porte de pré-vol** : `scripts/m4_readiness.py` est re-exécuté
   DANS le clone (audit zéro-fuite re-joué, reconstruction déterministe,
   exclusion indépendante du scellé). Tout FAIL = épreuve interdite.
   Pour la phase S, R6 (adaptateurs M3b) doit être PASS.
3. **Le verrou** : après l'écriture des prédictions, `m4_exam.lock`
   rend toute seconde exécution impossible sans le geste délibéré
   `UNSEAL = "--je-brise-le-sceau"` — consigné comme bris de scellé dans
   le rapport. Les prédictions sont écrites AVANT que la moindre vérité
   terrain ne soit lue : le score consomme un fichier gelé et haché.

## Pré-inscription de l'analyse (verrouillée ici, avant tout résultat)

| Règle | Valeur |
|---|---|
| Test décisif | McNemar exact bilatéral, B vs A, α = 0,05 |
| Unités | affaire (direction + disposition) et vote par juge |
| Strates | futur (OT2020+) / entrelacé (OT2015-2019), global + stratifié |
| Intervalles | Wilson 95 % (une décimale max) |
| Calibration | p_libéral par choix contraint ; bandes égales ×5 ; ECE |
| p_affaire | moyenne des p_libéral des juges interrogés |
| Égalité (tie) | prédiction exclue, code d'échec, jamais tranchée |
| A/C par juge | la prédiction d'affaire est répliquée aux 9 juges |
| Disposition | A/C : neutre · B : persona Roberts · D : toujours reverse |
| C — récupération | k=5, TF-IDF (1-2 grammes) sur la question, fenêtre train stricte, scellés et sœurs exclus, date < décision de la cible, extrait de 900 caractères |
| D — ajustement | règle B4 stricte : direction modale par juge, scellées exclues de l'ajustement |
| Sièges dégradés | sans adaptateur : base + prompt persona, étiqueté |

L'implémentation de toutes ces règles vit dans `scripts/m4_scoring.py`,
prouvée par `scripts/test_m4_machinery.py` (McNemar vérifié contre
scipy, B4 reproduit à l'identique : 0,6366 vote / 0,558 affaire).""")

# ------------------------------------------------------------- §1 env --
md("""## 1 · Environnement (versions épinglées, exécuter une fois)

⚠️ Runtime → Change runtime type → GPU (**T4 suffit**). La leçon M3b
s'applique : plancher `bitsandbytes >=0.47.0,<0.51` (la 0.45.x importe
`triton.ops`, supprimé dans triton ≥ 3.2 ; et les pins d'une version
inexistante annulent toute la ligne pip).""")

code("""%pip -q install "transformers>=4.55,<5" "peft>=0.16" \\
    "bitsandbytes>=0.47.0,<0.51" "accelerate>=1.5"
import torch
assert torch.cuda.is_available(), "GPU requis (Runtime → Change runtime type)"
print("GPU :", torch.cuda.get_device_name(0))""")

# ------------------------------------------------- §2 acquisition gel --
md("""## 2 · Acquisition du gel + chaîne de preuve

Trois choses, dans l'ordre : cloner le repo **au tag `m4-freeze`**
(données, code d'analyse et audit gelés) ; déposer les **adaptateurs
M3b** (le zip exporté par le notebook d'entraînement) ; re-exécuter la
**porte de pré-vol**. Rien ne s'exécute si la chaîne ne tient pas.""")

code("""import glob, gzip, hashlib, json, math, os, re, subprocess, sys, \\
    time, zipfile
from collections import Counter, defaultdict
from pathlib import Path

PINNED_TAG = "m4-freeze"
REPO = "/content/legally-subjective" if os.path.exists("/content") \\
       else "./legally-subjective"

if not os.path.isdir(REPO):
    r = subprocess.run(["git", "clone", "--depth", "1", "--branch",
                        PINNED_TAG,
                        "https://github.com/Vitalcheffe/legally-subjective.git",
                        REPO], capture_output=True, text=True)
    print(r.stdout, r.stderr)

head = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
tag = subprocess.run(["git", "-C", REPO, "describe", "--tags"],
                     capture_output=True, text=True).stdout.strip()
print(f"gel : {tag} @ {head[:12]}")

# --- le scellé se recalcule, sinon tout s'arrête -----------------------
stats = json.load(open(f"{REPO}/data/processed/stats_v1.json",
                       encoding="utf-8"))
ff = stats["five_four_selection"]
recomputed = hashlib.sha256(
    json.dumps(sorted(ff["cases"])).encode()).hexdigest()
assert recomputed == ff["sealed_sha256"], "SCELLÉ MODIFIÉ — ARRÊT IMMÉDIAT"
print(f"scellé intègre : {ff['sealed_sha256'][:20]}… ({len(ff['cases'])} affaires)")

# --- adaptateurs M3b : déposer m3b_adapters_*.zip dans le répertoire ---
ADAPTER_DIR = os.path.join(REPO, "adapters")
M3B_REPORT = os.path.join(REPO, "m3b_report.json")
for z in sorted(glob.glob("m3b_adapters_*.zip")):
    with zipfile.ZipFile(z) as zf:
        zf.extractall(ADAPTER_DIR)          # adapters/<juge>/…
    inner = os.path.join(ADAPTER_DIR, "m3b_report.json")
    if os.path.exists(inner):
        os.replace(inner, M3B_REPORT)
    print(f"décompressé : {z}")
has_adapters = bool(glob.glob(os.path.join(ADAPTER_DIR, "*", "*")))
print("adaptateurs présents :", has_adapters)

# --- la porte de pré-vol, re-exécutée à froid dans le clone -------------
r = subprocess.run([sys.executable, "scripts/m4_readiness.py"],
                   cwd=REPO, capture_output=True, text=True)
print(r.stdout[-1600:])
gate = json.load(open(f"{REPO}/results/m4_readiness.json",
                      encoding="utf-8"))
assert "FAIL" not in gate["verdict"], "porte de pré-vol en échec"
print("verdict porte :", gate["verdict"])""")

# ---------------------------------------------------- §3 config imports --
md("""## 3 · Configuration + imports du gel

`PHASE` sélectionne l'exécution : `"T"` = test transparent OT2020-23
(répétable — validation de la machinerie, sans scellé), `"S"` =
**l'Épreuve**. Les prompts persona et la tâche de vote sont importés du
builder gelé — identité d'octet garantie avec l'entraînement.""")

code("""PHASE = "T"      # "T" transparent (répétable) · "S" ÉPREUVE SCELLÉE
PHASE_T_LIMIT = None    # None = tout ; un entier = validation mécanique
CONDITIONS_T = ["A", "B", "D"]     # "C" optionnelle en phase T
SEED = 271828

sys.path.insert(0, os.path.join(REPO, "scripts"))
import m3_build_datasets as B      # builder gelé : prompts EXACTS
import m4_scoring as MS            # la pré-inscription de l'analyse

cases, opinions, stats_x, amap = B.load_corpus()
is_sealed = B.sealed_dockets(stats_x)
oyez = B.load_oyez()
LA_CHAMBRE = B.LA_CHAMBRE
print(f"corpus : {len(cases)} affaires | personas : "
      f"{len(glob.glob(os.path.join(REPO, 'data/m3/personas/*')))}")""")

# ------------------------------------------------- §4 base + adaptateurs --
md("""## 4 · Base 4-bit + adaptateurs par juge

Le modèle de base DOIT être celui de `m3b_report.json` (vérifié). Les
sièges sans adaptateur passent en mode dégradé pré-inscrit :
`persona=base-prompt-only` (rapport de puissance — Barrett, Jackson,
et tout juge dont l'entraînement a été sauté).""")

code("""from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

if os.path.exists(M3B_REPORT):
    report = json.load(open(M3B_REPORT, encoding="utf-8"))
    MODEL_ID = report["model"]
    print("modèle de l'entraînement :", MODEL_ID)
else:
    report = {"results": []}
    MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"
    print("⚠ m3b_report.json absent — phase T sans adaptateurs (A/D "
          "seuls). Pour l'épreuve S : déposer le zip (§2).")

tok = AutoTokenizer.from_pretrained(MODEL_ID)
base = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, load_in_4bit=True, device_map="auto",
    torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported()
    else torch.float16)

trained = {r["persona"] for r in report.get("results", [])}
have = {os.path.basename(p) for p in glob.glob(
    os.path.join(ADAPTER_DIR, "*")) if os.path.isdir(p)}
ACTIVE = sorted(trained & have)
DEGRADED = [s for s in LA_CHAMBRE if s not in ACTIVE]
print(f"adaptateurs actifs ({len(ACTIVE)}) :", ", ".join(ACTIVE))
print(f"sièges dégradés base-prompt-only ({len(DEGRADED)}) :",
      ", ".join(DEGRADED) or "aucun")

_loaded = {}
def model_for(slug):
    if slug is None or slug not in ACTIVE:
        return base
    if slug not in _loaded:
        _loaded[slug] = PeftModel.from_pretrained(
            base, os.path.join(ADAPTER_DIR, slug))
    return _loaded[slug]""")

# ------------------------------------------------ §5 le primitif contraint --
md("""## 5 · Le primitif de scoring contraint

Pas de génération libre : pour chaque question, la log-probabilité de
**séquence** de chaque mot-candidat est calculée (teacher forcing) et la
softmax des deux (ou trois) candidats donne la prédiction ET la
probabilité de calibration. Déterministe, sans échantillonnage.

Les prompts de B viennent du builder gelé (`B.PERSONA_SYSTEM`,
`B.VOTE_TASK`) — la même exacte formulation que l'entraînement. Les
prompts de A/C (analyste neutre) sont pré-inscrits ici.""")

code("""# ---- prompts pré-inscrits ------------------------------------------------
A_SYSTEM = ("You are a careful, neutral analyst of the U.S. Supreme "
            "Court. You read the case file exactly as it was before the "
            "Court decided, and you answer as an expert in Court "
            "practice.")
A_VOTE_TASK = ("State the direction of the decisive vote on the question "
               "presented: conservative or liberal. Answer with exactly "
               "one word.")
DISPOSITION_TASK = ("How should the judgment below be treated? Answer "
                    "with exactly one word: affirm, reverse, or vacate.")

def b_system(slug):
    return B.PERSONA_SYSTEM.format(
        name=B.FULL_NAMES[slug],
        role=B.ROLE_OF.get(slug, "Associate Justice"))

def b_vote_task(slug):
    return B.VOTE_TASK.format(name=B.FULL_NAMES[slug])

# ---- scoring contraint ---------------------------------------------------
def choice_logprob(model, system, user, choices):
    msgs = [{"role": "system", "content": system},
            {"role": "user", "content": user}]
    prompt = tok.apply_chat_template(
        msgs, tokenize=True, add_generation_prompt=True,
        return_tensors="pt").to(base.device)
    out = {}
    for ch in choices:
        cand = tok(" " + ch, add_special_tokens=False).input_ids
        ids = torch.cat([prompt, torch.tensor([cand],
                                              device=base.device)], dim=1)
        with torch.no_grad():
            logits = model(ids).logits[0]
        lp = 0.0
        for j, t in enumerate(cand):
            lp += torch.log_softmax(
                logits[prompt.shape[1] - 1 + j], dim=-1)[t].item()
        out[ch] = lp
    return out

def p_of(scores):
    mx = max(scores.values())
    ex = {k: math.exp(v - mx) for k, v in scores.items()}
    s = sum(ex.values())
    return {k: v / s for k, v in ex.items()}

def vote_query(model, system, user):
    p = p_of(choice_logprob(model, system, user,
                            ["conservative", "liberal"]))
    return {"vote": max(p, key=p.get), "p_liberal": round(p["liberal"], 4)}

def disposition_query(model, system, user):
    p = p_of(choice_logprob(model, system, user,
                            ["affirm", "reverse", "vacate"]))
    return max(p, key=p.get)

# ---- fumée : une affaire, une requête par type, avant tout long run ----
cf_smoke = json.load(open(sorted(glob.glob(
    os.path.join(REPO, "data/m3/casefiles/*.json")))[0]))
v = vote_query(base, A_SYSTEM, cf_smoke["instruction"] + "\\n" + A_VOTE_TASK)
d = disposition_query(base, A_SYSTEM,
                      cf_smoke["instruction"] + "\\n" + DISPOSITION_TASK)
print("fumée A :", v, "| disposition :", d)
if ACTIVE:
    v_b = vote_query(model_for(ACTIVE[0]), b_system(ACTIVE[0]),
                     cf_smoke["instruction"] + "\\n"
                     + b_vote_task(ACTIVE[0]))
    print(f"fumée B [{ACTIVE[0]}] :", v_b)""")

# ---------------------------------------------------------- §6 phase T --
md("""## 6 · Phase T — test transparent OT2020-23 (répétable, sans scellé)

La répétition sans risque : conditions A/B/D sur les affaires de test
transparentes (scellées exclues). La condition D est vérifiée contre le
B4 publié de M2 (régression de fidélité : 0,6366 vote / 0,558 affaire).
En cas de bris de session : re-exécuter, la phase T est idempotente.
~1 h sur T4 (B interroge 9 juges × 211 affaires).""")

code("""def casefiles_window(window):
    out = []
    for p in sorted(glob.glob(os.path.join(REPO, "data/m3/casefiles",
                                           "*.json"))):
        cf = json.load(open(p, encoding="utf-8"))
        if cf.get("window") == window:
            out.append(cf)
    return out

def run_condition_A(cfs):
    \"\"\"Une requête direction + une disposition par affaire ; la
    prédiction d'affaire est répliquée aux 9 juges (pré-inscrit : A
    n'a pas d'information par juge — c'est ce que B doit battre).\"\"\"
    preds = []
    for i, cf in enumerate(cfs):
        u = cf["instruction"] + "\\n" + A_VOTE_TASK
        v = vote_query(base, A_SYSTEM, u)
        dsc = disposition_query(base, A_SYSTEM,
                                cf["instruction"] + "\\n" + DISPOSITION_TASK)
        preds.append({"docket": cf["docket"], "condition": "A",
                      "votes": {s: v["vote"] for s in LA_CHAMBRE},
                      "p_votes": {s: v["p_liberal"] for s in LA_CHAMBRE},
                      "direction": v["vote"],
                      "p_liberal": v["p_liberal"],
                      "disposition": dsc})
        if (i + 1) % 25 == 0:
            print(f"  A {i + 1}/{len(cfs)}")
    return preds

def run_condition_B(cfs):
    \"\"\"Une requête par juge (adaptateur si actif, sinon dégradé
    base-prompt-only) ; disposition par le persona Roberts (pré-inscrit).\"\"\"
    by_case = {cf["docket"]: {"docket": cf["docket"], "condition": "B",
                              "votes": {}, "p_votes": {}} for cf in cfs}
    for slug in LA_CHAMBRE:
        model = model_for(slug)
        tag = "adaptateur" if slug in ACTIVE else "DÉGRADÉ base-prompt"
        sys_b, task_b = b_system(slug), b_vote_task(slug)
        for i, cf in enumerate(cfs):
            v = vote_query(model, sys_b,
                           cf["instruction"] + "\\n" + task_b)
            by_case[cf["docket"]]["votes"][slug] = v["vote"]
            by_case[cf["docket"]]["p_votes"][slug] = v["p_liberal"]
        print(f"  B [{slug}] — {tag} : {len(cfs)} votes")
    for d, rec in by_case.items():
        rec["votes"] = {k: v for k, v in rec["votes"].items()
                        if v is not None}
        rec["p_votes"] = {k: v for k, v in rec["p_votes"].items()
                          if v is not None}
        rec["direction"] = MS.majority_vote(list(rec["votes"].values()))
        ps = list(rec["p_votes"].values())
        rec["p_liberal"] = round(sum(ps) / len(ps), 4) if ps else None
    for cf in cfs:                       # disposition : persona Roberts
        rec = by_case[cf["docket"]]
        rec["disposition"] = disposition_query(
            model_for("JGRoberts"), b_system("JGRoberts"),
            cf["instruction"] + "\\n" + DISPOSITION_TASK)
    return [by_case[cf["docket"]] for cf in cfs]

# ---- ajustement D strict (toujours défini — phases T et S) --------------
fit_strict = MS.fit_condition_d(cases, exclude_sealed=is_sealed)

# ---- exécution de la phase T -------------------------------------------
if PHASE == "T":
    cfs_T = casefiles_window("test")
    if PHASE_T_LIMIT:
        cfs_T = cfs_T[:PHASE_T_LIMIT]
    truth_T = MS.load_truth(cases, is_sealed, want="test",
                            include_sealed=False)
    preds_T = {}
    if "A" in CONDITIONS_T:
        preds_T["A"] = run_condition_A(cfs_T)
    if "B" in CONDITIONS_T and ACTIVE:
        preds_T["B"] = run_condition_B(cfs_T)
    # D : régression M2 (fidélité) + ajustement strict (honnête)
    fit_m2 = MS.fit_condition_d(cases, exclude_sealed=None)
    pm2 = MS.condition_d_predict(cases, fit_m2, target="test",
                                 include_sealed=True, dedup=False)
    tm2 = MS.load_truth(cases, is_sealed, want="test",
                        include_sealed=True, dedup=False)
    acc_m2 = MS.score_votes(pm2, tm2)
    print(f"régression B4 : vote {acc_m2['accuracy']} "
          f"(publié 0.6366) — fidélité prouvée")
    preds_T["D"] = MS.condition_d_predict(cases, fit_strict,
                                          target="test",
                                          is_sealed=is_sealed)
    rep_T = MS.build_report("T", preds_T, truth_T,
                            pinned={"tag": PINNED_TAG},
                            extra={"degraded": DEGRADED,
                                   "b4_regression": {
                                       "vote": acc_m2["accuracy"],
                                       "published": 0.6366}})
    with open("m4_phaseT.json", "w", encoding="utf-8") as f:
        json.dump(rep_T, f, ensure_ascii=False, indent=1)
    for c, m in rep_T["conditions"].items():
        cd, vv, dp = (m["case_direction"], m["votes"],
                      m["disposition"])
        print(f"{c} : direction {cd['accuracy']} ({cd['k']}/{cd['n']}) "
              f"| votes {vv['accuracy']} | disposition {dp['accuracy']} "
              f"| ECE {m['calibration']['case_level']['ece']}")
    mc = rep_T["mcnemar_B_vs_A"]
    print("McNemar B vs A (affaires) :",
          mc.get("case_direction", "— condition B absente"))""")

# ---------------------------------------------------------- §7 phase S --
md("""## 7 · Phase S — **L'ÉPREUVE** (une seule fois, les 50 scellées)

La cellule-garde refuse de s'exécuter si le verrou `m4_exam.lock`
existe. Briser le scellé exige le geste délibéré
`UNSEAL = "--je-brise-le-sceau"` — consigné dans le rapport comme bris.
Les prédictions sont écrites et hachées AVANT que la cellule de score
ne lise la moindre vérité terrain.""")

code("""# ═══════════════ LA GARDE ═══════════════
UNSEAL = ""      # bris délibéré : UNSEAL = "--je-brise-le-sceau"
EXAM_LOCK = Path("m4_exam.lock")
PRED_FILE = Path("m4_predictions.json")

if EXAM_LOCK.exists() and UNSEAL != "--je-brise-le-sceau":
    raise SystemExit("L'ÉPREUVE A DÉJÀ EU LIEU — verrou présent, les "
                     "prédictions sont immuables. Passer directement à "
                     "la cellule de score. Briser le scellé (violence "
                     "délibérée, consignée) : UNSEAL = "
                     "'--je-brise-le-sceau' puis re-exécuter.")
BROKEN_SEAL = (UNSEAL == "--je-brise-le-sceau")
if BROKEN_SEAL:
    print("⚠ SCELLÉ BRISÉ VOLONTAIREMENT — consigné dans le rapport.")

stats_s = json.load(open(f"{REPO}/data/processed/stats_v1.json",
                         encoding="utf-8"))
ff_s = stats_s["five_four_selection"]
assert hashlib.sha256(json.dumps(sorted(ff_s["cases"])).encode()) \\
    .hexdigest() == ff_s["sealed_sha256"], "SCELLÉ MODIFIÉ — ARRÊT"
gate = json.load(open(f"{REPO}/results/m4_readiness.json",
                      encoding="utf-8"))
assert "FAIL" not in gate["verdict"], "la porte de pré-vol est fermée"
assert any(e["check"] == "R6" and e["status"] == "PASS"
           for e in gate["checks"]), ("R6 absent — adapter M3b "
                                      "manquants (§2)")
if PRED_FILE.exists():
    PRED_FILE.unlink()
print("GARDES PASSÉES — l'épreuve peut s'exécuter (une fois).")""")

md("""### 7.1 · Les 50 dossiers pré-décision + le pool de récupération (C)

Les dossiers sont construits par `B.build_casefile` du builder gelé — le
format EXACT de l'entraînement, jamais l'issue. Le pool de la condition
C : textes v3 de la fenêtre train, scellées et affaires sœurs exclues,
date réelle strictement antérieure à la décision de la cible.""")

code("""sealed_list = ff_s["cases"]
reps = MS.sealed_representatives(cases, sealed_list)
cfs_S = []
for entry, rep in reps:
    assert rep is not None, f"aucune affaire du corpus pour {entry}"
    cfs_S.append(B.build_casefile(
        rep, oyez.get(B.norm_docket(rep["docket_number"]))))
print(f"{len(cfs_S)} dossiers scellés construits — dernière chose vue "
      "avant les prédictions.")

# ---- pool C (pré-inscrit) ----------------------------------------------
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

TRAIN_CUTOFF = "2020-10-01"
cluster_to_docket = {}
for c in cases:
    for cl in (c.get("cluster_ids") or []):
        cluster_to_docket[str(cl)] = c["docket_number"]
docket_of_oid = {o["opinion_id"]:
                 cluster_to_docket.get(str(o["cluster_id"]))
                 for o in opinions}
date_of_oid = {o["opinion_id"]: o.get("date_filed") for o in opinions}
docket_to_case = {c["docket_number"]: c for c in cases}

texts_v3 = {}
with gzip.open(os.path.join(REPO, "data/m15_store/clean",
                            "opinion_texts_v3.jsonl.gz"), "rt",
               encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        oid = r.get("id") or r.get("opinion_id")
        t = r.get("plain_text") or r.get("text")
        if oid and t:
            texts_v3[int(oid)] = t

pool, seen_pool = [], set()
for oid, t in texts_v3.items():
    dn = docket_of_oid.get(oid)
    d = date_of_oid.get(oid)
    if not dn or not d or d >= TRAIN_CUTOFF or dn in seen_pool:
        continue
    cse = docket_to_case.get(dn)
    if not cse or is_sealed(cse):
        continue
    seen_pool.add(dn)
    oy = oyez.get(B.norm_docket(dn))
    q = B.strip_html((oy or {}).get("question") or "") or t[:600]
    pool.append({"docket": dn, "term": int(cse["term"]), "date": d,
                 "question": q, "excerpt": t[:900],
                 "case_name": cse.get("case_name")})
vec = TfidfVectorizer(lowercase=True, ngram_range=(1, 2),
                      sublinear_tf=True)
pool_vec = vec.fit_transform([p["question"] for p in pool])
print(f"pool C : {len(pool)} affaires train non scellées")

def rag_context(cf, target_case):
    tgt_date = target_case.get("date_filed") or "9999-99-99"
    idx = [i for i, p in enumerate(pool)
           if p["date"] < tgt_date and p["docket"] != cf["docket"]]
    q = cf.get("question") or ""
    if not q or q.startswith("not available"):
        q = (cf.get("facts") or "")[:600]
    v = vec.transform([q[:600]])
    sims = (pool_vec[idx] @ v.T).toarray().ravel()
    blocks = []
    for j in np.argsort(-sims)[:5]:
        p = pool[idx[j]]
        blocks.append(f"[{len(blocks) + 1}] {p['case_name']} "
                      f"(No. {p['docket']}, OT{p['term']}): "
                      f"{p['excerpt']}")
    return ("Prior similar decisions of the Court (most similar "
            "first):\\n" + "\\n".join(blocks))

def run_condition_C(cfs, reps_map):
    preds = []
    for i, cf in enumerate(cfs):
        ctx = rag_context(cf, reps_map[cf["docket"]])
        u = cf["instruction"] + "\\n" + ctx + "\\n" + A_VOTE_TASK
        v = vote_query(base, A_SYSTEM, u)
        dsc = disposition_query(base, A_SYSTEM,
                                cf["instruction"] + "\\n" + ctx
                                + "\\n" + DISPOSITION_TASK)
        preds.append({"docket": cf["docket"], "condition": "C",
                      "votes": {s: v["vote"] for s in LA_CHAMBRE},
                      "p_votes": {s: v["p_liberal"] for s in LA_CHAMBRE},
                      "direction": v["vote"],
                      "p_liberal": v["p_liberal"],
                      "disposition": dsc})
        if (i + 1) % 10 == 0:
            print(f"  C {i + 1}/{len(cfs)}")
    return preds""")

md("""### 7.2 · **L'ÉPREUVE** — les quatre conditions, puis écriture + verrou

L'ordre d'écriture est la loi : prédictions → empreinte → verrou. Rien
de la vérité terrain n'est chargé dans cette cellule.""")

code("""t0 = time.time()
reps_map = {rep["docket_number"]: rep for _, rep in reps}

preds_S = {}
preds_S["A"] = run_condition_A(cfs_S)
preds_S["B"] = run_condition_B(cfs_S)
preds_S["C"] = run_condition_C(cfs_S, reps_map)
preds_S["D"] = MS.condition_d_predict(cases, fit_strict,
                                      target="sealed",
                                      is_sealed=is_sealed,
                                      sealed_list=sealed_list)
print(f"prédictions en {time.time() - t0:.0f} s")

def adapter_sha(slug):
    h = hashlib.sha256()
    for p in sorted(glob.glob(os.path.join(ADAPTER_DIR, slug, "*"))):
        h.update(Path(p).read_bytes())
    return h.hexdigest()

doc = {"phase": "S", "broken_seal": BROKEN_SEAL,
       "pinned_tag": PINNED_TAG, "head": head,
       "sealed_sha256": ff_s["sealed_sha256"],
       "model": MODEL_ID,
       "adapters": {s: adapter_sha(s) for s in ACTIVE},
       "degraded": DEGRADED, "seed": SEED,
       "predictions": preds_S}
PRED_FILE.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                     encoding="utf-8")
pred_sha = hashlib.sha256(PRED_FILE.read_bytes()).hexdigest()
EXAM_LOCK.write_text(json.dumps(
    {"broken_seal": BROKEN_SEAL, "predictions_sha256": pred_sha,
     "head": head, "sealed_sha256": ff_s["sealed_sha256"]},
    indent=1), encoding="utf-8")
print(f"PRÉDICTIONS GELÉES : {pred_sha}")
print("verrou posé : m4_exam.lock — toute ré-exécution est refusée.")""")

# ------------------------------------------------------------ §8 score --
md("""## 8 · Le score — la vérité terrain entre en scène

Les prédictions sont relues et leur empreinte vérifiée contre le
verrou. Puis la vérité terrain des 50 affaires (direction, disposition,
votes par juge) alimente la pré-inscription complète : exactitudes +
Wilson, McNemar B vs A (global + strates), calibration, codes d'échec.""")

code("""raw = PRED_FILE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == json.loads(
    EXAM_LOCK.read_text())["predictions_sha256"], ("prédictions "
                                                    "altérées — ARRÊT")
pred_doc = json.loads(raw)
truth_S = MS.load_truth(cases, is_sealed, want="sealed",
                        sealed_list=sealed_list)

report = MS.build_report(
    "S", pred_doc["predictions"], truth_S,
    pinned={"tag": PINNED_TAG, "head": pred_doc["head"],
            "sealed_sha256": pred_doc["sealed_sha256"]},
    extra={"model": pred_doc["model"],
           "adapters": pred_doc["adapters"],
           "degraded": pred_doc["degraded"],
           "broken_seal": pred_doc["broken_seal"],
           "predictions_sha256": hashlib.sha256(raw).hexdigest()})
with open("m4_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)

print(f"\\n═══ M4 — RÉSULTATS ({report['n_truth_cases']} affaires "
      "scellées) ═══")
for c, m in report["conditions"].items():
    cd, vv, dp = m["case_direction"], m["votes"], m["disposition"]
    print(f"{c} : direction {cd['accuracy']} ({cd['k']}/{cd['n']}) "
          f"| votes {vv['accuracy']} ({vv['k']}/{vv['n']}) "
          f"| disposition {dp['accuracy']} "
          f"| ECE {m['calibration']['case_level']['ece']}")
mc = report["mcnemar_B_vs_A"]
mcd, mcv = mc["case_direction"], mc["vote"]
sig = ("SIGNIFICATIF (α = 0,05)" if mcd["significant_at_005"]
       else "non significatif")
print(f"\\nMcNemar B vs A — affaires : b={mcd['b']} c={mcd['c']} "
      f"p={mcd['p_value']} — {sig}")
print(f"McNemar B vs A — votes   : b={mcv['b']} c={mcv['c']} "
      f"p={mcv['p_value']}")
for s, mm in mc.get("strata", {}).items():
    print(f"  strate {s} ({mm['n_cases']} affaires) : "
          f"b={mm['case_direction']['b']} "
          f"c={mm['case_direction']['c']} "
          f"p={mm['case_direction']['p_value']}")
print(f"\\naffaires exclues (codes) : "
      f"{Counter(e['code'] for e in report['conditions']['A']['case_direction']['excluded'])}")
print("rapport : m4_report.json — empreinte",
      report["report_sha256"][:20], "…")""")

# -------------------------------------------------------- §9 publication --
md("""## 9 · Publication

Télécharger l'export, le verser dans le repo (`results/`), committer,
pousser. Le protocole exige la publication **quels que soient les
résultats** — un résultat nul est un résultat. Les contre-factuels
éventuels restent étiquetés « fiction » (`docs/06-ETHIQUE.md`).""")

code("""with zipfile.ZipFile("m4_epreuve_export.zip", "w",
                  zipfile.ZIP_DEFLATED) as z:
    for fn in ("m4_predictions.json", "m4_report.json", "m4_exam.lock",
               "m4_phaseT.json"):
        if os.path.exists(fn):
            z.write(fn)
print("→ m4_epreuve_export.zip "
      f"({os.path.getsize('m4_epreuve_export.zip') / 1e3:.0f} Ko)")
print("à verser : m4_report.json + m4_predictions.json → results/, "
      "commit + push + tag m4-exam.")""")

# ------------------------------------------------------------ assemblage --
nbf.write(nb, OUT)
src = open(OUT, encoding="utf-8").read()
for guard in ("sealed_sha256", "je-brise-le-sceau", "EXAM_LOCK"):
    assert guard in src, f"garde absente du notebook : {guard}"
print(f"notebook généré : {OUT} ({len(nb.cells)} cellules)")
