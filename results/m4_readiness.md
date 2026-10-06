# M4 — Porte de pré-vol (pre-flight gate)

**Verdict : READY — l'Épreuve Finale peut être exécutée (une fois)**

Empreinte du scellé : `596ea80ae2478082dca3a4aef85b370f0b30b7f121f5ffb2a59c6778ee652fee`

| Contrôle | État | Détail |
|---|---|---|
| R1.1 | PASS | scellé recalculé à l'identique (596ea80ae2478082dca3…, 50 affaires) |
| R1.2 | PASS | 50 sélectionnées parmi 79 affaires 5-4 |
| R1.3 | PASS | les 50 scellées matchent le corpus (51 entrées — doublons de graphie exclus aussi) |
| R1.4 | PASS | docs/04-PROTOCOLE.md est versionné |
| R1.5 | PASS | arbre git propre (fichiers suivis ; HEAD edf1359) |
| R2 | PASS | audit zéro-fuite re-exécuté à froid : 14/14 PASS |
| R3.1 | PASS | artefacts M3 : 518 case files, 477 lignes persona train, 793 textes v3, 9 juges |
| R3.2 | PASS | re-construction déterministe : 537 fichiers, empreintes identiques avant/après |
| R4 | PASS | exclusion du scellé confirmée par le matcher indépendant (859 lignes persona + case files) |
| R5.1 | PASS | vérité terrain disponible (les 50 entrées scellées) : direction 49/50, disposition 49/50, votes par juge 440 |
| R5.2 | PASS | strates pré-enregistrées : 20 futures (OT2020+) / 30 entrelacées (OT2015-2019) — McNemar global + stratifié |
| R6 | PASS | M3b présent : rapport (Qwen/Qwen2.5-3B-Instruct) + 7 adaptateurs |
| R7 | PASS | runner M4 présent, AST-valide, gardes (scellé + usage unique) en place |

La chaîne de preuve : protocole versionné → scellé recalculé → audit re-exécuté → reconstruction déterministe → exclusion indépendante → disponibilité de la vérité terrain (jamais ses valeurs) → adaptateurs → runner. L'épreuve s'exécute une seule fois, quel que soit le résultat.
