#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3b — gel du protocole scientifique du notebook (contrat architectural).

Contrat (cahier des charges LS-14/15, point 13) : améliorer l'INFRASTRUCTURE
M3b ne doit JAMAIS modifier la MÉTHODOLOGIE. Ce test rend le contrat
architectural : il extrait les fragments porteurs de protocole du notebook
généré et les compare, octet par octet, au gel de référence
(``results/protocol_m3b_freeze.json``).

Fragments gelés (définition du protocole M3b) :

  config_sci       bloc scientifique de CONFIG (modèle, LoRA, optimisation,
                   protocole — hors clés opérationnelles SAVE_STEPS/SOFT_);
  data_selection   sélection des personas (filtre >200 signes, tri temporel,
                   MIN_TRAIN_ROWS) ;
  temporal_split   découpage temporel no-leak (validation = plus récentes) ;
  tokenization     politique de troncature déclarée (encode_row) ;
  dataset          construction des tenseurs (masquage -100 du prompt) ;
  qlora_base       quantization 4-bit + préparation k-bit ;
  lora_targets     configuration LoRA (r, alpha, dropout, modules ciblés) ;
  training_args    l'appel TrainingArguments(...) EXACT (epochs, lr, warmup,
                   éval, batch, accumulation) ;
  eval_probe       paramètres de la sonde §7 (génération greedy 120 tokens) ;
  memo_audit       constantes de l'audit anti-mémorisation §7bis ;
  sci_keys         la définition des clés scientifiques dans m3b_state.py
                   (ce qui constitue l'empreinte d'expérience).

Toute divergence = FAIL avec le nom du fragment. Mettre à jour le gel exige
le rituel explicite ``--je-change-le-protocole`` (décision consciente,
consignée dans le journal du dépôt) — miroir du ``--je-brise-le-sceau`` M4.

Usage :
  python scripts/test_m3b_protocol_freeze.py            # vérifier (CI, local)
  python scripts/test_m3b_protocol_freeze.py --je-change-le-protocole
                                                         # régénérer le gel
"""

import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
NB = os.path.join(REPO, "notebooks", "m3b_qlora_personas.ipynb")
STATE = os.path.join(REPO, "scripts", "m3b_state.py")
GOLDEN = os.path.join(REPO, "results", "protocol_m3b_freeze.json")
RITUAL = "--je-change-le-protocole"
SCHEMA = "m3b-protocol-freeze/1"

NPASS = NFAIL = 0


def check(cond, name, detail=""):
    global NPASS, NFAIL
    if cond:
        NPASS += 1
        print(f"  PASS  {name}")
    else:
        NFAIL += 1
        print(f"  FAIL  {name}  {detail}")


def cell_sources():
    nb = json.load(open(NB, encoding="utf-8"))
    out = []
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        s = c["source"]
        out.append("".join(s) if isinstance(s, list) else s)
    return out


def _balanced_call(cell, opener):
    """Extrait l'appel complet ouvert par ``opener`` en équilibrant les
    parenthèses (robuste aux appels imbriqués du style f(x=g()))."""
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
        raise SystemExit(f"appel {opener!r} introuvable/incomplet")
    return "\n".join(acc)


def find_cell(cells, marker):
    hits = [c for c in cells if marker in c]
    if len(hits) != 1:
        raise SystemExit(f"fragment introuvable ou ambigu ({marker}) : "
                         f"{len(hits)} cellule(s)")
    return hits[0]


def extract_fragments():
    cells = cell_sources()

    cfg = find_cell(cells, "CONFIG = {")
    # bloc scientifique = tout ce qui précède le marqueur opérationnel
    sci_block = cfg.split("# ---- opérationnel")[0]

    train_cell = find_cell(cells, "def train_one")
    training_args = _balanced_call(train_cell, "args = TrainingArguments(")

    memo_cell = find_cell(cells, "def cloze_hits")
    m = re.search(r"^\s+K_FRAC.*$", memo_cell, re.M)
    if not m:
        raise SystemExit("constantes d'audit §7bis introuvables")
    memo_consts = m.group(0)

    probe_cell = find_cell(cells, "def generate(name, instruction")
    m = re.search(r"^\s+def generate\(name, instruction.*$",
                  probe_cell, re.M)
    probe_sig = m.group(0)

    state_src = open(STATE, encoding="utf-8").read()
    m = re.search(r"SCI_KEYS = \(.*?\)", state_src, re.S)
    if not m:
        raise SystemExit("SCI_KEYS introuvable dans m3b_state.py")
    sci_keys = m.group(0)

    return {
        "config_sci": sci_block,
        "data_selection": find_cell(cells, "def load_persona"),
        "temporal_split": find_cell(cells, "def temporal_split"),
        "tokenization": find_cell(cells, "def encode_row"),
        "dataset": find_cell(cells, "class PersonaTorch"),
        "qlora_base": find_cell(cells, "bnb_cfg = BitsAndBytesConfig"),
        "lora_targets": find_cell(cells, "def make_lora"),
        "training_args": training_args,
        "eval_probe": probe_sig,
        "memo_audit": memo_consts,
        "sci_keys": sci_keys,
    }


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument(RITUAL, action="store_true", dest="update")
    opts, _ = ap.parse_known_args(sys.argv[1:])

    frags = extract_fragments()
    if opts.update:
        print("⚠ RITUEL — le gel du protocole M3b est RÉGÉNÉRÉ.")
        print("  C'est un geste protocolaire explicite : consigner la décision")
        print("  dans le journal du dépôt et prévenir le porteur du projet.")
        golden = {"schema": SCHEMA,
                  "note": "gel régénéré par rituel --je-change-le-protocole",
                  "fragments": {k: {"sha256": hashlib.sha256(
                                        v.encode("utf-8")).hexdigest(),
                                    "n_lines": len(v.splitlines())}
                                for k, v in frags.items()},
                  "texts": {k: v for k, v in frags.items()}}
        os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
        tmp = GOLDEN + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(golden, f, indent=1, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, GOLDEN)
        print(f"→ nouveau gel : {GOLDEN} ({len(frags)} fragments)")
        return 0

    if not os.path.exists(GOLDEN):
        print(f"FAIL — gel absent : {GOLDEN}")
        print("  le créer UNE fois depuis un état de confiance :")
        print(f"  python {os.path.basename(__file__)} {RITUAL}")
        return 1
    golden = json.load(open(GOLDEN, encoding="utf-8"))
    check(golden.get("schema") == SCHEMA, "gel.schema", golden.get("schema"))

    texts = golden.get("texts", {})
    for name in sorted(golden.get("fragments", {})):
        want = texts.get(name)
        got = frags.get(name)
        if got is None:
            check(False, f"protocole.{name}", "fragment absent du notebook")
            continue
        h = hashlib.sha256(got.encode("utf-8")).hexdigest()
        ok = (want == got) and \
             (h == golden["fragments"][name]["sha256"])
        detail = "" if ok else (
            f"divergence — gel {golden['fragments'][name]['sha256'][:12]}… "
            f"vs notebook {h[:12]}… ; diff minimal :")
        check(ok, f"protocole.{name}", detail)
        if not ok and want is not None:
            wl, gl = want.splitlines(), got.splitlines()
            shown = 0
            for i in range(max(len(wl), len(gl))):
                a = wl[i] if i < len(wl) else "<absent>"
                b = gl[i] if i < len(gl) else "<absent>"
                if a != b:
                    print(f"        gel   : {a[:90]}")
                    print(f"        actuel: {b[:90]}")
                    shown += 1
                    if shown >= 6:
                        print("        …")
                        break

    print("─" * 60)
    print(f"GEL DU PROTOCOLE M3b : {NPASS} PASS / {NFAIL} FAIL")
    if not NFAIL:
        print("la méthodologie du notebook est INTACTE — seules les parties "
              "infrastructure peuvent avoir bougé")
    return 1 if NFAIL else 0


if __name__ == "__main__":
    sys.exit(main())
