# -*- coding: utf-8 -*-
"""Fusionne couverture + corps en un seul PDF A4 normalise."""
from pypdf import PdfReader, PdfWriter

A4_W, A4_H = 595.28, 841.89

COVER = "/home/z/my-project/scripts/audit_figs/audit_cover.pdf"
BODY = "/home/z/my-project/scripts/audit_figs/audit_body.pdf"
OUT = "/home/z/my-project/download/rapport-instruction-legally-subjective.pdf"


def normalize(page):
    box = page.mediabox
    w, h = float(box.width), float(box.height)
    if abs(w - A4_W) > 0.1 or abs(h - A4_H) > 0.1:
        page.scale_to(A4_W, A4_H)
    return page


writer = PdfWriter()
writer.add_page(normalize(PdfReader(COVER).pages[0]))
for p in PdfReader(BODY).pages:
    writer.add_page(normalize(p))

writer.add_metadata({
    "/Title": "Légalement Subjective sous examen — rapport d'instruction",
    "/Author": "Z.ai",
    "/Creator": "Z.ai",
    "/Subject": "Audit hostile interne du projet Légalement Subjective",
})
with open(OUT, "wb") as f:
    writer.write(f)

r = PdfReader(OUT)
print("MERGE OK:", OUT)
print("pages:", len(r.pages), "| taille:", __import__("os").path.getsize(OUT), "octets")
