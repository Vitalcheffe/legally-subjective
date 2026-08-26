# Rapport de Phase 2 — Le corpus à l'échelle

Date : 26 août 2026 · Auteur : pipeline Legally Subjective (exécution
complète, journalisée dans `data/corpus/FETCH_LOG.json` — 1 571 requêtes)

Conforme au manifeste : chaque chiffre de ce rapport est reproduit par
script (`analyze:base-rate`, `verify_data --mode corpus`) sur les
données commitées. Rien n'est estimé, rien n'est arrondi au-delà de
l'affichage.

## 1. Ce qui a été collecté

**1 387 appels criminels réels** de la Cour Suprême de l'État de New
York, division d'appel (Appellate Division), fenêtres 2015–2023,
requête pré-enregistrée `"judgment of conviction"` (protocole §2.1),
dédupliqués par cluster. Tous les documents sont du HTML texte,
chaque requête HTTP est journalisée, chaque document commité avec son
sha256.

| fenêtre | collectés | | fenêtre | collectés |
|---|---|---|---|---|
| 2015 | 53 | | 2020 | 186 |
| 2016 | 70 | | 2021 | 196 |
| 2017 | 134 | | 2022 | 186 |
| 2018 | 213 | | 2023 | 151 |
| 2019 | 198 | | **total** | **1 387** |

Composition de la population (honnêteté sur l'objet étudié) :
1 290 « People v. » (93 % — appels criminels au sens strict),
63 « Matter of » (procédures Article 78 / libération conditionnelle
ayant matché la requête), 34 autres. Les trois classes sont comptées
séparément dans l'artefact d'analyse, jamais mélangées.

### 1.1 Décisions d'ingénierie documentées (écarts au plan initial)

Trois découvertes ont modifié le chemin prévu ; chacune est un
écart *documenté* au sens de l'en-tête du protocole :

1. **Cloudflare sur le canal officiel.** `nycourts.gov` injecte un
   script Cloudflare à jeton tournant dans chaque réponse : deux
   requêtes du même document ne produisent jamais les mêmes octets
   (sha256 instable), et les connexions persistantes sont silencieusement
   abandonnées (requêtes suspendues au-delà du timeout de lecture).
   Décision : le corpus utilise les **copies d'archivage publiques de
   CourtListener** (`storage.courtlistener.com`), byte-stables, l'URL
   officielle restant enregistrée dans la provenance de chaque cas.
   L'échantillon Phase 1 conserve ses documents officiels ; les deux
   canaux sont déclarés par enregistrement (`document_channel`).
2. **Pagination par curseur.** L'API de recherche v4 ignore le
   paramètre `page` (elle retourne la première page pour toute valeur).
   La pagination suit l'URL `next` renvoyée par chaque réponse —
   découverte coûtée : voir la section 5 du rapport de Phase 1 pour le
   contexte des pièges de cette API.
3. **Débordement de fenêtre (amendement de protocole).** La fenêtre
   pré-enregistrée était 2010–2020. Les années 2011–2015 ne sont
   disponibles qu'en PDFs scannés (verrouillées hors pipeline, cf.
   Phase 1) et 2016–2020 n'offrent que ~840 cas exploitables. Pour
   atteindre l'objectif pré-enregistré — **≥1 000 cas utilisables pour
   le split 600/400** — la collecte s'est étendue à 2021–2023 (années
   de même fiabilité HTML). La population d'étude devient 2015–2023 ;
   c'est la seule modification du périmètre, motivée par le respect du
   calcul de puissance, pas par la commodité.

### 1.2 Rendement de la collecte

Sur 1 645 candidats uniques évalués (fenêtres 2015–2020, avant
débordement) : 1 050 collectés, 229 rejetés PDF-seuls (aucun canal
texte disponible), 359 sans URL de document, 0 rejet par la porte
criminelle (la requête fait le travail de sélection — constat
documenté), 0 échec réseau définitif. Les fenêtres 2022–2023 : 337
collectés, 0 rejet — les années récentes sont intégralement en HTML
dans l'archive.

## 2. Extraction structurée à l'échelle

Populations successives (la chaîne exacte est dans
`data/analysis/base_rate_corpus.json`) :

| population | n | part |
|---|---|---|
| collectés | 1 387 | 100 % |
| disposition extraite (règles) | 1 231 | 88,7 % |
| **éligibles binaire** (affirmé vs infirmé/annulé) | **1 111** | 80,1 % |

Les 156 cas sans disposition extraite sont **drapeautés, pas cachés** :
file d'adjudication humaine (R10), jamais comptés comme des données.
Le split pré-enregistré 600/400 devient possible : 1 111 ≥ 1 000 (le
seuil étendu 800/600 exigeait ≥ 1 400 — non atteint, le split
primaire 600/400 s'applique).

## 3. Le taux de base — la mesure exigée par le protocole

**Taux d'confirmation binaire : 855/1 111 = 77,0 % (IC Wilson à 95 %
[74,4 % ; 79,3 %]).** C'est le nombre qui pondérera la loss du
fine-tuning (protocole §4) et le contexte de tout chiffre de
performance à venir.

Distribution multiclasse complète : affirmé 855, infirmé 228, modifié
81, annulé 28, rejeté (non-lieu d'appel) 20, renvoyé 19.

### 3.1 Par année (taux d'confirmation binaire)

| année | n | taux | | année | n | taux |
|---|---|---|---|---|---|---|
| 2015 | 46 | 65,2 % | | 2020 | 144 | 75,7 % |
| 2016 | 53 | 66,0 % | | 2021 | 161 | 82,0 % |
| 2017 | 112 | 77,7 % | | 2022 | 150 | 87,3 % |
| 2018 | 167 | 73,7 % | | 2023 | 117 | 76,1 % |
| 2019 | 161 | 73,9 % | | | | |

### 3.2 Par département — la « loterie » mesurée pour la première fois ici

| département | n | taux de confirmation | IC 95 % |
|---|---|---|---|
| 1er | 115 | 70,4 % | [61,5 % ; 77,9 %] |
| 2e | 319 | 62,4 % | [57,0 % ; 67,5 %] |
| 3e | 402 | 82,8 % | [78,9 % ; 86,2 %] |
| 4e | 274 | 88,0 % | [83,4 % ; 91,6 %] |

**Écart brut 2e → 4e département : 25,6 points de pourcentage**, les
intervalles ne se chevauchent pas. Un appel criminel porté devant le
4e département a une probabilité de confirmation radicalement
différente du même appel porté devant le 2e. C'est la première mesure
concrète du projet — le décor naturel de la question d'accroche
(« auriez-vous été coupable avec un autre juge ? »), et le motif pour
lequel RQ3 (contre-factuel par juge) est la suite logique. Ce chiffre
décrit des **pannels différents jugeant des affaires différentes** :
ce n'est pas encore une preuve d'effet juge, c'est la raison pour
laquelle l'expérience croisée de Phase 5 est conçue.

## 4. Validation (R10) — l'état exact, sans fard

- **Instrument prêt** : 30 cas tirés stratifiés (année × disposition
  binaire), graine fixée (2026 08 26), 18 strates, feuille de revue
  humaine remplissable : `data/validation/corpus_worksheet.md`.
- **Contre-vérification LLM** (même prompt figé que Phase 1) sur les
  30 cas : **23/25 accords = 92 %** (IC Wilson [75 % ; 97,8 %]) sur
  les comparaisons déterminables ; 2 désaccords réels (cas Bennett :
  règle « vacated » vs LLM « mixed » ; cas Brinson : règle « affirmed »
  vs LLM « modified » — deux frontières de classification, pas deux
  erreurs évidentes) ; 5 « unknown » du LLM (textes longs ou
  dispositions composites) — drapeautés pour la revue humaine en
  priorité.
- **Revue humaine : en attente.** C'est le statut honnête. La Phase 1
  avait mesuré 5/5 d'accord règle/LLM ; à l'échelle l'accord tombe à
  92 % (sur échantillon stratifié) — c'est précisément pourquoi la
  constitution exige une revue humaine avant toute publication, et
  pourquoi aucun chiffre de ce rapport ne prétend être une performance
  de modèle.
- **Vérification LLM du corpus complet** : non exécutée (1 387 appels
  API ≈ heures) — c'est la première case du plan de Phase 3, la
  structure de briques la rendant ré-exécutable sans réécriture.

## 5. Intégrité — le gate est passé

`verify_data --mode corpus` : **VALIDATION PASSED** sur les 1 387 cas
(sha256 de chaque document vérifié contre son enregistrement,
provenance complète, porte criminelle matchée, zéro motif de secret
dans les données). 38 drapeaux « panel < 3 juges » et 156
« pas de disposition » — avertissements d'extraction, alimentent la
file d'adjudication. Le journal de requêtes complet (1 571 entrées :
1 569 × HTTP 200, 2 erreurs réseau récupérées) est commité.

## 6. Ce que la Phase 2 arme

- **Phase 3 (Expérience A)** : corpus 1 111 cas binaires ≥ 1 000 →
  split pré-enregistré 600/400 applicable tel quel ; 50 cas de
  calibration à tirer des 111 cas restants ; le taux de base (77 %)
  fournit la baseline-majorité à battre et la pondération de classe.
- **Phase 4 (Expérience B)** : la faisabilité QLoRA reste celle de
  `docs/feasibility.md` ; la pondération par fréquence de disposition
  est désormais calculée sur données réelles.
- **Phase 5 (Expérience C)** : les panels sont extraits pour 1 349
  cas sur 1 387 (97 %) — le profilage des juges dispose de sa matière
  première ; la mesure par département (§3.2) en est le prologue.
- **Le chantier OCR** (slot S1 de `docs/vision.md`) ouvrira 2011–2014
  (≈1 500 décisions supplémentaires) sans toucher au reste.

## 7. Limitations nouvelles de la Phase 2 (cumulées à celles du README)

1. La source documentaire du corpus est la copie d'archivage
   CourtListener (canal officiel verrouillé par Cloudflare — §1.1) ;
   l'URL officielle est enregistrée par cas, l'échantillon Phase 1
   garde ses documents officiels, mais la byte-identité entre les deux
   canaux n'est pas auditée cas par cas.
2. Le taux de base mesure des appels de 2015–2023 sur quatre
   départements d'une seule juridiction ; l'amendement de fenêtre
   (§1.1.3) est motivé par le calcul de puissance, il reste un
   amendement.
3. L'étiquette « disposition » extraite par règles est validée à 92 %
   par LLM sur 30 cas ; les 2 désaccords et les 5 indéterminés ne
   sont résolus par personne pour l'instant (revue humaine en attente).
4. Les 156 cas sans disposition extraite disparaissent de la
   population binaire — si leur profil diffère systématiquement des
   cas extraits (ex. décisions plus longues, formules non standards),
   la population d'étude a un biais de sélection mesurable : 11,3 %
   des cas collectés.
5. La mesure par département (§3.2) confond affaires et juges : les
   départements ne jugent pas les mêmes dossiers. Toute inférence
   causale est reportée à l'expérience croisée de Phase 5.
