# M4 — rapport de pré-vol (readiness gate)


## R1

- **PASS** R1.corpus_gelé — n_cases=569, n_opinions=1778 (valeurs gelées attendues : 569 / 1778)
- **PASS** R1.jeu_scellé_défini — n_available=79, n_selected=50
- **PASS** R1.scellé_intact — sealed_sha256 recalculé = référence
- **PASS** R1.protocole_préenregistré — docs/04-PROTOCOLE.md sha256=9ed00873b737cdc5…
- **PASS** R1.emballage_LICENSE — présent
- **PASS** R1.emballage_CITATION.cff — présent

## R2

- **PASS** R2.audit_zéro_fuite_reexécuté — m15_audit.py rc=0, verdict=PASS, échecs=aucun

## R3

- **FAIL** R3.rapport_m3b — results/m3b_report.json ABSENT — entraînement persona inachevé (sessions Colab côté utilisateur)
- **FAIL** R3.adaptateurs — 0 adaptateurs dans data/m3/adapters (répertoire absent)
- **FAIL** R3.audits_anti_mémorisation — section memorization ABSENTE (section 7bis du notebook)
- **FAIL** R3.personas_complets — personas actifs couverts : — ; manquants : ['JGRoberts', 'CThomas', 'SAAlito', 'SSotomayor', 'EKagan', 'NMGorsuch', 'BMKavanaugh'] ; base-prompt-only (pré-enregistré) : ['ACBarrett', 'KBJackson']

## R4

- **PASS** R4.baselines_condition_D — B4 (barre à battre, niveau vote) = 0.6366
- **PASS** R4.personas_train — 477 lignes train (477 attendues) ; écarts : aucun
- **PASS** R4.casefiles — 519 casefiles (519 attendues : 308 train + 211 test)
- **PASS** R4.textes_v3 — textes distincts v3 = 793 (793 attendus)

## R5

- **PASS** R5.taille_du_scellé — 50 affaires scellées (50 attendues)
- **WARN** R5.vérité_terrain — SCDB join 49/50 ; split maj/min 49/50 ; direction d'affaire 49/50 ; votes par juge 441/441 lignes (avec direction 440) — comptages seuls, contenu non lu ; sans vérité terrain (constaté avant tout envoi au modèle, cause documentée du protocole) : ['No. 18–726.']

## Verdict : **BLOCKED**

Bloqué par : R3.rapport_m3b, R3.adaptateurs, R3.audits_anti_mémorisation, R3.personas_complets.
L'étape 5 (Épreuve Finale) ne peut être exécutée que une fois ces portes fermées — une seule passe, protocole scellé.
