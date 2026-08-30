#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M3: pré-vol du notebook Colab (sans GPU).

Simule localement, en stdlib pur, tout ce que le notebook m3b fait AVANT
d'allumer un GPU — pour ne découvrir aucun pépin de données pendant une
session T4 comptée :

  1. acquisition données (Option A: repo) — fichiers personas présents ;
  2. load_persona (filtre output > 200 cars, tri temporel) ;
  3. garde MIN_TRAIN_ROWS (8) — qui passe, qui est sauté ;
  4. split temporel VAL_FRACTION=0.15 — tailles réelles train/val ;
  5. budget de séquence en HEURISTIQUE chars/4 (le vrai tokeniseur
     tournera sur Colab) : part des lignes tenant dans MAX_LEN=4096,
     part des instructions dépassant INSTR_KEEP=1024.

Sortie : results/m3_preflight.md
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSONAS = os.path.join(REPO, "data", "m3", "personas")
OUT = os.path.join(REPO, "results", "m3_preflight.md")

MIN_TRAIN_ROWS, VAL_FRACTION = 8, 0.15
MAX_LEN, INSTR_KEEP = 4096, 1024          # tokens (notebook CONFIG)
CHARS_PER_TOKEN = 4                       # heuristique affichée comme telle


def load_persona(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("output") and len(r["output"]) > 200:
                rows.append(r)
    rows.sort(key=lambda r: r.get("date_filed") or "9999")
    return rows


def temporal_split(rows, frac=VAL_FRACTION):
    if len(rows) < 4:
        return rows, rows
    cut = max(1, int(len(rows) * (1 - frac)))
    return rows[:cut], rows[cut:]


def main():
    md = [
        "# M3 — Pré-vol du notebook Colab (exécuté sans GPU, données seules)",
        "",
        f"Heuristique de tokens : **chars/{CHARS_PER_TOKEN}** (le tokeniseur",
        "réel tourne dans le notebook ; ici on borne les surprises).",
        "",
        "| Persona | Brutes | Gardées (>200 c) | Train | Val | Fenêtre |",
        "| médias out (c) | Instr. >budget | Lignes >MAX_LEN |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    active, skipped = [], []
    for name in sorted(os.listdir(PERSONAS)):
        p = os.path.join(PERSONAS, name, "train.jsonl")
        if not os.path.isfile(p):
            continue
        raw = sum(1 for _ in open(p, encoding="utf-8"))
        rows = load_persona(p)
        if len(rows) < MIN_TRAIN_ROWS:
            skipped.append((name, len(rows)))
            continue
        active.append(name)
        tr, va = temporal_split(rows)

        def stats(rs):
            outs = [len(r["output"]) for r in rs]
            instr_over = sum(
                1 for r in rs
                if len(r["instruction"]) > INSTR_KEEP * CHARS_PER_TOKEN)
            over_max = sum(
                1 for r in rs
                if (len(r["instruction"]) + len(r["output"]))
                / CHARS_PER_TOKEN > MAX_LEN - 128)     # marge template
            return (int(sum(outs) / len(outs)) if outs else 0,
                    instr_over, over_max)

        s_tr, s_va = stats(tr), stats(va)
        n_over = s_tr[1] + s_va[1]
        n_max = s_tr[2] + s_va[2]
        md.append(
            f"| {name} | {raw} | {len(rows)} | {len(tr)} | {len(va)} "
            f"| {rows[0]['date_filed']}→{rows[-1]['date_filed']} "
            f"| {(s_tr[0] + s_va[0]) // 2} | {n_over} | {n_max} |")

    total_train = 0
    md += [
        "",
        f"- Personas **actives** ({len(active)}) : {', '.join(active)}",
        f"- Personas **sautées** (< {MIN_TRAIN_ROWS} lignes) : "
        + (", ".join(f"{n} ({c} lignes)" for n, c in skipped)
           if skipped else "aucune"),
        "",
        "## Lecture",
        "",
        "- « Instr. >budget » : lignes dont l'instruction dépasse le budget",
        f"  INSTR_KEEP = {INSTR_KEEP} tokens en heuristique — le notebook",
        "  la tronque **par la tête** (la question présentée vit en queue) ;",
        "  c'est attendu, pas un défaut.",
        "- « Lignes >MAX_LEN » : lignes dont instruction+output débordent",
        f"  MAX_LEN = {MAX_LEN} tokens en heuristique — le notebook réduit",
        "  la sortie par la queue ; les personas à forte proportion perdent",
        "  du signal d'entraînement (à comparer avec le tokeniseur réel).",
        "",
        "---",
        "",
        "*Généré par `scripts/m3_preflight.py` — stdlib seule, aucun réseau.*",
    ]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md[:14]))
    print("→", os.path.relpath(OUT, REPO))


if __name__ == "__main__":
    main()
