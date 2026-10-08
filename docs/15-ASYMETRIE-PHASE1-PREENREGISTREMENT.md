# Asymétrie conservateur/libéral — phase 0 (analyse) et phase 1 (plan pré-enregistré)

**Document compagnon du figage** (`m4_resultats_et_interpretations_figes.md`,
enseignement E4). Établi le 2026-10-07.

**Mandat** (propriétaire) : analyser l'asymétrie conservateur/libéral
**hors scellé**, sans toucher au test primaire (McNemar B vs A, affaires,
reste le chiffre publié — jamais recalculé pour de nouveaux claims).

**Garde-fous respectés** :
- La phase 0 n'utilise QUE (i) les prédictions M4 **publiées** (commit
  `f6145a5`), (ii) le rapport de phase T — fenêtre **transparente**
  OT2020+ répétée, scellées exclues —, (iii) les corpus d'entraînement
  publics (personas v3, pré-garde 2020-10). Aucune vérité terrain
  scellée n'est jointe à une analyse non couverte par la publication.
- Tout ce qui suit la phase S est **exploratoire post-hoc** (règle 15 du
  protocole) ; tout ce qui suit la phase T est analyse secondaire sur
  fenêtre transparente. Aucun résultat ci-dessous n'est confirmatoire.
- Aucun modèle n'est ré-entraîné ; aucune nouvelle inférence n'est
  exécutée en phase 0 (GPU zéro).

---

## 1 · Phase 0 — le dial idéologique comprimé (constat central)

### 1.1 Le tableau par siège (phase S, 50 scellées, publié)

| Siège | Adaptateur | n votes | B_acc | B vote libéral **prédit** | vote libéral **réel** | D_acc | p_libéral moyen B |
|---|---|---|---|---|---|---|---|
| CThomas | oui (146 lignes) | 49 | 0,8367 | **0,0 %** | 16,3 % | 0,8367 | 0,163 |
| SAAlito | oui (83) | 49 | 0,8367 | **0,0 %** | 16,3 % | 0,8367 | — |
| BMKavanaugh | oui (21) | 39 | 0,7436 | 10,3 % | 30,8 % | 0,6923 | — |
| ACBarrett | **non** (prompt) | 20 | 0,7500 | 15,0 % | 20,0 % | — | — |
| NMGorsuch | oui (39) | 48 | 0,6875 | 4,2 % | 35,4 % | 0,6458 | — |
| JGRoberts | oui (43) | 49 | 0,6327 | **0,0 %** | 36,7 % | 0,6327 | — |
| KBJackson | **non** (prompt) | 9 | 0,4444 | **44,4 %** | 77,8 % | — | 0,361 |
| SSotomayor | oui (95) | 49 | 0,2449 | 18,4 % | **85,7 %** | **0,8571** | 0,392 |
| EKagan | oui (50) | 49 | 0,2041 | **4,1 %** | **83,7 %** | **0,8367** | 0,320 |

Le fait central n'est pas « libéraux ratés » : c'est que **la colonne
des votes libéraux prédits est quasi vide pour tout le monde** (0-18 %)
pendant que la colonne réelle s'étale de 16 % à 86 %. Les personas —
libéraux compris — votent « conservateur » presque toujours. Le persona
de Kagan vote libéral à 4,1 % quand la Kagan réelle vote libéral à
83,7 % ; le persona de Thomas vote libéral à 0 % quand le Thomas réel
vote libéral à 16,3 %. **Le persona n'a pas appris la position
politique du juge : il a appris (au mieux) une intensité, et son argmax
est bloqué sous 0,5 pour les neuf sièges.**

La colonne des probabilités moyennes (0,16-0,39) précise le mécanisme :
ce n'est pas un effondrement en constante, c'est un **dial comprimé**.
L'éventail idéologique réel (0,16 → 0,86) est recalé dans une bande
étroite (≈ 0,16 → 0,39). Thomas et Alito « tombent juste » parce que
leur vrai dial est déjà sous 0,5 ; Kagan et Sotomayor sont
structurellement faux parce que leur vrai dial est au-dessus et que
l'imitation ne l'y ramène jamais.

### 1.2 La statistique triviale capte ce que le langage perd

D (direction modale par juge sur la fenêtre train) prédit les libéraux
à 0,8367-0,8571 en phase S : dans les 5-4, le bloc libéral vote quasi
systématiquement ensemble. La couche langage (A : 0,2041-0,2653 sur les
libéraux ; B : 0,2041-0,2449) ne transporte pas ce signal de bloc. La
phrase exacte : **la seule couche qui capture la structure de bloc est
la statistique la plus triviale — pas la couche langage.**

### 1.3 Les deux hypothèses faciles sont mortes (descriptif, n = 7)

- **H1 « volume de données » : morte.** Spearman lignes d'entraînement ↔
  B_acc = **+0,144** (n = 7). Kagan a 50 lignes (2,4 × Kavanaugh) et
  rate à l'envers ; Kavanaugh a 21 lignes et réussit. Le volume
  n'explique pas l'asymétrie.
- **H3 « composition de rôle » : morte, et son cadavre est
  instructif.** Spearman part d'opinions majoritaires ↔ B_acc =
  **−0,739**. Plus un juge écrit d'opinions MAJORITAIRES, plus son
  persona est mauvais. Kagan : 39/50 opinions majoritaires (78 %) —
  persona anti-corrélé. Thomas : 32/146 (22 %), 110 opinions séparées —
  persona le mieux imité. Lecture préliminaire (à tester en E2) : les
  opinions séparées portent une voix plus distinctive (je contre la
  majorité, registre autoriel) ; les opinions majoritaires sont un
  écrit de coalition, délibérément neutre — moins de signal de voix par
  mot. n = 7 : tout ceci est descriptif, aucune inférence.

### 1.4 Le contraste prompt-only : le biographique bat le stylistique

Les deux sièges dégradés (aucun adaptateur, prompt biographique seul)
sont les seuls dont le dial bouge vers la vérité : KBJackson prédit
44,4 % libéral (réel 77,8 % ; n = 9, échantillon minuscule) ;
ACBarrett 15,0 % (réel 20,0 % ; n = 20). À comparer au persona adapté
de Kagan : 4,1 %. **L'identité transportée par le prompt déplace le dial
davantage que l'entraînement sur les textes.** D'où le fait brut déjà
publié — Barrett sans adaptateur 0,75 > Roberts avec 0,6327 — qui cesse
d'être une curiosité et devient un point de données cohérent avec le
mécanisme du dial comprimé. (n petit, hétérogénéité des sièges :
confirmatoire seulement via E1.)

### 1.5 Réplication hors scellé (phase T, fenêtre transparente)

| Camp | B_T (votes) | D_T (votes) | écart |
|---|---|---|---|
| Libéraux (Sotomayor, Kagan) | 0,4065 | 0,6667 | **−0,26** |
| Conservateurs (5 sièges) | 0,5967 | 0,5998 | −0,003 |

L'asymétrie **se réplique sur la fenêtre transparente** (205 affaires
ordinaires, scellées exclues) : elle n'est pas un artefact de la
sélection 5-4. Mais elle y est **atténuée** (Kagan 0,3333 en T contre
0,2041 en S) : les 5-4 l'amplifient parce que le bloc libéral y est
presque toujours uni. Deux lectures cumulatives : (i) le déficit
persona sur les libéraux est général ; (ii) il coûte le plus exactement
là où l'hypothèse forte avait placé son pari.

### 1.6 Ce que la phase 0 établit / n'établit pas

**Établi (au niveau descriptif)** : (a) les argmax des personas sont
quasi unanimement conservateurs ; (b) l'éventail réel des votes est
comprimé par la couche persona ; (c) le volume et la composition de
rôle n'expliquent pas l'asymétrie ; (d) l'asymétrie se réplique hors
scellé ; (e) le prompt biographique déplace le dial plus que
l'adaptateur.
**Non établi** : la cause (distinction style/contenu ? défaut du modèle
de base ? tâche de vote mal posée pour les adaptateurs stylistiques ?) ;
toute causalité ; toute généralisation au-delà de n = 7 adaptateurs,
n = 9 sièges, 1 modèle 3B. C'est l'objet de la phase 1.

---

## 2 · Phase 1 — plan d'enquête pré-enregistré (à figer par commit avant toute exécution GPU)

**Principe directeur** : décomposer le dial en effets causaux
additifs — défaut du modèle de base / effet prompt biographique /
effet adaptateur — sur données NON scellées uniquement. Le test
primaire M4 n'est jamais recalculé ; les 50 scellées ne sont jamais
invoquées.

### E1 · Décomposition causale du dial (prompt-swap, 3 bras)

Pour chaque siège s des 9, sur la fenêtre transparente (205 affaires,
scellées exclues), une requête de vote identique par affaire sous
trois system prompts :
- **bras N (neutre)** : aucune identité (« You are a legal analyst… ») ;
- **bras P (biographique)** : prompt B dégradé actuel (biographie du
  juge, sans adaptateur) ;
- **bras A (adaptateur)** : prompt B + adaptateur du siège (pour les 7
  qui en ont un ; pour Barrett/Jackson le bras A n'existe pas par
  construction).

Mesures pré-inscrites : taux de votes libéraux prédits par bras et par
siège ; p_libéral moyen ; Δ(P−N) = **effet prompt** ; Δ(A−P) = **effet
adaptateur** (la grandeur que la phase 0 soupçonne d'être négative pour
les libéraux : l'adaptateur replierait le dial vers le défaut
conservateur). Prédictions inscrites AVANT exécution : (i) le bras N
présente un défaut conservateur pour tous les sièges ; (ii) Δ(P−N) est
positif pour les libéraux, faible pour les conservateurs ; (iii)
Δ(A−P) est négatif pour Kagan et Sotomayor (l'adaptateur efface le gain
du prompt). Coût : 9 sièges × 205 affaires × ≤3 bras ≈ 4 600 requêtes
≈ 2-3 h de T4. **Étiquette : confirmatoire DANS son propre cadre
(fenêtre transparente, hypothèses inscrites au préalable), sans
retombée sur le test primaire M4.**

### E2 · Distinctivité stylistique (LOCAL, sans GPU — exécutable immédiatement)

Sur les 793 textes v3 (corpus propre, pré-garde), calculer par juge
signataire : richesse lexicale (type-token par fenêtre glissante),
variance de longueur de phrases, signature mots-outils (100 + hapax
relatifs), marqueurs auteurisiels (« I dissent », « the Court »,
première personne, questions rhétoriques), distinctive TF-IDF contre
les autres juges, part de vocabulaire Originaliste/technique. Puis
corrélations inscription préalable : distinctivité ↔ fidélité persona
(B_acc phase S et phase T). **Prédictions inscrites** : (i) Thomas >
Alito > Roberts > Kavanaugh > Gorsuch > Sotomayor > Kagan sur la
distinctivité ; (ii) corrélation distinctivité ↔ B_acc positive et
supérieure à la corrélation volume ↔ B_acc. Étiquette : exploratoire
(corpus figé, mais mesures choisies après avoir vu les fidélités) —
dérivées de H2, jamais présentées comme confirmatoires.

### E3 · Auto-cohérence (le persona connaît-il SES affaires ?)

Sur les affaires de la fenêtre train où le juge a réellement signé et
voté (vérité pré-garde, publique), faire voter le persona du même juge.
Si le persona de Kagan vote « conservateur » même sur les affaires où
la Kagan réelle a voté libéral EN ÉCRIVANT l'opinion dont le texte a
servi à l'entraînement, l'échec est auto-probé : l'adaptateur n'a pas
appris la fonction de décision, même là où il a vu le texte. Coût :
≈ 400 requêtes ≈ 30 min de T4. Étiquette : exploratoire.

### E4 · Réplication croisée (contrôle de robustesse, optionnel)

Rejouer E1 bras N/P sur le pool C RAG (295 affaires pré-décision,
autres que la fenêtre transparente) pour vérifier que la décomposition
ne dépend pas du jeu. Étiquette : exploratoire.

**Garde-fous communs** : adaptateurs = zip authentifié
`m3b_adapters_final.zip` (sha256 `f46d07f7…`, lignage 14/14) ; seed
fixe ; journaux complets ; aucune écriture dans `results/` publiés
(nouveaux fichiers préfixés `a1_`) ; document de pré-enregistrement =
celui-ci, figé par commit AVANT le lancement du kernel ; budget GPU
total ≤ 4 h ; résultat publié quels qu'il soient (même règle que M4).

### Séquence recommandée

E2 (local, maintenant — **exécuté le 2026-10-07, résultats en § 3**) →
E1 + E3 (un kernel Kaggle unique, ~3 h) → intégration dans le papier si
les étiquettes le permettent. E4 en option. **Décision attendue du
propriétaire (D1-bis)** : mandater l'exécution du kernel E1+E3.

---

## 3 · E2 exécuté — résultats (le 2026-10-07)

Script : `scripts/e2_distinctivite.py` → artefact
`download/m4_regen/distinctivite_E2.json`. Corpus : textes v3 pré-garde
tiers full, attribution par signature, ≥ 10 textes par juge (7 juges,
75 903-275 794 mots). **Étiquette : exploratoire.**

| Juge | textes | mots | TTR-500 | phrase σ | JSD (vs autres) | « I dissent »/10k | Distinctivité composite (z) | B_acc phase S |
|---|---|---|---|---|---|---|---|---|
| EKagan | 37 | 204 896 | 0,537 | 14,3 | 0,167 | 0,00 | **+0,24** | **0,2041** |
| JGRoberts | 36 | 202 675 | 0,527 | 14,8 | 0,168 | 0,00 | +0,17 | 0,6327 |
| BMKavanaugh | 18 | 75 903 | 0,483 | 14,4 | 0,212 | 0,13 | +0,11 | 0,7436 |
| SSotomayor | 53 | 179 337 | 0,505 | 14,8 | 0,168 | 0,06 | −0,06 | 0,2449 |
| SAAlito | 37 | 223 420 | 0,515 | 15,2 | 0,158 | 0,04 | −0,07 | 0,8367 |
| NMGorsuch | 24 | 114 596 | 0,539 | 14,1 | 0,186 | 0,00 | −0,08 | 0,6875 |
| CThomas | 70 | 275 794 | 0,505 | 14,3 | **0,155** | 0,18 | **−0,32** | **0,8367** |

**Les deux prédictions inscrites AVANT exécution sont FALSIFIÉES :**
- Prédiction (i) — classement attendu Thomas > … > Kagan : **observé
  l'inverse** (Kagan le plus distinctif en surface, Thomas le moins).
- Prédiction (ii) — corrélation positive distinctivité ↔ fidélité :
  **observé négatif** : Spearman = **−0,721** (phase S) et −0,607
  (phase T), contre +0,144 pour le volume. La distinctivité de surface
  prédit la fidélité du persona *à l'envers*.

Prudence de lecture : le composite inclut un axe à petit n pour Kagan
(JSD sur opinions séparées : 2 textes) ; mais la corrélation négative
tient aussi sur l'axe JSD-tous-textes seul (Thomas/Alito les
distributions les plus proches du corpus, les meilleurs personas ;
Kavanaugh la plus éloignée, un persona moyen). Quoi qu'il en soit,
**aucune mesure de surface ne corrèle positivement avec la fidélité.**

**Interprétation (révision de H2).** Le mécanisme du dial comprimé
(§ 1.1) sort renforcé et précisé : l'échec du persona n'est **pas un
échec de transfert de style** — les signatures de surface des sept
juges sont toutes à des distances JSD minuscules les unes des autres
(0,155-0,212 : l'anglais juridique est un registre commun), et les
juges les plus « standard » en surface obtiennent les meilleurs
personas. Ce qui varie entre les juges — et ce que l'adaptateur ne
transfère pas — c'est **la fonction de décision** (le dial), pas la
voix. Formulation candidate pour le papier :

> L'adaptateur déplace les mots, pas les votes : la ressemblance
> stylistique se transfère, la position idéologique non — et la
> fidélité du persona suit l'alignement du juge sur le défaut du
> modèle, non la distinctivité de sa plume.

Cette falsification pré-enregistrée renforce la crédibilité du
reportage scientifique (une prédiction inscrite qui échoue vaut mieux
qu'une prédiction retro-adaptée). Les tests causaux restent E1/E3.

---

## 4 · Implications pour la rédaction (si phase 1 confirme)

- L'histoire de l'asymétrie dans l'article passe de « fait curieux » à
  « mécanisme identifié » : le persona compresse le spectre idéologique ;
  l'avantage revient à qui vote déjà comme le défaut du modèle. C'est
  une contribution méthodologique exportable (quiconque fine-tune un
  « juge » doit mesurer son dial avant de clamer l'imitation).
- L'essai V79 (SLR Online, fenêtre ouverte) et le papier JOLT/JELS
  gagnent leur figure asymétrie : le graphique « dial prédit vs dial
  réel par siège » (9 points sur la diagonale attendue, tous sous la
  diagonale côté libéral) est déjà calculable avec les chiffres § 1.1.
- La presse (MIT TR / ProPublica / The Markup) reste verrouillée
  jusqu'à E1 : l'angle « le clone du juge échoue » ne devient solide
  qu'avec la cause démontrée.

---

## 5 · Addendum d'implémentation (pré-exécution, figé au même commit)

Établi le 2026-10-07 avant l'exécution du kernel E1+E3, au moment du
figage par commit du tag `a1-freeze`. Ces notes clarifient comment le
plan pré-enregistré ci-dessus (§2) se projette en code
(`scripts/a1_e1e3_kernel.py`, exécuté verbatim depuis ce tag). Elles ne
modifient AUCUNE prédiction inscrite — (i), (ii), (iii) restent
verbatim.

1. **Bras N (neutre)** : la requête N ne contient aucune identité de
   siège ; elle est donc indépendante du siège par construction. Le
   plan décrit « une requête de vote identique par affaire sous trois
   system prompts » pour chacun des 9 sièges ; pour le bras N cette
   requête est la même pour les neuf. Implémentation : N est calculé
   UNE fois par affaire puis répliqué aux neuf sièges — exactement le
   schéma de la condition A du notebook gelé (« A n'a pas
   d'information par juge », vote répliqué aux 9 sièges). Un contrôle
   de déterminisme (double exécution de N sur la première affaire,
   assertion d'égalité byte-exacte) est inclus.
2. **Fenêtre transparente** : la fenêtre complète du builder gelé est de
   211 casefiles test ; le chiffre « 205 » de la phase 0 désigne les
   affaires avec vérité direction (identique à la phase T :
   n_truth_cases = 211, case_direction n = 205). E1 court sur les 211
   (les mesures du dial ne requiert pas de vérité) ; les précisions
   supplémentaires se calculent sur les 205, comme en phase T.
3. **Bras P** = le mode dégradé pré-inscrit de M4 (prompt biographique
   du siège, modèle de base, sans adaptateur) — identique en octets aux
   requêtes des sièges dégradés (Barrett, Jackson) de la phase T.
   **Bras A** = même prompt + adaptateur du siège (7 sièges).
4. **Régressions de fidélité incluses** (suppléments non pré-inscrits) :
   (a) B4 sans exclusion du scellé doit reproduire 0,6366 (machinerie
   vérité) ; (b) les précisions vote par juge du bras A (7 sièges
   adaptés) et du bras P (Barrett/Jackson) doivent reproduire
   EXACTEMENT celles de la condition B de la phase T publiée
   (`results/m4_phaseT.json`) — mêmes prompts, mêmes adaptateurs,
   scoring déterministe ; tout écart signale une divergence
   d'environnement et est consigné comme tel.
5. **Évaluation opérationnalisée de (ii)** : « positif pour les
   libéraux » = Δ(P−N) > 0 pour chacun des trois sièges libéraux
   (Sotomayor, Kagan, Jackson) ; « faible pour les conservateurs » =
   moyenne des Δ(P−N) des six autres sièges inférieure à la moyenne
   des libéraux. Les valeurs par siège sont publiées — toute autre
   lecture reste vérifiable depuis les prédictions brutes.
6. **Sorties** : `a1_e1_decomposition.json`, `a1_e3_autocoherence.json`,
   `a1_e1_predictions.json`, `a1_e3_predictions.json`,
   `a1_run_manifest.json` (+ points de contrôle JSONL au fil de
   l'eau). Aucune écriture dans les fichiers publiés `results/m4_*` —
   ceux-ci ne sont que lus (régression). Résultats publiés quels
   qu'ils soient.
