#!/usr/bin/env python3
"""Valide le notebook: AST sur le code Python réel.

Les lignes magiques IPython (%pip, !git, continuations comprises) sont
remplacées par `pass` indenté — syntaxe valide — avant l'analyse.
"""
import ast
import sys

import nbformat

path = sys.argv[1] if len(sys.argv) > 1 else "notebooks/m3b_qlora_personas.ipynb"
nb = nbformat.read(path, as_version=4)
nerr = 0
for i, c in enumerate(nb.cells):
    if c.cell_type != "code":
        continue
    lines = c.source.split("\n")
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
print("cellules:", len(nb.cells), "| erreurs réelles:", nerr)
sys.exit(1 if nerr else 0)
