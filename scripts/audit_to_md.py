# -*- coding: utf-8 -*-
"""Genere la version markdown d'archive du rapport d'instruction."""
import sys

sys.path.insert(0, "/home/z/my-project/scripts")

from audit_content_a import CH_1_4
from audit_content_b import CH_5_8


def to_md(blocks, out):
    lines = []
    for blk in blocks:
        kind = blk[0]
        if kind == "h1":
            lines += ["", "## " + blk[1], ""]
        elif kind == "h2":
            lines += ["", "### " + blk[1], ""]
        elif kind == "h3":
            lines += ["", "#### " + blk[1], ""]
        elif kind == "p":
            lines += [blk[1], ""]
        elif kind == "bullets":
            lines += ["- " + it for it in blk[1]] + [""]
        elif kind == "nums":
            lines += ["%d. %s" % (i + 1, it) for i, it in enumerate(blk[1])] + [""]
        elif kind == "quote":
            lines += ["", "> « %s »" % blk[1], ">", "> — *%s*" % blk[2], ""]
        elif kind == "callout":
            lines += ["", "> **%s** — %s" % (blk[1][0], blk[1][1]), ""]
        elif kind == "statrow":
            cells = [" | ".join(b for b, _ in blk[1]),
                     " | ".join("---" for _ in blk[1]),
                     " | ".join(l for _, l in blk[1])]
            lines += ["", " | ".join([""] * 0) + "\n".join(cells), ""]
        elif kind == "table":
            spec = blk[1]
            lines += ["", "| " + " | ".join(spec["head"]) + " |",
                      "| " + " | ".join("---" for _ in spec["head"]) + " |"]
            for row in spec["rows"]:
                lines += ["| " + " | ".join(str(c) for c in row) + " |"]
            lines += ["", "*" + spec["caption"] + "*", ""]
        elif kind == "fig":
            lines += ["", "![figure](" + blk[1].split("/")[-1] + ")", "",
                      "*" + blk[2] + "*", ""]
        elif kind == "note":
            lines += ["", "> " + blk[1], ""]
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).replace("\n\n\n", "\n\n"))
    print("MD OK:", out)


HEADER = """# Légalement Subjective sous examen — rapport d'instruction

> **Dossier LS-AUDIT-001 · établi le 27 août 2026 · commit 3ec9f3b · dépôt Vitalcheffe/legally-subjective**
>
> Rapport d'instruction interne : le projet passe au tribunal de sa propre
> méthode. Chaque chiffre a été recalculé depuis les pièces du dépôt.
> Huit chefs d'accusation, trois témoins hostiles, six scénarios de mort,
> une sentence en douze injonctions. Le but : survivre aux commentaires
> des autres.

---
"""

with open("/home/z/my-project/archives/rapport-instruction-2026-08-27.md",
          "w", encoding="utf-8") as f:
    f.write(HEADER)

to_md(CH_1_4, "/tmp/part1.md")
to_md(CH_5_8, "/tmp/part2.md")

with open("/home/z/my-project/archives/rapport-instruction-2026-08-27.md",
          "a", encoding="utf-8") as f:
    for part in ("/tmp/part1.md", "/tmp/part2.md"):
        f.write(open(part, encoding="utf-8").read())
    f.write("\n---\n\n*Sources de régénération : `scripts/audit_figures.py`, "
            "`scripts/audit_content_a.py`, `scripts/audit_content_b.py`, "
            "`scripts/audit_rapport.py`, `scripts/audit_cover.html`, "
            "`scripts/audit_merge.py`. Le PDF livré : "
            "`download/rapport-instruction-legally-subjective.pdf` (20 pages).*\n")

import os
print("taille:", os.path.getsize("/home/z/my-project/archives/rapport-instruction-2026-08-27.md"), "octets")
