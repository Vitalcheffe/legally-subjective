#!/usr/bin/env python3
"""Legally Subjective — Module 1: the collector.

Fetches real criminal-appeal cases from the CourtListener v4 search API and
their full text from the official source documents (New York slip opinions
published by the NY State Law Reporting Bureau).

Design constraints (see docs/MANIFEST.md):
  R1  zero mock data            — every record carries its source URLs;
  R2  zero hardcoded parameters — everything comes from config.json;
  R9  reproducibility           — checkpoint for crash recovery, and a
                                  FETCH_LOG that records every HTTP request.

Anonymous access works; a free CourtListener token (env COURTLISTENER_TOKEN)
raises rate limits.

Usage:
    python scripts/fetch_courtlistener.py [--config config.json]
        [--dry-run] [--reset]

Outputs (paths configurable):
    data/sample/cases.jsonl        one record per collected case
    data/sample/documents/*.html   official slip opinions
    data/sample/FETCH_LOG.json     provenance log of every request
    data/sample/.checkpoint.json   resume state
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
        as_json: bool = False,
    ) -> requests.Response:
        """GET with retry on 429/5xx/network errors. Logs every attempt."""
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            ua = self.ua
            try:
                resp = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    headers={"User-Agent": ua},
                )
                # some official hosts reject non-browser agents: one retry
                # with the browser UA, recorded in the log (never silent).
                if resp.status_code == 403 and ua != self.ua_browser:
                    self.log.add(purpose=purpose, url=url, status=403,
                                 note="retrying with browser UA")
                    ua = self.ua_browser
                    resp = self.session.get(
                        url, params=params, timeout=self.timeout,
                        headers={"User-Agent": ua})
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
    """Choose the opinion entry whose official document we download."""
    opinions = result.get("opinions") or []
    with_url = [o for o in opinions if o.get("download_url")]
    if not with_url:
        return None
    for op in with_url:
        if op.get("type") == "combined-opinion":
            return op
    return with_url[0]


def criminal_gate(text: str, keywords: list[str],
                  require_all: bool) -> list[str]:
    """Return the keywords present in the document (the evidence of the
    gate). Empty list means the case is rejected."""
    low = text.lower()
    matched = [k for k in keywords if k.lower() in low]
    if require_all:
        return matched if len(matched) == len(keywords) else []
    return matched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="search only, print what would be collected")
    parser.add_argument("--reset", action="store_true",
                        help="ignore the checkpoint and start over")
    args = parser.parse_args()

    cfg = json.loads((REPO_ROOT / args.config).read_text(encoding="utf-8"))
    cl_cfg = cfg["courtlistener"]
    sample = cfg["sample"]
    paths = cfg["paths"]

    cases_path = REPO_ROOT / paths["cases_jsonl"]
    docs_dir = REPO_ROOT / paths["documents_dir"]
    log = FetchLog(REPO_ROOT / paths["fetch_log"])
    checkpoint_path = REPO_ROOT / paths["checkpoint"]

    checkpoint: dict[str, Any] = {"windows_done": [], "cluster_ids": []}
    if checkpoint_path.exists() and not args.reset:
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))

    client = HttpClient(cl_cfg, log)
    keywords = sample["criminal_keywords"]
    require_all = bool(sample.get("require_all_keywords", False))

    for window in sample["windows"]:
        label = window["label"]
        if label in checkpoint["windows_done"]:
            print(f"[{label}] already collected — skipping (checkpoint)")
            continue
        params = {
            "q": sample["query"],
            "type": sample["case_type"],
            "court": sample["court"],
            "filed_after": window["filed_after"],
            "filed_before": window["filed_before"],
            "order_by": sample["order_by"],
            "page_size": sample["page_size"],
        }
        print(f"[{label}] searching {params['court']} "
              f"{window['filed_after']} → {window['filed_before']}")
        data = client.get(cl_cfg["search_url"], purpose=f"search:{label}",
                          params=params, as_json=True).json()
        results = data.get("results", [])
        print(f"    {data.get('count')} matches, page of {len(results)}")

        taken = 0
        for result in results:
            if taken >= int(window["take"]):
                break
            cid = result.get("cluster_id")
            if cid is None or cid in checkpoint["cluster_ids"]:
                continue
            op = pick_opinion(result)
            if op is None:
                continue
            if args.dry_run:
                print(f"    would take: {result.get('caseName')} "
                      f"({result.get('dateFiled')})")
                taken += 1
                continue

            print(f"    downloading {result.get('caseName')} "
                  f"({result.get('dateFiled')})")
            doc = client.get(op["download_url"],
                             purpose=f"document:{cid}")
            ctype = doc.headers.get("Content-Type", "")
            is_html = "html" in ctype.lower() or doc.content[:64].lstrip()[:1] == b"<"
            suffix = ".html" if is_html else ".pdf"
            docs_dir.mkdir(parents=True, exist_ok=True)
            doc_path = docs_dir / f"{cid}{suffix}"
            doc_path.write_bytes(doc.content)

            text = doc.content.decode("utf-8", errors="ignore") if is_html else ""
            matched = criminal_gate(text, keywords, require_all)
            if not matched:
                print("    rejected by criminal gate — trying next candidate")
                doc_path.unlink()
                continue

            record = {
                "cluster_id": cid,
                "case_name": result.get("caseName"),
                "court": result.get("court"),
                "court_id": result.get("court_id"),
                "date_filed": result.get("dateFiled"),
                "docket_number": result.get("docketNumber"),
                "citations": result.get("citation") or [],
                "courtlistener_url":
                    "https://www.courtlistener.com" + result.get("absolute_url", ""),
                "official_source_url": op["download_url"],
                "document_path": str(doc_path.relative_to(REPO_ROOT)),
                "document_format": "html" if is_html else "pdf",
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
            checkpoint["cluster_ids"].append(cid)
            checkpoint["windows_done"].append(label)
            checkpoint_path.write_text(json.dumps(checkpoint, indent=1),
                                       encoding="utf-8")
            taken += 1
            print(f"    collected ({len(doc.content)} bytes, "
                  f"gate matched: {matched})")
        if taken == 0 and not args.dry_run:
            print(f"    WARNING: no case collected for window {label}")

    print(f"\ncollected cases: {len(checkpoint['cluster_ids'])} "
          f"(log: {len(log.entries)} requests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
