"""CourtListener REST v4 client — anonymous, cached, resumable.

Zero-fabrication law: every fetched payload is cached on disk with its
request URI and retrieval timestamp. No live lookups at compute time.

Anonymous access notes (verified 2026-08-27):
- /api/rest/v4/search/      works anonymously, cursor pagination, 20/page
- /api/rest/v4/people/      works anonymously
- /api/rest/v4/courts/      works anonymously
- /api/rest/v4/clusters/    401 on filters/detail (needs a token)
- /api/rest/v4/opinions/    401 (needs a token)

So the pipeline is built on /search/ + /people/ only.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://www.courtlistener.com/api/rest/v4"
UA = "legally-subjective/1.0 (open standard; contact: https://legallysubjective.org)"
REPO = Path(__file__).resolve().parents[4]
CACHE = REPO / "data" / "sources" / "courtlistener"

MAX_RETRIES = 4
RETRY_BACKOFF = 2.5  # seconds, multiplied per attempt


def _get(url: str, timeout: int = 30) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):  # transient
                last_err = e
            elif e.code == 404:
                return {"__status__": 404}
            else:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
        time.sleep(RETRY_BACKOFF * attempt)
    raise RuntimeError(f"CourtListener fetch failed after {MAX_RETRIES} attempts: {url} ({last_err})")


def search(**params) -> dict:
    """One page of /search/ with defaults applied. Returns parsed JSON."""
    q = {"format": "json", "order_by": "dateFiled desc"}
    q.update({k: v for k, v in params.items() if v is not None})
    url = f"{API}/search/?{urllib.parse.urlencode(q)}"
    return _get(url)


def search_all_pages(
    cache_dir: Path,
    label: str,
    sleep: float = 0.6,
    **params,
) -> list[dict]:
    """Walk every page of a /search/ query, caching each page as a file.

    Resume-safe: pages already on disk are replayed from cache. The manifest
    (request URI + retrieval timestamp) is written next to the pages.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / f"{label}.manifest.json"
    manifest: dict = {"label": label, "pages": []}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    q = {"format": "json", "order_by": "dateFiled desc"}
    q.update({k: v for k, v in params.items() if v is not None})
    first_url = f"{API}/search/?{urllib.parse.urlencode(q)}"

    results: list[dict] = []
    url: str | None = first_url
    page_no = 0
    while url:
        page_no += 1
        page_file = cache_dir / f"{label}__page_{page_no:03d}.json"
        if page_file.exists():
            data = json.loads(page_file.read_text())
        else:
            data = _get(url)
            page_file.write_text(json.dumps(data, ensure_ascii=False, indent=1))
            manifest["pages"].append(
                {"page": page_no, "uri": url, "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            )
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
            time.sleep(sleep)
        if not isinstance(data, dict) or "results" not in data:
            break
        results.extend(data["results"])
        url = data.get("next")
    return results


def person_by_name(first: str, last: str) -> dict | None:
    """Look up a person in /people/ by first+last name."""
    q = urllib.parse.urlencode({"name_first": first, "name_last": last, "format": "json"})
    data = _get(f"{API}/people/?{q}")
    for r in data.get("results", []):
        if (r.get("name_last") or "").lower() == last.lower():
            return r
    return None


def load_page_cache(cache_dir: Path, label: str) -> list[dict]:
    """Replay a paginated search purely from disk (no network)."""
    out: list[dict] = []
    i = 1
    while True:
        f = cache_dir / f"{label}__page_{i:03d}.json"
        if not f.exists():
            return out
        data = json.loads(f.read_text())
        if isinstance(data, dict):
            out.extend(data.get("results", []))
        i += 1
