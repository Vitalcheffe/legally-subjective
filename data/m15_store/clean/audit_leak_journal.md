# Journal d'audit zéro-fuite — M1.5.4

Généré : 2026-08-30T08:31:01.846805+00:00  
Verdict : **PASS** (14 contrôles, 0 échec(s))

| Contrôle | Verdict | Détail |
|---|---|---|
| `A4.seal_integrity` | PASS | sealed_sha256 recomputed: match |
| `A1.sealed_not_in_casefiles` | PASS | 519 casefiles, scellés trouvés: aucun |
| `A2.sealed_not_in_personas` | PASS | 477 train rows, scellés: aucun |
| `A3.sealed_not_in_test_votes` | PASS | 382 test votes, scellés: aucun |
| `B1.train_before_cutoff` | PASS | rows décidées après 2020-10-01: aucun |
| `B2.segments_date_guard` | PASS | segments sans date: 0, décidés après cutoff: 0 |
| `B3.test_is_ot2020plus` | PASS | votes test hors fenêtre: aucun |
| `C1.v3_no_duplicates` | PASS | 793 textes v3, doublons exacts: 0 |
| `C2.dedup_map_covers_corpus` | PASS | 1778 ids mappés, corpus 1778, cibles absentes de v3: 0 |
| `C3.no_duplicate_outputs_within_persona` | PASS | doublons intra-persona: aucun |
| `D1.rows_in_v3_and_long_enough` | PASS | rows invalides: aucun |
| `D2.signatures_match_persona` | PASS | erreurs d'attribution: aucun |
| `E1.casefiles_pre_decision` | PASS | clés interdites: aucune (519 fichiers) |
| `F1.chain_hashes` | PASS | 8 artefacts hachés (voir journal) |

## Chaîne (sha256)

| Artefact | sha256 (12) | octets |
|---|---|---|
| corpus_stats | `ad6081e71c7e` | 4,712 |
| texts_v2 | `5d5f4c6d24a1` | 18,701,575 |
| texts_v3 | `cedf561a6fc0` | 7,600,365 |
| dedup_map | `5c6fabbd00bd` | 45,040 |
| clean_report | `312650bd4d8b` | 5,261 |
| authorship | `d615859f8330` | 292,473 |
| segments | `81dca2f8ad9a` | 40,035,472 |
| manifest | `85a7963455c2` | 2,410 |
