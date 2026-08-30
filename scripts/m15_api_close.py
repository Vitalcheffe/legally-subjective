#!/usr/bin/env python3
"""M1.5 clôture — fetch des textes d'opinions via l'API CourtListener v4 (token).

Stratégie : id__in par lots (défaut 100 ids/requête), pagination suivie,
budget persisté (quota compte = 125/jour), 100% resumable via state.json
(suivi PAR IDS récupérés, immunisé contre tout changement de taille de lot).
Invoquable par incréments : au 429, sauve l'état et sort avec le retry-after.

Usage:
  python3 scripts/m15_api_close.py                # cible auto: snippets+manquants, mode id=
  python3 scripts/m15_api_close.py --all          # tous les ids non encore fetchés
  python3 scripts/m15_api_close.py --probe        # 1 requête unique de test
Codes retour: 0 fini/budget ; 1 erreur HTTP ; 2 throttled (retry_after imprimé).

NOTE: l'endpoint v4 /opinions/ REFUSE id__in (400) mais accepte id=<exact>.
Le mode par lot a donc été remplacé par du id= unitaire, ciblé sur les
opinions dont le texte n'est pas déjà couvert par la voie D (CDN storage).
"""
import gzip
import json
import os
import sys
import time
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = "/home/z/my-project/legally-subjective/.cl_token"
CORPUS = os.path.join(REPO, "data", "processed", "corpus_opinions_v1.jsonl.gz")
STORE = os.path.join(REPO, "data", "m15_store", "api")
STATE = os.path.join(STORE, "state.json")
API = "https://www.courtlistener.com/api/rest/v4/opinions/"

DAILY_BUDGET = 118          # garde-fou sous le plafond 125/jour du compte
HTTP_TIMEOUT = 120


def log(*a):
    print(*a, flush=True)


def load_token():
    with open(TOKEN_FILE) as f:
        return f.read().strip()


def load_corpus_ids():
    ids = set()
    with gzip.open(CORPUS, "rt") as f:
        for line in f:
            ids.add(int(json.loads(line)["opinion_id"]))
    return sorted(ids)


def load_targets():
    """Cibles du top-up: snippets voie D + manquants (fenêtre train d'abord)."""
    import gzip as gz
    final = os.path.join(REPO, "data", "m15_store", "final",
                         "opinion_texts_v2.jsonl.gz")
    targets = []
    with gz.open(final, "rt") as f:
        for line in f:
            r = json.loads(line)
            if r["source"].startswith("storage:snippet") or not r["n_chars"]:
                targets.append((r["opinion_id"], r["term"]))
    targets.sort(key=lambda x: (x[1] > "2019", x[1]))
    return [t[0] for t in targets]


def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f:
            return json.load(f)
    return {"requests_used": 0, "day_marker": "", "fetched_ids": [],
            "next_file_idx": 0, "last_throttle_at": 0}


def save_state(st):
    os.makedirs(STORE, exist_ok=True)
    with open(STATE + ".tmp", "w") as f:
        json.dump(st, f)
    os.replace(STATE + ".tmp", STATE)


class Throttled(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after


def api_get(url, token):
    """GET avec retries 5xx/réseau. Lève Throttled sur 429."""
    last = (0, None)
    for attempt in range(3):
        req = urllib.request.Request(url, headers={
            "Authorization": "Token " + token,
            "User-Agent": "legally-subjective research (M1.5 closure)",
        })
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = b""
            try:
                body = e.read()
            except Exception:
                pass
            if e.code == 429:
                raise Throttled(int(e.headers.get("retry-after", "3600")))
            if e.code >= 500 and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            try:
                return e.code, json.loads(body.decode("utf-8"))
            except Exception:
                return e.code, None
        except (urllib.error.URLError, TimeoutError):
            if attempt < 2:
                time.sleep(10 * (attempt + 1))
                continue
            raise
    return last


def extract_records(payload):
    return [r for r in payload.get("results", []) if r and "id" in r]


def main():
    args = sys.argv[1:]
    probe = "--probe" in args
    fetch_all = "--all" in args

    token = load_token()
    all_ids = load_targets() if not fetch_all else load_corpus_ids()
    st = load_state()

    if st["day_marker"] != time.strftime("%Y-%m-%d") and st["requests_used"] > 0:
        # fenêtre glissante ~24h : conservateur, on ne remet le compteur à zéro
        # que si le jour civil a changé depuis la dernière utilisation
        st["day_marker"] = time.strftime("%Y-%m-%d")
        st["requests_used"] = 0
    st["day_marker"] = time.strftime("%Y-%m-%d")

    fetched = set(st["fetched_ids"])
    # cohérence : les fichiers déjà écrits font foi
    for fname in os.listdir(STORE) if os.path.isdir(STORE) else []:
        if fname.startswith("resp_") and fname.endswith(".json"):
            with open(os.path.join(STORE, fname)) as f:
                for r in json.load(f).get("records", []):
                    fetched.add(int(r["id"]))
    remaining = [i for i in all_ids if i not in fetched]

    log(f"cibles={len(all_ids)} déjà_récupérés={len(fetched & set(all_ids))} "
        f"restants={len(remaining)} budget={st['requests_used']}/{DAILY_BUDGET}")

    if not remaining:
        log("RIEN À FAIRE — toutes les cibles ont déjà une réponse stockée.")

    for oid in remaining:
        if probe and st["requests_used"] > 0:
            log("probe: une requête déjà consommée, arrêt.")
            break
        if not probe and st["requests_used"] >= DAILY_BUDGET:
            log(f"BUDGET ÉPUISÉ ({st['requests_used']} req) — relancer après "
                f"reset de la fenêtre.")
            break

        url = API + "?" + urllib.parse.urlencode({"id": str(oid)})
        records, n_req = [], 0
        tries_throttle = 0
        try:
            while url:
                try:
                    status, payload = api_get(url, token)
                except Throttled as t:
                    # fenêtre roulante: le budget se libère requête par
                    # requête — si le prochain créneau est proche, on attend
                    # sur place plutôt que de sortir
                    if (t.retry_after <= 90 and tries_throttle < 60
                            and not probe):
                        time.sleep(t.retry_after + 1)
                        tries_throttle += 1
                        continue
                    raise
                st["requests_used"] += 1
                n_req += 1
                if status != 200 or payload is None:
                    log(f"  HTTP {status} — {str(payload)[:300]}")
                    save_state(st)
                    return 1
                got = extract_records(payload)
                records.extend(got)
                url = payload.get("next")
                if url and st["requests_used"] >= DAILY_BUDGET and not probe:
                    log("  budget atteint en pleine pagination — reprise plus tard.")
                    break
        except Throttled as t:
            st["last_throttle_at"] = time.time()
            save_state(st)
            log(f"THROTTLED — retry_after={t.retry_after}s "
                f"({t.retry_after / 3600:.1f}h) — état sauvegardé, "
                f"{len(fetched)} ids sûrs.")
            return 2

        by_id = {str(r["id"]): r for r in records}
        os.makedirs(STORE, exist_ok=True)
        fname = os.path.join(STORE, f"resp_{st['next_file_idx']:04d}.json")
        with open(fname + ".tmp", "w") as f:
            json.dump({"requested": [oid], "count": len(by_id),
                       "records": list(by_id.values())}, f)
        os.replace(fname + ".tmp", fname)
        st["next_file_idx"] += 1
        fetched |= {int(k) for k in by_id}
        st["fetched_ids"] = sorted(fetched)
        save_state(st)
        log(f"  resp_{st['next_file_idx'] - 1:04d}: id {oid} "
            f"{'✓' if by_id else '✗ introuvable'} | total={len(fetched)} | "
            f"req={st['requests_used']}")

    log(f"PASSE TERMINÉE — {len(fetched)} ids couverts, "
        f"{st['requests_used']} requêtes ce cycle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
