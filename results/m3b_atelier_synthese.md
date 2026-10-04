# Synthèse atelier M3b — format §XXIII du cahier des charges

*Généré le 2026-10-05 (UTC+1) au commit `d12b8c4` — atelier de l'agent
d'exécution, toutes les affirmations ci-dessous relèvent d'une exécution
réelle de ce jour ou d'un artefact vérifiable cité.*

---

## A. EXECUTIVE SUMMARY

Le cahier des charges « Point B » (23 sections) demande un M3b
scientifiquement valide, entièrement vérifié, reproductible et documenté,
sans modification du protocole scientifique. Au commit `d12b8c4` :

1. **Le protocole scientifique est préservé et INALTERABLE par
   construction** : gel des 11 fragments méthodologiques du notebook
   (sha256 octet par octet, vérifié en CI à chaque push) — testé ce jour
   12/12 PASS, et une tentative de mutation (EPOCHS 8→3) est détectée
   (preuve 009).
2. **L'infrastructure M3b est complète et re-vérifiée ce jour** :
   143 contrôles d'injection de pannes (interruptions brutales, corruption,
   reprises multiples, idempotence) + 30 contrôles d'intégration avec les
   VRAIS transformers/peft + 25 contrôles sur les VRAIES cellules du
   notebook — tous PASS.
3. **L'exécution locale de l'entraînement est OBJECTIVEMENT IMPOSSIBLE**
   dans l'atelier, prouvé par mesures réelles ce jour : aucun GPU
   (nvidia-smi absent, `/dev/nvidia*` absent, `torch.cuda=False` — or le
   protocole gelé exige bitsandbytes nf4, CUDA uniquement), disque libre
   1,42 Go < 6,4 Go requis pour le seul modèle de base, RAM totale
   4,14 Go < 6,4 Go, et extrapolation CPU mesurée : ~37 jours de calcul
   continu (846 s/pas × 3 816 pas).
4. **La route d'exécution désignée est l'architecture alternative du
   projet** : notebook Colab T4 + état Drive persistant — construit,
   testé, documenté (`docs/12-GUIDE-COLAB.md`), reprise automatique
   inter-sessions. Elle attend l'exécution par l'utilisateur.
5. **M4 n'a pas été touché** : scellé re-vérifié, porte PENDING
   (12 PASS + R6 = adaptateurs M3b attendus), aucune vérité scellée lue.
6. **Les 11 standards de reproductibilité** exigés (splits,
   hyperparamètres, seeds, ressources, temps, code, données, métriques,
   reproduction, notebooks, documentation) : **11/11 PASS** vérifiés par
   machine ce jour (`results/repro_standards_check.{json,md}`).

**Verdict global : infrastructure GO — entraînement réel NON EXÉCUTÉ
(atelier sans GPU, preuves à l'appui) — la balle est dans le camp Colab.**

## B. ÉTAT INITIAL

- Dépôt `Vitalcheffe/legally-subjective`, branche `main`, HEAD `d12b8c4`,
  arbre propre, synchronisé avec l'origine (0/0), tag `m4-freeze` en place.
- M1.5 clos (1 778 textes collectés → 793 distincts après
  normalisation/dédup documentée, audit zéro-fuite 14/14 en CI).
- M3a clos : baseline B4 = 0,6366 vote / 0,558 affaire (IC95 documentés),
  reproduit exactement ce jour par `test_m4_machinery.py`.
- M3b : notebook v3 (31 cellules, validate 0 erreur), état durable v3
  (manifeste source de vérité unique, atomicité, journal d'événements),
  portillon G1-G10, pilote CPU réel GO.
- M4 : épreuve scellée (50 affaires 5-4), analyse pré-inscrite
  (règles 1-15), machinerie de scoring testée (B4 exact, McNemar, Wilson).

## C. ARCHITECTURE RETENUE

Écriture locale + promotion atomique + manifeste en dernier
(`scripts/m3b_state.py`, schéma `m3b-state/3`) :

- **source de vérité unique** : `state.json` sur Drive (tmp + fsync +
  rename, `.bak`, repli génération précédente sur corruption) ;
- **checkpoints fréquents** promus atomiquement (fichiers d'abord,
  manifeste ensuite) — une coupure coûte ≤ ~10 pas ;
- **reprise automatique** inter- et intra-juge (RNG/optimizer/scheduler
  restaurés — le bug transformers 4.46.3 `weights_only` a été trouvé par
  le test d'intégration réel AVANT de coûter une session) ;
- **journal d'événements** `events.jsonl` append+fsync (12 types :
  START, CHECKPOINT, RESUME, RECOVERY, VALIDATION, ERROR, JUDGE_COMPLETE,
  RUN_COMPLETE, EXPORT, SESSION_START, …), ligne déchirée réparée ;
- **arrêt propre ≠ corruption** : budget temps → save-puis-stop ;
  corruption → repli déterministe au dernier état valide ;
- **idempotence** : relance après succès = saut sans double comptabilisation ;
  export zip déterministe (deux exports = octet-identiques) ;
- **lignage** : `build_experiment_manifest` (m3b-manifest/1) +
  `verify_lineage` L1-L8 — la chaîne résultat → prédiction → modèle →
  checkpoint → configuration → données → split → commit → environnement →
  journal, chaque maillon re-haché ;
- **portillon objectif** : `m3b_gate.py` G1-G10 (GO/NO-GO, rc 0/1).

## D. ENVIRONNEMENT RÉEL (mesuré ce jour, `results/m3b_local_feasibility.json`)

| dimension | valeur mesurée | exigence du protocole gelé | verdict |
|---|---|---|---|
| GPU | **aucun** (nvidia-smi absent, `/dev/nvidia*` absent, `torch.cuda=False`) | bitsandbytes nf4 = CUDA uniquement | IMPOSSIBLE |
| VRAM | n/a (pas de GPU) | ~6-8 Go (T4 16 Go validée Colab) | IMPOSSIBLE |
| CPU | 2 cœurs | — | micro-bench : 846 s/pas extrapolé 3B |
| RAM | 4,14 Go totale / 3,24 Go dispo | 6,4 Go pour charger bf16 avant quantif | IMPOSSIBLE |
| stockage | 1,42 Go libre | 6,4 Go (téléchargement bf16 du modèle) | IMPOSSIBLE |
| réseau | HuggingFace joignable (HTTP 200) | — | inutile sans disque |
| versions | Python 3.12.14, torch 2.14.1+cpu, transformers 4.49.0, peft 0.13.2 | — | pile CPU valide (pilote) |
| persistance | filesystem atelier persistant entre sessions | — | OK (worklog, bundles, venv) |
| jobs longs | sessions de travail fractionnées | 37 jours continus calculés | IMPOSSIBLE |

## E. EXPÉRIENCES EFFECTUÉES (ce jour, toutes RÉELLES)

1. **Audit froid complet** : git, docs, notebook, scripts, résultats M3a,
   gel du protocole, porte M4, scellé, protections, dépendances.
2. **Sonde d'impossibilité locale** (`scripts/m3b_local_feasibility.py`) :
   5 mesures réelles (GPU, RAM/disque, bitsandbytes, micro-benchmark CPU
   0,268 s/pas sur mini-transformer 3,9M params → extrapolation 846 s/pas
   pour le 3B gelé → 37,4 jours pour 3 816 pas), réseau.
3. **Re-vérification intégrale au commit courant** : gel 12/12, zéro-fuite
   14/14, pannes injectées 143/143, intégration transformers réelle 30/30,
   flow notebook 25/25, machinerie M4 (B4 = 0,6366/0,558 exact), métriques
   19/19, portillon pilote GO, lignage pilote 16/16.
4. **Vérification croisée des standards de reproductibilité**
   (`scripts/repro_standards_check.py`) : 11/11 PASS.
5. **Captures de preuves fraîches** 011-014 (sorties réelles horodatées).

## F. TABLEAU PAR JUGE (données d'entraînement réelles, exécution en attente)

| juge | lignes train | fenêtre réelle | statut entraînement |
|---|---|---|---|
| JGRoberts | 43 | OT2015..OT2019 | ATTENDU (Colab) |
| CThomas | 146 | OT2015..OT2019 | ATTENDU (Colab) |
| SAAlito | 83 | OT2015..OT2019 | ATTENDU (Colab) |
| SSotomayor | 95 | OT2015..OT2019 | ATTENDU (Colab) |
| EKagan | 50 | OT2015..OT2019 | ATTENDU (Colab) |
| NMGorsuch | 39 | OT2015..OT2019 | ATTENDU (Colab) |
| BMKavanaugh | 21 | OT2015..OT2019 | ATTENDU (Colab) |
| ACBarrett | 0 | aucune pré-garde | SAUTÉ (règle MIN_TRAIN_ROWS=8, dégradé pré-inscrit) |
| KBJackson | 0 | aucune pré-garde | SAUTÉ (idem) |

Total : 477 lignes train (+382 votes test transparents jamais en
entraînement). Configuration gelée identique pour tous : Qwen2.5-3B
-Instruct, QLoRA nf4 double-quant, LoRA r16/α32/dropout 0,05, LR 1e-4,
8 époques, batch 1 × grad-accum 8, MAX_LEN 4096, SEED 42. Durées Colab
mesurées précédemment : ~15-22 h total sur T4 (multisessions).

## G. CHECKPOINTS / INTERRUPTIONS / REPRISES

- **Scénarios A-P + X testés par VRAIES interruptions** (sous-processus
  tués à des pas précis, threads tueurs pendant les copies Drive) :
  143 contrôles PASS — lancement propre, arrêt normal, interruption
  brutale, reprise, interruption avant/après checkpoint, checkpoint
  corrompu (repli génération précédente), état incomplet, checkpoint
  orphelin, double reprise, relance après succès, budget temps,
  stockage EIO, processus tué, redémarrage complet, générations
  multiples recyclées.
- **Intégration réelle transformers/peft** : 30 contrôles PASS
  (reprise exacte pas 16→48, compteur d'early stopping persistant,
  finalisation avec rechargement + forward vérifié).
- Le pilote CPU du jour a re-démontré la chaîne complète : entraînement →
  checkpoints → finalisation → export → lignage 16/16 → portillon GO
  (preuve 013).

## H. VALIDATION SCIENTIFIQUE

- scellé M4 recalculé et intègre (50 affaires, sha256 méthode exacte du
  builder) — re-vérifié ce jour par la porte ET par le lignage pilote (L7) ;
- scellé exclu de l'entraînement : audit 14/14 (A1-A3) + re-parcours
  indépendant au portillon (G8) + garde de date réelle dans le builder ;
- split temporel strict : B1/B2/B3 PASS (train < 2020-10-01, test OT2020+) ;
- config gelée inchangée : 12/12 fragments octet-identiques ;
- seeds : SEED=42 dans l'empreinte d'expérience ;
- chargement/inférence des adaptateurs : rechargement PeftModel + forward
  logits AVANT tout marquage « done » (mécanique I4, prouvée en pilote).

## I. RÉSULTATS M3b

**Aucun résultat d'entraînement réel n'existe encore** — et aucun n'est
fabriqué. Conformément à la règle absolue (§XX) : pas de valeurs inventées,
pas de fichiers de résultats remplis. Les seuls chiffres publiés sont les
baselines M3a (B4 = 0,6366/0,558) et les mesures d'infrastructure. Le
rapport final M3b sera généré par `m3b_report_gen.py` depuis l'état Drive
réel après les sessions Colab, avec étiquettes PROUVÉ/TESTÉ/OBSERVÉ/
SIMULÉ/NON TESTÉ. Si la condition B perd contre B4, ce sera rapporté tel
quel — l'honnêteté du NULL RESULT est déjà la position assumée du projet
(cf. M3a).

## J. ARTEFACTS PRODUITS (ce jour)

- `results/m3b_local_feasibility.{json}` — mesures réelles d'impossibilité ;
- `results/repro_standards_check.{json,md}` — 11/11 standards vérifiés ;
- preuves 011-014 + index régénéré avec cadrage honnête ;
- captures d'écran AUCUNE (règle : jamais de capture fabriquée) — les
  preuves sont les sorties réelles, format texte, contextées ;
- scripts atelier : `scripts/m3b_local_feasibility.py`,
  `scripts/repro_standards_check.py` (persistés, ré-exécutables).

## K. HASHES

Chaîne complète re-calculable par `scripts/m3b_lineage.py` (L1-L8 :
empreinte re-dérivée, adaptateurs re-hachés, journal, export, scellé,
rapport). Artefacts gelés du dépôt : `results/protocol_m3b_freeze.json`
(11 fragments sha256), chaîne sha256 des 8 artefacts M1.5 (F1, audit
14/14), scellé `stats_v1.json` (recalculé ce jour : match). Le paquet
d'artefacts d'une expérience réelle sera produit par
`scripts/build_artifacts.py` (idempotence prouvée : deux builds =
octet-identiques).

## L. PREUVES ET CAPTURES

`download/EVIDENCE-M3B/` — 14 captures, chacune = sortie NON MODIFIÉE
d'une commande réellement exécutée, avec en-tête (UTC, commit git,
propreté de l'arbre, commande exacte, code retour, durée) et index
machine-readable + lisible. Cadrage honnête en tête d'index : expériences
exécutées dans l'environnement de recherche du projet par l'agent, traces
reproductibles — aucune imitation de travail humain manuel, aucune
interface simulée, aucune capture fabriquée. Les captures complètent les
journaux et artefacts machine-readable, elles ne les remplacent pas.

## M. TESTS (tous re-exécutés ce jour au commit d12b8c4)

| suite | contrôles | verdict |
|---|---|---|
| gel du protocole scientifique | 12 | 12/12 PASS |
| audit zéro-fuite M1.5/M3 | 14 | 14/14 PASS |
| injection de pannes A-P+X (état durable) | 143 | 143/143 PASS |
| intégration RÉELLE transformers/peft | 30 | 30/30 PASS |
| cellules réelles du notebook M3b | 25 | 25/25 PASS |
| machinerie M4 (B4 exact, scoring) | suite | PASS |
| métriques M4 (Wilson/McNemar/κ/ECE) | 19 | 19/19 OK |
| standards de reproductibilité | 11 | 11/11 PASS |
| portillon (état pilote réel) | G1-G10 | GO |
| lignage (état pilote réel) | L1-L8 | 16/16 INTÈGRE |
| portillon (état vide — contrôle négatif) | — | NO-GO (rc 1, attendu) |

## N. ANOMALIES

1. **Environnement atelier sans GPU** — permanente, documentée par
   mesures (pas un incident : une contrainte). Conséquence : l'exécution
   réelle M3b ne peut pas venir de l'atelier.
2. **Disque atelier tendu** (1,42 Go libres) — surveillé ; les suites de
   tests ont déjà été purgées de leurs fichiers temporaires ; aucun
   impact sur le dépôt (artefacts légers).
3. **Aucune anomalie de protocole détectée ce jour** : gel intact,
   scellé intègre, audits verts. Les anomalies historiques (fuite
   « 145, Orig. », bug transformers 4.46.3, pins bitsandbytes) sont
   closes et documentées dans le dépôt.

## O. AUTO-AUDIT (indépendant, ce jour)

- fuite de données : NON — audit 14/14 + G8 + garde de date (contrôlés) ;
- contamination temporelle : NON — B1/B2/B3 verts ;
- divergence protocole prévu/exécuté : NON — gel 12/12, et le simulateur
  comme le pilote portent la MÊME empreinte miroir que le notebook (L3) ;
- résultats écrasés : NON — atomicité + manifeste en dernier (testé) ;
- fichiers non versionnés : les nouveaux artefacts du jour sont committés
  (ce commit) ; seeds/versions/dépendances enregistrées (S3/S4) ;
- checkpoints non vérifiés : NON — hash par fichier + rechargement avant
  « done » (I4) ;
- métriques ambiguës : NON — l'analyse est pré-inscrite, aucune métrique
  calculée avant l'épreuve ;
- captures ambiguës : le cadrage honnête est désormais généré dans
  l'index ; les échecs restent publiés (010 : rc 1) ;
- résultats simulés : étiquetés SIMULÉ/PILOTE automatiquement par le
  générateur de rapport — jamais présentés comme réels ;
- incohérences logs/fichiers/rapport : NON — portillon G7 + lignage L8.

**Sévérité : aucun CRITICAL/HIGH ouvert. MEDIUM persistant : impossibilité
GPU atelier (contournée par architecture alternative). LOW : disque tendu.**

## P. REPRODUCTIBILITÉ

11/11 standards vérifiés par machine (S1-S11, `results/repro_standards_
check.md`) : splits, hyperparamètres, seeds, ressources de calcul, temps,
code, données, métriques/statistiques, procédure de reproduction d'un
tiers, notebooks exécutables, documentation des paramètres importants.
Procédure d'un tiers : `docs/13-REPRODUCTIBILITE-M3B.md` §3 (5 commandes).
Niveau minimal = standards des conférences ML ; le projet y ajoute le gel
de protocole en CI, le portillon objectif et le lignage re-calculable.

## Q. IMPACT SUR M4

Aucun lancement automatique (§XIX respecté). M4 reste protégé : scellé
intègre (50 affaires 5-4), tag `m4-freeze`, analyse pré-inscrite, porte
PENDING avec R6 = adaptateurs M3b attendus. La séquence reste : fin des
sessions Colab M3b → dépôt de l'export → phase T (régression B4 attendue
exacte : 0,6366/0,558) → décision explicite → phase S (une seule fois).
Le comparateur pré-inscrit (B4 re-ajusté strict sur la population scellée)
et les barres seront publiés côte à côte, quel que soit le résultat.

## R. GO / NO-GO

**GO pour l'exécution M3b sur Colab** (infrastructure prouvée, protocole
gelé, données prêtes, reprise automatique, portillon objectif en fin de
course). **NO-GO pour déclarer M3b terminé** — l'entraînement réel n'a pas
encore été exécuté : le critère de fin (§XXI) exige « M3b réellement
exécuté », et l'atelier ne peut pas le faire à la place du GPU. Le verdict
final appartiendra au portillon après les sessions Colab — s'il dit NO-GO,
le dossier dira NO-GO.

## S. LISTE EXACTE DES FICHIERS À CONSULTER

Dans le dépôt (`/home/z/my-project/legally-subjective-repo/`) :
- `results/m3b_local_feasibility.json` — mesures réelles du jour ;
- `results/repro_standards_check.md` — 11/11 standards vérifiés ;
- `results/protocol_m3b_freeze.json` — protocole gelé (11 fragments) ;
- `results/m4_readiness.md` — porte M4 (PENDING attendu) ;
- `results/m2_baselines.json` — B4 = 0,6366/0,558 (référence à battre) ;
- `docs/12-GUIDE-COLAB.md` — guide d'exécution Colab (l'utilisateur) ;
- `docs/13-REPRODUCTIBILITE-M3B.md` — chaîne + procédure d'un tiers ;
- `docs/04-PROTOCOLE.md` — protocole + pré-inscription (règles 1-15) ;
- `notebooks/m3b_qlora_personas.ipynb` — le notebook à exécuter (31 cellules).

Dans l'atelier (`/home/z/my-project/download/`) :
- `EVIDENCE-M3B/` — 14 captures réelles + `index.md` (cadrage honnête) ;
- `artifacts-pilote-cpu/` — paquet du pilote (11 fichiers hachés,
  lineage_ok, gate GO) ;
- `Dossier_Experimental_M3b_LS15.pdf` — dossier expérimental complet ;
- `legally-subjective-m4-freeze.bundle` — bundle de résilience.

Scripts atelier (`/home/z/my-project/scripts/`) :
- `m3b_local_feasibility.py`, `repro_standards_check.py` (nouveaux du jour).
