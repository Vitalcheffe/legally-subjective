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

**Métrique de succès** : accuracy de A vs accuracy de B. Si B bat A de plus
de 5 points, l'apprentissage fonctionne. Si B ne bat pas A, on arrête et on
documente — résultat négatif honnête, et les résultats négatifs publient
aussi.

**Gate de sortie** : accuracies de A et B calculées sur les 400 affaires,
matrice de confusion produite, biais par type de crime mesuré.

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
Pour chaque juge, fine-tuning d'un modèle séparé sur SES affaires à lui.
Quand ce juge voit un crime de type X avec des circonstances Y, il décide Z.
Méthode : QLoRA, un fine-tuning par juge ; split 80/20 ; si le modèle prédit
les 20 % de test au-dessus du hasard, on a capturé quelque chose du cerveau
du juge. Plus l'accuracy est haute, plus le profil est précis. Étape la plus
coûteuse en calcul — 9 modèles pour les Neuf, potentiellement des centaines
pour les cours d'appel. Le temps n'est pas un problème : on le fait.

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

## ÉTAGE 4 — LE MODULE INFINI : le système qui découvre ses propres variables

Le composant darwinien. Population initiale de 200 cellules ; chaque cellule
est une petite fonction qui lit les données et produit un score (mesure une
corrélation potentielle entre un feature et la décision). À chaque
génération : la cellule survit et se reproduit (variantes mutées) si son
feature améliore la prédiction du verdict ; sinon elle meurt. On garde les
200 meilleures.

Le système ne sait pas à l'avance qu'il doit chercher « le mot tragic » ou
« l'heure de l'audience ». Il découvre seul les variables qui prédisent les
décisions — y compris des variables absurdes, qui meurent parce qu'elles ne
prédisent rien.

**Gate de l'étage 4** : au moins 3 cellules survivantes traduisibles en
phrases humaines compréhensibles et non triviales. Si le système ne découvre
que des évidences (« les juges condamnent plus quand il y a des preuves »),
échec. Des patterns surprenants, succès.

---

## ÉTAGE 5 — LA VALIDATION CROISÉE HUMAINE

Le juriste humain (l'ami en droit) reçoit les 400 affaires du set de test,
sans les verdicts. Il prédit. On compare : le juge réel, le Modèle A, le
Modèle B, le per-judge, et le juriste.

Le triangle qui rend le projet inattaquable : si l'IA bat le juriste —
résultat fort. Si le juriste bat l'IA — résultat fort aussi (l'humain
apporte ce que la machine ne capture pas). Si les deux échouent sur les
mêmes affaires — preuve que certaines affaires sont indécidables par
nature ; peut-être le résultat le plus intéressant de tous.

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
prédiction pure est le per-judge fine-tuning (Couche 3). Le meilleur moyen
pour le produit public est le casier + similarité (Méthode 2 de l'Étage 3).
On fait les deux : le fine-tuning pour la recherche et le papier, le casier
pour le site public. Le casier ne ment jamais ; le fine-tuning est marqué
« simulation » dans le disclaimer.

---

## Les 8 phases d'exécution

| Phase | Contenu | Dépend de | Gate de sortie |
|---|---|---|---|
| 1 | Dataset complet + Modèle A vs B | — | accuracies A/B sur 400 affaires, matrices de confusion, biais par crime |
| 2 | Profilage des 9 juges (statistique + textuel) | 1 | 4 couches amorcées, profils publiés |
| 3 | Per-judge fine-tuning (9 modèles SCOTUS) | 2 | chaque modèle bat le hasard sur ses 20 % de test |
| 4 | Similarité sémantique (le casier public) | 1 | embeddings + retrieval opérationnels |
| 5 | Simulation croisée (casier + fine-tuning) | 3, 4 | les deux méthodes livrées et disclaimées |
| 6 | Module infini darwinien | 1 | ≥ 3 cellules survivantes non triviales et traduisibles |
| 7 | Validation humaine (le juriste) | 1 | triangle comparé : réel / A / B / per-judge / humain |
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
QLoRA (rank 16, lr 2e-4, 3 époques), évaluation sur les 400 affaires,
matrices de confusion, biais par catégorie de crime, gate ±5 points,
rapport JSON. Prêt pour Colab T4.

**Reste (Phase 1).**
1. Exécuter le notebook sur Colab T4 (compte utilisateur — le sandbox n'a
   pas de GPU) et rapporter `results_stage1.json`.
2. Décider la gate : B − A > 5 points → Étage 2 fondé ; sinon documenter le
   résultat négatif.
3. (Optionnel) Étendre le corpus au-delà de nyappdiv pour la robustesse.

**Phases 2 à 8** : non commencées — chacune dépend de la gate précédente.

---

*Le Projet Manhattan du Droit ne se finit pas en une nuit, mais chaque nuit
le rapproche.*
