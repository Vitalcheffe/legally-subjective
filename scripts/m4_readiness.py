#!/usr/bin/env python3
"""m4_readiness.py — pré-vol de l'Épreuve Finale (M4).

Une seule commande avant l'étape 5 du protocole scellé (docs/04-PROTOCOLE.md) :
vérifie que TOUTES les préconditions sont réunies et liste précisément ce qui
manque. Ne lit du scellé que les identifiants de docket et des comptages de
vérité terrain — aucune évaluation, aucun réglage, aucun contenu d'affaire
(« on ne touche pas au scellé »).

Sections :
  R1  chaîne de pré-enregistrement (corpus gelé, scellé intact, protocole)
  R2  zéro-fuite (m15_audit.py re-exécuté en processus frais, verdict lu)
  R3  artefacts M3b (rapport + adaptateurs) — LE portillon de l'étape 5
  R4  entrées des conditions (baselines, personas, casefiles, textes v3)
  R5  vérité terrain du scellé (comptages SCDB uniquement)

Sortie : results/m4_readiness.{md,json}.
Exit : 0 = READY ; 3 = BLOCKED (le rapport est écrit dans les deux cas).
Adapter dir : data/m3/adapters/ par défaut, ou variable M4_ADAPTER_DIR.
"""

import glob
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import m3_build_datasets as B  # noqa: E402  (load_corpus, sealed_dockets...)

RESULTS = os.path.join(ROOT, "results")
ACTIVE_PERSONAS = ["JGRoberts", "CThomas", "SAAlito", "SSotomayor",
                   "EKagan", "NMGorsuch", "BMKavanaugh"]
BASE_ONLY = ["ACBarrett", "KBJackson"]
EXPECTED_TRAIN_ROWS = {"JGRoberts": 43, "CThomas": 146, "SAAlito": 83,
                       "SSotomayor": 95, "EKagan": 50, "NMGorsuch": 39,
                       "BMKavanaugh": 21, "ACBarrett": 0, "KBJackson": 0}
AUDIT_JOURNAL = os.path.join(ROOT, "data", "m15_store", "clean",
                             "audit_leak_journal.json")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    checks = []  # (section, name, status, detail)

    def rec(section, name, ok, detail, warn=False):
        status = "PASS" if ok else ("WARN" if warn else "FAIL")
        checks.append((section, name, status, detail))
        return ok

    # ------------------------------------------------------------- R1 ----
    stats_path = os.path.join(ROOT, "data", "processed", "stats_v1.json")
    stats = json.load(open(stats_path, encoding="utf-8"))
    rec("R1", "corpus_gelé", stats.get("n_cases") == 569
        and stats.get("n_opinions") == 1778,
        f"n_cases={stats.get('n_cases')}, n_opinions={stats.get('n_opinions')}"
        " (valeurs gelées attendues : 569 / 1778)")

    sel = stats.get("five_four_selection", {})
    rec("R1", "jeu_scellé_défini", sel.get("n_selected") == 50,
        f"n_available={sel.get('n_available')}, n_selected="
        f"{sel.get('n_selected')}")

    recomputed = hashlib.sha256(
        json.dumps(sel.get("cases", [])).encode()).hexdigest()
    ref = sel.get("sealed_sha256")
    if recomputed == ref:
        seal_detail = "sealed_sha256 recalculé = référence"
    else:
        seal_detail = ("sealed_sha256 recalculé ≠ référence ("
                       + str(ref)[:16] + "…)")
    rec("R1", "scellé_intact", recomputed == ref, seal_detail)

    proto = os.path.join(ROOT, "docs", "04-PROTOCOLE.md")
    proto_sha = sha256_file(proto) if os.path.exists(proto) else None
    rec("R1", "protocole_préenregistré", proto_sha is not None,
        f"docs/04-PROTOCOLE.md sha256="
        f"{proto_sha[:16] + '…' if proto_sha else 'ABSENT'}")
    for f in ("LICENSE", "CITATION.cff"):
        rec("R1", f"emballage_{f}", os.path.exists(os.path.join(ROOT, f)),
            "présent" if os.path.exists(os.path.join(ROOT, f)) else "absent")

    # ------------------------------------------------------------- R2 ----
    audit_rc = None
    audit_verdict = None
    audit_failed = []
    try:
        r = subprocess.run([sys.executable,
                            os.path.join(HERE, "m15_audit.py")],
                           capture_output=True, text=True, timeout=600,
                           cwd=ROOT)
        audit_rc = r.returncode
        j = json.load(open(AUDIT_JOURNAL, encoding="utf-8"))
        audit_verdict = j.get("verdict")
        audit_failed = [e["check"] for e in j.get("entries", [])
                        if e.get("verdict") != "PASS"]
        # le journal committé reste l'artefact de clôture M1.5 : on le
        # restaure — la preuve de la re-exécution vit dans CE rapport.
        subprocess.run(["git", "checkout", "--",
                        AUDIT_JOURNAL.replace(".json", ".md"),
                        AUDIT_JOURNAL], cwd=ROOT, capture_output=True)
    except Exception as e:  # noqa: BLE001 — toute défaillance = FAIL honnête
        audit_verdict = f"ERREUR: {e}"
    rec("R2", "audit_zéro_fuite_reexécuté",
        audit_rc == 0 and audit_verdict == "PASS" and not audit_failed,
        f"m15_audit.py rc={audit_rc}, verdict={audit_verdict}, "
        f"échecs={audit_failed or 'aucun'}")

    # ------------------------------------------------------------- R3 ----
    report_path = os.path.join(RESULTS, "m3b_report.json")
    m3b = json.load(open(report_path, encoding="utf-8")) \
        if os.path.exists(report_path) else None
    rec("R3", "rapport_m3b", m3b is not None,
        "results/m3b_report.json présent" if m3b is not None
        else "results/m3b_report.json ABSENT — entraînement persona "
             "inachevé (sessions Colab côté utilisateur)")

    done = []
    if isinstance(m3b, dict):
        for k, v in m3b.items():
            if k in ACTIVE_PERSONAS + BASE_ONLY:
                ok = bool(v) if not isinstance(v, dict) else bool(
                    v.get("done", v.get("status") in ("done", "ok", "PASS")))
                if ok:
                    done.append(k)
    adapters_dir = os.environ.get(
        "M4_ADAPTER_DIR", os.path.join(ROOT, "data", "m3", "adapters"))
    adapters = sorted(os.listdir(adapters_dir)) \
        if os.path.isdir(adapters_dir) else []
    rec("R3", "adaptateurs", len(adapters) >= 7,
        f"{len(adapters)} adaptateurs dans {os.path.relpath(adapters_dir, ROOT)}"
        f" ({', '.join(adapters) if adapters else 'répertoire absent'})")

    mem = isinstance(m3b, dict) and (
        "memorization" in m3b
        or any(isinstance(v, dict) and "memorization" in v
               for v in m3b.values()))
    rec("R3", "audits_anti_mémorisation", bool(mem),
        "section memorization présente dans m3b_report.json" if mem
        else "section memorization ABSENTE (section 7bis du notebook)")

    missing = [p for p in ACTIVE_PERSONAS
               if p not in done and p not in adapters]
    rec("R3", "personas_complets", not missing,
        f"personas actifs couverts : {sorted(set(done) | set(adapters)) or '—'}"
        f" ; manquants : {missing or 'aucun'} ; "
        f"base-prompt-only (pré-enregistré) : {BASE_ONLY}")

    # ------------------------------------------------------------- R4 ----
    baselines = json.load(open(os.path.join(RESULTS, "m2_baselines.json"),
                               encoding="utf-8"))
    b4 = baselines.get("B4_justice_ideology", {})
    b4_acc = b4.get("vote_accuracy") if isinstance(b4, dict) else None
    rec("R4", "baselines_condition_D", b4_acc is not None,
        f"B4 (barre à battre, niveau vote) = {b4_acc}")

    rows = {}
    for seat in sorted(EXPECTED_TRAIN_ROWS):
        p = os.path.join(ROOT, "data", "m3", "personas", seat, "train.jsonl")
        n = sum(1 for _ in open(p, encoding="utf-8")) if os.path.exists(p) \
            else -1
        rows[seat] = n
    total_rows = sum(max(0, v) for v in rows.values())
    mism = {k: (v, EXPECTED_TRAIN_ROWS[k]) for k, v in rows.items()
            if v != EXPECTED_TRAIN_ROWS[k]}
    rec("R4", "personas_train", total_rows == 477 and not mism,
        f"{total_rows} lignes train (477 attendues) ; "
        f"écarts : {mism or 'aucun'}")

    n_cf = len(glob.glob(os.path.join(ROOT, "data", "m3", "casefiles",
                                      "*.json")))
    rec("R4", "casefiles", n_cf == 519,
        f"{n_cf} casefiles (519 attendues : 308 train + 211 test)")

    clean = json.load(open(os.path.join(ROOT, "data", "m15_store", "clean",
                                        "clean_report.json"),
                           encoding="utf-8"))
    n_v3 = clean.get("n_kept")
    rec("R4", "textes_v3", n_v3 == 793,
        f"textes distincts v3 = {n_v3} (793 attendus)")

    # ------------------------------------------------------------- R5 ----
    cases, _, _, _ = B.load_corpus()
    is_sealed = B.sealed_dockets(stats)
    sealed = [c for c in cases if is_sealed(c)]
    rec("R5", "taille_du_scellé", len(sealed) == 50,
        f"{len(sealed)} affaires scellées (50 attendues)")

    with_scdb = [c for c in sealed if c.get("scdb")]
    with_split = [c for c in sealed
                  if str((c.get("scdb") or {}).get("maj_votes", "")).strip()
                  and str((c.get("scdb") or {}).get("min_votes", "")).strip()]
    with_dir = [c for c in sealed
                if str((c.get("scdb") or {})
                       .get("decision_direction", "")).strip()]
    j_rows = [j for c in sealed for j in c.get("justices", [])]
    j_votes = [j for j in j_rows if str(j.get("vote", "")).strip()]
    j_dir = [j for j in j_rows if str(j.get("direction", "")).strip()]
    no_gt = [c.get("docket_number", "?") for c in sealed if not c.get("scdb")]
    gt_detail = (f"SCDB join {len(with_scdb)}/50 ; split maj/min "
                 f"{len(with_split)}/50 ; direction d'affaire {len(with_dir)}/50 ; "
                 f"votes par juge {len(j_votes)}/{len(j_rows)} lignes (avec "
                 f"direction {len(j_dir)}) — comptages seuls, contenu non lu")
    if no_gt:
        gt_detail += (" ; sans vérité terrain (constaté avant tout envoi au "
                      f"modèle, cause documentée du protocole) : {no_gt}")
    rec("R5", "vérité_terrain", len(with_scdb) == 50 and len(j_votes) >= 300,
        gt_detail, warn=True)

    # -------------------------------------------------------- verdict ----
    blockers = [f"{s}.{n}" for s, n, st, _ in checks if st == "FAIL"]
    ready = not blockers
    out = {
        "file": "results/m4_readiness.json",
        "tool": "scripts/m4_readiness.py",
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "preregistration_chain": {
            "protocol_sha256": proto_sha,
            "stats_v1_sha256": sha256_file(stats_path),
            "sealed_sha256": recomputed,
            "sealed_matches_reference": recomputed == ref,
        },
        "audit_reexecution": {"rc": audit_rc, "verdict": audit_verdict,
                              "failed": audit_failed},
        "m3b": {"report_present": m3b is not None,
                "justices_in_report": done,
                "adapters": adapters,
                "adapters_dir": os.path.relpath(adapters_dir, ROOT)},
        "sealed_ground_truth": {
            "cases": len(sealed), "with_scdb": len(with_scdb),
            "with_split": len(with_split), "with_direction": len(with_dir),
            "justice_rows": len(j_rows), "justice_votes": len(j_votes),
            "justice_votes_with_direction": len(j_dir),
            "no_ground_truth_dockets": no_gt,
            "note": ("identifiants et comptages uniquement ; aucune lecture "
                     "de contenu, aucune évaluation avant l'étape 5")},
        "checks": [{"section": s, "name": n, "status": st, "detail": d}
                   for s, n, st, d in checks],
        "verdict": "READY" if ready else "BLOCKED",
        "blockers": blockers,
    }
    os.makedirs(RESULTS, exist_ok=True)
    json.dump(out, open(os.path.join(RESULTS, "m4_readiness.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)

    lines = ["# M4 — rapport de pré-vol (readiness gate)", ""]
    cur = None
    for s, n, st, d in checks:
        if s != cur:
            lines += ["", f"## {s}", ""]
            cur = s
        lines.append(f"- **{st}** {s}.{n} — {d}")
    lines += ["", f"## Verdict : **{out['verdict']}**", ""]
    if blockers:
        lines.append("Bloqué par : " + ", ".join(blockers) + ".")
        lines.append("L'étape 5 (Épreuve Finale) ne peut être exécutée que "
                     "une fois ces portes fermées — une seule passe, "
                     "protocole scellé.")
    else:
        lines.append("Toutes les préconditions sont réunies. L'étape 5 "
                     "peut être exécutée — une seule passe, publier quoi "
                     "qu'il arrive.")
    lines.append("")
    open(os.path.join(RESULTS, "m4_readiness.md"), "w",
         encoding="utf-8").write("\n".join(lines))

    for s, n, st, d in checks:
        print(f"[{st}] {s}.{n} — {d}")
    print(f"\nverdict: {out['verdict']}"
          + (f" → {os.path.join(RESULTS, 'm4_readiness.md')}" ))
    return 0 if ready else 3


if __name__ == "__main__":
    sys.exit(main())
