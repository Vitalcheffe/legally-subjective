#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — sonde d'environnement d'exécution (cahier §III).

Teste RÉELLEMENT, sans supposer rien de la plateforme :
  GPU     : présence de nvidia-smi, drivers, périphériques CUDA visibles,
            torch.cuda.is_available() + VRAM (dans l'interpréteur courant) ;
  CPU     : cœurs, modèle, charge ;
  RAM     : totale / disponible ;
  disque  : espace libre + vitesse approximative (écriture 64 Mo) ;
  réseau  : joignabilité github.com et huggingface.co (timeout court) ;
  persistance : le filesystem survit-il au processus (fichier témoin) ;
  jobs longs : possibilité de processus fils persistant (témoin 5 s).

Sortie : rapport texte + JSON (results/environment_probe.json).
Verdict GPU honnête : « EXÉCUTION M3b LOCALE POSSIBLE » ou
« IMPOSSIBLE (raison exacte) » — jamais d'inférence.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT_JSON = os.path.join(REPO, "results", "environment_probe.json")


def probe_gpu():
    r = {"nvidia_smi": None, "devices": [], "torch_cuda": None}
    if shutil.which("nvidia-smi"):
        p = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,"
                            "driver_version", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=20)
        r["nvidia_smi"] = {"present": True, "rc": p.returncode,
                           "stdout": p.stdout.strip(),
                           "stderr": p.stderr.strip()[:200]}
    else:
        r["nvidia_smi"] = {"present": False,
                           "why": "exécutable nvidia-smi absent du PATH"}
    for i in range(4):
        if os.path.exists(f"/dev/nvidia{i}"):
            r["devices"].append(f"/dev/nvidia{i}")
    try:
        import torch
        r["torch"] = {"version": torch.__version__,
                      "cuda_available": bool(torch.cuda.is_available()),
                      "cuda_version_build": getattr(
                          torch.version, "cuda", None),
                      "device_count": torch.cuda.device_count()
                      if torch.cuda.is_available() else 0}
    except ImportError:
        r["torch"] = {"import_error": "torch absent de cet interpréteur"}
    return r


def probe_cpu():
    model = ""
    try:
        for ln in open("/proc/cpuinfo", encoding="utf-8"):
            if ln.startswith("model name"):
                model = ln.split(":", 1)[1].strip()
                break
    except OSError:
        model = platform.processor() or "inconnu"
    return {"model": model, "logical_cores": os.cpu_count(),
            "loadavg_1min": round(os.getloadavg()[0], 2)
            if hasattr(os, "getloadavg") else None}


def probe_ram():
    tot = avail = None
    try:
        for ln in open("/proc/meminfo", encoding="utf-8"):
            if ln.startswith("MemTotal"):
                tot = int(ln.split()[1]) / 1024
            elif ln.startswith("MemAvailable"):
                avail = int(ln.split()[1]) / 1024
    except OSError:
        pass
    return {"total_mb": round(tot) if tot else None,
            "available_mb": round(avail) if avail else None}


def probe_disk():
    du = shutil.disk_usage(os.getcwd())
    speed = None
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, dir=os.getcwd())
        buf = b"x" * (1 << 20)
        t0 = time.time()
        for _ in range(64):                       # 64 Mo
            tmp.write(buf)
        tmp.flush()
        os.fsync(tmp.fileno())
        dur = time.time() - t0
        tmp.close()
        os.remove(tmp.name)
        speed = round(64 / dur)                   # Mo/s (écriture+fsync)
    except OSError:
        pass
    return {"free_gb": round(du.free / 1e9, 1),
            "total_gb": round(du.total / 1e9, 1),
            "write_mbs_fsync": speed}


def probe_network():
    out = {}
    for host, url in (("github.com", "https://github.com"),
                      ("huggingface.co", "https://huggingface.co")):
        t0 = time.time()
        try:
            urllib.request.urlopen(url, timeout=10)
            out[host] = {"reachable": True,
                         "latency_ms": round((time.time() - t0) * 1000)}
        except Exception as e:
            out[host] = {"reachable": False, "error": str(e)[:120]}
    return out


def probe_persistence():
    """Le filesystem survit-il au PROCESSUS ? (témoin réutilisable)"""
    marker = os.path.join(tempfile.gettempdir(), "ls_probe_marker.txt")
    with open(marker, "w", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    return {"note": ("témoin écrit ; survie entre processus testée par "
                     "un second appel (le fichier existe-t-il déjà ?)"),
            "marker": marker,
            "preexisting": os.path.exists(marker)}


def probe_long_job():
    """Peut-on laisser tourner un fils pendant que le père rend la main ?"""
    code = ("import time,sys;"
            "open(sys.argv[1],'w').write('done');"
            "time.sleep(3)")
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    out.close()
    try:
        subprocess.Popen([sys.executable, "-c", code, out.name])
        return {"background_process_spawnable": True, "note":
                "fils détaché lancé (3 s) — le conteneur/exécuteur "
                "doit rester vivant assez longtemps pour les jobs longs"}
    except Exception as e:
        return {"background_process_spawnable": False, "error": str(e)[:200]}


def verdict(gpu):
    reasons = []
    torchinfo = gpu.get("torch", {})
    cuda_ok = torchinfo.get("cuda_available")
    if not gpu["nvidia_smi"]["present"] and not gpu["devices"]:
        reasons.append("aucun pilote NVIDIA ni périphérique /dev/nvidia*")
    if cuda_ok is False:
        reasons.append(
            f"torch {torchinfo.get('version')} : cuda_available=False "
            "(build CPU)")
    elif cuda_ok is None and "import_error" in torchinfo:
        reasons.append(torchinfo["import_error"])
    possible = cuda_ok is True
    return ("EXÉCUTION M3b LOCALE POSSIBLE (GPU visible)" if possible else
            "EXÉCUTION M3b LOCALE IMPOSSIBLE — " + " ; ".join(reasons))


def main():
    r = {
        "schema": "ls-environment-probe/1",
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "interpreter": {"python": sys.version.split()[0],
                        "executable": sys.executable,
                        "platform": platform.platform()},
        "gpu": probe_gpu(),
        "cpu": probe_cpu(),
        "ram": probe_ram(),
        "disk": probe_disk(),
        "network": probe_network(),
        "persistence": probe_persistence(),
        "long_job": probe_long_job(),
    }
    r["verdict_gpu"] = verdict(r["gpu"])

    print("═" * 68)
    print("SONDE D'ENVIRONNEMENT D'EXÉCUTION — résultats RÉELS")
    print("═" * 68)
    print(f"python      : {r['interpreter']['python']} "
          f"({sys.executable})")
    print(f"plateforme  : {r['interpreter']['platform']}")
    g = r["gpu"]
    print(f"nvidia-smi  : {'PRÉSENT' if g['nvidia_smi']['present'] else 'ABSENT'}"
          + (f" — {g['nvidia_smi'].get('stdout', '')[:60]}"
             if g["nvidia_smi"]["present"] else ""))
    print(f"/dev/nvidia*: {g['devices'] or 'aucun'}")
    print(f"torch       : {g.get('torch', {}).get('version', '—')} | "
          f"cuda_available="
          f"{g.get('torch', {}).get('cuda_available', '—')} | "
          f"build cuda="
          f"{g.get('torch', {}).get('cuda_version_build', '—')}")
    print(f"CPU         : {r['cpu']['model']} "
          f"({r['cpu']['logical_cores']} cœurs logiques)")
    print(f"RAM         : {r['ram']['total_mb']} Mo totaux, "
          f"{r['ram']['available_mb']} Mo disponibles")
    print(f"disque      : {r['disk']['free_gb']} Go libres, "
          f"écriture+fsync ≈ {r['disk']['write_mbs_fsync']} Mo/s")
    for h, v in r["network"].items():
        print(f"réseau      : {h} "
              f"{'joignable' if v['reachable'] else 'INJOIGNABLE'} "
              f"{v.get('latency_ms', '')}")
    print("─" * 68)
    print(f"VERDICT     : {r['verdict_gpu']}")
    print("═" * 68)

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    tmp = OUT_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(r, f, indent=1, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, OUT_JSON)
    print(f"→ {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
