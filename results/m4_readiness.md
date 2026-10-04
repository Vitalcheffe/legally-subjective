# M4 — Porte de pré-vol (pre-flight gate)

**Verdict : FAIL — l'Épreuve Finale est INTERDITE jusqu'à réparation**

Empreinte du scellé : `596ea80ae2478082dca3a4aef85b370f0b30b7f121f5ffb2a59c6778ee652fee`

| Contrôle | État | Détail |
|---|---|---|
| R1.1 | PASS | scellé recalculé à l'identique (596ea80ae2478082dca3…, 50 affaires) |
| R1.2 | PASS | 50 sélectionnées parmi 79 affaires 5-4 |
| R1.3 | PASS | les 50 scellées matchent le corpus (51 entrées — doublons de graphie exclus aussi) |
| R1.4 | PASS | docs/04-PROTOCOLE.md est versionné |
| R1.5 | FAIL | fichiers suivis modifiés au départ : M .github/workflows/audit.yml;  M data/m15_store/clean/audit_leak_journal.json;  M data/m15_store/clean/audit_leak_journal.md |
| R2 | PASS | audit zéro-fuite re-exécuté à froid : 14/14 PASS |
| R3.1 | PASS | artefacts M3 : 518 case files, 477 lignes persona train, 793 textes v3, 9 juges |
| R3.2 | PASS | re-construction déterministe : 537 fichiers, empreintes identiques avant/après |
| R4 | PASS | exclusion du scellé confirmée par le matcher indépendant (859 lignes persona + case files) |
| R5.1 | PASS | vérité terrain disponible (les 50 entrées scellées) : direction 49/50, disposition 49/50, votes par juge 440 |
| R5.2 | PASS | strates pré-enregistrées : 20 futures (OT2020+) / 30 entrelacées (OT2015-2019) — McNemar global + stratifié |
| R6 | PENDING | artefacts M3b absents localement (entraînement Colab en cours) : déposer m3b_adapters_*.zip → adapters/ + m3b_report.json à la racine du repo |
| R7 | PASS | runner M4 présent, AST-valide, gardes (scellé + usage unique) en place |

La chaîne de preuve : protocole versionné → scellé recalculé → audit re-exécuté → reconstruction déterministe → exclusion indépendante → disponibilité de la vérité terrain (jamais ses valeurs) → adaptateurs → runner. L'épreuve s'exécute une seule fois, quel que soit le résultat.
