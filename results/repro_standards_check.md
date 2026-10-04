# Standards de reproductibilité — vérification croisée (machine)

*Généré le 2026-10-04T17:37:24.002335+00:00 au commit `d12b8c47d1` — chaque contrôle relit les artefacts, recalcule les hashs ou re-exécute les tests.*

| # | standard | verdict | preuve vérifiée |
|---|----------|---------|------------------|
| S1 | splits temporels + scellé exclu | PASS | manifest train=OT2015..OT2019 test=OT2020..OT2023 ; audit zéro-fuite 14 contrôles re-exécuté ce jour : PASS (B1/B2/B3 = gardes temporelles) |
| S2 | hyperparamètres complets + gelés | PASS | 11 fragments gelés (sha256), test gel re-exécuté : 12/12 ; config_sci contient MODEL_ID/MAX_LEN/LoRA/LR/EPOCHS/BATCH/GRAD_ACCUM/VAL_FRACTION |
| S3 | seed fixe, consignée, dans l'empreinte | PASS | SEED=42 (random/np/torch/cuda) ; seed=SEED dans TrainingArguments gelé ; empreinte = sha256({cfg, données, seed}) — une autre seed = autre expérience |
| S4 | ressources de calcul enregistrées par session | PASS | results/environment_probe.json + m3b_local_feasibility.json (mesures réelles atelier) ; state.json consigne env+scellé à CHAQUE session (GPU, VRAM, versions python/torch/transformers/peft/bnb) |
| S5 | temps/mémoire/interruptions par juge | PASS | stats par juge dans state.json (n_train, tokens, params, steps, wall, max_mem, interruptions, reprises, val_loss_history) + journal events.jsonl (START/CHECKPOINT/RESUME/RECOVERY/… horodatés) |
| S6 | code versionné (commit + tag + bundle) | PASS | HEAD d12b8c47d1 ; tag m4-freeze présent ; 3 bundle(s) de résilience dans download/ (histoire complète vérifiable hors ligne) |
| S7 | données déterministes + hachées | PASS | 477 lignes train (9 juges, Barrett/Jackson=0 pré-garde) + 382 votes test transparents (extension M4, jamais en entraînement) ; 307+211 case files ; textes v3 793 distincts ; hash par juge dans le manifeste d'expérience ; régénération : scripts/m3_build_datasets.py (déterministe, audité) |
| S8 | métriques pré-inscrites, aucune calculée avant protocole | PASS | m4_metrics.py (Wilson, McNemar exact, κ, ECE, Brier) : 19 tests OK re-exécutés ; analyse pré-inscrite dans docs/04-PROTOCOLE.md (règles 1-15) AVANT l'épreuve scellée |
| S9 | procédure de reproduction d'un tiers + idempotence | PASS | docs/13 §3 : 5 commandes (clone au commit consigné → lignage → portillon → rapport → paquet) ; build_artifacts.py prouve l'idempotence (deux builds = paquets octet-identiques, testé) |
| S10 | notebooks validés, exécutables, gardes incluses | PASS | M3b OK ; M4 OK ; gardes : GPU en tête d'install, scellé re-vérifié avant entraînement, pins planchers documentés (leçon bitsandbytes : planchers + matrice de versions observées plutôt que pins exacts périssables) |
| S11 | documentation des paramètres importants | PASS | m3_preflight.md (7 personas actives, fenêtres réelles, part lignes tronquées documentée) ; m3_power_report.md (Barrett/Jackson = 0 pré-garde, condition B dégradée pré-enregistrée) ; docs/12-GUIDE-COLAB.md (séquence d'exécution, incidents connus) |

**Bilan : 11/11 PASS.** Les 11 standards de reproductibilité exigés (splits, hyperparamètres, seeds, ressources, temps, code, données, métriques, reproduction, notebooks, documentation) sont vérifiés PAR MACHINE au commit d12b8c47d1. Chaque vérification relit les artefacts, recalcule les hashs ou re-exécute les tests — aucune affirmation non vérifiée.