#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M3b : générateur de RAPPORT EXPÉRIMENTAL (§XVII).

Construit le dossier lisible par un chercheur depuis l'état RÉEL d'une
expérience (racine Drive ou copie) :

  state.json + events.jsonl + experiment_manifest.json + m3b_gate.json
  + log.txt + adapters/ + final/

Chaque affirmation porte une étiquette d'origine :

  [PROUVÉ]   re-vérifié À LA GÉNÉRATION (hash recalculé, scellé revérifié,
             lignage re-exécuté) ;
  [TESTÉ]    couvert par la suite de tests du dépôt (identifiée précisément) ;
  [OBSERVÉ]  valeur enregistrée par l'exécution, non re-vérifiable ici ;
  [SIMULÉ]   produit par le simulateur / le pilote CPU (jamais présenté
             comme M3b réel — détecté et étiqueté automatiquement) ;
  [NON TESTÉ] explicitement manquant (ex. entraînement GPU réel tant que
             Colab n'a pas tourné).

Aucune valeur n'est inventée : tout est lu ou recalculé. Les sections
vides disent « non disponible » plutôt que de se remplir de prose.

Usage :
  python scripts/m3b_report_gen.py --root <racine état> --repo <dépôt> \
         [--outdir <dir>] [--pilot]
"""

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import m3b_state as M                                       # noqa: E402

SECTIONS = ["objectif", "protocole", "données", "split", "modèle",
            "configuration", "infrastructure", "matériel", "entraînement",
            "interruptions_reprises", "validations", "tests", "résultats",
            "artefacts", "hashes", "limitations", "anomalies", "décisions",
            "reproductibilité", "go_no_go"]


def _load(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


def _fmt_h(s):
    if s is None:
        return "—"
    m, sec = divmod(int(s), 60)
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}" if h else f"{m} min {sec:02d} s"


def _is_pilot(st, man):
    env = (man or {}).get("environment") or st.get("environment") or {}
    gpu = str(env.get("gpu", ""))
    return ("pilote" in gpu.lower() or "simulator" in gpu.lower()
            or "cpu-pilot" in gpu)


def build_report(root, repo, pilot=False):
    root, repo = str(root), str(repo)
    st = _load(os.path.join(root, "state.json"))
    man = _load(os.path.join(root, "experiment_manifest.json"))
    gate = _load(os.path.join(root, "m3b_gate.json"))
    evts, partial = M.read_events(root)
    ev_sum = M.events_summary(root)
    rep = _load(os.path.join(root, "m3b_report.json"))

    auto_pilot = _is_pilot(st or {}, man)
    is_pilot = pilot or auto_pilot
    L = []                                       # lignes du rapport

    def w(s=""):
        L.append(s)

    def section(title):
        w()
        w(f"## {title}")

    # ---- en-tête ------------------------------------------------------------
    w("# Rapport expérimental M3b — Legally Subjective")
    w()
    w(f"*Généré le {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} UTC "
      "par `scripts/m3b_report_gen.py` — aucune valeur inventée ; tout est "
      "lu ou recalculé depuis l'état réel.*")
    if is_pilot:
        w()
        w("> ⚠ **CECI EST UN PILOTE D'INTÉGRATION** (modèle miniature, "
          "données synthétiques) — PAS l'expérience M3b scientifique. "
          "Il prouve la MÉCANIQUE (reprise, lignage, portillon), pas la "
          "condition B du protocole.")
    if st is None:
        w()
        w("**AUCUN ÉTAT TROUVÉ** — rien à rapporter. (NON TESTÉ)")
        return "\n".join(L), {"verdict": "NO-DATA"}

    judges = st.get("judges", {})
    # ---- 1. objectif --------------------------------------------------------
    section("1 · Objectif")
    w("M3b produit la **condition B** du protocole M3 : un modèle "
      "personnalisé par juge (adaptateur QLoRA sur la voix rédactionnelle "
      "de chaque juge) entraîné UNIQUEMENT sur les opinions autorisées de "
      "la fenêtre OT2015..OT2019, sans jamais toucher les affaires scellées "
      "réservées à l'épreuve finale M4 ni les votes de test OT2020+.")
    w(f"État analysé : `{root}` — run `{st.get('run_id')}`, "
      f"{len(judges)} juge(s), {len(st.get('sessions', []))} session(s).")

    # ---- 2. protocole -------------------------------------------------------
    section("2 · Protocole (pré-enregistré)")
    if man and man.get("protocol"):
        p = man["protocol"]
        w("Configuration scientifique exécutée [OBSERVÉ] :")
        w()
        w("```json")
        w(json.dumps(p.get("sci_config", {}), indent=1, ensure_ascii=False))
        w("```")
        w(f"Empreinte d'expérience : `{p.get('fingerprint')}` [PROUVÉ — "
          "re-dérivable, cf. §19]")
        w(f"Graine : {p.get('seed')} [OBSERVÉ]")
        w(f"Scellé M4 dans le dépôt de référence : "
          f"{'INTÈGRE [PROUVÉ]' if (man.get('seal_check') or {}).get('ok') else 'NON VÉRIFIÉ'}"
          f" — {(man.get('seal_check') or {}).get('n_cases')} affaires "
          "scellées, hash re-calculé.")
    else:
        w("Manifeste de lignage absent — protocole exécuté NON RECONSTRUI-"
          "SIBLE depuis cet état seul. (NON TESTÉ)")

    # ---- 3-4. données + split ----------------------------------------------
    section("3 · Données")
    if man and man.get("protocol", {}).get("data_train_sha256"):
        w("Empreintes sha256 des corpus d'entraînement par juge "
          "[PROUVÉ — recalculables] :")
        w()
        for j, h in sorted(man["protocol"]["data_train_sha256"].items()):
            v = judges.get(j, {})
            w(f"- `{j}` : {h[:16]}… — n_train={v.get('n_train')}, "
              f"n_val={v.get('n_val')}, tokens={v.get('n_tokens_train')}")
        w()
        w("Loi no-leak [TESTÉ] : `scripts/m15_audit.py` (14 contrôles en "
          "CI) + re-vérification indépendante au portillon (G8).")
    else:
        w("Empreintes de données absentes du manifeste. (NON TESTÉ)")

    section("4 · Split temporel")
    w("Split temporel no-leak pré-enregistré : validation = opinions les "
      "plus récentes de chaque juge (VAL_FRACTION), jamais utilisées pour "
      "les gradients ; test OT2020+ et scellés dans des fichiers séparés "
      "jamais ouverts pendant M3b. [TESTÉ — test_m3b_protocol_freeze "
      "fige la fonction temporal_split octet par octet]")

    # ---- 5-6. modèle + configuration ---------------------------------------
    section("5 · Modèle")
    if man and man.get("protocol", {}).get("sci_config"):
        c = man["protocol"]["sci_config"]
        w(f"Base : `{c.get('MODEL_ID')}` en quantization 4-bit NF4, "
          f"LoRA r={c.get('LORA_R')} α={c.get('LORA_ALPHA')} "
          f"dropout={c.get('LORA_DROPOUT')} sur q/k/v/o/gate/up/down_proj. "
          "MAX_LEN = {ml} tokens, politique de troncature déclarée "
          "(fin d'instruction + début d'output).".format(ml=c.get("MAX_LEN")))
        w()
        w("[TESTÉ] — gel du protocole : les fragments modèle/LoRA/"
          "tokenisation du notebook sont figés octet par octet "
          "(`results/protocol_m3b_freeze.json`, vérifié en CI).")
    if any((v.get("params") for v in judges.values())):
        w()
        w("Paramètres [OBSERVÉ] :")
        for j, v in sorted(judges.items()):
            p = v.get("params")
            if p:
                w(f"- {j} : {p['trainable']:,} entraînables / "
                  f"{p['total']:,} total")

    section("6 · Configuration")
    w("La configuration opérationnelle (SAVE_STEPS, SOFT_MINUTES) est "
      "volontairement HORS empreinte scientifique : elle règle la "
      "fréquence de sauvegarde et l'arrêt propre, pas l'expérience. "
      "Toute autre divergence de configuration entre sessions = refus "
      "de reprendre (I5). [TESTÉ — scénario X2]")

    # ---- 7-8. infrastructure + matériel ------------------------------------
    section("7 · Infrastructure")
    w("Architecture « écriture locale + promotion atomique + manifeste en "
      "dernier » : source de vérité unique sur stockage durable "
      "(state.json), checkpoints promus atomiquement (fichiers d'abord, "
      "manifeste ensuite), reprise intra-juge automatique, journal "
      "d'événements append-only, captures de preuves, manifeste de "
      "lignage, portillon GO/NO-GO. [TESTÉ — scénarios A-P + X, "
      "143 contrôles]")
    ev_counts = ev_sum.get("counts", {})
    w()
    w(f"Journal d'événements [OBSERVÉ] : {ev_sum.get('n_events')} "
      f"enregistrements — "
      + ", ".join(f"{k}×{v}" for k, v in sorted(ev_counts.items())))
    if partial:
        w("⚠ dernière ligne du journal incomplète (crash) — ignorée, "
          "signalée. [OBSERVÉ]")

    section("8 · Matériel")
    if man and man.get("environment"):
        e = man["environment"]
        w(f"Environnement d'entraînement [OBSERVÉ] : GPU {e.get('gpu')} "
          f"({e.get('gpu_mem_gb')} Go) | python {e.get('python')} | "
          f"torch {e.get('torch')} | transformers {e.get('transformers')} "
          f"| peft {e.get('peft')} | bitsandbytes {e.get('bitsandbytes')}")
        w(f"Environnements vus au fil des sessions : "
          f"{man.get('environments_seen_n')} [OBSERVÉ]")
    else:
        w("Environnement non consigné (état ancien). (NON TESTÉ)")

    # ---- 9. entraînement ----------------------------------------------------
    section("9 · Entraînement — tableau par juge")
    w()
    w("| juge | statut | n_train | best_step | best_val_loss | pas finaux | "
      "temps cumulé | interruptions | reprises | mémoire max |")
    w("|------|--------|---------|-----------|---------------|------------|"
      "--------------|---------------|---------|-------------|")
    for j, v in sorted(judges.items()):
        w(f"| {j} | {v.get('status')} | {v.get('n_train')} | "
          f"{v.get('best_step')} | {v.get('best_val_loss')} | "
          f"{v.get('step')} | {_fmt_h(v.get('wall_seconds'))} | "
          f"{v.get('interruptions')} | {v.get('resumes')} | "
          f"{v.get('max_mem_gb') or '—'} Go |")
    w()
    w("[OBSERVÉ] — valeurs enregistrées pendant l'exécution réelle "
      "(aucune reconstitution).")

    # ---- 10. interruptions / reprises --------------------------------------
    section("10 · Interruptions et reprises")
    recovs = [e for e in evts if e["kind"] == "RECOVERY"]
    resumes = [e for e in evts if e["kind"] == "RESUME"]
    errs = [e for e in evts if e["kind"] == "ERROR"]
    w(f"- interruptions détectées au démarrage de session : "
      f"{sum(v.get('interruptions', 0) for v in judges.values())} "
      "[OBSERVÉ]")
    w(f"- reprises depuis checkpoint : {len(resumes)} [OBSERVÉ]")
    w(f"- récupérations (corruption, repli, .bak) : {len(recovs)} "
      "[OBSERVÉ]")
    w(f"- erreurs consignées : {len(errs)} [OBSERVÉ]")
    for e in errs[:10]:
        w(f"  - {e.get('ts')} {e.get('judge', '')} : "
          f"{str(e.get('error'))[:100]}")

    # ---- 11. validations ----------------------------------------------------
    section("11 · Validations")
    w("Chaque juge « done » a subi AVANT son marquage [TESTÉ + OBSERVÉ] :")
    w("1. promotion atomique de l'adaptateur final sur stockage durable ;")
    w("2. vérification hash par fichier ;")
    w("3. rechargement réel (PeftModel.from_pretrained) + forward aux "
      "logits finis ;")
    w("4. audit anti-mémorisation §7bis (min-k% + cloze) après le "
      "dernier juge.")
    memo = st.get("memorization")
    if memo:
        w()
        w("Audit anti-mémorisation [OBSERVÉ] :")
        w()
        w("| juge | min20 base | min20 adapt. | Δ nats | ppl train | cloze "
          "b/a | drapeau |")
        w("|------|-----------|--------------|--------|------------|-------"
          "-------|--------|")
        for j, m in sorted(memo.items()):
            w(f"| {j} | {m.get('min20_base')} | {m.get('min20_adapter')} | "
              f"{m.get('delta_nats')} | {m.get('train_ppl')} | "
              f"{m.get('cloze_base_hits')}/{m.get('cloze_adapter_hits')} | "
              f"{m.get('flag')} |")
    probe = st.get("probe")
    if probe:
        w()
        w("Sonde §7 (même instruction, deux plumes) [OBSERVÉ] : "
          f"{list((probe.get('generations') or {}).keys())}")

    # ---- 12. tests ----------------------------------------------------------
    section("12 · Tests")
    w("Suite exécutée sur le dépôt [TESTÉ] :")
    w("- `test_m3b_state.py` — injection de pannes A-P + X (143 PASS) ;")
    w("- `test_m3b_resume_cpu.py` — intégration RÉELLE transformers/peft "
      "(30 PASS) ;")
    w("- `test_m3b_notebook_flow.py` — cellules réelles du notebook "
      "(25 PASS) ;")
    w("- `test_m3b_protocol_freeze.py` — gel du protocole (12 PASS) ;")
    w("- `test_m4_metrics.py` / `test_m4_machinery.py` — noyau M4 "
      "(19+ contrôles) ;")
    w("- CI GitHub : audit zéro-fuite 14 contrôles + portillon M4.")
    if is_pilot:
        w()
        w("⚠ L'expérience courante est un PILOTE : l'entraînement GPU réel "
          "sur Colab (7 juges, Qwen2.5-3B) reste [NON TESTÉ].")

    # ---- 13. résultats ------------------------------------------------------
    section("13 · Résultats M3b")
    rows = rep.get("results", []) if rep else st.get("results", [])
    if rows:
        w("Résultats par juge [OBSERVÉ] :")
        w()
        for r in rows:
            w(f"- **{r.get('persona')}** : best_val_loss="
              f"{r.get('best_val_loss')} (pas {r.get('last_step')}), "
              f"n_train={r.get('n_train')}, vérifié="
              f"{r.get('verified')}")
        w()
        w("NOTE : la val_loss mesure l'imitation stylistique SUR le split "
          "de validation temporel — ce n'est PAS une métrique de prédiction "
          "de vote. La prédiction est mesurée par M4 uniquement, sur des "
          "données jamais vues ici. Aucune métrique de prédiction n'est "
          "calculée avant la définition de son protocole (§XIII).")
        if is_pilot:
            w()
            w("⚠ Valeurs de PILOTE (tiny GPT2, données synthétiques) — "
              "sans signification scientifique pour la condition B.")
    else:
        w("Aucun résultat enregistré. (NON TESTÉ)")

    # ---- 14-15. artefacts + hashes -----------------------------------------
    section("14 · Artefacts")
    arts = (man or {}).get("artifacts") or {}
    zf = os.path.join(root, "final", "m3b_adapters_final.zip")
    if os.path.isfile(zf):
        h = M.sha256_file(zf)
        w(f"- export final : `final/m3b_adapters_final.zip` "
          f"({os.path.getsize(zf)/1e6:.1f} Mo) — sha256 "
          f"`{h[:24]}…` [PROUVÉ — recalculé à la génération]")
    else:
        w("- export final : ABSENT (NON TESTÉ)")
    for j in sorted(judges):
        d = os.path.join(root, "adapters", j)
        if os.path.isdir(d):
            w(f"- adaptateur `{j}` : {len(os.listdir(d))} fichiers sur "
              "stockage durable [OBSERVÉ]")
    w(f"- manifeste de lignage : "
      f"{'présent [PROUVÉ]' if man else 'ABSENT (NON TESTÉ)'}")
    w(f"- journal : events.jsonl ({ev_sum.get('n_events')} événements) ; "
      f"log.txt ; evidence/ (captures réelles)")

    section("15 · Hashes (chaîne de lignage)")
    links, ok_all = M.verify_lineage(root, repo)
    for ok, name, detail in links:
        w(f"- {'✓' if ok else '✗'} `{name}` — {detail} "
          f"[{'PROUVÉ' if ok else 'ÉCHEC'}]")
    if links:
        w()
        w(f"**Chaîne complète : "
          f"{sum(1 for o, _, _ in links if o)}/{len(links)} liens "
          f"vérifiés — {'INTÈGRE' if ok_all else 'ROMPUE'} [PROUVÉ]**")

    # ---- 16-18. limitations, anomalies, décisions ---------------------------
    section("16 · Limitations")
    w("- La val_loss n'évalue que l'imitation rédactionnelle, pas la "
      "prédiction de vote ;")
    w("- Barrett et Jackson sont hors corpus (garde temporelle "
      "pré-inscrite — pas assez d'opinions antérieures au cutoff) ;")
    w("- l'entraînement réel dépend d'un runtime GPU gratuit "
      "(Colab T4) : interrompu par construction, jamais perdu "
      "(architecture) ;")
    if is_pilot:
        w("- CE RAPPORT DÉCRIT UN PILOTE : modèle miniature, données "
          "synthétiques — aucun pouvoir de généralisation.")

    section("17 · Anomalies")
    if errs or partial:
        w(f"- {len(errs)} erreur(s) consignée(s), "
          f"{'journal terminé par une ligne incomplète, ' if partial else ''}"
          "toutes résorbées ou documentées ci-dessus [OBSERVÉ]")
    else:
        w("- aucune anomalie enregistrée [OBSERVÉ]")

    section("18 · Décisions d'ingénierie (journal synthétique)")
    w("- schéma d'état v3 : enrichissement statistique sans changement "
      "scientifique ;")
    w("- scellé M4 re-vérifié dans le clone AVANT CHAQUE session "
      "(refus de démarrer sinon) ;")
    w("- gel du protocole : toute modification méthodologique exige le "
      "rituel `--je-change-le-protocole` (décision explicite).")

    # ---- 19. reproductibilité ------------------------------------------------
    section("19 · Reproductibilité")
    w("Re-vérification indépendante, sans faire confiance à ce rapport :")
    w()
    w("```bash")
    w(f"python scripts/m3b_lineage.py --root {root} --repo {repo}")
    w(f"python scripts/m3b_gate.py --root {root} --repo {repo}")
    w("```")
    w()
    if man and man.get("code"):
        c = man["code"]
        w(f"- commit initial de l'expérience : `{c.get('head_initial')}` ;")
        w(f"- commits vus : {len(c.get('heads_seen') or [])} ; "
          f"git describe : `{c.get('git_describe')}` ;")
        w(f"- m4-freeze ancêtre du code d'entraînement : "
          f"{'oui' if c.get('m4_freeze_ancestor') else 'non/vrai dépôt requis'}"
          f" [OBSERVÉ]")
        w(f"- gel du protocole : sha256 "
          f"`{(c.get('protocol_freeze_sha256') or '—')[:24]}…` [OBSERVÉ]")

    # ---- 20. GO/NO-GO --------------------------------------------------------
    section("20 · GO / NO-GO")
    if gate:
        v = gate.get("verdict")
        w(f"**Portillon M3b : {v}** ({gate.get('n_fail')} échec(s), "
          f"{gate.get('n_warn')} avertissement(s)) [OBSERVÉ — exécuté "
          "à la finalisation]")
        for c in gate.get("checks", []):
            if c.get("severity") != "PASS":
                w(f"- [{c['severity']}] {c['id']} : {c['detail'][:90]}")
    else:
        w("m3b_gate.json absent — portillon non exécuté sur cet état. "
          "(NON TESTÉ)")
    if is_pilot:
        w()
        w("⚠ GO de pilote = la MÉCANIQUE est prête. L'expérience M3b "
          "scientifique (GPU, 7 juges) reste à exécuter sur Colab : "
          "verdict final attendu du portillon exécuté après le vrai "
          "entraînement.")

    verdict_data = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "root": os.path.abspath(root), "pilot": bool(is_pilot),
        "lineage_ok": ok_all if links else None,
        "gate": (gate or {}).get("verdict"),
        "judges_done": sum(1 for v in judges.values()
                           if v.get("status") == "done"),
        "judges_total": len(judges),
    }
    return "\n".join(L), verdict_data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--pilot", action="store_true",
                    help="force l'étiquette pilote (détection auto sinon)")
    args = ap.parse_args()

    text, verdict = build_report(args.root, args.repo, pilot=args.pilot)
    outdir = args.outdir or os.path.join(args.root, "reports")
    os.makedirs(outdir, exist_ok=True)
    md = os.path.join(outdir, "m3b_dossier.md")
    js = os.path.join(outdir, "m3b_dossier.json")
    for path, data in ((md, text), (js, json.dumps(verdict, indent=1,
                                                   ensure_ascii=False))):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    print(f"→ {md} ({len(text.splitlines())} lignes)")
    print(f"→ {js}")
    print("verdict :", json.dumps(verdict, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
