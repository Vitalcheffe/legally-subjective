#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legally Subjective — M1.5 en BATCH : la physique du token a changé le problème.

Découverte (2026-08-29) : le token gratuit CourtListener est limité à
5 req/min, ~55 req/h, ET 125 req/JOUR. À 1 opinion par requête, 1 778
opinions = 14 jours de drip. Mais la limite compte des REQUÊTES, pas des
opinions : le filtre `id__in` de l'API liste permet de récupérer N opinions
PAR requête. À 20 opinions/requête : 89 requêtes ≈ 20 minutes, très loin
sous le plafond journalier.

Ce script est compatible bit-à-bit avec l'infrastructure du drip :
- même sortie  data/raw/opinion_texts/opinions_text.jsonl.gz  (mêmes champs)
- même état    data/raw/opinion_texts/state.json               (done, cooldown_until)
- la passe finale rattrape au cas par cas les opinions absentes des réponses
  liste (404 → state["missing"], comptées comme résolues).

Stratégie :
  1. SONDE  : ?id__in=<3 ids réels>&page_size=100
     - 200 + résultats avec plain_text  -> id__in OK, la sonde EST la 1re passe
     - 400 (filtre inconnu)             -> diagnostic + exit 2 (retour au drip)
     - liste sans plain_text            -> diagnostic + exit 2
  2. PASSES : lots de --batch ids (défaut 20), une requête par lot,
     pagination suivie si la réponse est tronquée (champ next).
     Champs demandés sans html (réponses légères) ; html récupéré en seconde
     passe uniquement pour les opinions sans plain_text.
  3. RATTRAPAGE : ids jamais vus -> détail par id (comme le drip) ; 404 -> missing.

Usage :
  python3 scripts/fetch_opinion_texts_batch.py --probe-only   # sonde et dit
  python3 scripts/fetch_opinion_texts_batch.py                # tout
  python3 scripts/fetch_opinion_texts_batch.py --batch 40     # si page_size le permet
"""
import argparse
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

ROOT = "/home/z/my-project/legally-subjective"
OPINIONS = os.path.join(ROOT, "data", "processed", "corpus_opinions_v1.jsonl.gz")
OUT_DIR = os.path.join(ROOT, "data", "raw", "opinion_texts")
OUT = os.path.join(OUT_DIR, "opinions_text.jsonl.gz")
STATE = os.path.join(OUT_DIR, "state.json")
BASE = "https://www.courtlistener.com/api/rest/v4/opinions/"

PAGE_FIELD = "page_size"


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def load_token():
    env = os.path.join(ROOT, ".env")
    if os.path.exists(env):
        for line in open(env):
            line = line.strip()
            if line.startswith("COURTLISTENER_TOKEN="):
                return line.split("=", 1)[1]
    return os.environ.get("COURTLISTENER_TOKEN", "")


def api_get(query, token, timeout=180):
    """GET liste avec paramètres ; retourne (status, parsed|None, retry_after)."""
    url = BASE + "?" + query
    req = urllib.request.Request(url, headers={
        "Authorization": f"Token {token}",
        "User-Agent": "legally-subjective/0.1 (research)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode()), 0
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read()
        except Exception:
            pass
        return e.code, _try_json(body), int(e.headers.get("Retry-After", "60"))


def api_get_detail(oid, token, timeout=120):
    url = BASE + str(oid) + "/"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Token {token}",
        "User-Agent": "legally-subjective/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _try_json(b):
    try:
        return json.loads(b.decode())
    except Exception:
        return None


def load_state():
    done, cooldown, missing = set(), 0, set()
    if os.path.exists(STATE):
        st = json.load(open(STATE))
        done = set(st.get("done", []))
        cooldown = st.get("cooldown_until", 0)
        missing = set(st.get("missing", []))
    return done, cooldown, missing


def save_state(done, cooldown=0, missing=None):
    st = {"done": sorted(done)}
    if cooldown:
        st["cooldown_until"] = int(cooldown)
    if missing:
        st["missing"] = sorted(missing)
    with open(STATE + ".tmp", "w") as f:
        json.dump(st, f)
    os.replace(STATE + ".tmp", STATE)


def expected_ids():
    ids = []
    with gzip.open(OPINIONS, "rt", encoding="utf-8") as f:
        for line in f:
            oid = json.loads(line).get("opinion_id")
            if oid:
                ids.append(oid)
    return sorted(set(ids))


def rec_from(d, oid, want_html=False):
    """Traduit un enregistrement API -> format exact du drip."""
    pt = d.get("plain_text") or ""
    html = ""
    if want_html and not pt:
        html = (d.get("html") or "")[:500000]
    return {
        "opinion_id": oid,
        "plain_text": pt,
        "html": html,
        "sha1": d.get("sha1"), "type": d.get("type"),
        "author_id": d.get("author_id"), "cluster_id": d.get("cluster_id"),
        "per_curiam": d.get("per_curiam"), "page_count": d.get("page_count"),
        "download_url": d.get("download_url"),
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def write_records(recs):
    """Obsolète en interne — conservée pour compat : réécrit TOUT le fichier
    proprement (un seul membre gzip) à partir des enregistrements donnés +
    ce qui est déjà lisible dans le fichier existant."""
    existing = load_all_records()
    for rec in recs:
        existing[rec["opinion_id"]] = rec
    rebuild_output(existing)


def load_all_records():
    """Lecteur ROBUSTE du fichier de sortie (leçon du 2026-08-29 : le drip
    écrivait des membres gzip en append ; un processus tué au milieu d'une
    écriture brisait la chaîne et 42 enregistrements sont devenus
    illisibles). Ce lecteur sauve tout ce qui est sauvable :
    - chaque membre gzip est décompressé indépendamment ;
    - les lignes JSON valides sont conservées (la dernière ligne tronquée
      d'un membre tué en pleine écriture est ignorée) ;
    - un éventuel opinions_text.jsonl non compressé est aussi fusionné.
    Retourne {opinion_id: record}."""
    records = {}
    # 1. fichier gz multi-membres, sauvetage membre par membre
    if os.path.exists(OUT):
        raw = open(OUT, "rb").read()
        starts = []
        for i in range(len(raw) - 2):
            if raw[i] == 0x1F and raw[i + 1] == 0x8B and raw[i + 2] == 8:
                starts.append(i)
        for s in starts:
            d = zlib.decompressobj(16 + zlib.MAX_WBITS)
            try:
                data = d.decompress(raw[s:])
            except Exception:
                continue
            _absorb_lines(data, records)
    # 2. jsonl non compressé (chemin du drip corrigé)
    plain = OUT[:-3] if OUT.endswith(".gz") else OUT + ".jsonl"
    if os.path.exists(plain):
        try:
            _absorb_lines(open(plain, "rb").read(), records)
        except OSError:
            pass
    return records


def _absorb_lines(data, records):
    for line in data.split(b"\n"):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            if isinstance(r, dict) and r.get("opinion_id"):
                records[r["opinion_id"]] = r
        except Exception:
            continue


def rebuild_output(records):
    """Réécriture ATOMIQUE du fichier en UN SEUL membre gzip propre :
    écriture dans .tmp puis os.replace — un processus tué à tout instant
    laisse soit l'ancien fichier, soit le nouveau, jamais un hybride."""
    tmp = OUT + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        for oid in sorted(records):
            f.write(json.dumps(records[oid], ensure_ascii=False) + "\n")
    os.replace(tmp, OUT)


def query_for(ids, page_size, with_fields):
    q = "id__in=" + ",".join(str(i) for i in ids)
    if with_fields:
        q += "&fields=id,plain_text,sha1,type,author_id,cluster_id,per_curiam,page_count,download_url"
    q += f"&{PAGE_FIELD}={page_size}"
    return q


def fetch_batch(ids, token, page_size, with_fields, results):
    """Une requête liste + boucle de pagination (jusqu'à 6 pages).
    Retourne (n_ok, by_id) ; n_ok = -1 si 429 (quota), -2 si erreur."""
    status, data, ra = api_get(query_for(ids, page_size, with_fields), token)
    if status == 429:
        return -1, {}
    if status != 200 or not isinstance(data, dict):
        log(f"liste : HTTP {status} — {str(data)[:200]}")
        return -2, {}
    by_id = {}
    pages = 0
    while isinstance(data, dict) and pages < 6:
        for d in data.get("results", []):
            if d.get("id"):
                by_id[d["id"]] = d
        nxt = data.get("next")
        if not nxt or len(by_id) >= len(ids):
            break
        # page suivante : suivre le lien tel quel (contient déjà les filtres)
        pages += 1
        time.sleep(13)  # respecter 5 req/min même en pagination
        req = urllib.request.Request(nxt, headers={
            "Authorization": f"Token {token}",
            "User-Agent": "legally-subjective/0.1 (research)"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return -1, {}
            log(f"page suivante : HTTP {e.code} — ignorée")
            break
    results.update(by_id)
    return len(by_id), by_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=20,
                    help="opinions par requête (défaut 20 ; monter si page_size le permet)")
    ap.add_argument("--pace", type=float, default=13.0,
                    help="secondes entre requêtes (13 = 5 req/min)")
    ap.add_argument("--probe-only", action="store_true",
                    help="sonde id__in + plain_text et s'arrête")
    args = ap.parse_args()

    token = load_token()
    if not token:
        raise SystemExit("COURTLISTENER_TOKEN manquant (.env)")
    os.makedirs(OUT_DIR, exist_ok=True)

    ids_all = expected_ids()
    done, cooldown, missing = load_state()

    # ---- RÉCONCILIATION état <-> fichier réel ----
    # Le state.json peut mentir (corruption du 2026-08-29 : 112 déclarées,
    # 70 lisibles). La vérité est ce qui est LISIBLE dans le fichier.
    records = load_all_records()
    records = {k: v for k, v in records.items() if k in set(ids_all)}
    if set(records) != done:
        lost = done - set(records)
        if lost:
            log(f"RÉCONCILIATION : {len(lost)} ids déclarées dans state.json mais "
                f"absentes du fichier (corruption passée) — retournent en TODO")
        done = set(records)
        save_state(done, missing=missing)
    # guérison immédiate : réécrire le gz en UN membre propre, une fois
    if records and os.path.exists(OUT):
        rebuild_output(records)

    if cooldown and cooldown > time.time():
        log(f"token en cooldown — encore {int(cooldown - time.time())}s ; passe sautée")
        raise SystemExit(0)
    # Le state.json peut mentir (corruption du 2026-08-29 : 112 déclarées,
    # 70 lisibles). La vérité est ce qui est LISIBLE dans le fichier.
    records = load_all_records()
    records = {k: v for k, v in records.items() if k in set(ids_all)}
    if set(records) != done:
        lost = done - set(records)
        if lost:
            log(f"RÉCONCILIATION : {len(lost)} ids déclarées dans state.json mais "
                f"absentes du fichier (corruption passée) — retournent en TODO")
        done = set(records)
        save_state(done, missing=missing)
    # guérison immédiate : réécrire le gz en UN membre propre, une fois
    if records and os.path.exists(OUT):
        rebuild_output(records)

    todo = [i for i in ids_all if i not in done and i not in missing]
    log(f"{len(ids_all)} attendues ; {len(done)} faites (fichier : {len(records)}) ; "
        f"{len(missing)} missing ; {len(todo)} à faire")

    # ------- SONDE : 3 ids réels, page_size=100 -------
    probe_ids = todo[:3] if todo else ids_all[:3]
    status, data, ra = api_get(query_for(probe_ids, 100, with_fields=True), token)
    if status == 429:
        log(f"429 — Retry-After {ra}s ; quota non libéré")
        if ra > 600:
            save_state(done, cooldown=time.time() + ra, missing=missing)
            log("cooldown persisté dans state.json")
        raise SystemExit(0)
    if status == 400:
        log("SONDE 400 — le filtre id__in (ou fields) est REFUSÉ :")
        log(json.dumps(data, ensure_ascii=False)[:400])
        raise SystemExit(2)
    if status != 200 or not isinstance(data, dict):
        log(f"SONDE HTTP {status} — abandon")
        raise SystemExit(2)
    rows = data.get("results", [])
    has_pt = any(d.get("plain_text") for d in rows)
    log(f"SONDE OK — HTTP 200, count={data.get('count')}, résultats={len(rows)}, "
        f"plain_text présent : {has_pt}")
    if rows and not has_pt:
        log("la liste ne renvoie PAS plain_text — batch inutile, retour au drip")
        raise SystemExit(2)
    if not rows:
        log("réponse vide (ids déjà faits ?) — rien à faire")
        raise SystemExit(0)

    if args.probe_only:
        return

    # la sonde a déjà rapporté ses opinions : les enregistrer.
    # Celles SANS plain_text sont différées (la passe html les complétera
    # avant écriture — jamais de doublon de ligne dans le jsonl).
    t0 = time.time()
    deferred = []
    for d in rows:
        if not d.get("id"):
            continue
        if d.get("plain_text"):
            records[d["id"]] = rec_from(d, d["id"])
            done.add(d["id"])
        else:
            deferred.append(d["id"])
    rebuild_output(records)
    save_state(done, missing=missing)
    log(f"sonde créditée (total {len(done)}/{len(ids_all)}) ; "
        f"{len(deferred)} différées (sans texte)")

    # ------- PASSES PRINCIPALES -------
    remaining = [i for i in ids_all if i not in done and i not in missing]
    nb_req = 1  # la sonde
    for i in range(0, len(remaining), args.batch):
        chunk = remaining[i:i + args.batch]
        results = {}
        n_ok, _ = fetch_batch(chunk, token, max(args.batch, 20), True, results)
        nb_req += 1
        if n_ok == -1:
            log("429 en cours de passe — arrêt propre, résumable")
            break
        recs = []
        for oid in chunk:
            d = results.get(oid)
            if d is None:
                continue
            if d.get("plain_text"):
                recs.append(rec_from(d, oid))
                done.add(oid)
            else:
                deferred.append(oid)
        for rec in recs:
            records[rec["opinion_id"]] = rec
        if recs:
            rebuild_output(records)
        save_state(done, missing=missing)
        log(f"lot {i // args.batch + 1}/{(len(remaining) + args.batch - 1) // args.batch} : "
            f"+{len(recs)} (total {len(done)}/{len(ids_all)}) ; "
            f"req={nb_req} ; différées={len(deferred)}")
        if i + args.batch < len(remaining):
            time.sleep(max(args.pace, 1.0))

    # ------- PASSES HTML (opinions sans plain_text) -------
    # ces opinions ne sont NI dans done NI écrites : on récupère leur html,
    # on les écrit une seule fois complète, PUIS on les marque faites.
    deferred = [i for i in dict.fromkeys(deferred) if i not in done]
    if deferred:
        log(f"{len(deferred)} opinions sans plain_text — passe html (repli)")
        for i in range(0, len(deferred), args.batch):
            chunk = deferred[i:i + args.batch]
            results = {}
            n_ok, _ = fetch_batch(chunk, token, max(args.batch, 20), False, results)
            nb_req += 1
            if n_ok == -1:
                log("429 pendant la passe html — arrêt propre (différées restent à faire)")
                break
            recs = [rec_from(results[oid], oid, want_html=True)
                    for oid in chunk if oid in results]
            if recs:
                for rec in recs:
                    records[rec["opinion_id"]] = rec
                rebuild_output(records)
                for rec in recs:
                    done.add(rec["opinion_id"])
                save_state(done, missing=missing)
            log(f"passe html : +{len(recs)} (total {len(done)}/{len(ids_all)}) ; "
                f"req={nb_req}")
            time.sleep(max(args.pace, 1.0))
        # ids introuvables même en seconde passe : rattrapage détail
        for oid in [i for i in deferred if i not in done]:
            try:
                d = api_get_detail(oid, token)
                records[oid] = rec_from(d, oid, want_html=True)
                rebuild_output(records)
                done.add(oid)
                save_state(done, missing=missing)
                time.sleep(max(args.pace, 1.0))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    log("429 détail (différées) — arrêt propre")
                    break
                if e.code == 404:
                    log(f"opinion {oid} : 404 — marquée missing")
                    missing.add(oid)
                    save_state(done, missing=missing)
                else:
                    log(f"opinion {oid} : HTTP {e.code}")
                time.sleep(2)

    # ------- RATTRAPAGE au cas par cas -------
    stragglers = [i for i in ids_all if i not in done and i not in missing]
    if stragglers:
        log(f"{len(stragglers)} opinions jamais vues en liste — rattrapage détail")
        for oid in stragglers:
            try:
                d = api_get_detail(oid, token)
                rec = rec_from(d, oid, want_html=True)
                records[oid] = rec
                rebuild_output(records)
                done.add(oid)
                save_state(done, missing=missing)
                time.sleep(max(args.pace, 1.0))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    ra = int(e.headers.get("Retry-After", "60"))
                    log(f"429 détail — Retry-After {ra}s ; arrêt propre")
                    if ra > 600:
                        save_state(done, cooldown=time.time() + ra, missing=missing)
                    break
                if e.code == 404:
                    log(f"opinion {oid} : 404 — marquée missing")
                    missing.add(oid)
                    save_state(done, missing=missing)
                else:
                    log(f"opinion {oid} : HTTP {e.code}")
                time.sleep(2)
            except Exception as e:  # réseau
                log(f"opinion {oid} : {e}")
                time.sleep(2)

    still = [i for i in ids_all if i not in done and i not in missing]
    log(f"fin : {len(done)}/{len(ids_all)} faites, {len(missing)} missing, "
        f"{len(still)} restantes ; requêtes consommées ce run : ~{nb_req}")
    if not still:
        log("M1.5 COLLECTE COMPLÈTE — lancer scripts/m15_watcher.py --finalize")


if __name__ == "__main__":
    main()
