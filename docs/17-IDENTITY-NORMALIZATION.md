# 17 — Normalisation d'identité de l'historique git

> **Ce document est la table de correspondance officielle entre les hashes de commits pré- et post-normalisation d'identité.**

## Ce qui a été fait

Le 8 octobre 2026, à la demande du propriétaire du dépôt, l'intégralité
de l'historique git (les trois branches `main`, `archive/pre-rebuild`,
`site/paper-v1`, et les tags `a1-freeze`, `m4-freeze`, `m4-exam`) a été
ré-attribuée à l'identité unique **VitalCheffe <Amineharchelkorane5@gmail.com>**.

Avant l'opération, les 136 commits étaient répartis sous 9 identités
d'auteurs différentes : l'identité par défaut du conteneur de travail
(`Z User <z@container>`), les pushes des kernels Kaggle du propriétaire
(`AmineHRC <aminehrc@users.noreply.github.com>`), plusieurs variantes de
l'adresse noreply du compte GitHub, et l'identité exacte du propriétaire.
Aucune de ces identités n'était une falsification — chaque commit
correspond à un travail réel — mais l'historique devait être uniforme.

## Ce qui n'a pas changé (vérifiable)

- **Les messages de commit** : identiques, dans le même ordre, sur les
  trois branches (111 + 25 + 37 commits).
- **Les dates** : dates d'auteur et dates de commit conservées pour les
  136 commits.
- **Les contenus** : l'arbre (`tree`) de chacun des 136 commits est
  **bit-identique** avant/après — pas un octet de contenu n'a bougé.
- **Les tags** : mêmes noms, mêmes messages annotés, arbres cibles
  identiques.
- **Les artefacts gelés** (`results/`) : aucun fichier modifié ; les
  chaînes sha256 internes (`m4_exam.lock`, audits) restent valides.

## Ce qui a changé (inévitable cryptographiquement)

- Les champs **auteur** et **committeur** de chaque commit (désormais tous
  à VitalCheffe <Amineharchelkorane5@gmail.com>).
- Par conséquent **les SHA des commits** : l'auteur fait partie de
  l'objet commit signé ; changer l'auteur change le hash, même à contenu
  identique. C'est la seule raison du changement de hash.

## Tags de gel scientifique

| Tag | Ancien commit | Nouveau commit | Arbre |
|---|---|---|---|
| `a1-freeze` | `6d713e40b9` | `9248bfc5f0` | identique |
| `m4-freeze` | `843283e0a4` | `8be32afac6` | identique |
| `m4-exam` | `2aff6a0fda` | `f6145a5b48` | identique |

## Comment résoudre un hash pré-normalisation

Certains enregistrements historiques citent des hashes PRÉ-normalisation
et sont volontairement laissés tels quels :
- les champs `head` / `pinned.head` des artefacts gelés
  (`results/m4_predictions.json`, `results/m4_report.json`,
  `results/a1_run_manifest.json`, `results/m4_exam.lock`) —
  immuables par discipline de gel ;
- les constantes `REPO_COMMIT` des scripts d'exécution Kaggle
  (`scripts/m3b_kaggle_runner.py`, `scripts/m3b_kaggle_probe.py`,
  `scripts/m3b_eval_microtest.py`) — elles documentent le commit qui a
  réellement tourné à l'époque ;
- divers rapports sous `results/` (même raison que ci-dessus).

**Règle : tout hash ancien ci-dessous se traduit par le hash nouveau de
la même ligne ; l'arbre (le contenu) est identique.** La documentation
vivante (`paper/`, `docs/`, script des figures) a déjà été re-pointée
vers les nouveaux hashes.

## Table de correspondance (136 commits)

| Ancien | Nouveau | Date | Sujet |
|---|---|---|---|
| `00da7543f0` | `00da7543f0` | 2026-08-26 | matrix: phase 5 — institutional light theme (Codex) — warm ivory paper, ink navy accent... |
| `0408cf982d` | `0408cf982d` | 2026-08-26 | ci: the corpus joins the gate — 1,387 cases validated on every push |
| `0df3bd8256` | `0df3bd8256` | 2026-08-26 | docs: add project manifest — quality gates R1-R10 |
| `1838bebd14` | `1838bebd14` | 2026-08-26 | matrix: phase 4 — experimental protocol engine (module 10) + author attribution |
| `21afc98a95` | `21afc98a95` | 2026-08-26 | docs: phase 4 — the console becomes a laboratory |
| `44fec0059a` | `44fec0059a` | 2026-08-26 | feat: add structured preprocessing with evidence-based extraction (panel, disposition, ... |
| `55fa237e6c` | `55fa237e6c` | 2026-08-26 | matrix: phase 6 — INFINITUM Mail, the public interface (jmail system) |
| `69817e6c84` | `69817e6c84` | 2026-08-26 | docs: phase 2 report — the corpus, the base rate, the honest gaps |
| `6ac79525e0` | `6ac79525e0` | 2026-08-26 | data: add structured 5-case sample (rule + LLM cross-validated, 5/5 agreement); feat: o... |
| `6ada141a22` | `6ada141a22` | 2026-08-26 | feat: block architecture — kernel, auto-discovered blocks, pipeline runner |
| `8762d14350` | `8762d14350` | 2026-08-26 | docs: add phase 0 precedents, experimental protocol with power analysis, and Colab feas... |
| `8a96728189` | `8a96728189` | 2026-08-26 | matrix: phase 7 — harden the public door (rate limit + shareable dossiers) |
| `8fd82af392` | `8fd82af392` | 2026-08-26 | chore: bootstrap repository (license, gitignore, env template) |
| `9627076cb8` | `9627076cb8` | 2026-08-26 | docs: phase 7 — pay the documentation debt (status, roadmap, phases 3-7) |
| `9a0621b845` | `9a0621b845` | 2026-08-26 | docs: vision — an infinite construction set |
| `9e93bda0d2` | `9e93bda0d2` | 2026-08-26 | feat: corpus-scale collection — cursor pagination, channel preference, crash-safe resume |
| `ada00a601b` | `ada00a601b` | 2026-08-26 | matrix: behavioral matrix console — ten modules of real-data telemetry over the corpus |
| `af5edc5d1e` | `af5edc5d1e` | 2026-08-26 | docs: phase 3 console — layout entry, README section, roadmap update |
| `c21f92f0b0` | `c21f92f0b0` | 2026-08-26 | ci: golden regression test joins the gate; blocks gain department extraction |
| `c32535353c` | `c32535353c` | 2026-08-26 | data: phase 7 — P0 science archive (verbatim record, versioned) |
| `c57550d014` | `c57550d014` | 2026-08-26 | fix: normalize LLM enum answers at record construction |
| `d6af3d2531` | `d6af3d2531` | 2026-08-26 | feat: add collector module with retry, rate limiting, checkpoint and provenance logging |
| `e9bd4d9199` | `e9bd4d9199` | 2026-08-26 | data: Phase 2 corpus — 1,387 real criminal appeals, 2015-2023 |
| `eb3c6d75f5` | `eb3c6d75f5` | 2026-08-26 | docs: official zero-shot result — 13/16 blind agreements (81.2%) vs 68.8% baseline |
| `f25f16a3b3` | `f25f16a3b3` | 2026-08-26 | feat: add data validation gate and CI workflow; docs: add phase 1 report and project RE... |
| `11c58c422c` | `11c58c422c` | 2026-08-27 | 00fcbf2f-23d9-44c2-8d0a-e6dfe6812abf |
| `14b9d945a2` | `14b9d945a2` | 2026-08-27 | 925b01dc-b91e-4657-8628-55550a6df3a9 |
| `230a3837fd` | `230a3837fd` | 2026-08-27 | front: the home page speaks to humans — THE MAP (URLs) replaced by THE QUESTIONS |
| `2d96d386aa` | `2d96d386aa` | 2026-08-27 | Initial commit |
| `2fd59a21b6` | `2fd59a21b6` | 2026-08-27 | 1e395063-0eb5-4db0-beda-208001863445 |
| `3ec9f3b79b` | `3ec9f3b79b` | 2026-08-27 | manhattan: the roadmap is the law — phase 1 foundation restored and extended |
| `44f54f5a3b` | `44f54f5a3b` | 2026-08-27 | 85ca4c0d-80b7-4b12-beef-16e89d3527e3 |
| `4a0b69a3f3` | `4a0b69a3f3` | 2026-08-27 | a7efe35c-bee8-4c3d-9609-9b3bdd9691a5 |
| `4e71eaad66` | `4e71eaad66` | 2026-08-27 | 8e555dec-a525-466a-b6fe-2b9e47bad34b |
| `50dd356ee7` | `50dd356ee7` | 2026-08-27 | 536c0e77-75a5-43f4-aa42-17a529cdffd9 |
| `5718f046e8` | `5718f046e8` | 2026-08-27 | worklog: incident log — history restored, authorship fixed to VitalCheffe everywhere |
| `67ace98897` | `67ace98897` | 2026-08-27 | 5f18c3dd-676f-4548-9e9d-1c05eed47de5 |
| `8187fa8b21` | `8187fa8b21` | 2026-08-27 | 25c61850-0d7a-477c-b297-e6a91d42ec9c |
| `87a33169a6` | `87a33169a6` | 2026-08-27 | chore: repo hygiene — untrack sandbox artifacts, harden .gitignore |
| `8ff3f3b007` | `8ff3f3b007` | 2026-08-27 | worklog: session sync — GitHub access audit, remote sync |
| `97ce02f777` | `97ce02f777` | 2026-08-27 | audit: the judge against the project — LS-AUDIT-001 instruction report |
| `a3aa739393` | `a3aa739393` | 2026-08-27 | c4f728e6-2056-4c6c-a6ea-e6c315595569 |
| `a3f38a75cf` | `a3f38a75cf` | 2026-08-27 | front: THE DRAW — the roulette is the storefront |
| `add4a7b1aa` | `add4a7b1aa` | 2026-08-27 | c96804d4-e7e7-4130-85a9-4a62bd2a97f6 |
| `b001a783c5` | `b001a783c5` | 2026-08-27 | fix(deploy): Vercel-ready — vaul removed, package-lock.json pinned, all routes static (... |
| `c883d38a5b` | `c883d38a5b` | 2026-08-27 | 08953b4f-c856-4320-ab8f-08fb2bbb2f36 |
| `cb75a3d05a` | `cb75a3d05a` | 2026-08-27 | d6d96dfd-cb8e-4558-b730-ceaf33cdb2f5 |
| `d24cd892e1` | `d24cd892e1` | 2026-08-27 | d503f562-9515-45e5-850d-a15e5be55beb |
| `d60c9ac0bb` | `d60c9ac0bb` | 2026-08-27 | sentence: the audit's 12 injunctions executed — uncertainty becomes the brand |
| `e913215b5e` | `e913215b5e` | 2026-08-27 | the science: train the model for real — LS-R-001 research article, searchable record, c... |
| `fb33e72b73` | `fb33e72b73` | 2026-08-27 | 828ee3f2-a9d9-4658-9eda-5f26f4a5752b |
| `1e8f3f5fed` | `48e351aef4` | 2026-08-28 | m1.5: mode --finalize au veilleur (sandbox tue les processus d'arrière-plan) |
| `1f18c0679c` | `2679150d77` | 2026-08-28 | docs: vision, méthodologie, protocole scellé, reproductibilité, limites |
| `3368aa087f` | `a33a53e9cc` | 2026-08-28 | docs: rattachement du site au corpus fait — README et roadmap alignés |
| `390cf623ea` | `15a1a2081c` | 2026-08-28 | m1.5: mode quota au collecteur — le token gratuit est à 5 req/min |
| `4c8d5595f7` | `d769c8e802` | 2026-08-28 | docs(m2): correction du chiffre B3 — toujours infirmer = 60,1 % [51,8 ; 67,9] |
| `6376d3d0da` | `157936f4a1` | 2026-08-28 | site: le site statique du projet — Subjectivity, measured. |
| `7ec7c9e420` | `00829d1ea6` | 2026-08-28 | m1.5: pacing proactif — la vraie physique du token gratuit mesurée |
| `8aced95924` | `aac0586e3a` | 2026-08-28 | front: THE DRAW est de retour — restauration intégrale de l'ancien site |
| `9d628c6a66` | `b90519b8ca` | 2026-08-28 | m1: gel du Corpus-Monde v1 (569 affaires, OT2015-2023) |
| `aa3efa7a9b` | `67cdaf79b1` | 2026-08-28 | docs: ressources juridiques publiques + correction des IC dans les README |
| `ae183b8fdc` | `7d361192a6` | 2026-08-28 | docs: README alignés sur le retour de l'ancien site (src/, npm ci, note corpus) |
| `b252192ce6` | `c1d94d0124` | 2026-08-28 | standard: LS-1.0 restauré — perdu au rebuild, retrouvé dans l'historique |
| `b52b543911` | `91c1c0e585` | 2026-08-28 | rebuild: retrait de l'arborescence de l'itération précédente |
| `b817b1f0f5` | `cd76948a4c` | 2026-08-28 | m1.5: veilleur de collecte autonome |
| `c8abccbd4f` | `05f2f877dc` | 2026-08-28 | front: THE DRAW et toutes les pages sur le Corpus-Monde — treize portes |
| `d31c0a6f74` | `5591b0cbd2` | 2026-08-28 | m1: chaîne de collecte complète (bulk segmenté + API recherche) |
| `d5eed39fbe` | `29d39f3eba` | 2026-08-28 | m2: baselines statistiques — le pari à battre |
| `d92ed50d9c` | `9ee3548383` | 2026-08-28 | data: la transfusion — le socle de données du site régénéré sur le Corpus-Monde v1 |
| `e8adf70715` | `24cc53a017` | 2026-08-28 | rebuild: pivot vers Corpus-Monde SCOTUS — squelette du projet |
| `035b751e00` | `73136a79c3` | 2026-08-29 | data: oyez source files (550 dockets) — case-file inputs, protect against env resets |
| `255f0f6347` | `cc4c4a4990` | 2026-08-29 | m1.5: cooldown persistant — le mur 429 s'écrit dans l'état, les passes sautent au lieu ... |
| `281f6786f4` | `8df26ac1be` | 2026-08-29 | exhibits: LS-EXHIBIT-1.1 — the six exhibits refounded as adaptive SVGs |
| `34f83f6e4a` | `0d1cc9ddc7` | 2026-08-29 | M1.5: prédictions chiffrées avant exécution (pré-enregistrement) |
| `41d2fc7cdc` | `2f426394da` | 2026-08-29 | m1.5-b: segmented bulk scanner — bit-shift bz2 repair, dual-anchor extraction, budget-a... |
| `49f80767fb` | `10aba7002e` | 2026-08-29 | M1.5: README provenance m15_store + script de simulation |
| `503aec61fa` | `1d7287f3ca` | 2026-08-29 | docs: LS-R-003 — the project from A to Z, the full report filed |
| `52cc9755c7` | `0e392687f1` | 2026-08-29 | m3: persona datasets live — 156 training rows (bound + slip segments, oyez-guarded), bu... |
| `5427a6b7a9` | `46eae1ca7f` | 2026-08-29 | readme: the exhibit system — English primary, the six exhibits filed |
| `599527d109` | `c23b971a5a` | 2026-08-29 | paper: the working paper — corpus, protocol, baselines, and the M3a null result |
| `5cb24189c5` | `5cb5d6b5af` | 2026-08-29 | m1.5-c: supremecourt.gov slip harvester — volume preliminary-print extraction, judge se... |
| `6146a3df04` | `f660fe1de1` | 2026-08-29 | M1.5: merge idempotent + simulation validée ; notebook: URL repo réelle |
| `7157de3e50` | `1cbc737c3e` | 2026-08-29 | M3b: notebook QLoRA personas (condition B) — générateur + validateur |
| `77130fe398` | `5beb5e106c` | 2026-08-29 | m1.5: the daily wall measured — 125 requests/day, so the drip became a batch |
| `cc2dd77a7c` | `40648faab3` | 2026-08-29 | docs: the visual guide — LS-EXHIBIT-1.0, the AEGIS template re-grounded for the house |
| `cfe7c2de2a` | `6a56f02e74` | 2026-08-29 | exhibits: LS-EXHIBIT-1.2 — two faces, two files, one <picture> |
| `e1c197d0f6` | `6dcbff2b28` | 2026-08-29 | m3a: the structured challenger — trained, and the bar held (null result) |
| `e635d2bcee` | `405290a9ca` | 2026-08-29 | m1.5: the drip's gzip appends corrupted the store — atomic rewrites, robust reader, hon... |
| `eebcd3b760` | `1e3d782591` | 2026-08-29 | M1.5: scripts de clôture API (id__in batches, budget-aware, resumable) + merge final |
| `10b91ab33b` | `0a5f9afb37` | 2026-08-30 | fix: plancher bnb >=0.47.0,<0.51 — 0.46.2 n'existe pas sur PyPI (0.46.1→0.47.0); borne ... |
| `13e7ecd071` | `61992e4916` | 2026-08-30 | M1.5 voie D: CDN storage (99,8% couverture) + attribution par signature (96,7% validé) ... |
| `6a352799ec` | `e3ed974e9d` | 2026-08-30 | M1.5 final: 119/135 top-ups (116 xml_harvard), 16 snippets résiduels; personas 513 lignes |
| `6be0f42bb2` | `4566ea3dcb` | 2026-08-30 | fix colab: bitsandbytes plancher >=0.46.2 — la 0.45.0 importe triton.ops (supprimé dans... |
| `93944b5f52` | `214e12edeb` | 2026-08-30 | m1.5 clos : dédup+normalisation v3 (1778→793 textes distincts), audit zéro-fuite 14/14 ... |
| `9d378b6db2` | `2f3a3d98e4` | 2026-08-30 | M3 préparation sans GPU: power report Barrett/Jackson, audits min-k%+cloze (notebook 7b... |
| `e7dd0a5adf` | `32bdebc227` | 2026-08-30 | M1.5 CLOSE À 100% (1778/1778) — personas 502 lignes propres |
| `32197a90c0` | `97aab122b5` | 2026-10-03 | m4 pré-vol : portillon de readiness — chaîne de pré-enregistrement vérifiée, audit zéro... |
| `647a2cd089` | `eee8ad8443` | 2026-10-03 | ci : chaîne de vérification à chaque push — audit zéro-fuite (14 contrôles), portillon ... |
| `6a992d5af2` | `dc09227ec3` | 2026-10-03 | m4 : noyau statistique de l'épreuve — Wilson + bootstrap 10k déterministe (graine du sc... |
| `afa17c9359` | `2e9c6a3a19` | 2026-10-03 | validate_notebook : lecture JSON stdlib (un notebook est du JSON) — le validateur ne dé... |
| `025ec0badc` | `290c67d996` | 2026-10-04 | papier r2 : révision critique — bornes du claim, comparateur scellé, prudence lexicale |
| `0fc4be67f8` | `983f1af028` | 2026-10-04 | m3b v2 : architecture durable — reprise automatique Drive, checkpoints intra-juge, arrê... |
| `1b094720ab` | `8108d4260f` | 2026-10-04 | état froid re-vérifié post-fusion : porte PENDING (12 PASS, R6=M3b attendu), audit 14/1... |
| `3107062ca0` | `a976ce3633` | 2026-10-04 | état froid re-vérifié : porte PENDING (12 PASS, R6=M3b attendu), journaux régénérés |
| `329efa4c18` | `e7c7c3d1e9` | 2026-10-04 | m3b LS-17 : acquire_repo accepte l'archive opaque .tar.bin (pas d'extraction serveur, .... |
| `51c34e754f` | `06ec7446be` | 2026-10-04 | m3b : reprise multisession + guide d'exécution Colab (M3b -> M4) |
| `55462bb612` | `93d1bd749e` | 2026-10-04 | m3b LS-16 : faisabilité locale mesurée (impossible, 4 bloqueurs réels), standards repro... |
| `7082bae027` | `350dee307b` | 2026-10-04 | m3b LS-17 : acquire_repo route tar (dataset code = archive du dépôt + .git, arbre vérif... |
| `74703ddf6e` | `fef077758e` | 2026-10-04 | M4: fuite du scellé réparée + porte de pré-vol + pré-inscription de l'analyse + runner |
| `7ff7ffd603` | `a47018ff56` | 2026-10-04 | m3b LS-17 : runner — un rc=137 réel (OOM) n'est toléré QUE si le kill était demandé (ja... |
| `9446789f40` | `fffda9ef7e` | 2026-10-04 | m3b LS-17 : exécution Kaggle — runner exécutant les cellules gelées verbatim (shims inf... |
| `a8a3341c98` | `6fc37e88e2` | 2026-10-04 | m3b : garde GPU avant install (retour utilisateur CPU runtime) + gel du protocole scien... |
| `b9217486f9` | `2c2188efbd` | 2026-10-04 | m3b v3 : lignage complet + journal d'événements + preuves + portillon GO/NO-GO |
| `c52e351dd4` | `f4b7fa4118` | 2026-10-04 | m3b : m3b_lineage.py (remontée de chaîne CLI) + m3b_report_gen.py (20 sections, étiquet... |
| `d12b8c47d1` | `694678bfa2` | 2026-10-04 | m3b v3 : docs — guide Colab v3 (garde GPU anticipée, portillon en fin de §8), reproduct... |
| `d96582ad10` | `a04a4bac50` | 2026-10-04 | M4: porte de pré-vol — verdict PENDING (13 PASS, R6 en attente M3b) |
| `de174fb8d5` | `2d010356e9` | 2026-10-04 | fusion lignes M4 parallèles : porte post-fuite + noyau statistique + CI |
| `044a665517` | `e6284e35bb` | 2026-10-05 | m3b micro-test : dé-indentation du fragment TrainingArguments avant exécution |
| `127514611d` | `33cf26471c` | 2026-10-05 | m3b micro-test : SHIM AVANT les cellules de données (bug v4 du runner) |
| `74c5ec5cee` | `84047ba2b2` | 2026-10-05 | m3b : audit du rituel de réparation — verdict GO S2 |
| `8866c0a0b3` | `c30bfdb3f4` | 2026-10-05 | m3b : RESYNCHRONISATION du runner du repo sur le source kernel qui a réellement tourné s1 |
| `960279ec1a` | `68e2bf7fe0` | 2026-10-05 | m3b : correctif évaluation — per_device_eval_batch_size=1 (OOM T4 déterministe) |
| `dbb032bb58` | `fb7c0629ac` | 2026-10-05 | m3b : micro-test d'évaluation (rituel de réparation) — kernel d'audit dédié |
| `edf13590f9` | `7e98ff1d81` | 2026-10-05 | m3b LS-18 : plan de session DÉDUIT des state.json — remaining_steps juge par juge, jama... |
| `2aff6a0fda` | `f6145a5b48` | 2026-10-06 | M4 : L'Épreuve exécutée (une seule fois, scellé intègre) — résultats publiés quels qu'i... |
| `6d713e40b9` | `9248bfc5f0` | 2026-10-06 | A1 phase 1 : pré-enregistrement E1+E3 figé (D1-bis) — plan asymétrie + addendum d'implé... |
| `843283e0a4` | `8be32afac6` | 2026-10-06 | M4 phase T : pré-vol READY (13 PASS, R6 PASS) — artefacts M3b déposés et vérifiés |
| `056713ff87` | `35c7a4d8de` | 2026-10-07 | results : publication du rapport d'entraînement m3b (ADD, aucun gel modifié) |
| `3d9f078536` | `940b1d55d9` | 2026-10-07 | paper : cinq figures principales D1-bis (M4 primaire, dial idéologique, décomposition E... |
| `66a544fe89` | `ad3a0040e9` | 2026-10-07 | paper : version narrative — abstract v1 + récit aligné sur les résultats |
| `68b1a4597f` | `e4185799c2` | 2026-10-07 | A1 : E1+E3 exécutés selon le plan pré-enregistré (tag a1-freeze) — résultats publiés qu... |
| `70dd744323` | `ed1b5bfe11` | 2026-10-07 | D1-bis : verrouillage court des résultats E1/E2/E3 — variance cuBLAS = hypothèse diagno... |
| `874b37679d` | `8f0f9318d2` | 2026-10-07 | paper : titre-tension + abstract final — fin calibrée au niveau de preuve §5 |
| `93000afeaa` | `70a3a14598` | 2026-10-07 | paper : passe éditoriale hostile v1 — titre-question + 13 corrections de calibrage |
| `d72bf695b5` | `614e58d78e` | 2026-10-07 | paper : positioning v1 — §2 situe le nul dans la littérature de l'ère LLM |
| `e21e8228cf` | `d98f59a8dd` | 2026-10-07 | paper : version Results — §5 intégré, revu et scellé (GO scientifique) |

## Carte machine-readable (SHA complets)

```
00da7543f034e20603fbf5aa1bf0bb77ec9d8cfb 00da7543f034e20603fbf5aa1bf0bb77ec9d8cfb
025ec0badc5c51d1a9d45dca19282463ab4abb3d 290c67d9967037f4aa4514e7b27f33681e41a9c7
035b751e0033b812c6dc54e5662c36c0c701982d 73136a79c3c87745e75dc5bd57998558c034c840
0408cf982d7f5fc2a7f6c24c4ffe69df0c690f39 0408cf982d7f5fc2a7f6c24c4ffe69df0c690f39
044a665517f6722f2e7ab689bce53c91db5909e8 e6284e35bba528fd2994e80644631c85e90dc3e1
056713ff8747738849bd22ce0c3fca7a38c07be2 35c7a4d8de11ef9604d425fd88a0bcae2e82f421
0df3bd825690dc88c16e6ab9904ab95266bc738f 0df3bd825690dc88c16e6ab9904ab95266bc738f
0fc4be67f881bf0bc64c71845d54c0cf04df646a 983f1af028e06d4d5a7841a5977b8da78c7876f8
10b91ab33baab59b4b22c4440e8b3686bfa87041 0a5f9afb3750c274209a25a5f440208c4f32bf3b
11c58c422cfeb45425bc4716ba36b6f1fcd658dc 11c58c422cfeb45425bc4716ba36b6f1fcd658dc
127514611d048fbb193bf3b15217761afc42449d 33cf26471cf28c33a704fa145a58f8a0e24055ad
13e7ecd071075d98679488b58af976b1b5c0bd95 61992e491698317250b35526c7ded0473b14d020
14b9d945a2d004202f5ae0c5c2e78e4771f332cd 14b9d945a2d004202f5ae0c5c2e78e4771f332cd
1838bebd149352310fc2a7a857c8c6823cecf557 1838bebd149352310fc2a7a857c8c6823cecf557
1b094720ab7201c8971ab1f575abb747dd3523b2 8108d4260fe2eb32bcb852bccab2d7cfb5127a68
1e8f3f5fedd01596bf67823a22acb753ca0b074b 48e351aef4d437a31543f07683301cda714793cd
1f18c0679cc6993791e2251dc668d4c4ef46e03c 2679150d770ad3b15e2b9412aebb1507f07a0414
21afc98a95da65dc7a3d3049f318519adb9bed4b 21afc98a95da65dc7a3d3049f318519adb9bed4b
230a3837fd697776c004c3ad04be22d1e2baf554 230a3837fd697776c004c3ad04be22d1e2baf554
255f0f63478ca56641a6c059386c7c6bc8a3e354 cc4c4a499022f4bbd31ee872cf35c67e75ff5585
281f6786f4776e2fc48cdb7f370de3145c6d16b8 8df26ac1be8e469c85a57949becd52b04c024f03
2aff6a0fda8e179c33bb988ea1ee62ca05de5d3b f6145a5b484196cc37f86a65dad30e8eeeead2de
2d96d386aaf37a0ed1b8638ff0070c6f0a63944b 2d96d386aaf37a0ed1b8638ff0070c6f0a63944b
2fd59a21b63b4c4b6156a6285329f77758f40b6e 2fd59a21b63b4c4b6156a6285329f77758f40b6e
3107062ca0fafb8b7d995714d0990d475ce237c2 a976ce3633a80e7f2a02c1972e76d300742e1c42
32197a90c02e37f80f1e7f5763199809cad364d0 97aab122b5017c58bb38f92a7bea51d5efb00882
329efa4c18e26dde0c635c8e0711849c54f9241c e7c7c3d1e98bbc966271a3a2bae95b6e8ff28f43
3368aa087f50bf0a268d5aebc074c6f754e6c4db a33a53e9ccae11cb8665f7a27f803afd2dc2a8e0
34f83f6e4a060f1040fdb200aae18013dd156f63 0d1cc9ddc7e8a6620b4ed12895380df0248eaa46
390cf623ea41f6167e12f581ceedd3465a50a2ac 15a1a2081cb8afdf9a6a744cc80f84b94440845d
3d9f0785363f5a3cc9c4a8bb96614cc2b648764f 940b1d55d9e7e56e34a005f9fd68b274514c0279
3ec9f3b79bad9cd47f37147e3e3bdb3daeec8eb9 3ec9f3b79bad9cd47f37147e3e3bdb3daeec8eb9
41d2fc7cdc567b486e3ca93ed36e0db091bc133c 2f426394da0cec085516868a8ae275fe8f8837a1
44f54f5a3b735ec353a08e7f6bff632807d25550 44f54f5a3b735ec353a08e7f6bff632807d25550
44fec0059a9e56d03141f4e9faf8fd557cc21fbd 44fec0059a9e56d03141f4e9faf8fd557cc21fbd
49f80767fbb6902df8adc1b550831efac7be817f 10aba7002e18f05157094af0cbeb1639b6fe00fe
4a0b69a3f38e8c0026e82ad9343bf084bfe62fd4 4a0b69a3f38e8c0026e82ad9343bf084bfe62fd4
4c8d5595f7bda3d8777680eb5cc504354933cbb4 d769c8e802b238c6ce8bdb2d06b7d44aa421d4d4
4e71eaad66e18cba30d555eb13c214e04680ed32 4e71eaad66e18cba30d555eb13c214e04680ed32
503aec61fa4798460171cba3db9cc4913e9f2c11 1d7287f3ca324dcb4b0572d95d14b84e00d5402e
50dd356ee70919d6ddb4a695f0e01b2ce9c1f33b 50dd356ee70919d6ddb4a695f0e01b2ce9c1f33b
51c34e754f137d262cc20dd5802989fb486479d4 06ec7446be41e6158477c8d46d767a4449336350
52cc9755c71435d9632c968560eb6ff67db1982d 0e392687f1e50e1107831aeba3daf5d6e4174e3e
5427a6b7a94f4df5be619e56cbdb829d426571a3 46eae1ca7f0efcda54345a831c26b01cbdd2ae3f
55462bb6129715ef5a76f06e088a528ca9d8bfa7 93d1bd749e9e1ac37541ba11891b5442b3706dcd
55fa237e6c25d5bdbd1b8c417fe30baac82139f5 55fa237e6c25d5bdbd1b8c417fe30baac82139f5
5718f046e860474b8577ac8c43a81dbd0be0c895 5718f046e860474b8577ac8c43a81dbd0be0c895
599527d109d920ed335bd2266295db29ac6ac32f c23b971a5a6077ba7a56cd00780be4467307b478
5cb24189c5a511994326fab394bec932d86a147f 5cb5d6b5af1af89e521ba75927e7879e7e5f5ee7
6146a3df04408230814bb8f0e9f5699c7e30e38f f660fe1de1ab6935e431b3dd4b0949f143694118
6376d3d0daf0910a1e669de4c784883ae9dde30d 157936f4a1d87d84790d430b487cb5ad69b20db0
647a2cd0897278e63f4d5487af864c3c984737c7 eee8ad8443b1981c7af0693516e875798649f32e
66a544fe8930a844484b380febf2c9406f310227 ad3a0040e9bebc9dd84e979b214faf62a9f0874a
67ace988975165a8c2446252d1b535e7c4d27ec7 67ace988975165a8c2446252d1b535e7c4d27ec7
68b1a4597f467299672c2eb2f65ac049e6db45c7 e4185799c2d233df55299ed3350c962bec2cb9f4
69817e6c84a46b1df9eaecc4011b288252654a4e 69817e6c84a46b1df9eaecc4011b288252654a4e
6a352799ecf0547f3b7e77b10bbc966fe5c4b1c4 e3ed974e9d39698e37fd532b444831afb5ddf731
6a992d5af24eaaf81baa58e3d7866e8d3dfbb310 dc09227ec370aa9ec2b7fa08a9d2494254434097
6ac79525e01fb79f730486e36bccc4fb689ed780 6ac79525e01fb79f730486e36bccc4fb689ed780
6ada141a229be5134fe00dcf3f60101328ae82f5 6ada141a229be5134fe00dcf3f60101328ae82f5
6be0f42bb2ac22933b268babb35574cc40c2e746 4566ea3dcb458c1c1569cb945b7f3c80dfe2577e
6d713e40b943fdf86abd81c30cc1b608365be25d 9248bfc5f06dc3e0df682b81a087ac7fbb27a6cb
7082bae0273bc11007c755243300c6abab23993c 350dee307b659a0f662d1c4af033a92a76966467
70dd7443232e92b9e26dfc73d713ba70a1e0b15f ed1b5bfe1192fedec1a0d72df6ca0719ad0c4c68
7157de3e5011200cd27a22dd2ea973fe1e6164ba 1cbc737c3e2586663af4362ef0ddcffe76c19eb1
74703ddf6eb12b3f911e9525cbdd4e3c12b8eabb fef077758e2b88072e03fd316b6e76e67fcb3aa2
74c5ec5cee8d8a9f9ed716fcfba2cf188be98b70 84047ba2b2a96fbb6ed510148bfbd596444781dd
77130fe398f05858dd048ba37691624f7ebdd35d 5beb5e106c29f329758ce86e763274fee8fbcafc
7ec7c9e420d97fa733f6c6014b1d1b2868f9f0e7 00829d1ea650c9e0f0474855c4f899d187f577c0
7ff7ffd60356fef830213bd0ed7efa6d41830368 a47018ff563340f66837e75e5d7d0aecacc75acf
8187fa8b21e7afaa44dce71841277a6c902e47f8 8187fa8b21e7afaa44dce71841277a6c902e47f8
843283e0a472de7cae6f9acb689131f8766cf3a8 8be32afac67116ab1288c8078d936be0a8a040ee
874b37679df8186851b4d5745371f6c120675a2d 8f0f9318d20a92af2aa975f90154f0b9018de69d
8762d14350227960bc78dc7f74f4f87700878383 8762d14350227960bc78dc7f74f4f87700878383
87a33169a6e0dbcee5d82cb256101e39f0822c34 87a33169a6e0dbcee5d82cb256101e39f0822c34
8866c0a0b39e619da9cd2c74057d6e38a38911e1 c30bfdb3f45b58b4b20947486f577edd33993842
8a96728189d90e98e14d2be7d42966ad43ec6888 8a96728189d90e98e14d2be7d42966ad43ec6888
8aced95924abebc7b5943db91e685944ca78ace6 aac0586e3a66c8a942dac818cd8c12dd2385566b
8fd82af392dfa5e7dc100d4354aede7fd641120d 8fd82af392dfa5e7dc100d4354aede7fd641120d
8ff3f3b0077dc16664edfbd2834e62f7b2be307d 8ff3f3b0077dc16664edfbd2834e62f7b2be307d
93000afeaac944e32252ef97eaecb3ab96ea9f72 70a3a14598108ba480faba3020c23ccb7853eda6
93944b5f52616be8ab716df242186ac629b10a73 214e12edeb7c3370f84cb8681b93a622862bec08
9446789f40df2aa868dea55e8e92225ffdbae8c4 fffda9ef7ec04de6d83185285d15bbec8c7df60f
960279ec1acabe23d9bbf58bb53b01aacf247138 68e2bf7fe0c8d08a5d5a0e99ccc3f3fc043555bd
9627076cb8fbdf3b2a958e714142a34563e66a15 9627076cb8fbdf3b2a958e714142a34563e66a15
97ce02f77749120dad2884f2e20f2b09c9b76e47 97ce02f77749120dad2884f2e20f2b09c9b76e47
9a0621b845e794f02cf3c670cd92a8de1b55c3d4 9a0621b845e794f02cf3c670cd92a8de1b55c3d4
9d378b6db298df4f8b8356d149cb295bc0528737 2f3a3d98e4fa63e5b5e1f57bf3f3b4eaaa49615e
9d628c6a6677ed9ab64e5f8ef09535ecd6146378 b90519b8ca1a25239664bb4db19c3caba7f945cd
9e93bda0d2ad8e274a5982d90179bbc28166c31d 9e93bda0d2ad8e274a5982d90179bbc28166c31d
a3aa739393c9b5911a3f12286d8341fc79e963d2 a3aa739393c9b5911a3f12286d8341fc79e963d2
a3f38a75cfb968d3fc00de8b085f1b196c10f167 a3f38a75cfb968d3fc00de8b085f1b196c10f167
a8a3341c98377815f87f1d78318ddef247b36669 6fc37e88e28777ed0c87894707851616ca69b7c7
aa3efa7a9b4d55894540daa821dfd24523714510 67cdaf79b1e692e0eb4cc08cf97c7664f807ad2f
ada00a601b73c9db6c18a47acd956af03155a704 ada00a601b73c9db6c18a47acd956af03155a704
add4a7b1aa4a381affa1758e254e5fa52c9e1852 add4a7b1aa4a381affa1758e254e5fa52c9e1852
ae183b8fdc0b653369dbba1893bf7e00c9b6c0be 7d361192a6b7d1cb37fb16a7b16502c95162ac5b
af5edc5d1e61a2f2b2e08cd8f21d849ea381cc15 af5edc5d1e61a2f2b2e08cd8f21d849ea381cc15
afa17c935983ba45fc93b844c27cfc16947f2db3 2e9c6a3a19d2668b389e47509b2bac9d291c2256
b001a783c546d4eb37c216111c1b286fd3272f25 b001a783c546d4eb37c216111c1b286fd3272f25
b252192ce62ff9bb3d4f30ec8a23085fd1919bf8 c1d94d0124b07e7ef5779b78869c01d5e36c8665
b52b5439115513b21e96ce96152d8ee45b4352f9 91c1c0e585419f5d805d70c4262f6df41ce64fc5
b817b1f0f501fccd065755b0adf5d9d0f0c01f43 cd76948a4ce00c894de843c07f5b275280826e54
b9217486f9a79b94f047be35121cabaa6ab55291 2c2188efbd25e77e5dfa076bff6a3038f08912ed
c21f92f0b0e6cd28754cfea96d547402a1066af7 c21f92f0b0e6cd28754cfea96d547402a1066af7
c32535353cfec0f2b597708ceee7969582853038 c32535353cfec0f2b597708ceee7969582853038
c52e351dd4b475ef35b2e52b52791c462c6d7686 f4b7fa4118c29af1c86a93192235c41d89df4135
c57550d01454f9610258275f8e05b711c452ae37 c57550d01454f9610258275f8e05b711c452ae37
c883d38a5bbed12d28126983e14edd2ac9e1f491 c883d38a5bbed12d28126983e14edd2ac9e1f491
c8abccbd4f632d6010e112ddd19bdfeefa1aca58 05f2f877dc09d04eee6eaa18a8c4edcc404f29a1
cb75a3d05ad2e812e8a0fd5b306816932ae8de7d cb75a3d05ad2e812e8a0fd5b306816932ae8de7d
cc2dd77a7cec19235ed51bd7aa012aab4b86ea3b 40648faab3a7b714e08919265599df1f91579246
cfe7c2de2a708b597dc340840e90c1ec9077cd8e 6a56f02e742e092189a623dade83f21f006dc0c2
d12b8c47d1cbae04980ba24cde40d75c09535529 694678bfa2e1065d3d9b700f2c0dedc4390292ec
d24cd892e156a3429e425173d2627eda453a226c d24cd892e156a3429e425173d2627eda453a226c
d31c0a6f747eb68b90da2c66df3ac73541bec0b4 5591b0cbd26e3c9a7779cb6f5c276a80693c7d60
d5eed39fbecb4e503d38e92075768100c951a954 29d39f3eba6c81be2f6d276ad7dc21a199cda21c
d60c9ac0bbf6a5b1e84ebd7e3a0d6af8acf1b6ec d60c9ac0bbf6a5b1e84ebd7e3a0d6af8acf1b6ec
d6af3d25317e833d28b0359ae4aeb4d1aa428218 d6af3d25317e833d28b0359ae4aeb4d1aa428218
d72bf695b5b095911866e8f36b979d501b400b67 614e58d78e486d7d4c672397ef856dcf43973a7e
d92ed50d9c3682eb1c291b736d54af9e4f62c89a 9ee3548383893998e3d9f1d9e1033691e7bd813f
d96582ad10e093a841fc6bb89e810719e4f3ae9d a04a4bac500597d520c4102aff3537cd4a6f4ea0
dbb032bb58e77da9c59f36fa9daadc60c3590cba fb7c0629ac7ce25fcb7b847b05c2ff2a370d41d8
de174fb8d5b4301257a1a9d55048e0c3077c4d34 2d010356e9d9d62996216287b28b32a053a52608
e1c197d0f6f04481f2b1822ec438019d03b012e5 6dcbff2b2867de3170def7227d2fbdd5757a91a0
e21e8228cfb875b7ebee2a657d3909bcfb02ffbd d98f59a8dd20ddec7fbc79bf2719e9e110c01ec1
e635d2bcee9a37a9186fd18f8c94c6e2a607b366 405290a9cac8af13abf11104fcd30ce281dff8f6
e7dd0a5adf3a07158ffffb5fbf06a4b66ef50a6d 32bdebc22714719abf354adb1f66a544b09f66c9
e8adf707151ce7a1199a5e5ccbd3d597e7db0fed 24cc53a017481520e8ab35b1d50562bb544bf755
e913215b5e168eaf4c078522854b611469a42887 e913215b5e168eaf4c078522854b611469a42887
e9bd4d91990f991b85a9d38519f972431317934c e9bd4d91990f991b85a9d38519f972431317934c
eb3c6d75f5b3b31acd76591287e25b7443e2e1a2 eb3c6d75f5b3b31acd76591287e25b7443e2e1a2
edf13590f9de0774a4404f12ced8bd6ac60689d4 7e98ff1d810d26d9dac7034d8d1daf13db3c2ecc
eebcd3b760fdb9639cc431c7b1f04b96bc7aaf1d 1e3d7825914d07393e27f13e8be19a7c325e388c
f25f16a3b301f743021295b35deb7fb14bb90cd3 f25f16a3b301f743021295b35deb7fb14bb90cd3
fb33e72b73e19037b6071c7047bd9dfc4c6dc63f fb33e72b73e19037b6071c7047bd9dfc4c6dc63f
```

## Méthode de vérification

Comparaison multiset `(arbre, sujet, date)` avant/après sur toutes les
références (136/136 identiques), unicité de l'identité auteur+committeur,
égalité des arbres par tag, propreté de l'arbre de travail. Une sauvegarde
complète pré-opération (bundle git, 154 Mo) est conservée côté propriétaire :
`legally-subjective-pre-identity-rewrite.bundle`.
