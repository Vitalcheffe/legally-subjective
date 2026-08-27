# BACKLOG — Legally Subjective
*La queue humaine. Le moteur (scripts/engine.py) exécute les tâches [engine] de QUEUE.json ; les tâches [agent] sont produites par l'agent principal, sous autorité de BOSS.md.*

## Roadmap — MANHATTAN (remplace le plan des 9 semaines, 2026-08-27)

Le chemin complet est persisté dans [archives/manhattan-roadmap.md](archives/manhattan-roadmap.md) : ambition = **Projet Manhattan du Droit**, ratio qualité/temps = **infini**. Huit phases, chacune avec sa gate de sortie mesurable.

| Phase | Objectif | Gate | État |
|---|---|---|---|
| 1 | Dataset complet + Modèle A vs B | accuracies A/B sur 400 affaires, confusion, biais par crime | **EN COURS** — collecteur 1 677 cas ✓, golden 5/5 ✓, split 600/400 ✓, notebook Colab ✓ ; reste : exécuter sur T4 |
| 2 | Profilage des 9 juges (statistique + textuel) | 4 couches amorcées | — |
| 3 | Per-judge fine-tuning (9 modèles) | chaque modèle bat le hasard (80/20) | — |
| 4 | Similarité sémantique — le casier public | embeddings + retrieval | — |
| 5 | Simulation croisée (casier + fine-tuning) | les 2 méthodes disclaimées | — |
| 6 | Module infini darwinien | ≥ 3 cellules non triviales | — |
| 7 | Validation humaine (le juriste) | triangle réel/A/B/per-judge/humain | — |
| 8 | Publication + déploiement | arXiv + site + vidéo + notebook | — |

## Règles du backlog
1. Rien n'est FILED sans validation Boss (« Ok. Go. »).
2. Zéro donnée fabriquée — le GUARD du moteur scanne en permanence.
3. Les dossiers publiés sont immuables ; toute correction = révision nouvelle.
4. Une gate manquée n'est pas un échec à cacher : résultat négatif = résultat documenté.

## Historique (sprints clos)
- **Sprint 2026-08-27 — LE RECORD EST OUVERT** : A-006 ingestion réelle (688 clusters CL, 329 cas Oyez) · A-005 les routes-outils · LS-1.0 gelé, 9 dockets FILED
- **Sprint 2026-08-27 — LA DEVANTURE** : THE DRAW (la roulette des juges) + THE QUESTIONS + THE SCIENCE (LS-R-001, modèle entraîné pour de vrai, 349 pages statiques)
- **Sprint 2026-08-27 — MANHATTAN amorcé** : roadmap fondatrice persistée, corpus criminel restauré et étendu (1 677 cas), dataset A/B 600/400 construit (zéro fuite vérifiée), notebook Colab livré

## Prochain sprint
- [ ] P1-exécution : lancer `phase1/colab/manhattan_stage1_ab.ipynb` sur Colab T4, rapporter `results_stage1.json`
- [ ] P1-décision : gate B − A > 5 points → ouvrir Phase 2 ; sinon documenter le négatif
- [ ] A-007 Axe Orality — transcriptions d'audience (Oyez)
- [ ] A-008 Axe Reversal — traitement des citations
- [ ] A-009 ONE DOOR DOWN par cour — cours d'appel (raccord Phase 4 : le casier)
