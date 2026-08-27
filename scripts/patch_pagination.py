#!/usr/bin/env python3
"""Post-traitement pagination INFINITUM docx :
1. identifie les sections et leurs footers (via document.xml + rels)
2. patche l'instrText PAGE du footer de la section TOC en ROMAN,
   celui de la section corps en arab
3. supprime les <w:pgNumType/> vides (compatibilite WPS)
"""
import re
import shutil
import sys
import zipfile
from pathlib import Path

DOCX = Path("/home/z/my-project/download/INFINITUM_Rapport_Direction_UI.docx")
TMP = DOCX.with_suffix(".tmp.docx")


def main():
    with zipfile.ZipFile(DOCX) as zin:
        names = zin.namelist()
        data = {n: zin.read(n) for n in names}

    doc = data["word/document.xml"].decode("utf-8")
    rels = data["word/_rels/document.xml.rels"].decode("utf-8")

    # rId -> fichier footer
    rid_to_target = dict(re.findall(r'<Relationship[^>]*Id="([^"]+)"[^>]*Target="(footer\d+\.xml)"', rels))
    # certaines attributs sont dans un ordre different
    for m in re.finditer(r"<Relationship\b[^>]*/>", rels):
        tag = m.group(0)
        rid = re.search(r'Id="([^"]+)"', tag)
        tgt = re.search(r'Target="(footer\d+\.xml)"', tag)
        if rid and tgt:
            rid_to_target[rid.group(1)] = tgt.group(1)

    # sectPr dans l'ordre
    sects = re.findall(r"<w:sectPr\b.*?</w:sectPr>", doc, flags=re.S)
    print(f"sections trouvees : {len(sects)}")

    patched = {}
    for idx, sect in enumerate(sects):
        # footer par defaut de la section
        fref = re.search(r'<w:footerReference[^>]*w:type="default"[^>]*r:id="([^"]+)"', sect)
        if not fref:
            fref = re.search(r'<w:footerReference[^>]*r:id="([^"]+)"[^>]*w:type="default"', sect)
        if not fref:
            print(f"  section {idx+1}: pas de footer de reference")
            continue
        target = rid_to_target.get(fref.group(1))
        if not target:
            print(f"  section {idx+1}: rId {fref.group(1)} sans cible")
            continue
        fmt = None
        if 'w:fmt="upperRoman"' in sect or 'w:fmt="lowerRoman"' in sect:
            fmt = "ROMAN"
        elif 'w:fmt=' in sect or idx >= 2:
            fmt = "arabic"
        if fmt:
            key = "word/" + target
            fx = data[key].decode("utf-8")
            fx2 = re.sub(r"(<w:instrText[^>]*>)\s*PAGE\s*(</w:instrText>)",
                         r"\g<1> PAGE \\* " + fmt + r" \\* MERGEFORMAT \g<2>", fx)
            if fx2 != fx:
                data[key] = fx2.encode("utf-8")
                patched[key] = fmt
                print(f"  section {idx+1}: {target} -> PAGE \\* {fmt}")
            else:
                print(f"  section {idx+1}: {target} sans champ PAGE a patcher")

    # retirer les pgNumType vides (section couverture)
    doc2 = doc.replace("<w:pgNumType/>", "")
    if doc2 != doc:
        print("pgNumType vide supprime (section couverture)")
    data["word/document.xml"] = doc2.encode("utf-8")

    with zipfile.ZipFile(TMP, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            zout.writestr(n, data[n])
    shutil.move(TMP, DOCX)
    print("OK — pagination patchee")


if __name__ == "__main__":
    sys.exit(main())
