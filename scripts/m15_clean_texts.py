#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M1.5 étape 2+3 : déduplication + normalisation.

C'est l'étape 2 de l'ordre d'exécution pré-enregistré (docs/04-PROTOCOLE.md) :
nettoyage des textes AVANT tout entraînement. Le traitement est déterministe,
aveugle à l'issue (aucune information de décision n'est lue ni écrite), et
s'applique mécaniquement à tout le corpus — le scellé reste exclu de tout
artefact de DATASET par les builders, jamais du magasin de textes (M4 en
aura besoin, et le nettoyage ne regarde pas les résultats).

Entrée  : data/m15_store/final/opinion_texts_v2.jsonl.gz (1778, canonique,
          intouché — la provenance reste la vérité)
Sortie  : data/m15_store/clean/
            opinion_texts_v3.jsonl.gz  — exemplaires conservés, textes propres
            dedup_map.json             — les 1778 ids → id conservé
            clean_report.json          — statistiques complètes

Normalisation (règles pré-enregistrées, roadmap M1.5.3) :
  NFC ; en-têtes de slip (« Cite as: », « (Slip Opinion) », « OCTOBER TERM »,
  « SUPREME COURT OF THE UNITED STATES », « Syllabus », note du Reporter) ;
  numéros de page (lignes numériques seules, marqueurs *1234 Harvard) ;
  dépliage des paragraphes (le texte passe en paragraphes continus) ;
  notes de bas de page SIGNALÉES (comptées) mais CONSERVÉES.

Déduplication (roadmap M1.5.2) :
  ratio ≥ 0,95 sur le texte normalisé pour comparaison. Deux passes :
  exacte (empreinte du texte sans ponctuation/casse) puis quasi-exacte
  (difflib ≥ 0,95 sur 6 000 premiers caractères, candidats même affaire).
  On conserve l'exemplaire le plus propre : priorité api:plain_text >
  api:xml_harvard > storage:direct > storage:bound-type > legacy > snippet,
  puis le texte le plus long, puis l'id le plus bas (déterminisme).

L'inventaire du corpus (1778 lignes d'opinions, gel M1) NE CHANGE PAS.
La carte de déduplication documente chaque fusion : row id X = doublon de
l'exemplaire conservé Y.
"""
import argparse
import difflib
import gzip
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(REPO, "data", "m15_store", "final",
                  "opinion_texts_v2.jsonl.gz")
OUT_DIR = os.path.join(REPO, "data", "m15_store", "clean")

SOURCE_RANK = {
    "api:plain_text": 0, "api:xml_harvard": 1, "api:html": 2,
    "storage:direct": 3, "storage:bound-type": 4, "legacy:bc": 5,
    "storage:snippet": 6,
}

# ------------------------------------------------------------------ normal --

FURNITURE_PATTERNS = [
    # slip cover + page furniture
    (re.compile(r"^\(Slip Opinion\).*$"), "slip_hdr"),
    (re.compile(r"^Cite as: .*$"), "cite_as"),
    (re.compile(r"^\s*OCTOBER TERM,?\s+20\d\d.*$"), "oct_term"),
    (re.compile(r"^\s*SUPREME COURT OF THE UNITED STATES\s*$"), "scotus_hdr"),
    (re.compile(r"^\s*Syllabus\s*$"), "syllabus"),
    # Reporter's note (slip headnote preamble)
    (re.compile(r"^\s*NOTE: Where it is feasible.*$"), "reporter_note"),
    (re.compile(r"^\s*prepared by the Reporter of Decisions.*$"),
     "reporter_note"),
    (re.compile(r"^\s*See United States v\. Detroit Timber.*$"),
     "reporter_note"),
    # standalone side headers of slip pages
    (re.compile(r"^\s*(Opinion of the Court|Opinion of the Court in Part)"
                r"\s*$"), "side_hdr"),
    (re.compile(r"^\s*(Opinion|Dissent|Concurrence|Statement|Per Curiam)"
                r"\s+of\s+[A-Z][A-Za-z.]+.*$"), "side_hdr"),
    (re.compile(r"^\s*in Part\s*$"), "side_hdr"),
]
PAGE_NUM_LINE = re.compile(r"^\s*\d{1,4}\s*$")
HARVARD_PAGE_MARKER = re.compile(r"\*+\d{3,4}\*+")
FOOTNOTE_LINE = re.compile(r"^\d{1,2}\s{1,4}\S")
# opinion starts where a justice signs in (or per curiam). Everything
# before the first signature in a slip document is syllabus/headnote
# matter (Reporter's convenience), not the opinion itself.
SIGNATURE_ANCHOR = re.compile(
    r"(?m)^(?:CHIEF JUSTICE|JUSTICE|Justice)\s+[A-Z][A-Za-z.,'\- ]+?"
    r"\s+(?:delivered the opinion of the Court|delivered a|concurring|"
    r"dissenting|with whom|filed a|announcing the judgment of the Court)"
    r"|^Per Curiam$|^Per Curiam\.")


def clean_text(raw):
    """Return (text, stats). Deterministic, outcome-blind."""
    st = Counter()
    t = unicodedata.normalize("NFC", raw)
    st["harvard_page_markers"] += len(HARVARD_PAGE_MARKER.findall(t))
    t = HARVARD_PAGE_MARKER.sub(" ", t)

    lines = t.split("\n")
    out = []
    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            out.append("")
            continue
        if PAGE_NUM_LINE.match(stripped):
            st["page_number_lines"] += 1
            continue          # drop the line entirely
        hit = False
        for pat, tag in FURNITURE_PATTERNS:
            if pat.match(stripped):
                st[tag] += 1
                hit = True
                break
        if hit:
            continue
        out.append(stripped)

    # collapse blank runs, trim
    t = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()

    # paragraph unwrap: hard-wrapped slip/harvard text → continuous prose.
    # a paragraph = block of non-blank lines; lines are joined with a space.
    paras = [re.sub(r"\s+", " ", p).strip()
             for p in t.split("\n\n")]
    paras = [p for p in paras if p]
    t = "\n\n".join(paras)

    # uniform syllabus trim: cut headnote matter before the first
    # signature anchor (no-op when the text already starts signed)
    m = SIGNATURE_ANCHOR.search(t)
    if m and m.start() > 0:
        cut = t[m.start():].strip()
        if len(cut) >= 0.5 * len(t):      # garde-fou : la coupe doit garder
            st["syllabus_trim"] += 1      # l'essentiel du document
            st["syllabus_chars"] += m.start()
            t = cut
            paras = [p for p in t.split("\n\n") if p]

    # footnote estimate: numbered lines kept as-is (roadmap: conservées)
    st["footnote_markers_est"] = sum(1 for p in paras
                                     if FOOTNOTE_LINE.match(p))
    return t, st


def norm_for_cmp(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


# -------------------------------------------------------------------- main --

class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="analyse sans écrire les sorties")
    args = ap.parse_args()

    rows = []
    with gzip.open(V2, "rt", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    print(f"[in] {len(rows)} records (v2)")

    # ---- 1. normalisation ------------------------------------------------
    for r in rows:
        text, stats = clean_text(r["plain_text"])
        r["clean_text"] = text
        r["clean_stats"] = stats
        r["n_chars_clean"] = len(text)
        if len(text) >= 2000:
            r["tier"] = "full"
        elif len(text) >= 500:
            r["tier"] = "thin"
        else:
            r["tier"] = "snippet"
        r["cmp"] = norm_for_cmp(text)
        r["sha_cmp"] = hashlib.sha1(r["cmp"].encode()).hexdigest()

    agg = Counter()
    for r in rows:
        agg.update(r["clean_stats"])
    print("[norm] furniture removed:", dict(agg))
    print("[norm] chars: %d → %d (-%.1f%%)"
          % (sum(len(r['plain_text']) for r in rows),
             sum(r['n_chars_clean'] for r in rows),
             100 * (1 - sum(r['n_chars_clean'] for r in rows)
                    / max(1, sum(len(r['plain_text']) for r in rows)))))
    print("[norm] tiers:", dict(Counter(r["tier"] for r in rows)))

    # ---- 2. déduplication ------------------------------------------------
    uf = UF()
    by_hash = defaultdict(list)
    for r in rows:
        by_hash[r["sha_cmp"]].append(r["opinion_id"])
    exact_groups = 0
    for h, ids in by_hash.items():
        if len(ids) > 1:
            exact_groups += 1
            for i in ids[1:]:
                uf.union(ids[0], i)
    print(f"[dedup] exact groups: {exact_groups} "
          f"({sum(len(v) for v in by_hash.values() if len(v) > 1)} records)")

    # near-dup: same case, comparable length, difflib ≥ 0.95 (sur 6 000 c.)
    by_case = defaultdict(list)
    for r in rows:
        by_case[r["case_name"]].append(r)
    near_pairs = []
    for cn, rs in by_case.items():
        rs = sorted(rs, key=lambda r: r["opinion_id"])
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                a, b = rs[i], rs[j]
                if a["sha_cmp"] == b["sha_cmp"]:
                    continue                      # déjà fusionné (exact)
                la, lb = len(a["cmp"]), len(b["cmp"])
                if la == 0 or lb == 0:
                    continue
                if min(la, lb) / max(la, lb) < 0.85:
                    continue
                ratio = difflib.SequenceMatcher(
                    None, a["cmp"][:6000], b["cmp"][:6000]).ratio()
                if ratio >= 0.95:
                    near_pairs.append((a["opinion_id"], b["opinion_id"],
                                       round(ratio, 4)))
                    uf.union(a["opinion_id"], b["opinion_id"])
    print(f"[dedup] near-dup pairs merged: {len(near_pairs)}")

    groups = defaultdict(list)
    for r in rows:
        groups[uf.find(r["opinion_id"])].append(r)

    # ---- 3. exemplaire le plus propre ------------------------------------
    def exemplar_rank(r):
        return (SOURCE_RANK.get(r["source"], 9),
                -r["n_chars_clean"],
                r["opinion_id"])

    kept, mapping, group_info = [], {}, []
    for root, members in sorted(groups.items()):
        members = sorted(members, key=exemplar_rank)
        keep = members[0]
        dropped = members[1:]
        for m in members:
            mapping[str(m["opinion_id"])] = keep["opinion_id"]
        group_info.append({
            "kept": keep["opinion_id"],
            "kept_source": keep["source"],
            "dropped": [m["opinion_id"] for m in dropped],
            "dropped_types": sorted({m["type"] for m in dropped}),
            "case_name": keep["case_name"],
            "n_chars_clean": keep["n_chars_clean"],
        })
        kept.append(keep)
    kept.sort(key=lambda r: r["opinion_id"])
    n_dropped = len(rows) - len(kept)
    print(f"[dedup] {len(rows)} → {len(kept)} distinct texts "
          f"({n_dropped} dropped as duplicates, "
          f"{len(group_info)} groups)")

    # ---- 4. écriture ------------------------------------------------------
    os.makedirs(OUT_DIR, exist_ok=True)
    kept_alias = defaultdict(list)
    for gid, kid in mapping.items():
        if int(gid) != kid:
            kept_alias[kid].append(int(gid))

    out_path = os.path.join(OUT_DIR, "opinion_texts_v3.jsonl.gz")
    if not args.dry_run:
        with gzip.open(out_path, "wt", encoding="utf-8") as f:
            for r in kept:
                rec = {
                    "opinion_id": r["opinion_id"],
                    "alias_ids": sorted(kept_alias.get(r["opinion_id"], [])),
                    "plain_text": r["clean_text"],
                    "n_chars_raw": len(r["plain_text"]),
                    "n_chars": r["n_chars_clean"],
                    "tier": r["tier"],
                    "source": r["source"],
                    "type": r["type"],
                    "term": r["term"],
                    "cluster_id": r["cluster_id"],
                    "case_name": r["case_name"],
                    "date_filed": r.get("date_filed"),
                    "author_id": r.get("author_id"),
                    "per_curiam": r.get("per_curiam"),
                    "footnote_markers_est":
                        r["clean_stats"].get("footnote_markers_est", 0),
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        map_path = os.path.join(OUT_DIR, "dedup_map.json")
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump({"opinion_id_to_kept": mapping,
                       "n_input": len(rows), "n_kept": len(kept),
                       "n_dropped": n_dropped,
                       "exact_groups": exact_groups,
                       "near_pairs": [{"a": a, "b": b, "ratio": r}
                                      for a, b, r in near_pairs]},
                      f, indent=1, ensure_ascii=False)

        report = {
            "input": "data/m15_store/final/opinion_texts_v2.jsonl.gz",
            "output": "data/m15_store/clean/opinion_texts_v3.jsonl.gz",
            "n_input": len(rows), "n_kept": len(kept),
            "n_dropped": n_dropped, "n_groups": len(group_info),
            "exact_groups": exact_groups,
            "near_pairs_merged": len(near_pairs),
            "furniture_removed": dict(agg),
            "tiers": dict(Counter(r["tier"] for r in kept)),
            "tiers_input": dict(Counter(r["tier"] for r in rows)),
            "by_term_kept": dict(Counter(str(r["term"]) for r in kept)),
            "by_source_kept": dict(Counter(r["source"] for r in kept)),
            "chars_raw_total": sum(len(r["plain_text"]) for r in rows),
            "chars_clean_total": sum(r["n_chars_clean"] for r in kept),
            "biggest_groups": sorted(
                group_info, key=lambda g: -len(g["dropped"]))[:10],
            "rules": {
                "similarity_threshold": 0.95,
                "comparison": "text lowercased, non-alphanumerics stripped; "
                              "near-pass on first 6000 chars, same case, "
                              "length ratio >= 0.85",
                "exemplar": "source rank api>storage>legacy>snippet, then "
                            "longer clean text, then lower opinion_id",
            },
            "sha256_v2": hashlib.sha256(
                open(V2, "rb").read()).hexdigest(),
        }
        with open(os.path.join(OUT_DIR, "clean_report.json"), "w",
                  encoding="utf-8") as f:
            json.dump(report, f, indent=1, ensure_ascii=False)
        print(f"[out] written {out_path}")
        print(f"[out] kept by term:", report["by_term_kept"])
        print(f"[out] tiers kept:", report["tiers"])

    # ---- 5. sanity: le scellé n'est pas touché, l'inventaire non plus ------
    print(f"[sanity] inventory unchanged: {len(rows)} corpus rows intact "
          f"(v2 untouched); dedup is a provenance map, not a corpus edit")


if __name__ == "__main__":
    main()
