#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legally Subjective — M1.5 voie C : les PDF slip de supremecourt.gov.

La cartographie du terrain (session 2) :
  * le bulk S3 2026-06-30 ne contient QUE les lignes à plain_text natif
    (types 'combined' du pipeline PDF de CL) ; les 955 opinions Harvard-XML
    ('lead'/'dissent'/'concurrence', sans sha1) en sont ABSENTES, et 544
    'combined' manquent aussi ;
  * l'API exige un token (perdu au reset), le site CL est derrière AWS WAF
    + blocage géo CloudFront, archive.org est injoignable depuis le poste ;
  * MAIS supremecourt.gov sert ses pages d'index par terme :
      https://www.supremecourt.gov/opinions/slipopinion/{17..23}
    chaque ligne : [n°, date, docket, nom, auteur-code, citation, PDF].
    Les codes auteurs sont les initiales (R=Roberts, EK=Kagan, BK=Kavanaugh,
    AB=Barrett, NG=Gorsuch, SS=Sotomayor, A=Alito, T=Thomas, B=Breyer,
    K=Jackson, PC=per curiam).
    Le PDF slip d'une affaire contient l'opinion de tête PLUS les opinions
    séparées (dissidences, concurrences) — on segmente par en-tête de juge.

Phases (chacune repreneable, état sur disque) :
  A. index    — parse les 7 pages de termes → slip_index.json
  B. match    — docket normalisé ↔ corpus cases → slip_match.json
  C. download — PDFs dans data/raw/slip_pdfs/{term}/{docket}.pdf (état .state.json)
  D. extract  — pdftotext + sha1 + segmentation par juge → slip_found.jsonl
  E. merge    — fusion dans le store M1.5 (opinions_text.jsonl.gz)

Usage : python3 scripts/m15_slip_fetch.py [phase|all]
"""
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(REPO, "data", "processed", "corpus_cases_v1.jsonl.gz")
OPINIONS = os.path.join(REPO, "data", "processed", "corpus_opinions_v1.jsonl.gz")
AUTHOR_MAP = os.path.join(REPO, "data", "m3", "author_map.json")
OUT_DIR = os.path.join(REPO, "data", "raw", "opinion_texts")
PDF_DIR = os.path.join(REPO, "data", "raw", "slip_pdfs")
INDEX = os.path.join(OUT_DIR, "slip_index.json")
MATCH = os.path.join(OUT_DIR, "slip_match.json")
DL_STATE = os.path.join(PDF_DIR, "dl_state.json")
FOUND = os.path.join(OUT_DIR, "slip_found.jsonl")

TERMS = [17, 18, 19, 20, 21, 22, 23]
BASE = "https://www.supremecourt.gov"

# code du site → (nom de famille, slug CL) ; PC traité à part
CODE2J = {
    "R": ("Roberts", "JGRoberts"), "T": ("Thomas", "CThomas"),
    "A": ("Alito", "SAAlito"), "S": ("Sotomayor", "SSotomayor"),
    "EK": ("Kagan", "EKagan"), "NG": ("Gorsuch", "NMGorsuch"),
    "BK": ("Kavanaugh", "BMKavanaugh"), "AB": ("Barrett", "ACBarrett"),
    "K": ("Jackson", "KBJackson"), "B": ("Breyer", "SGBreyer"),
    "G": ("Ginsburg", "RBGinsburg"), "K": ("Kennedy", "AMKennedy"),
}
CODE2J["K"] = ("Jackson", "KBJackson")   # OT2022+ ; Kennedy n écrit plus

UA = {"User-Agent": "legally-subjective/0.1 (research)"}


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def norm_docket(s):
    s = re.sub(r"^No\.?\s*", "", (s or "").strip())
    s = s.replace("–", "-").replace("—", "-").replace("\u2011", "-")
    s = s.rstrip(".").strip()
    if not re.match(r"^\d{2}-\d{2,4}", s) and not re.match(r"^\d{2}[A-Z]\d+", s) \
       and ", Orig" not in s and "Orig" not in s:
        pass
    return s.lower()


def http_get(url, timeout=60, retries=4):
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if a == retries - 1:
                raise
            time.sleep(2 * (a + 1))
    return b""


# ---------------------------------------------------------------- A. index
def phase_index():
    all_rows = []
    for t in TERMS:
        url = f"{BASE}/opinions/slipopinion/{t}"
        html = http_get(url).decode("utf-8", "replace")
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
        n = 0
        for r in rows:
            if ".pdf" not in r or "publicinfo" in r:
                continue
            cells = [re.sub(r"<[^>]+>", " ", c).strip()
                     for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
            # href avec fragment éventuel (#page=N pour les volumes preliminary print)
            pdf = re.search(r"href='([^']+?\.pdf)(?:#page=(\d+))?'", r) or \
                re.search(r'href="([^"]+?\.pdf)(?:#page=(\d+))?"', r)
            if not pdf or len(cells) < 5:
                continue
            seq, date, dk, name, code = cells[0], cells[1], cells[2], cells[3], cells[4]
            kind = "vol" if pdf.group(2) else "slip"
            all_rows.append({
                "term": 2000 + t, "seq": seq, "date_filed": date,
                "docket": norm_docket(dk), "docket_raw": dk,
                "name": name, "author_code": code,
                "pdf": BASE + pdf.group(1), "kind": kind,
                "page": int(pdf.group(2)) if pdf.group(2) else None,
            })
            n += 1
        log(f"terme OT{2000+t} : {n} opinions indexées")
    json.dump(all_rows, open(INDEX, "w"), ensure_ascii=False, indent=1)
    log(f"INDEX : {len(all_rows)} opinions → {INDEX}")
    return all_rows


# ---------------------------------------------------------------- B. match
def load_cases():
    cases = []
    with gzip.open(CASES, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            r["_dockets"] = {norm_docket(r.get("docket_number") or "")}
            # dockets additionnels depuis docket_tokens si présents
            for tok in (r.get("docket_tokens") or []):
                r["_dockets"].add(norm_docket(tok))
            cases.append(r)
    return cases


def phase_match():
    rows = json.load(open(INDEX))
    cases = load_cases()
    opinions = {}
    with gzip.open(OPINIONS, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            opinions.setdefault(r["cluster_id"], []).append(r)
    # cluster_ids → opinion ids du corpus
    by_docket = {}
    for c in cases:
        for d in c["_dockets"]:
            if d:
                by_docket.setdefault((c["term"], d), []).append(c)
    # aussi par docket seul (croisement de termes, rares)
    by_docket_any = {}
    for c in cases:
        for d in c["_dockets"]:
            if d:
                by_docket_any.setdefault(d, []).append(c)

    matched, unmatched = [], []
    for r in rows:
        cand = by_docket.get((r["term"], r["docket"])) or \
            by_docket_any.get(r["docket"], [])
        cand = [c for c in cand if c["term"] == r["term"]] or cand
        if not cand:
            unmatched.append(r)
            continue
        c = cand[0]
        ops = []
        for cl in c.get("cluster_ids", []):
            ops.extend(opinions.get(cl, []))
        matched.append({
            **r, "case_name_corpus": c["case_name"],
            "case_term": c["term"],
            "opinion_ids": [o["opinion_id"] for o in ops],
            "sha1s": {str(o["opinion_id"]): o.get("sha1") for o in ops},
            "authors": {str(o["opinion_id"]): o.get("author_id") for o in ops},
        })
    json.dump(matched, open(MATCH, "w"), ensure_ascii=False, indent=1)
    n_ops = sum(len(m["opinion_ids"]) for m in matched)
    log(f"MATCH : {len(matched)}/{len(rows)} opinions slip ↔ corpus "
        f"({n_ops} opinion_ids couvertes), {len(unmatched)} sans correspondance")
    if unmatched:
        log("  exemples non-matchés : " +
            ", ".join(f"{u['docket_raw']} ({u['term']})" for u in unmatched[:8]))
    return matched


# ---------------------------------------------------------------- C. download
def phase_download(budget_s=420):
    matched = json.load(open(MATCH))
    state = json.load(open(DL_STATE)) if os.path.exists(DL_STATE) else {}
    t0 = time.time()
    n_new = 0
    # 1) volumes preliminary print : UN téléchargement par volume distinct
    vols = {}
    for m in matched:
        if m.get("kind") == "vol":
            vols.setdefault(m["pdf"], []).append(m)
    for pdf_url, members in vols.items():
        vname = pdf_url.rstrip("/").split("/")[-1].replace(".pdf", "")
        vkey = "vol_" + vname
        if not state.get(vkey, {}).get("ok"):
            path = os.path.join(PDF_DIR, "volumes", vname + ".pdf")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # certains volumes n'existent qu'en variante _web (leçon terrain :
            # 584US*/585US* sont morts en _final mais vivants en _web)
            urls = [pdf_url]
            if "_final" in pdf_url:
                urls.append(pdf_url.replace("_final", "_web"))
            got = False
            for u in urls:
                try:
                    pdf = http_get(u, timeout=300)
                    assert pdf[:4] == b"%PDF", "pas un PDF"
                    open(path, "wb").write(pdf)
                    state[vkey] = {"ok": True, "bytes": len(pdf), "path": path,
                                   "sha1": hashlib.sha1(pdf).hexdigest(),
                                   "pdf_url": u, "members": len(members)}
                    n_new += 1
                    got = True
                    log(f"  volume {vname} : {len(pdf)/1e6:.1f} Mo "
                        f"({len(members)} opinions)")
                    break
                except Exception as e:  # noqa: BLE001
                    last_e = e
            if not got:
                state[vkey] = {"ok": False, "err": str(last_e)[:120],
                               "pdf_url": pdf_url}
                log(f"  ✗ volume {vname}: {last_e}")
            time.sleep(0.4)
    # bornes de pages : opinion i du volume → [page_i, page_suivante - 1]
    for pdf_url, members in vols.items():
        vname = pdf_url.rstrip("/").split("/")[-1].replace(".pdf", "")
        vkey = "vol_" + vname
        if not state.get(vkey, {}).get("ok"):
            continue
        ms = sorted(members, key=lambda m: m.get("page") or 0)
        for i, m in enumerate(ms):
            p0 = m.get("page") or 1
            p1 = ms[i + 1]["page"] - 1 if i + 1 < len(ms) else p0 + 45
            state[vkey].setdefault("ranges", {})[
                f"{m['term']}_{m['docket']}"] = [p0, max(p1, p0)]
    # 2) PDFs slip individuels (OT2020+)
    for m in matched:
        if m.get("kind") == "vol":
            continue
        if time.time() - t0 > budget_s:
            log(f"budget download atteint ({n_new} nouveaux) — reprendre")
            break
        key = f"{m['term']}_{m['docket'].replace('/', '_')}"
        if state.get(key, {}).get("ok"):
            continue
        path = os.path.join(PDF_DIR, str(m["term"]), key + ".pdf")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            pdf = http_get(m["pdf"], timeout=90)
            assert pdf[:4] == b"%PDF", "pas un PDF"
            open(path, "wb").write(pdf)
            state[key] = {"ok": True, "bytes": len(pdf), "path": path,
                          "sha1": hashlib.sha1(pdf).hexdigest(),
                          "pdf_url": m["pdf"]}
            n_new += 1
        except Exception as e:  # noqa: BLE001
            state[key] = {"ok": False, "err": str(e)[:120], "pdf_url": m["pdf"]}
            log(f"  ✗ {key}: {e}")
        time.sleep(0.4)          # poli
        if n_new % 25 == 0 and n_new:
            json.dump(state, open(DL_STATE, "w"))
    json.dump(state, open(DL_STATE, "w"))
    ok = sum(1 for v in state.values() if v.get("ok"))
    log(f"DOWNLOAD : {ok} PDFs locaux (slip + volumes) / {len(matched)} affaires "
        f"({sum(1 for v in state.values() if not v.get('ok'))} erreurs)")
    return state


# ---------------------------------------------------------------- D. extract
HEAD_RE = re.compile(
    r"(?:^|\n)\s*(?:JUSTICE|Justice|CHIEF JUSTICE|Chief Justice)\s+"
    r"([A-Z][a-zA-Z]+)"
    r"([^\n]{0,200}?)\s*(?:,\s*(deliver\w*|concurr\w*|dissent\w*|with whom[^,.]*)"
    r"[^.]{0,180}\.)",
    re.M)


def role_of(frag, full):
    f = (frag + " " + full[:150]).lower()
    if "dissent" in f and "concurr" in f:
        return "concurrence-dissent"
    if "dissent" in f:
        return "dissent"
    if "concurr" in f:
        return "concurrence"
    if "deliver" in f or "statement" in f:
        return "lead"
    return "lead"


def pdftotext(path, f_page=None, l_page=None):
    for args in (["-layout"], []):
        cmd = ["pdftotext"] + args
        if f_page:
            cmd += ["-f", str(f_page)]
        if l_page:
            cmd += ["-l", str(l_page)]
        cmd += [path, "-"]
        try:
            out = subprocess.run(cmd, capture_output=True, timeout=180)
            if out.returncode == 0:
                return out.stdout.decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            pass
    return ""


def phase_extract():
    matched = json.load(open(MATCH))
    state = json.load(open(DL_STATE))
    amap = json.load(open(AUTHOR_MAP))["mapping"]
    id2slug = {int(k): v["slug"] for k, v in amap.items()}
    id2last = {int(k): v["last_name"] for k, v in amap.items()}
    # types du corpus (pour le binding par rôle quand l auteur est inconnu)
    oid_type = {}
    with gzip.open(OPINIONS, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            oid_type[r["opinion_id"]] = r.get("type")
    ROLE2TYPES = {
        "lead": {"lead", "combined", "per-curiam"},
        "dissent": {"dissent"},
        "concurrence": {"concurrence"},
        "concurrence-dissent": {"in-part-opinion", "in-part-dissent"},
    }
    out = open(FOUND, "w", encoding="utf-8")
    n_bound = n_seg = n_sha = 0
    for m in matched:
        key = f"{m['term']}_{m['docket'].replace('/', '_')}"
        if m.get("kind") == "vol":
            vname = m["pdf"].rstrip("/").split("/")[-1].replace(".pdf", "")
            vkey = "vol_" + vname
            vst = state.get(vkey, {})
            rng = (vst.get("ranges") or {}).get(f"{m['term']}_{m['docket']}")
            if not vst.get("ok") or not rng:
                continue
            text = pdftotext(vst["path"], rng[0], rng[1])
            st = {"sha1": None, "pdf_url": m["pdf"]}
        else:
            st = state.get(key, {})
            if not st.get("ok"):
                continue
            text = pdftotext(st["path"])
        if len(text) < 1500:
            log(f"  ⚠ {key}: texte pdf trop court ({len(text)})")
            continue
        common = {"case_docket": m["docket_raw"], "term": m["term"],
                  "case_name": m["name"], "lead_author_code": m["author_code"],
                  "pdf_sha1": st.get("sha1"), "pdf_url": st.get("pdf_url"),
                  "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

        # 1) OR : les oids dont le sha1 corpus == sha1 du PDF → texte COMPLET
        sha_hit = [int(oid) for oid, s in m["sha1s"].items()
                   if s and s == st.get("sha1")]
        bound = set()
        for oid in sha_hit:
            out.write(json.dumps({**common, "opinion_id": oid,
                                  "justice": "(pdf-validé)",
                                  "role": "full-pdf", "plain_text": text[:2000000],
                                  "pdf_validated_opinion": oid,
                                  "corpus_type": oid_type.get(oid)},
                                 ensure_ascii=False) + "\n")
            bound.add(oid)
            n_sha += 1
            n_bound += 1

        # 2) segmentation par en-têtes de juge
        heads = list(HEAD_RE.finditer(text))
        segs = []
        if len(heads) >= 2:
            for i, h in enumerate(heads):
                e = heads[i + 1].start() if i + 1 < len(heads) else len(text)
                segs.append({"justice": h.group(1),
                             "role": role_of(h.group(2), text[h.start():e]),
                             "text": text[h.start():e]})
        else:
            j = CODE2J.get(m["author_code"], ("per_curiam",))[0] \
                if m["author_code"] != "PC" else "per_curiam"
            segs = [{"justice": j, "role": "lead", "text": text}]

        # candidats à lier : opinions du corpus non déjà liées
        cand = {}
        for oid in m["opinion_ids"]:
            if oid in bound:
                continue
            aid = m["authors"].get(str(oid))
            cand[oid] = {"author": id2last.get(aid) if aid else None,
                         "type": oid_type.get(oid)}
        used = set()
        for seg in segs:
            oid_bound = None
            # 2a) par auteur (nom de famille depuis l en-tête du texte)
            for oid, info in cand.items():
                if oid in used or not info["author"]:
                    continue
                if info["author"].lower() == seg["justice"].lower():
                    oid_bound = oid
                    break
            # 2b) par rôle unique (opinions sans auteur connu)
            if oid_bound is None:
                fam = ROLE2TYPES.get(seg["role"], set())
                cands = [oid for oid, info in cand.items()
                         if oid not in used and info["type"] in fam]
                if len(cands) == 1:
                    oid_bound = cands[0]
            if oid_bound:
                used.add(oid_bound)
                n_bound += 1
            n_seg += 1
            out.write(json.dumps({**common, "opinion_id": oid_bound,
                                  "justice": seg["justice"], "role": seg["role"],
                                  "plain_text": seg["text"][:2000000],
                                  "pdf_validated_opinion":
                                      sha_hit[0] if sha_hit else None,
                                  "corpus_type": oid_type.get(oid_bound)
                                      if oid_bound else None},
                                 ensure_ascii=False) + "\n")
    out.close()
    log(f"EXTRACT : {n_seg} segments, {n_bound} liés à un opinion_id "
        f"dont {n_sha} sha1-validés (texte complet)")
    return


def phase_merge():
    import gzip as gz
    # le store existant (voie B)
    store_path = os.path.join(OUT_DIR, "opinions_text.jsonl.gz")
    store = {}
    if os.path.exists(store_path):
        with gz.open(store_path, "rt", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                store[r["opinion_id"]] = r
    n_before = len(store)
    # les trouvailles slip → converties au schéma du store quand opinion_id connu
    if os.path.exists(FOUND):
        for line in open(FOUND, encoding="utf-8"):
            r = json.loads(line)
            oid = r.get("opinion_id")
            if oid is None or oid in store:
                continue
            store[oid] = {
                "opinion_id": oid,
                "plain_text": r["plain_text"],
                "html": "",
                "sha1": r.get("pdf_sha1"),
                "type": {"lead": "lead", "dissent": "dissent",
                         "concurrence": "concurrence",
                         "concurrence-dissent": "in-part-opinion"}.get(r["role"]),
                "author_id": None,          # lié plus tard via auteur du texte
                "cluster_id": None,
                "per_curiam": r.get("lead_author_code") == "PC",
                "page_count": None,
                "download_url": r.get("pdf_url"),
                "author_str": r.get("justice"),
                "fetched_at": r["fetched_at"],
                "provenance": "supremecourt.gov slip PDF",
            }
    tmp = store_path + ".tmp"
    with gz.open(tmp, "wt", encoding="utf-8") as f:
        for oid in sorted(store):
            f.write(json.dumps(store[oid], ensure_ascii=False) + "\n")
    os.replace(tmp, store_path)
    # les segments non liés → fichier séparé pour M3
    loose = os.path.join(OUT_DIR, "slip_segments_unbound.jsonl")
    if os.path.exists(FOUND):
        with open(loose, "w", encoding="utf-8") as fo:
            for line in open(FOUND, encoding="utf-8"):
                r = json.loads(line)
                if r.get("opinion_id") is None:
                    fo.write(line)
    log(f"MERGE : store {n_before} → {len(store)} opinions liées ; "
        f"segments non liés → {os.path.basename(loose)}")


def main():
    ph = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    if ph in ("index", "all"):
        phase_index()
    if ph in ("match", "all"):
        phase_match()
    if ph in ("download", "all"):
        phase_download()
    if ph in ("extract", "all"):
        phase_extract()
    if ph in ("merge", "all"):
        phase_merge()


if __name__ == "__main__":
    main()
