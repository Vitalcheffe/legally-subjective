"""LS-1.0 axes computation — v1.

Pure functions over cached sources only. No network. Deterministic:
same cache -> bit-identical metrics. Seeds derive from sha256(docket_id|axis|standard).

Axis definitions as implemented (each disclosed in the docket's metric_def):

  disposition  "petitioner-alignment rate" — of the merits cases the justice
               voted in, the share where their side favored the party seeking
               relief (petitioner/appellant), derived from the Oyez
               winning-party record. Directional outcome orientation.
  temperament  "dissent rate" — of the merits votes cast, the share cast with
               the minority. Collegial-conduct proxy, NOT psychology.
  precedent    "citation density" — mean authorities cited per authored lead
               opinion.
  exposure     "publication rate" — authored lead opinions per year of service
               inside the declared window.
  reversal     null — SCOTUS is the terminal court; treatment analysis by
               reviewing courts is not computable from current sources.
  orality      null — oral-argument transcripts not yet ingested.

Percentiles: median-rank convention against the declared bench
(pct = 100*(rank-0.5)/bench_size, ties averaged). Small-bench rule (LS-1.0
sec. 3.5bis, added before first filing): a bench of >= 5 members is valid;
the docket must disclose bench_n and the coarse granularity.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SOURCES = REPO / "data" / "sources"
OYEZ_DIR = SOURCES / "oyez"
JUDGES_DIR = SOURCES / "courtlistener" / "judges"
INDEX_DIR = SOURCES / "courtlistener" / "index"

STANDARD = "LS-1.0"
BOOTSTRAP_ITERS = 10_000

# The Nine, seniority order = docket order. (slug, display name, CL author_id)
THE_NINE = [
    ("roberts", "John G. Roberts, Jr.", 2738),
    ("thomas", "Clarence Thomas", 3200),
    ("alito", "Samuel A. Alito, Jr.", 77),
    ("sotomayor", "Sonia Sotomayor", 3045),
    ("kagan", "Elena Kagan", 1691),
    ("gorsuch", "Neil M. Gorsuch", 1250),
    ("kavanaugh", "Brett M. Kavanaugh", 1713),
    ("barrett", "Amy Coney Barrett", 8543),
    ("jackson", "Ketanji Brown Jackson", 1609),
]

ROLE = {
    "roberts": "chief-justice",
    "thomas": "associate-justice",
    "alito": "associate-justice",
    "sotomayor": "associate-justice",
    "kagan": "associate-justice",
    "gorsuch": "associate-justice",
    "kavanaugh": "associate-justice",
    "barrett": "associate-justice",
    "jackson": "associate-justice",
}

WINDOW_START = "2020-10-01"  # OT2020 opening — the declared bench window

_STOP_TOKENS = {"inc", "llc", "co", "et", "al", "the", "of", "and", "for", "plc", "jr", "ltd", "usa"}


def _tokens(s: str | None) -> list[str]:
    import re

    return [re.sub(r"[^a-z0-9]", "", t.lower()) for t in re.split(r"[\s,.]+", (s or "")) if t]


def resolve_winning_side(winning_party: str | None, first_party: str | None, second_party: str | None) -> str | None:
    """Which side won — 'first' (petitioner/appellant) or 'second'.

    Oyez's winning_party is a short display name (often a surname, an
    acronym, or carrying typos: 'Rutledge' vs 'Leslie Rutlege, ...').
    Resolver order: exact, containment, token-subset, prefix, acronym.
    Returns None when unresolvable — missing data stays missing."""
    if not winning_party:
        return None
    w = winning_party.strip()
    for party, side in ((first_party, "first"), (second_party, "second")):
        if party and w.lower() == party.strip().lower():
            return side
    for party, side in ((first_party, "first"), (second_party, "second")):
        if party and w.lower() in party.lower():
            return side
    wt = set(_tokens(w)) - _STOP_TOKENS
    for party, side in ((first_party, "first"), (second_party, "second")):
        pt = _tokens(party) if party else []
        if not pt:
            continue
        if wt and wt.issubset(set(pt)):
            return side
        for t in wt:
            if len(t) >= 4 and any(p.startswith(t[:4]) for p in pt):
                return side
        acronym = "".join(p[0] for p in pt if p and p not in _STOP_TOKENS)
        if len(w) >= 2 and w.replace(".", "").lower() == acronym:
            return side
    return None


# ————————————————————————————————————————————————
# Loading
# ————————————————————————————————————————————————

def load_oyez_votes() -> list[dict]:
    """Every cached Oyez case with a usable decision -> flat vote records.

    Record: {docket, term, name, decided, petitioner_won,
             justice(slug), vote, opinion_type, separate(bool)}
    """
    by_last: dict[str, str] = {}
    for slug, _, _ in THE_NINE:
        by_last[slug] = slug

    records: list[dict] = []
    for f in sorted(OYEZ_DIR.glob("*.json")):
        if f.name.endswith(".miss.json"):
            continue
        case = json.loads(f.read_text())
        decisions = case.get("decisions") or []
        if not decisions:
            continue
        dec = decisions[0]
        fp = case.get("first_party")
        sp = case.get("second_party")
        fpn = fp.get("name") if isinstance(fp, dict) else fp
        spn = sp.get("name") if isinstance(sp, dict) else sp
        side = resolve_winning_side(dec.get("winning_party"), fpn, spn)
        petitioner_won = None if side is None else side == "first"
        term = case.get("term")
        docket = case.get("docket_number")
        name = case.get("name")
        decided = None
        for tl in case.get("timeline") or []:
            if tl.get("event") == "Decided":
                dates = tl.get("dates") or []
                if dates:
                    decided = dates[0]
        for v in dec.get("votes") or []:
            member = v.get("member") or {}
            ln = (member.get("last_name") or "").strip().lower()
            slug = by_last.get(ln)
            if not slug:
                continue  # Breyer and pre-2022 benches are not the declared bench
            vote = v.get("vote")
            if vote not in ("majority", "minority"):
                continue  # recusal / no data — participation is not assumed
            op_type = v.get("opinion_type") or "none"
            records.append(
                {
                    "docket": docket,
                    "term": term,
                    "name": name,
                    "decided": decided,
                    "petitioner_won": petitioner_won,
                    "justice": slug,
                    "vote": vote,
                    "opinion_type": op_type,
                    "separate": op_type not in ("none", "majority"),
                }
            )
    records.sort(key=lambda r: (str(r["docket"]), r["justice"]))
    return records


def load_cl_opinions(slug: str) -> list[dict]:
    """Lead-opinion cache for one justice: [{cluster_id, dateFiled, cites, citeCount}]."""
    d = JUDGES_DIR / slug
    out: list[dict] = []
    i = 1
    while True:
        f = d / f"opinions__page_{i:03d}.json"
        if not f.exists():
            break
        page = json.loads(f.read_text())
        for r in page.get("results", []):
            ops = r.get("opinions") or []
            own = [op for op in ops if op.get("cites") is not None]
            cites = sum(len(op.get("cites") or []) for op in own) if own else None
            out.append(
                {
                    "cluster_id": r.get("cluster_id"),
                    "caseName": r.get("caseName"),
                    "docketNumber": r.get("docketNumber"),
                    "dateFiled": r.get("dateFiled"),
                    "cites": cites,
                    "citeCount": r.get("citeCount"),
                }
            )
        i += 1
    # dedupe by cluster (revised postings can duplicate)
    seen: dict = {}
    for r in out:
        key = str(r["cluster_id"])
        if key not in seen or (r["cites"] or 0) > (seen[key]["cites"] or 0):
            seen[key] = r
    return sorted(seen.values(), key=lambda r: (str(r["dateFiled"]), str(r["cluster_id"])))


def service_years(slug: str, window_start_iso: str, window_end_iso: str) -> list[int]:
    """Calendar years of service inside the window, from Oyez role metadata
    in cache. The full span is returned (a year with no opinions still counts)."""
    import datetime as dt

    start = dt.date.fromisoformat(window_start_iso)
    end = dt.date.fromisoformat(window_end_iso)
    role_start_unix = None
    for f in sorted(OYEZ_DIR.glob("*.json")):
        if f.name.endswith(".miss.json"):
            continue
        case = json.loads(f.read_text())
        for dec in case.get("decisions") or []:
            for v in dec.get("votes") or []:
                m = v.get("member") or {}
                if (m.get("last_name") or "").strip().lower() == slug:
                    for role in m.get("roles") or []:
                        if role.get("type") == "scotus_justice" and role.get("date_start"):
                            rs = role["date_start"]
                            role_start_unix = rs if role_start_unix is None else min(role_start_unix, rs)
        if role_start_unix is not None:
            break
    if role_start_unix is not None:
        sworn = dt.datetime.fromtimestamp(role_start_unix, dt.timezone.utc).date()
        start = max(start, sworn)
    return list(range(start.year, end.year + 1))


def window_end_date() -> str:
    """Latest filing date observed in the CL index — the window is data-bounded."""
    idx = json.loads((INDEX_DIR / "index.json").read_text())
    dates = [c.get("dateFiled") for c in idx["clusters"] if c.get("dateFiled")]
    return max(dates)


# ————————————————————————————————————————————————
# Metrics
# ————————————————————————————————————————————————

def metric_disposition(votes: list[dict]) -> tuple[float, int] | None:
    """Petitioner-alignment rate: share of voted cases where the justice's
    side favored the party seeking relief (petitioner/appellant)."""
    rs = [v for v in votes if v["petitioner_won"] is not None]
    if not rs:
        return None
    aligned = sum(
        1
        for v in rs
        if (v["petitioner_won"] and v["vote"] == "majority")
        or (not v["petitioner_won"] and v["vote"] == "minority")
    )
    return aligned / len(rs), len(rs)


def metric_temperament(votes: list[dict]) -> tuple[float, int] | None:
    if not votes:
        return None
    val = sum(1 for v in votes if v["vote"] == "minority") / len(votes)
    return val, len(votes)


def metric_precedent(ops: list[dict]) -> tuple[float, int] | None:
    rs = [o["cites"] for o in ops if o["cites"] is not None]
    if not rs:
        return None
    return statistics.fmean(rs), len(rs)


def metric_exposure(ops: list[dict], years: list[int]) -> tuple[float, int] | None:
    """Opinions per calendar year of service in the window.
    `years` = the full list of service calendar years (zeros counted)."""
    if not ops or not years:
        return None
    return len(ops) / len(years), len(ops)


def percentile_rank(value: float, bench: list[float]) -> float:
    """Median-rank percentile of value within bench (value included in bench)."""
    n = len(bench)
    below = sum(1 for b in bench if b < value)
    equal = sum(1 for b in bench if b == value)
    # ties averaged: positions below+1 .. below+equal
    rank = below + (equal + 1) / 2.0
    return 100.0 * (rank - 0.5) / n


def _seed(docket_id: str, axis: str) -> int:
    h = hashlib.sha256(f"{docket_id}|{axis}|{STANDARD}".encode()).hexdigest()
    return int(h[:8], 16) % (2**32)


def bootstrap_ci(
    docket_id: str,
    axis: str,
    unit_values: list[float],
    metric_fn,
    bench_others: list[float],
    self_value: float,
) -> list[int]:
    """Resample the justice's decision units, recompute metric and its
    percentile against the fixed bench (others' metrics unchanged).
    Returns [p2.5, p97.5] of the percentile distribution."""
    rng = random.Random(_seed(docket_id, axis))
    n = len(unit_values)
    pcts: list[float] = []
    for _ in range(BOOTSTRAP_ITERS):
        sample = [unit_values[rng.randrange(n)] for _ in range(n)]
        m = metric_fn(sample)
        if m is None:
            continue
        pcts.append(percentile_rank(m, bench_others + [m]))
    if not pcts:
        return [0, 100]
    pcts.sort()
    lo = pcts[int(0.025 * len(pcts))]
    hi = pcts[min(int(0.975 * len(pcts)), len(pcts) - 1)]
    return [round(lo), round(hi)]


# ————————————————————————————————————————————————
# The full computation
# ————————————————————————————————————————————————

def compute_bench() -> dict:
    """Compute every justice's metrics + percentiles + CIs from cache."""
    votes = load_oyez_votes()
    wend = window_end_date()

    per_slug_votes: dict[str, list[dict]] = {s: [] for s, _, _ in THE_NINE}
    for v in votes:
        per_slug_votes[v["justice"]].append(v)

    raw: dict[str, dict] = {}
    for slug, name, author_id in THE_NINE:
        vs = per_slug_votes[slug]
        ops = load_cl_opinions(slug)
        years = service_years(slug, WINDOW_START, wend)
        raw[slug] = {
            "name": name,
            "author_id": author_id,
            "votes": vs,
            "ops": ops,
            "years": years,
            "m_disposition": metric_disposition(vs),
            "m_temperament": metric_temperament(vs),
            "m_precedent": metric_precedent(ops),
            "m_exposure": metric_exposure(ops, years),
        }

    def bench_of(key: str) -> list[float]:
        return [raw[s][key][0] for s, _, _ in THE_NINE if raw[s][key] is not None]

    axes_meta = {
        "disposition": ("m_disposition", "reversal-share"),
        "temperament": ("m_temperament", "dissent-rate"),
        "precedent": ("m_precedent", "citation-density"),
        "exposure": ("m_exposure", "publication-rate"),
    }
    bench_values = {axis: bench_of(mk) for axis, (mk, _) in axes_meta.items()}

    for slug, _, _ in THE_NINE:
        r = raw[slug]
        docket_id = f"LS-J-{THE_NINE.index((slug, r['name'], r['author_id'])) + 1:03d}"
        r["docket_id"] = docket_id
        r["axes"] = {}
        for axis, (mk, mname) in axes_meta.items():
            m = r[mk]
            if m is None or len(bench_values[axis]) < 5:
                r["axes"][axis] = None
                continue
            value, n = m
            pct = percentile_rank(value, bench_values[axis])
            others = [b for s2, _, _ in THE_NINE if s2 != slug and raw[s2][mk] is not None for b in [raw[s2][mk][0]]]
            if axis == "disposition":
                units = [
                    1.0
                    if ((v["petitioner_won"] and v["vote"] == "majority")
                        or (not v["petitioner_won"] and v["vote"] == "minority"))
                    else 0.0
                    for v in r["votes"]
                    if v["petitioner_won"] is not None
                ]
                ci = bootstrap_ci(docket_id, axis, units, lambda s: sum(s) / len(s) if s else None, others, value)
            elif axis == "temperament":
                units = [1.0 if v["vote"] == "minority" else 0.0 for v in r["votes"]]
                ci = bootstrap_ci(docket_id, axis, units, lambda s: sum(s) / len(s) if s else None, others, value)
            elif axis == "precedent":
                units = [float(o["cites"]) for o in r["ops"] if o["cites"] is not None]
                ci = bootstrap_ci(docket_id, axis, units, lambda s: statistics.fmean(s) if s else None, others, value)
            else:  # exposure — resample yearly counts (zeros included)
                per_year: dict[int, int] = {y: 0 for y in r["years"]}
                for o in r["ops"]:
                    y = (o.get("dateFiled") or "")[:4]
                    if y and int(y) in per_year:
                        per_year[int(y)] += 1
                units = [float(per_year[y]) for y in sorted(per_year)]
                ci = bootstrap_ci(docket_id, axis, units, lambda s: sum(s) / len(s) if s else None, others, value)
            r["axes"][axis] = {
                "percentile": round(pct),
                "ci95": ci,
                "n": n,
                "status": "ok",
                "value": value,
                "metric": mname,
            }

    return {"window_start": WINDOW_START, "window_end": wend, "justices": raw}


def agreement_matrix() -> dict:
    """Pairwise agreement rate over common merits cases (same case, both voted)."""
    votes = load_oyez_votes()
    by_case: dict[str, dict[str, str]] = {}
    for v in votes:
        by_case.setdefault(str(v["docket"]), {})[v["justice"]] = v["vote"]
    slugs = [s for s, _, _ in THE_NINE]
    out: dict[str, dict] = {}
    for i, a in enumerate(slugs):
        for b in slugs[i + 1 :]:
            common = [c for c, m in by_case.items() if a in m and b in m]
            agree = sum(1 for c in common if by_case[c][a] == by_case[c][b])
            out[f"{a}|{b}"] = {
                "n": len(common),
                "agree": agree / len(common) if common else None,
            }
    return out
