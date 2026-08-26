#!/usr/bin/env python3
"""Legally Subjective — Module 2: the formatter.

Transforms raw opinions (HTML slip opinions collected by
fetch_courtlistener.py) into structured case records. Every extracted
field carries its evidence (the source sentence) and its method
(MANIFEST R8), so any number in the project can be traced back to the
official text.

Deterministic extraction (this script, no LLM):
  - panel of judges and presiding justice, from the concurrence line;
  - appellate disposition (rule: decretal "Ordered that..." formula,
    First-Department inline recital, or dismissal formula);
  - charge, from the "convicting ... of ..." recital;
  - trial judge(s), from the "(Name, J.)" recitals;
  - facts recital excerpt (raw, for human verification).

LLM enrichment (--llm, scripts/llm_extractor.py): factual summary masked
of the outcome, charge cross-check, crime type, and an independent
outcome_check that is compared with the rule-based label (agreement
field) — the cross-validation required by docs/protocol.md §2.2.

Usage:
    python scripts/preprocess.py [--config config.json] [--llm]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

SCHEMA = "legally-subjective/structured-case/0.1"
PIPELINE_VERSION = "0.1.0"

# --------------------------------------------------------------------------
# HTML → text (stdlib only; the official slip opinions are simple documents)
# --------------------------------------------------------------------------


class _TextExtractor(HTMLParser):
    """Collect visible text; block tags act as soft separators."""

    _BLOCKS = {"p", "br", "div", "tr", "td", "li", "h1", "h2", "h3", "h4",
               "table", "blockquote"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in self._BLOCKS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag in self._BLOCKS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


# --------------------------------------------------------------------------
# Field extractors — every result is {value(s), evidence, method}
# --------------------------------------------------------------------------

_PANEL_STOP = re.compile(r"(?i),?\s*concur\.?\s*$")
_PANEL_SPLIT = re.compile(r",\s*|\s+and\s+")
_JP = "J.P."

_AUTHOR_RX = re.compile(
    r"\b(?P<name>[A-Z][A-Za-z.'\-]+(?: [A-Za-z.'\-]+){0,3})"
    r", (?P<role>P\.J\.|J\.)\s+(?=[A-Z])")


def _extract_author(text: str) -> dict[str, Any] | None:
    """Leading signature, e.g. 'Garry, P.J.' / 'Devine, J.' — Third
    Department slip opinions open with the writing justice."""
    m = _AUTHOR_RX.search(text[:900])
    if not m:
        return None
    return {"name": m.group("name").strip(),
            "role": ("author-presiding" if m.group("role") == "P.J."
                     else "author"),
            "evidence": m.group(0)}


def _last_sentence_of(window: str) -> str:
    """Last sentence of the window, protecting 'J.P.' from splitting."""
    protected = window.replace("J.P.", "\x00JP\x00")
    parts = protected.split(". ")
    return parts[-1].replace("\x00JP\x00", "J.P.")


def extract_panel(text: str) -> dict[str, Any]:
    """Judges from the concurrence line, merged with the leading author
    signature when there is one. Examples:

        "Leventhal, J.P., Cohen, Miller and Connolly, JJ., concur."
        "Concur—Tom, J.P., Mazzarelli, Richter and Gische, JJ."
        "Garry, P.J." (author) + "Lynch, Clark, Aarons and Pritzker, JJ."

    The LAST occurrence of "JJ." in the document is used: slip opinions
    list the concurring panel exactly once, at the end. Third/Fourth
    Department opinions additionally open with the writing justice.
    """
    evidence_parts: list[str] = []
    names: list[dict[str, Any]] = []
    presiding: str | None = None

    author = _extract_author(text)
    if author:
        names.append({"name": author["name"], "role": author["role"]})
        if author["role"] == "author-presiding":
            presiding = author["name"]
        evidence_parts.append(author["evidence"])

    matches = list(re.finditer(r"\bJJ\.", text))
    if matches:
        last = matches[-1]
        window = text[max(0, last.start() - 200):last.start()]
        segment = _last_sentence_of(window)
        segment = re.sub(r"(?i)^[\s—–-]*concur[\s—–-]+", "", segment)
        segment = _PANEL_STOP.sub("", segment).strip(" ,.")
        tokens = [t.strip(" ,.") for t in _PANEL_SPLIT.split(segment)]
        for idx, token in enumerate(tokens):
            if not 2 <= len(token) <= 40:
                continue
            if not re.fullmatch(r"[A-Z][A-Za-z.'\- ]*", token):
                continue  # refuse garbage tokens rather than guess
            if token in ("JJ", "J"):
                continue
            if token in ("J.P", "J.P."):
                # presiding marker attaches to the preceding name
                for n in reversed(names):
                    if n["name"] == tokens[idx - 1].strip(" ,."):
                        n["role"] = "presiding"
                        if presiding is None:
                            presiding = n["name"]
                        break
                continue
            entry = {"name": token, "role": "panel"}
            if entry["name"] and not any(n["name"] == entry["name"]
                                         for n in names):
                names.append(entry)
        evidence_parts.append(segment + " JJ.")

    method = "regex:author-signature+concur-line"
    if not names:
        return {"judges": [], "presiding": None, "evidence": None,
                "method": method, "note": "no panel markers found"}
    return {"judges": names, "presiding": presiding,
            "evidence": " | ".join(p for p in evidence_parts if p),
            "method": method}


_VERB_NORMALIZE = {
    "affirm": "affirmed", "affirmed": "affirmed",
    "reverse": "reversed", "reversed": "reversed",
    "vacate": "vacated", "vacated": "vacated",
    "modify": "modified", "modified": "modified",
    "dismiss": "dismissed", "dismissed": "dismissed",
    "remit": "remitted", "remitted": "remitted",
}

_DISPOSITION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # decretal (2d/3d Dept): "Ordered that the judgment is reversed, ..."
    ("decretal", re.compile(
        r"(?i)\bOrdered that the (?P<subj>judgment|order|appeal[^,.]{0,90}?|"
        r"indictment|matter|decision)[^.]{0,150}?\b"
        r"(?:is|be|are) (?P<verb>affirmed|reversed|vacated|modified|"
        r"dismissed|remitted)")),
    # inline recital (1st Dept): "Judgment, Supreme Court, ... ,
    # unanimously affirmed." (periods allowed inside — the recital
    # contains 'J.' markers)
    ("inline-recital", re.compile(
        r"(?i)\b(?P<subj>Judgment|Order), .{10,420}?(?:unanimously )?"
        r"(?P<verb>affirmed|reversed|vacated|modified)(?=[.,;])")),
    # prose disposition: "The judgment is therefore affirmed"
    ("prose-disposition", re.compile(
        r"(?i)\bthe (?P<subj>judgment|order|conviction|sentence)\b"
        r"[^.]{0,60}?\b(?:is|was|are|be) [a-z ]{0,20}?"
        r"(?P<verb>affirmed|reversed|vacated|modified)(?=[.,;])")),
    # dismissal formula: "the appeal ... is academic, and must be dismissed"
    ("dismissal", re.compile(
        r"(?i)\bthe (?P<subj>appeal[^,.]{0,100}?)[^.]{0,90}?"
        r"(?:is|are|must be) (?P<verb>dismissed)")),
    # "we affirm/reverse/..." — opinions that reason in the first person
    ("first-person", re.compile(
        r"(?i)\bwe (?P<verb>affirm|reverse|vacate|modify|dismiss)\b"
        r"(?P<subj>)")),
]

_SUBJECT_CLASS = [
    ("judgment", re.compile(r"(?i)^\s*judgment\b|^$")),
    ("order", re.compile(r"(?i)^\s*order\b")),
    ("appeal", re.compile(r"(?i)^\s*appeal")),
]
_SUBJECT_PRIORITY = {"judgment": 0, "": 1, "order": 2, "appeal": 3,
                     "other": 4}
_METHOD_PRIORITY = {"rule:decretal": 0, "rule:inline-recital": 1,
                    "rule:prose-disposition": 2, "rule:dismissal": 3,
                    "rule:first-person": 4}

_BINARY_MAP = {"affirmed": "affirmed",
               "reversed": "reversed_vacated",
               "vacated": "reversed_vacated"}


def _classify_subject(subj: str) -> str:
    subj = (subj or "").strip()
    for label, rx in _SUBJECT_CLASS:
        if label and rx.search(subj):
            return label
    return "other" if subj else ""


def _sentence_around(text: str, start: int, end: int) -> str:
    left = text.rfind(".", 0, start)
    left = 0 if left == -1 else left + 1
    right = text.find(".", end)
    right = len(text) if right == -1 else right + 1
    return text[left:right].strip()


def extract_disposition(text: str) -> dict[str, Any]:
    """All disposition statements, then the primary one.

    Priority: the disposition attached to 'the judgment' wins (that is the
    object of the appeal); an 'order' or 'appeal' disposition is recorded
    but does not override it. 'modified' is kept out of the binary label
    (neither a clean affirmance nor a clean reversal).
    """
    found: list[dict[str, Any]] = []
    for method, rx in _DISPOSITION_PATTERNS:
        for m in rx.finditer(text):
            verb = _VERB_NORMALIZE[m.group("verb").lower()]
            subj = (m.groupdict().get("subj") or "").strip()
            attached = _classify_subject(subj)
            sentence = _sentence_around(text, m.start(), m.end())
            # guard: skip citations — "see People v X, ... affirmed"
            rel = sentence.find(m.group("verb"))
            before = sentence[:rel] if rel >= 0 else sentence
            if re.search(r"(?i)\b(see|citing|cf\.)\b", before):
                continue
            found.append({
                "value": verb,
                "attached_to": attached,
                "method": f"rule:{method}",
                "evidence": sentence,
                "position": m.start(),
            })
    # de-duplicate identical evidence sentences
    seen: set[str] = set()
    unique = []
    for f in sorted(found, key=lambda x: x["position"]):
        key = f["evidence"]
        if key not in seen:
            seen.add(key)
            unique.append(f)
    if not unique:
        return {"primary": None, "binary": None, "binary_eligible": False,
                "all": [], "method": "rule:disposition-patterns",
                "note": "no disposition formula matched — manual review"}

    best = min(unique, key=lambda f: (_SUBJECT_PRIORITY[f["attached_to"]],
                                      _METHOD_PRIORITY.get(f["method"], 9),
                                      f["position"]))
    primary = best["value"]
    binary = _BINARY_MAP.get(primary)
    distinct = sorted({f["value"] for f in unique})
    return {
        "primary": primary,
        "primary_evidence": best["evidence"],
        "primary_method": best["method"],
        "binary": binary,
        "binary_eligible": binary is not None,
        "values_found": distinct,
        "all": [{k: v for k, v in f.items() if k != "position"}
                for f in unique],
        "method": "rule:disposition-patterns",
    }


_CHARGE_RX = re.compile(
    r"(?i)convicting (?:him|her|the defendant|defendant)"
    r"(?: upon (?:his|her) plea of guilty)? of (?:the )?(?:crimes? of )?"
    r"(?P<charge>[^.]{5,240}?)"
    r"(?=, (?:upon|and sentencing|as a|after|following|and|dated|by)|\.)")


def extract_charge(text: str) -> dict[str, Any]:
    m = _CHARGE_RX.search(text)
    if not m:
        return {"value": None, "evidence": None,
                "method": "regex:convicting-of",
                "note": "no 'convicting ... of' recital — see LLM fields"}
    return {"value": m.group("charge").strip(),
            "evidence": _sentence_around(text, m.start(), m.end()),
            "method": "regex:convicting-of"}


_TRIAL_JUDGE_RX = re.compile(
    r"\b(?P<name>[A-Z][A-Za-z.'\-]+(?: [A-Za-z.'\-]+){0,3}), J\.")


def extract_trial_judges(text: str, exclude: set[str] | None = None) -> dict[str, Any]:
    """Trial-court judges from the '(Name, J.)' recitals in the opening
    procedural section (first 60% of the opinion). The appellate author
    signature (e.g. 'Devine, J.') is excluded so it is not mistaken for
    a trial judge."""
    exclude = exclude or set()
    judges: list[str] = []
    evidences: list[str] = []
    zone = text[: int(len(text) * 0.6) + 1]
    for m in _TRIAL_JUDGE_RX.finditer(zone):
        name = m.group("name").strip()
        if not name or name in judges or name in exclude:
            continue
        judges.append(name)
        evidences.append(_sentence_around(text, m.start(), m.end()))
    return {"judges": judges, "evidence": "; ".join(evidences) or None,
            "method": "regex:(name, J.)-recital"}


_FACTS_ANCHORS = re.compile(
    r"(?i)(Appeal by the defendant from|Judgment, Supreme Court|"
    r"Order, Supreme Court|The defendant (?:was )?convicted|"
    r"Defendant moves|motion pursuant to)")


def extract_facts_excerpt(text: str, length: int = 900) -> dict[str, Any]:
    m = _FACTS_ANCHORS.search(text)
    if not m:
        return {"value": None, "evidence": None,
                "method": "regex:recital-anchor",
                "note": "no factual recital anchor found"}
    excerpt = text[m.start():m.start() + length].strip()
    return {"value": excerpt, "anchor": m.group(0),
            "method": "regex:recital-anchor"}


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------

def build_record(raw: dict[str, Any], text: str,
                 llm_fields: dict[str, Any] | None,
                 llm_backend: str | None) -> dict[str, Any]:
    panel = extract_panel(text)
    disposition = extract_disposition(text)
    charge = extract_charge(text)
    author_names = {j["name"] for j in panel["judges"]}
    trial = extract_trial_judges(text, exclude=author_names)
    facts = extract_facts_excerpt(text)

    if llm_fields:
        rule_value = disposition.get("primary")
        llm_value = llm_fields.get("outcome_check")
        disposition["llm_check"] = llm_value
        disposition["agreement"] = (
            None if rule_value is None or llm_value is None
            else rule_value == llm_value)

    return {
        "case_id": f"{raw['court_id']}-{raw['cluster_id']}",
        "case_name": raw["case_name"],
        "court": {"id": raw["court_id"], "name": raw["court"]},
        "date_filed": raw["date_filed"],
        "docket_number": raw["docket_number"],
        "citations": raw["citations"],
        "window": raw["window"],
        "panel": panel,
        "trial_judges": trial,
        "charge": charge,
        "facts": {
            "recital_excerpt": facts,
            "summary": (llm_fields or {}).get("facts"),
        },
        "crime_type": {
            "value": (llm_fields or {}).get("crime_type"),
            "method": "llm" if llm_fields else "not_extracted",
        },
        "defendant_gender": {
            "value": (llm_fields or {}).get("defendant_gender"),
            "method": "llm" if llm_fields else "not_extracted",
        },
        "disposition": disposition,
        "provenance": {
            "courtlistener_url": raw["courtlistener_url"],
            "official_source_url": raw["official_source_url"],
            "document_channel": raw["document_channel"],
            "document_url_used": raw["document_url_used"],
            "document_sha256": raw["document_sha256"],
            "document_bytes": raw["document_bytes"],
            "fetched_at": raw["fetched_at"],
            "criminal_gate": raw["criminal_gate"],
        },
        "extraction": {
            "schema": SCHEMA,
            "pipeline_version": PIPELINE_VERSION,
            "extracted_at":
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "llm_backend": llm_backend,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--llm", action="store_true",
                        help="enrich with an LLM backend (requires "
                             "LLM_API_KEY, see .env.example)")
    parser.add_argument("--llm-fields-file", default=None,
                        help="inject LLM fields computed offline (JSON: "
                             "{backend, fields: {case_id: {...}}}); the "
                             "same frozen prompt as llm_extractor.py "
                             "must have been used")
    parser.add_argument("--dump-texts", default=None,
                        help="write {case_id: text} JSON to this path and "
                             "exit (for offline LLM runs)")
    args = parser.parse_args()

    cfg = json.loads((REPO_ROOT / args.config).read_text(encoding="utf-8"))
    pre = cfg["preprocess"]
    input_path = REPO_ROOT / cfg["paths"]["cases_jsonl"]
    output_path = REPO_ROOT / pre["structured_jsonl"]
    max_chars = int(pre.get("max_text_chars", 9000))

    raw_cases = [json.loads(line) for line in
                 input_path.open(encoding="utf-8")]

    if args.dump_texts:
        dump = {}
        for raw in raw_cases:
            if raw.get("document_format") != "html":
                continue
            doc_path = REPO_ROOT / raw["document_path"]
            dump[f"{raw['court_id']}-{raw['cluster_id']}"] = html_to_text(
                doc_path.read_text(encoding="utf-8", errors="ignore"))
        Path(args.dump_texts).write_text(
            json.dumps(dump, ensure_ascii=False), encoding="utf-8")
        print(f"dumped {len(dump)} case texts → {args.dump_texts}")
        return 0

    offline_fields: dict[str, Any] = {}
    offline_backend = None
    if args.llm_fields_file:
        payload = json.loads(
            Path(args.llm_fields_file).read_text(encoding="utf-8"))
        offline_fields = payload.get("fields", {})
        offline_backend = payload.get("backend", "llm-fields-file")

    extractor = None
    llm_backend = None
    if args.llm:
        from llm_extractor import LLMExtractor
        extractor = LLMExtractor(pre["llm"])
        llm_backend = extractor.backend_name

    records: list[dict[str, Any]] = []
    for raw in raw_cases:
        case_id = f"{raw['court_id']}-{raw['cluster_id']}"
        if raw.get("document_format") != "html":
            print(f"  ! {raw['case_name']}: document is "
                  f"{raw.get('document_format')} — deterministic "
                  f"extraction needs HTML; skipping LLM fields")
            text = ""
        else:
            text = html_to_text(
                (REPO_ROOT / raw["document_path"]).read_text(
                    encoding="utf-8", errors="ignore"))
        llm_fields = None
        if extractor and text:
            print(f"  extracting LLM fields: {raw['case_name']}")
            llm_fields = extractor.extract(text, max_chars)
        elif case_id in offline_fields:
            llm_fields = offline_fields[case_id]
            llm_backend = offline_backend
        record = build_record(raw, text, llm_fields, llm_backend)
        if not text:
            record["extraction"]["note"] = (
                "deterministic fields unavailable (non-HTML document)")
        records.append(record)
        disp = record["disposition"].get("primary")
        print(f"  → {raw['case_name']}: disposition={disp}, "
              f"panel={len(record['panel']['judges'])} judges")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"\nwrote {len(records)} structured records → {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
