#!/usr/bin/env python3
"""MANHATTAN Phase 1 — build the A/B dataset (facts in, verdict out).

Reads the structured corpus restored in phase1/ (1,387 real NY Appellate
Division criminal appeals, 2015-2023, collected from CourtListener) and
produces the training/test JSONL for the Model A vs Model B experiment
(Etage 1 of the Manhattan roadmap).

Deterministic rules (seed 20260827, zero fabrication):

  INPUT TEXT — "the case as seen before the order":
    R1  decretal cut     — text stops at the first "Ordered that" (the
                           verdict paragraph is removed entirely);
    R2  panel strip      — the appellate panel line (evidence string from
                           the golden-tested pipeline) is removed: Etage 1
                           is judge-agnostic, panels belong to Etage 2;
    R3  outcome strip    — inline verdict phrases ("unanimously affirmed",
                           "is reversed", trailing ", affirmed.") removed;
    R4  leak gate        — a text that still contains any verdict word
                           (affirmed/reversed/vacated/modified/dismissed)
                           EXCLUDES the case. Zero leakage by construction,
                           verified, counted, reported;
    R5  length gate      — sanitized text >= 200 chars, else excluded.

  LABEL      — disposition.binary from the golden-tested pipeline
               (affirmed vs reversed_vacated). Never re-derived here.
  STRATA     — crime_category (deterministic keyword map on charge.value)
               x verdict x window, proportional largest-remainder.
  SPLIT      — 600 train / 400 test if the clean pool allows, else 60/40
               of everything. Seeded, reproducible bit-for-bit.

Outputs:
    phase1/dataset/train.jsonl
    phase1/dataset/test.jsonl
    phase1/dataset/split_report.json
"""
from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PHASE1 = REPO / "phase1"
sys.path.insert(0, str(PHASE1 / "scripts"))
import preprocess  # noqa: E402  (golden-tested pipeline: html_to_text)

SEED = 20260827
STRUCTURED = PHASE1 / "data/structured/corpus_structured.jsonl"
OUT_DIR = PHASE1 / "dataset"

VERDICT_WORDS = re.compile(
    r"\b(affirmed|reversed|vacated|modified|dismissed)\b", re.IGNORECASE)
DECRETAL = re.compile(r"\bOrdered that\b", re.IGNORECASE)

# R3 — inline outcome phrases (documented, order matters)
OUTCOME_PATTERNS = [
    re.compile(r",?\s*unanimously\s+(?:affirmed|reversed|modified|vacated)"
               r"\b\s*\.?", re.IGNORECASE),
    re.compile(r"\b(?:is|are)\s+(?:hereby\s+)?"
               r"(?:affirmed|reversed|vacated|modified|dismissed)\b"
               r"[^.]*\.?", re.IGNORECASE),
    re.compile(r",\s*(?:affirmed|reversed|vacated|modified|dismissed)\.",
               re.IGNORECASE),
]

# crime_category — deterministic keyword map on charge.value
CRIME_RULES: list[tuple[str, re.Pattern]] = [
    ("drug", re.compile(
        r"controlled substance|cocaine|heroin|marijuana|methadone|"
        r"fentanyl|narcotic|methamphetamine", re.IGNORECASE)),
    ("weapon", re.compile(
        r"weapon|firearm|gun|pistol|rifle|shotgun|ammunition|dirk|dagger",
        re.IGNORECASE)),
    ("violent", re.compile(
        r"murder|manslaughter|assault|robbery|strangulation|kidnapping|"
        r"rape|sexual abuse|sodomy|sexually|abus", re.IGNORECASE)),
    ("property", re.compile(
        r"burglary|larceny|theft|stolen|mischief|arson|forgery|fraud|"
        r"identity|criminal possession of stolen|criminal mischief|"
        r"criminal trespass|falsifying", re.IGNORECASE)),
]


# R2b — the Third/Fourth Department concur line closing the opinion:
# "Aarons, J.P., Pritzker, Ceresia, Fisher and Mackey, JJ., concur."
CONCUR_LINE = re.compile(
    r"(?:[A-Z][A-Za-z'\._\-]+(?:\s+Jr\.?)?"
    r"(?:,?\s*(?:J\.P\.|P\.J\.|J\.))?"
    r"(?:\s*,\s*|\s+and\s+|\s+))+"
    r"[A-Z][A-Za-z'\._\-]+(?:\s+Jr\.?)?"
    r"(?:,?\s*(?:J\.P\.|P\.J\.|J\.))?"
    r",?\s*JJ\.,?\s*concur\.?")


def _panel_names(judge_names: list[str]) -> list[str]:
    """Drop extractor artifacts ('P.J', 'J.') from the name list."""
    return [n for n in judge_names
            if n and len(n) >= 3 and not re.fullmatch(r"[JP]\.?J?\.?", n)]


def crime_category(charge: str | None) -> str:
    if not charge:
        return "unstated"
    for name, rx in CRIME_RULES:
        if rx.search(charge):
            return name
    return "other"


def strip_panel(text: str, judge_names: list[str]) -> tuple[str, bool]:
    """Remove the appellate panel block from the header region.

    The structured record gives the panel surnames (reliably extracted,
    golden-tested). The panel line sits in the header (first 2000 chars):
    either "Surname, J.P., Surname, Surname, JJ." (1st/3d/4th Dept) or
    "FULL CAPS NAMES with J.P./JJ. markers" (2d Dept). We locate the
    densest cluster of panel surnames within a bounded window and cut it,
    then remove any standalone "Surname, P.J./J." signature left behind.
    """
    if not judge_names:
        return text, False
    region = text[:2000]
    names = [n for n in judge_names if n]

    # occurrences (start, end, name) of each surname in the header region
    occ: list[tuple[int, int, str]] = []
    for name in names:
        for m in re.finditer(rf"\b{re.escape(name)}\b", region):
            occ.append((m.start(), m.end(), name))
    if len({n for _, _, n in occ}) < 2:
        return text, False

    # densest cluster: most distinct names within a <=350 char window
    occ.sort()
    best_span, best_count = None, 0
    for i, (start, _, _) in enumerate(occ):
        covered = {occ[j][2] for j in range(i, len(occ))
                   if occ[j][0] - start <= 350}
        if len(covered) > best_count:
            best_count = len(covered)
            best_span = (start, start + 350)
    if best_span is None or best_count < 2:
        return text, False

    cluster = [o for o in occ if best_span[0] <= o[0] < best_span[1]]
    cut_start = min(o[0] for o in cluster)
    cut_end = max(o[1] for o in cluster)
    # swallow trailing markers: ", JJ." / ", J." / "concur." + initials
    tail_m = re.match(
        r"(?:[A-Za-z'\.\- ]{0,20}?(?:,?\s*JJ?\.|concur\.?))",
        text[cut_end:cut_end + 45])
    if tail_m:
        cut_end += tail_m.end()
    # swallow a leading first-name run before the first surname
    # ("BETSY BARROS" -> cut starts at BETSY, not BARROS)
    head_m = re.search(r"[A-Z][A-Za-z'\.\- ]{0,20}$", text[:cut_start])
    if head_m and "," not in head_m.group(0):
        cut_start = head_m.start()

    stripped = text[:cut_start] + " " + text[cut_end:]

    # remove standalone signatures of remaining panel names
    for name in names:
        stripped = re.sub(
            rf"\b{re.escape(name)},?\s*(?:P\.J\.|J\.P\.|JJ\.|J\.)\b", " ",
            stripped)
    return re.sub(r"\s+", " ", stripped).strip(), True


def sanitize(text: str, panel_judges: list[str]) -> tuple[str, bool]:
    """R1-R3. Returns the pre-order view of the case (panel stripped)."""
    m = DECRETAL.search(text)
    if m:
        text = text[:m.start()]
    names = _panel_names(panel_judges)
    text = CONCUR_LINE.sub(" ", text)          # R2b: closing concur line
    text, panel_stripped = strip_panel(text, names)  # R2: header block
    for rx in OUTCOME_PATTERNS:
        text = rx.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip(), panel_stripped


def largest_remainder(total: int, weights: dict[str, int]) -> dict[str, int]:
    """Proportional integer allocation summing exactly to `total`."""
    s = sum(weights.values())
    if s == 0 or total == 0:
        return {k: 0 for k in weights}
    raw = {k: total * v / s for k, v in weights.items()}
    alloc = {k: int(v) for k, v in raw.items()}
    rest = total - sum(alloc.values())
    order = sorted(weights, key=lambda k: (-(raw[k] - alloc[k]), k))
    for k in order[:rest]:
        alloc[k] += 1
    return alloc


def main() -> int:
    records = [json.loads(l) for l in
               STRUCTURED.open(encoding="utf-8")]
    print(f"structured corpus: {len(records)} records")

    stages: dict[str, int] = {"structured": len(records)}
    reasons: Counter = Counter()

    pool = []
    panel_strip_hits = 0
    panel_resid = 0
    for r in records:
        disp = r["disposition"]
        if not disp.get("binary_eligible"):
            reasons["not_binary_eligible"] += 1
            continue
        cid = r["case_id"].split("-", 1)[1]
        doc = PHASE1 / "data/corpus/documents" / f"{cid}.html"
        if not doc.exists():
            reasons["document_missing"] += 1
            continue
        text = preprocess.html_to_text(
            doc.read_text(encoding="utf-8", errors="replace"))
        panel_names = [j.get("name") for j in
                       ((r.get("panel") or {}).get("judges") or [])]
        clean, panel_stripped = sanitize(text, panel_names)
        if panel_stripped:
            panel_strip_hits += 1
        check_names = _panel_names(panel_names)
        resid = sum(1 for n in check_names
                    if n and re.search(rf"\b{re.escape(n)}\b", clean))
        if resid >= 2:
            panel_resid += 1
        if len(clean) < 200:
            reasons["too_short_after_sanitize"] += 1
            continue
        if VERDICT_WORDS.search(clean):
            reasons["leak_gate_residual_verdict_word"] += 1
            continue
        charge = (r.get("charge") or {}).get("value")
        pool.append({
            "case_id": r["case_id"],
            "case_name": r.get("case_name"),
            "court": (r.get("court") or {}).get("name"),
            "date_filed": r.get("date_filed"),
            "window": r.get("window"),
            "verdict": disp["binary"],
            "charge": charge,
            "crime_category": crime_category(charge),
            "panel_judges": panel_names,
            "text": clean,
            "text_chars": len(clean),
            "provenance": {
                "courtlistener_url": (r["provenance"]
                                      .get("courtlistener_url")),
                "document_sha256": (r["provenance"]
                                    .get("document_sha256")),
                "document_bytes": (r["provenance"].get("document_bytes")),
                "fetched_at": (r["provenance"].get("fetched_at")),
            },
        })
    stages["clean_pool"] = len(pool)
    print(f"clean pool (leak-gate + length-gate passed): {len(pool)}")
    for k, v in reasons.most_common():
        print(f"  excluded[{k}]: {v}")

    # ---- stratified selection ----
    strata: dict[tuple, list[dict]] = defaultdict(list)
    for rec in pool:
        strata_key = (rec["crime_category"], rec["verdict"], rec["window"])
        strata[strata_key].append(rec)

    target = min(1000, len(pool))
    n_train = (target * 3) // 5 if target == 1000 else (target * 3) // 5
    n_test = target - n_train
    weights = {k: len(v) for k, v in strata.items()}
    take = largest_remainder(target, weights)
    train_take = largest_remainder(n_train, weights)  # <= take per stratum

    rng = random.Random(SEED)
    train, test = [], []
    overflow = []
    for key in sorted(strata):
        members = sorted(strata[key], key=lambda r: r["case_id"])
        idx = list(range(len(members)))
        rng.shuffle(idx)
        picked = [members[i] for i in idx[:take[key]]]
        ntr = min(train_take[key], len(picked))
        train.extend(picked[:ntr])
        overflow.extend(picked[ntr:])
    # distribute the remainder deterministically to hit exact 600/400
    overflow.sort(key=lambda r: r["case_id"])
    need_train = n_train - len(train)
    train.extend(overflow[:need_train])
    test.extend(overflow[need_train:])
    assert len(train) == n_train and len(test) == n_test, \
        (len(train), len(test), n_train, n_test)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train", train), ("test", test)):
        rows = sorted(rows, key=lambda r: r["case_id"])
        with (OUT_DIR / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for rec in rows:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"{name}.jsonl: {len(rows)} records")

    # ---- report ----
    def dist(rows, field):
        return dict(sorted(Counter(r[field] for r in rows).items()))

    lens = sorted(r["text_chars"] for r in train + test)
    report = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": SEED,
        "source": {
            "structured_corpus": str(STRUCTURED.relative_to(REPO)),
            "records": len(records),
            "lineage": "restored from origin/archive/pre-rebuild "
                       "(collected 2026-08-26, CourtListener v4 + NY Law "
                       "Reporting Bureau slip opinions)",
        },
        "stages": stages,
        "exclusion_reasons": dict(reasons.most_common()),
        "rules": {
            "R1_decretal_cut": "text stops at first 'Ordered that'",
            "R2_panel_strip": "panel removed two ways: header block "
                              "cluster (R2) + closing concur line (R2b); "
                              "measured effectiveness in "
                              "panel_verification",
            "R3_outcome_strip": "inline verdict phrases removed",
            "R4_leak_gate": "any residual verdict word excludes the case "
                            "(zero leakage by construction)",
            "R5_length_gate": "sanitized text >= 200 chars",
            "crime_rules": {name: rx.pattern for name, rx in CRIME_RULES},
        },
        "split": {"train": len(train), "test": len(test),
                  "target": target},
        "verdict_balance": {
            "train": dist(train, "verdict"), "test": dist(test, "verdict"),
            "pool": dist(pool, "verdict")},
        "crime_categories": {
            "train": dist(train, "crime_category"),
            "test": dist(test, "crime_category"),
            "pool": dist(pool, "crime_category")},
        "windows": {"train": dist(train, "window"),
                    "test": dist(test, "window")},
        "text_chars": {"min": lens[0], "median": lens[len(lens) // 2],
                       "max": lens[-1]},
        "leak_verification": {
            "method": "regex scan of every shipped text for "
                      "affirmed|reversed|vacated|modified|dismissed",
            "train_hits": sum(1 for r in train
                              if VERDICT_WORDS.search(r["text"])),
            "test_hits": sum(1 for r in test
                             if VERDICT_WORDS.search(r["text"]))},
        "panel_verification": {
            "panel_stripped": panel_strip_hits,
            "pool": stages["clean_pool"],
            "texts_with_2plus_panel_names_remaining": panel_resid,
            "note": "panel identity stays as metadata for Etage 2; the "
                    "strip keeps Etage 1 inputs judge-agnostic",
        },
    }
    (OUT_DIR / "split_report.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"split_report.json written")
    print(f"verdict balance train: {dist(train, 'verdict')}")
    print(f"verdict balance test : {dist(test, 'verdict')}")
    print(f"crime categories     : {dist(train + test, 'crime_category')}")
    print(f"leak verification    : "
          f"{report['leak_verification']['train_hits']} train / "
          f"{report['leak_verification']['test_hits']} test hits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
