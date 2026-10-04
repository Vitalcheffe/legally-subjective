#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3b — exécution des VRAIES cellules du notebook (harnais sans GPU).

Ce test charge notebooks/m3b_qlora_personas.ipynb et exécute le code EXACT
de ses cellules (seule transformation : le préfixe « /content » est réécrit
vers un bac à sable local, parce que /content n'existe que sur Colab) :

  cellule 4   imports + garde GPU (torch.cuda patché) ;
  cellule 6   CONFIG + RUN_ID ;
  cellule 8   §2bis — montage Drive (google.colab factice), clone (symlink),
              import m3b_state, statut brut ;
  cellules 10-11  PERSONAS_DIR + chargement des VRAIS personas du dépôt ;
  cellule 20  §5bis — empreinte + état (création VIERGE réelle) ;
  cellule 20 (2e passage) — reprise « resume » ;
  cellule 20 (config mutée) — REFUS attendu (AssertionError) ;
  cellules 24/26/28/30 — gardes « ignoré » + reset à confirmation.

Les cellules GPU (3, 18, 22) sont couvertes ailleurs : §6 par le VRAI
transformers (test_m3b_resume_cpu.py), l'environnement par le pin pip.

Auto-skip si torch est absent (CI = stdlib).
"""

import json
import os
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
NB = os.path.join(os.path.dirname(HERE), "notebooks",
                  "m3b_qlora_personas.ipynb")
SANDBOX = tempfile.mkdtemp(prefix="m3b_nbflow_")
REPO = os.path.dirname(HERE)

NPASS = NFAIL = 0


def check(cond, name, detail=""):
    global NPASS, NFAIL
    if cond:
        NPASS += 1
        print(f"  PASS  {name}")
    else:
        NFAIL += 1
        print(f"  FAIL  {name}  {detail}")


def cell_source(i):
    nb = json.load(open(NB, encoding="utf-8"))
    src = nb["cells"][i]["source"]
    src = "".join(src) if isinstance(src, list) else src
    # transformation mécanique et documentée : /content -> bac à sable
    return src.replace("/content", SANDBOX)


def magic_free(src):
    out = []
    for ln in src.split("\n"):
        s = ln.lstrip()
        if s.startswith(("%", "!")):
            indent = ln[: len(ln) - len(s)]
            out.append(indent + "pass")       # même indentation que la magie
        else:
            out.append(ln)
    return "\n".join(out)


def main():
    try:
        import torch                                        # noqa: F401
    except ImportError:
        print("SKIP — torch absent (CI stdlib). Exécuter avec .venvs/m3b.")
        return 0
    import torch

    # ---- patch CUDA (pas de GPU ici, la garde de la cellule 4 doit passer)
    torch.cuda.is_available = lambda: True
    torch.cuda.get_device_name = lambda *a: "FakeT4 (harnais CPU)"
    torch.cuda.get_device_properties = \
        lambda *a: type("P", (), {"total_memory": 16e9})()
    torch.cuda.is_bf16_supported = lambda: False
    torch.cuda.manual_seed_all = lambda *a: None

    # ---- bitsandbytes n'existe que côté GPU/Colab : la cellule 4 affiche
    # sa version — le harnais lui fournit une valeur factice (sur Colab,
    # le pip de la cellule 3 l'installe réellement).
    import importlib.metadata as _im
    _real_version = _im.version

    def _version_h(name, *a, **k):
        try:
            return _real_version(name, *a, **k)
        except _im.PackageNotFoundError:
            if name == "bitsandbytes":
                return "0.48.0-harnais"
            raise

    _im.version = _version_h

    # ---- google.colab factice : drive.mount crée le dossier --------------
    import types
    drive_mod = types.ModuleType("google.colab.drive")
    drive_mod.mount = lambda dest, **k: (os.makedirs(dest, exist_ok=True),
                                         print(f"[fake drive] monté : {dest}"))[0]
    colab_mod = types.ModuleType("google.colab")
    colab_mod.drive = drive_mod
    google_mod = types.ModuleType("google")
    google_mod.colab = colab_mod
    sys.modules["google"] = google_mod
    sys.modules["google.colab"] = colab_mod
    sys.modules["google.colab.drive"] = drive_mod

    # ---- le clone : symlink du dépôt local dans le bac à sable -----------
    os.makedirs(SANDBOX, exist_ok=True)
    os.symlink(REPO, os.path.join(SANDBOX, "legally-subjective"))

    G = {"__name__": "__main__"}

    def run_cell(i, name):
        src = magic_free(cell_source(i))
        try:
            exec(compile(src, f"<cellule {i+1}>", "exec"), G)
            return True, ""
        except Exception:
            return False, traceback.format_exc(limit=3)

    print("\n=== N1 · boot complet (cellules 4, 6, 8, 10, 11) ===")
    ok, err = run_cell(3, "imports+GPU")
    check(ok, "N1.cellule4", err)
    ok, err = run_cell(5, "config")
    check(ok, "N1.cellule6", err)
    ok, err = run_cell(7, "drive+clone+état brut")
    check(ok, "N1.cellule8_§2bis", err)
    check(G.get("HEAD") and len(G["HEAD"]) >= 7, "N1.HEAD_lu")
    check("m3b_state" in sys.modules, "N1.m3b_state_importé")
    ok, err = run_cell(9, "personas_dir")
    check(ok, "N1.cellule10", err)
    ok, err = run_cell(10, "load_personas")
    check(ok, "N1.cellule11", err)
    check(len(G.get("personas", {})) == 7, "N1.sept_personas",
          str(len(G.get("personas", {}))))

    print("\n=== N2 · §5bis : état VIERGE créé sur le « Drive » ===")
    ok, err = run_cell(19, "§5bis")
    check(ok, "N2.cellule20", err)
    check(G.get("MODE") == "fresh", "N2.mode_fresh", str(G.get("MODE")))
    st = json.load(open(os.path.join(SANDBOX, "drive", "MyDrive",
                                     "legally-subjective-m3b",
                                     "state.json"), encoding="utf-8"))
    check(st["schema"] == "m3b-state/2", "N2.schema")
    check(len(st["judges"]) == 7 and all(
        v["status"] == "pending" for v in st["judges"].values()),
        "N2.juges_pending")
    check(st["fingerprint"] == G["FINGERPRINT"], "N2.empreinte_cohérente")

    print("\n=== N3 · §5bis re-exécuté : REPRISE automatique ===")
    ok, err = run_cell(19, "§5bis (2e fois)")
    check(ok, "N3.cellule20_reexec", err)
    check(G.get("MODE") == "resume", "N3.mode_resume", str(globals().get("MODE")))
    st = json.load(open(os.path.join(SANDBOX, "drive", "MyDrive",
                                     "legally-subjective-m3b",
                                     "state.json"), encoding="utf-8"))
    check(len(st["sessions"]) == 1, "N3.pas_de_doublon_session")

    print("\n=== N4 · config scientifique mutée → REFUS ===")
    G["CONFIG"]["EPOCHS"] = 3                  # mutation scientifique
    ok, err = run_cell(19, "§5bis muté")
    check(not ok and "AssertionError" in err, "N4.refus_assert", err[-300:])
    G["CONFIG"]["EPOCHS"] = 8                  # restauration

    print("\n=== N5 · gardes des cellules finales (rien n'est entraîné) ===")
    for i, nm in ((23, "§7"), (25, "§7bis"), (27, "§8")):
        ok, err = run_cell(i, nm)
        check(ok, f"N5.garde_{nm}", err)
    ok, err = run_cell(29, "§8bis reset sans confirmation")
    check(ok, "N5.reset_refusé_sans_confirm", err)

    print("\n════════════════════════════════════════════════")
    print(f"NOTEBOOK (cellules réelles) : {NPASS} PASS / {NFAIL} FAIL")
    print("════════════════════════════════════════════════")
    return 1 if NFAIL else 0


if __name__ == "__main__":
    sys.exit(main())
