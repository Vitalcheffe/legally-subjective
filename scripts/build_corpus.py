#!/usr/bin/env python3
"""
Legally Subjective — M1 : construction et gel du Corpus-Monde v1.2.

Règle du corpus (documentée, déterministe, reproductible) :
  1. Candidats = affaires PLAIDÉES entre le 2015-10-01 et le 2024-06-30 selon
     SCDB 2025_01 (dateArgument) OU selon CourtListener (docket.date_argued).
  2. Affaire = groupe de grappes CourtListener partageant le même jeu de jetons
     de docket normalisé (les doublons de dockets CourtListener se recollent).
  3. Validation : au moins une grappe datée (dateFiled) dans
     [2015-10-01, 2024-07-31] — élimine les fantômes (vieux numéros de docket
     avec des dates de plaidoirie erronées).
  4. Join SCDB par jetons (règle assouplie pour les compétences d'origine).
  5. Join audio (plaidoiries + transcriptions) par jetons de docket.
  6. Inventaire d'opinions = toutes les opinions des grappes, dédupliquées par
     id (la déduplication de texte des ré-ingestions se fera au nettoyage M1.5).

Sorties (data/processed/) : corpus_cases_v1.jsonl.gz, corpus_opinions_v1.jsonl.gz,
corpus_justices_v1.jsonl.gz, stats_v1.json.
"""
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import random

ROOT = "/home/z/my-project/legally-subjective"
RAW = os.path.join(ROOT, "data", "raw")
PROC = os.path.join(ROOT, "data", "processed")
SCDB = os.path.join(RAW, "scdb", "SCDB_2025_01_justiceCentered_Citation.csv")

WIN_START, WIN_END = "2015-10-01", "2024-06-30"
FILED_START, FILED_END = "2015-10-01", "2024-07-31"
JUSTICES = {
    "JGRoberts": "John G. Roberts, Jr.", "CThomas": "Clarence Thomas",
    "AAlito": "Samuel A. Alito, Jr.", "SSotomayor": "Sonia Sotomayor",
    "EKagan": "Elena Kagan", "NGorsuch": "Neil M. Gorsuch",
    "BMKavanaugh": "Brett M. Kavanaugh", "ACBarrett": "Amy Coney Barrett",
    "KJackson": "Ketanji Brown Jackson", "ABreyer": "Stephen G. Breyer",
    "AScalia": "Antonin Scalia", "AMKennedy": "Anthony M. Kennedy",
    "RBGinsburg": "Ruth Bader Ginsburg",
}
OPINION_TYPES = {
    "010combined": "combined", "020lead": "lead", "030concurrence": "concurrence",
    "040dissent": "dissent", "050concurrence-dissent": "concurrence-dissent",
    "060addendum": "addendum", "070rehearing": "rehearing",
    "080onthemotiontofilereview": "on-motion", "090statement": "statement",
    "combined-opinion": "combined", "lead-opinion": "lead",
    "concurrence-opinion": "concurrence", "dissent-opinion": "dissent",
}

os.makedirs(PROC, exist_ok=True)


def log(m):
    print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)


def norm_tokens(d):
    if not d:
        return frozenset()
    d = re.sub(r"^no\.?\s+", "", d.strip().rstrip("."), flags=re.I)
    d = re.sub(r"orig\.?$", "original", d, flags=re.I)
    d = re.sub(r"(\d+)O(\d+)", r"\1 \2 original", d)
    return frozenset(t.upper().replace("ORIG", "ORIGINAL")
                     for t in re.split(r"[^0-9A-Za-z]+", d) if t)


def orig_aware_match(t_a, t_b):
    """Vrai si les jeux de jetons correspondent (règle assouplie pour les
    compétences d'origine : au moins un numéro d'origine partagé)."""
    if not t_a or not t_b:
        return False
    if t_a == t_b or t_a.issubset(t_b) or t_b.issubset(t_a):
        return True
    if "ORIGINAL" in t_a and "ORIGINAL" in t_b:
        na = {t for t in t_a if t != "ORIGINAL"}
        nb = {t for t in t_b if t != "ORIGINAL"}
        return bool(na & nb)
    return False


def scdb_date(s):
    if not s:
        return None
    try:
        m, d, y = s.split("/")
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except ValueError:
        return None


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    # ---------- 1. SCDB ----------
    scdb_cases, scdb_justices = {}, {}
    with open(SCDB, encoding="latin-1") as f:
        for row in csv.DictReader(f):
            if not row.get("dateArgument"):
                continue
            da = scdb_date(row["dateArgument"])
            if not (WIN_START <= da <= WIN_END):
                continue
            cid = row["caseId"]
            if cid not in scdb_cases:
                scdb_cases[cid] = {
                    "scdb_case_id": cid, "scdb_docket": row.get("docket", ""),
                    "scdb_case_name": row.get("caseName", "").title(),
                    "term": row.get("term", ""), "date_argument": da,
                    "date_decision": scdb_date(row.get("dateDecision")),
                    "decision_type": row.get("decisionType", ""),
                    "maj_votes": int(row["majVotes"]) if row.get("majVotes", "").isdigit() else None,
                    "min_votes": int(row["minVotes"]) if row.get("minVotes", "").isdigit() else None,
                    "decision_direction": row.get("decisionDirection", ""),
                    "maj_opin_writer": row.get("majOpinWriter", ""),
                    "maj_opin_assigner": row.get("majOpinAssigner", ""),
                    "us_cite": row.get("usCite", ""), "issue_area": row.get("issueArea", ""),
                    "party_winning": row.get("partyWinning", ""),
                    "lc_disposition": row.get("lcDisposition", ""),
                    "case_disposition": row.get("caseDisposition", ""),
                }
            scdb_justices.setdefault(cid, []).append({
                "scdb_case_id": cid, "justice": row.get("justiceName", ""),
                "justice_name": JUSTICES.get(row.get("justiceName", ""), row.get("justiceName", "")),
                "vote": row.get("vote", ""), "opinion": row.get("opinion", ""),
                "direction": row.get("direction", ""), "majority": row.get("majority", ""),
            })
    log(f"SCDB : {len(scdb_cases):,} affaires plaidées dans la fenêtre")

    # index SCDB par jetons
    scdb_by_tokens = []
    for cid, c in scdb_cases.items():
        for d in re.split(r"[;,]", c["scdb_docket"]):
            tk = norm_tokens(d)
            if tk:
                scdb_by_tokens.append((tk, cid))

    # ---------- 2. dockets CL (dates plaidées + carte audio) ----------
    cl_argued = {}   # tokens -> date plaidée CL
    audio_by_tokens = {}  # tokens -> liste audio
    with gzip.open(os.path.join(RAW, "scotus_dockets.jsonl.gz"), "rt") as f:
        for line in f:
            r = json.loads(line)
            tk = norm_tokens(r.get("docket_number"))
            if not tk:
                continue
            da = r.get("date_argued")
            if da and WIN_START <= da <= WIN_END and tk not in cl_argued:
                cl_argued[tk] = (da, r.get("case_name", ""))
    for r in (json.loads(l) for l in gzip.open(os.path.join(RAW, "scotus_oral_arguments.jsonl.gz"), "rt")):
        tk = norm_tokens(r.get("case_name") and r.get("docket_id") and "")  # placeholder
    # audio : jointure par docket_id -> tokens du docket correspondant
    docket_id_tokens = {}
    with gzip.open(os.path.join(RAW, "scotus_dockets.jsonl.gz"), "rt") as f:
        for line in f:
            r = json.loads(line)
            tk = norm_tokens(r.get("docket_number"))
            if tk:
                docket_id_tokens[r["id"]] = tk
    for r in (json.loads(l) for l in gzip.open(os.path.join(RAW, "scotus_oral_arguments.jsonl.gz"), "rt")):
        tk = docket_id_tokens.get(r.get("docket_id", ""))
        if tk:
            audio_by_tokens.setdefault(tk, []).append(
                {"id": r["id"], "duration": r.get("duration"),
                 "has_transcript": bool(r.get("stt_transcript")),
                 "stt_source": r.get("stt_source")})
    log(f"dockets CL plaidés fenêtre : {len(cl_argued):,} ; "
        f"jetons audio : {len(audio_by_tokens):,}")

    # ---------- 3. grappes de recherche groupées par jetons ----------
    groups = {}  # tokens -> {"clusters": [...], "query_dockets": set, "argued_cl": ...}
    with gzip.open(os.path.join(RAW, "corpus_search_results.jsonl.gz"), "rt") as f:
        for line in f:
            r = json.loads(line)
            c = r["cluster"]
            tk = norm_tokens(c.get("docketNumber", ""))
            if not tk:
                continue
            g = groups.setdefault(tk, {"clusters": [], "query_dockets": set(),
                                       "argued_cl": None})
            if not any(x.get("cluster_id") == c.get("cluster_id") for x in g["clusters"]):
                g["clusters"].append(c)
            g["query_dockets"].add(r.get("query_docket", ""))
            da = r.get("date_argued")
            if da and WIN_START <= da <= WIN_END:
                g["argued_cl"] = da
    log(f" groupes de grappes (par jetons) : {len(groups):,}")

    # ---------- 4. assemblage (SCDB d'abord, puis groupes CL purs) ----------
    out_cases, out_opinions = [], []
    ghosts, no_scdb = [], []
    claimed = set()

    def emit_case(tk_list, g, scdb, votes):
        """Émet une affaire fusionnée à partir d'un groupe (ou plusieurs)."""
        clusters = []
        seen_cid = set()
        for gg in g:
            for c in gg["clusters"]:
                if c.get("cluster_id") not in seen_cid:
                    seen_cid.add(c.get("cluster_id"))
                    clusters.append(c)
        tk = frozenset().union(*tk_list)
        recent = [c for c in clusters if FILED_START <= (c.get("dateFiled") or "") <= FILED_END]
        if not recent:
            return None
        canon = max(recent, key=lambda c: (len(c.get("opinions", [])),
                                           c.get("citeCount") or 0))
        seen_id, ops = set(), []
        for c in clusters:
            for o in c.get("opinions", []):
                if o.get("id") in seen_id:
                    continue
                seen_id.add(o.get("id"))
                ops.append({
                    "opinion_id": o.get("id"),
                    "type": OPINION_TYPES.get(o.get("type"), o.get("type")),
                    "cluster_id": c.get("cluster_id"),
                    "author_id": o.get("author_id"), "per_curiam": o.get("per_curiam"),
                    "sha1": o.get("sha1"), "download_url": o.get("download_url"),
                    "joined_by_ids": o.get("joined_by_ids", []),
                })
        term = scdb["term"] if scdb else None
        if not term:
            df = canon.get("dateFiled") or ""
            if df[:4].isdigit():
                y = int(df[:4])
                term = str(y - 1) if df[5:7].isdigit() and int(df[5:7]) <= 6 else str(y)
        auds = []
        for atk, av in audio_by_tokens.items():
            if atk == tk or atk.issubset(tk) or tk.issubset(atk):
                auds.extend(av)
        name = canon.get("caseName") or (scdb["scdb_case_name"] if scdb else "") or ""
        rec = {
            "docket_tokens": sorted(tk),
            "docket_number": canon.get("docketNumber", ""),
            "case_name": name,
            "date_argued": (scdb["date_argument"] if scdb else None) or
                           (g[0]["argued_cl"] if g and g[0].get("argued_cl") else None),
            "date_argued_source": "scdb" if scdb else "courtlistener",
            "date_filed": canon.get("dateFiled"),
            "term": term,
            "cluster_ids": sorted({c.get("cluster_id") for c in clusters}),
            "canonical_cluster_id": canon.get("cluster_id"),
            "judges": canon.get("judge", ""),
            "syllabus_len": len(canon.get("syllabus") or ""),
            "cite_count": canon.get("citeCount"),
            "n_opinions": len(ops),
            "n_clusters": len(clusters),
            "scdb": scdb,
            "justices": votes,
            "audio": auds,
            "absolute_url": canon.get("absolute_url", ""),
        }
        for o in ops:
            out_opinions.append({**o, "case_name": name, "term": term,
                                 "date_filed": canon.get("dateFiled")})
        return rec

    # 4a. affaires SCDB (primaires)
    for cid, sc in sorted(scdb_cases.items(), key=lambda kv: (kv[1]["date_argument"], kv[0])):
        stks = [norm_tokens(d) for d in re.split(r"[;,]", sc["scdb_docket"]) if norm_tokens(d)]
        matched_groups = []
        for stk in stks:
            for gtk, g in groups.items():
                if gtk in claimed:
                    continue
                if orig_aware_match(stk, gtk):
                    matched_groups.append(g)
                    claimed.add(gtk)
        all_tks = list(stks) + [gtk for gtk in claimed if gtk in groups]
        rec = emit_case(all_tks, matched_groups, sc, scdb_justices.get(cid, []))
        if rec:
            out_cases.append(rec)

    # 4b. groupes CL plaidés non réclamés par SCDB
    for gtk, g in sorted(groups.items(), key=lambda kv: (kv[1]["argued_cl"] or "9999", sorted(kv[0]))):
        if gtk in claimed or not g["argued_cl"]:
            continue
        rec = emit_case([frozenset(gtk)], [g], None, [])
        if rec:
            out_cases.append(rec)
        elif not any(FILED_START <= (c.get("dateFiled") or "") <= FILED_END for c in g["clusters"]):
            ghosts.append(sorted(gtk))
    out_cases.sort(key=lambda r: (r.get("date_argued") or "", r["case_name"]))
    with gzip.open(os.path.join(PROC, "corpus_cases_v1.jsonl.gz"), "wt", encoding="utf-8") as f:
        for r in out_cases:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with gzip.open(os.path.join(PROC, "corpus_opinions_v1.jsonl.gz"), "wt", encoding="utf-8") as f:
        for r in out_opinions:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with gzip.open(os.path.join(PROC, "corpus_justices_v1.jsonl.gz"), "wt", encoding="utf-8") as f:
        for r in out_cases:
            for j in r["justices"]:
                f.write(json.dumps({**j, "case_name": r["case_name"],
                                    "date_argued": r["date_argued"]}, ensure_ascii=False) + "\n")

    # ---------- 5. stats + scellement 5-4 ----------
    n = len(out_cases)
    with_scdb = sum(1 for r in out_cases if r["scdb"])
    no_scdb_list = [r["docket_number"] or str(r["docket_tokens"]) for r in out_cases if not r["scdb"]]
    five_four = [r for r in out_cases if r["scdb"] and r["scdb"]["maj_votes"] == 5
                 and r["scdb"]["min_votes"] == 4]
    audio_cov = sum(1 for r in out_cases if r["audio"])
    tr_cov = sum(1 for r in out_cases if any(a["has_transcript"] for a in r["audio"]))
    by_term = {}
    for r in out_cases:
        t = r.get("term") or "?"
        by_term.setdefault(t, {"cases": 0, "with_scdb": 0, "five_four": 0, "opinions": 0})
        by_term[t]["cases"] += 1
        by_term[t]["opinions"] += r["n_opinions"]
        if r["scdb"]:
            by_term[t]["with_scdb"] += 1
            if r["scdb"]["maj_votes"] == 5 and r["scdb"]["min_votes"] == 4:
                by_term[t]["five_four"] += 1

    ff_sorted = sorted(five_four, key=lambda r: (r["date_argued"], r["case_name"]))
    seed_material = json.dumps([r["docket_number"] or str(r["docket_tokens"])
                                for r in ff_sorted], sort_keys=True)
    seed = int(hashlib.sha256(seed_material.encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    selected = rng.sample(ff_sorted, min(50, len(ff_sorted)))
    selected_keys = sorted(r["docket_number"] or str(r["docket_tokens"]) for r in selected)
    scdb_covered = {c["scdb_case_id"] for c in scdb_cases.values()}
    corpus_scdb_ids = {r["scdb"]["scdb_case_id"] for r in out_cases if r["scdb"]}
    scdb_not_in_corpus = sorted(scdb_covered - corpus_scdb_ids)

    stats = {
        "corpus_rule": {
            "court": "Supreme Court of the United States",
            "argued_window": [WIN_START, WIN_END],
            "filed_validation": [FILED_START, FILED_END],
            "terms": "OT2015..OT2023",
            "case_definition": "affaires plaidées (SCDB dateArgument OU CourtListener "
                               "date_argued) avec >= 1 grappe d'opinion dans la fenêtre",
            "grouping": "jetons de docket normalisés (déduplication des dockets dupliqués)",
            "opinions": "inventaire par id ; déduplication de texte différée au nettoyage M1.5",
            "scdb_join": "jetons de docket ; compétence d'origine par numéro partagé",
        },
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "n_cases": n,
        "n_opinions": len(out_opinions),
        "n_with_scdb": with_scdb,
        "n_five_four": len(five_four),
        "audio_coverage": audio_cov,
        "transcript_coverage": tr_cov,
        "by_term": by_term,
        "ghost_groups_excluded": len(ghosts),
        "no_scdb_dockets": no_scdb_list,
        "scdb_cases_not_in_corpus": scdb_not_in_corpus,
        "five_four_selection": {
            "method": "échantillon aléatoire déterministe (Random MT, graine = SHA-256 "
                      "de la liste triée des identifiants 5-4)",
            "seed_hex": hex(seed),
            "n_available": len(ff_sorted),
            "n_selected": len(selected_keys),
            "cases": selected_keys,
            "sealed_sha256": hashlib.sha256(json.dumps(selected_keys).encode()).hexdigest(),
        },
        "source_sha256": {
            "dockets_bulk": json.load(open(os.path.join(RAW, "provenance",
                                                        "dockets-2026-06-30.done.json")))["sha256_compressed"],
            "clusters_bulk": json.load(open(os.path.join(RAW, "provenance",
                                                         "opinion-clusters-2026-06-30.done.json")))["sha256_compressed"],
            "oral_arguments_bulk": json.load(open(os.path.join(RAW, "provenance",
                                                               "oral-arguments-2026-06-30.done.json")))["sha256_compressed"],
            "scdb_2025_01_zip": sha256_file(os.path.join(RAW, "scdb",
                                                         "SCDB_2025_01_justiceCentered_Citation.csv.zip")),
            "search_results": sha256_file(os.path.join(RAW, "corpus_search_results.jsonl.gz")),
        },
        "notes": [
            "Le fichier bulk opinion-clusters-2026-06-30.csv.bz2 de CourtListener ne couvre pas "
            "les grappes SCOTUS postérieures à ~2015 : les métadonnées de grappes proviennent de "
            "l'API de recherche v4 (accès anonyme, extrait le 2026-08-28).",
            "Les fichiers bulk 2026-06-30 sont tronqués à la fin côté S3 (sans marqueur de fin "
            "bzip2) ; impact documenté, sans effet sur le corpus.",
            "CourtListener stocke souvent le same slip opinion en plusieurs exemplaires (sha1 "
            "différents) : la déduplication fine se fera sur le texte au M1.5.",
        ],
    }
    with open(os.path.join(PROC, "stats_v1.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    log(f"CORPUS v1.2 GELÉ : {n} affaires | {len(out_opinions)} opinions | "
        f"{with_scdb} avec SCDB | {len(five_four)} en 5-4 | audio {audio_cov} | "
        f"transcriptions {tr_cov} | fantômes écartés : {len(ghosts)}")
    for t in sorted(by_term):
        b = by_term[t]
        log(f"  OT{t}: {b['cases']} affaires | {b['opinions']} opinions | "
            f"{b['with_scdb']} SCDB | {b['five_four']} en 5-4")
    log(f"SCELLÉ 50 affaires 5-4 : {stats['five_four_selection']['sealed_sha256'][:20]}…")


if __name__ == "__main__":
    main()
