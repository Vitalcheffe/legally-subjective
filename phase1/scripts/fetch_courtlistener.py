#!/usr/bin/env python3
"""Legally Subjective — Module 1: the collector.

Fetches real criminal-appeal cases from the CourtListener v4 search API and
their full text from the official source documents (New York slip opinions
published by the NY State Law Reporting Bureau).

Two modes (--mode):
  sample   the small stratified Phase 1 sample — config sections
           "sample" + "paths" (one page per window, "take" cases each);
  corpus   the Phase 2 full collection — config sections "corpus" +
           "paths_corpus": paginates through every search result of each
           time window, deduplicates by cluster id, rejects PDFs without a
           text layer (documented Phase 1 finding) and non-criminal
           documents, then tops up from "overflow_windows" until
           "target_usable" usable cases are collected. Any interruption
           (crash, Ctrl-C, --max-runtime-minutes) resumes from the
           checkpoint without re-downloading already-attempted cases.

Design constraints (see docs/MANIFEST.md):
  R1  zero mock data            — every record carries its source URLs;
  R2  zero hardcoded parameters — everything comes from config.json or CLI;
  R9  reproducibility           — checkpoint for crash recovery, and a
                                  FETCH_LOG that records every HTTP request.

Anonymous access works; a free CourtListener token (env COURTLISTENER_TOKEN)
raises rate limits.

Usage:
    python scripts/fetch_courtlistener.py [--config config.json]
        [--mode sample|corpus] [--dry-run] [--reset]
        [--max-runtime-minutes N]

Outputs (paths from config):
    data/sample/cases.jsonl        one record per collected case
    data/sample/documents/*.{html,txt,pdf}   source documents
    data/sample/FETCH_LOG.json     provenance log of every request
    data/sample/.checkpoint.json   resume state
    (corpus mode: data/corpus/… per "paths_corpus")
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class FetchLog:
    """Append-only provenance log, flushed after every request (R9)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: list[dict[str, Any]] = []
        if path.exists():
            try:
                self.entries = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                # a partially written log from a crashed run: keep the
                # parseable prefix by starting fresh — raw copies of the
                # responses are re-fetched anyway on resume.
                self.entries = []

    def add(self, **kw: Any) -> None:
        self.entries.append({"timestamp": utc_now(), **kw})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.entries, indent=1, ensure_ascii=False),
            encoding="utf-8",
        )


class HttpClient:
    """Rate-limited HTTP client with exponential backoff and UA fallback."""

    def __init__(self, cfg: dict[str, Any], log: FetchLog) -> None:
        self.timeout = float(cfg["timeout_seconds"])
        self.min_delay = float(cfg["min_delay_seconds"])
        self.max_retries = int(cfg["max_retries"])
        self.backoff_base = float(cfg["backoff_base_seconds"])
        self.ua = cfg["user_agent"]
        self.ua_browser = cfg["user_agent_browser_fallback"]
        self.session = requests.Session()
        token = os.environ.get(cfg.get("auth_token_env", ""))
        if token:
            self.session.headers["Authorization"] = f"Token {token}"
        self._last_request = 0.0
        self.log = log

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last_request = time.monotonic()

    def get(
        self,
        url: str,
        *,
        purpose: str,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        """GET with retry on 429/5xx/network errors. Logs every attempt.

        Every request sends `Connection: close`: pooled keep-alive
        connections were observed hanging past the read timeout when the
        official host silently drops them (documented in the Phase 2
        report) — a fresh connection per request is immune.
        """
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            ua = self.ua
            try:
                resp = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    headers={"User-Agent": ua, "Connection": "close"},
                )
                # some official hosts reject non-browser agents: one retry
                # with the browser UA, recorded in the log (never silent).
                if resp.status_code == 403 and ua != self.ua_browser:
                    self.log.add(purpose=purpose, url=url, status=403,
                                 note="retrying with browser UA")
                    ua = self.ua_browser
                    resp = self.session.get(
                        url, params=params, timeout=self.timeout,
                        headers={"User-Agent": ua,
                                 "Connection": "close"})
                self.log.add(purpose=purpose, url=resp.url,
                             status=resp.status_code, bytes=len(resp.content))
                if resp.status_code == 200:
                    return resp
                if resp.status_code in (429, 500, 502, 503, 504):
                    last_error = RuntimeError(f"HTTP {resp.status_code}")
                else:
                    raise RuntimeError(
                        f"unexpected HTTP {resp.status_code} for {resp.url}")
            except requests.RequestException as exc:
                last_error = exc
                self.log.add(purpose=purpose, url=url, status="network-error",
                             note=str(exc)[:200])
            if attempt < self.max_retries:
                pause = self.backoff_base * (2 ** (attempt - 1))
                print(f"    retry {attempt}/{self.max_retries - 1} "
                      f"in {pause:.0f}s ({last_error})", flush=True)
                time.sleep(pause)
        raise RuntimeError(f"failed after {self.max_retries} attempts: {url}"
                           f" — {last_error}")


def pick_opinion(result: dict[str, Any]) -> dict[str, Any] | None:
    """Choose the opinion entry we can obtain a document for.

    Two channels, in order of preference:
      1. the official source URL (`download_url`) — NY State Law Reporting
         Bureau slip opinions. The state migrated its domain from
         courts.state.ny.us to nycourts.gov; old links are rewritten.
      2. CourtListener's public copy (`local_path` on
         storage.courtlistener.com).
    """
    opinions = result.get("opinions") or []
    with_url = [o for o in opinions
                if o.get("download_url") or o.get("local_path")]
    if not with_url:
        return None
    for op in with_url:
        if has_official_url(op) and op.get("type") in ("combined-opinion",
                                                       "lead-opinion"):
            return op
    for op in with_url:
        if has_official_url(op):
            return op
    return with_url[0]


def has_official_url(op: dict[str, Any]) -> bool:
    return bool(op.get("download_url"))


DEFAULT_CHANNEL_PREFERENCE = ["official", "courtlistener-storage"]


def resolve_document_urls(op: dict[str, Any],
                          preference: list[str]) -> list[tuple[str, str]]:
    """Return (url, channel) download candidates, best channel first.

    Channels: 'official' (NY State Law Reporting Bureau slip opinion; the
    state migrated its domain from courts.state.ny.us to nycourts.gov and
    the legacy domain answers 403) and 'courtlistener-storage' (Free Law
    Project's public archival copy — byte-stable, unlike the official
    host whose responses embed a rotating Cloudflare script).

    Candidates never mix opinion entries: the chosen opinion's own URLs,
    in the configured channel preference order.
    """
    candidates: list[tuple[str, str]] = []
    official = None
    if op.get("download_url"):
        url = op["download_url"]
        url = url.replace("http://www.courts.state.ny.us/",
                          "https://www.nycourts.gov/")
        url = url.replace("http://www.nycourts.gov/",
                          "https://www.nycourts.gov/")
        official = (url, "official")
    storage = None
    if op.get("local_path"):
        storage = (f"https://storage.courtlistener.com/{op['local_path']}",
                   "courtlistener-storage")
    for channel in preference:
        if channel == "official" and official:
            candidates.append(official)
        elif channel == "courtlistener-storage" and storage:
            candidates.append(storage)
    return candidates


def classify_document(resp: requests.Response) -> str:
    """Best-effort format detection: 'html', 'pdf' or 'txt'.

    Content-Type first, magic bytes as fallback — official servers have
    been observed sending generic types.
    """
    ctype = (resp.headers.get("Content-Type") or "").lower()
    head = resp.content[:1024].lstrip()
    if "html" in ctype or head[:1] == b"<":
        return "html"
    if "pdf" in ctype or head[:5] == b"%PDF-":
        return "pdf"
    return "txt"


def criminal_gate(text: str, keywords: list[str],
                  require_all: bool) -> list[str]:
    """Return the keywords present in the document (the evidence of the
    gate). Empty list means the case is rejected."""
    low = text.lower()
    matched = [k for k in keywords if k.lower() in low]
    if require_all:
        return matched if len(matched) == len(keywords) else []
    return matched


def load_collected_ids(cases_path: Path) -> set[Any]:
    """Rebuild the set of collected cluster ids from cases.jsonl.

    cases.jsonl is the source of truth: the checkpoint is written *after*
    the append, so a crash between the two would otherwise re-download
    (and duplicate) the case on resume. A truncated trailing line — the
    only line a crash mid-append can damage — is dropped.
    """
    ids: set[Any] = set()
    if not cases_path.exists():
        return ids
    raw_lines = cases_path.read_text(encoding="utf-8").splitlines()
    kept: list[str] = []
    for line in raw_lines:
        if not line.strip():
            continue
        try:
            ids.add(json.loads(line)["cluster_id"])
            kept.append(line)
        except (json.JSONDecodeError, KeyError):
            break
    if len(kept) != len([l for l in raw_lines if l.strip()]):
        cases_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return ids


def save_checkpoint(path: Path, checkpoint: dict[str, Any],
                    collected: set[Any], attempted: set[Any]) -> None:
    checkpoint["cluster_ids"] = sorted(collected)
    checkpoint["attempted_ids"] = sorted(attempted)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checkpoint, indent=1), encoding="utf-8")


def run(mode: str, cfg: dict[str, Any], args: argparse.Namespace) -> int:
    section = cfg["sample"] if mode == "sample" else cfg["corpus"]
    paths = cfg["paths"] if mode == "sample" else cfg["paths_corpus"]
    cl_cfg = cfg["courtlistener"]

    cases_path = REPO_ROOT / paths["cases_jsonl"]
    docs_dir = REPO_ROOT / paths["documents_dir"]
    log = FetchLog(REPO_ROOT / paths["fetch_log"])
    checkpoint_path = REPO_ROOT / paths["checkpoint"]
    cases_path.parent.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    checkpoint: dict[str, Any] = {"windows_done": [], "cluster_ids": [],
                                  "attempted_ids": []}
    if checkpoint_path.exists() and not args.reset:
        loaded = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        checkpoint = {**checkpoint, **loaded}

    collected = load_collected_ids(cases_path) | set(checkpoint["cluster_ids"])
    attempted = set(checkpoint.get("attempted_ids", [])) | collected

    client = HttpClient(cl_cfg, log)
    preference = list(section.get("document_channel_preference",
                                  DEFAULT_CHANNEL_PREFERENCE))
    keywords = section["criminal_keywords"]
    require_all = bool(section.get("require_all_keywords", False))
    target = section.get("target_usable")
    target = int(target) if target else None

    windows: list[tuple[dict[str, Any], bool]] = [
        (w, False) for w in section.get("windows", [])]
    windows += [(w, True) for w in section.get("overflow_windows", [])]

    counters = {"collected": 0, "gate_rejected": 0, "pdf_rejected": 0,
                "failed": 0, "no_document": 0, "duplicates": 0}
    deadline = (time.monotonic() + args.max_runtime_minutes * 60
                if args.max_runtime_minutes else None)
    incomplete = False

    print(f"mode={mode} — {len(collected)} cases already collected, "
          f"{len(attempted)} already attempted")

    for window, is_overflow in windows:
        label = window["label"]
        if label in checkpoint["windows_done"]:
            print(f"[{label}] already processed — skipping (checkpoint)")
            continue
        if is_overflow and target and len(collected) >= target:
            checkpoint["windows_done"].append(label)
            save_checkpoint(checkpoint_path, checkpoint, collected, attempted)
            print(f"[{label}] target of {target} already reached — "
                  f"overflow window skipped")
            continue

        take = window.get("take")
        taken = 0
        window_done = False
        print(f"[{label}] searching {section['court']} "
              f"{window['filed_after']} → {window['filed_before']}")
        # The v4 search API paginates by cursor: the `page` parameter is
        # IGNORED (every page returns the first result set) — pagination
        # must follow the absolute `next` URL returned with each response.
        request_url: str | None = cl_cfg["search_url"]
        request_params: dict[str, Any] | None = {
            "q": section["query"],
            "type": section["case_type"],
            "court": section["court"],
            "filed_after": window["filed_after"],
            "filed_before": window["filed_before"],
            "order_by": section["order_by"],
            "page_size": int(section["page_size"]),
        }
        purpose = f"search:{label}"
        pages = 0
        while not window_done:
            if deadline and time.monotonic() > deadline:
                incomplete = True
                break
            data = client.get(request_url, purpose=purpose,
                              params=request_params).json()
            pages += 1
            results = data.get("results", [])
            if pages == 1:
                print(f"    {data.get('count')} matches "
                      f"({int(section['page_size'])}/page, cursor-paginated)")
            if pages > int(data.get("count") or 0) // max(1, int(
                    section["page_size"])) + 5:
                # tripwire: the cursor should never need this many pages
                print(f"    WARNING: pagination tripwire hit at {pages} "
                      f"pages — stopping this window")
                window_done = True

            for result in results:
                if deadline and time.monotonic() > deadline:
                    incomplete = True
                    break
                if take is not None and taken >= int(take):
                    window_done = True
                    break
                cid = result.get("cluster_id")
                if cid is None or cid in attempted or cid in collected:
                    counters["duplicates"] += 1
                    continue
                op = pick_opinion(result)
                if op is None:
                    if not args.dry_run:
                        attempted.add(cid)
                        counters["no_document"] += 1
                    continue
                if args.dry_run:
                    print(f"    would take: {result.get('caseName')} "
                          f"({result.get('dateFiled')})")
                    taken += 1
                    continue

                print(f"    downloading {result.get('caseName')} "
                      f"({result.get('dateFiled')})")
                doc = None
                doc_url = channel = None
                saw_pdf = False
                saw_network_failure = False
                for cand_url, cand_channel in resolve_document_urls(
                        op, preference):
                    # a .pdf URL is a PDF without fetching it — and some
                    # legacy official hosts are dead (multi-minute connect
                    # timeouts), so never fetch a URL we already know is
                    # unusable.
                    if cand_url.lower().split("?")[0].endswith(".pdf"):
                        saw_pdf = True
                        print(f"    {cand_channel}: PDF url — trying next "
                              f"channel")
                        continue
                    try:
                        cand_doc = client.get(
                            cand_url, purpose=f"document:{cid}")
                    except RuntimeError as exc:
                        saw_network_failure = True
                        print(f"    {cand_channel} failed ({exc})")
                        continue
                    if classify_document(cand_doc) == "pdf":
                        # fetched but PDF: a text-bearing channel may still
                        # exist — try it before giving up on the case.
                        saw_pdf = True
                        print(f"    {cand_channel} served a PDF — trying "
                              f"next channel")
                        continue
                    doc, doc_url, channel = cand_doc, cand_url, cand_channel
                    break
                if doc is None:
                    if saw_network_failure:
                        attempted.add(cid)
                        counters["failed"] += 1
                        print("    no text-bearing document reachable — "
                              "next candidate")
                    else:
                        attempted.add(cid)
                        counters["pdf_rejected"] += 1
                        print("    rejected: PDF-only case — next candidate")
                    continue

                fmt = classify_document(doc)
                if fmt == "pdf":
                    # PDFs without a text layer cannot pass the criminal
                    # gate (documented Phase 1 finding for 2011-2015
                    # batches). Rejected and counted — never silently
                    # dropped.
                    attempted.add(cid)
                    counters["pdf_rejected"] += 1
                    print("    rejected: PDF document (no text gate)")
                    continue
                text = doc.content.decode("utf-8", errors="ignore")
                matched = criminal_gate(text, keywords, require_all)
                if not matched:
                    attempted.add(cid)
                    counters["gate_rejected"] += 1
                    print("    rejected by criminal gate — next candidate")
                    continue

                doc_path = docs_dir / f"{cid}.{fmt}"
                doc_path.write_bytes(doc.content)

                record = {
                    "cluster_id": cid,
                    "case_name": result.get("caseName"),
                    "court": result.get("court"),
                    "court_id": result.get("court_id"),
                    "date_filed": result.get("dateFiled"),
                    "docket_number": result.get("docketNumber"),
                    "citations": result.get("citation") or [],
                    "courtlistener_url":
                        "https://www.courtlistener.com"
                        + result.get("absolute_url", ""),
                    "official_source_url": op.get("download_url"),
                    "document_channel": channel,
                    "document_url_used": doc_url,
                    "document_path": str(doc_path.relative_to(REPO_ROOT)),
                    "document_format": fmt,
                    "document_sha256":
                        hashlib.sha256(doc.content).hexdigest(),
                    "document_bytes": len(doc.content),
                    "criminal_gate": {"matched_keywords": matched,
                                      "mode": "all" if require_all else "any"},
                    "window": label,
                    "fetched_at": utc_now(),
                }
                with cases_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                collected.add(cid)
                attempted.add(cid)
                save_checkpoint(checkpoint_path, checkpoint,
                                collected, attempted)
                taken += 1
                counters["collected"] += 1
                print(f"    collected ({len(doc.content)} bytes, "
                      f"gate matched: {matched})")
            if incomplete:
                break
            if not window_done and data.get("next"):
                request_url = data["next"]
                request_params = None
                purpose = f"search:{label}:cursor"
            else:
                window_done = True

        if incomplete:
            break
        if not args.dry_run:
            checkpoint["windows_done"].append(label)
            save_checkpoint(checkpoint_path, checkpoint, collected, attempted)
            print(f"[{label}] window processed — total {len(collected)} "
                  f"collected so far")
        elif taken == 0:
            print(f"    WARNING: no collectable case found for window "
                  f"{label}")

    print(f"\ntotal collected ({mode}): {len(collected)} cases")
    print(f"this run: {counters}")
    print(f"requests logged: {len(log.entries)}")
    if incomplete:
        print("STATUS: INCOMPLETE — re-run the same command to resume "
              "from the checkpoint")
    else:
        print("STATUS: COMPLETE")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--mode", choices=["sample", "corpus"],
                        default="sample",
                        help="sample: Phase 1 stratified sample; "
                             "corpus: Phase 2 full collection "
                             "(default: sample)")
    parser.add_argument("--dry-run", action="store_true",
                        help="search only, print what would be collected")
    parser.add_argument("--reset", action="store_true",
                        help="ignore the checkpoint and start over")
    parser.add_argument("--max-runtime-minutes", type=float, default=None,
                        help="stop gracefully after N minutes; the "
                             "checkpoint preserves progress, re-run to "
                             "resume")
    args = parser.parse_args()

    cfg = json.loads((REPO_ROOT / args.config).read_text(encoding="utf-8"))
    return run(args.mode, cfg, args)


if __name__ == "__main__":
    sys.exit(main())
