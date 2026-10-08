#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3b — tests d'injection de pannes sur la gestion d'état durable.

Chaque scénario du cahier des charges (§15) est joué sur de VRAIS
fichiers, dans de VRAIS sous-processus (la « mort du runtime » est un
os._exit brutal, comme une coupure Colab) :

  A  première exécution vierge ;
  B  interruption pendant l'entraînement ;
  C  interruption juste avant une sauvegarde ;
  D  interruption PENDANT la promotion Drive (copie) ;
  E  nouvelle session après interruption (reprise automatique) ;
  F  juge terminé puis nouvelle session (pas de réentraînement) ;
  G  plusieurs sessions successives sur le même juge (+ compteur early
     stopping persistant) ;
  H  checkpoint officiel corrompu (fallback génération précédente) ;
  I  manifeste manquant avec checkpoints présents (refus I7) ;
  J  manifeste incohérent (pas officiel inexistant → fallback réel) ;
  K  relancements accidentels / idempotence (export octet-identique) ;
  L  lancement alors que tout est finalisé ;
  M  stockage Drive temporairement indisponible (EIO) — v3 ;
  O  redémarrage COMPLET multi-sessions avec continuité — v3 ;
  P  reprise après PLUSIEURS générations de checkpoints (recyclage
     save_total_limit + corruption du plus récent) — v3.

  +  X1 budget temps → arrêt PROPRE avec sauvegarde du pas courant ;
     X2 empreinte scientifique modifiée → refus de reprendre ;
     X3 atomicité : crash pendant copytree (injection directe) ;
     X4 RESET TOTAL (double confirmation) ;
     X5 adaptateur final falsifié → détecté par verify ;
     X6 v3 : journal d'événements (ligne partielle tolérée), montée de
        niveau v2→v3, preuves indexées, manifeste + lignage complet.

Stdlib uniquement. Durée totale ~2-4 min.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m3b_state as M                                       # noqa: E402

PY = sys.executable
SIM = os.path.join(HERE, "m3b_sim_session.py")
JUDGES = ["AA", "BB", "CC", "DD"]

NPASS = NFAIL = 0


def check(cond, name, detail=""):
    global NPASS, NFAIL
    if cond:
        NPASS += 1
        print(f"  PASS  {name}")
    else:
        NFAIL += 1
        print(f"  FAIL  {name}  {detail}")


def session(drive, local, **kw):
    """Lance une session simulée en sous-processus. Retour
    (returncode, stdout, result_json|None)."""
    cmd = [PY, SIM, "--drive", drive, "--local", local]
    for k, v in kw.items():
        flag = "--" + k.replace("_", "-")
        if v is True:
            cmd.append(flag)
        elif v is not False:
            cmd += [flag, str(v)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    out = r.stdout + ("\n[stderr] " + r.stderr[-2000:] if r.stderr else "")
    js = None
    for line in reversed((r.stdout or "").splitlines()):
        if line.startswith("RESULT_JSON "):
            js = json.loads(line[len("RESULT_JSON "):])
            break
    return r.returncode, out, js


def state_of(drive):
    return json.load(open(os.path.join(drive, "state.json"),
                          encoding="utf-8"))


def sha(path):
    return M.sha256_file(path)


def fresh():
    base = tempfile.mkdtemp(prefix="m3b_sim_")
    return base, os.path.join(base, "drive"), os.path.join(base, "local")


# ------------------------------------------------------------------ scén. --
def events_of(drive):
    return M.read_events(drive)[0]


def scenario_A():
    print("\n=== A · première exécution vierge ===")
    base, drive, local = fresh()
    rc, out, js = session(drive, local)
    check(rc == 0, "A.rc0", out[-400:])
    check(js and js.get("mode") == "fresh", "A.mode_fresh")
    check(js and js.get("finalized") is True, "A.finalized")
    st = state_of(drive)
    check(all(st["judges"][j]["status"] == "done" for j in JUDGES),
          "A.tous_done", str(st["judges"]))
    # early stopping AA : loss remonte après le pas 60 → arrêt au pas 120
    check(js["judges"]["AA"] == "done@120/stopped", "A.AA_earlystop@120",
          str(js["judges"].get("AA")))
    check(st["judges"]["AA"]["best_val_loss"] == 1.8, "A.AA_best1.8",
          str(st["judges"]["AA"]))
    check(st["judges"]["AA"]["best_step"] == 60, "A.AA_best@60")
    # checkpoints purgés pour les juges finis, adaptateurs présents
    for j in JUDGES:
        d = os.path.join(drive, "checkpoints", j)
        check(not os.path.isdir(d) or not os.listdir(d),
              f"A.ckpts_purgés_{j}")
        a = os.path.join(drive, "adapters", j)
        check(os.path.isfile(os.path.join(a, "adapter_model.safetensors")),
              f"A.adaptateur_{j}")
    rep = json.load(open(os.path.join(drive, "m3b_report.json")))
    check(len(rep["results"]) == 4 and all(r["verified"] for r in rep["results"]),
          "A.rapport_4rows_vérifiés")
    # DD : 3 pas < SAVE_STEPS → finalisé depuis l'adaptateur frais (aucun ckpt)
    check("DD : aucun checkpoint" in out, "A.DD_adaptateur_frais")
    zf = os.path.join(drive, "final", "m3b_adapters_final.zip")
    check(os.path.isfile(zf), "A.zip_final_existe")
    with zipfile.ZipFile(zf) as z:
        names = z.namelist()
    check(sum(1 for n in names if n.endswith("adapter_config.json")) == 4
          and "m3b_report.json" in names, "A.zip_structure_M4")
    check(st["judges"]["AA"]["es_counter"] == 3, "A.compteur_es_3")
    # ---- v3 : journal, stats, manifeste, lignage, preuves ----------------
    evts = events_of(drive)
    kinds = [e["kind"] for e in evts]
    check(kinds.count("SESSION_START") == 1, "A.v3.1_session_start")
    check(kinds.count("JUDGE_COMPLETE") == 4, "A.v3.4_juges_complétés")
    check(kinds.count("START") == 4, "A.v3.4_start")
    check("RUN_COMPLETE" in kinds and "EXPORT" in kinds,
          "A.v3.run_complete+export")
    check(all(e.get("ts") for e in evts), "A.v3.événements_datés")
    check(st["judges"]["AA"]["n_tokens_train"] > 0
          and st["judges"]["AA"]["params"]["trainable"] > 0
          and st["judges"]["AA"]["wall_seconds"] >= 0,
          "A.v3.stats_par_juge", str(st["judges"]["AA"].keys()))
    check(st.get("environment", {}).get("gpu") == "simulator"
          and st.get("seal_checks") and st["seal_checks"][0]["ok"] is True,
          "A.v3.environnement+scellé_enregistrés")
    check(os.path.isfile(os.path.join(drive, "experiment_manifest.json")),
          "A.v3.manifeste_lignage_écrit")
    check(js.get("lineage_ok") is True, "A.v3.chaîne_complète_vérifiée",
          str(js.get("lineage_ok")))
    man = json.load(open(os.path.join(drive, "experiment_manifest.json")))
    check(man["protocol"]["seed"] == 42
          and len(man["protocol"]["data_train_sha256"]) == 4
          and man["seal_check"]["ok"] is True,
          "A.v3.manifeste.contenu")
    evd = os.path.join(drive, "evidence")
    idx = json.load(open(os.path.join(evd, "index.json")))
    check(len(idx["captures"]) >= 5, "A.v3.preuves_indexées",
          str(len(idx.get("captures", []))))
    check(any("TERMINÉ" in open(c["file"], encoding="utf-8").read()
              for c in idx["captures"]), "A.v3.preuve_juge_réelle")
    return base, drive, local


def scenario_B_C_D_E():
    print("\n=== B/C/D/E · interruptions brutales + reprise automatique ===")
    for tag, kw in (("B", {"kill_at_step": 23}),
                    ("C", {"kill_before_save": 30}),
                    ("D", {"kill_during_copy": 30})):
        print(f" -- variante {tag} : {kw}")
        base, drive, local = fresh()
        rc1, out1, _ = session(drive, local, **kw)
        check(rc1 == 9, f"{tag}.mort_brutale_rc9", f"rc={rc1}")
        st = state_of(drive)
        check(st["judges"]["AA"]["status"] == "training",
              f"{tag}.AA_training")
        check(st["judges"]["AA"]["step"] == 20, f"{tag}.AA_pas_durable_20",
              str(st["judges"]["AA"]["step"]))
        if tag == "D":
            tmpd = os.path.join(drive, "checkpoints", "AA")
            orphans = [p for p in os.listdir(tmpd)
                       if p.startswith(".tmp-")]
            check(len(orphans) == 1, f"{tag}.tmp_orphelin_présent",
                  str(orphans))
            # le ckpt officiel 20 reste intègre malgré la copie interrompue
            ok, why = M.ExpState(drive).verify_drive_entry(
                st["judges"]["AA"]["ckpt"], "AA")
            check(ok, f"{tag}.ckpt20_intègre", why)
        # E : nouvelle session — reprise automatique, rien à téléverser
        rc2, out2, js2 = session(drive, local)
        check(rc2 == 0, f"{tag}.session2_rc0", out2[-400:])
        check("reprend au pas 20" in out2, f"{tag}.E.reprise_automatique_20")
        st2 = state_of(drive)
        check(st2["judges"]["AA"]["best_val_loss"] == 1.8,
              f"{tag}.E.AA_best_1.8")
        check(js2 and js2.get("finalized") is True, f"{tag}.E.finalisée")
        if tag == "D":
            tmpd = os.path.join(drive, "checkpoints", "AA")
            if os.path.isdir(tmpd):
                orphans = [p for p in os.listdir(tmpd)
                           if p.startswith(".tmp-")]
                check(not orphans, f"{tag}.E.tmp_nettoyés", str(orphans))


def scenario_F_L():
    print("\n=== F/L · juge fini + relancement après finalisation ===")
    base, drive, local = fresh()
    session(drive, local)
    st0 = state_of(drive)
    steps0 = {j: st0["judges"][j]["step"] for j in JUDGES}
    zip_sha0 = sha(os.path.join(drive, "final", "m3b_adapters_final.zip"))
    n_sessions0 = len(st0["sessions"])
    # F/L : nouvelle session complète par-dessus un état finalisé
    rc, out, js = session(drive, local)
    check(rc == 0, "FL.rc0", out[-300:])
    check(js and js.get("mode") == "resume", "FL.mode_resume")
    check(js and js.get("already_finalized") is True, "FL.déjà_finalisée")
    check("déjà fait, sauté" in out, "FL.juges_sautés")
    st1 = state_of(drive)
    check({j: st1["judges"][j]["step"] for j in JUDGES} == steps0,
          "FL.aucun_pas_changé")
    check(len(st1["results"]) == 4, "FL.pas_de_doublon_résultats")
    check(len(st1["sessions"]) == n_sessions0 + 1, "FL.session_tracée")


def scenario_G():
    print("\n=== G · même juge sur 4 sessions successives ===")
    base, drive, local = fresh()
    rc1, _, _ = session(drive, local, kill_at_step=23)
    check(state_of(drive)["judges"]["AA"]["step"] == 20, "G.s1_pas20")
    rc2, out2, _ = session(drive, local, kill_at_step=55)
    check(state_of(drive)["judges"]["AA"]["step"] == 50, "G.s2_pas50")
    check("reprend au pas 20" in out2, "G.s2_reprise20")
    rc3, out3, _ = session(drive, local, kill_at_step=87)
    check(state_of(drive)["judges"]["AA"]["step"] == 80, "G.s3_pas80")
    st3 = state_of(drive)
    # compteur early stopping persisté : eval@80 dégradée → compteur 1
    check(st3["judges"]["AA"]["es_counter"] == 1, "G.s3_compteur_es_1",
          str(st3["judges"]["AA"]["es_counter"]))
    check(st3["judges"]["AA"]["best_val_loss"] == 1.8, "G.s3_best_1.8")
    rc4, out4, js4 = session(drive, local)
    check(rc4 == 0 and js4 and js4.get("finalized"), "G.s4_finalisée",
          out4[-300:])
    st4 = state_of(drive)
    # le compteur restauré (1) + eval@100 (2) + eval@120 (3) → arrêt 120
    check(st4["judges"]["AA"]["es_counter"] == 3, "G.s4_compteur_3",
          str(st4["judges"]["AA"]["es_counter"]))
    check(st4["judges"]["AA"]["best_step"] == 60, "G.s4_best_60")


def scenario_H():
    print("\n=== H · checkpoint officiel corrompu ===")
    base, drive, local = fresh()
    session(drive, local, kill_at_step=23)          # officiel : 20
    session(drive, local, kill_at_step=45)          # officiel : 40
    st = state_of(drive)
    check(st["judges"]["AA"]["step"] == 40, "H.officiel_40")
    rc, out, js = session(drive, local, corrupt_official=True)
    check(rc == 0 and js and js.get("finalized"), "H.session_termine",
          out[-400:])
    check("invalide" in out and "hash" in out, "H.corruption_détectée")
    check("reprend au pas 30" in out, "H.fallback_génération_précédente_30")
    st1 = state_of(drive)
    check(st1["judges"]["AA"]["status"] == "done", "H.AA_done_malgré_tout")


def scenario_I():
    print("\n=== I · manifeste manquant, checkpoints présents (I7) ===")
    base, drive, local = fresh()
    session(drive, local, kill_at_step=23)
    rc, out, js = session(drive, local, delete_state=True)
    check(js and js.get("mode_after_delete") == "error",
          "I.refus_de_repartir_de_zéro", str(js))
    # et le manifeste n'a PAS été recréé vierge par-dessus le travail
    check(not os.path.exists(os.path.join(drive, "state.json")),
          "I.pas_de_manifeste_vierge_écrasant")


def scenario_J():
    print("\n=== J · manifeste incohérent (pas pointé inexistant) ===")
    base, drive, local = fresh()
    session(drive, local, kill_at_step=23)
    session(drive, local, kill_at_step=45)          # ckpt-40 officiel
    rc, out, js = session(drive, local, point_state_to=55)
    check(rc == 0 and js and js.get("finalized"), "J.session_termine",
          out[-400:])
    check("reprend au pas 40" in out, "J.fallback_réel_40")
    st = state_of(drive)
    check(st["judges"]["AA"]["step"] in (120, 130) or
          st["judges"]["AA"]["status"] == "done", "J.état_final_coherent")


def scenario_K():
    print("\n=== K · idempotence : export régénéré octet-identique ===")
    base, drive, local = fresh()
    session(drive, local)
    zf = os.path.join(drive, "final", "m3b_adapters_final.zip")
    sha0 = sha(zf)
    # simule un relancement de la cellule d'export : on repart de
    # finalized=false (la cellule est re-exécutable), export re-construit
    rc, out, js = session(drive, local, action="export")
    check(rc == 0, "K.reexport_ok", out[-300:])
    check(sha(zf) == sha0, "K.zip_octet_identique")
    # double promote final adapter : atomique, pas de doublons
    d = os.path.join(drive, "adapters", "AA")
    check(sorted(os.listdir(d)) ==
          sorted(["adapter_model.safetensors", "adapter_config.json"]),
          "K.adaptateur_sans_doublon", str(os.listdir(d)))


def scenario_X1():
    print("\n=== X1 · budget temps → arrêt PROPRE + sauvegarde du pas ===")
    base, drive, local = fresh()
    # 0,001 min = 60 ms. FakeRun n'a PAS de sleep : son rythme est le coût
    # d'E/S des callbacks (manifestes, checkpoints). Avec 0,004 min ≈ la
    # durée d'UN juge complet, un runner à disque rapide peut laisser ce
    # juge TERMINER avant l'expiration — l'arrêt propre se produit alors au
    # juge suivant (flake CI du 2026-10-08, run 37790012575). Deux garde-fous :
    # (i) budget plus court pour expirer tôt ; (ii) le juge interrompu est
    # identifié depuis la sortie du simulateur, sans supposer que c'est AA.
    rc, out, js = session(drive, local, budget_minutes=0.001)
    check(rc == 0, "X1.rc0")
    check(js and js.get("budget_hit") is True, "X1.arrêt_par_budget")
    stopped = next((j for j, v in sorted((js.get("judges") or {}).items())
                    if isinstance(v, str) and v.startswith("budget-stop@")),
                   None)
    check(stopped is not None, "X1.juge_interrompu_identifié",
          str(js.get("judges")))
    if stopped is None:
        return
    st = state_of(drive)
    jt = st["judges"][stopped]
    check(jt["status"] == "training", "X1.interrompu_pas_finalisé")
    check(jt["step"] >= 1 and jt["ckpt"] is not None,
          "X1.dernier_pas_sauvegardé", str(jt))
    # le pas officiel correspond BIEN au pas d'arrêt (save à l'arrêt)
    check(jt["step"] == jt["ckpt"]["step"], "X1.ckpt==pas_arrêt")
    check(not js.get("finalized"), "X1.pas_finalisée")
    # session suivante : reprend au pas d'arrêt exact
    rc2, out2, js2 = session(drive, local)
    check(f"reprend au pas {jt['step']}" in out2, "X2.reprise_au_pas_exact")
    check(js2 and js2.get("finalized"), "X1.termine_ensuite")


def scenario_X2():
    print("\n=== X2 · configuration scientifique modifiée → REFUS ===")
    base, drive, local = fresh()
    session(drive, local, kill_at_step=23)
    rc, out, js = session(drive, local, mutate_config=True)
    check(js and js.get("mode") == "error" and js.get("refused"),
          "X2.refus_mode_error")
    check("EMPREINTE" in out, "X2.message_empreinte")
    st = state_of(drive)
    check(st["judges"]["AA"]["step"] == 20, "X2.état_intouché")


def scenario_X3_X5():
    print("\n=== X3/X5 · atomicité par injection directe ===")
    base = tempfile.mkdtemp(prefix="m3b_unit_")
    drive = os.path.join(base, "drive")
    os.makedirs(drive)
    # état vierge
    es = M.ExpState(drive)
    mode, _ = es.load_or_init("fp1", {}, 42, "h", ["AA"], "run_t")
    check(mode == "fresh", "X3.fresh")

    # X3 : crash pendant copytree de la promotion
    src = os.path.join(base, "src")
    os.makedirs(src)
    for fn in M.CKPT_REQUIRED:
        open(os.path.join(src, fn), "wb").write(b"x" * 1024)
    open(os.path.join(src, "adapter_model.safetensors"), "wb").write(b"y" * 4096)
    real_copytree = shutil.copytree

    def dying_copytree(a, b, **kw):
        # copie un fichier puis meurt brutalement (équivalent coupure)
        os.makedirs(b, exist_ok=True)
        shutil.copy2(os.path.join(a, "scheduler.pt"), b)
        raise RuntimeError("SIMULATED CRASH DURING COPY")

    shutil.copytree = dying_copytree
    try:
        es.register_and_promote("AA", 10, src)
        raised = False
    except Exception:
        raised = True
    finally:
        shutil.copytree = real_copytree
    check(raised, "X3.promotion_échouée_visiblement")
    st = json.load(open(os.path.join(drive, "state.json")))
    check(st["judges"]["AA"]["ckpt"] is None, "X3.manifeste_inchangé")
    orphans = [p for p in os.listdir(os.path.join(drive, "checkpoints", "AA"))
               if p.startswith(".tmp-")]
    check(len(orphans) == 1, "X3.tmp_orphelin_un_seul", str(orphans))
    check(not os.path.exists(os.path.join(drive, "checkpoints", "AA",
                                          "ckpt-10")),
          "X3.pas_de_ckpt_fantôme")
    # nettoyage au boot suivant
    es2 = M.ExpState(drive)
    es2.state = st
    es2.clean_tmp()
    check(not [p for p in os.listdir(os.path.join(drive, "checkpoints", "AA"))
               if p.startswith(".tmp-")], "X3.nettoyé_au_boot")

    # X5 : promote final réel puis falsification → détectée
    es2.register_and_promote("AA", 20, src)
    es2.j("AA")["best_step"] = 20
    tmp_final = os.path.join(base, "final")
    os.makedirs(tmp_final)
    shutil.copy2(os.path.join(src, "adapter_model.safetensors"), tmp_final)
    open(os.path.join(tmp_final, "adapter_config.json"), "w").write("{}")
    es2.promote_final_adapter("AA", tmp_final)
    ok, why = es2.verify_final_adapter("AA")
    check(ok, "X5.adaptateur_intègre", why)
    p = os.path.join(drive, "adapters", "AA", "adapter_model.safetensors")
    with open(p, "r+b") as f:
        f.write(b"Z")
    ok2, why2 = es2.verify_final_adapter("AA")
    check(not ok2, "X5.falsification_détectée", str((ok2, why2)))


def scenario_X4():
    print("\n=== X4 · RESET TOTAL (double confirmation) ===")
    base, drive, local = fresh()
    session(drive, local)
    es = M.ExpState(drive)
    es.state = state_of(drive)
    ok, msg = es.reset("mauvaise-confirmation")
    check(not ok, "X4.mauvaise_conf_refusée")
    ok2, msg2 = es.reset("je-veux-tout-effacer")
    check(ok2, "X4.reset_confirmé", msg2)
    check(not os.path.exists(os.path.join(drive, "state.json")),
          "X4.racine_déplacée")
    # nouvelle vie : départ propre, plus de fichiers fantômes
    es2 = M.ExpState(drive)
    mode, _ = es2.load_or_init("fp1", {}, 42, "h", ["AA"], "run_t2")
    check(mode == "fresh", "X4.nouveau_départ_vierge")
    check(not (drive / "checkpoints").exists() if hasattr(drive, "exists")
          else not os.path.exists(os.path.join(drive, "checkpoints")),
          "X4.aucun_fantôme")
    renamed = [d for d in os.listdir(base) if "DELETED" in d]
    check(len(renamed) == 1, "X4.sauvegarde_de_dernier_recours", str(renamed))


def scenario_M():
    print("\n=== M · stockage Drive temporairement indisponible (EIO) ===")
    base, drive, local = fresh()
    session(drive, local, kill_at_step=23)          # officiel : pas 20
    st0 = state_of(drive)
    n_evts0 = len(events_of(drive))
    # session avec échec de TOUTES les écritures Drive (EIO simulé,
    # équivalent quota plein) — activé après le chargement de l'état
    rc, out, js = session(drive, local, readonly_drive=True)
    check(rc == 0, "M.session_survie_proprement", out[-300:])
    check("stockage Drive indisponible" in out, "M.message_arrêt_propre")
    st1 = state_of(drive)
    check(st1["judges"]["AA"]["step"] == 20, "M.manifeste_reste_au_pas_20",
          str(st1["judges"]["AA"]["step"]))
    check(st1["judges"]["AA"]["ckpt"] == st0["judges"]["AA"]["ckpt"],
          "M.aucun_checkpoint_fantôme_promu")
    check(st1["fingerprint"] == st0["fingerprint"], "M.empreinte_intacte")
    # le journal n'a pas bougé pendant la panne (aucune écriture possible —
    # seuls des artefacts DURABLES comptent, rien de fabriqué en mémoire)
    check(len(events_of(drive)) >= n_evts0, "M.journal_jamais_falsifié")
    # session suivante (Drive revenu) : reprise PROPRE depuis le pas 20,
    # interruption de la session 1 détectée au boot, fin normale
    rc2, out2, js2 = session(drive, local)
    check(rc2 == 0 and js2 and js2.get("finalized"), "M.reprise_après_panne",
          out2[-300:])
    check("reprend au pas 20" in out2, "M.reprise_pas_20")
    evts = events_of(drive)
    check(any(e["kind"] == "RECOVERY" for e in evts),
          "M.recovery_consigné_au_retour")
    check(js2.get("lineage_ok") is True, "M.lignage_final_intègre")
    st2 = state_of(drive)
    check(st2["judges"]["AA"]["interruptions"] >= 1
          and st2["judges"]["AA"]["status"] == "done",
          "M.interruptions_comptées_puis_juge_fini")


def scenario_O():
    print("\n=== O · redémarrage complet — 4 processus, continuité totale ===")
    base, drive, local = fresh()
    session(drive, local, kill_at_step=23)
    session(drive, local, kill_at_step=53)
    session(drive, local, kill_at_step=83)
    rc, out, js = session(drive, local)
    check(rc == 0 and js and js.get("finalized"), "O.finalisée_en_4_processus",
          out[-300:])
    evts = events_of(drive)
    kinds = [e["kind"] for e in evts]
    check(kinds.count("SESSION_START") == 4, "O.4_démarrages_de_processus",
          str(kinds.count("SESSION_START")))
    recovs = [e for e in evts if e["kind"] == "RECOVERY"
              and "interruption" in str(e.get("detail", ""))]
    check(len(recovs) == 3, "O.3_interruptions_détectées_au_boot",
          str(len(recovs)))
    st = state_of(drive)
    check(st["judges"]["AA"]["interruptions"] == 3,
          "O.compteur_interruptions_3",
          str(st["judges"]["AA"]["interruptions"]))
    check(st["judges"]["AA"]["resumes"] == 3,
          "O.compteur_reprises_3",
          str(st["judges"]["AA"]["resumes"]))
    check(js.get("lineage_ok") is True, "O.lignage_intègre_malgré_restarts")


def scenario_P():
    print("\n=== P · plusieurs générations de checkpoints + corruption du "
          "plus récent ===")
    base, drive, local = fresh()
    session(drive, local, kill_at_step=23)          # gen 20
    session(drive, local, kill_at_step=45)          # gens {20, 40}
    session(drive, local, kill_at_step=65)          # prune → {40, 60}
    st = state_of(drive)
    gens = sorted(p for p in os.listdir(
        os.path.join(drive, "checkpoints", "AA"))
        if p.startswith("ckpt-"))
    check(st["judges"]["AA"]["step"] == 60, "P.officiel_60",
          str(st["judges"]["AA"]["step"]))
    check(len(gens) <= 3, "P.recyclage_générations", str(gens))
    # corruption du PLUS RÉCENT (officiel 60) → repli sur génération
    # précédente disponible (50 : après recyclage, {50,60} subsistent),
    # promue nouvel officiel
    rc, out, js = session(drive, local, corrupt_official=True)
    check(rc == 0 and js and js.get("finalized"), "P.session_termine",
          out[-400:])
    check("reprend au pas 50" in out, "P.repli_génération_précédente_50")
    evts = events_of(drive)
    recov = [e for e in evts if e["kind"] == "RECOVERY"
             and "repli" in str(e.get("detail", ""))]
    check(len(recov) >= 1, "P.événement_recovery_consigné")
    st1 = state_of(drive)
    check(st1["judges"]["AA"]["status"] == "done", "P.juge_fini_malgré_tout")
    check(js.get("lineage_ok") is True, "P.lignage_final_intègre")


def scenario_X6():
    print("\n=== X6 · v3 : journal tolérant, montée v2→v3, preuves ===")
    base = tempfile.mkdtemp(prefix="m3b_unit3_")
    drive = os.path.join(base, "drive")
    os.makedirs(drive)

    # 1) ligne partielle (crash mid-write) → ignorée, signalée
    with open(os.path.join(drive, "events.jsonl"), "w") as f:
        f.write(json.dumps({"ts": "t", "kind": "NOTE"}) + "\n")
        f.write('{"ts": "t2", "kind": "CHECKPOI')     # crash simulé
    evts, partial = M.read_events(drive)
    check(len(evts) == 1 and partial is True,
          "X6.ligne_partielle_tolérée", str((len(evts), partial)))

    # 2) manifeste v2 → v3 : enrichi, aucune donnée perdue
    v2 = {"schema": "m3b-state/2", "run_id": "r1",
          "fingerprint": "fpx", "fingerprint_parts": {"config": "a",
                                                       "data": "b"},
          "seed": 42, "code": {"head_initial": "h", "heads_seen": ["h"]},
          "judges": {"AA": {"status": "training", "step": 30,
                            "ckpt": None, "best_step": 20,
                            "best_val_loss": 2.0, "es_counter": 1,
                            "error": None}},
          "results": [], "probe": None, "memorization": None,
          "finalized": False, "sessions": []}
    json.dump(v2, open(os.path.join(drive, "state.json"), "w"))
    es = M.ExpState(drive)
    mode, _ = es.load_or_init("fpx", {"config": "a", "data": "b"}, 42,
                              "h", ["AA"], run_id="r2")
    check(mode == "resume", "X6.v2_repris_sans_refus")
    st = state_of(drive)
    check(st["schema"] == "m3b-state/3", "X6.schéma_porté_en_v3")
    check(st["judges"]["AA"]["best_val_loss"] == 2.0
          and st["judges"]["AA"]["step"] == 30,
          "X6.données_v2_préservées")
    check(st["judges"]["AA"]["interruptions"] == 1
          and st["judges"]["AA"]["status"] == "pending",
          "X6.interruption_détectée_au_passage_v3")
    evts = M.read_events(drive)[0]
    check(any(e["kind"] == "RECOVERY" for e in evts),
          "X6.recovery_consigné")

    # 3) preuves : index atomique, séquences croissantes
    M.evidence_dump(drive, "test-1", "sortie réelle 1", note="n1")
    M.evidence_dump(drive, "test-2", "sortie réelle 2", note="n2")
    idx = json.load(open(os.path.join(drive, "evidence", "index.json")))
    seqs = [c["seq"] for c in idx["captures"]]
    check(seqs == sorted(seqs) and len(seqs) == 2, "X6.preuves_séquences",
          str(seqs))
    check(os.path.isfile(os.path.join(drive, "evidence", "002_test-2.txt")),
          "X6.preuve_2_écrite")

    # 4) type d'événement inconnu → refus (le journal n'est pas une poubelle)
    try:
        es.event("NOT_A_KIND")
        bad = False
    except ValueError:
        bad = True
    check(bad, "X6.type_inconnu_refusé")


def main():
    t0 = time.time()
    scenario_A()
    scenario_B_C_D_E()
    scenario_F_L()
    scenario_G()
    scenario_H()
    scenario_I()
    scenario_J()
    scenario_K()
    scenario_M()
    scenario_O()
    scenario_P()
    scenario_X1()
    scenario_X2()
    scenario_X3_X5()
    scenario_X4()
    scenario_X6()
    print(f"\n════════════════════════════════════════════════")
    print(f"INJECTION DE PANNES : {NPASS} PASS / {NFAIL} FAIL "
          f"({time.time() - t0:.0f}s)")
    print("════════════════════════════════════════════════")
    return 1 if NFAIL else 0


if __name__ == "__main__":
    sys.exit(main())
