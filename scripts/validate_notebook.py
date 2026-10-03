#!/usr/bin/env python3
"""Valide le notebook: AST sur le code Python réel.

Les lignes magiques IPython (%pip, !git, continuations comprises) sont
remplacées par `pass` indenté — syntaxe valide — avant l'analyse.
Stdlib uniquement : un notebook est du JSON, pas besoin de dépendance.
"""
import ast
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "notebooks/m3b_qlora_personas.ipynb"
nb = json.load(open(path, encoding="utf-8"))
if nb.get("nbformat") != 4:
    print("format notebook non v4 :", nb.get("nbformat"))
    sys.exit(1)


def cell_source(c):
    src = c.get("source", "")
    return "".join(src) if isinstance(src, list) else src


nerr = 0
for i, c in enumerate(nb["cells"]):
    if c.get("cell_type") != "code":
        continue
    lines = cell_source(c).split("\n")
    out = []
    in_magic = False
    for ln in lines:
        if in_magic:
            in_magic = ln.rstrip().endswith("\\")
            continue                       # avale les continuations de magie
        stripped = ln.lstrip()
        if stripped.startswith(("%", "!")):
            indent = ln[: len(ln) - len(stripped)]
            out.append(indent + "pass")   # placeholder valide dans un bloc
            if ln.rstrip().endswith("\\"):
                in_magic = True
        else:
            out.append(ln)
    src = "\n".join(out)
    try:
        ast.parse(src)
    except SyntaxError as e:
        nerr += 1
        print(f"cellule {i}: SyntaxError: {e}")
        ctx = src.splitlines()
        print("   contexte:", ctx[max(0, (e.lineno or 1) - 2):(e.lineno or 1)])
print("cellules:", len(nb["cells"]), "| erreurs réelles:", nerr)
sys.exit(1 if nerr else 0)
