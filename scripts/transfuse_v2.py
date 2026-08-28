#!/usr/bin/env python3
"""
Legally Subjective — transfusion du site vers le Corpus-Monde v1.

Le front restauré (THE DRAW, /court, /judge, /compare, /cases, /case, /paper)
lit des fichiers de données précis. Ce script RÉGÉNÈRE ces fichiers à partir
du corpus gelé (data/processed/) et des baselines M2 (results/) — même
schéma, nouvelles mesures réelles. Zéro invention : chaque valeur est
calculée depuis les enregistrements SCDB 2025_01 fusionnés au corpus.

Sorties :
  data/dockets/LS-J-001..013.json + MANIFEST.json   (13 juges, OT2015–2023)
  data/productions/agreement.json                    (accords B5, 13 juges)
  data/productions/cases.json                        (569 affaires)
  data/productions/research_state.json               (état M1+M2, /paper)
  data/productions/custody.json                      (chaîne de garde)

Règles reprises de LS-1.0 : percentiles = rang médian sur le banc déclaré ;
bandes = bootstrap 10 000 du RANG (percentile 2,5–97,5), graine
sha256(docket|axis|LS-1.0) tronquée à 32 bits ; Wilson 95 % pour les parts
binomiales ; scellement = sha256 de la sérialisation compacte sans
chain.sha256, écrit en dernier.
"""
import gzip
import hashlib
import json
import math
import os
import random
import re
import statistics
import time
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(REPO, "data", "processed")
RES = os.path.join(REPO, "results")
DOCKETS = os.path.join(REPO, "data", "dockets")
PROD = os.path.join(REPO, "data", "productions")

# ——— Le banc déclaré : 13 juges, OT2015–OT2023 ———
# slug, nom affiché, clé justice SCDB (corpus), code écrivain SCDB, docket LS-J
BENCH = [
    ("roberts",   "John G. Roberts, Jr.",   "JGRoberts",     "111", "LS-J-001", "chief-justice"),
    ("thomas",    "Clarence Thomas",        "CThomas",       "108", "LS-J-002", "associate-justice"),
    ("alito",     "Samuel A. Alito, Jr.",   "SAAlito",       "112", "LS-J-003", "associate-justice"),
    ("sotomayor", "Sonia Sotomayor",        "SSotomayor",    "113", "LS-J-004", "associate-justice"),
    ("kagan",     "Elena Kagan",            "EKagan",        "114", "LS-J-005", "associate-justice"),
    ("gorsuch",   "Neil M. Gorsuch",        "NMGorsuch",     "115", "LS-J-006", "associate-justice"),
    ("kavanaugh", "Brett M. Kavanaugh",     "BMKavanaugh",   "116", "LS-J-007", "associate-justice"),
    ("barrett",   "Amy Coney Barrett",      "ACBarrett",     "117", "LS-J-008", "associate-justice"),
    ("jackson",   "Ketanji Brown Jackson",  "KBJackson",     "118", "LS-J-009", "associate-justice"),
    ("scalia",    "Antonin Scalia",         "AScalia",       "105", "LS-J-010", "associate-justice"),
    ("kennedy",   "Anthony M. Kennedy",     "AMKennedy",     "106", "LS-J-011", "associate-justice"),
    ("ginsburg",  "Ruth Bader Ginsburg",    "RBGinsburg",    "109", "LS-J-012", "associate-justice"),
    ("breyer",    "Stephen G. Breyer",      "SGBreyer",      "110", "LS-J-013", "associate-justice"),
]
SLUG_OF_KEY = {k: s for s, n, k, w, d, r in BENCH}
KEY_OF_SLUG = {s: k for s, n, k, w, d, r in BENCH}

ISSUE_AREAS = {
    "1": "Criminal Procedure", "2": "Civil Rights", "3": "First Amendment",
    "4": "Due Process", "5": "Privacy", "6": "Attorneys", "7": "Unions",
    "8": "Economic Activity", "9": "Judicial Power", "10": "Federalism",
    "11": "Interstate Relations", "12": "Federal Taxation",
    "13": "Miscellaneous", "14": "Private Suits",
}
DISPO_LABEL = {
    "1": "stay granted", "2": "affirmed", "3": "affirmed in part",
    "4": "reversed", "5": "reversed in part", "7": "dismissed",
    "9": "unsettled", "11": "affirmed in part", "12": "remanded",
}
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def wilson(k, n, z=1.959964):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(max(0.0, (c - h) / d), 4), round(min(1.0, (c + h) / d), 4)]


def seed_for(docket, axis):
    h = hashlib.sha256(f"{docket}|{axis}|LS-1.0".encode()).hexdigest()
    return int(h[:8], 16)


def percentile_of_rank(rank, n):
    return round(100 * (rank - 0.5) / n)


def median_rank(values, i):
    """Rang médian (1 = plus petit) de values[i], ex æquo moyennés."""
    v = values[i]
    below = sum(1 for x in values if x < v)
    ties = sum(1 for x in values if x == v)
    return below + (ties + 1) / 2


# ————————————————————————————————————————————————
# 1. Chargement du corpus
# ————————————————————————————————————————————————
def load():
    cases = []
    with gzip.open(os.path.join(PROC, "corpus_cases_v1.jsonl.gz"), "rt", encoding="utf-8") as f:
        for line in f:
            cases.append(json.loads(line))
    stats = json.load(open(os.path.join(PROC, "stats_v1.json"), encoding="utf-8"))
    m2 = json.load(open(os.path.join(RES, "m2_baselines.json"), encoding="utf-8"))
    log(f"corpus : {len(cases)} affaires ; stats v1 chargées ; M2 chargé")
    return cases, stats, m2


# ————————————————————————————————————————————————
# 2. Axes par juge — calculés depuis les votes SCDB
# ————————————————————————————————————————————————
def compute_axes(cases):
    """Retourne slug -> {votes, dispo_k, dispo_n, diss_k, diss_n,
    writings [{term, cite}], terms {term: n_writings}}."""
    per = {s: {"votes": 0, "dispo_k": 0, "dispo_n": 0, "diss_k": 0,
               "writings": [], "terms": Counter(), "sep": 0}
           for s in SLUG_OF_KEY.values()}
    for c in cases:
        sc = c.get("scdb") or {}
        disp = str(sc.get("case_disposition") or "")
        writer = str(sc.get("maj_opin_writer") or "")
        term = str(c.get("term") or "")
        cite = c.get("cite_count") or 0
        for j in c.get("justices", []):
            slug = SLUG_OF_KEY.get(j.get("justice", ""))
            if not slug:
                continue
            maj = str(j.get("majority") or "")
            if maj not in ("1", "2"):
                continue  # pas de vote enregistré
            per[slug]["votes"] += 1
            in_min = maj == "1"
            if in_min:
                per[slug]["diss_k"] += 1
            if str(j.get("opinion") or "") in ("2", "3"):
                per[slug]["sep"] += 1
            # disposition : sous-ensemble propre affirmé(2)/infirmé(4)
            if disp in ("2", "4"):
                per[slug]["dispo_n"] += 1
                # côté du juge : majorité + infirmé -> pétitionnaire ;
                # minorité + infirmé -> répondant ; majorité + confirmé ->
                # répondant ; minorité + confirmé -> pétitionnaire.
                for_petitioner = (not in_min) == (disp == "4")
                if for_petitioner:
                    per[slug]["dispo_k"] += 1
        # écritures (opinion majoritaire signée)
        wslug = next((s for s, n, k, w, d, r in BENCH if w == writer), None)
        if wslug and term:
            per[wslug]["writings"].append({"term": term, "cite": cite})
            per[wslug]["terms"][term] += 1
    return per


def axis_stats(bench_values, slug, axis, resampler):
    """Percentile + bande bootstrap du rang, graine déterministe.
    Le banc de l'axe = les juges dont la valeur est mesurée (None exclus
    honnêtement — le banc varie par axe si les données manquent)."""
    valid = [s for s, v in bench_values.items() if v is not None]
    n_bench = len(valid)
    vals = [bench_values[s] for s in valid]
    rank = median_rank(vals, valid.index(slug))
    pct = percentile_of_rank(rank, n_bench)
    rng = random.Random(seed_for(
        next(b[4] for b in BENCH if b[0] == slug), axis))
    boot = {s: resampler(rng, s) for s in valid}
    pcts = []
    bvals = list(boot.values())
    idx = valid.index(slug)
    for _ in range(10000):
        rr = median_rank(bvals, idx)
        pcts.append(percentile_of_rank(rr, n_bench))
    pcts.sort()
    lo = pcts[int(0.025 * len(pcts))]
    hi = pcts[min(len(pcts) - 1, int(0.975 * len(pcts)))]
    return pct, [lo, hi], rank


def build_dockets(per, stats, now):
    dockets = []
    for slug, name, key, writer, docket_id, role in BENCH:
        p = per[slug]
        n_votes = p["votes"]
        # ——— valeurs mesurées ———
        dispo_v = p["dispo_k"] / p["dispo_n"] if p["dispo_n"] else None
        dispo_ci = wilson(p["dispo_k"], p["dispo_n"]) if p["dispo_n"] else None
        temp_v = p["diss_k"] / n_votes if n_votes else None
        temp_ci = wilson(p["diss_k"], n_votes) if n_votes else None
        writes = p["writings"]
        prec_v = statistics.fmean(w["cite"] for w in writes) if writes else None
        terms = sorted(p["terms"])
        expo_v = len(writes) / len(terms) if terms else None
        service_years = len(terms)

        bench_vals = {}
        for s2, *_ in BENCH:
            q = per[s2]
            bench_vals[s2] = {
                "disposition": q["dispo_k"] / q["dispo_n"] if q["dispo_n"] else None,
                "temperament": q["diss_k"] / q["votes"] if q["votes"] else None,
                "precedent": statistics.fmean(w["cite"] for w in q["writings"]) if q["writings"] else None,
                "exposure": len(q["writings"]) / len(q["terms"]) if q["terms"] else None,
            }

        def mk_axis(axis, metric, mdef, value, n, ci, sources, resampler):
            if value is None or n == 0:
                return {"metric": None, "metric_def": None, "value": None,
                        "value_ci95": None, "n": 0, "percentile": None,
                        "rank_band": None, "status": "insufficient-data",
                        "sources": None,
                        "note": "not computable from current sources"}
            vals = {s: bench_vals[s][axis] for s in bench_vals}
            pct, band, rank = axis_stats(vals, slug, axis, resampler)
            return {"metric": metric, "metric_def": mdef, "value": round(value, 4),
                    "value_ci95": ci, "n": n, "percentile": pct,
                    "rank_band": band, "status": "ok", "sources": sources}

        src_votes = ["scdb:2025_01 — votes par juge fusionnés dans "
                     "data/processed/corpus_justices_v1.jsonl.gz (corpus gelé v1, "
                     "chaîne SHA-256 dans stats_v1.json)"]
        src_case = ["scdb:2025_01 (majOpinWriter, caseDisposition) + courtlistener:"
                    "citeCount — fusionnés dans data/processed/corpus_cases_v1.jsonl.gz"]

        def res_dispo(rng, s):
            q = per[s]
            return rng.binomialvariate(q["dispo_n"], q["dispo_k"] / q["dispo_n"]) / q["dispo_n"] if q["dispo_n"] else 0

        def res_temp(rng, s):
            q = per[s]
            return rng.binomialvariate(q["votes"], q["diss_k"] / q["votes"]) / q["votes"] if q["votes"] else 0

        def res_prec(rng, s):
            q = per[s]
            if not q["writings"]:
                return 0
            return statistics.fmean(rng.choice(q["writings"])["cite"] for _ in q["writings"])

        def res_expo(rng, s):
            q = per[s]
            if not q["terms"]:
                return 0
            ks = list(q["terms"].keys())
            return statistics.fmean(rng.choice([q["terms"][t] for t in ks]) for _ in ks)

        axes = {
            "disposition": mk_axis(
                "disposition", "reversal-share",
                "Petitioner-alignment rate: of the decided cases with a clean "
                "affirm/reverse disposition (SCDB caseDisposition 2 or 4) where "
                "this justice voted, the share where their side favored the "
                "party seeking relief — in the majority when the Court reversed "
                "the judgment below, in the minority when it affirmed. A "
                "directional outcome-orientation proxy — not an affirm/reverse "
                "count; mixed and unsettled dispositions are excluded, not "
                "guessed.",
                dispo_v, p["dispo_n"], dispo_ci, src_votes, res_dispo),
            "temperament": mk_axis(
                "temperament", "dissent-rate",
                "Dissent rate: of the merits votes cast (SCDB 2025_01), the "
                "share cast with the minority. A collegial-conduct proxy from "
                "public records — not a psychological assessment.",
                temp_v, n_votes, temp_ci, src_votes, res_temp),
            "precedent": mk_axis(
                "precedent", "citation-impact",
                "Citation impact: mean number of citing decisions received per "
                "authored majority opinion (CourtListener cluster citeCount, "
                "authorship from SCDB majOpinWriter). Influence on precedent, "
                "measured by citation volume, not by treatment. The frozen "
                "corpus does not carry outbound citation arrays — engagement "
                "with precedent (authorities cited) is not measurable from it; "
                "influence is, and is what this axis now reports.",
                prec_v, len(writes), None, src_case, res_prec),
            "reversal": {"metric": None, "metric_def": None, "value": None,
                         "value_ci95": None, "n": 0, "percentile": None,
                         "rank_band": None, "status": "insufficient-data",
                         "sources": None,
                         "note": "not computable from current sources"},
            "orality": {"metric": None, "metric_def": None, "value": None,
                        "value_ci95": None, "n": 0, "percentile": None,
                        "rank_band": None, "status": "insufficient-data",
                        "sources": None,
                        "note": "not computable from current sources"},
            "exposure": mk_axis(
                "exposure", "publication-rate",
                "Publication rate: authored majority opinions per term of "
                "service inside the declared window (authorship from SCDB "
                "majOpinWriter, terms present in the frozen corpus).",
                expo_v, len(writes), None, src_case, res_expo),
        }

        short = service_years < 9
        d = {
            "standard": "LS-1.0",
            "docket": docket_id,
            "revision": 2 if docket_id != "LS-J-010" and slug in {
                "roberts", "thomas", "alito", "sotomayor", "kagan", "gorsuch",
                "kavanaugh", "barrett", "jackson"} else 1,
            "subject": {
                "name": name, "slug": slug, "role": role,
                "court": "supreme-court-of-the-united-states",
                "bench": "scotus-ot2015-2023", "bench_n": 13,
                "small_bench": short,
            },
            "status": "FILED",
            "filed_at": now,
            "window": {"start": "2015-10-01", "end": "2024-06-30"},
            "raw": {
                "merits_votes": n_votes,
                "lead_opinions": len(writes),
                "service_years_window": service_years,
                "separate_writings": p["sep"],
                "dissents": p["diss_k"],
            },
            "axes": axes,
            "projections": {
                "iterations": 10000,
                "quantiles": {"p10": None, "p50": None, "p90": None},
                "seed_basis": "sha256(docket|axis|LS-1.0) truncated to 32 bits",
            },
            "limits": [
                "Temperament is a collegiality proxy from public voting records, not a psychological assessment.",
                "Percentiles are relative to the declared bench (the thirteen justices who sat OT2015–OT2023), not absolute qualities.",
                "Small-bench rule: with 13 members, percentiles take 13 discrete values — the granularity is coarse by construction.",
                "Reversal and Orality are null: SCOTUS is the terminal court (no reviewing treatment data), and oral-argument behavior is not yet ingested.",
                "The window is OT2015–OT2023; a justice who sat for part of it has fewer observations by fact, not by choice.",
                "Precedent measures citations received (influence), not authorities cited (engagement): the frozen corpus carries no outbound citation arrays, so the axis was re-based on CourtListener citeCount — the switch is disclosed here rather than silently kept. Citations accumulate with time: opinions authored late in the window (Barrett, Jackson) have had fewer years to be cited than early-window ones — a recency artifact of the measurement, visible in the values.",
                "Disposition is computed on the clean affirm/reverse subset (SCDB caseDisposition 2/4); other dispositions are excluded rather than guessed.",
            ],
            "chain": {
                "computed_at": now,
                "pipeline": "legally-subjective/2.0.0",
                "correction": "Corpus-Monde v1 pivot: every axis recomputed from "
                              "SCDB 2025_01 votes fused into the frozen corpus "
                              "(OT2015–OT2023), replacing the Oyez window "
                              "OCT2020–AUG2026. Precedent re-based from "
                              "authorities-cited to citations-received; disclosed "
                              "in limits.",
                "sha256": None,
            },
        }
        if d["revision"] == 2:
            d["supersedes"] = {
                "docket": docket_id, "revision": 1,
                "reason": "Corpus-Monde v1: re-measured on SCDB 2025_01 votes, "
                          "OT2015–OT2023 (13-justice bench), superseding the "
                          "Oyez OCT2020–AUG2026 measurement.",
            }
        # scellement : sérialisation compacte sans chain.sha256, écrite en dernier
        sealed = {k: v for k, v in d.items() if k != "chain"}
        sealed["chain"] = {k: v for k, v in d["chain"].items() if k != "sha256"}
        d["chain"]["sha256"] = hashlib.sha256(
            json.dumps(sealed, ensure_ascii=False, separators=(",", ":"))
            .encode("utf-8")).hexdigest().upper()
        dockets.append(d)
    return dockets


# ————————————————————————————————————————————————
# 3. Accord inter-juges (B5 → slugs)
# ————————————————————————————————————————————————
def build_agreement(m2):
    pairs = {}
    for key, v in m2["B5_agreement"].items():
        a, b = key.split("|")
        sa, sb = SLUG_OF_KEY.get(a), SLUG_OF_KEY.get(b)
        if not sa or not sb:
            continue
        k1, k2 = sorted([sa, sb])
        pairs[f"{k1}|{k2}"] = {"n": v["n"], "agree": v["agreement"]}
    return {
        "computed_at": NOW,
        "window": {"start": "2015-10-01", "end": "2024-06-30"},
        "basis": "common merits cases where both justices cast a vote with a "
                 "coded direction (SCDB 2025_01, direction 1/2), n >= 50 pairs "
                 "kept",
        "sources": [
            "scdb:2025_01 — via data/processed/corpus_justices_v1.jsonl.gz",
            "results/m2_baselines.json — B5 (Wilson 95% IC dans le fichier source)",
        ],
        "pairs": pairs,
    }


# ————————————————————————————————————————————————
# 4. Le dossier des affaires (cases.json)
# ————————————————————————————————————————————————
def epoch(datestr):
    import calendar
    return calendar.timegm(time.strptime(datestr[:10], "%Y-%m-%d")) if datestr else None


def norm_docket(scdb_docket, tokens):
    d0 = re.split(r"[;,]", (scdb_docket or "").strip())
    d0 = [x.strip().replace("–", "-").replace("—", "-").replace(" ", "")
          for x in d0 if x.strip()]
    if not d0 and tokens:
        d0 = [str(tokens[0])]
    return d0[0] if d0 else "undocketed"


def build_cases(cases):
    # ——— prédiction B4 par affaire : vote modal de chaque juge sur le train ———
    justice_train = defaultdict(Counter)
    for c in cases:
        if str(c.get("term") or "") <= "2019":
            for j in c.get("justices", []):
                if str(j.get("direction") or "") in ("1", "2"):
                    justice_train[j["justice"]][str(j["direction"])] += 1
    justice_modal = {j: Counter(v).most_common(1)[0][0]
                     for j, v in justice_train.items()
                     if sum(v.values()) >= 20}

    out = []
    seen = set()
    for c in cases:
        sc = c.get("scdb") or {}
        docket = norm_docket(sc.get("scdb_docket"), c.get("docket_tokens"))
        while docket in seen:
            docket += "x"  # pas de collision silencieuse dans les URLs
        seen.add(docket)
        votes = {}
        vote_dirs = {}
        for j in c.get("justices", []):
            slug = SLUG_OF_KEY.get(j.get("justice", ""))
            if not slug:
                continue
            maj = str(j.get("majority") or "")
            if maj == "2":
                votes[slug] = "majority"
            elif maj == "1":
                votes[slug] = "minority"
            d = str(j.get("direction") or "")
            if d in ("1", "2"):
                vote_dirs[slug] = "conservative" if d == "1" else "liberal"
        try:
            n_maj = int(sc.get("maj_votes")) if sc.get("maj_votes") else None
        except (TypeError, ValueError):
            n_maj = None
        try:
            n_min = int(sc.get("min_votes")) if sc.get("min_votes") else None
        except (TypeError, ValueError):
            n_min = None
        if n_maj is None:
            n_maj = sum(1 for v in votes.values() if v == "majority") or None
        if n_min is None:
            n_min = sum(1 for v in votes.values() if v == "minority") or 0
        split = f"{n_maj}–{n_min}" if n_maj is not None else "—"
        if n_maj is None or n_min is None or n_maj == n_min:
            flip = None  # pas de majorité nette parmi les votes enregistrés
        else:
            flip = (n_maj - n_min) // 2 + 1
        disp = str(sc.get("case_disposition") or "")
        ddir = str(sc.get("decision_direction") or "")
        # appel de la baseline B4 pour cette affaire (règle honnête, train seul)
        pred_votes = [justice_modal[j["justice"]] for j in c.get("justices", [])
                      if j.get("justice") in justice_modal]
        baseline_call = None
        if pred_votes:
            cnt = Counter(pred_votes)
            top = cnt.most_common()
            if len(top) == 1 or top[0][1] > top[1][1]:
                baseline_call = {"1": "conservative", "2": "liberal"}[top[0][0]]
        actual_dir = {"1": "conservative", "2": "liberal"}.get(ddir)
        baseline_correct = (
            baseline_call is not None and actual_dir is not None
            and baseline_call == actual_dir
        ) if (baseline_call is not None and actual_dir is not None) else None
        rec = {
            "docket": docket,
            "name": c.get("case_name") or "—",
            "term": str(c.get("term") or ""),
            "decided": epoch(sc.get("date_decision") or c.get("date_filed")),
            "issue_area": ISSUE_AREAS.get(str(sc.get("issue_area") or ""), "—")
            if sc.get("issue_area") else "—",
            "split": split,
            "n_maj": n_maj,
            "n_min": n_min,
            "flip_margin": flip,
            "unanimous": n_min == 0 and (n_maj or 0) > 0,
            "direction": {"1": "conservative", "2": "liberal"}.get(ddir),
            "disposition": DISPO_LABEL.get(disp, f"disposition {disp}" if disp else None),
            "petitioner_won": {"4": True, "2": False}.get(disp),
            "winning_party": None,
            "question": None,
            "votes": votes,
            "vote_dirs": vote_dirs,
            "baseline_call": baseline_call,
            "baseline_correct": baseline_correct,
            "model": {},
        }
        out.append(rec)
    return out


# ————————————————————————————————————————————————
# 5. État de recherche (/paper) + garde (custody)
# ————————————————————————————————————————————————
def build_research_state(stats, m2, cases, raw_cases):
    b5 = m2["B5_agreement"]
    lo = min(b5.items(), key=lambda kv: kv[1]["agreement"])
    hi = max(b5.items(), key=lambda kv: kv[1]["agreement"])
    n_dir = sum(1 for c in cases if c["direction"])
    n_votes = sum(1 for c in cases for v in c["votes"].values())
    one_door = sum(1 for c in cases if c["flip_margin"] == 1)
    # profil idéologique par juge (train OT2015-2019, fondement de B4)
    jt = defaultdict(Counter)
    for c in raw_cases:
        if str(c.get("term") or "") <= "2019":
            for j in c.get("justices", []):
                d = str(j.get("direction") or "")
                if d in ("1", "2"):
                    jt[j["justice"]][d] += 1
    lean = {}
    for jk, cnt in jt.items():
        n = cnt["1"] + cnt["2"]
        if n < 20:
            continue
        slug = SLUG_OF_KEY.get(jk)
        if not slug:
            continue
        lean[slug] = {
            "modal": "conservative" if cnt["1"] >= cnt["2"] else "liberal",
            "conservative_share": round(cnt["1"] / n, 4),
            "n_train": n,
        }
    return {
        "state_id": "LS-R-002",
        "filed_at": NOW,
        "corpus": {
            "name": "Corpus-Monde v1 (gelé 2026-08-28)",
            "n_cases": stats["n_cases"],
            "n_opinions": stats["n_opinions"],
            "n_with_scdb": stats["n_with_scdb"],
            "n_with_direction": n_dir,
            "n_votes": n_votes,
            "n_justices": 13,
            "terms": "OT2015–OT2023",
            "window": {"start": "2015-10-01", "end": "2024-06-30"},
            "n_five_four": stats["n_five_four"],
            "n_sealed": stats["five_four_selection"]["n_selected"],
            "sealed_sha256": stats["five_four_selection"]["sealed_sha256"],
            "audio_coverage": stats["audio_coverage"],
            "transcript_coverage": stats["transcript_coverage"],
            "one_vote_margin_cases": one_door,
        },
        "split": m2["split"],
        "baselines": [
            {"id": "B1", "name": "Majority class (liberal), OT2015–2019 prior",
             "accuracy": m2["B1_majority_class"]["accuracy"],
             "ic95": m2["B1_majority_class"]["accuracy_ic95"],
             "n": m2["B1_majority_class"]["test_n"],
             "note": m2["B1_majority_class"]["modal_direction"]},
            {"id": "B2", "name": "Always conservative",
             "accuracy": m2["B2_always"]["toujours_conservateur"]["accuracy"],
             "ic95": m2["B2_always"]["toujours_conservateur"]["ic95"], "n": 225},
            {"id": "B3", "name": "Always reverse the court below",
             "accuracy": m2["B3_petitioner_wins"]["accuracy"],
             "ic95": m2["B3_petitioner_wins"]["ic95"],
             "n": m2["B3_petitioner_wins"]["n"],
             "note": "clean affirm/reverse subset (SCDB caseDisposition 2/4)"},
            {"id": "B4", "name": "Per-justice ideology (vote level)",
             "accuracy": m2["B4_justice_ideology"]["vote_accuracy"],
             "ic95": m2["B4_justice_ideology"]["vote_accuracy_ic95"],
             "n": None,
             "note": "the number to beat"},
            {"id": "B4c", "name": "Per-justice ideology (case level)",
             "accuracy": m2["B4_justice_ideology"]["case_accuracy"],
             "ic95": m2["B4_justice_ideology"]["case_accuracy_ic95"],
             "n": None},
        ],
        "agreement": {
            "n_pairs": len(b5),
            "min": lo[1]["agreement"], "min_pair": lo[0],
            "min_n": lo[1]["n"], "min_ic95": lo[1]["ic95"],
            "max": hi[1]["agreement"], "max_pair": hi[0],
            "max_n": hi[1]["n"], "max_ic95": hi[1]["ic95"],
        },
        "justice_lean": lean,
        "protocol": {
            "conditions": [
                {"id": "A", "name": "Zero-shot",
                 "spec": "Llama 3 8B decides from the dossier alone — no learning of its own"},
                {"id": "B", "name": "Persona",
                 "spec": "same model, QLoRA-finetuned on a justice's PAST opinions; tested on that justice's FUTURE cases"},
                {"id": "C", "name": "Context",
                 "spec": "same model + retrieval of similar earlier opinions (RAG)"},
                {"id": "D", "name": "Statistics",
                 "spec": "the M2 baselines above"},
            ],
            "decisive_test": "B > A on unseen future cases => the persona is "
                             "extractible from public texts. B = A => the "
                             "personality is not in the public data. Both "
                             "outcomes are results.",
            "final_exam": "One pass, four conditions, on the 50 sealed 5-4 "
                          "decisions (selection seed and SHA-256 in "
                          "stats_v1.json).",
        },
        "status": {
            "m1_corpus": "frozen 2026-08-28",
            "m2_baselines": "done",
            "m15_opinion_texts": "in progress (CourtListener API, rate-limited "
                                 "token, resumable passes)",
            "m3_training": "pending (QLoRA personas, free Colab/Kaggle)",
            "m4_final_exam": "sealed, not run",
        },
        "figures": ["/figures/fig1-baselines.png", "/figures/fig2-agreement.png",
                    "/figures/fig3-balance.png"],
    }


def build_custody(dockets, stats):
    axes_sources = {
        "disposition": {
            "system": "scdb-2025_01",
            "uri_pattern": "http://scdb.wustl.edu (caseDisposition + vote records)",
            "cache": "data/processed/corpus_{cases,justices}_v1.jsonl.gz",
        },
        "temperament": {
            "system": "scdb-2025_01",
            "uri_pattern": "http://scdb.wustl.edu (vote records)",
            "cache": "data/processed/corpus_justices_v1.jsonl.gz",
        },
        "precedent": {
            "system": "scdb+courtlistener",
            "uri_pattern": "http://scdb.wustl.edu (majOpinWriter) + CourtListener citeCount",
            "cache": "data/processed/corpus_cases_v1.jsonl.gz",
        },
        "exposure": {
            "system": "scdb-2025_01",
            "uri_pattern": "http://scdb.wustl.edu (majOpinWriter)",
            "cache": "data/processed/corpus_cases_v1.jsonl.gz",
        },
    }
    tree = {}
    for fname in ("corpus_cases_v1.jsonl.gz", "corpus_justices_v1.jsonl.gz",
                  "corpus_opinions_v1.jsonl.gz"):
        h = hashlib.sha256()
        with open(os.path.join(PROC, fname), "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        tree[fname] = h.hexdigest().upper()
    dock = {}
    for d in dockets:
        dock[d["docket"]] = {
            "subject": d["subject"]["name"],
            "docket_sha256": d["chain"]["sha256"],
            "index": {
                "files": 3,
                "cache": "data/processed/corpus_{cases,justices,opinions}_v1.jsonl.gz — frozen Corpus-Monde v1",
                "retrieved_window": [stats.get("generated_at", "2026-08-28T07:54:52Z").replace("+00:00", "Z"), NOW],
                "tree_sha256": tree["corpus_cases_v1.jsonl.gz"],
            },
            "axes": {
                ax: {
                    "system": spec["system"],
                    "uri_pattern": spec["uri_pattern"],
                    "cache": spec["cache"],
                    "files": 3 if ax in ("disposition", "precedent") else
                             (2 if ax == "exposure" else 1),
                    "retrieved_window": ["2026-08-28T07:54:52Z", NOW],
                    "tree_sha256": tree.get(
                        "corpus_justices_v1.jsonl.gz" if ax in ("disposition", "temperament")
                        else "corpus_cases_v1.jsonl.gz"),
                }
                for ax, spec in axes_sources.items()
            },
        }
    return {
        "exported_at": NOW,
        "law": "Every non-null value in a FILED docket traces to >= 1 public "
               "source URI, cached with retrieval timestamps. Tree hashes "
               "cover the exact corpus bytes the docket was computed from "
               "(sha256 of the frozen jsonl.gz files, recorded in "
               "stats_v1.json).",
        "dockets": dock,
    }


# ————————————————————————————————————————————————
# main
# ————————————————————————————————————————————————
def main():
    cases, stats, m2 = load()
    per = compute_axes(cases)
    log("axes calculés ; écriture des dockets…")

    dockets = build_dockets(per, stats, NOW)
    os.makedirs(DOCKETS, exist_ok=True)
    manifest = {"filed_at": NOW, "standard": "LS-1.0",
                "pipeline": "legally-subjective/2.0.0", "dockets": {}}
    for d in dockets:
        path = os.path.join(DOCKETS, d["docket"] + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
            f.write("\n")
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        # le manifeste porte le SCEAU (comme l'ancienne chaîne) :
        manifest["dockets"][d["docket"]] = d["chain"]["sha256"]
    with open(os.path.join(DOCKETS, "MANIFEST.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    log(f"{len(dockets)} dockets écrits + MANIFEST")

    agr = build_agreement(m2)
    with open(os.path.join(PROD, "agreement.json"), "w", encoding="utf-8") as f:
        json.dump(agr, f, indent=2, ensure_ascii=False)
        f.write("\n")
    log(f"agreement.json : {len(agr['pairs'])} paires")

    recs = build_cases(cases)
    with open(os.path.join(PROD, "cases.json"), "w", encoding="utf-8") as f:
        json.dump({"n_cases": len(recs), "record_id": "LS-CORPUS-V1",
                   "cases": recs}, f, indent=1, ensure_ascii=False)
    log(f"cases.json : {len(recs)} affaires")

    rs = build_research_state(stats, m2, recs, cases)
    with open(os.path.join(PROD, "research_state.json"), "w", encoding="utf-8") as f:
        json.dump(rs, f, indent=2, ensure_ascii=False)
        f.write("\n")
    log("research_state.json écrit")

    cust = build_custody(dockets, stats)
    with open(os.path.join(PROD, "custody.json"), "w", encoding="utf-8") as f:
        json.dump(cust, f, indent=2, ensure_ascii=False)
        f.write("\n")
    log("custody.json écrit")

    # ——— résumé de contrôle ———
    print("\n===== RÉSUMÉ DE CONTRÔLE =====")
    for d in dockets:
        a = d["axes"]
        print(f"{d['docket']} {d['subject']['name']:<26} "
              f"disp={a['disposition']['value'] if a['disposition']['value'] is not None else '—'} "
              f"(n={a['disposition']['n']}) pct={a['disposition']['percentile']} | "
              f"diss={a['temperament']['value']} pct={a['temperament']['percentile']} | "
              f"cit={a['precedent']['value'] if a['precedent']['value'] is not None else '—'} "
              f"pct={a['precedent']['percentile']} | "
              f"expo={a['exposure']['value'] if a['exposure']['value'] is not None else '—'} "
              f"pct={a['exposure']['percentile']}")


if __name__ == "__main__":
    main()
