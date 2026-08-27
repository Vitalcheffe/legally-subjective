# BACKLOG — Legally Subjective
*La queue humaine. Le moteur (scripts/engine.py) exécute les tâches [engine] de QUEUE.json ; les tâches [agent] sont produites par l'agent principal, sous autorité de BOSS.md.*

## Roadmap (9 semaines)

| Semaine | Objectif | Tâches liées |
|---|---|---|
| S1 | Fondations : monorepo, tokens, squelettes 4 routes | E-001, E-002, A-001, A-004, A-005 |
| S2–S3 | Ingestion CourtListener réelle — les Neuf | A-006 |
| S4–S6 | Kernel : les 6 axes LS-1.0 + glyphe déterministe | A-004 (suite) |
| S7–S8 | The Bench + In re + v. + print CSS | A-002, A-005 (suite) |
| S9 | Daubert + lancement The Nine + In re You | A-003 |

## En cours
- [x] E-001 · E-002 · E-003 — queue engine
- [ ] A-001 Design System pixel — **prochaine tâche agent**
- [ ] A-002 Spec The Bench
- [ ] A-003 Spec In re You
- [ ] A-004 Kernel Python
- [ ] A-005 Web statique
- [ ] A-006 Ingestion CourtListener

## Règles du backlog
1. Rien n'est FILED sans validation Boss (« Ok. Go. »).
2. Zéro donnée fabriquée — le GUARD du moteur scanne en permanence.
3. Les dossiers publiés sont immuables ; toute correction = révision nouvelle.


## Sprint 2026-08-27 — LE RECORD EST OUVERT (terminé)
- [x] A-006 Ingestion réelle : CourtListener (688 clusters, 587 opinions signées) + Oyez (329 affaires, votes par juge) — cache sourcé 422 fichiers
- [x] A-005 Les 5 routes-outils : /judge/[id] · /court/[id] · /compare/[a]/[b] · /docket/[id] · /api/dockets — 7/7 URL LIVE, télémétrie WARM
- [x] LS-1.0 gelé au premier dépôt : 9 dockets FILED, déterminisme bit-identique, §3.5bis banc réduit, proxies v1 ratifiés

## Prochain sprint
- [ ] A-007 Axe Orality — transcriptions d'audience (Oyez sections audio)
- [ ] A-008 Axe Reversal — traitement des citations (ingestion profonde CL)
- [ ] A-009 ONE DOOR DOWN par cour — cours d'appel, banc 30+, percentiles pleine granularité
- [ ] A-003 Spec In re You (le test miroir)
- [ ] A-004 Modules kernel restants + packaging
