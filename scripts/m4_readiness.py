#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M4 : porte de pré-vol (pre-flight gate).

Le protocole (docs/04-PROTOCOLE.md) n'autorise l'Épreuve Finale que si
TOUTE la chaîne de preuve tient. Ce script est la vérification mécanique
de cette chaîne, exécutée à froid, depuis les artefacts seuls :

  R1 — Pré-enregistrement : le scellé se recalcule EXACTEMENT (formule de
       build_corpus.py), 50 affaires, toutes présentes au corpus, protocole
       versionné, arbre git propre au départ.
  R2 — Audit zéro-fuite re-exécuté (pas lu : re-exécuté) — 14/14 PASS.
  R3 — Artefacts M3 présents ET reproductibles : re-construction complète
       des datasets personas/casefiles, empreintes avant/après identiques.
  R4 — Exclusion du scellé, implémentation INDÉPENDANTE de celle du
       builder et de l'audit (deux fois vérifié, zéro confiance partagée).
  R5 — Vérité terrain du scellé : DISPONIBILITÉ seulement (comptages,
       jamais les valeurs — aucune direction n'est lue ici).
  R6 — Artefacts M3b (adaptateurs + rapport) — attendus du côté Colab ;
       absents localement = PENDING, pas FAIL.
  R7 — Runner M4 (notebook) présent, AST-valide, garde anti-usage
       unique et garde du scellé présentes.

Verdict global : READY (tout présent) / PENDING (M3b ou runner manquant)
/ FAIL (la chaîne est cassée — l'épreuve est interdite).

Sortie : results/m4_readiness.{json,md}. Exit 1 sur FAIL uniquement
(utilisable en CI ; PENDING n'est pas un échec de chaîne).
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(REPO, "results")

entries = []


def log(cid, status, detail):
    """status: PASS | FAIL | PENDING"""
    entries.append({"check": cid, "status": status, "detail": detail})
    print(f"[{status}] {cid} — {detail}")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_state():
    """Fichiers suivis modifiés/non-suivis éventuels (avant toute écriture)."""
    out = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                         capture_output=True, text=True).stdout.strip()
    return out


# ------------------------------------------------------------------ R1 ----
def check_r1():
    p = os.path.join(REPO, "data", "processed", "stats_v1.json")
    if not os.path.exists(p):
        log("R1", "FAIL", "stats_v1.json introuvable")
        return None
    stats = json.load(open(p, encoding="utf-8"))
    ff = stats.get("five_four_selection") or {}
    cases = ff.get("cases") or []

    # formule EXACTE de build_corpus.py :
    #   selected_keys = sorted(...) ; sha256(json.dumps(selected_keys))
    recomputed = hashlib.sha256(
        json.dumps(sorted(cases)).encode()).hexdigest()
    if recomputed == ff.get("sealed_sha256"):
        log("R1.1", "PASS",
            f"scellé recalculé à l'identique ({recomputed[:20]}…, "
            f"{len(cases)} affaires)")
    else:
        log("R1.1", "FAIL",
            f"scellé divergent : attendu {ff.get('sealed_sha256')[:20]}…, "
            f"recalculé {recomputed[:20]}…")
        return stats
    if len(cases) == 50 and ff.get("n_selected") == 50 \
            and ff.get("n_available") == 79:
        log("R1.2", "PASS", "50 sélectionnées parmi 79 affaires 5-4")
    else:
        log("R1.2", "FAIL",
            f"tailles incohérentes : {len(cases)} cases / "
            f"n_selected={ff.get('n_selected')} / "
            f"n_available={ff.get('n_available')}")

    # les 50 doivent toutes matcher le corpus via la règle du builder ;
    # des entrées dupliquées du corpus (même docket scellé sous deux
    # graphies, p. ex. « No. 18-726 » / « No. 18–726. ») sont tolérées :
    # chaque entrée scellée doit être couverte, aucun dossier non-scellé
    # ne doit être attrapé.
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import m3_build_datasets as B
    corpus_cases, _, _, _ = B.load_corpus()
    is_sealed = B.sealed_dockets(stats)
    matched = [c for c in corpus_cases if is_sealed(c)]
    raw = stats["five_four_selection"]["cases"]

    def nk(s):
        s = (s or "").replace("\u2013", "-").replace("\u2014", "-")
        return re.sub(r"\s+", " ", s).strip().rstrip(".")

    def covers(case, entry):
        cd = case.get("docket_number") or ""
        return (cd == entry or nk(cd) == nk(entry)
                or bool(B.nums(cd) & B.nums(entry)))

    covered = [e for e in raw if any(covers(c, e) for c in matched)]
    stray = [c for c in matched
             if not any(covers(c, e) for e in raw)]
    if len(covered) == 50 and not stray:
        log("R1.3", "PASS",
            f"les 50 scellées matchent le corpus ({len(matched)} entrées — "
            "doublons de graphie exclus aussi)")
    else:
        log("R1.3", "FAIL",
            f"couverture scellée : {len(covered)}/50 couvertes, "
            f"{len(stray)} attrapée(s) hors scellé")

    # protocole versionné au HEAD courant
    tracked = subprocess.run(["git", "ls-files", "docs/04-PROTOCOLE.md"],
                             cwd=REPO, capture_output=True,
                             text=True).stdout.strip()
    if tracked:
        log("R1.4", "PASS", "docs/04-PROTOCOLE.md est versionné")
    else:
        log("R1.4", "FAIL", "protocole non suivi par git")

    dirty = [ln for ln in tree_state().splitlines()
             if ln and not ln.startswith("??")]   # '??' = outil non suivi,
    # pas une altération d'un artefact suivi ; toute modification d'un
    # fichier SUIVI (données, protocole, code) casse la chaîne.
    if dirty:
        log("R1.5", "FAIL", f"fichiers suivis modifiés au départ : "
                          f"{'; '.join(dirty[:3])}")
    else:
        log("R1.5", "PASS", "arbre git propre (fichiers suivis ; HEAD "
             + subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=REPO, capture_output=True,
                              text=True).stdout.strip() + ")")
    return stats


# ------------------------------------------------------------------ R2 ----
def check_r2():
    r = subprocess.run([sys.executable, "scripts/m15_audit.py"],
                       cwd=REPO, capture_output=True, text=True)
    jp = os.path.join(REPO, "data", "m15_store", "clean",
                      "audit_leak_journal.json")
    if not os.path.exists(jp):
        log("R2", "FAIL", "journal d'audit introuvable après exécution")
        return
    j = json.load(open(jp, encoding="utf-8"))
    n_total = j.get("summary", {}).get("checks_total", 0)
    n_fail = j.get("summary", {}).get("checks_failed", 0)
    verdict = j.get("verdict")
    if verdict == "PASS" and n_fail == 0 and n_total == 14 \
            and r.returncode == 0:
        log("R2", "PASS",
            f"audit zéro-fuite re-exécuté à froid : {n_total}/{n_total} PASS")
    else:
        log("R2", "FAIL",
            f"audit re-exécuté : verdict={verdict}, total={n_total}, "
            f"{n_fail} échec(s) (exit {r.returncode})")


# ------------------------------------------------------------------ R3 ----
def snapshot_m3():
    snap = {}
    for pat in ("casefiles/*.json", "personas/*/train.jsonl",
                "personas/*/test_votes.jsonl", "manifest.json"):
        for p in glob.glob(os.path.join(REPO, "data", "m3", pat)):
            rel = os.path.relpath(p, REPO)
            snap[rel] = sha256_file(p)
    return snap


def check_r3():
    mpath = os.path.join(REPO, "data", "m3", "manifest.json")
    if not os.path.exists(mpath):
        log("R3.1", "FAIL", "data/m3/manifest.json introuvable")
        return
    m = json.load(open(mpath, encoding="utf-8"))
    n_cf = m["case_files"]["train"] + m["case_files"]["test"]
    rows = sum(v["train_text_rows"] for v in m["personas"].values())
    n_texts = m["opinion_texts"]["texts_available"]
    ok = (n_cf == 518 and rows == 477 and n_texts == 793
          and len(m["personas"]) == 9)
    if ok:
        log("R3.1", "PASS",
            f"artefacts M3 : {n_cf} case files, {rows} lignes persona "
            f"train, {n_texts} textes v3, 9 juges")
    else:
        log("R3.1", "FAIL",
            f"artefacts M3 inattendus : {n_cf} case files, {rows} lignes, "
            f"{n_texts} textes, {len(m['personas'])} juges")

    before = snapshot_m3()
    r = subprocess.run([sys.executable, "scripts/m3_build_datasets.py"],
                       cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        log("R3.2", "FAIL", f"builder M3 en échec (exit {r.returncode})")
        return
    after = snapshot_m3()
    if before == after:
        log("R3.2", "PASS",
            f"re-construction déterministe : {len(after)} fichiers, "
            "empreintes identiques avant/après")
    else:
        drift = [k for k in set(before) | set(after)
                 if before.get(k) != after.get(k)]
        log("R3.2", "FAIL",
            f"dérive de reconstruction sur {len(drift)} fichier(s) : "
            + ", ".join(drift[:5]))


# ------------------------------------------------------------------ R4 ----
def check_r4(stats):
    """Implémentation INDÉPENDANTE : ne réutilise ni sealed_dockets ni
    l'audit — matcher écrit from scratch, confiance zéro partagée."""
    raw = stats["five_four_selection"]["cases"]
    # Normalisation INDEPENDANTE : alnum-minuscule (attrape les variantes de
    # ponctuation — « 145, Orig. » vs « 145 Orig ») + intersection de jetons
    # \d+-\d+ (attrape « No. 18-726 » vs « 18-726 »). Aucun emprunt au
    # builder ni à l'audit : c'est la non-confiance partagée qui a attrapé
    # la fuite « 145, Orig. » que la règle officielle laissait passer.
    sealed_alnum = {re.sub(r"[^a-z0-9]", "", s.lower()) for s in raw}
    sealed_tokens = set()
    for s in raw:
        sealed_tokens |= set(re.findall(r"\d+-\d+",
                                        s.replace("–", "-")
                                         .replace("—", "-")))

    def leaks(docket):
        d = (docket or "").replace("–", "-").replace("—", "-")
        return (re.sub(r"[^a-z0-9]", "", d.lower()) in sealed_alnum
                or bool(set(re.findall(r"\d+-\d+", d)) & sealed_tokens))

    leaks_found = []
    for p in glob.glob(os.path.join(REPO, "data", "m3", "casefiles",
                                    "*.json")):
        cf = json.load(open(p, encoding="utf-8"))
        if leaks(cf.get("docket")):
            leaks_found.append(os.path.basename(p))
    n_persona_rows = 0
    for p in glob.glob(os.path.join(REPO, "data", "m3", "personas", "*",
                                    "*.jsonl")):
        for line in open(p, encoding="utf-8"):
            if not line.strip():
                continue
            n_persona_rows += 1
            if leaks(json.loads(line).get("docket")):
                leaks_found.append(os.path.relpath(p, REPO))
    if leaks_found:
        log("R4", "FAIL", f"scellée(s) trouvée(s) dans M3 : "
                          f"{leaks_found[:5]}")
    else:
        log("R4", "PASS",
            f"exclusion du scellé confirmée par le matcher indépendant "
            f"({n_persona_rows} lignes persona + case files)")


# ------------------------------------------------------------------ R5 ----
def check_r5(stats):
    """DISPONIBILITÉ de la vérité terrain, jamais les valeurs : on compte
    les lignes où SCDB fournit direction/disposition/votes, on ne lit
    aucune étiquette. Implémentation unique : m4_scoring.load_truth, la
    même que l'épreuve utilisera (la liste scellée gouverne — 50 entrées
    = 50 affaires, dockets consolidés résolus vers l'affaire principale).
    Le plan d'analyse stratifié est consigné ici (avant toute évaluation)
    : strate « futur » (OT2020+) vs strate « entrelacée » (OT2015-2019)."""
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import m3_build_datasets as B
    import m4_scoring as MS
    corpus_cases, _, _, _ = B.load_corpus()
    is_sealed = B.sealed_dockets(stats)
    sealed_list = stats["five_four_selection"]["cases"]
    truth = MS.load_truth(corpus_cases, is_sealed, want="sealed",
                          sealed_list=sealed_list)

    n_dir = sum(1 for t in truth if t["direction"])
    n_disp = sum(1 for t in truth if t["disposition"])
    n_votes = sum(len(t["votes"]) for t in truth)
    n_future = sum(1 for t in truth if t["stratum"] == "future")
    n_inter = len(truth) - n_future

    ok = (len(truth) == 50 and n_dir >= 45 and n_disp >= 45
          and n_votes >= 400)
    log("R5.1" if ok else "R5", "PASS" if ok else "FAIL",
        f"vérité terrain disponible (les 50 entrées scellées) : direction "
        f"{n_dir}/50, disposition {n_disp}/50, votes par juge {n_votes}")
    log("R5.2", "PASS",
        f"strates pré-enregistrées : {n_future} futures (OT2020+) / "
        f"{n_inter} entrelacées (OT2015-2019) — McNemar global + stratifié")


# ------------------------------------------------------------------ R6 ----
def check_r6():
    """Adaptateurs M3b : produits côté Colab par l'utilisateur. Leur
    absence n'est pas un échec de chaîne — c'est un blocage de calendrier."""
    places = [os.path.join(REPO, "results", "m3b_report.json"),
              os.path.join(REPO, "m3b_report.json")]
    report = next((p for p in places if os.path.exists(p)), None)
    adapters = os.path.join(REPO, "adapters")
    n_ad = len(glob.glob(os.path.join(adapters, "*"))) if \
        os.path.isdir(adapters) else 0
    if report and n_ad >= 7:
        rep = json.load(open(report, encoding="utf-8"))
        log("R6", "PASS",
            f"M3b présent : rapport ({rep.get('model')}) + {n_ad} "
            "adaptateurs")
    else:
        log("R6", "PENDING",
            "artefacts M3b absents localement (entraînement Colab en "
            "cours) : déposer m3b_adapters_*.zip → adapters/ + "
            "m3b_report.json à la racine du repo")


# ------------------------------------------------------------------ R7 ----
def check_r7():
    nb = os.path.join(REPO, "notebooks", "m4_epreuve_finale.ipynb")
    if not os.path.exists(nb):
        log("R7", "PENDING", "notebook m4_epreuve_finale.ipynb non généré")
        return
    r = subprocess.run([sys.executable, "scripts/validate_notebook.py",
                        "notebooks/m4_epreuve_finale.ipynb"],
                       cwd=REPO, capture_output=True, text=True)
    src = open(nb, encoding="utf-8").read()
    guards = ("sealed_sha256" in src) and ("je-brise-le-sceau" in src) \
        and ("EXAM_LOCK" in src)
    if r.returncode == 0 and guards:
        log("R7", "PASS",
            "runner M4 présent, AST-valide, gardes (scellé + usage "
            "unique) en place")
    else:
        log("R7", "FAIL",
            f"runner M4 invalide (exit {r.returncode}, gardes={guards})")


# ------------------------------------------------------------------ main --
def main():
    os.makedirs(RESULTS, exist_ok=True)
    stats = check_r1()
    if stats is None:
        stats = json.load(open(os.path.join(
            REPO, "data", "processed", "stats_v1.json"), encoding="utf-8"))
    check_r2()
    check_r3()
    check_r4(stats)
    check_r5(stats)
    check_r6()
    check_r7()

    n_fail = sum(1 for e in entries if e["status"] == "FAIL")
    n_pend = sum(1 for e in entries if e["status"] == "PENDING")
    if n_fail:
        verdict = "FAIL — l'Épreuve Finale est INTERDITE jusqu'à réparation"
    elif n_pend:
        verdict = "PENDING — chaîne intacte, M3b/runner en attente"
    else:
        verdict = "READY — l'Épreuve Finale peut être exécutée (une fois)"

    doc = {
        "gate": "scripts/m4_readiness.py",
        "verdict": verdict,
        "counts": {"pass": len(entries) - n_fail - n_pend,
                   "fail": n_fail, "pending": n_pend},
        "sealed_sha256": stats["five_four_selection"]["sealed_sha256"],
        "checks": entries,
    }
    with open(os.path.join(RESULTS, "m4_readiness.json"), "w",
              encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

    md = ["# M4 — Porte de pré-vol (pre-flight gate)", "",
          f"**Verdict : {verdict}**", "",
          f"Empreinte du scellé : `{doc['sealed_sha256']}`", "",
          "| Contrôle | État | Détail |", "|---|---|---|"]
    for e in entries:
        md.append(f"| {e['check']} | {e['status']} | {e['detail']} |")
    md += ["", "La chaîne de preuve : protocole versionné → scellé "
           "recalculé → audit re-exécuté → reconstruction déterministe → "
           "exclusion indépendante → disponibilité de la vérité terrain "
           "(jamais ses valeurs) → adaptateurs → runner. L'épreuve "
           "s'exécute une seule fois, quel que soit le résultat."]
    with open(os.path.join(RESULTS, "m4_readiness.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"\nverdict: {verdict} → results/m4_readiness.md")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
