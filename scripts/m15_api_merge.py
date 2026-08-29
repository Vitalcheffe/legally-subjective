#!/usr/bin/env python3
"""M1.5 merge final — assemble le store canonique des textes d'opinions.

Sources fusionnées (ordre de priorité DESCENDANT pour la qualité du texte) :
  1. API v4 (data/m15_store/api/resp_*.json)  — canonique CourtListener
  2. store M1.5 voies B+C (data/raw/opinion_texts/opinions_text.jsonl.gz,
     522 textes bulk+slip)                     — fallback si l'API n'a rien

Sorties :
  - data/m15_store/final/opinion_texts_v2.jsonl.gz  (git-tracked, canonique)
  - data/raw/opinion_texts/opinions_text.jsonl.gz   (miroir pour le builder M3)
  - data/m15_store/final/stats.json                 (couverture par terme/type)

Schéma de sortie : opinion_id, plain_text, n_chars, source, type, term,
cluster_id, case_name, date_filed, author_type, per_curiam, joined_by_ids.
"""
import glob
import gzip
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_DIR = os.path.join(REPO, "data", "m15_store", "api")
RAW_STORE = os.path.join(REPO, "data", "raw", "opinion_texts",
                         "opinions_text.jsonl.gz")
OUT_DIR = os.path.join(REPO, "data", "m15_store", "final")
CORPUS = os.path.join(REPO, "data", "processed", "corpus_opinions_v1.jsonl.gz")

FIELD_PRIORITY = ["plain_text", "html", "xml_harvard", "html_lawbox",
                  "html_columbia", "html_anonymous_2020"]


def html_to_text(s):
    if not s:
        return ""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(s, "html.parser")
        for t in soup(["script", "style"]):
            t.decompose()
        txt = soup.get_text("\n")
    except Exception:
        import html as h
        import re
        txt = h.unescape(re.sub(r"<[^>]+>", "\n", s))
    lines = [ln.strip() for ln in txt.splitlines()]
    out, blank = [], 0
    for ln in lines:                      # normalise les lignes vides multiples
        if ln:
            out.append(ln)
            blank = 0
        else:
            blank += 1
            if blank == 1 and out:
                out.append("")
    return "\n".join(out).strip()


def api_text(rec):
    """Retourne (texte, champ_source) depuis un enregistrement API v4."""
    for f in FIELD_PRIORITY:
        v = rec.get(f)
        if v and v.strip():
            if f == "plain_text":
                return v.strip(), "api:plain_text"
            return html_to_text(v), f"api:{f}"
    return "", ""


def main():
    # 1. corpus = vérité des métadonnées
    corpus = {}
    with gzip.open(CORPUS, "rt") as f:
        for line in f:
            r = json.loads(line)
            corpus[r["opinion_id"]] = r
    print(f"corpus: {len(corpus)} opinions")

    # 2. réponses API
    api_map = {}
    files = sorted(glob.glob(os.path.join(API_DIR, "resp_*.json")))
    for fp in files:
        with open(fp) as f:
            d = json.load(f)
        for r in d.get("records", []):
            api_map[int(r["id"])] = r
    print(f"API: {len(api_map)} enregistrements dans {len(files)} fichiers")

    # 3. store existant (voies B+C)
    old_map = {}
    if os.path.exists(RAW_STORE):
        with gzip.open(RAW_STORE, "rt") as f:
            for line in f:
                r = json.loads(line)
                oid = r.get("opinion_id") or r.get("id")
                old_map[oid] = r
    print(f"store B+C: {len(old_map)} textes")

    # 4. fusion
    out_rows, stats = [], {"source": {}}
    missing, empty_api = [], []
    for oid in sorted(corpus):
        c = corpus[oid]
        row = {
            "opinion_id": oid,
            "cluster_id": c["cluster_id"],
            "type": c["type"],
            "term": c["term"],
            "case_name": c["case_name"],
            "date_filed": c["date_filed"],
            "per_curiam": c.get("per_curiam", False),
            "author_id": c.get("author_id"),
            "joined_by_ids": c.get("joined_by_ids", []),
        }
        text, src = "", ""
        rec = api_map.get(oid)
        if rec is not None:
            text, src = api_text(rec)
        if text:
            stats["source"][src] = stats["source"].get(src, 0) + 1
        else:
            if rec is not None:
                empty_api.append(oid)     # API a la ligne mais aucun champ texte
            old = old_map.get(oid)
            if old:
                t = old.get("plain_text") or old.get("text") or ""
                if t.strip():
                    text, src = t.strip(), "legacy:" + str(
                        old.get("source", old.get("origin", "bc")))
                    stats["source"][src] = stats["source"].get(src, 0) + 1
        if not text:
            missing.append(oid)
        row["plain_text"] = text
        row["n_chars"] = len(text)
        row["source"] = src
        out_rows.append(row)

    # 5. écritures
    os.makedirs(OUT_DIR, exist_ok=True)
    out_gz = os.path.join(OUT_DIR, "opinion_texts_v2.jsonl.gz")
    with gzip.open(out_gz + ".tmp", "wt") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(out_gz + ".tmp", out_gz)
    # miroir pour le builder M3 (schéma id/plain_text compris par load_texts)
    with gzip.open(RAW_STORE + ".tmp", "wt") as f:
        for r in out_rows:
            f.write(json.dumps({"id": r["opinion_id"],
                                "opinion_id": r["opinion_id"],
                                "plain_text": r["plain_text"],
                                "source": r["source"],
                                "n_chars": r["n_chars"]},
                               ensure_ascii=False) + "\n")
    os.replace(RAW_STORE + ".tmp", RAW_STORE)

    # 6. stats
    n_have = sum(1 for r in out_rows if r["n_chars"] > 0)
    by_term, by_type = {}, {}
    for r in out_rows:
        if r["n_chars"] > 0:
            by_term[r["term"]] = by_term.get(r["term"], 0) + 1
            by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    tot_term = {}
    for r in out_rows:
        tot_term[r["term"]] = tot_term.get(r["term"], 0) + 1
    stats.update({
        "corpus_total": len(corpus),
        "texts_available": n_have,
        "coverage_pct": round(100 * n_have / len(corpus), 1),
        "api_records": len(api_map),
        "api_records_with_text": len(api_map) - len(empty_api),
        "api_empty_no_fallback": len(empty_api),
        "by_term_have": by_term,
        "by_term_total": tot_term,
        "by_type_have": by_type,
        "missing_ids": missing[:50],
        "missing_count": len(missing),
        "chars_total": sum(r["n_chars"] for r in out_rows),
        "chars_median": sorted(r["n_chars"] for r in out_rows)[len(out_rows) // 2],
    })
    with open(os.path.join(OUT_DIR, "stats.json"), "w") as f:
        json.dump(stats, f, indent=1)

    print(f"\n=== RÉSULTAT: {n_have}/{len(corpus)} "
          f"({100 * n_have / len(corpus):.1f}%) ===")
    print("par terme (couverts/total):")
    for t in sorted(tot_term):
        print(f"  {t}: {by_term.get(t, 0)}/{tot_term[t]}")
    print("par source:", json.dumps(stats["source"], indent=1))
    if missing:
        print(f"manquants: {len(missing)} (premiers: {missing[:10]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
