# 12 · Guide d'exécution Colab (M3b → M4)

Ce document décrit la séquence d'exécution opérationnelle, côté Colab,
de la fin de M3b (entraînement des personas) jusqu'à M4 (l'Épreuve
Finale). Il se lit dans l'ordre : chaque étape ne commence qu'après
validation de la précédente. Le notebook M3b est **repreneur** : la
section 5bis restaure les adaptateurs d'une session précédente, la
section 6 n'entraîne que les juges restants.

## Les trois règles d'or

1. **Notebook frais à chaque session.** Un notebook ouvert dans le
   navigateur est un artefact figé : les correctifs poussés au dépôt
   ne l'atteignent jamais. À chaque session, reprendre le notebook
   depuis le dépôt (re-clone ou re-téléchargement), pas la copie
   ouverte la fois précédente.
2. **Erreur = arrêt + traceback.** En cas d'erreur, ne rien
   improviser : copier la traceback complète et l'envoyer pour
   diagnostic. Les seules éditions de cellule autorisées sont celles
   explicitement prescrites dans ce guide.
3. **Phase S = une seule exécution.** Tout ce qui précède l'Épreuve
   est répétable ; l'Épreuve ne l'est pas. Le verrou `m4_exam.lock`
   et le drapeau `UNSEAL` existent pour ça.

## Étape A — finir M3b (plusieurs sessions GPU gratuites)

Runtime : T4 suffit. Notebook : `notebooks/m3b_qlora_personas.ipynb`.

**Session 1** — exécuter dans l'ordre :
- sections 1 à 5 (environnement, configuration, données,
  tokenisation, base 4-bit) ;
- section 5bis : **ne rien téléverser** (première session — la
  cellule reste sans effet) ;
- section 6 : l'entraînement. Un point de reprise est écrit
  (`m3b_report.json`) après **chaque juge** : une coupure en cours de
  juge ne perd que ce juge.

**Fin de chaque session** (ou juste avant une coupure de quota) :
- section 8 : export → télécharger `m3b_adapters_run_*.zip`.
  C'est le seul artefact à conserver précieusement (le rapport est
  inclus dedans). Une copie sur Drive est recommandée (cellule
  optionnelle fournie).

**Chaque session suivante** :
- sections 1 à 5 (runtime neuf = tout recharger) ;
- section 5bis : **téléverser le zip de la session précédente** —
  les adaptateurs déjà entraînés sont restaurés, le rapport remonté ;
- section 6 : seuls les juges restants sont entraînés ;
- section 8 : le zip final contient **tous** les adaptateurs
  (restaurés + nouveaux).

Répéter jusqu'à ce que la section 6 n'ait plus rien à entraîner,
puis :
- section 7 : contrôle de santé (même affaire, deux plumes) —
  copier la sortie ;
- section 7bis : audit anti-mémorisation (min-k% + cloze) — copier
  la sortie complète.

**Durées mesurées sur T4** (à titre d'ordre de grandeur) :
Kavanaugh ~80 min · Gorsuch ~2 h · Roberts 2-2,5 h · Kagan 2-3 h ·
Alito 3,5-4,5 h · Sotomayor 4-5 h · Thomas 4-9 h (early stopping
probable). Total de l'ordre de 15-22 h : étaler sur les sessions, la
configuration reste intacte (EPOCHS 8, MAX_LEN 4096 — toute déviation
doit être consignée, elle casserait la comparabilité inter-juges).

## Étape B — points de contrôle (ce qu'on envoie, et quand)

1. **Dès la fin de M3b** : `m3b_report.json` (petit fichier, inclus
   dans le zip) + sorties complètes des sections 7 et 7bis.
   → vérification du critère R6 et interprétation des audits
   anti-mémorisation ; réponse = GO ou NO-GO pour l'Épreuve.
2. **Après le GO** : exécuter la phase T de M4 (ci-dessous) et
   envoyer la sortie complète.
   → vérification de la régression B4 : les chiffres attendus sont
   exacts (0,6366 au niveau vote ; 0,558 au niveau affaire) — la
   moindre divergence signifie un défaut de machinerie à réparer
   AVANT l'Épreuve.
3. **Après validation de T** : l'Épreuve (phase S), une seule fois,
   puis envoi de l'export final.

## Étape C — M4, l'Épreuve Finale

Session Colab **fraîche** (GPU). Notebook :
`notebooks/m4_epreuve_finale.ipynb` (frais du dépôt).

**Phase T — transparente, répétable :**
1. Sections 1 et 2 : environnement, puis clone du dépôt au tag
   `m4-freeze` (le scellé y est recalculé — toute divergence arrête
   tout). Téléverser le zip FINAL des adaptateurs dans le répertoire
   de travail : la cellule le décompresse elle-même et re-exécute la
   porte de pré-vol dans le clone. Le verdict attendu : **READY**
   (R6 doit être PASS).
2. `PHASE = "T"` (valeur par défaut, ne rien changer) : exécuter les
   sections suivantes jusqu'à la section 6 incluse. C'est le test
   transparent sur la fenêtre publique : répétable sans risque.
3. Envoyer la sortie complète (étape B.2).

**Phase S — l'Épreuve, une seule fois :**
4. Après le GO : dans la cellule de configuration, passer
   `PHASE = "S"`. **Laisser `UNSEAL = ""`** : ce drapeau ne sert
   qu'aux bris de scellé délibérés (re-exécution après verrou),
   qui doivent rester des exceptions consignées.
5. Exécuter la section 7 (7.1 puis 7.2) : les prédictions des quatre
   conditions sont écrites et hachées AVANT toute lecture de vérité
   terrain, puis le verrou est posé.
6. Section 8 : le score (la vérité terrain entre en scène — McNemar
   pré-inscrit, strates, par juge, condition D = B4 re-ajusté strict
   sur la population scellée).
7. Section 9 : export → télécharger `m4_epreuve_export.zip`.

**En cas d'échec pendant l'Épreuve** : ne PAS relancer la 7.2 ;
copier la traceback et l'état (verrou posé ou non) — la reprise se
décide ensemble, avec le journal complet.

## Incidents connus et remèdes

- **bitsandbytes / triton (ImportError)** : les notebooks récents
  encadrent la version (`>=0.47.0,<0.51`) — plus d'édition manuelle
  nécessaire. Si un ImportError persiste après réinstallation :
  purger `sys.modules` des clés `bitsandbytes*` avant de re-tester ;
  en dernier recours, redémarrer le runtime (Restart, pas Delete —
  conserve les paquets).
- **Session coupée pendant un juge** : rien n'est perdu au-delà du
  juge en cours ; il sera réentraîné à la session suivante (absent
  du rapport = absent du compte).
- **Quota GPU épuisé en pleine session** : exécuter la section 8
  tant que le runtime vit, télécharger le zip, reprendre plus tard
  par la 5bis.
