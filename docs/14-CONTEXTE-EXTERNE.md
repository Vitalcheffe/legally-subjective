# 14 · Contexte externe — situer M3b/M4 sans comparaison artificielle

> Règle (cahier des charges §XIV) : ne comparer que ce qui est
> méthodologiquement comparable. Aucune phrase du type « nous sommes
> meilleurs que X » sans base comparable. Chaque entrée distingue ce qui
> est **VÉRIFIÉ** (source consultable, recherche web documentée) de ce qui
> relève du **savoir classique** du domaine.

## 1 · Les travaux comparables

### Katz, Bommarito & Blackman (2017) — référence majeure du domaine

- **source** : « Predicting the Behavior of the Supreme Court of the
  United States: A General Approach », *PLOS ONE* 12(4) — page archive.org
  consultée + couverture presse (Ars Technica « Algorithm predicts US
  Supreme Court decisions 70% of the time », juillet 2017) [VÉRIFIÉ par
  recherche web] ;
- **tâche** : prédire le vote de chaque juge et l'issue d'affaire de la
  Cour, à partir de caractéristiques de l'affaire ;
- **données** : corpus de la Cour 1953-2015 (décisions rendues —
  backward-looking pour l'essentiel de l'évaluation + une prévision
  « forward » sur le terme 2016) ;
- **modèle** : forêt aléatoire sur ~95 features (toutes sauf celles
  indisponibles avant décision) ;
- **chiffre souvent cité** : ≈ 70 % au niveau vote / ≈ 71 % au niveau
  affaire en backward-looking [savoir classique + presse] ;
- **différences avec Legally Subjective** :
  1. **le protocole** : Katz et al. évaluent majoritairement en
     backward-looking (la courbe ROC est mesurée sur des affaires déjà
     décidées, avec un découpage aléatoire) ; M4 évalue exclusivement en
     **forward strict** — les affaires de test sont postérieures à tout le
     corpus d'entraînement, et 50 d'entre elles sont scellées avant la
     moindre prédiction ;
  2. **les features** : leur force est le socle de métadonnées riches
     (topic, type de requête, cour inférieure, etc.) — exactement la
     famille de notre baseline B4 (63,7 % vote) : la comparaison pertinente
     est B4 ↔ Katz, pas M3b ↔ Katz ;
  3. **l'époque** : 1953-2015 vs notre fenêtre OT2015..OT2024 —
     distribution différente de la Cour et des matières ;
  4. **la question posée** : ils prédisent depuis des métadonnées ;
     M3b demande si la **plume des juges** (personnalisation textuelle)
     ajoute du signal PAR-DESSUS ces métadonnées.
- **verdict de comparabilité** : comparaison directe de scores
  **INVALIDE** (protocoles non superposables). Comparaison de FAMILLE
  (features structurées ≈ 63-71 % selon protocole/époque) : informative.

### Segal & Cover (1989) — l'ancêtre attitudinal

- **source** : Segal & Cover, « Approach Variables », *American Political
  Science Review* — scores d'idéologie des juges dérivés du contenu
  éditorial de la presse, corrélés aux votes [savoir classique du
  domaine, non re-vérifié par recherche web cette session] ;
- **différences** : signal idéologique agrégé vs notre signal
  textuel par juge ; époque ; pas de scellement prédictif.
- **verdict** : contexte historique, comparaison de scores invalide.

### Les annonces « LLM × SCOTUS » récentes

Plusieurs études et billets circulent depuis 2023-2025 sur GPT-4 et
prédiction d'issues de la Cour (chiffres médiatiques ~ 66-75 %,
protocoles variables : backward, échantillons post-décision, prompts
avec contexte juridique). **Aucune n'a été re-vérifiée par cette
session** (recherches web : pas de source primaire confirmée avec
protocole forward scellé). Nous ne les citons donc pas comme points de
comparaison : les conditions d'évaluation (fuite potentielle des
décisions dans les données de pré-entraînement des LLM commerciaux —
notre propre motivation pour un modèle et des données contrôlés) rendent
la comparaison invalide jusqu'à preuve du contraire.

## 2 · Standards de reporting mobilisés

M3b/M4 alignent son dossier de preuve sur les recommandations usuelles
de reproductibilité des conférences ML (données, splits,
hyperparamètres, seeds, ressources de calcul, code, chemin de
reproduction des résultats) et sur les pratiques de notebooks
exécutables/reproductibles :

| exigence usuelle | où elle vit dans ce projet |
|---|---|
| données + règles de construction | `docs/02-CORPUS.md`, `scripts/m3_build_datasets.py`, `data/processed/stats_v1.json` |
| splits (temporels, scellés) | `docs/04-PROTOCOLE.md` + gel octet par octet (`results/protocol_m3b_freeze.json`) |
| hyperparamètres + seeds | manifeste de lignage `experiment_manifest.json` (empreinte re-dérivable) |
| ressources de calcul | environnement consigné par session (GPU, VRAM, versions) + temps par juge |
| code + versions | dépôt Git (commit consigné), pins pip documentés dans le notebook |
| reproduction des résultats | `docs/13-REPRODUCTIBILITE-M3B.md` (chaîne re-vérifiable commande par commande) |
| intégrité de l'évaluation | scellé M4 re-vérifié à chaque session + CI zéro-fuite (14 contrôles) |

Le niveau visé n'est pas « plus de graphiques » : c'est la possibilité,
pour un tiers, de remonter **résultat → prédiction → modèle →
checkpoint → configuration → données → split → commit → environnement →
journal**, chaque maillon re-haché.

## 3 · Pourquoi aucun score externe n'apparaîtra comme « barre à battre »

La barre de M4 est **interne et pré-inscrite** : B4 re-ajusté strict sur
la population scellée (comparateur like-for-like), M3a-LR/IX/GB, et les
conditions A/C du protocole. Un chiffre externe (70 %, 75 %…) mesuré
sous un autre protocole, une autre époque, un autre découpage, ne peut
ni être « battu » ni « manqué » honnêtement — l'affirmer serait une
erreur méthodologique de première grandeur. La place des travaux
externes est le contexte (§1) et la discussion (limites de la
généralisation), jamais la table de résultats.
