#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — captures de preuves D'EXÉCUTIONS RÉELLES.

Règle absolue (cahier des charges LS-15, §VII) : on ne fabrique JAMAIS une
preuve. Chaque capture est la sortie NON MODIFIÉE d'une commande réellement
exécutée, accompagnée de son contexte complet (horodatage UTC, répertoire,
commit git, propreté de l'arbre, commande exacte, code de retour, durée).

Une capture peut être TRONQUÉE si la sortie est énorme — mais la troncature
est alors marquée explicitement dans le fichier ([sortie tronquée…]).

Format du dossier de preuves :

    EVIDENCE/
      001_environnement.txt     sortie réelle + en-tête de contexte
      002_….txt
      index.json                index machine-readable (append atomique)
      index.md                  index lisible (régénéré à chaque capture)

Chaque entrée d'index relie : ID → ce que montre la capture → commande →
commit → code retour → fichier. Les captures COMPLÈTENT les journaux et
artefacts machine-readable ; elles ne les remplacent jamais.

Usage :
  python scripts/capture_evidence.py <slug> --note "…" [--outdir DIR] \
         [--png] [--timeout S] -- <commande args…>
  python scripts/capture_evidence.py --index [--outdir DIR]   # régénère index.md
"""

import argparse
import json
import os
import subprocess
import sys
import time

MAX_OUT = 2_000_000          # 2 Mo — au-delà : troncature marquée


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def git_context(cwd):
    def run(*args):
        try:
            return subprocess.run(
                ["git", "-C", cwd, *args], capture_output=True,
                text=True, timeout=15).stdout.strip()
        except Exception:
            return ""
    head = run("rev-parse", "HEAD")
    if not head:
        return None, None, 0
    status = run("status", "--porcelain")
    dirty = [l for l in status.splitlines() if l.strip()]
    return head, status, len(dirty)


def load_index(outdir):
    p = os.path.join(outdir, "index.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return {"schema": "ls-evidence/1", "captures": []}


def atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def write_index_md(outdir, idx):
    lines = ["# Index des captures de preuves — exécutions réelles", ""]
    lines.append("Chaque fichier contient la sortie non modifiée d'une "
                 "commande réellement exécutée, avec horodatage UTC, "
                 "commit git et code de retour.")
    lines.append("")
    lines.append("| ID | fichier | ce que ça prouve | commande | commit | rc | UTC |")
    lines.append("|----|---------|------------------|----------|--------|----|-----|")
    for c in idx["captures"]:
        cmd = " ".join(c["cmd"])[:60].replace("|", "\\|")
        note = (c.get("note") or "")[:80].replace("|", "\\|")
        lines.append(
            f"| {c['id']} | `{os.path.basename(c['file'])}` | {note} "
            f"| `{cmd}` | `{(c.get('git_head') or '-')[:10]}` "
            f"| {c['rc']} | {c['ts_utc']} |")
    lines.append("")
    atomic_write(os.path.join(outdir, "index.md"), "\n".join(lines))


def render_png(path_txt, path_png):
    """Rendu IMAGE d'une sortie réelle — l'image est générée depuis le
    fichier texte capturé, et l'estampille « rendu d'une sortie réelle »
    figure dans l'image elle-même. Ce n'est jamais une interface simulée."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  (matplotlib absent — pas de rendu PNG)")
        return False
    txt = open(path_txt, encoding="utf-8").read()
    lines = txt.splitlines()
    keep = 64
    if len(lines) > keep:
        half = keep // 2
        lines = (lines[:half]
                 + [f"… [{len(lines) - keep} lignes omises dans le rendu "
                    f"— fichier texte complet = source de vérité] …"]
                 + lines[-half:])
    fig = plt.figure(figsize=(11, min(0.30 * len(lines) + 1.2, 22)),
                     facecolor="#101418")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#101418")
    ax.text(0.0, 1.0, "\n".join(lines), va="top", ha="left",
            family="monospace", fontsize=6.5, color="#d8dee9",
            transform=ax.transAxes)
    ax.axis("off")
    fig.text(0.99, 0.005,
             "rendu image d'une sortie d'exécution RÉELLE — source : "
             f"{os.path.basename(path_txt)}",
             ha="right", fontsize=6, color="#8a929e")
    fig.savefig(path_png, dpi=150, facecolor="#101418",
                bbox_inches="tight")
    plt.close(fig)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?", help="identifiant court du fichier")
    ap.add_argument("--note", default="", help="ce que cette capture prouve")
    ap.add_argument("--outdir", default="EVIDENCE")
    ap.add_argument("--png", action="store_true",
                    help="produit aussi un rendu image de la sortie réelle")
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--index", action="store_true",
                    help="régénérer uniquement index.md")
    ap.add_argument("cmd", nargs="*", help="commande (après --)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    if args.index:
        write_index_md(args.outdir, load_index(args.outdir))
        print("index.md régénéré")
        return 0

    if not args.slug or not args.cmd:
        ap.error("slug + commande requis (mettre la commande après --)")

    cwd = os.getcwd()
    head, status, n_dirty = git_context(cwd)
    idx = load_index(args.outdir)
    seq = max((c.get("seq", 0) for c in idx["captures"]), default=0) + 1
    cid = f"{seq:03d}"
    slug = "".join(ch if ch.isalnum() or ch in "-_" else "-"
                   for ch in args.slug)[:60]
    fname = f"{cid}_{slug}.txt"
    path = os.path.join(args.outdir, fname)

    t0 = time.time()
    proc = subprocess.run(args.cmd, cwd=cwd, timeout=args.timeout,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    dur = time.time() - t0
    out = proc.stdout.decode("utf-8", errors="replace")

    header = [
        "═" * 72,
        f"CAPTURE {cid} — {slug}",
        f"prouve   : {args.note}" if args.note else "prouve   : (voir index)",
        f"utc      : {utc_now()}",
        f"cwd      : {cwd}",
        f"git_head : {head or '(hors dépôt)'}",
        f"git_propre: {'oui' if head and n_dirty == 0 else 'non'}"
        + (f" ({n_dirty} fichiers modifiés)" if n_dirty else ""),
        f"commande : {' '.join(args.cmd)}",
        f"code_retour : {proc.returncode}   durée : {dur:.1f} s",
        "─" * 72,
        "SORTIE RÉELLE NON MODIFIÉE :",
        "",
    ]
    if len(out) > MAX_OUT:
        out = (out[:MAX_OUT]
               + f"\n… [sortie tronquée : {len(out)} caractères au total, "
                 f"{len(out) - MAX_OUT} omis — marqueur explicite] …")
    body = "\n".join(header) + out + "\n"
    atomic_write(path, body)

    entry = {"seq": seq, "id": cid, "slug": slug, "note": args.note,
             "ts_utc": utc_now(), "cwd": cwd, "git_head": head,
             "git_dirty": n_dirty, "cmd": args.cmd,
             "rc": proc.returncode, "duration_s": round(dur, 1),
             "file": path}
    idx["captures"].append(entry)
    atomic_write(os.path.join(args.outdir, "index.json"),
                 json.dumps(idx, indent=1, ensure_ascii=False))
    write_index_md(args.outdir, idx)

    if args.png:
        render_png(path, os.path.join(args.outdir, f"{cid}_{slug}.png"))

    print(f"capture {cid} → {path} (rc={proc.returncode}, {dur:.1f} s)")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
