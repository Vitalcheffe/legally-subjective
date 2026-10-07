# D1-bis — verrouillage court des résultats E1 / E2 / E3

**Document de verrouillage éditorial.** Établi le 2026-10-07, après
exécution et publication des résultats (tag `a1-freeze` = commit
`6d713e4`, résultats publiés au commit `68b1a45`, quels qu'ils soient).
Objet : figer ce que les résultats **établissent** et ce qu'ils
**n'établissent pas**, avant la construction des figures et du papier.
Aucune donnée n'est recalculée ; aucun artefact publié n'est modifié.

## 1 · Statut figé

- **E1** (décomposition causale du dial, 3 bras N/P/A, fenêtre
  transparente 211 casefiles, seed 271828) — exécuté selon le plan
  pré-enregistré. Verdict sur les trois prédictions inscrites :
  - (i) défaut conservateur du bras N pour tous les sièges :
    **confirmée** (N = 0,1137 < 0,5 partout) ;
  - (ii) Δ(P−N) positif pour les libéraux : **falsifiée pour Kagan**
    (−0,0616) alors qu'elle tient pour Sotomayor (+0,3887) et Jackson
    (+0,0617) ; le contraste libéraux/conservateurs (moyennes +0,1296
    vs −0,0766) est confirmé ;
  - (iii) Δ(A−P) négatif pour Kagan et Sotomayor : **confirmée**
    (−0,0284 et −0,0142).
- **E2** (distinctivité stylistique, local) — **deux prédictions
  inscrites falsifiées** : classement inversé (Kagan la plus
  distinctive, Thomas la moins) et corrélation distinctivité ↔
  fidélité **négative** (Spearman −0,721 en phase S, −0,607 en phase
  T ; volume : +0,144). Étiquette : exploratoire, falsification
  pré-enregistrée — jamais présentée comme hypothèse post-hoc.
- **E3** (auto-cohérence) — probe **pré-spécifié, exploratoire** :
  sur les 21 affaires où Kagan a signé une opinion majoritaire et
  voté libéral à l'entraînement, le persona vote libéral 3/21
  (14,3 %). Aucun statut confirmatoire ; ne re-touche jamais au test
  primaire M4.

## 2 · Le point de verrouillage : « variance cuBLAS inter-run »

**Constat brut** (régressions de fidélité pré-inscrites dans le kernel
A1) : avec scoring déterministe et entrées identiques, on attendait des
égalités exactes entre le bras A de E1 et la condition B publiée de la
phase T. Observé : **5 égalités exactes sur 7** (CThomas, JGRoberts,
NMGorsuch, SAAlito, SSotomayor) et deux écarts — EKagan (0,3431 vs
0,3333) et BMKavanaugh (0,5343 vs 0,5539) ; le bras N vs la condition A
de phase T diverge également (ex. Roberts 0,5441 vs 0,5147).

**Statut épistémique verrouillé** : la « variance cuBLAS inter-run »
est une **hypothèse diagnostique** — une cause candidate cohérente
avec les écarts observés, **non isolée expérimentalement**. Elle ne
doit être présentée nulle part comme une cause établie.

**Formulation imposée pour le papier** (et les figures) :

> Small inter-run divergences appear between logically identical
> re-executions (5/7 exact matches); their cause is unisolated —
> consistent with, but not demonstrated to be, cuBLAS non-determinism
> on the T4 GPU.

Toute affirmation causale exigerait une expérience dédiée (mêmes
entrées, exécutions répétées, environnement identique), qui n'a pas
été menée et n'est pas prévue avant la soumission.

**Conséquence pour les figures** : les comparaisons inter-bras
(N vs P vs A) utilisent exclusivement les nombres internes d'E1 (un
seul run, seed 271828) ; les nombres de phase T sont cités comme
valeurs publiées, jamais mélangés aux nombres E1 dans un même calcul
ou une même série visuelle.

## 3 · Ce que ce verrouillage ne change pas

Le test primaire M4 (McNemar B vs A sur les affaires scellées,
p = 1,0) reste le chiffre publié — jamais recalculé. Les 50 affaires
scellées restent fermées comme source d'entraînement ou de sélection.
La séparation confirmatoire/exploratoire (E1 confirmatoire dans son
propre cadre ; E2, E3 exploratoires) est inchangée. E4 reste non
lancé : il ne sera exécuté que si une question précise reste réellement
sans réponse après les figures.
