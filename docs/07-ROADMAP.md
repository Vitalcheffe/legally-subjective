# Feuille de route

## Où on en est

| Jalon | État | Contenu |
|---|---|---|
| **M1 — Corpus-Monde** | ✅ **gelé (2026-08-28)** | 569 affaires OT2015–2023, 1 778 opinions, votes SCDB, audio, scellé 5-4 |
| **M2 — Baselines** | ✅ **fait** | Classe majoritaire, idéologie par juge, infirmation, accords inter-juges |
| **M1.5 — Nettoyage** | ✅ **clos (2026-08-30, audit 14/14 PASS)** | Textes 1 778/1 778 (v2), puis dédup+normalisation (v3) : **793 textes distincts** (985 doublons de ré-ingestion fusionnés, carte de provenance complète), en-têtes/pages/notes traités, journal d'audit zéro-fuite `data/m15_store/clean/audit_leak_journal.md` ; personas reconstruits : **477 lignes train** propres (7 juges, Barrett/Jackson 0 par construction) |
| **M3a — Challenger structuré** | ✅ **fait (2026-08-29, résultat nul)** | LR additif / boosting / interactions juge×domaine : 58,6–60,4 % — aucun ne bat B4 (63,1 % sur les mêmes lignes, McNemar p ≤ 0,047). La barre tient ; le signal restant vit dans le texte. `scripts/m3a_train.py` + `results/m3a_report.md` |
| **M3 — Entraînement (LLM)** | ⏳ **prochaine étape** | Personas QLoRA (7 juges avec données train) sur Colab/Kaggle gratuits — M1.5 étant clos, le chemin critique est ouvert (`notebooks/m3b_qlora_personas.ipynb` prêt) |
| **M4 — Épreuve Finale** | ⏳ | Une seule passe sur les 50 affaires scellées |

## M1.5 — Nettoyage (clos — 2026-08-30)

1. **Collecte des textes** : ✅ 1 778/1 778 (voie D CDN storage 99,8 % +
   clôture API 119/135 ; détail `data/m15_store/final/stats.json`).
2. **Déduplication** : ✅ `scripts/m15_clean_texts.py` — ratio ≥ 0,95 sur
   texte normalisé ; 1 778 → **793 textes distincts** (370 groupes exacts,
   91 quasi-doublons fusionnés ; 985 ids documentés dans
   `data/m15_store/clean/dedup_map.json`). L'inventaire du corpus reste
   gelé — la carte de déduplication est de la provenance, pas une édition.
3. **Normalisation** : ✅ même script — en-têtes de slip (« Cite as: »,
   « (Slip Opinion) », en-têtes latéraux), numéros de page, marqueurs
   Harvard, trim de syllabus à la signature ; dépliage des paragraphes ;
   NFC ; notes de bas de page conservées et comptées (~12 100 estimées).
4. **Journal d'audit zéro-fuite** : ✅ `scripts/m15_audit.py` —
   **14/14 PASS** (`data/m15_store/clean/audit_leak_journal.md`) :
   scellé intact et absent de tout dataset, discipline temporelle
   (décision réelle < 2020-10-01), v3 sans doublons, personas conformes,
   casefiles pré-décision, chaîne sha256.

Après reconstruction sur v3 : personas **477 lignes train** (Roberts 43,
Thomas 146, Alito 83, Sotomayor 95, Kagan 50, Gorsuch 39, Kavanaugh 21,
Barrett 0, Jackson 0 — power report obligatoire pour ces deux derniers).

## M3a — Le challenger structuré (fait, résultat nul)

Question opérationnelle : *peut-on entraîner maintenant ?* Réponse
double, archivée dans `results/m3a_report.md` :

1. **Conditions structurées** — les données sont complètes depuis le gel
   du corpus : entraînées le 2026-08-29. Trois challengers (LR additif,
   boosting, interactions juge×domaine), fenêtres pré-décision
   uniquement, scellées exclues de tout split, CV groupé par affaire,
   McNemar contre B4 recalculé sur les mêmes lignes. **Aucun ne bat la
   barre** (58,6–60,4 % contre 63,1 %). Résultat nul, publié tel quel.
2. **Conditions LLM A/B/C** — impossible avant la fin de M1.5
   (112/1 778 textes au 2026-08-29). M3a confirme que c'est LE chemin
   critique : ce qui reste de signal est dans le texte.

## M3 — Entraînement (Colab/Kaggle, 0 €)

- Base : Llama 3 8B, quantification 4 bits (bitsandbytes), QLoRA r=16-64.
- 9 adapters (La Chambre) : Roberts, Thomas, Alito, Sotomayor, Kagan,
  Gorsuch, Kavanaugh, Barrett, Jackson. Le corpus de Jackson (OT2022–2023
  seulement) est notoirement petit — le protocole prévoit un rapport de
  puissance (fenêtre plus courte, mise en garde explicite dans les résultats).
- 1-3 epochs, early stopping, ~10 sessions GPU gratuites au total.
- Audits anti-mémorisation : min-k% prob + cloze, publiés avec chaque adapter.
- Publication : adapters sur Hugging Face, notebook Colab dans `notebooks/`.

### Préparation M3 (fait le 2026-08-30, sans GPU)

- **Rapport de puissance Barrett/Jackson** ✅
  `results/m3_power_report.md` — 0 ligne n'est pas un accident de collecte :
  Barrett (première opinion signée 2021-03-04, 46 au total) et Jackson
  (2023-04-19, 22) n'ont **aucune** opinion avant la garde 2020-10-01.
  Condition B dégradée pré-enregistrée pour ces sièges (base + prompt
  persona, sans adaptateur, étiquetée `persona=base-prompt-only`) ; votes
  couverts par A/C/D.
- **Audits anti-mémorisation dans le notebook** ✅ section 7bis
  (`min-k%` base-vs-adapter sur échantillon train + cloze verbatim,
  résultats dans `m3b_report.json` → `memorization`).
- **Corrections du builder** ✅ prompt persona exact (Roberts = *Chief*
  Justice ; noms canoniques — Oyez dégradeait Alito/Gorsuch/Jackson en
  slugs) ; **dates des segments propagées** (231/477 lignes triaient comme
  « plus récentes » sans date et chargeaient la validation du split
  temporel du notebook) ; audit re-passé **14/14 PASS** après
  régénération.
- **Pré-vol données** ✅ `results/m3_preflight.md` — 7 personas actives,
  split réel train/val, part des lignes débordant MAX_LEN (troncature
  queue documentée, forte pour Alito/Thomas — signal concentré sur le
  début des opinions).

L'étape suivante est l'exécution du notebook sur Colab (T4 suffit) :
`notebooks/m3b_qlora_personas.ipynb`, option A (clone du repo public).

## M4 — Épreuve Finale

Voir `docs/04-PROTOCOLE.md`. Une seule passe, quatre conditions, les 50
affaires scellées, publication des résultats quelles qu'ils soient.

## Ensuite (idées, rien de promis)

- Condition multimodale : la plaidoirie **audio** (98,6 % de couverture) comme
  entrée supplémentaire.
- Matrice d'accord modèle-vs-juge : le persona B prédit-il le vote des
  *autres* juges mieux que son propre juge ? (mesure de style vs substance)
- Extension du corpus vers les cours d'appel fédérales (le pipeline est déjà
  générique — il suffit de changer `court_id`).

## Journal des versions

- **v1.0 (2026-08-28)** : gel du Corpus-Monde + baselines M2 + scellé 5-4.
  Sources : bulk CourtListener 2026-06-30 + API recherche v4 (2026-08-28) +
  SCDB 2025_01. Empreintes dans `data/processed/stats_v1.json`.
