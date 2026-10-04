# 12 · Guide d'exécution Colab (M3b → M4), édition architecture durable

Ce guide décrit la séquence opérationnelle complète, **depuis un
environnement totalement vierge** (rien n'a jamais été fait, aucun fichier
n'existe nulle part), jusqu'à l'Épreuve Finale M4. Il se lit dans l'ordre.

L'architecture v2 rend l'entraînement **insensible aux coupures** : toute la
vérité de l'expérience vit dans un seul dossier Google Drive, les
checkpoints sont promus pendant l'entraînement (pas seulement entre les
juges), et la reprise est automatique. Le notebook est le notebook
`m3b_qlora_personas.ipynb` du dépôt ; sa logique de reprise est testée par
injection de pannes (`scripts/test_m3b_state.py`, scénarios A-L) et par
exécution réelle du Trainer (`scripts/test_m3b_resume_cpu.py`).

## 0 · Ce que « partir de zéro » veut dire, concrètement

Au premier passage, **rien n'existe** :

- aucun dossier `legally-subjective-m3b` sur ton Drive (il sera créé
  automatiquement au §5bis du notebook) ;
- aucun état, aucun manifeste, aucun checkpoint, aucun adaptateur ;
- rien à téléverser, rien à restaurer, rien à fusionner.

Le système distingue sans ambiguïté, à tout moment : *aucune expérience
commencée* / *commencée, aucun juge terminé* / *juge en cours* / *certains
juges terminés* / *tous terminés* / *finalisé*. C'est le manifeste
`state.json` du dossier Drive qui fait la différence — lui seul.

**Ce que tu dois avoir** (et rien d'autre) :

1. le **lien du notebook** (ci-dessous) en favori ;
2. à partir de la première session : le dossier
   `legally-subjective-m3b/` sur ton Drive — **à ne jamais renommer,
   déplacer, ni supprimer** ;
3. un compte Google avec ~3 Go libres sur le Drive.

**Ce que tu ne dois PAS avoir / ne dois PAS faire** :

- pas d'ancien notebook Colab enregistré (toujours repartir du lien) ;
- pas de zip `m3b_adapters_*.zip` à conserver ou fusionner (l'export final
  vit sur le Drive et le runner M4 va le chercher tout seul) ;
- ne jamais éditer une cellule (les seules exceptions sont notées
  « édition autorisée » dans ce guide) ;
- ne jamais relancer une phase S de M4 (une seule fois dans ta vie).

## 1 · La session type M3b (à répéter autant de fois que nécessaire)

Lien (à ouvrir **après** confirmation que le dépôt est à jour) :

    https://colab.research.google.com/github/Vitalcheffe/legally-subjective/blob/main/notebooks/m3b_qlora_personas.ipynb

1. Ouvrir le lien (Colab charge le notebook **depuis GitHub** = toujours
   frais). Si un avertissement « ce notebook n'a pas été créé par Google »
   apparaît : **Exécuter quand même**.
2. **Exécution → Modifier le type d'exécution → T4 GPU → Enregistrer**.
3. **Exécution → Tout exécuter** (ou Ctrl+F9).
4. Une fenêtre Google Drive s'ouvre au §2bis : **autoriser** (compte →
   Autoriser). C'est la seule interaction de toute la session.
5. Ne rien toucher. Laisser travailler jusqu'à ce que tout s'arrête
   (arrêt propre programmé à ~55 min d'entraînement, ou mort de session —
   dans les deux cas, rien ne se perd au-delà d'au plus ~10 pas
   d'entraînement).

**Ce que tu verras** (repères de bon fonctionnement) :

- §1 : `python 3.x`, puis `torch … | transformers 4.49.0 | peft 0.13.2 …` ;
- §2bis : `AUCUNE EXPÉRIENCE COMMENCÉE` (première session) puis, les
  suivantes, un tableau `ÉTAT : EN COURS — n/7 juges terminés` avec le
  dernier pas durable de chaque juge ;
- §5bis : le même tableau, plus `répertoire durable : …legally-subjective-m3b` ;
- §6 : `=== <juge> ===`, la barre de progression HF (perte qui descend),
  et dans le journal `ckpt promu : <juge> pas N` à chaque sauvegarde Drive ;
- arrêt propre : `⏹ budget temps atteint — ARRÊT PROPRE au pas N` **suivi
  de l'instruction** : si le runtime est encore vivant (icône RAM/Disque
  en haut à droite), relancer §6 (ou Tout exécuter) ouvre une nouvelle
  fenêtre sans rien perdre ; sinon, revenir plus tard ;
- fin complète : `TOUS LES JUGES SONT TERMINÉS`, puis §7/§7bis/§8
  s'exécutent tout seuls et l'export final est écrit sur le Drive.

**Fin de session** : rien à télécharger, rien à sauvegarder. Fermer
l'onglet, arrêter la session si tu veux économiser le quota. Revenir plus
tarde au même lien. C'est tout.

## 2 · Les trois points de contrôle (ce qu'on m'envoie, et quand)

1. **Dès que §8 affiche l'export final** (ou si une sortie te semble
   anormale à n'importe quel moment) : copier-coller
   - la sortie complète du §7 (les deux plumes) ;
   - la sortie complète du §7bis (table anti-mémorisation) ;
   - le contenu du fichier `state.json` du dossier Drive (petit fichier
     texte — clic → Ouvrir avec → texte).
   → je vérifie R6 et les audits ; réponse = **GO ou NO-GO** pour M4.
2. **Après le GO** : exécuter M4 phase T (ci-dessous) et m'envoyer la
   sortie complète. La régression B4 doit donner **exactement** 0,6366
   (vote) et 0,558 (affaire) — la moindre divergence = machinerie à
   réparer AVANT l'Épreuve.
3. **Après validation de T** : l'Épreuve (phase S), une seule fois, puis
   m'envoyer la sortie des sections 7-8 et l'export.

Règle transversale : **toute erreur = arrêt immédiat + traceback complète
copiée telle quelle** (le bloc rouge en entier, sans tronquer). Ne jamais
improviser de correction.

## 3 · M4 — l'Épreuve Finale

Lien (notebook **frais**, T4) :

    https://colab.research.google.com/github/Vitalcheffe/legally-subjective/blob/main/notebooks/m4_epreuve_finale.ipynb

**Phase T — transparente, répétable :**
1. Tout exécuter. Au §2, le runner clone le dépôt au tag `m4-freeze`,
   **récalcule le scellé** (toute divergence = arrêt automatique), puis
   récupère **tout seul** l'export final M3b sur le Drive — aucun
   téléversement manuel. La porte de pré-vol est re-exécutée dans le
   clone : le verdict attendu est **READY** (R6 doit être PASS).
2. `PHASE = "T"` est la valeur par défaut — ne rien changer. Exécuter
   jusqu'à la section 6 incluse. Plusieurs heures.
3. M'envoyer la sortie complète (point de contrôle n°2).

**Phase S — l'ÉPREUVE, une seule fois :**
4. Après mon GO : dans la cellule de configuration, passer
   `PHASE = "T"` en `PHASE = "S"` (seule édition autorisée).
   **Laisser `UNSEAL = ""`** — il ne sert qu'aux bris de scellé délibérés.
5. Exécuter la section 7 (7.1 puis 7.2) : les prédictions des quatre
   conditions sont écrites et hachées AVANT toute lecture de vérité
   terrain, puis le verrou `m4_exam.lock` est posé.
6. Section 8 : le score (McNemar pré-inscrit, strates, par juge).
7. Section 9 : export → m'envoyer la sortie + le zip.

**Si erreur pendant 7.2** : ne PAS relancer. Copier la traceback + dire si
le verrou était déjà posé. La reprise se décide ensemble.

## 4 · Incidents connus et remèdes

- **`No module named 'triton.ops'`** : redémarrer l'exécution
  (Exécution → Redémarrer l'exécution, PAS Supprimer — les paquets
  restent), puis relancer. Le pin `>=0.47.0,<0.51` est censé l'empêcher ;
  si ça persiste : traceback complète.
- **Session coupée en plein juge** : rien n'est perdu au-delà d'environ
  10 pas. Session suivante : reprise automatique (message
  `reprise depuis le pas N`).
- **Quota GPU épuisé** (« no GPU available ») : attendre le rechargement,
  rouvrir le lien. L'état est sur le Drive.
- **Fenêtre Drive rejetée / montage échoué** : le notebook refuse de
  démarrer (normal : pas de stockage durable = pas d'entraînement).
  Relancer la cellule §2bis et autoriser.
- **« EMPREINTE INCOMPATIBLE »** : la config scientifique ou les données
  ont changé — ne rien contourner, m'envoyer le message complet.
- **« checkpoints présents mais manifeste illisible »** : ne rien
  relancer, m'envoyer `log.txt` + la liste des fichiers du dossier.
- **Sessions plus longues qu'une heure** : monter `SOFT_MINUTES` dans la
  cellule de configuration (clé opérationnelle, sans impact scientifique).
