# M3 — Pré-vol du notebook Colab (exécuté sans GPU, données seules)

Heuristique de tokens : **chars/4** (le tokeniseur
réel tourne dans le notebook ; ici on borne les surprises).

| Persona | Brutes | Gardées (>200 c) | Train | Val | Fenêtre |
| médias out (c) | Instr. >budget | Lignes >MAX_LEN |
|---|---|---|---|---|---|---|---|---|
| BMKavanaugh | 21 | 21 | 17 | 4 | 2019-01-08→2020-07-09 | 28537 | 0 | 16 |
| CThomas | 146 | 146 | 124 | 22 | 2015-12-14→2020-07-09 | 21218 | 0 | 85 |
| EKagan | 50 | 50 | 42 | 8 | 2016-01-20→2020-07-08 | 29186 | 0 | 39 |
| JGRoberts | 43 | 43 | 36 | 7 | 2015-10-19→2020-07-09 | 29403 | 0 | 36 |
| NMGorsuch | 39 | 39 | 33 | 6 | 2018-01-22→2020-07-06 | 30738 | 0 | 32 |
| SAAlito | 83 | 83 | 70 | 13 | 2016-01-12→2020-07-09 | 38073 | 0 | 59 |
| SSotomayor | 95 | 95 | 80 | 15 | 2016-01-12→2020-07-08 | 24617 | 0 | 62 |

- Personas **actives** (7) : BMKavanaugh, CThomas, EKagan, JGRoberts, NMGorsuch, SAAlito, SSotomayor
- Personas **sautées** (< 8 lignes) : ACBarrett (0 lignes), KBJackson (0 lignes)

## Lecture

- « Instr. >budget » : lignes dont l'instruction dépasse le budget
  INSTR_KEEP = 1024 tokens en heuristique — le notebook
  la tronque **par la tête** (la question présentée vit en queue) ;
  c'est attendu, pas un défaut.
- « Lignes >MAX_LEN » : lignes dont instruction+output débordent
  MAX_LEN = 4096 tokens en heuristique — le notebook réduit
  la sortie par la queue ; les personas à forte proportion perdent
  du signal d'entraînement (à comparer avec le tokeniseur réel).

---

*Généré par `scripts/m3_preflight.py` — stdlib seule, aucun réseau.*
