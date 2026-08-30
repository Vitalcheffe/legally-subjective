#!/usr/bin/env python3
"""M1.5 voie D — moisson du CDN storage.courtlistener.com (anonyme, hors quota).

Découverte : chaque opinion a un `local_path` (miroir du document original)
servi anonymement par https://storage.courtlistener.com/{local_path}.
Le endpoint v4 /search/ (anonyme aussi) rend, par docket, TOUTES les grappes
avec leurs opinions imbriquées (id, local_path, type, sha1, snippet).

Phases:
  search  (A) goutte-à-goutte anonyme par docket → search/*.json + index.jsonl
  docs    (B) fetch CDN des documents (local_path ≠ '') → data/raw/m15_docs/
  bind    (C) extraction texte (pdftotext etc.) + liaison aux 1778 ids du
          corpus (direct, puis par type pour les doublons Harvard sans PDF)
          → data/m15_store/storage/texts.jsonl.gz + bind_report.json
"""
import gzip
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(REPO, "data", "processed", "corpus_cases_v1.jsonl.gz")
OPINIONS = os.path.join(REPO, "data", "processed", "corpus_opinions_v1.jsonl.gz")
BASE = os.path.join(REPO, "data", "m15_store", "storage")
SEARCH_DIR = os.path.join(BASE, "search")
DOCS_DIR = os.path.join(REPO, "data", "raw", "m15_docs")
UA = {"User-Agent": "legally-subjective/0.1 (research; M1.5 storage harvest)"}
SEARCH_URL = "https://www.courtlistener.com/api/rest/v4/search/"
CDN = "https://storage.courtlistener.com/"

DRIP = 6.0          # s entre requêtes search (adaptatif)
N_WORKERS = 3


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


# ------------------------------------------------------------------ dockets
def clean_docket(d):
    d = re.sub(r"^no\.?\s+", "", (d or "").strip().rstrip("."),
               flags=re.I)
    return d.replace("–", "-").replace("—", "-").replace(" ", "")


def load_dockets():
    """docket nettoyé -> liste cluster_ids (l'ordre du fichier cases fait foi)."""
    out = {}
    with gzip.open(CASES, "rt") as f:
        for line in f:
            c = json.loads(line)
            dk = clean_docket(c.get("docket_number"))
            if dk:
                out.setdefault(dk, []).extend(c.get("cluster_ids", []))
    return out


# ------------------------------------------------------------------ phase A
def http_get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def phase_search():
    os.makedirs(SEARCH_DIR, exist_ok=True)
    dockets = load_dockets()
    todo = [d for d in dockets if not os.path.exists(
        os.path.join(SEARCH_DIR, d.replace("/", "_") + ".json"))]
    log(f"SEARCH: {len(dockets)} dockets, {len(todo)} à faire "
        f"(déjà faits: {len(dockets) - len(todo)})")
    drip = DRIP
    n429 = 0
    for i, dk in enumerate(todo):
        fn = os.path.join(SEARCH_DIR, dk.replace("/", "_") + ".json")
        # dockets courts ("15-7"): le préfixe "No." rend la requête
        # sélective (sinon trop de hits full-text → throttle/timeout)
        qterm = f"No. {dk}" if len(dk) <= 5 else dk
        q = urllib.parse.quote(f'"{qterm}"')
        pages, page, ok = [], 1, False
        for attempt in range(6):
            try:
                st, body = http_get(
                    f"{SEARCH_URL}?court=scotus&type=o&q={q}&page_size=20"
                    f"&page={page}")
                d = json.loads(body)
                pages.append(d)
                if d.get("next"):
                    page += 1
                    continue
                ok = True
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    n429 += 1
                    drip = min(drip * 1.6, 20.0)      # ralentit durablement
                    wait = 90 if n429 < 4 else 300
                    log(f"  429 sur {dk} — pause {wait}s (drip→{drip:.1f}s)")
                    time.sleep(wait)
                else:
                    log(f"  HTTP {e.code} sur {dk}, tentative {attempt + 1}")
                    time.sleep(15)
            except Exception as e:                    # noqa: BLE001
                log(f"  {type(e).__name__} sur {dk}: {e}")
                time.sleep(20)
        if ok:
            with open(fn + ".tmp", "w") as f:
                json.dump(pages, f)
            os.replace(fn + ".tmp", fn)
            if drip > DRIP:
                drip = max(DRIP, drip * 0.95)        # guérison lente
        else:
            with open(fn + ".err", "w") as f:         # marqué, pas bloquant
                f.write(f"échec après tentatives, {time.ctime()}\n")
        if i % 25 == 0:
            log(f"  {i}/{len(todo)} | {dk}")
        time.sleep(drip)
    build_index()
    errs = [f for f in os.listdir(SEARCH_DIR) if f.endswith(".err")]
    log(f"SEARCH fini. erreurs: {len(errs)}")


def build_index():
    """Aplatit search/*.json → index.jsonl (une ligne par opinion)."""
    out = os.path.join(BASE, "index.jsonl")
    n = 0
    with open(out + ".tmp", "w") as fo:
        for fn in sorted(os.listdir(SEARCH_DIR)):
            if not fn.endswith(".json"):
                continue
            docket = fn[:-5].replace("_", "/")
            for page in json.load(open(os.path.join(SEARCH_DIR, fn))):
                for r in page.get("results", []):
                    for op in r.get("opinions", []) or []:
                        fo.write(json.dumps({
                            "docket": docket,
                            "cluster_id": r.get("cluster_id"),
                            "case_name": r.get("caseName"),
                            "date_filed": r.get("dateFiled"),
                            "opinion_id": op.get("id"),
                            "local_path": op.get("local_path") or "",
                            "type": op.get("type"),
                            "sha1": op.get("sha1"),
                            "snippet": (op.get("snippet") or "")[:500],
                            "author_id": op.get("author_id"),
                            "per_curiam": op.get("per_curiam"),
                            "joined_by_ids": op.get("joined_by_ids") or [],
                        }) + "\n")
                        n += 1
    os.replace(out + ".tmp", out)
    log(f"INDEX: {n} opinions indexées → {out}")


# ------------------------------------------------------------------ phase B
def fetch_doc(op_id, path):
    ext = os.path.splitext(path)[1].lower() or ".bin"
    fn = os.path.join(DOCS_DIR, f"{op_id}{ext}")
    if os.path.exists(fn) or os.path.exists(fn + ".fail"):
        return "skip"
    for attempt in range(2):
        try:
            st, body = http_get(CDN + urllib.parse.quote(path), timeout=90)
            if st == 200 and body:
                with open(fn + ".tmp", "wb") as f:
                    f.write(body)
                os.replace(fn + ".tmp", fn)
                return "ok"
        except Exception as e:                        # noqa: BLE001
            if attempt:
                with open(fn + ".fail", "w") as f:
                    f.write(f"{e}\n")
                return "fail"
            time.sleep(2)
    return "fail"


def phase_docs():
    os.makedirs(DOCS_DIR, exist_ok=True)
    idx = [json.loads(l) for l in open(os.path.join(BASE, "index.jsonl"))]
    direct = {r["opinion_id"]: r for r in idx
              if r["local_path"] and r["opinion_id"]}
    log(f"DOCS: {len(direct)} documents localisés (local_path ≠ '')")
    stats = {"ok": 0, "fail": 0, "skip": 0}
    with ThreadPoolExecutor(N_WORKERS) as ex:
        for res in ex.map(lambda kv: fetch_doc(kv[0], kv[1]["local_path"]),
                          list(direct.items())):
            stats[res] = stats.get(res, 0) + 1
            if stats["ok"] % 100 == 0 and stats["ok"]:
                log(f"  {stats}")
    log(f"DOCS fini: {stats}")


# ------------------------------------------------------------------ phase C
HEAD_RE = re.compile(
    r"(?:^|\n)\s*(?:JUSTICE|Justice|CHIEF JUSTICE|Chief Justice)\s+"
    r"(?P<name>[A-Z][a-zA-Z]+)"
    r"(?P<filler>[^\n]{0,200}?)\s*(?:,?\s*(?P<role>deliver\w*|concurr\w*|dissent\w*|with whom[^,.]*)"
    r"[^.]{0,180}\.)",
    re.M)


def extract_text(fn):
    ext = os.path.splitext(fn)[1].lower()
    try:
        if ext == ".pdf":
            for args in (["-layout"], []):
                p = subprocess.run(["pdftotext"] + args + [fn, "-"],
                                   capture_output=True, timeout=180)
                if p.returncode == 0:
                    return p.stdout.decode("utf-8", "replace")
            return ""
        if ext in (".txt", ".json", ".html", ".htm"):
            import html as hh

            raw = open(fn, "rb").read().decode("utf-8", "replace")
            if ext in (".html", ".htm"):
                raw = re.sub(r"<[^>]+>", " ", hh.unescape(raw))
            return raw
        if ext in (".doc", ".wpd"):
            for tool in (["antiword"], ["catdoc"]):
                try:
                    p = subprocess.run(tool + [fn], capture_output=True,
                                       timeout=120)
                    if p.returncode == 0 and p.stdout:
                        return p.stdout.decode("utf-8", "replace")
                except Exception:                    # noqa: BLE001
                    pass
            return ""
    except Exception as e:                            # noqa: BLE001
        log(f"  extract échoue {fn}: {e}")
    return ""


def strip_preamble(text):
    """Garde le SEGMENT d'opinion principal : coupe le syllabus (avant la
    première signature de juge) ET s'arrête à la signature suivante (début
    d'une opinion séparée d'un autre juge dans les documents pluriels)."""
    matches = list(HEAD_RE.finditer(text))
    if not matches:
        return text
    first = matches[0]
    if first.start() > len(text) * 0.6:             # en-tête trop tard : suspect
        return text
    end = matches[1].start() if len(matches) > 1 else len(text)
    return text[first.start():end].strip()


def clean_text(t):
    lines = [re.sub(r"[ \t]+", " ", ln).rstrip() for ln in t.splitlines()]
    out, blank = [], 0
    for ln in lines:
        if ln.strip():
            out.append(ln.strip())
            blank = 0
        else:
            blank += 1
            if blank == 1:
                out.append("")
    return "\n".join(out).strip()


TYPE_MAP = {   # type corpus (CL search) → familles
    "combined": {"combined-opinion", "lead-opinion", "unanimous-opinion",
                 "per-curiam"},
    "lead": {"lead-opinion", "combined-opinion", "unanimous-opinion"},
    "dissent": {"dissent-opinion"},
    "concurrence": {"concurrence-opinion", "plurality-opinion"},
    "concurrence-dissent": {"concurrence-dissent-opinion",
                            "dissent-opinion", "concurrence-opinion"},
    "per-curiam": {"per-curiam", "lead-opinion"},
    "plurality": {"plurality-opinion", "lead-opinion"},
}


def phase_bind():
    idx = [json.loads(l) for l in open(os.path.join(BASE, "index.jsonl"))]
    by_id = {r["opinion_id"]: r for r in idx if r["opinion_id"]}
    corpus = {}
    with gzip.open(OPINIONS, "rt") as f:
        for line in f:
            r = json.loads(line)
            corpus[r["opinion_id"]] = r

    # cluster_id -> docket (via fichier cases) pour les ids hors index
    cl2docket = {}
    with gzip.open(CASES, "rt") as f:
        for line in f:
            c = json.loads(line)
            dk = clean_docket(c.get("docket_number"))
            for cid in c.get("cluster_ids", []):
                cl2docket[cid] = dk

    # --- extraction des documents téléchargés
    texts = {}
    os.makedirs(DOCS_DIR, exist_ok=True)
    for fn in os.listdir(DOCS_DIR):
        if fn.endswith((".fail", ".tmp")) or ".tmp." in fn:
            continue
        oid_s = os.path.splitext(fn)[0]
        if not oid_s.isdigit():
            continue
        t = extract_text(os.path.join(DOCS_DIR, fn))
        if t:
            texts[int(oid_s)] = clean_text(strip_preamble(t))
    log(f"BIND: {len(texts)} documents extraits")

    # --- liaison directe puis par type intra-affaire
    rows, stats = [], {"direct": 0, "bound-type": 0, "bound-combined": 0,
                       "snippet": 0, "none": 0}
    idx_by_docket = {}
    for r in idx:
        if r["opinion_id"]:
            idx_by_docket.setdefault(r["docket"], []).append(r)

    for oid in sorted(corpus):
        c = corpus[oid]
        row = {"opinion_id": oid, "text": "", "via": "none",
               "n_chars": 0}
        if oid in texts:
            row.update(text=texts[oid], via="direct",
                       n_chars=len(texts[oid]))
            stats["direct"] += 1
        else:
            # doublon Harvard sans PDF, ou id hors index → retrouver
            # l'affaire (docket) par cluster_id si nécessaire
            ent = by_id.get(oid)
            if ent is not None:
                docket, my_cluster = ent["docket"], ent.get("cluster_id")
                my_type_idx = ent.get("type")
            else:
                docket = cl2docket.get(c["cluster_id"])
                my_cluster = c["cluster_id"]
                my_type_idx = None
            dockets = idx_by_docket.get(docket, []) if docket else []
            fam = TYPE_MAP.get(c["type"], {"lead-opinion"})
            cand = [r for r in dockets
                    if r["opinion_id"] in texts
                    and (r.get("type") in fam
                         or (c["type"] == "lead" and r.get("type")
                             == "combined-opinion"))]
            if len(cand) >= 1:
                # si plusieurs, préférer un doc d'un AUTRE cluster (doublon)
                pick = next((r for r in cand
                             if r["cluster_id"] != my_cluster),
                            cand[0])
                src = texts[pick["opinion_id"]]
                row.update(text=src, via="bound-type",
                           n_chars=len(src),
                           bound_to=pick["opinion_id"])
                stats["bound-type"] += 1
            elif ent and ent.get("snippet"):
                row.update(text=ent["snippet"].strip(), via="snippet",
                           n_chars=len(ent["snippet"]))
                stats["snippet"] += 1
            else:
                stats["none"] += 1
        rows.append(row)

    out = os.path.join(BASE, "texts.jsonl.gz")
    with gzip.open(out + ".tmp", "wt") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(out + ".tmp", out)

    have = [r for r in rows if r["n_chars"] > 400]
    by_term, tot_term = {}, {}
    for r, c in zip(rows, (corpus[r["opinion_id"]] for r in rows)):
        tot_term[c["term"]] = tot_term.get(c["term"], 0) + 1
        if r["n_chars"] > 400:
            by_term[c["term"]] = by_term.get(c["term"], 0) + 1
    report = {"docs_extracted": len(texts), "stats": stats,
              "usable_texts": len(have), "corpus_total": len(corpus),
              "by_term_have": by_term, "by_term_total": tot_term}
    with open(os.path.join(BASE, "bind_report.json"), "w") as f:
        json.dump(report, f, indent=1)
    log(f"BIND fini: {json.dumps(stats)}")
    for t in sorted(tot_term):
        log(f"  {t}: {by_term.get(t, 0)}/{tot_term[t]}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("search", "all"):
        phase_search()
    if which in ("docs", "all"):
        phase_docs()
    if which in ("bind", "all"):
        phase_bind()
