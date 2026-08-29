#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M3: build the persona datasets (condition B) and the
evaluation case files (conditions A/B/C).

What this builder enforces (the no-leak law, mechanically):

  * CASE FILES are PRE-DECISION only. From Oyez we take facts, question,
    parties, posture and lower court. We NEVER take `conclusion`,
    `decided_by`, `decisions`, or `opinion_announcement` — those encode the
    outcome. From the corpus/SCDB we take issue area and lower-court
    disposition. No votes, no directions, no disposition of the Court.
  * SPLIT is temporal and strict: train = OT2015..OT2019, transparent test =
    OT2020..OT2023, exactly as pre-registered (docs/04-PROTOCOLE.md).
  * THE SEALED FIFTY are excluded from every file this builder emits —
    train, test, case files — using the same docket-matching rule as M2/M3a.
    They are not written anywhere. The Final Test (M4) is the only consumer.
  * PERSONA TRAINING ROWS = the justice's own opinions (majority/dissent/
    concurrence) inside the train window, wrapped in the shared instruction
    template. Vote-direction labels are NOT training targets (the
    pre-registered design trains on written output only; `--with-vote-sft`
    exists as a documented, default-off extension).
  * WAITING STATE: opinion texts live in data/raw/opinion_texts/ (M1.5
    output, not committed). Until M1.5 completes, the builder emits the
    case files, the persona skeletons (0 text rows), per-justice vote
    tables for the transparent eval, and an honest manifest. No mock data,
    ever.

Usage:
  python3 scripts/m3_build_datasets.py                # normal run
  python3 scripts/m3_build_datasets.py --with-vote-sft  # extension (off)
Output: data/m3/casefiles/*.json, data/m3/personas/<slug>/{train,test}.jsonl,
        data/m3/manifest.json
"""
import argparse
import glob
import gzip
import hashlib
import html
import json
import os
import re
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(REPO, "data", "processed")
OYEZ = os.path.join(REPO, "data", "sources", "oyez")
M3 = os.path.join(REPO, "data", "m3")
TEXTS = os.path.join(REPO, "data", "raw", "opinion_texts",
                     "opinions_text.jsonl.gz")

TRAIN_END = 2019
TEST_START = 2020

LA_CHAMBRE = ["JGRoberts", "CThomas", "SAAlito", "SSotomayor", "EKagan",
              "NMGorsuch", "BMKavanaugh", "ACBarrett", "KBJackson"]

PERSONA_SYSTEM = (
    "You are {name}, Associate Justice of the Supreme Court of the United "
    "States. You read the case file exactly as it was before the Court "
    "decided, and you write as yourself.")

CASEFILE_INSTRUCTION = (
    "CASE FILE — {title}\n"
    "Docket: {docket} | Term: OT{term} | Court below: {lower}\n"
    "Parties: {parties}\n"
    "Question presented: {question}\n"
    "Facts: {facts}\n"
    "Posture: {posture}\n")

VOTE_TASK = (
    "As {name}, state your vote direction on the question presented: "
    "conservative or liberal. Answer with exactly one word.")


# ------------------------------------------------------------------ utils --

def wilson(k, n, z=1.96):
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def nums(s):
    if not isinstance(s, str):
        return set()
    return set(re.findall(r"\d+-\d+", s.replace("–", "-").replace("—", "-")))


def strip_html(s):
    if not isinstance(s, str):
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def norm_docket(s):
    """Canonical docket key: 'No. 15–537.' and '15-537' collide on '15-537'."""
    if not isinstance(s, str):
        return ""
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = re.sub(r"\bno\.?\s*", "", s, flags=re.I)
    s = re.sub(r"[^0-9\-]", "", s)
    return s.strip("-.")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------- data --

def load_corpus():
    with gzip.open(os.path.join(PROC, "corpus_cases_v1.jsonl.gz"), "rt",
                   encoding="utf-8") as f:
        cases = [json.loads(line) for line in f]
    with gzip.open(os.path.join(PROC, "corpus_opinions_v1.jsonl.gz"), "rt",
                   encoding="utf-8") as f:
        opinions = [json.loads(line) for line in f]
    stats = json.load(open(os.path.join(PROC, "stats_v1.json"),
                           encoding="utf-8"))
    amap = json.load(open(os.path.join(M3, "author_map.json"),
                          encoding="utf-8"))
    return cases, opinions, stats, amap


def sealed_dockets(stats):
    raw = stats["five_four_selection"]["cases"]
    snums = set()
    for s in raw:
        snums |= nums(s)
    snorm = {s.strip().rstrip(".").replace("–", "-") for s in raw}
    def is_sealed(c):
        cd = c.get("docket_number") or c.get("docket") or ""
        return bool(nums(cd) & snums) or (cd in snorm) or (cd == "No.142")
    return is_sealed


def load_oyez():
    out = {}
    for path in glob.glob(os.path.join(OYEZ, "*.json")):
        if path.endswith(".miss.json"):
            continue
        try:
            d = json.load(open(path, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("docket_number"):
            out[norm_docket(d["docket_number"])] = d
    return out


def load_texts():
    """opinion_id -> plain_text, from M1.5 output (may be absent)."""
    if not os.path.exists(TEXTS):
        return None
    out = {}
    with gzip.open(TEXTS, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            oid = r.get("id") or r.get("opinion_id")
            t = r.get("plain_text") or r.get("text") or ""
            if oid and t:
                out[int(oid)] = t
    return out


# --------------------------------------------------------------- builders --

def build_casefile(c, oy):
    """PRE-DECISION case file. Never the outcome."""
    sc = c.get("scdb") or {}
    lower = ""
    if oy:
        lc = oy.get("lower_court") or {}
        lower = strip_html(lc.get("name") or "") or "not recorded"
    lower = lower or strip_html(str(sc.get("lc_disposition") or "")) \
        or "not recorded"
    parties = "v. ".join(
        p for p in [strip_html((oy or {}).get("first_party") or ""),
                    strip_html((oy or {}).get("second_party") or "")] if p
    ) or c.get("case_name", "unknown parties")
    if oy and oy.get("first_party_label"):
        parties += f" ({strip_html(oy['first_party_label'])} v. "
        parties += f"{strip_html(oy.get('second_party_label') or '')})"
    cf = {
        "docket": c["docket_number"],
        "case_name": c.get("case_name"),
        "term": int(c["term"]),
        "issue_area": sc.get("issue_area"),
        "lc_disposition": sc.get("lc_disposition"),
        "lower_court": lower,
        "parties": parties,
        "question": strip_html((oy or {}).get("question") or "")
        or "not available in Oyez (metadata-only case file)",
        "facts": strip_html((oy or {}).get("facts_of_the_case") or "")
        or "not available in Oyez (metadata-only case file)",
        "posture": strip_html((oy or {}).get("manner_of_jurisdiction") or ""),
        "sources": {"oyez": bool(oy), "scdb": bool(sc)},
    }
    cf["instruction"] = CASEFILE_INSTRUCTION.format(
        title=cf["case_name"], docket=cf["docket"], term=cf["term"],
        lower=cf["lower_court"], parties=cf["parties"],
        question=cf["question"][:1200], facts=cf["facts"][:4000],
        posture=cf["posture"] or "not recorded")
    return cf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-vote-sft", action="store_true",
                    help="extension: add vote-direction SFT rows "
                         "(default OFF — the pre-registered design trains "
                         "on written output only)")
    args = ap.parse_args()

    cases, opinions, stats, amap = load_corpus()
    is_sealed = sealed_dockets(stats)
    oyez = load_oyez()
    texts = load_texts()
    slug_of_aid = {int(k): v["slug"] for k, v in amap["mapping"].items()}
    # anomaly enforcement: Jackson's out-of-window docket
    outlawed_dockets = set()
    for ev in amap["mapping"].values():
        outlawed_dockets.update(ev.get("dockets_outside_service_window")
                                or [])

    cluster_to_docket = {}
    for c in cases:
        for cl in (c.get("cluster_ids") or []):
            cluster_to_docket[str(cl)] = c["docket_number"]
    docket_to_case = {c["docket_number"]: c for c in cases}

    # ---- case files (transparent windows only, sealed excluded) -----------
    cf_dir = os.path.join(M3, "casefiles")
    os.makedirs(cf_dir, exist_ok=True)
    n_train_cf = n_test_cf = n_oyez_train = n_oyez_test = 0
    for c in cases:
        if is_sealed(c):
            continue
        term = int(c["term"])
        oy = oyez.get(norm_docket(c["docket_number"]))
        cf = build_casefile(c, oy)
        window = "train" if term <= TRAIN_END else \
            ("test" if term >= TEST_START else None)
        if window is None:
            continue
        cf["window"] = window
        if window == "train":
            n_train_cf += 1
            n_oyez_train += int(bool(oy))
        else:
            n_test_cf += 1
            n_oyez_test += int(bool(oy))
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", c["docket_number"])[:80]
        with open(os.path.join(cf_dir, f"{safe}.json"), "w",
                  encoding="utf-8") as f:
            json.dump(cf, f, ensure_ascii=False, indent=1)

    # ---- persona datasets --------------------------------------------------
    persona_dir = os.path.join(M3, "personas")
    os.makedirs(persona_dir, exist_ok=True)
    manifest_personas = {}
    for slug in LA_CHAMBRE:
        name = next((j["justice_name"] for c in cases
                     for j in c.get("justices", []) if j["justice"] == slug),
                    slug)
        aid = next((a for a, s in slug_of_aid.items() if s == slug), None)
        train_rows, test_rows = [], []
        n_train_votes = n_test_votes = 0
        for o in opinions:
            if aid is None or o.get("author_id") != aid:
                continue
            dn = cluster_to_docket.get(str(o["cluster_id"]))
            c = docket_to_case.get(dn)
            if not c or is_sealed(c) or dn in outlawed_dockets:
                continue
            term = int(c["term"])
            window = "train" if term <= TRAIN_END else \
                ("test" if term >= TEST_START else None)
            text = (texts or {}).get(o["opinion_id"])
            if text:
                row = {
                    "opinion_id": o["opinion_id"],
                    "docket": dn,
                    "type": o["type"],
                    "date_filed": o.get("date_filed"),
                    "system": PERSONA_SYSTEM.format(name=name),
                    "instruction": CASEFILE_INSTRUCTION.format(
                        title=c.get("case_name"), docket=dn, term=term,
                        lower="record below",
                        parties=c.get("case_name"),
                        question="record below",
                        facts="record below",
                        posture="record below"),
                    "output": text,
                }
                if window == "train":
                    train_rows.append(row)
            # vote ground truth for the transparent eval (never a training
            # target under the pre-registered design)
            jj = next((j for j in c.get("justices", [])
                       if j["justice"] == slug), None)
            if jj and jj.get("direction") in ("1", "2"):
                rec = {"docket": dn, "term": term,
                       "direction": "liberal" if jj["direction"] == "2"
                       else "conservative"}
                if window == "test":
                    test_rows.append(rec)
                    n_test_votes += 1
                elif window == "train":
                    n_train_votes += 1
        pdir = os.path.join(persona_dir, slug)
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "train.jsonl"), "w",
                  encoding="utf-8") as f:
            for r in train_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        with open(os.path.join(pdir, "test_votes.jsonl"), "w",
                  encoding="utf-8") as f:
            for r in test_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        manifest_personas[slug] = {
            "name": name, "author_id": aid,
            "train_text_rows": len(train_rows),
            "train_votes_available": n_train_votes,
            "test_votes": len(test_rows),
            "service_note": ("OT2022-23 only — power report mandatory"
                             if slug == "KBJackson" else ""),
        }

    # ---- manifest ----------------------------------------------------------
    text_state = "present" if texts else "ABSENT (M1.5 not run since the " \
        "environment rebuild — run scripts/fetch_opinion_texts_batch.py)"
    manifest = {
        "file": "data/m3/manifest.json",
        "builder": "scripts/m3_build_datasets.py",
        "split": {"train": f"OT2015..OT{TRAIN_END}",
                  "test_transparent": f"OT{TEST_START}..OT2023",
                  "sealed": "excluded everywhere (M4 only)"},
        "case_files": {"train": n_train_cf, "test": n_test_cf,
                       "oyez_coverage_train": n_oyez_train,
                       "oyez_coverage_test": n_oyez_test,
                       "note": "case files without Oyez fall back to "
                               "metadata-only (flagged in sources.oyez)"},
        "opinion_texts": {"state": text_state,
                          "texts_available": len(texts or {})},
        "vote_sft_extension": ("enabled" if args.with_vote_sft
                               else "disabled (pre-registered default)"),
        "personas": manifest_personas,
        "total_opinions": len(opinions),
    }
    with open(os.path.join(M3, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"case files  : train {n_train_cf} (oyez {n_oyez_train}) | "
          f"test {n_test_cf} (oyez {n_oyez_test})")
    print(f"opinion text: {text_state}")
    for slug in LA_CHAMBRE:
        m = manifest_personas[slug]
        print(f"  {slug:13} train_text={m['train_text_rows']:4d} "
              f"train_votes={m['train_votes_available']:4d} "
              f"test_votes={m['test_votes']:4d} {m['service_note']}")
    print(f"\nwritten: {os.path.relpath(M3, REPO)}/ "
          f"(casefiles/, personas/, manifest.json)")


if __name__ == "__main__":
    sys.exit(main())
