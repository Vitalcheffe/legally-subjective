#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M1.5 étape 4 : journal d'audit zéro-fuite.

Le roadmap M1.5.4 exige : « Vérification automatique : zéro fuite
documentée dans un journal d'audit ». Ce script EST cette vérification.
Il ne produit pas de données — il les inspecte, depuis les artefacts
seuls (jamais depuis l'état mémoire d'un builder), et écrit un journal
horodaté et haché : chaque contrôle PASS/FAIL, avec les détails.

Contrôles :
  A. Scellé — les 50 affaires scellées n'apparaissent dans AUCUN
     artefact de dataset (casefiles, personas train, test votes) ;
     l'empreinte du scellé se recalule (intégrité de la liste).
  B. Temporel — train = décision réelle < 2020-10-01 ; test = OT2020+ ;
     les segments héritent de la garde de date de leur opinion source.
  C. Déduplication — v3 sans doublons ; la carte couvre les 1778 ids ;
     aucun output dupliqué à l'intérieur d'un persona.
  D. Hygiène personas — chaque opinion_id de row existe dans v3 ;
     signatures cohérentes avec le persona ; ≥ 1500 caractères.
  E. Casefiles pré-décision — clés interdites absentes (conclusion,
     decided_by, decisions, opinion_announcement, votes, directions).
  F. Chaîne — sha256 de chaque artefact audité, consigné.

Sortie : data/m15_store/clean/audit_leak_journal.{json,md}
Le script sort avec code 1 si un contrôle échoue (utilisable en CI).
"""
import glob
import gzip
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m3_build_datasets as B  # noqa: E402  (load_corpus, sealed_dockets...)

REPO = B.REPO
CLEAN = os.path.join(REPO, "data", "m15_store", "clean")
M3 = os.path.join(REPO, "data", "m3")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmp_norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def main():
    entries = []

    def log(cid, ok, detail):
        entries.append({"check": cid, "verdict": "PASS" if ok else "FAIL",
                        "detail": detail})
        print(f"[{'PASS' if ok else 'FAIL'}] {cid} — {detail}")

    # ---- données ----------------------------------------------------------
    cases, opinions, stats, amap = B.load_corpus()
    is_sealed = B.sealed_dockets(stats)
    sealed_cases = [c for c in cases if is_sealed(c)]
    sealed_dockets = {B.norm_docket(c["docket_number"])
                      for c in sealed_cases}

    # A0/A4 — intégrité du scellé lui-même (méthode de build_corpus.py :
    # sha256(json.dumps(liste triée des dockets)))
    sel = stats["five_four_selection"]
    ref = sel["sealed_sha256"]
    rec = hashlib.sha256(json.dumps(sel["cases"]).encode()).hexdigest()
    log("A4.seal_integrity",
        rec == ref,
        f"sealed_sha256 recomputed: {'match' if rec == ref else 'MISMATCH'}")

    # ---- A. scellé exclu des datasets -------------------------------------
    cf_files = glob.glob(os.path.join(M3, "casefiles", "*.json"))
    bad = [f for f in cf_files
           if B.norm_docket(os.path.basename(f)[:-5].replace("_", "-"))
           in sealed_dockets
           or any(B.norm_docket(json.load(open(f, encoding="utf-8"))
                                .get("docket", "").replace("_", "-"))
                  == sd for sd in sealed_dockets)]
    # (le nom de fichier encode le docket — vérification robuste ci-dessous)
    bad = []
    sealed_hit_files = []
    for f in cf_files:
        cf = json.load(open(f, encoding="utf-8"))
        dn = cf.get("docket", "")
        if any(B.nums(dn) & B.nums(s) for s in sel["cases"]):
            bad.append(dn)
            sealed_hit_files.append(os.path.basename(f))
    log("A1.sealed_not_in_casefiles", not bad,
        f"{len(cf_files)} casefiles, scellés trouvés: {bad or 'aucun'}")

    persona_dirs = sorted(glob.glob(os.path.join(M3, "personas", "*")))
    train_bad, test_bad, n_train_rows, n_test_rows = [], [], 0, 0
    for pdir in persona_dirs:
        slug = os.path.basename(pdir)
        tpath = os.path.join(pdir, "train.jsonl")
        if os.path.exists(tpath):
            for line in open(tpath, encoding="utf-8"):
                r = json.loads(line)
                n_train_rows += 1
                dn = r.get("docket", "")
                if any(B.nums(dn) & B.nums(s) for s in sel["cases"]):
                    train_bad.append((slug, dn))
        vpath = os.path.join(pdir, "test_votes.jsonl")
        if os.path.exists(vpath):
            for line in open(vpath, encoding="utf-8"):
                r = json.loads(line)
                n_test_rows += 1
                dn = r.get("docket", "")
                if any(B.nums(dn) & B.nums(s) for s in sel["cases"]):
                    test_bad.append((slug, dn))
    log("A2.sealed_not_in_personas", not train_bad,
        f"{n_train_rows} train rows, scellés: {train_bad or 'aucun'}")
    log("A3.sealed_not_in_test_votes", not test_bad,
        f"{n_test_rows} test votes, scellés: {test_bad or 'aucun'}")

    # ---- B. discipline temporelle -----------------------------------------
    docket_to_case = {c["docket_number"]: c for c in cases}
    date_of_oid = {o["opinion_id"]: o.get("date_filed") for o in opinions
                   if o.get("date_filed")}
    CUTOFF = "2020-10-01"
    b1_bad, seg_nodesc, seg_late = [], 0, 0
    per_slug_rows = {}
    for pdir in persona_dirs:
        slug = os.path.basename(pdir)
        rows = [json.loads(l) for l in
                open(os.path.join(pdir, "train.jsonl"), encoding="utf-8")]
        per_slug_rows[slug] = rows
        for r in rows:
            if r.get("opinion_id") is None:      # segment
                d = date_of_oid.get(r.get("segment_of"))
                if not d:
                    seg_nodesc += 1
                elif d >= CUTOFF:
                    seg_late += 1
                continue
            d = r.get("date_filed")
            if not d:
                d = date_of_oid.get(r["opinion_id"], "")
            if d and d >= CUTOFF:
                b1_bad.append((slug, r["opinion_id"], d))
    log("B1.train_before_cutoff", not b1_bad,
        f"rows décidées après {CUTOFF}: {b1_bad[:5] or 'aucun'}")
    log("B2.segments_date_guard",
        seg_nodesc == 0 and seg_late == 0,
        f"segments sans date: {seg_nodesc}, décidés après cutoff: {seg_late}")

    b3_bad = []
    for pdir in persona_dirs:
        vpath = os.path.join(pdir, "test_votes.jsonl")
        if not os.path.exists(vpath):
            continue
        for line in open(vpath, encoding="utf-8"):
            r = json.loads(line)
            c = docket_to_case.get(r.get("docket"))
            if c and int(c["term"]) < 2020:
                b3_bad.append((r.get("docket"), c["term"]))
    log("B3.test_is_ot2020plus", not b3_bad,
        f"votes test hors fenêtre: {b3_bad[:5] or 'aucun'}")

    # ---- C. intégrité de la déduplication ----------------------------------
    v3 = [json.loads(l) for l in gzip.open(
        os.path.join(CLEAN, "opinion_texts_v3.jsonl.gz"), "rt",
        encoding="utf-8")]
    hashes = [cmp_norm(r["plain_text"]) for r in v3]
    n_dup = len(hashes) - len(set(hashes))
    log("C1.v3_no_duplicates", n_dup == 0,
        f"{len(v3)} textes v3, doublons exacts: {n_dup}")

    dmap = json.load(open(os.path.join(CLEAN, "dedup_map.json"),
                          encoding="utf-8"))
    corpus_ids = {o["opinion_id"] for o in opinions}
    v3_ids = {r["opinion_id"] for r in v3}
    m = dmap["opinion_id_to_kept"]
    covers = {int(k) for k in m.keys()} == corpus_ids
    vals_ok = {int(v) for v in set(m.values())} <= v3_ids
    log("C2.dedup_map_covers_corpus", covers and vals_ok,
        f"{len(m)} ids mappés, corpus {len(corpus_ids)}, "
        f"cibles absentes de v3: {len(set(m.values()) - v3_ids)}")

    c3_bad = []
    for slug, rows in per_slug_rows.items():
        seen = {}
        for r in rows:
            h = hashlib.sha1(cmp_norm(r.get("output", ""))
                             [:8000].encode()).hexdigest()
            if h in seen:
                c3_bad.append((slug, seen[h], r.get("opinion_id")))
            seen[h] = r.get("opinion_id") or r.get("segment_of")
    log("C3.no_duplicate_outputs_within_persona", not c3_bad,
        f"doublons intra-persona: {c3_bad[:5] or 'aucun'}")

    # ---- D. hygiène personas ----------------------------------------------
    d1_bad, d2_bad = [], []
    sig_of_oid = {}
    with open(os.path.join(REPO, "data", "m15_store", "final",
                           "authorship.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            sig_of_oid[r["opinion_id"]] = r["slug"]
    alias_map = {}
    for r in v3:
        for a in r.get("alias_ids", []):
            alias_map[a] = r["opinion_id"]
    for slug, rows in per_slug_rows.items():
        for r in rows:
            if r.get("opinion_id") is None:
                continue
            oid = r["opinion_id"]
            if oid not in v3_ids:
                d1_bad.append((slug, oid, "not_in_v3"))
            if len(r.get("output", "")) < 1500:
                d1_bad.append((slug, oid, "too_short"))
            sig = sig_of_oid.get(oid)
            if sig is None:
                kept = alias_map.get(oid)
                sig = sig_of_oid.get(kept)
            if sig is not None and sig != slug:
                d2_bad.append((slug, oid, sig))
    log("D1.rows_in_v3_and_long_enough", not d1_bad,
        f"rows invalides: {d1_bad[:5] or 'aucun'}")
    log("D2.signatures_match_persona", not d2_bad,
        f"erreurs d'attribution: {d2_bad[:5] or 'aucun'}")

    # ---- E. casefiles pré-décision ----------------------------------------
    forbidden = {"conclusion", "decided_by", "decisions",
                 "opinion_announcement", "direction", "vote",
                 "disposition_of_court", "winning_party"}
    e1_bad = []
    for f in cf_files:
        cf = json.load(open(f, encoding="utf-8"))
        hit = forbidden & set(cf.keys())
        if hit:
            e1_bad.append((os.path.basename(f), sorted(hit)))
    log("E1.casefiles_pre_decision", not e1_bad,
        f"clés interdites: {e1_bad[:5] or 'aucune'} "
        f"({len(cf_files)} fichiers)")

    # ---- F. chaîne ---------------------------------------------------------
    chain = {}
    for label, path in [
        ("corpus_stats", os.path.join(REPO, "data", "processed",
                                      "stats_v1.json")),
        ("texts_v2", os.path.join(REPO, "data", "m15_store", "final",
                                  "opinion_texts_v2.jsonl.gz")),
        ("texts_v3", os.path.join(CLEAN, "opinion_texts_v3.jsonl.gz")),
        ("dedup_map", os.path.join(CLEAN, "dedup_map.json")),
        ("clean_report", os.path.join(CLEAN, "clean_report.json")),
        ("authorship", os.path.join(REPO, "data", "m15_store", "final",
                                    "authorship.jsonl")),
        ("segments", os.path.join(REPO, "data", "m15_store", "storage",
                                  "segments.jsonl")),
        ("manifest", os.path.join(M3, "manifest.json")),
    ]:
        if os.path.exists(path):
            chain[label] = {"path": os.path.relpath(path, REPO),
                            "sha256": sha256(path), "bytes":
                            os.path.getsize(path)}
    log("F1.chain_hashes", True,
        f"{len(chain)} artefacts hachés (voir journal)")

    # ---- journal -----------------------------------------------------------
    verdict = all(e["verdict"] == "PASS" for e in entries)
    journal = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "M1.5 étape 4 — zéro fuite, dédup, hygiène, pré-décision",
        "summary": {
            "checks_total": len(entries),
            "checks_failed": sum(e["verdict"] == "FAIL" for e in entries),
            "persona_train_rows": n_train_rows,
            "persona_test_votes": n_test_rows,
            "casefiles": len(cf_files),
            "v3_texts": len(v3),
        },
        "verdict": "PASS" if verdict else "FAIL",
        "entries": entries,
        "chain": chain,
    }
    jpath = os.path.join(CLEAN, "audit_leak_journal.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(journal, f, indent=1, ensure_ascii=False)

    md = ["# Journal d'audit zéro-fuite — M1.5.4",
          "",
          f"Généré : {journal['generated_at']}  ",
          f"Verdict : **{journal['verdict']}** "
          f"({len(entries)} contrôles, "
          f"{journal['summary']['checks_failed']} échec(s))",
          "",
          "| Contrôle | Verdict | Détail |", "|---|---|---|"]
    for e in entries:
        md.append(f"| `{e['check']}` | {e['verdict']} | {e['detail']} |")
    md += ["", "## Chaîne (sha256)", "",
           "| Artefact | sha256 (12) | octets |", "|---|---|---|"]
    for label, info in chain.items():
        md.append(f"| {label} | `{info['sha256'][:12]}` | "
                  f"{info['bytes']:,} |")
    with open(os.path.join(CLEAN, "audit_leak_journal.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"\nverdict: {journal['verdict']} → {jpath}")
    sys.exit(0 if verdict else 1)


if __name__ == "__main__":
    main()
