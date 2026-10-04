#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M3b Kaggle PROBE (LS-17, Phase 4 du mandat).

Sonde l'environment d'exécution Kaggle RÉELLEMENT (aucune hypothèse) :
GPU (nombre, modèle, VRAM), CUDA/driver, versions logicielles de l'image,
CPU/RAM/disque, connectivité sortante, clonage du dépôt au commit gelé,
exécution IN SITU du gel du protocole (12 fragments) et de l'audit
zéro-fuite (14 contrôles).

Aucun entraînement. Aucun secret (le kernel ne contient aucun credential).
Sortie : /kaggle/working/m3b_kaggle_probe.{json,md} + console.
"""

import datetime
import json
import os
import shutil
import socket
import subprocess
import sys

REPO_URL = "https://github.com/Vitalcheffe/legally-subjective.git"
REPO_COMMIT = "55462bb"          # protocole gelé + audits verts (CI GitHub)
OUT_JSON = "/kaggle/working/m3b_kaggle_probe.json"
OUT_MD = "/kaggle/working/m3b_kaggle_probe.md"


def sh(cmd, timeout=90):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout)
        out = r.stdout.strip()
        if r.stderr.strip():
            out += "\n[stderr] " + r.stderr.strip()[-600:]
        return out or "(vide)"
    except subprocess.TimeoutExpired:
        return f"[timeout après {timeout}s]"
    except Exception as e:
        return f"[erreur {type(e).__name__}: {e}]"


def reachable(host, port=443, t=8):
    try:
        s = socket.create_connection((host, port), timeout=t)
        s.close()
        return True
    except Exception:
        return False


def module_version(name):
    try:
        m = __import__(name)
        return getattr(m, "__version__", "présent (version inconnue)")
    except Exception as e:
        return f"ABSENT ({type(e).__name__})"


def main():
    r = {"schema": "m3b-kaggle-probe/1",
         "utc_start": datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "mission": "LS-17 Phase 4 — sonde d'environnement avant tout entraînement"}

    # ---------- système ----------
    r["os"] = sh("head -2 /etc/os-release")
    r["cpu_cores"] = os.cpu_count()
    with open("/proc/meminfo") as f:
        mi = {l.split(":")[0]: int(l.split()[1]) for l in f if ":" in l}
    r["ram_total_gb"] = round(mi["MemTotal"] / 1e6, 2)
    r["ram_available_gb"] = round(mi["MemAvailable"] / 1e6, 2)
    r["disk"] = {}
    for p in ("/", "/kaggle/working", "/tmp", "/kaggle/input"):
        try:
            du = shutil.disk_usage(p)
            r["disk"][p] = {"total_gb": round(du.total / 1e9, 2),
                            "free_gb": round(du.free / 1e9, 2)}
        except Exception:
            r["disk"][p] = "indisponible"

    # env Kaggle (clés seulement ; valeurs filtrées anti-secret par précaution)
    r["kaggle_env"] = {
        k: (v if not any(x in k.upper() for x in ("TOKEN", "KEY", "SECRET", "PASS"))
            else "***filtré***")
        for k, v in os.environ.items() if k.startswith("KAGGLE")}

    # ---------- GPU (mesures réelles) ----------
    r["nvidia_smi"] = sh("nvidia-smi", 30)
    try:
        import torch
        r["torch"] = {"version": torch.__version__,
                      "cuda": torch.version.cuda,
                      "cudnn": torch.backends.cudnn.version(),
                      "device_count": torch.cuda.device_count(),
                      "bf16_supported": torch.cuda.is_bf16_supported()}
        r["gpus"] = []
        for i in range(torch.cuda.device_count()):
            p = torch.cuda.get_device_properties(i)
            r["gpus"].append({
                "index": i, "name": p.name,
                "total_vram_gb": round(p.total_memory / 1e9, 2),
                "compute_capability": f"{p.major}.{p.minor}",
                "sm_count": p.multi_processor_count})
        # micro-sonde CUDA : allocation + noyau trivial + determinisme cudnn flag
        try:
            x = torch.randn(1024, 1024, device="cuda")
            y = (x @ x).sum().item()
            r["cuda_smoke"] = {"ok": True, "matmul_sum": y}
        except Exception as e:
            r["cuda_smoke"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    except Exception as e:
        r["torch"] = f"IMPORT IMPOSSIBLE ({type(e).__name__}: {e})"

    # ---------- versions logicielles de l'image ----------
    r["python"] = sys.version.split()[0]
    r["versions"] = {m: module_version(m) for m in
                     ("transformers", "peft", "bitsandbytes", "accelerate",
                      "tokenizers", "triton", "numpy", "datasets", "safetensors")}
    r["pip_freeze_head"] = sh("pip freeze 2>/dev/null | head -40", 60)

    # ---------- connectivité sortante ----------
    r["internet"] = {h: reachable(h) for h in
                     ("github.com", "huggingface.co", "pypi.org",
                      "www.kaggle.com", "api.kaggle.com")}

    # ---------- dépôt + audits in situ ----------
    repo = "/kaggle/working/legally-subjective"
    if r["internet"]["github.com"]:
        r["repo_clone"] = sh(
            f"rm -rf {repo} && git clone --quiet {REPO_URL} {repo} "
            f"&& cd {repo} && git checkout --quiet {REPO_COMMIT} "
            f"&& git rev-parse HEAD && git status --porcelain | head -3", 240)
        r["gel_protocole_12"] = sh(
            f"cd {repo} && python scripts/test_m3b_protocol_freeze.py 2>&1 | tail -3", 180)
        r["audit_zero_fuite_14"] = sh(
            f"cd {repo} && python scripts/m15_audit.py 2>&1 | tail -4", 300)
    else:
        r["repo_clone"] = ("PAS D'INTERNET github — la route sans internet "
                           "(dataset privé de code) sera utilisée")
        r["gel_protocole_12"] = "NON EXÉCUTÉ (pas de dépôt)"
        r["audit_zero_fuite_14"] = "NON EXÉCUTÉ (pas de dépôt)"

    # ---------- entrées attachées ----------
    r["kaggle_inputs"] = sh("ls -la /kaggle/input/ 2>/dev/null; "
                            "find /kaggle/input -maxdepth 3 -type d 2>/dev/null | head -20", 30)

    r["utc_end"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # ---------- sorties ----------
    os.makedirs("/kaggle/working", exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(r, f, indent=1, ensure_ascii=False)

    lines = ["# Sonde Kaggle M3b — résultat réel", "",
             f"*UTC : {r['utc_start']} → {r['utc_end']}*", ""]
    lines.append(f"- GPU : {len(r.get('gpus', []))} × "
                 + ", ".join(g["name"] + f" ({g['total_vram_gb']} Go)"
                             for g in r.get("gpus", [])))
    lines.append(f"- torch {r.get('torch', {}).get('version', '?')} / CUDA "
                 f"{r.get('torch', {}).get('cuda', '?')} / python {r['python']}")
    lines.append(f"- versions image : " + json.dumps(r["versions"]))
    lines.append(f"- internet : {r['internet']}")
    gel = "12/12 PASS" if "12 PASS" in r.get("gel_protocole_12", "") else r.get("gel_protocole_12", "")[:120]
    audit = "14/14 PASS" if "verdict: PASS" in r.get("audit_zero_fuite_14", "") else r.get("audit_zero_fuite_14", "")[:120]
    lines.append(f"- gel du protocole in situ : {gel}")
    lines.append(f"- audit zéro-fuite in situ : {audit}")
    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines))

    print(json.dumps({k: r[k] for k in
                      ("gpus", "torch", "python", "versions", "internet")}, indent=1))
    print("gel :", r["gel_protocole_12"].splitlines()[-1][:100])
    print("audit :", r["audit_zero_fuite_14"].splitlines()[-1][:100])
    print(f"→ {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
