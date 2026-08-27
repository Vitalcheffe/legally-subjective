# MANHATTAN — Le Projet Manhattan du Droit

**Roadmap fondatrice. Persisté le 2026-08-27 d'après la directive du fondateur.**

L'ambition est explicite : le **Projet Manhattan du Droit**. Du premier octet
de donnée publique au système final — prédiction, profilage par juge,
simulation croisée, découverte automatique de variables, validation humaine,
publication. Le **ratio qualité/temps est infini** : on vise 100 %, et si une
phase prend trois mois pour gagner 1 % de précision, on prend les trois mois.

Loi constitutionnelle inchangée : **zéro fabrication**. Chaque chiffre trace
jusqu'à une URI publique. Les données manquantes sont rendues comme
manquantes. Les résultats négatifs sont des résultats.

---

## L'arbre des dépendances

```
Étage 1 (A vs B) → prouve que l'IA prédit
    ↓
Étage 2 (profilage) → extrait le cerveau de chaque juge
    ↓
Étage 3 (croisé) → simule "un autre juge"
    ↓ (en parallèle)
Étage 4 (infini) → découvre des variables non codées
    ↓
Étage 5 (validation humaine) → rend le projet inattaquable
    ↓
Étage 6 (publication) → arXiv + site + vidéo + notebook
```

On finit l'Étage 1 d'abord. Pourquoi : la comparaison Modèle A (vierge) vs
Modèle B (qui apprend) est le socle. Elle prouve deux choses — l'IA peut-elle
prédire un verdict, et l'apprentissage de cas passés améliore-t-il la
prédiction ? Sans cette preuve, tout ce qui suit (profilage, simulation
croisée, module infini) repose sur du sable. On construit l'étage 1 avant
l'étage 2.

---

## ÉTAGE 1 — LE SOCLE : Modèle A vs Modèle B

**Le dataset** : 600 affaires criminelles pour l'entraînement, 400 pour le
test. Split stratifié (type de crime × verdict × année) pour que les deux
ensembles portent la même distribution.

**Modèle A, le vierge.** Llama 3 8B, NON entraîné. Pour chaque affaire du set
de test, on lui donne les faits et on demande un verdict. 400 prédictions
indépendantes. Le modèle ne se souvient de rien entre deux affaires. C'est le
juge qui arrive le premier jour : il a lu la loi mais n'a jamais jugé.

**Modèle B, qui apprend.** Même modèle de base, fine-tuné sur les 600
affaires avec leurs vrais verdicts. Méthode : QLoRA, rank 16, learning rate
2e-4, 3 époques. Le modèle voit les faits ET le verdict réel de chaque
affaire d'entraînement, et ajuste ses poids pour mieux prédire. Puis test sur
les 400 affaires jamais vues.

**Métrique de succès — règle pré-enregistrée (amendée le 2026-08-27 avant
tout lancement GPU, sur ordre de l'audit interne LS-AUDIT-001, injonction 2
— après le run, la même modification s'appellerait une fraude de
convenance)**. L'expérience oppose TROIS joueurs : le Modèle A (vierge), le
Modèle B (fine-tuné), et la ligne de base-majoritaire (l'idiot utile qui
répond toujours « confirmé » — 79,75 % d'accuracy sur ce corpus : ignorer
ce troisième joueur, c'est organiser un match à deux en prétendant que le
troisième ne gagne pas sans réfléchir). Les deux modèles jugent les MÊMES
400 affaires : la différence B − A est donc testée par **McNemar exact
apparié**, avec **intervalle à 95 %** sur la différence. La gate n'est
franchie que si les TROIS conditions tiennent :

1. `accuracy(B) − accuracy(A) > 5 points` ;
2. `p(McNemar exact) < 0,05` ;
3. `accuracy(B) > accuracy(ligne de base)`.

Pourquoi la condition 3 : à n = 400 et un taux de base de 80 %, un écart
réel de 5 points ne produit un z observé que de ~1,77 — la gate, à son
propre seuil, ne détecte l'effet que 42 fois sur 100 quand il est réel.
Le test apparié regagne la puissance perdue ; la ligne de base empêche de
célébrer une victoire sur un adversaire plus faible que l'idiot. Si les
trois conditions ne tiennent pas — y compris partiellement — le résultat
est un **résultat négatif honnête** : documenté, publié, et l'étage 2 n'est
pas fondé. Les résultats négatifs publient aussi.

**Gate de sortie** : accuracies de A, B et de la ligne de base-majoritaire
sur les 400 affaires, McNemar exact apparié + IC 95 % sur B − A, matrice de
confusion produite, biais par type de crime mesuré — règle complète
pré-enregistrée ci-dessus, exécutable par le notebook Colab (amendé).

---

## ÉTAGE 2 — LE PROFILAGE : extraire le cerveau de chaque juge

Quatre couches d'extraction, de la plus superficielle à la plus profonde.

### Couche 1 — le profil statistique
Pour chaque juge ayant au moins 30 affaires : taux de condamnation,
sévérité moyenne, écart-type de sévérité (l'imprévisibilité), taux de
dissidence, taux d'inversion. Ces chiffres existent déjà dans le site
(actuellement pour les Neuf de la Cour suprême — les six axes LS-1.0).
Surface du cerveau du juge, mesurable en cinq minutes.

### Couche 2 — le profil textuel
Le LANGAGE du juge, pas seulement ses décisions. Longueur moyenne des
opinions, vocabulaire dominant, formules signatures (« I write separately
to note… »), ton émotionnel (colère, prudence, ironie, formalité).
Méthode : texte intégral des opinions depuis CourtListener ; features =
TF-IDF sur bigrammes, distribution de longueur de phrases, densité de
citations (celui qui cite beaucoup est un juge de précédent, celui qui cite
peu est un juge de principe), fréquence des mots émotionnels (« tragic »,
« devastating », « egregious » vs « accordingly », « therefore »,
« pursuant to »). Résultat : un vecteur de personnalité textuelle par juge.

### Couche 3 — le profil de décision
Pour chaque juge, capturer SA logique de décision. **Décision de conception
(amendée le 2026-08-27, LS-AUDIT-001 injonction 9) : UN SEUL modèle
conditionné au juge, pas neuf fine-tunages séparés.** L'identité du juge
entre dans le prompt comme un jeton ; le modèle apprend UNE fois la loi
commune du corpus, puis les décalages individuels. Pourquoi : neuf
fine-tunages séparés réapprennent neuf fois les mêmes régularités du
corpus et étouffent le signal discriminant entre juges — qui ne vit que
dans la fraction d'affaires disputées. Un modèle conditionné apprend le
juge marginal avec les mêmes données. Méthode : QLoRA, jeton de juge dans
le prompt, split 80/20 stratifié PAR JUGE ; si le modèle prédit mieux les
20 % de test qu'un modèle non conditionné au hasard, on a capturé quelque
chose du cerveau du juge. Le temps n'est pas un problème : on le fait.

### Couche 4 — le profil comportemental profond
Ce que le juge FAIT dans le temps. Évolution du taux de condamnation sur
10 ans, clémence/sévérité avec l'âge, effet de composition du panel (le
juge A est-il plus sévère quand le juge B est dans la salle ?), effets
d'audience (plus sévère le matin, plus clément après le déjeuner — documenté
dans la littérature, études israéliennes sur l'heure du repas).
Méthode : analyse temporelle, régression sur variables contextuelles
(heure, jour, panel, ancienneté), détection de points de rupture (le juge
a-t-il changé après une affaire marquante ?).

---

## ÉTAGE 3 — LA SIMULATION CROISÉE : « Seriez-vous encore libre ? »

Deux méthodes.

**Méthode 1 (la tentation) — remplacer le juge dans le prompt.** Donner
l'affaire du juge Y au modèle fine-tuné du juge X. Simulation croisée
directe. Problème : le modèle X sort de sa distribution d'entraînement, il
peut halluciner. Prédiction intéressante, validité limitée.

**Méthode 2 (la méthode honnête, celle de Boss) — le casier, pas la
prédiction.** Chercher les N affaires les plus similaires dans le casier du
juge X. Le système dit : « Le juge X n'a jamais vu cette affaire précise.
Mais il a vu 43 affaires similaires. Dans 72 % de ces 43 affaires, il a
condamné. » Récupération, pas prédiction — inattaquable : on montre ce que
le juge a VRAIMENT fait, pas ce qu'une IA imagine.

Technique de similarité : embeddings sémantiques (sentence-transformers),
distance cosinus entre le vecteur des faits de l'affaire Y et les vecteurs
des affaires du juge X, récupération des N plus proches.

« Seriez-vous encore libre ? » devient : dans les N affaires les plus
similaires à la vôtre, le juge X a condamné dans X % des cas, le juge Y
(vous l'avez eu) dans Y % des cas. L'écart entre X et Y, c'est votre
roulette.

---

## ÉTAGE 4 — LE MODULE INFINI : le générateur d'hypothèses (protocole verrouillé avant la première ligne de code)

**Amendement LS-AUDIT-001 injonction 8, enregistré le 2026-08-27, AVANT
toute implémentation.** Le composant darwinien — population initiale de
200 cellules ; chaque cellule est une petite fonction qui lit les données
et produit un score — est requalifié officiellement : **générateur
d'hypothèses**, jamais « découvreur de vérités ». Sans protocole, ce module
est un générateur garanti de faux positifs : deux cents prédicteurs soumis
à sélection multiple produisent des survivants même sur des données
purement aléatoires — c'est la définition même de l'évolution. Le
protocole, non négociable :

1. **Jeu de test scellé.** La fitness de chaque cellule est calculée
   EXCLUSIVEMENT sur un jeu de test tenu à l'écart de la naissance, de la
   mutation et de toute décision de sélection. Le jeu est évalué UNE fois,
   à la fin — jamais en boucle.
2. **Contrôle du taux de faux découvertes.** Le seuil de survie est
calibré
   pour 200 prédicteurs concurrents (Bonferroni ou Benjamini-Hochberg,
   déclaré avant le run). Une cellule qui survit au contrôle n'a fait que
   survivre au contrôle.
3. **Réplication sur une deuxième fenêtre.** Toute cellule survivante doit
   reproduire son signal sur une seconde fenêtre de données, disjointe de
   la première. Pas de réplication, pas de publication.
4. **La traduisibilité n'est pas une preuve.** L'humain est une machine à
   narrativiser le bruit (apophénie). La gate « traduisible en phrase
   humaine » mesure la rhétorique, pas la réalité — elle est conservée
   comme exigence de COMMUNICATION, retirée comme critère de VÉRITÉ.

**Gate de l'étage 4 (amendée)** : au moins 3 cellules qui survivent au jeu
scellé, au contrôle des faux découvertes ET à la réplication — et
l'article les publie comme **hypothèses confirmées à tester**, jamais
comme résultats. Si le système ne découvre que des évidences (« les juges
condamnent plus quand il y a des preuves »), échec. Des patterns
surprenants ET répliqués, succès.

---

## ÉTAGE 5 — LE PILOTE DE VALIDATION HUMAINE (requalifié par LS-AUDIT-001 injonction 10)

**Amendement du 2026-08-27 : l'étage s'appelle « pilote », pas « validation »
— jusqu'à ce que son protocole complet soit écrit.** Avec un seul
évaluateur, on mesure autant la personne que la méthode : publier cela
sous le nom de « validation croisée humaine » offrirait à la critique
exactement ce que le projet prétend fermer. Le triangle reste l'objectif :
le juriste humain (l'ami en droit) reçoit les 400 affaires du set de test,
sans les verdicts ; il prédit ; on compare le juge réel, le Modèle A, le
Modèle B, le modèle conditionné au juge, et le juriste. Les trois issues
restent précieuses : l'IA bat le juriste — résultat fort ; le juriste bat
l'IA — résultat fort aussi ; les deux échouent sur les mêmes affaires —
peut-être le résultat le plus intéressant : certaines affaires sont
indécidables par nature.

**Conditions de requalification en « validation »** (toutes obligatoires) :
- aveuglement décrit par écrit (ce que l'évaluateur voit, ce qu'il ne voit
  pas, dans quelle ordre) ;
- au moins deux évaluateurs indépendants ;
- accord inter-annotateurs rapporté (kappa de Cohen ou équivalent) ;
- puissance calculée a priori : combien d'affaires faut-il pour distinguer
  une différence de 5 points entre le juriste et le modèle ;
- critères d'inclusion des affaires fixés avant la distribution.

Tant que ces conditions ne sont pas réunies, tout livrable de cet étage
s'appelle **un pilote** — et un pilote publiable comme tel.

---

## ÉTAGE 6 — LA PUBLICATION ET LE DÉPLOIEMENT

Le papier arXiv de 8 pages. Le site avec The Wheel et One Door Down. La
vidéo de 90 secondes. Le notebook Colab reproductible. Le module infini en
démonstration live.

---

## Questions tranchées par le fondateur

**« Doit-on la tester sur toutes les affaires de X juges jusqu'à ce qu'elle
dise la même chose à chaque fois ? »** — Non. On ne cherche pas la
convergence vers une réponse unique, on cherche la CONFIANCE dans la
prédiction. Chaque prédiction porte un score de confiance ; un score bas
signifie zone grise — on mesure l'incertitude et on la rapporte honnêtement.
Le test de stabilité n'est pas « le modèle dit-il la même chose à chaque
fois » mais « le modèle, entraîné sur 80 % des affaires du juge, prédit-il
correctement les 20 % qu'il n'a pas vues » — le test standard de
généralisation, la seule métrique qui compte.

**« Est-ce le meilleur moyen ou t'as mieux ? »** — Le meilleur moyen pour la
prédiction pure est le modèle conditionné au juge (Couche 3, un seul
fine-tuning avec jeton d'identité — amendé inj. 9). Le meilleur moyen
pour le produit public est le casier + similarité (Méthode 2 de l'Étage 3).
On fait les deux : le modèle conditionné pour la recherche et le papier,
le casier pour le site public. Le casier ne ment jamais ; le modèle
conditionné est marqué « simulation » dans le disclaimer.

---

## Les 8 phases d'exécution

| Phase | Contenu | Dépend de | Gate de sortie |
|---|---|---|---|
| 1 | Dataset complet + Modèle A vs B + ligne de base (règle pré-enregistrée — inj. 2) | — | A, B, base-majoritaire, McNemar exact + IC 95 % sur B − A, matrices de confusion, biais par crime |
| 2 | Profilage des 9 juges (statistique + textuel) | 1 | 4 couches amorcées, profils publiés |
| 3 | Modèle conditionné au juge (UN seul, jeton d'identité — inj. 9) | 2 | le modèle conditionné bat le hasard ET le modèle non conditionné sur ses 20 % de test |
| 4 | Similarité sémantique (le casier public) | 1 | embeddings + retrieval opérationnels |
| 5 | Simulation croisée (casier + fine-tuning) | 3, 4 | les deux méthodes livrées et disclaimées |
| 6 | Module infini darwinien (générateur d'hypothèses — protocole inj. 8) | 1 | ≥ 3 cellules survivant au jeu scellé, au FDR et à la réplication |
| 7 | Pilote de validation humaine (requalifiable — inj. 10) | 1 | triangle comparé : réel / A / B / conditionné / humain |
| 8 | Publication + déploiement | toutes | arXiv + site + vidéo + notebook |

---

## État d'exécution — photographie du 2026-08-27

### Phase 1 (EN COURS)

**Fait — le collecteur existe et a tourné.**
`phase1/scripts/fetch_courtlistener.py` : collecte CourtListener v4 + slip
opinions officielles NY, gate criminelle, dédoublonnage par cluster,
checkpoint de reprise, FETCH_LOG de provenance (chaque requête HTTP
journalisée). État : **1 677 affaires criminelles réelles collectées**
(1 387 restaurées de la lignée du 2026-08-26 + 290 collectées ce jour sur
les fenêtres 2024-2025), documents HTML sources archivés avec sha256.

**Fait — le preprocessing existe et est vérifié.**
`phase1/scripts/preprocess.py` (pipeline blocs + kernel) : extraction
déterministe (panel, disposition, charge, juges du procès, récit des
faits), zéro LLM requis. **Test de régression doré repassé ce jour :
concordance 5/5** — l'extraction reproduit exactement les 5 affaires
vérifiées à la main (commit R10 de la lignée d'origine).

**Fait — le dataset A/B est construit.**
`phase1/dataset/` : **train 600 / test 400**, split stratifié
(catégorie de crime × verdict × fenêtre), seed 20260827, reproductible.
Sanitisation documentée (règles R1-R5) : coupe du décret (« Ordered that »),
retrait du panel (bloc d'en-tête + ligne de concurrence — 588/600 cas sans
aucun nom de panel), retrait des verdicts en ligne, **gate anti-fuite :
0 occurrence des mots de verdict dans les 1 000 textes livrés** (vérifié),
longueur minimale 200 caractères. Rapport complet :
`phase1/dataset/split_report.json`.

**Fait — le notebook d'entraînement existe.**
`phase1/colab/manhattan_stage1_ab.ipynb` : Modèle A zero-shot vs Modèle B
QLoRA (rank 16, lr 2e-4, 3 époques) vs ligne de base-majoritaire (troisième
bras — inj. 2), évaluation sur les 400 affaires, McNemar exact apparié + IC
95 % sur B − A, matrices de confusion, biais par catégorie de crime, gate
pré-enregistrée à trois conditions, rapport JSON. Prêt pour Colab T4.

**Reste (Phase 1).**
1. Exécuter le notebook sur Colab T4 (compte utilisateur — le sandbox n'a
   pas de GPU) et rapporter `results_stage1.json`. La règle de décision à
   trois conditions est pré-enregistrée ci-dessus ET dans le notebook :
   le run ne pourra plus la réécrire.
2. Lire la gate telle qu'elle est écrite : B − A > 5 points ET McNemar
   p < 0,05 ET B > ligne de base. Toute autre issue se documente comme
   résultat négatif — sans réinterprétation.
3. (Optionnel) Étendre le corpus au-delà de nyappdiv pour la robustesse.

**Amendements de conception enregistrés ce jour (LS-AUDIT-001)** : gate de
l'étage 1 pré-enregistrée à trois conditions (inj. 2) ; un seul modèle
conditionné au juge pour l'étage 2-couche 3 (inj. 9) ; le module darwinien
requalifié générateur d'hypothèses avec protocole scellé (inj. 8) ;
l'étage 5 requalifié pilote jusqu'à protocole complet (inj. 10).

**Phases 2 à 8** : non commencées — chacune dépend de la gate précédente.

---

*Le Projet Manhattan du Droit ne se finit pas en une nuit, mais chaque nuit
le rapproche.*
