#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M3b KAGGLE RUNNER (LS-17, mandat « Point B » Kaggle).

PRINCIPE : ce runner est une COQUILLE D'INFRASTRUCTURE. Toute la science
vient du notebook gelé du dépôt (commit épinglé), dont les cellules sont
exécutées OCTET POUR OCTET après re-vérification du gel in situ. Ce que ce
runner remplace, c'est uniquement l'infrastructure Colab→Kaggle :

  cellule 2 (install pip)    → mêmes pins, exécutés par le parent ;
  cellule 7 (montage Drive)  → SHIM : clone du dépôt au commit épinglé +
                               racine d'état /kaggle/working + consignation
                               environnement + scellé re-vérifié (mêmes
                               noms de variables : DRIVE_ROOT, REPO_PATH,
                               HEAD, ENV_INFO, SEAL_CHECK, M3B) ;
  boucle §6                  → restreinte au sous-ensemble du worker
                               (l'empreinte §5bis reste calculée sur les
                               données COMPLÈTES : identité d'expérience
                               identique quel que soit le découpage).

Exigences vérifiées AVANT tout entraînement (sinon REFUS) :
  R1  gel du protocole 12/12 dans le clone (fragments octet-identiques) ;
  R2  audit zéro-fuite 14/14 dans le clone ;
  R3  scellé M4 intègre dans le clone (seal_check_from_repo) ;
  R4  GPU réellement visible (torch.cuda) ;
  R5  poids du modèle de base sha256-identiques aux hashs officiels HF
      (Qwen/Qwen2.5-3B-Instruct, capturés le 2026-10-05 depuis l'API HF).

Persistance inter-sessions : chaque noyau Kaggle attache le noyau de la
session précédente comme source de données (lecture seule) ; les racines
d'état m3b_state_w{0,1} sont copiées vers /kaggle/working et reprises par
la machinerie atomique de scripts/m3b_state.py (testée 143+30 contrôles).
La finalisation fusionne les racines (scripts/m3b_state_merge.py, testée
25 contrôles) puis exécute §7/§7bis/§8 + portillon DANS le noyau.

Aucun secret ici : ce fichier ne contient aucun credential.
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

REPO_URL = "https://github.com/Vitalcheffe/legally-subjective.git"
REPO_COMMIT = "55462bb6129715ef5a76f06e088a528ca9d8bfa7"   # LS-16 (CI verte)
REPO_PATH = "/tmp/legally-subjective"                        # éphémère, hors sortie
WORKING = "/kaggle/working"

# hashs LFS officiels HuggingFace (API /tree/main, capturés 2026-10-05) —
# toute divergence des poids téléchargés = REFUS d'entraîner (R5).
HF_OFFICIAL_SHA256 = {
    "model-00001-of-00002.safetensors":
        "67347b23fb4165b652eb6611f5e1f2a06dfcddba8e909df1b2b0b1857bee06c2",
    "model-00002-of-00002.safetensors":
        "a40d941d0e7e0b966ad8b62bb6d6b7c88cce1299197b599d9d0a4ce59aabfc1d",
}
PIP_PINS = ["transformers==4.49.0", "peft==0.13.2",
            "bitsandbytes>=0.47.0,<0.51", "accelerate==1.2.1",
            "datasets==3.1.0", "sentencepiece", "protobuf"]

MARKERS = {                      # découverte robuste (pas d'index en dur)
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
    "probe_7": "def generate(name, instruction",
    "memo_7bis": "def cloze_hits",
    "export_8": "deterministic_write_zip",
}


def log(msg):
    print(f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')}] {msg}",
          flush=True)


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


# --------------------------------------------------------------- cellules --
def load_cells():
    """Cellules de code du notebook gelé, indexées par marqueur."""
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
            raise RuntimeError(f"cellule {name!r} introuvable/ambiguë "
                               f"({len(hits)} occurrences de {marker!r})")
        out[name] = hits[0]
    return out


SHIM = '''
# --- SHIM KAGGLE (remplace la cellule Drive Colab — INFRASTRUCTURE) ------
# Mêmes noms de variables que la cellule d'origine pour que les cellules
# scientifiques gelées s'exécutent SANS AUCUNE modification.
REPO_PATH = @@REPO_PATH@@
HEAD = @@HEAD@@
sys.path.insert(0, os.path.join(REPO_PATH, "scripts"))
import m3b_state as M3B

DRIVE_ROOT = @@DRIVE_ROOT@@

ENV_INFO = @@ENV_INFO@@
print("environnement :", ENV_INFO["gpu"], "|", ENV_INFO["torch"],
      "|", ENV_INFO["transformers"])

SEAL_CHECK = M3B.seal_check_from_repo(REPO_PATH)
assert SEAL_CHECK.get("ok") is True, (
    "scellé M4 non vérifiable dans le clone — REFUS de démarrer. "
    f"Diagnostic : {SEAL_CHECK}")
print("scellé M4 intègre dans le clone :",
      str(SEAL_CHECK.get("sealed_sha256"))[:16] + "…",
      f"({SEAL_CHECK.get('n_cases')} affaires scellées)")

_p = os.path.join(DRIVE_ROOT, "state.json")
if os.path.exists(_p):
    try:
        _es = M3B.ExpState(DRIVE_ROOT)
        _es.state = json.load(open(_p, encoding="utf-8"))
        print(_es.summary())
    except Exception:
        print("state.json présent mais illisible — le §5bis donnera le diagnostic")
else:
    print("AUCUNE EXPÉRIENCE COMMENCÉE — la racine d'état sera créée en §5bis")
'''


def render_shim(repo_path, head, drive_root, env_info):
    """Placeholders @@...@@ remplacés littéralement — jamais .format()
    (les f-strings du shim contiennent des accolades)."""
    return (SHIM.replace("@@REPO_PATH@@", repr(repo_path))
                .replace("@@HEAD@@", repr(head))
                .replace("@@DRIVE_ROOT@@", repr(drive_root))
                .replace("@@ENV_INFO@@", repr(env_info)))


# ------------------------------------------------------------ préparation --
def acquire_repo():
    """Source du code : dataset privé Kaggle (archive tar OPAQUE du dépôt
    complet avec .git — extension .bin pour éviter l'extraction serveur ;
    arbre vérifiable octet-identique au commit épinglé) — sinon
    clone GitHub public. Les DEUX routes vérifient HEAD == REPO_COMMIT
    et l'arbre PROPRE (git status vide)."""
    if os.path.exists(REPO_PATH):
        shutil.rmtree(REPO_PATH)
    src_ds = "/kaggle/input/legally-subjective-code"
    if os.path.isdir(src_ds):
        tars = sorted(f for f in os.listdir(src_ds)
                      if f.endswith((".tar.bin", ".tar.gz", ".tgz")))
        assert tars, f"dataset code sans archive tar : {src_ds}"
        assert len(tars) == 1, f"plusieurs archives possibles : {tars}"
        os.makedirs(REPO_PATH, exist_ok=True)
        log(f"source code : dataset privé ({tars[0]})…")
        sh(["tar", "-xzf", os.path.join(src_ds, tars[0]), "-C", REPO_PATH],
           timeout=600)
        source = f"dataset:legally-subjective-code/{tars[0]}"
    else:
        log("source code : clone GitHub public au commit épinglé…")
        sh(["git", "clone", "--quiet", REPO_URL, REPO_PATH], timeout=600)
        sh(["git", "-C", REPO_PATH, "checkout", "--quiet", REPO_COMMIT],
           timeout=120)
        source = "github:" + REPO_URL
    head = sh(["git", "-C", REPO_PATH, "rev-parse", "HEAD"]).stdout.strip()
    assert head == REPO_COMMIT, \
        f"commit attendu {REPO_COMMIT}, obtenu {head}"
    # arbre PROPRE = le contenu de l'archive est octet-identique au commit
    status = sh(["git", "-C", REPO_PATH, "status", "--porcelain"]).stdout
    assert not status.strip(), \
        f"arbre du dépôt divergent du commit :\n{status[:500]}"
    log(f"dépôt vérifié : HEAD {head[:12]} | arbre propre | {source}")
    return source


def prepare():
    """Étapes 1-5 : pins, code, gel, audit, pré-téléchargement."""
    t0 = time.time()
    log("1/5 pins d'environnement (identiques au notebook cellule 2)…")
    r = sh([sys.executable, "-m", "pip", "install", "--quiet", *PIP_PINS],
           timeout=1200, check=False)
    if r.returncode != 0:
        # les conflits de dépendances préinstallées sont tolérés si les
        # pins finaux sont bien en place (vérifiés ci-dessous)
        log("pip a signalé des conflits — vérification des versions réelles…")
    import importlib.metadata as md
    got = {n: md.version(n) for n in ("transformers", "peft", "bitsandbytes")}
    log(f"versions : transformers={got['transformers']} "
        f"peft={got['peft']} bitsandbytes={got['bitsandbytes']}")
    assert got["transformers"] == "4.49.0", "pin transformers 4.49.0 non en place"
    assert got["peft"] == "0.13.2", "pin peft 0.13.2 non en place"

    log("2/5 acquisition du dépôt au commit épinglé…")
    code_source = acquire_repo()
    head = REPO_COMMIT

    log("3/5 gel du protocole in situ (12 fragments)…")
    r = sh([sys.executable, os.path.join(REPO_PATH, "scripts",
                                         "test_m3b_protocol_freeze.py")],
           timeout=600)
    assert "12 PASS / 0 FAIL" in r.stdout, f"gel divergent :\n{r.stdout[-800:]}"

    log("4/5 audit zéro-fuite in situ (14 contrôles)…")
    r = sh([sys.executable, os.path.join(REPO_PATH, "scripts", "m15_audit.py")],
           timeout=900)
    assert "verdict: PASS" in r.stdout, f"fuite détectée :\n{r.stdout[-800:]}"

    log("5/5 pré-téléchargement du modèle + vérification des poids (R5)…")
    from huggingface_hub import snapshot_download
    t1 = time.time()
    snap = snapshot_download("Qwen/Qwen2.5-3B-Instruct")
    log(f"snapshot HF : {snap} ({time.time() - t1:.0f}s)")
    for fn, want in HF_OFFICIAL_SHA256.items():
        p = os.path.join(snap, fn)
        assert os.path.isfile(p), f"poids absent du snapshot : {fn}"
        got_hash = sha256_file(p)
        assert got_hash == want, (
            f"POIDS NON OFFICIELS ({fn}) :\n  obtenu   {got_hash}\n"
            f"  officiel {want}\nREFUS d'entraîner — modèle non conforme "
            "au protocole (R5).")
    log(f"poids conformes aux hashs officiels HF ({len(HF_OFFICIAL_SHA256)} shards)")
    return {"clone_seconds": round(time.time() - t0, 1), "snapshot": snap,
            "head": head, "code_source": code_source}


def find_input_states():
    """Cherche les racines d'état des sessions précédentes dans les entrées
    attachées (/kaggle/input/<noyau-précédent>/m3b_state_w*/)."""
    found = {}
    inp = "/kaggle/input"
    if not os.path.isdir(inp):
        return found
    for src in os.listdir(inp):
        d = os.path.join(inp, src)
        if not os.path.isdir(d):
            continue
        for sub in os.listdir(d) if os.path.isdir(d) else []:
            if sub.startswith("m3b_state") and \
                    os.path.isfile(os.path.join(d, sub, "state.json")):
                found[sub] = os.path.join(d, sub)
    return found


def copy_states_in(inputs, names=("m3b_state_w0", "m3b_state_w1",
                                  "m3b_state")):
    os.makedirs(WORKING, exist_ok=True)
    copied = {}
    for n in names:
        if n in inputs:
            dst = os.path.join(WORKING, n)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(inputs[n], dst)
            copied[n] = dst
            log(f"état précédent restauré : {n} "
                f"({os.path.getsize(os.path.join(dst, 'state.json'))} octets de manifeste)")
    return copied


# ------------------------------------------------------------------ worker --
def worker_main(args, cells):
    """Un worker = un GPU (CUDA_VISIBLE_DEVICES) + un sous-ensemble de
    juges + sa PROPRE racine d'état (aucune écriture partagée)."""
    os.makedirs(args.worker_dir, exist_ok=True)
    os.chdir(args.worker_dir)          # CKPT_LOCAL du §6 devient local au worker

    if args.kill_after:
        def _killer():
            time.sleep(args.kill_after)
            print(f"\n!! MORT BRUTALE INJECTÉE (tueur --kill-after "
                  f"{args.kill_after}s) — os._exit(137)", flush=True)
            os._exit(137)
        threading.Thread(target=_killer, daemon=True).start()

    import torch
    env_info = {
        "python": sys.version.split()[0], "torch": torch.__version__,
        "transformers": __import__("importlib.metadata", fromlist=["version"])
                        .version("transformers"),
        "peft": __import__("importlib.metadata", fromlist=["version"])
                .version("peft"),
        "bitsandbytes": __import__("importlib.metadata", fromlist=["version"])
                        .version("bitsandbytes"),
        "gpu": torch.cuda.get_device_name(0),
        "gpu_mem_gb": round(
            torch.cuda.get_device_properties(0).total_memory / 1e9, 1),
    }
    log(f"worker {args.worker_idx} : GPU {env_info['gpu']} "
        f"({env_info['gpu_mem_gb']} Go) | juges {args.judges}")

    ns = {"__name__": "m3b_nbexec"}
    order = ["imports", "config", "personas_dir", "load_persona",
             "temporal_split", "tokenization", "dataset", "qlora",
             "state_5bis"]
    for name in order:
        log(f"worker {args.worker_idx} : cellule gelée « {name} »")
        exec(compile(cells[name], f"<notebook:{name}>", "exec"), ns)

    # SOFT_MINUTES : paramètre OPÉRATIONNEL (hors empreinte, cellule 5 le
    # documente : « ajustable librement ») adapté aux sessions batch Kaggle.
    ns["CONFIG"]["SOFT_MINUTES"] = float(args.soft_minutes)

    # SHIM (cellule Drive → Kaggle) après la config, comme dans le notebook
    shim = render_shim(REPO_PATH, cells_head, args.drive_root, env_info)
    log(f"worker {args.worker_idx} : SHIM infrastructure Kaggle")
    exec(compile(shim, "<shim:kaggle>", "exec"), ns)

    # restriction du sous-ensemble APRÈS §5bis (empreinte = données complètes)
    if args.judges:
        wanted = [j.strip() for j in args.judges.split(",") if j.strip()]
        unknown = [j for j in wanted if j not in ns["personas"]]
        assert not unknown, f"juges inconnus du protocole : {unknown}"
        ns["personas"] = {k: v for k, v in ns["personas"].items()
                          if k in wanted}
        log(f"worker {args.worker_idx} : boucle §6 restreinte à {wanted} "
            f"(empreinte calculée sur les données complètes)")

    log(f"worker {args.worker_idx} : cellule gelée « train_6 » (le cœur)")
    exec(compile(cells["train_6"], "<notebook:train_6>", "exec"), ns)
    log(f"worker {args.worker_idx} : terminé proprement")
    return 0


cells_head = None       # rempli par main() après le clone


# ---------------------------------------------------------------- finalize --
def finalize_main(args, cells):
    """Session de finalisation : fusion des racines + §7/§7bis/§8 + portillon
    DANS le noyau, sur l'état fusionné (miroir exact du notebook)."""
    inputs = find_input_states()
    roots = [inputs[n] for n in ("m3b_state_w0", "m3b_state_w1")
             if n in inputs]
    if len(roots) < 2:
        log("une seule racine (ou aucune) — fusion inutile, copie directe")
        if roots:
            copy_states_in(inputs, ("m3b_state_w0", "m3b_state_w1",
                                    "m3b_state"))
    else:
        merged = os.path.join(WORKING, "m3b_state")
        log(f"fusion des {len(roots)} racines parallèles (outil testé 25 contrôles)…")
        r = sh([sys.executable, os.path.join(REPO_PATH, "scripts",
                                             "m3b_state_merge.py"),
                "--roots", *roots, "--out", merged], timeout=1800, check=False)
        print(r.stdout[-3000:])
        if r.returncode != 0:
            raise RuntimeError(f"fusion en échec :\n{r.stderr[-2000:]}")

    drive_root = os.path.join(WORKING, "m3b_state")
    assert os.path.isfile(os.path.join(drive_root, "state.json")), \
        "aucun état à finaliser"

    import torch
    env_info = {
        "python": sys.version.split()[0], "torch": torch.__version__,
        "transformers": __import__("importlib.metadata", fromlist=["version"])
                        .version("transformers"),
        "peft": __import__("importlib.metadata", fromlist=["version"])
                .version("peft"),
        "bitsandbytes": __import__("importlib.metadata", fromlist=["version"])
                        .version("bitsandbytes"),
        "gpu": torch.cuda.get_device_name(0),
        "gpu_mem_gb": round(
            torch.cuda.get_device_properties(0).total_memory / 1e9, 1),
    }
    ns = {"__name__": "m3b_nbexec"}
    order = ["imports", "config", "personas_dir", "load_persona",
             "temporal_split", "tokenization", "dataset", "qlora",
             "state_5bis"]
    for name in order:
        log(f"finalize : cellule gelée « {name} »")
        exec(compile(cells[name], f"<notebook:{name}>", "exec"), ns)
    ns["CONFIG"]["SOFT_MINUTES"] = float(args.soft_minutes)
    shim = render_shim(REPO_PATH, cells_head, drive_root, env_info)
    log("finalize : SHIM infrastructure Kaggle")
    exec(compile(shim, "<shim:kaggle>", "exec"), ns)
    for name in ("probe_7", "memo_7bis", "export_8"):
        log(f"finalize : cellule gelée « {name} »")
        exec(compile(cells[name], f"<notebook:{name}>", "exec"), ns)
    log("finalize : §7/§7bis/§8 exécutés (sonde, audit, export, portillon)")
    return 0


# ------------------------------------------------------------------- main --
def main():
    global cells_head, REPO_COMMIT
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="train", choices=["train", "finalize"])
    ap.add_argument("--repo-commit", default=REPO_COMMIT,
                    help="commit épinglé du dépôt (arbre exécuté), "
                         "généralement passé explicitement au push")
    ap.add_argument("--soft-minutes", type=float, default=55.0,
                    help="budget temps D'ENTRAÎNEMENT par worker "
                         "(opérationnel, hors empreinte)")
    ap.add_argument("--soft-minutes-w0", type=float, default=None)
    ap.add_argument("--soft-minutes-w1", type=float, default=None)
    ap.add_argument("--judges-w0", default=None)
    ap.add_argument("--judges-w1", default=None)
    ap.add_argument("--worker", type=int, default=None,
                    help="(interne) indice du worker relancé en sous-processus")
    ap.add_argument("--kill-after", type=float, default=None,
                    help="(test) mort brutale du worker 0 après S secondes")
    ap.add_argument("--dry", action="store_true",
                    help="préparation seule (aucun entraînement)")
    args = ap.parse_args()

    t_start = time.time()
    if args.repo_commit and args.repo_commit != REPO_COMMIT:
        REPO_COMMIT = args.repo_commit
        log(f"commit épinglé (override CLI) : {REPO_COMMIT[:12]}")

    # ---- sous-processus worker -----------------------------------------
    if args.worker is not None:
        # le worker hérite du clone/du pip du parent (même session noyau) —
        # mais re-vérifie le commit épinglé avant de toucher à la science.
        head = subprocess.run(["git", "-C", REPO_PATH, "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        assert head == REPO_COMMIT, \
            f"clone divergent : {head} != {REPO_COMMIT}"
        cells_head = head
        if args.worker == 0:
            judges = args.judges_w0
            soft = args.soft_minutes_w0 if args.soft_minutes_w0 is not None \
                else args.soft_minutes
            root = os.path.join(WORKING, "m3b_state_w0")
            wdir = os.path.join(WORKING, "w0")
        else:
            judges = args.judges_w1
            soft = args.soft_minutes_w1 if args.soft_minutes_w1 is not None \
                else args.soft_minutes
            root = os.path.join(WORKING, "m3b_state_w1")
            wdir = os.path.join(WORKING, f"w{args.worker}")
        wargs = argparse.Namespace(
            phase=args.phase, soft_minutes=soft,
            soft_minutes_w0=None, soft_minutes_w1=None,
            judges_w0=None, judges_w1=None, judges=judges,
            worker=args.worker, worker_idx=args.worker, worker_dir=wdir,
            drive_root=root, kill_after=(args.kill_after
                                         if args.worker == 0 else None),
            dry=False)
        return worker_main(wargs, load_cells())

    # ---- processus parent -------------------------------------------------
    import torch
    n_gpu = torch.cuda.device_count()
    env_facts = {
        "schema": "m3b-kaggle-runner/1",
        "utc_start": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "gpus": [{"index": i,
                  "name": torch.cuda.get_device_properties(i).name,
                  "total_vram_gb": round(
                      torch.cuda.get_device_properties(i).total_memory / 1e9, 2)}
                 for i in range(n_gpu)],
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "phase": args.phase,
        "soft_minutes": args.soft_minutes,
        "judges_w0": args.judges_w0, "judges_w1": args.judges_w1,
        "repo_commit": REPO_COMMIT,
    }
    log(f"GPU visibles : {n_gpu} × "
        + (env_facts["gpus"][0]["name"] if env_facts["gpus"] else "aucun"))
    assert n_gpu >= 1, "AUCUN GPU — REFUS de démarrer (R4)"

    prep = prepare()
    cells_head = prep["head"]
    env_facts["clone_seconds"] = prep["clone_seconds"]
    env_facts["code_source"] = prep["code_source"]

    cells = load_cells()
    log(f"notebook gelé : {len(cells)} cellules scientifiques découvertes "
        "par marqueurs (fragments protégés par le gel 12/12 in situ)")

    inputs = find_input_states()
    log(f"entrées détectées : {sorted(inputs) or 'aucune (départ frais)'}")

    if args.dry:
        log("mode --dry : préparation seule, aucun entraînement")
        json.dump(env_facts, open(os.path.join(WORKING, "kaggle_env.json"),
                                  "w"), indent=1)
        return 0

    if args.phase == "finalize":
        rc = finalize_main(args, cells)
        json.dump(env_facts, open(os.path.join(WORKING, "kaggle_env.json"),
                                  "w"), indent=1)
        return rc

    # ---- phase train : workers en parallèle (1 GPU chacun) ---------------
    copy_states_in(inputs)
    os.makedirs(WORKING, exist_ok=True)

    # affectation par défaut SÛRE : si aucune affectation explicite, on
    # répartit les juges attendus (règle du dépôt) en alternance — deux
    # workers ne doivent JAMAIS entraîner le même juge (racines séparées,
    # fusion par la suite) sans que ce soit une décision consciente.
    if not args.judges_w0 and not args.judges_w1:
        sys.path.insert(0, os.path.join(REPO_PATH, "scripts"))
        from m3b_gate import expected_judges   # dépôt cloné au commit épinglé
        exp, _ = expected_judges(REPO_PATH, min_rows=8)
        names = sorted(exp)
        args.judges_w0 = ",".join(names[0::2])
        args.judges_w1 = ",".join(names[1::2])
        log(f"affectation alternée par défaut : w0={args.judges_w0} | "
            f"w1={args.judges_w1}")

    specs = []
    if n_gpu >= 2 and args.judges_w1:
        specs = [
            {"idx": 0, "judges": args.judges_w0, "root": "m3b_state_w0"},
            {"idx": 1, "judges": args.judges_w1, "root": "m3b_state_w1"},
        ]
    else:
        specs = [{"idx": 0, "judges": args.judges_w0 or args.judges_w1,
                  "root": "m3b_state_w0"}]
    log(f"lancement de {len(specs)} worker(s) : "
        + json.dumps([{**s, "judges": s["judges"] or "(tous)"} for s in specs]))

    procs = {}
    for s in specs:
        env = dict(os.environ)
        env["CUDA_VISIBLE_DEVICES"] = str(s["idx"])
        cmd = [sys.executable, os.path.abspath(__file__),
               "--worker", str(s["idx"]),
               "--repo-commit", REPO_COMMIT,
               "--soft-minutes", str(args.soft_minutes)]
        if args.soft_minutes_w0 is not None and s["idx"] == 0:
            cmd += ["--soft-minutes-w0", str(args.soft_minutes_w0)]
        if args.soft_minutes_w1 is not None and s["idx"] == 1:
            cmd += ["--soft-minutes-w1", str(args.soft_minutes_w1)]
        if args.judges_w0 and s["idx"] == 0:
            cmd += ["--judges-w0", args.judges_w0]
        if args.judges_w1 and s["idx"] == 1:
            cmd += ["--judges-w1", args.judges_w1]
        if args.kill_after and s["idx"] == 0:
            cmd += ["--kill-after", str(args.kill_after)]
        procs[s["idx"]] = subprocess.Popen(cmd, env=env, cwd=WORKING)

    outcomes = {}
    for idx, p in procs.items():
        rc = p.wait()
        outcomes[f"w{idx}"] = rc
        log(f"worker w{idx} terminé : rc={rc}"
            + (" (mort brutale injectée — VOLONTAIRE, test)" if rc == 137 else ""))

    # ---- résumé de session ------------------------------------------------
    summary = {"schema": "m3b-session/1",
               "utc_end": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "wall_minutes": round((time.time() - t_start) / 60, 1),
               "repo_commit": REPO_COMMIT,
               "outcomes": outcomes, "env": env_facts}
    for n in ("m3b_state_w0", "m3b_state_w1"):
        p = os.path.join(WORKING, n, "state.json")
        if os.path.isfile(p):
            st = json.load(open(p, encoding="utf-8"))
            summary[n] = {
                "statuses": {j: v.get("status")
                             for j, v in st.get("judges", {}).items()},
                "steps": {j: v.get("step") for j, v in st.get("judges", {}).items()},
                "sessions": len(st.get("sessions", [])),
            }
    json.dump(summary, open(os.path.join(WORKING, "SESSION_SUMMARY.json"),
                            "w"), indent=1, ensure_ascii=False)
    print(json.dumps(summary, indent=1, ensure_ascii=False)[:3000])

    # 137 = mort brutale VOLONTAIRE (test --kill-after) ; en production, un
    # 137 réel (OOM-kill du superviseur) doit rester un ÉCHECH de session,
    # visible et diagnostiqué — jamais toléré silencieusement.
    expected_rc = {0} | ({137} if args.kill_after else set())
    hard_fail = [w for w, rc in outcomes.items() if rc not in expected_rc]
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
