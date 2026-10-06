#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A1 — E1 + E3 : décomposition causale du dial + auto-cohérence.

*Legally Subjective*, phase 1 de l'enquête asymétrie (D1-bis, mandat du
propriétaire). Pré-enregistrement : `docs/15-ASYMETRIE-PHASE1-
PREENREGISTREMENT.md` §2 (copie conforme de download/
m4_asymetrie_phase0.md, figée par le commit du tag `a1-freeze` AVANT
toute exécution GPU).

ÉTIQUETTES (séparation confirmatoire / exploratoire, exigée par le mandat) :
  * E1 — confirmatoire DANS son propre cadre (fenêtre transparente,
    hypothèses inscrites au préalable), SANS retombée sur le test primaire
    M4 (McNemar B vs A, affaires — jamais recalculé ici).
  * E3 — exploratoire (le persona vote-t-il comme le juge sur SES
    propres affaires de la fenêtre train ?).

GARDE-FOUS :
  * Le protocole M4 primaire n'est pas modifié ; les fichiers publiés
    results/m4_*.json ne sont jamais réécrits (les sorties sont préfixées
    a1_). results/m4_phaseT.json n'est ici que LU (régression).
  * Les 50 affaires scellées ne sont JAMAIS invoquées comme évaluation
    ni comme entraînement : E1/E3 ne couvrent que la fenêtre transparente
    (casefiles window=='test', scellées exclues PAR CONSTRUCTION par le
    builder gelé) et la fenêtre train (window=='train', pré-garde,
    publique). Le scellé n'est chargé que pour l'assertion d'intégrité
    (recalcul SHA-256, identique au notebook M4 §2) et l'exclusion.
  * Aucun ré-entraînement ; adaptateurs = zip authentifié
    m3b_adapters_final.zip (sha256 f46d07f7…, lignage 14/14).
  * Seed fixe ; scoring contraint déterministe (aucun échantillonnage) ;
    journaux complets ; résultats publiés QUELS QU'ILS SOIENT.

NOTES D'IMPLÉMENTATION (clarifications opérationnelles, pré-exécution,
consignées aussi dans l'addendum du document de pré-enregistrement) :
  * Bras N (neutre) : la requête ne contient AUCUNE identité de siège —
    par construction le résultat N est indépendant du siège. Le plan
    pré-enregistré décrit « une requête de vote identique par affaire
    sous trois system prompts » pour chaque siège ; pour le bras N cette
    requête est la même pour les neuf sièges, elle est donc calculée UNE
    fois par affaire puis répliquée aux neuf sièges — exactement le
    schéma de run_condition_A du notebook gelé (cond. A = « pas
    d'information par juge », vote d'affaire répliqué aux 9 sièges).
    Vérification de déterminisme incluse (fumée N exécutée deux fois).
  * Fenêtre transparente : 211 casefiles test (le chiffre « 205 » du
    document de phase 0 = affaires avec vérité direction ; la fenêtre
    complète du builder gelé = 211). E1 court sur les 211 — mesures du
    dial sans vérité requise ; les précisions supplémentaires se
    calculent sur les 205 avec vérité, comme en phase T.
  * Bras P = prompt biographique du siège SANS adaptateur (mode dégradé
    pré-inscrit de M4 — identique en octets aux requêtes des sièges
    dégradés de la phase T) ; bras A = même prompt + adaptateur du siège
    (7 sièges ; Barrett/Jackson : bras A inexistant par construction).
"""
import glob
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from collections import Counter, defaultdict

PINNED_TAG = "a1-freeze"
EXPECTED_ZIP_SHA = ("f46d07f757f2ec410e5f092ae09e1696bef6ef5"
                    "af377b39b2d0154b5067a2a5b")
SEED = 271828
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SCRIPT_DIR)
CWD = os.getcwd()

# évaluation de la prédiction pré-inscrite (ii) — camp idéologique
LIBERALS = ["SSotomayor", "EKagan", "KBJackson"]

ADAPTED_SEATS = ["BMKavanaugh", "CThomas", "EKagan", "JGRoberts",
                 "NMGorsuch", "SAAlito", "SSotomayor"]

T0 = time.time()


def log(msg):
    print(f"[a1 +{time.time() - T0:6.0f}s] {msg}", flush=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(name, obj):
    path = os.path.join(CWD, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return {"file": name, "sha256": sha256_file(path),
            "bytes": os.path.getsize(path)}


# ------------------------------------------------------------- 0 · deps ----
def ensure_deps():
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                        "transformers>=4.55,<5", "peft>=0.16",
                        "bitsandbytes>=0.47.0,<0.51", "accelerate>=1.5"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        log("ÉCHEC pip install\n" + r.stderr[-800:])
        sys.exit(2)
    import torch
    assert torch.cuda.is_available(), "GPU requis"
    log(f"GPU : {torch.cuda.get_device_name(0)} "
        f"(bf16 : {torch.cuda.is_bf16_supported()})")
    return torch


# ------------------------------------------------- 1 · gardes provenance --
def guard_provenance():
    """Tag gelé, scellé intègre (recalcul), zip adaptateurs authentifié."""
    head = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    tag = subprocess.run(["git", "-C", REPO, "describe", "--tags"],
                         capture_output=True, text=True).stdout.strip()
    if tag != PINNED_TAG:
        log(f"ERREUR FATALE : describe = {tag!r} ≠ {PINNED_TAG!r}")
        sys.exit(2)
    log(f"gel : {tag} @ {head[:12]}")

    stats = json.load(open(os.path.join(REPO, "data/processed/stats_v1.json"),
                           encoding="utf-8"))
    ff = stats["five_four_selection"]
    recomputed = hashlib.sha256(
        json.dumps(sorted(ff["cases"])).encode()).hexdigest()
    assert recomputed == ff["sealed_sha256"], "SCELLÉ MODIFIÉ — ARRÊT"
    log(f"scellé intègre (assertion) : {ff['sealed_sha256'][:20]}… "
        f"({len(ff['cases'])} entrées — jamais invoquées ci-dessous)")

    # zip authentifié (le wrapper l'a déposé au CWD ; re-vérifié ici)
    cands = ([os.path.join(CWD, "m3b_adapters_final.zip")]
             if os.path.isfile(os.path.join(CWD, "m3b_adapters_final.zip"))
             else sorted(glob.glob(os.path.join(CWD, "m3b_adapters_*.zip")))
             + [p for p in sorted(glob.glob(
                 "/kaggle/input/**/m3b_adapters_final.zip",
                 recursive=True))])
    if not cands:
        log("ERREUR FATALE : zip adaptateurs introuvable")
        sys.exit(2)
    zip_path = cands[0]
    zip_sha = sha256_file(zip_path)
    if zip_sha != EXPECTED_ZIP_SHA:
        log(f"ERREUR FATALE : sha zip {zip_sha} ≠ {EXPECTED_ZIP_SHA}")
        sys.exit(2)
    log(f"zip adaptateurs authentifié : {zip_sha[:16]}…")

    adapter_dir = os.path.join(REPO, "adapters")
    if not glob.glob(os.path.join(adapter_dir, "*", "*")):
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(adapter_dir)
        inner = os.path.join(adapter_dir, "m3b_report.json")
        if os.path.exists(inner):
            os.replace(inner, os.path.join(REPO, "m3b_report.json"))
        log("zip décompressé dans le clone (non suivi par git)")
    return {"tag": tag, "head": head, "adapters_zip_sha256": zip_sha}


# ------------------------------------------------------------- 2 · données -
def load_data():
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import m3_build_datasets as B          # builder gelé — prompts EXACTS
    import m4_scoring as MS                # pré-inscription M4 (lecture)

    cases, opinions, stats, amap = B.load_corpus()
    is_sealed = B.sealed_dockets(stats)
    la_chambre = list(B.LA_CHAMBRE)

    cfs_test, cfs_train = [], {}
    for p in sorted(glob.glob(os.path.join(REPO, "data/m3/casefiles",
                                           "*.json"))):
        cf = json.load(open(p, encoding="utf-8"))
        if cf.get("window") == "test":
            cfs_test.append(cf)
        elif cf.get("window") == "train":
            cfs_train[cf["docket"]] = cf

    # garde anti-fuite : aucun docket E1/E3 ne touche le scellé
    leaks = [cf["docket"] for cf in cfs_test + list(cfs_train.values())
             if is_sealed({"docket_number": cf["docket"]})]
    assert not leaks, f"FUITES SCELLÉ : {leaks[:5]}"
    log(f"garde anti-fuite : 0/632 dockets E1+E3 dans le scellé")

    truth_T = MS.load_truth(cases, is_sealed, want="test",
                            include_sealed=False)
    n_truth_dir = sum(1 for t in truth_T if t.get("direction"))
    log(f"E1 : {len(cfs_test)} casefiles transparents, "
        f"{n_truth_dir} avec vérité direction")

    # lignes d'entraînement personas (fenêtre train, pré-garde, publique)
    train_rows = {}
    for slug in ADAPTED_SEATS:
        path = os.path.join(REPO, "data/m3/personas", slug, "train.jsonl")
        train_rows[slug] = [json.loads(l) for l in open(path,
                                                        encoding="utf-8")]
    n_dock = sum(len({r["docket"] for r in rs})
                 for rs in train_rows.values())
    log(f"E3 : {n_dock} dockets train distincts (7 sièges adaptés)")

    docket_to_case = {c["docket_number"]: c for c in cases}
    return {"B": B, "MS": MS, "cases": cases, "is_sealed": is_sealed,
            "la_chambre": la_chambre, "cfs_test": cfs_test,
            "cfs_train": cfs_train, "truth_T": truth_T,
            "train_rows": train_rows, "docket_to_case": docket_to_case}


# ------------------------------------------------------------- 3 · modèle --
def load_models():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    import torch

    report_path = os.path.join(REPO, "m3b_report.json")
    if os.path.exists(report_path):
        report = json.load(open(report_path, encoding="utf-8"))
        model_id = report["model"]
    else:
        model_id = "Qwen/Qwen2.5-3B-Instruct"
    log(f"modèle de l'entraînement : {model_id}")

    tok = AutoTokenizer.from_pretrained(model_id)
    base = AutoModelForCausalLM.from_pretrained(
        model_id, load_in_4bit=True, device_map="auto",
        torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported()
        else torch.float16)

    trained = {r["persona"] for r in (report.get("results", [])
                                      if os.path.exists(report_path) else [])}
    have = {os.path.basename(p) for p in glob.glob(
        os.path.join(REPO, "adapters", "*")) if os.path.isdir(p)}
    active = sorted(trained & have)
    if active != sorted(ADAPTED_SEATS):
        log(f"ERREUR FATALE : adaptateurs actifs {active} ≠ "
            f"{sorted(ADAPTED_SEATS)}")
        sys.exit(2)
    log(f"adaptateurs actifs ({len(active)}) : {', '.join(active)}")

    _loaded = {}

    def model_for(slug):
        if slug is None or slug not in active:
            return base
        if slug not in _loaded:
            _loaded[slug] = PeftModel.from_pretrained(
                base, os.path.join(REPO, "adapters", slug))
        return _loaded[slug]

    return tok, base, active, model_for, model_id


# ---------------------------------------------------- 4 · scoring verbatim -
# Primitif et prompts COPIÉS VERBATIM du notebook gelé M4 (cellule 10) —
# identité d'octet garantie avec l'épreuve (et l'entraînement pour B).
A_SYSTEM = ("You are a careful, neutral analyst of the U.S. Supreme "
            "Court. You read the case file exactly as it was before the "
            "Court decided, and you answer as an expert in Court "
            "practice.")
A_VOTE_TASK = ("State the direction of the decisive vote on the question "
               "presented: conservative or liberal. Answer with exactly "
               "one word.")


def make_queries(tok, base, model_for, data):
    B = data["B"]
    import torch

    def b_system(slug):
        return B.PERSONA_SYSTEM.format(
            name=B.FULL_NAMES[slug],
            role=B.ROLE_OF.get(slug, "Associate Justice"))

    def b_vote_task(slug):
        return B.VOTE_TASK.format(name=B.FULL_NAMES[slug])

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
        return {"vote": max(p, key=p.get),
                "p_liberal": round(p["liberal"], 4)}

    return b_system, b_vote_task, vote_query


# --------------------------------------------------------- 5 · E1 (exéc.) --
def run_E1(data, b_system, b_vote_task, vote_query, model_for, base):
    """3 bras sur la fenêtre transparente. N : 1 requête/affaire
    (indépendante du siège par construction), répliquée aux 9 sièges ;
    P : prompt biographique sans adaptateur (base) ; A : prompt +
    adaptateur (7 sièges). Points de contrôle JSONL au fil de l'eau."""
    cfs = data["cfs_test"]
    la_chambre = data["la_chambre"]
    out = {"N": [], "P": [], "A": []}
    ckpt = os.path.join(CWD, "a1_e1_predictions.jsonl")
    t_start = time.time()
    n_q = 0

    def emit(rec):
        nonlocal n_q
        n_q += 1
        with open(ckpt, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---- bras N (neutre — condition A du gel, répliquée aux sièges) ----
    for i, cf in enumerate(cfs):
        u = cf["instruction"] + "\n" + A_VOTE_TASK
        v = vote_query(base, A_SYSTEM, u)
        rec = {"arm": "N", "docket": cf["docket"], "seat": None,
               "vote": v["vote"], "p_liberal": v["p_liberal"]}
        out["N"].append(rec)
        emit(rec)
        if (i + 1) % 25 == 0:
            log(f"  E1 N {i + 1}/{len(cfs)}")
    log(f"bras N terminé : {len(out['N'])} requêtes")

    # ---- bras P (biographique, base — mode dégradé du gel) --------------
    for k, slug in enumerate(la_chambre):
        sys_p, task_p = b_system(slug), b_vote_task(slug)
        for i, cf in enumerate(cfs):
            v = vote_query(base, sys_p, cf["instruction"] + "\n" + task_p)
            rec = {"arm": "P", "docket": cf["docket"], "seat": slug,
                   "vote": v["vote"], "p_liberal": v["p_liberal"]}
            out["P"].append(rec)
            emit(rec)
            if (i + 1) % 50 == 0:
                log(f"  E1 P [{slug}] {i + 1}/{len(cfs)}")
        log(f"bras P [{slug}] terminé ({k + 1}/9)")

    # ---- bras A (adaptateur, 7 sièges) ------------------------------------
    for k, slug in enumerate(ADAPTED_SEATS):
        model = model_for(slug)
        sys_b, task_b = b_system(slug), b_vote_task(slug)
        for i, cf in enumerate(cfs):
            v = vote_query(model, sys_b, cf["instruction"] + "\n" + task_b)
            rec = {"arm": "A", "docket": cf["docket"], "seat": slug,
                   "vote": v["vote"], "p_liberal": v["p_liberal"]}
            out["A"].append(rec)
            emit(rec)
            if (i + 1) % 50 == 0:
                log(f"  E1 A [{slug}] {i + 1}/{len(cfs)}")
        log(f"bras A [{slug}] terminé ({k + 1}/7)")

    return out, {"n_queries": n_q, "duration_s": round(time.time() - t_start, 1)}


# ------------------------------------------------------ 6 · E1 (analyse) ---
def arm_records(arm, recs, la_chambre):
    """Condition-style records (format run_condition_B) pour MS.score_votes.
    N : vote répliqué aux 9 sièges (schéma run_condition_A du gel)."""
    by_case = {}
    for r in recs:
        d = by_case.setdefault(r["docket"], {"docket": r["docket"],
                                             "votes": {}, "p_votes": {}})
        if arm == "N":
            for s in la_chambre:
                d["votes"][s] = r["vote"]
                d["p_votes"][s] = r["p_liberal"]
        else:
            d["votes"][r["seat"]] = r["vote"]
            d["p_votes"][r["seat"]] = r["p_liberal"]
    return list(by_case.values())


def analyse_E1(data, e1_recs, timings, pinned, versions):
    MS = data["MS"]
    la_chambre = data["la_chambre"]
    truth_T = data["truth_T"]

    measures = {}
    for slug in la_chambre:
        m = {}
        for arm in ("N", "P", "A"):
            recs = [r for r in e1_recs[arm]
                    if arm == "N" or r["seat"] == slug]
            if arm == "N":
                recs = e1_recs["N"]          # indépendant du siège
            if not recs:
                m[arm] = None
                continue
            m[arm] = {
                "n": len(recs),
                "rate_liberal": round(
                    sum(1 for r in recs if r["vote"] == "liberal")
                    / len(recs), 4),
                "mean_p_liberal": round(
                    sum(r["p_liberal"] for r in recs) / len(recs), 4),
            }
        entry = {"N": m["N"], "P": m["P"], "A": m["A"]}
        if m["N"] and m["P"]:
            entry["delta_P_minus_N"] = {
                "rate_liberal": round(m["P"]["rate_liberal"]
                                      - m["N"]["rate_liberal"], 4),
                "mean_p_liberal": round(m["P"]["mean_p_liberal"]
                                        - m["N"]["mean_p_liberal"], 4)}
        if m["A"] and m["P"]:
            entry["delta_A_minus_P"] = {
                "rate_liberal": round(m["A"]["rate_liberal"]
                                      - m["P"]["rate_liberal"], 4),
                "mean_p_liberal": round(m["A"]["mean_p_liberal"]
                                        - m["P"]["mean_p_liberal"], 4)}
        measures[slug] = entry

    # ---- évaluation des prédictions pré-inscrites ------------------------
    n_rate = {s: measures[s]["N"]["rate_liberal"] for s in la_chambre}
    dpn = {s: measures[s]["delta_P_minus_N"]["rate_liberal"]
           for s in la_chambre}
    dap = {s: (measures[s]["delta_A_minus_P"]["rate_liberal"]
               if measures[s].get("delta_A_minus_P") else None)
           for s in la_chambre}

    pred_i = {"per_seat": n_rate,
              "confirmed": all(v < 0.5 for v in n_rate.values())}
    lib_d = [dpn[s] for s in LIBERALS]
    cons_d = [dpn[s] for s in la_chambre if s not in LIBERALS]
    pred_ii = {"delta_P_minus_N": dpn,
               "liberals": LIBERALS,
               "confirmed_liberals_positive": all(v > 0 for v in lib_d),
               "mean_delta_liberals": round(sum(lib_d) / len(lib_d), 4),
               "mean_delta_conservatives": round(
                   sum(cons_d) / len(cons_d), 4),
               "confirmed_contrast": (sum(lib_d) / len(lib_d)
                                      > sum(cons_d) / len(cons_d))}
    pred_iii = {"delta_A_minus_P": {s: dap[s] for s in ADAPTED_SEATS},
                "targets": ["EKagan", "SSotomayor"],
                "confirmed": all(dap[s] < 0 for s in ["EKagan",
                                                     "SSotomayor"])}

    # ---- suppléments NON pré-inscrits (précisions + régressions) --------
    accs = {}
    for arm in ("N", "P", "A"):
        if not e1_recs[arm]:
            continue
        recs = arm_records(arm, e1_recs[arm], la_chambre)
        accs[arm] = MS.score_votes(recs, truth_T)["per_justice"]

    # régression vs phase T publiée (mêmes prompts/adaptateurs/scoring →
    # les précisions par juge doivent être EXACTEMENT celles de la phase T)
    phaseT_path = os.path.join(REPO, "results/m4_phaseT.json")
    regression = {"note": ("arm A ≡ condition B phase T (7 sièges adaptés) ; "
                           "arm P (Barrett/Jackson) ≡ condition B dégradée ; "
                           "arm N ≡ condition A (vote répliqué). Scoring "
                           "déterministe → égalité exacte attendue."),
                  "armA_vs_phaseT_B": {}, "armP_degraded_vs_phaseT_B": {},
                  "armN_vs_phaseT_A": {}, "all_match": None}
    if os.path.exists(phaseT_path):
        pt = json.load(open(phaseT_path, encoding="utf-8"))
        ptB = pt["conditions"]["B"]["votes"]["per_justice"]
        ptA = pt["conditions"]["A"]["votes"]["per_justice"]
        ok = True
        for s in ADAPTED_SEATS:
            a1v = accs["A"].get(s, {}).get("accuracy")
            match = (a1v is not None
                     and a1v == ptB.get(s, {}).get("accuracy"))
            regression["armA_vs_phaseT_B"][s] = {
                "a1": a1v, "phaseT": ptB.get(s, {}).get("accuracy"),
                "match": bool(match)}
            ok &= bool(match)
        for s in ("ACBarrett", "KBJackson"):
            a1v = accs["P"].get(s, {}).get("accuracy")
            match = (a1v is not None
                     and a1v == ptB.get(s, {}).get("accuracy"))
            regression["armP_degraded_vs_phaseT_B"][s] = {
                "a1": a1v, "phaseT": ptB.get(s, {}).get("accuracy"),
                "match": bool(match)}
            ok &= bool(match)
        any_seat = la_chambre[0]
        a1v = accs["N"].get(any_seat, {}).get("accuracy")
        match = (a1v is not None
                 and a1v == ptA.get(any_seat, {}).get("accuracy"))
        regression["armN_vs_phaseT_A"] = {
            "a1": a1v, "phaseT": ptA.get(any_seat, {}).get("accuracy"),
            "match": bool(match)}
        ok &= bool(match)
        regression["all_match"] = bool(ok)
        log(f"régression phase T : all_match = {regression['all_match']}")

    # B4 (fidélité de la machinerie vérité — copie notebook §6)
    fit_m2 = MS.fit_condition_d(data["cases"], exclude_sealed=None)
    pm2 = MS.condition_d_predict(data["cases"], fit_m2, target="test",
                                 include_sealed=True, dedup=False)
    tm2 = MS.load_truth(data["cases"], data["is_sealed"], want="test",
                        include_sealed=True, dedup=False)
    b4 = {"vote": MS.score_votes(pm2, tm2)["accuracy"],
          "published": 0.6366}

    return {
        "schema": "a1-e1/1",
        "experiment": ("E1 — décomposition causale du dial "
                       "(prompt-swap, 3 bras N/P/A, fenêtre transparente)"),
        "label": ("confirmatoire DANS son propre cadre (hypothèses "
                  "pré-inscrites) — SANS retombée sur le test primaire M4"),
        "preregistration": ("docs/15-ASYMETRIE-PHASE1-PREENREGISTREMENT.md "
                            "§2 E1 — figé au tag a1-freeze avant exécution"),
        "pinned": dict(pinned, seed=SEED, versions=versions),
        "window": {
            "n_casefiles": len(data["cfs_test"]),
            "n_truth_direction": sum(1 for t in truth_T
                                     if t.get("direction")),
            "sealed_leaks": 0,
            "note": ("205 = affaires avec vérité direction (phase T) ; la "
                     "fenêtre complète du builder gelé = 211 casefiles, "
                     "tous utilisés pour les mesures du dial."),
        },
        "predictions_preregistrees_verbatim": {
            "(i)": "le bras N présente un défaut conservateur pour tous "
                   "les sièges",
            "(ii)": "Δ(P−N) est positif pour les libéraux, faible pour "
                    "les conservateurs",
            "(iii)": "Δ(A−P) est négatif pour Kagan et Sotomayor "
                     "(l'adaptateur efface le gain du prompt)",
        },
        "preinscribed_evaluation": {
            "(i)_defaut_conservateur_N": pred_i,
            "(ii)_effet_prompt": pred_ii,
            "(iii)_effet_adaptateur": pred_iii,
        },
        "measures": measures,
        "supplements_non_preinscrits": {
            "label": "exploratoire (non couvert par le pré-enregistrement)",
            "accuracy_vote_par_juge_par_bras": accs,
            "regression_phase_T": regression,
            "b4_regression": b4,
        },
        "timings": timings,
    }


# --------------------------------------------------------- 7 · E3 (exéc.) --
def run_E3(data, b_system, b_vote_task, vote_query, model_for):
    """Auto-cohérence : le persona (bras A) vote sur les affaires TRAIN où
    le juge a réellement signé (le texte a servi à l'entraînement) et voté
    (vérité pré-garde publique). Une requête par docket distinct."""
    out = []
    ckpt = os.path.join(CWD, "a1_e3_predictions.jsonl")
    t_start = time.time()
    n_q = 0
    docket_to_case = data["docket_to_case"]
    cfs_train = data["cfs_train"]

    for k, slug in enumerate(ADAPTED_SEATS):
        rows = data["train_rows"][slug]
        dockets = sorted({r["docket"] for r in rows})
        types_by_docket = defaultdict(set)
        for r in rows:
            types_by_docket[r["docket"]].add(r["type"])
        model = model_for(slug)
        sys_b, task_b = b_system(slug), b_vote_task(slug)
        done = 0
        for d in dockets:
            cf = cfs_train.get(d)
            if cf is None:
                continue                # sans casefile : non requêtable
            c = docket_to_case.get(d)
            jj = next((j for j in (c.get("justices") or [])
                       if j["justice"] == slug), None) if c else None
            truth = ("liberal" if jj.get("direction") == "2"
                     else "conservative" if jj.get("direction") == "1"
                     else None) if jj else None
            v = vote_query(model, sys_b, cf["instruction"] + "\n" + task_b)
            rec = {"seat": slug, "docket": d, "vote": v["vote"],
                   "p_liberal": v["p_liberal"], "truth_vote": truth,
                   "types_authored": sorted(types_by_docket[d]),
                   "term": cf.get("term")}
            out.append(rec)
            n_q += 1
            with open(ckpt, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            done += 1
        log(f"E3 [{slug}] : {done} dockets requêtés ({k + 1}/7)")
    return out, {"n_queries": n_q,
                 "duration_s": round(time.time() - t_start, 1)}


# ------------------------------------------------------ 8 · E3 (analyse) ---
def analyse_E3(e3_recs, timings, pinned, versions):
    per_judge = {}
    for slug in ADAPTED_SEATS:
        recs = [r for r in e3_recs if r["seat"] == slug]
        with_t = [r for r in recs if r["truth_vote"]]
        n = len(with_t)
        acc = (sum(1 for r in with_t
                   if r["vote"] == r["truth_vote"]) / n) if n else None

        def sub(sel):
            s = [r for r in with_t if sel(r)]
            if not s:
                return {"n": 0, "persona_liberal_rate": None,
                        "accuracy": None}
            return {"n": len(s),
                    "persona_liberal_rate": round(
                        sum(1 for r in s if r["vote"] == "liberal")
                        / len(s), 4),
                    "accuracy": round(
                        sum(1 for r in s if r["vote"] == r["truth_vote"])
                        / len(s), 4)}

        by_type = {t: sub(lambda r, t=t: t in r["types_authored"])
                   for t in ("lead", "dissent", "concurrence",
                             "concurrence-dissent")}
        per_judge[slug] = {
            "n_dockets_queried": len(recs),
            "n_with_truth": n,
            "accuracy_on_own_train_cases": round(acc, 4) if acc else None,
            "persona_liberal_rate_on_own_cases": round(
                sum(1 for r in with_t if r["vote"] == "liberal") / n, 4)
            if n else None,
            "real_liberal_votes": sum(1 for r in with_t
                                      if r["truth_vote"] == "liberal"),
            "by_real_vote": {
                "liberal": sub(lambda r: r["truth_vote"] == "liberal"),
                "conservative": sub(lambda r: r["truth_vote"]
                                    == "conservative"),
            },
            "by_authored_type": by_type,
            "probe_real_liberal_and_lead_author": sub(
                lambda r: r["truth_vote"] == "liberal"
                and "lead" in r["types_authored"]),
        }

    kagan = per_judge.get("EKagan", {})
    probe = kagan.get("probe_real_liberal_and_lead_author", {})
    return {
        "schema": "a1-e3/1",
        "experiment": ("E3 — auto-cohérence : le persona vote-t-il comme "
                       "le juge sur SES propres affaires de train ?"),
        "label": "exploratoire",
        "preregistration": ("docs/15-ASYMETRIE-PHASE1-PREENREGISTREMENT.md "
                            "§2 E3 — figé au tag a1-freeze avant exécution"),
        "pinned": dict(pinned, seed=SEED, versions=versions),
        "note": ("Le probe central (pré-enregistré) : affaires où le juge "
                 "a réellement voté libéral EN SIGNANT une opinion lead "
                 "dont le texte a servi à l'entraînement — si le persona "
                 "vote conservateur là, l'échec est auto-probé."),
        "per_judge": per_judge,
        "kagan_probe": {
            "description": ("EKagan, votes libéraux réels + opinion lead "
                            "signée (texte vu à l'entraînement)"),
            **probe,
        },
        "timings": timings,
    }


# ------------------------------------------------------------- 9 · main ----
def main():
    log("═══ A1 — E1+E3 (D1-bis) : wrapper opérationnel, science du tag "
        "a1-freeze exécutée verbatim ═══")
    provenance = guard_provenance()
    torch = ensure_deps()
    torch.manual_seed(SEED)

    data = load_data()
    tok, base, active, model_for, model_id = load_models()
    b_system, b_vote_task, vote_query = make_queries(tok, base, model_for,
                                                     data)

    # fumées : 1 affaire × 3 bras + déterminisme N (deux exécutions)
    cf0 = data["cfs_test"][0]
    v_n1 = vote_query(base, A_SYSTEM, cf0["instruction"] + "\n" + A_VOTE_TASK)
    v_n2 = vote_query(base, A_SYSTEM, cf0["instruction"] + "\n" + A_VOTE_TASK)
    assert v_n1 == v_n2, f"NON-DÉTERMINISME N : {v_n1} vs {v_n2}"
    v_p = vote_query(base, b_system("EKagan"),
                     cf0["instruction"] + "\n" + b_vote_task("EKagan"))
    v_a = vote_query(model_for("EKagan"), b_system("EKagan"),
                     cf0["instruction"] + "\n" + b_vote_task("EKagan"))
    log(f"fumées : N={v_n1} (déterminisme OK) | P[Kagan]={v_p} | "
        f"A[Kagan]={v_a}")

    import transformers, peft
    versions = {"python": sys.version.split()[0],
                "torch": torch.__version__,
                "transformers": transformers.__version__,
                "peft": peft.__version__,
                "gpu": torch.cuda.get_device_name(0)}
    pinned = dict(provenance, model=model_id, started_utc=time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    # ---- E1 ---------------------------------------------------------------
    e1_recs, e1_timings = run_E1(data, b_system, b_vote_task, vote_query,
                                  model_for, base)
    log("E1 exécuté — analyse (pré-inscrite + suppléments)")
    e1_report = analyse_E1(data, e1_recs, e1_timings, pinned, versions)

    # ---- E3 ---------------------------------------------------------------
    e3_recs, e3_timings = run_E3(data, b_system, b_vote_task, vote_query,
                                  model_for)
    log("E3 exécuté — analyse")
    e3_report = analyse_E3(e3_recs, e3_timings, pinned, versions)

    # ---- sorties (publication quels que soient les résultats) -------------
    outputs = {
        "e1_decomposition": write_json("a1_e1_decomposition.json", e1_report),
        "e3_autocoherence": write_json("a1_e3_autocoherence.json", e3_report),
        "e1_predictions": write_json(
            "a1_e1_predictions.json",
            {"schema": "a1-e1-pred/1", "predictions": e1_recs}),
        "e3_predictions": write_json(
            "a1_e3_predictions.json",
            {"schema": "a1-e3-pred/1", "predictions": e3_recs}),
    }
    manifest = {
        "experiment": "A1 — E1+E3 (D1-bis, plan pré-enregistré phase 1)",
        "status": "OK",
        "pinned": pinned,
        "versions": versions,
        "queries": {"e1": e1_timings["n_queries"],
                    "e3": e3_timings["n_queries"],
                    "total": e1_timings["n_queries"]
                    + e3_timings["n_queries"]},
        "timings_s": {"e1": e1_timings["duration_s"],
                      "e3": e3_timings["duration_s"],
                      "total": round(time.time() - T0, 1)},
        "outputs": outputs,
        "smoke": {"N": v_n1, "P_Kagan": v_p, "A_Kagan": v_a,
                  "determinism_N": True},
        "labels": {"E1": "confirmatoire dans son propre cadre",
                   "E3": "exploratoire"},
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                      time.gmtime()),
    }
    outputs["run_manifest"] = write_json("a1_run_manifest.json", manifest)
    log("artefacts : " + json.dumps(
        {k: v["sha256"][:12] for k, v in outputs.items()}))
    log(f"═══ A1 E1+E3 : OK ({manifest['timings_s']['total']} s, "
        f"{manifest['queries']['total']} requêtes) ═══")
    return 0


if __name__ == "__main__":
    sys.exit(main())
