# 13 · Reproductibilité M3b — la chaîne de preuve

> Ce document répond à UNE question, posée par n'importe quel chercheur
> tenant le dépôt : **« Prouve-moi que ce résultat vient bien de cette
> expérience précise. »** La réponse n'est pas une capture d'écran : c'est
> une chaîne dont chaque maillon est un **hash re-calculable**.

## 1 · La chaîne

    résultat (m3b_report.json, lignes par juge)
      ↑ dérivé de
    manifeste d'état (state.json — source de vérité unique)
      ↑ signé par
    empreinte d'expérience = sha256({config scientifique, hash des données, seed})
      ↑ calculé depuis
    données (data/m3/personas/<juge>/train.jsonl, hash par juge)
      ↑ sélectionnées par le protocole figé
    gel du protocole (results/protocol_m3b_freeze.json — fragments du
    notebook hachés octet par octet, vérifiés en CI à chaque push)
      ↑ vivant dans
    commit Git (head_initial consigné + m4-freeze ancêtre + git describe)
      ↑ exécuté dans
    environnement consigné (python, torch, transformers, peft, bnb, GPU,
    VRAM — enregistré à CHAQUE session, scellé M4 re-vérifié à chaque
    session avant tout entraînement)
      ↑ raconté par
    journal d'événements (events.jsonl — START, CHECKPOINT, RESUME,
    RECOVERY, VALIDATION, ERROR, JUDGE_COMPLETE, RUN_COMPLETE, EXPORT)
      ↑ corroboré par
    captures de preuves (evidence/ — sorties réelles horodatées, index
    machine-readable)

Chaque flèche est vérifiée par `verify_lineage()` (liens L1-L8) : le
manifeste de lignage est relu, les empreintes re-dérivées depuis le dépôt,
les adaptateurs re-hachés fichier par fichier, le journal re-parcouru,
l'export final re-haché, le scellé M4 re-calculé, le rapport re-dérivé.

## 2 · Les outils (tous dans `scripts/`)

| outil | rôle | sortie |
|---|---|---|
| `m3b_state.py` | la mécanique entière (état, atomicité, journal, preuves, manifeste, lignage) | — |
| `m3b_lineage.py` | remonte la chaîne et re-calcule chaque maillon | ✓/✗ par maillon, rc 0/1 |
| `m3b_gate.py` | portillon GO/NO-GO (G1-G10), exclusion du scellé re-vérifiée indépendamment | verdict + `m3b_gate.json` |
| `m3b_report_gen.py` | rapport expérimental 20 sections, chaque affirmation étiquetée PROUVÉ / TESTÉ / OBSERVÉ / SIMULÉ / NON TESTÉ | `reports/m3b_dossier.md` |
| `build_artifacts.py` | paquet d'artefacts auto-vérifiant (copie hachée avant/après) | `artifacts/` + `hashes.json` |
| `capture_evidence.py` | capture une exécution réelle (commande + sortie + contexte) avec index | `EVIDENCE/` |

## 3 · Re-vérifier une expérience M3b (procédure d'un tiers)

```bash
# 1. cloner le dépôt au commit enregistré dans experiment_manifest.json
git clone https://github.com/Vitalcheffe/legally-subjective.git
cd legally-subjective
git checkout <head_initial>          # consigné dans le manifeste

# 2. remonter la chaîne (chaque hash est re-calculé, jamais cru)
python scripts/m3b_lineage.py --root <dossier d'état> --repo .

# 3. faire rendre son verdict au portillon objectif
python scripts/m3b_gate.py --root <dossier d'état> --repo .

# 4. régénérer le rapport expérimental (étiquettes d'origine incluses)
python scripts/m3b_report_gen.py --root <dossier d'état> --repo .

# 5. assembler un paquet d'artefacts auto-vérifiant
python scripts/build_artifacts.py --root <dossier d'état> --repo . \
     --out /tmp/artifacts
```

Le dossier d'état est soit le dossier Drive `legally-subjective-m3b/`
(l'original), soit le paquet d'artefacts (les hashs du paquet doivent
alors matcher `hashes.json` — deux builds du même état donnent des
paquets octet-identiques : idempotence testée).

## 4 · Ce qui est prouvé, par quel mécanisme

| affirmation | mécanisme de preuve |
|---|---|
| les 50 affaires scellées ne sont JAMAIS dans l'entraînement | CI `m15_audit.py` (14 contrôles) + re-vérification indépendante au portillon (G8) + scellé re-vérifié dans le clone à CHAQUE session avant tout entraînement |
| la méthodologie du notebook n'a pas changé pendant les travaux d'infrastructure | gel du protocole (`test_m3b_protocol_freeze.py`, 12 fragments octet-par-octet, en CI) — une divergence = échec du build |
| un juge « done » a un adaptateur intègre, rechargé et testé | promotion atomique + hash par fichier + rechargement `PeftModel.from_pretrained` + forward logits finis, AVANT le marquage (I4) |
| une coupure ne détruit pas le travail | atomicité (tmp + rename + manifeste en dernier), scénarios A-P d'injection de pannes en VRAIS sous-processus tués brutalement (143 contrôles) |
| la reprise Trainer est exacte (poids + optimizer + scheduler + RNG) | intégration RÉELLE transformers/peft en sous-processus (30 contrôles) — c'est elle qui a attrapé le bug transformers 4.46.3/weights_only AVANT qu'il ne coûte une session |
| l'export est idempotent | zip déterministe (métadonnées figées) — deux exports du même état sont octet-identiques (testé) |
| l'environnement d'exécution est documenté | consigné à chaque session dans state.json + manifeste (GPU, VRAM, versions) ; aucune valeur inventée |
| le journal reflète ce qui s'est réellement passé | append-only + fsync, ligne déchirée réparée/détectée ; incohérence manifeste/journal = échec du portillon (G7) |

## 5 · Étiquettes d'origine (vocabulaire commun)

- **PROUVÉ** : re-vérifié à froid, hash recalculé, reproductible par
  commande ;
- **TESTÉ** : couvert par un test automatisé identifié (fichier + scénario) ;
- **OBSERVÉ** : enregistré par l'exécution (temps, pertes, mémoire) —
  indicatif, pas re-vérifiable a posteriori ;
- **SIMULÉ** : produit par le simulateur ou le pilote CPU — étiqueté
  automatiquement (gpu = « simulator » / « cpu-pilot »), jamais présenté
  comme expérience réelle ;
- **NON TESTÉ** : explicitement manquant — le rapport l'écrit noir sur
  blanc au lieu de remplir du vide.

## 6 · Limites honnêtes

- Le pilote CPU et le simulateur prouvent la MÉCANIQUE (reprise, lignage,
  portillon), pas la qualité scientifique de la condition B : seules les
  sessions Colab T4 réelles produisent l'expérience M3b ;
- la val_loss M3b mesure l'imitation stylistique sur le split de
  validation temporel — AUCUNE métrique de prédiction de vote n'est
  calculée avant M4, par construction ;
- les captures de preuves complètent les journaux machine-readable ; elles
  ne les remplacent jamais, et aucune capture n'est jamais fabriquée,
  simulée ou retouchée — une capture sans commande réelle derrière est
  une fraude, pas une preuve.
