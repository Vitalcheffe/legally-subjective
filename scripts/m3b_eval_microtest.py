#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M3b MICRO-TEST D'ÉVALUATION (rituel de réparation).

Objectif UNIQUE (LS-17, post-s1) : démontrer que le défaut déterministe
observé en s1 — OOM CUDA à la PREMIÈRE évaluation (EVAL_EVERY=20,
per_device_eval_batch_size héritant du défaut HF = 8 à MAX_LEN=4096 sur
T4 15,6 Go, allocation 8,00 GiB réclamée d'un coup) — est SUPPRIMÉ par
le correctif per_device_eval_batch_size=1.

Session d'AUDIT, pas de production :
  - aucun pas d'entraînement consommé ;
  - aucun état scientifique écrit (les racines s1 sont copiées depuis la
    sortie du kernel s1 en lecture seule ; la sortie de CE kernel n'est
    pas une racine de production) ;
  - sortie = rapport JSON + console.

Chaîne de preuve :
  0. bootstrap identique au runner (pins, dépôt au commit épinglé,
     gel 12/12 in situ, audit zéro-fuite 14/14 in situ, scellé M4,
     poids HF officiels re-hashés) ;
  1. cellules gelées exécutées VERBATIM (imports → … → state_5bis) ;
  2. pour chaque juge tombé en OOM d'évaluation en s1 (NMGorsuch,
     EKagan, SAAlito) :
       restore_ckpt_local (machinerie officielle, manifeste vérifié) ;
       PeftModel.from_pretrained(base, ckpt) — rechargement réel ;
       TrainingArguments EXACT = fragment balancé extrait de la cellule
       gelée CORRIGÉE et ré-exécuté (sha256 du fragment comparé au gel
       du protocole → preuve que l'évaluation tourne sous le protocole
       corrigé, octet pour octet) ;
       Trainer(...).evaluate() — VRAIE évaluation (boucle Trainer,
       dataloader batch 1, perte de validation agrégée) ;
  3. Kavanaugh (terminé en s1 sans évaluation) : adaptateur promu →
     rechargement + forward logits finis (miroir de finalize_judge) ;
  4. rapport + terminaison propre.

Aucun secret dans ce fichier.
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import time

REPO_URL = "https://github.com/Vitalcheffe/legally-subjective.git"
REPO_COMMIT = "960279ec1acabe23d9bbf58bb53b01aacf247138"   # correctif eval batch
REPO_PATH = "/tmp/legally-subjective"
WORKING = "/kaggle/working"
OUT_JSON = os.path.join(WORKING, "m3b_eval_microtest_result.json")

HF_OFFICIAL_SHA256 = {
    "model-00001-of-00002.safetensors":
        "67347b23fb4165b652eb6611f5e1f2a06dfcddba8e909df1b2b0b1857bee06c2",
    "model-00002-of-00002.safetensors":
        "a40d941d0e7e0b966ad8b62bb6d6b7c88cce1299197b599d9d0a4ce59aabfc1d",
}
PIP_PINS = ["transformers==4.49.0", "peft==0.13.2",
            "bitsandbytes>=0.47.0,<0.51", "accelerate==1.2.1",
            "datasets==3.1.0", "sentencepiece", "protobuf"]

MARKERS = {
    "imports": "SEED = 42",
    "config": "CONFIG = {",
    "personas_dir": "PERSONAS_DIR =",
    "load_persona": "def load_persona",
    "temporal_split": "def temporal_split",
    "tokenization": "def encode_row",
    "dataset": "class PersonaTorch",
    "qlora": "bnb_cfg = BitsAndBytesConfig",
    "state_5bis": "M3B.fingerprint_of(CONFIG)",
    "train_6": "def train_one",
}

JUDGES_OOM = {"w1": ["NMGorsuch", "SAAlito"], "w0": ["EKagan"]}
JUDGE_DONE = ("w0", "BMKavanaugh")            # adaptateur promu : forward seul


def log(msg):
    print(f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')}] "
          f"{msg}", flush=True)


def sh(cmd, timeout=3600, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(
            f"commande en échec ({cmd[:3]}…) rc={r.returncode}\n"
            f"stdout: {r.stdout[-2000:]}\nstderr: {r.stderr[-2000:]}")
    return r


def sha256_file(p, chunk=1 << 20):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(chunk), b""):
            h.update(c)
    return h.hexdigest()


# ----------------------------------------------------------------- préparation
def acquire_repo():
    if os.path.exists(REPO_PATH):
        shutil.rmtree(REPO_PATH)
    inp = "/kaggle/input"
    tar_path = None
    if os.path.isdir(inp):
        for root, dirs, files in os.walk(inp):
            if root.count(os.sep) - inp.count(os.sep) > 4:
                dirs[:] = []
                continue
            for f in sorted(files):
                if f.endswith((".tar.bin", ".tar.gz", ".tgz")) and \
                        "legally-subjective-repo" in f:
                    tar_path = os.path.join(root, f)
                    break
            if tar_path:
                break
    if tar_path:
        os.makedirs(REPO_PATH, exist_ok=True)
        log(f"source code : archive du dépôt ({tar_path})…")
        sh(["tar", "-xzf", tar_path, "-C", REPO_PATH], timeout=600)
        source = f"archive:{tar_path}"
    else:
        log("source code : clone GitHub public au commit épinglé…")
        sh(["git", "clone", "--quiet", REPO_URL, REPO_PATH], timeout=600)
        sh(["git", "-C", REPO_PATH, "checkout", "--quiet", REPO_COMMIT],
           timeout=120)
        source = "github:" + REPO_URL
    sh(["git", "config", "--global", "--add", "safe.directory", REPO_PATH])
    head = sh(["git", "-C", REPO_PATH, "rev-parse", "HEAD"]).stdout.strip()
    assert head == REPO_COMMIT, f"commit attendu {REPO_COMMIT}, obtenu {head}"
    status = sh(["git", "-C", REPO_PATH, "status", "--porcelain"]).stdout
    assert not status.strip(), f"arbre divergent :\n{status[:500]}"
    log(f"dépôt vérifié : HEAD {head[:12]} | arbre propre | {source}")
    return source


def load_cells():
    nb = json.load(open(os.path.join(REPO_PATH, "notebooks",
                                     "m3b_qlora_personas.ipynb"),
                        encoding="utf-8"))
    cells = [(c.get("source") if isinstance(c.get("source"), str)
              else "".join(c.get("source", [])))
             for c in nb["cells"] if c.get("cell_type") == "code"]
    out = {}
    for name, marker in MARKERS.items():
        hits = [c for c in cells if marker in c]
        if len(hits) != 1:
            raise RuntimeError(f"cellule {name!r} introuvable/ambiguë")
        out[name] = hits[0]
    return out


SHIM = '''
REPO_PATH = @@REPO_PATH@@
HEAD = @@HEAD@@
sys.path.insert(0, os.path.join(REPO_PATH, "scripts"))
import m3b_state as M3B
DRIVE_ROOT = @@DRIVE_ROOT@@
ENV_INFO = @@ENV_INFO@@
SEAL_CHECK = M3B.seal_check_from_repo(REPO_PATH)
assert SEAL_CHECK.get("ok") is True, "scellé M4 non vérifiable — REFUS"
_p = os.path.join(DRIVE_ROOT, "state.json")
if os.path.exists(_p):
    _es = M3B.ExpState(DRIVE_ROOT)
    _es.state = json.load(open(_p, encoding="utf-8"))
    print(_es.summary())
else:
    print("AUCUNE EXPÉRIENCE COMMENCÉE")
'''


def render_shim(repo_path, head, drive_root, env_info):
    return (SHIM.replace("@@REPO_PATH@@", repr(repo_path))
                .replace("@@HEAD@@", repr(head))
                .replace("@@DRIVE_ROOT@@", repr(drive_root))
                .replace("@@ENV_INFO@@", repr(env_info)))


def find_input_states():
    found = {}
    inp = "/kaggle/input"
    if not os.path.isdir(inp):
        return found
    for root, dirs, files in os.walk(inp):
        if root.count(os.sep) - inp.count(os.sep) > 3:
            dirs[:] = []
            continue
        for d in list(dirs):
            if d.startswith("m3b_state") and \
                    os.path.isfile(os.path.join(root, d, "state.json")):
                found[d] = os.path.join(root, d)
    return found


def balanced_call(cell, opener):
    lines = cell.splitlines()
    acc, depth, started = [], 0, False
    for ln in lines:
        if not started:
            if opener in ln:
                started = True
                acc.append(ln)
                depth += ln.count("(") - ln.count(")")
            continue
        acc.append(ln)
        depth += ln.count("(") - ln.count(")")
        if depth <= 0:
            break
    if not started or depth > 0:
        raise RuntimeError(f"appel {opener!r} introuvable/incomplet")
    return "\n".join(acc)


# ------------------------------------------------------------------- le test --
def main():
    global REPO_COMMIT
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-commit", default=REPO_COMMIT)
    args, _ = ap.parse_known_args()
    if args.repo_commit and args.repo_commit != REPO_COMMIT:
        REPO_COMMIT = args.repo_commit
        log(f"commit épinglé (override CLI) : {REPO_COMMIT[:12]}")

    report = {"schema": "m3b-eval-microtest/1",
              "utc_start": datetime.datetime.now(
                  datetime.timezone.utc).isoformat(),
              "repo_commit": REPO_COMMIT,
              "mission": "démontrer que l'OOM d'évaluation s1 est supprimé "
                         "par per_device_eval_batch_size=1"}

    import torch
    n_gpu = torch.cuda.device_count()
    report["gpus"] = [{"index": i,
                       "name": torch.cuda.get_device_properties(i).name,
                       "total_vram_gb": round(
                           torch.cuda.get_device_properties(i).total_memory
                           / 1e9, 2)} for i in range(n_gpu)]
    log(f"GPU visibles : {n_gpu} × "
        + (report["gpus"][0]["name"] if report["gpus"] else "aucun"))
    assert n_gpu >= 1, "AUCUN GPU — REFUS (R4)"

    # ---- 0. bootstrap (pins + dépôt + batteries in situ + poids) ----------
    log("1/4 pins d'environnement…")
    r = sh([sys.executable, "-m", "pip", "install", "--quiet", *PIP_PINS],
           timeout=1200, check=False)
    import importlib.metadata as md
    got = {n: md.version(n) for n in ("transformers", "peft",
                                      "bitsandbytes")}
    log(f"versions : transformers={got['transformers']} "
        f"peft={got['peft']} bitsandbytes={got['bitsandbytes']}")
    report["versions"] = got

    log("2/4 acquisition du dépôt au commit épinglé…")
    report["code_source"] = acquire_repo()

    log("3/4 batteries in situ (gel 12/12, fuite 14/14, scellé)…")
    r = sh([sys.executable, os.path.join(REPO_PATH, "scripts",
                                         "test_m3b_protocol_freeze.py")],
           timeout=600)
    assert "12 PASS / 0 FAIL" in r.stdout, f"gel divergent :\n{r.stdout[-600:]}"
    report["gel_in_situ"] = "12 PASS / 0 FAIL"
    r = sh([sys.executable, os.path.join(REPO_PATH, "scripts",
                                         "m15_audit.py")], timeout=900)
    assert "verdict: PASS" in r.stdout, f"fuite détectée :\n{r.stdout[-600:]}"
    report["audit_in_situ"] = "14/14 verdict: PASS"

    log("4/4 poids du modèle de base (R5)…")
    from huggingface_hub import snapshot_download
    snap = snapshot_download("Qwen/Qwen2.5-3B-Instruct")
    for fn, want in HF_OFFICIAL_SHA256.items():
        p = os.path.join(snap, fn)
        assert os.path.isfile(p), f"poids absent : {fn}"
        got_hash = sha256_file(p)
        assert got_hash == want, f"POIDS NON OFFICIELS ({fn}) — REFUS (R5)"
    report["poids_officiels"] = True
    log("poids conformes aux hashs officiels HF (2 shards)")

    # ---- état s1 : racines restaurées depuis la sortie du kernel s1 -------
    inputs = find_input_states()
    log(f"racines d'état détectées : {sorted(inputs) or 'AUCUNE'}")
    assert "m3b_state_w0" in inputs and "m3b_state_w1" in inputs, \
        "les DEUX racines s1 (w0, w1) doivent être montées comme source"
    report["racines_s1"] = sorted(inputs)
    copied = {}
    for n in ("m3b_state_w0", "m3b_state_w1"):
        dst = os.path.join(WORKING, n)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(inputs[n], dst)
        copied[n] = dst
        log(f"racine s1 restaurée (copie locale, lecture seule en entrée) : {n}")

    cells = load_cells()
    log(f"notebook gelé : {len(cells)} cellules chargées par marqueurs")

    # fragment TrainingArguments EXACT + preuve d'identité avec le gel
    frag = balanced_call(cells["train_6"], "args = TrainingArguments(")
    import hashlib
    frag_sha256 = hashlib.sha256(frag.encode("utf-8")).hexdigest()
    golden = json.load(open(os.path.join(REPO_PATH, "results",
                                         "protocol_m3b_freeze.json"),
                            encoding="utf-8"))
    want_sha = golden["fragments"]["training_args"]["sha256"]
    assert frag_sha256 == want_sha, \
        f"fragment TrainingArguments ≠ gel ({frag_sha256[:12]} vs {want_sha256[:12]})"
    assert "per_device_eval_batch_size=1" in frag, \
        "le fragment gelé ne contient PAS le correctif — mauvais commit ?"
    report["fragment_training_args_sha256"] = frag_sha256
    report["fragment_identique_au_gel"] = True
    log(f"fragment TrainingArguments = gel du protocole "
        f"({frag_sha256[:12]}…) — le correctif est bien le code exécuté")

    env_info = {"python": sys.version.split()[0], "torch": torch.__version__,
                "transformers": got["transformers"], "peft": got["peft"],
                "bitsandbytes": got["bitsandbytes"],
                "gpu": torch.cuda.get_device_name(0),
                "gpu_mem_gb": round(
                    torch.cuda.get_device_properties(0).total_memory / 1e9, 1)}

    # ---- cellules gelées (une fois) puis SHIM/état par racine -------------
    ns = {"__name__": "m3b_microtest"}
    for name in ("imports", "config"):
        log(f"cellule gelée « {name} »")
        exec(compile(cells[name], f"<notebook:{name}>", "exec"), ns)  # noqa: S102
    ns["CONFIG"]["SOFT_MINUTES"] = 1.0          # opérationnel (hors empreinte)
    for name in ("personas_dir", "load_persona", "temporal_split",
                 "tokenization", "dataset", "qlora"):
        log(f"cellule gelée « {name} »")
        exec(compile(cells[name], f"<notebook:{name}>", "exec"), ns)  # noqa: S102

    from peft import PeftModel
    from transformers import Trainer, TrainingArguments

    evals = []
    for root_name in ("w1", "w0"):
        root = copied[f"m3b_state_{root_name}"]
        shim = render_shim(REPO_PATH, REPO_COMMIT, root, env_info)
        log(f"SHIM + §5bis sur la racine {root_name} ({root})")
        exec(compile(shim, "<shim:kaggle>", "exec"), ns)              # noqa: S102
        exec(compile(cells["state_5bis"], "<notebook:state_5bis>",  # noqa: S102
                     "exec"), ns)
        STATE, CONFIG, SEED = ns["STATE"], ns["CONFIG"], ns["SEED"]
        splits, personas = ns["splits"], ns["personas"]

        # vérification d'empreinte in situ (l'état s1 doit être repris tel quel)
        st = json.load(open(os.path.join(root, "state.json"), encoding="utf-8"))
        report.setdefault("empreinte_état_s1", {})[root_name] = \
            st.get("fingerprint")

        for judge in (JUDGES_OOM.get(root_name) or []):
            log(f"— juge {judge} : restore + reload + VRAIE évaluation —")
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
            vram_avant = torch.cuda.mem_get_info()[0] / 1e9
            local_out = os.path.join(WORKING, "microtest_ckpt", judge)
            resume_from = STATE.restore_ckpt_local(judge, local_out)
            assert resume_from, f"aucun checkpoint restauré pour {judge}"
            log(f"  checkpoint restauré (manifeste vérifié) : {resume_from}")
            model = PeftModel.from_pretrained(ns["base"], resume_from)
            log("  adaptateur rechargé dans le modèle 4-bit")
            ns_args = {"local_out": local_out, "CONFIG": CONFIG,
                       "SEED": SEED, "torch": torch,
                       "TrainingArguments": TrainingArguments}
            exec(compile(frag, "<gel:training_args>", "exec"), ns_args)  # noqa: S102
            targs = ns_args["args"]
            assert targs.per_device_eval_batch_size == 1, \
                "le batch d'évaluation n'est pas 1 — correctif non appliqué"
            va_ds = ns["PersonaTorch"](splits[judge][1])
            trainer = Trainer(model=model, args=targs, eval_dataset=va_ds,
                              data_collator=ns["collate"])
            t0 = time.time()
            metrics = trainer.evaluate()
            dt = time.time() - t0
            peak = torch.cuda.max_memory_allocated() / 1e9
            vram_après = torch.cuda.mem_get_info()[0] / 1e9
            entry = {
                "juge": judge, "racine": root_name,
                "checkpoint": os.path.basename(resume_from),
                "per_device_eval_batch_size": targs.per_device_eval_batch_size,
                "n_exemples_évalués": len(va_ds),
                "eval_loss": metrics.get("eval_loss"),
                "eval_runtime_s": round(metrics.get("eval_runtime", dt), 2),
                "durée_mesurée_s": round(dt, 1),
                "vram_libre_avant_Go": round(vram_avant, 2),
                "vram_libre_après_Go": round(vram_après, 2),
                "pic_mémoire_allouée_Go": round(peak, 2),
                "oom": False,
            }
            evals.append(entry)
            log("  RÉSULTAT : " + json.dumps(entry, ensure_ascii=False))
            del model, trainer
            torch.cuda.empty_cache()

        # Kavanaugh (racine w0) : adaptateur promu → reload + forward
        if root_name == JUDGE_DONE[0]:
            judge = JUDGE_DONE[1]
            log(f"— juge {judge} (terminé en s1) : adaptateur promu, "
                f"reload + forward —")
            m = PeftModel.from_pretrained(
                ns["base"], str(STATE.final_adapter_dir(judge)))
            with torch.no_grad():
                p_ids, o_ids = ns["encode_row"](personas[judge][0])
                ids = torch.tensor([p_ids + o_ids[:16]],
                                   device=ns["base"].device)
                finis = bool(torch.isfinite(
                    m(input_ids=ids).logits).all())
            report["kavanaugh_reload_forward"] = {
                "juge": judge, "logits_finis": finis,
                "adaptateur": str(STATE.final_adapter_dir(judge))}
            log(f"  forward logits finis : {finis}")
            del m
            torch.cuda.empty_cache()

    report["évaluations"] = evals
    report["utc_end"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat()

    # ---- nettoyage : la sortie de ce kernel d'audit ne doit PAS ressembler
    # à une racine de production (les originaux s1 restent dans la sortie du
    # kernel s1, montée en lecture seule) — on ne conserve que les manifests
    # légers (state.json/events.jsonl) comme preuve de lecture.
    for n in ("m3b_state_w0", "m3b_state_w1"):
        p = os.path.join(WORKING, n)
        for sub in ("checkpoints", "adapters"):
            q = os.path.join(p, sub)
            if os.path.isdir(q):
                shutil.rmtree(q)
    q = os.path.join(WORKING, "microtest_ckpt")
    if os.path.isdir(q):
        shutil.rmtree(q)
    log("copies lourdes supprimées de la sortie (originaux intacts dans le "
        "kernel s1)")

    # ---- verdict du micro-test ---------------------------------------------
    ok = (len(evals) == 3
          and all(e["eval_loss"] is not None and e["oom"] is False
                  for e in evals)
          and report.get("kavanaugh_reload_forward", {}).get("logits_finis")
          is True)
    report["verdict_microtest"] = "PASS" if ok else "FAIL"
    report["verdict_detail"] = (
        "3 évaluations complètes (Gorsuch, Kagan, Alito) : aucune OOM, "
        "val_loss produites, batch d'évaluation 1 confirmé ; adaptateur "
        "Kavanaugh rechargé + forward logits finis."
        if ok else "voir évaluations/erreurs ci-dessus")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print(json.dumps(report, indent=1, ensure_ascii=False))
    log(f"→ {OUT_JSON}")
    log(f"VERDICT MICRO-TEST : {report['verdict_microtest']}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
