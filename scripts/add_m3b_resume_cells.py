#!/usr/bin/env python3
"""Ajoute la reprise multisession au notebook M3b (idempotent).

L'entraînement complet (7 juges, ~15-22 h sur T4 gratuit) dépasse une
session Colab. Ce patch rend le notebook repreneur :

1. insère une section 5bis (téléversement du zip précédent ->
   restauration des adaptateurs + du rapport) ;
2. rend la boucle d'entraînement (section 6) consciente du rapport
   restauré : les juges déjà faits (et dont l'adaptateur est présent)
   sont sautés ;
3. l'export (section 8) zippe TOUT répertoire d'adaptateur présent,
   pas seulement les personas actives — un adaptateur restauré d'une
   session précédente est donc toujours ré-exporté.

Chaîne de régénération : ce script POST-traite le notebook généré par
make_qlora_notebook.py (même principe que add_mem_audit_cells.py) ;
il ne le régénère pas.
"""
import json
import sys

NB = "notebooks/m3b_qlora_personas.ipynb"

# ------------------------------------------------------------------ patch --
MD_5BIS = """### 5bis · Reprise multisession (sessions suivantes uniquement)

L'entraînement complet dépasse une session Colab gratuite. À chaque
nouvelle session : ré-exécuter les cellules des sections 1 à 5, puis
**téléverser ici le zip exporté par la session précédente**
(`m3b_adapters_*.zip`). Les adaptateurs déjà entraînés sont restaurés
dans `adapters/`, le rapport `m3b_report.json` est remonté à la racine,
et la section 6 n'entraînera que les juges restants. Première session :
ne rien téléverser — la cellule reste sans effet."""

CODE_5BIS = """# --- 5bis · reprise : restaurer les adaptateurs d'une session précédente
import glob as _glob
_zips = sorted(_glob.glob("m3b_adapters_*.zip"))
try:                                    # Colab : boîte de téléversement
    from google.colab import files as _files
    _up = _files.upload()               # choisir le zip précédent (optionnel)
    _zips += [fn for fn in _up if fn not in _zips]
except Exception:
    pass                                # hors Colab / rien téléversé
if not _zips:
    print("première session : aucun zip de reprise — entraînement complet")
for _zn in _zips:
    with zipfile.ZipFile(_zn) as _z:
        _names = _z.namelist()
        _z.extractall(ADAPTER_DIR)      # <juge>/… -> adapters/<juge>/…
        if "m3b_report.json" in _names:  # le rapport sort sous adapters/
            os.replace(os.path.join(ADAPTER_DIR, "m3b_report.json"),
                       REPORT)
    _n_ad = sum(1 for n in _names if n.endswith("adapter_config.json"))
    print(f"restauré : {_zn} ({_n_ad} adaptateurs)")"""

TRAIN_TAIL_NEW = """report = {"config": CONFIG, "model": CONFIG["MODEL_ID"],
          "run_id": RUN_ID, "results": []}
if os.path.exists(REPORT):        # reprise : rapport restauré par la 5bis
    try:
        _old = json.load(open(REPORT, encoding="utf-8"))
        report["results"] = _old.get("results", [])
        print(f"reprise : {len(report['results'])} juge(s) déjà fait(s)")
    except Exception as _e:
        print("rapport illisible — reprise ignorée :", _e)
for name in personas:
    _done = any(r.get("persona") == name for r in report["results"])
    if _done and os.path.isdir(os.path.join(ADAPTER_DIR, name)):
        print(f"=== {name} — déjà entraîné (reprise), sauté ===")
        continue
    if _done:   # inscrit au rapport mais adaptateur absent : réentraîner
        report["results"] = [r for r in report["results"]
                             if r.get("persona") != name]
    print(f"\\n=== {name} ===")
    report["results"].append(train_one(name, personas[name]))
    with open(REPORT, "w") as f:
        json.dump(report, f, indent=1)   # checkpoint après chaque juge"""

EXPORT_OLD = """    for name in personas:
        for fn in os.listdir(os.path.join(ADAPTER_DIR, name)):
            z.write(os.path.join(ADAPTER_DIR, name, fn), f"{name}/{fn}")"""

EXPORT_NEW = """    for name in sorted(os.listdir(ADAPTER_DIR)):
        _d = os.path.join(ADAPTER_DIR, name)
        if not os.path.isdir(_d):
            continue
        for fn in os.listdir(_d):
            z.write(os.path.join(_d, fn), f"{name}/{fn}")"""


def lines(s):
    out, buf = [], ""
    for ch in s:
        buf += ch
        if ch == "\n":
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return out


def main():
    nb = json.load(open(NB, encoding="utf-8"))
    joined = ["".join(c["source"]) for c in nb["cells"]]

    if any("5bis · reprise" in s for s in joined):
        print("déjà patché (5bis présent) — rien à faire")
        return 0

    # -- 1. insérer 5bis avant le markdown « ## 6 · Entraînement » --------
    idx6 = next(i for i, s in enumerate(joined)
                if s.startswith("## 6 · Entraînement"))
    nb["cells"].insert(idx6, {"cell_type": "markdown", "metadata": {},
                              "source": lines(MD_5BIS)})
    nb["cells"].insert(idx6 + 1, {"cell_type": "code",
                                  "execution_count": None,
                                  "metadata": {}, "outputs": [],
                                  "source": lines(CODE_5BIS)})
    print(f"5bis inséré avant la cellule {idx6}")

    # -- 2. boucle d'entraînement repreneur -------------------------------
    itr = next(i for i, c in enumerate(nb["cells"])
               if c["cell_type"] == "code"
               and "def train_one" in "".join(c["source"]))
    src = "".join(nb["cells"][itr]["source"])
    cut = src.find('report = {"config"')
    assert cut > 0, "marqueur boucle d'entraînement introuvable"
    nb["cells"][itr]["source"] = lines(src[:cut] + TRAIN_TAIL_NEW)
    print(f"cellule d'entraînement {itr} rendue repreneuse")

    # -- 3. export : tout adaptateur présent -------------------------------
    # (chercher par la signature d'export, pas « m3b_adapters_ » : la
    # cellule 5bis insérée ci-dessus contient aussi cette chaîne)
    iex = next(i for i, c in enumerate(nb["cells"])
               if c["cell_type"] == "code"
               and "z.write(REPORT, REPORT)" in "".join(c["source"]))
    src = "".join(nb["cells"][iex]["source"])
    assert EXPORT_OLD in src, "bloc export introuvable"
    nb["cells"][iex]["source"] = lines(src.replace(EXPORT_OLD, EXPORT_NEW))
    print(f"cellule d'export {iex} étendue à tous les adaptateurs")

    with open(NB, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"OK — {NB} : {len(nb['cells'])} cellules")
    return 0


if __name__ == "__main__":
    sys.exit(main())
