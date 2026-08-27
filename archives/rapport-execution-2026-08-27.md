# Rapport d'exécution — LS-AUDIT-001-EX

> **Dossier LS-AUDIT-001-EX · établi le 27 août 2026, soir · dépôt Vitalcheffe/legally-subjective**
>
> Réouverture de l'instruction promise par le rapport du même jour : « au
> prochain commit majeur, l'instruction se rouvrira, vérifiera
> l'exécution, et rejugera. » Le présent rapport constate, injonction par
> injonction, ce qui a été exécuté, où la preuve vit, et ce qui reste.
> Chaque constat est vérifiable par commande, depuis le dépôt.

---

## Constatations

### Injonction 1 — Effectif et intervalle à côté de chaque pourcentage public
**EXÉCUTÉE.** La roulette affiche désormais le chiffre ET son ± ET son
effectif à la même échelle visuelle : « 58 ±8 OUT OF 100 · 148 VOTES »,
avec l'intervalle Wilson complet en dessous et dans le titre de l'onglet —
ce qui est capturé emporte son doute. Les trois portes du contrefactuel
portent leurs effectifs. La paire vedette de l'accueil (56,95 % vs
95,24 %) est recalculée depuis `agreement.json` et affiche ses bases
(151 affaires communes vs 231) et ses ±. Les bornes de l'axe dissidence
(4,8 %–25,5 %) portent effectifs et intervalles ; les moyennes de
citations portent leurs n et l'aveu « means, no interval ». Preuve :
`src/components/ls/draw.tsx`, `src/lib/justices.ts`, `src/app/page.tsx`,
et le HTML construit.

### Injonction 2 — Gate de Phase 1 amendée avant le GPU
**EXÉCUTÉE.** Le notebook Colab évalue maintenant TROIS bras : A, B, et la
ligne de base-majoritaire (classe majoritaire de l'entraînement — jamais
du test). La différence B − A est testée par McNemar exact apparié (les
deux modèles jugent les mêmes 400 affaires) avec intervalle à 95 % ; la
règle complète à trois conditions est pré-enregistrée dans le roadmap ET
dans le notebook, et le rapport persisté embarque `mcnemar_p`,
`delta_ci95`, `baseline_majority` et le verdict. Vérifications : les deux
cellules compilent ; la formule exacte reproduit le cas classique de la
littérature (b=15, c=5 → p=0,0414, identique à `scipy.stats.binomtest`).
La fenêtre de tir était ouverte — le notebook n'a jamais tourné sur GPU ;
l'amendement est donc ante-run, pas post-hoc. Preuve :
`phase1/colab/manhattan_stage1_ab.ipynb` (cellules 10–12),
`scripts/amend_gate_stage1.py`, `archives/manhattan-roadmap.md`.

### Injonction 3 — Étiquette « ci95 » corrigée dans le schéma
**EXÉCUTÉE.** Les neuf dockets sont refilés en **révision 1** avec chaîne
`supersedes` et motif gravé dans `chain.correction`. Le champ
`ci95` (bande bootstrap du RANG centile) est renommé `rank_band` ;
`value_ci95` (Wilson 95 % de la valeur mesurée) est ajouté partout où la
métrique est une part binomiale (disposition, temperament) et reste null,
assumé, pour les moyennes et taux (precedent, exposure). Le kernel
(`core/src/legally_subjective/axes/v1.py`) calcule le Wilson ; la
régénération a reproduit les valeurs révision 0 à l'identique (vérifié :
percentiles, effectifs et bandes inchangés au bit près). Le standard
LS-1.0 est amendé (règles 4, 4bis, 6, schéma §4, note d'immuabilité
documentant le premier usage du mécanisme de révision). Interface,
page juge, page cour et route API mis en cohérence. Preuve : neuf scellés
sha256 vérifiés, `standards/LS-1.0.md`, `src/lib/dockets.ts`, pages
concernées.

### Injonction 4 — Compteurs réconciliés publiquement
**EXÉCUTÉE.** Bandeau public sur l'accueil : 342 fichiers interrogés (dont
13 échecs archivés comme misses) → 329 lisibles → 237 décidés → 232
modélisés, chaque marche expliquée en une proposition. Les compteurs sont
calculés par `system-state.ts` depuis le dépôt lui-même (fichiers
`.miss.json` comptés, décision présente, `model.json.dataset.cases`) —
rien n'est tapé à la main. La page science porte la même réconciliation
en note encadrée. Preuve : HTML construit de `/` et `/paper`.

### Injonction 5 — Drapeau mandat court
**EXÉCUTÉE.** Le drapeau « Short record » apparaît quand le dossier
lui-même déclare moins d'années de service dans la fenêtre que le maximum
du banc — piloté par `raw.service_years_window`, jamais par un nom codé en
dur. Aujourd'hui : Jackson, 5 sessions contre 7, 153 voix contre ~230 —
avec l'avertissement de lecture supplémentaire. Preuve :
`src/lib/justices.ts` (`shortMandate`), `src/components/ls/draw.tsx`.

### Injonction 6 — Boîte d'antériorité
**EXÉCUTÉE.** Encart « Prior work — read this before calling anything
new » en tête du corps du papier : Martin-Quinn (2002, séries depuis
1937), base Spaeth (chaque vote depuis 1946), Empirical SCOTUS et la
littérature citée en §1 ; en regard, les quatre différences réelles
(fenêtre entièrement cachée et traçable, mesure ancrée dans le texte,
contrefactuel par affaire, chaîne de garde publique comme livrable) et
l'aveu final : « la nouveauté est dans les reçus, pas dans les
statistiques ». Preuve : `src/app/paper/page.tsx`, HTML construit.

### Injonction 7 — Machine's call reformulé
**EXÉCUTÉE.** La section dit désormais ce que le modèle a vu avant de
prédire (dossier + momentum des huit autres, jamais les votes de l'affaire)
et ce que cela signifie (lecture largement ex post de la cohérence du
banc, pas une boule de cristal). La note de calibration encadrée accompagne
les tampons : modèle 83,4 % contre ligne de base par juge 84,1 % — « sur
les tampons seuls, la règle bête est en tête » — et chaque tampon porte le
marqueur « ·b » renvoyant à l'avertissement. Les nombres viennent de
`model.json`, pas d'une constante. Preuve : `src/app/case/[docket]/page.tsx`,
HTML construit de `/case/18-1259`.

### Injonction 8 — Protocole darwinien verrouillé avant le code
**EXÉCUTÉE (verrou écrit ; module non codé — l'ordre portait sur
l'écriture).** L'étage 4 est requalifié « générateur d'hypothèses » ;
protocole non négociable enregistré : jeu de test scellé évalué une seule
fois, fitness exclusivement hors échantillon de sélection, contrôle du
taux de faux découvertes calibré pour 200 prédicteurs concurrents,
réplication sur une deuxième fenêtre, et retrait de la traduisibilité
comme critère de vérité. La gate devient : ≥ 3 cellules survivant au
scellé, au FDR et à la réplication — publiées comme hypothèses. Preuve :
`archives/manhattan-roadmap.md`, Étage 4.

### Injonction 9 — Un seul modèle conditionné au juge
**EXÉCUTÉE (décision de conception enregistrée).** La couche 3 de l'étage
2 abandonne les neuf fine-tunages séparés : un seul modèle, l'identité du
juge comme jeton du prompt, la loi commune apprise une fois, les décalages
individuels en sus — avec le motif (le signal discriminant ne vit que dans
les affaires disputées). Le tableau des phases et la question tranchée
correspondante sont mis en cohérence. Preuve : roadmap, couche 3, phases.

### Injonction 10 — Validation humaine requalifiée
**EXÉCUTÉE.** L'étage s'appelle « pilote » dans le roadmap, avec les cinq
conditions de requalification en « validation » (aveuglement écrit, deux
évaluateurs, kappa, puissance a priori, critères d'inclusion fixés avant
distribution) et l'engagement : tant que les conditions ne sont pas
réunies, tout livrable s'appelle un pilote. Preuve : roadmap, étage 5.

### Injonction 11 — Charte éthique du vocabulaire
**EXÉCUTÉE.** `standards/ETHICS-1.0.md` est ratifiée : principe (aucun
label de déficience, de vertu ou de tempérament à côté d'un juge nommé),
test de la capture en trois questions, table banni/prescrit (blind spot →
divergence profile ; soft/tough/sévère/clément → taux mesurés avec n et ± ;
activist/restrained → ne pas utiliser), règles d'application (dont les
corrections publiques par révision — premier usage documenté). Le site est
passe au peigne : plus aucune occurrence de « blind spots » hors du
commentaire qui documente le renommage ; aucune occurrence de tough /
severe / lenient / harsh. La section est renommée « Divergence profile »
avec un texte qui refuse la lecture en déficience. Preuve :
`standards/ETHICS-1.0.md`, `src/app/judge/[id]/page.tsx`, recherche
exhaustive dans `src/`.

### Injonction 12 — L'incertitude comme élément de marque
**EXÉCUTÉE.** Le ± est affiché à l'échelle du chiffre vedette (moitié de
la taille, couleur signal profonde — un objet visuel de première grandeur,
pas une note de bas de page), l'onglet du navigateur le porte, la ligne
d'intervalle Wilson est en fixed sous le chiffre, et la promesse est
écrite : « le compte et son doute voyagent ensemble, y compris dans votre
capture d'écran ». L'accueil le dit en toutes lettres sous la roue. C'est
une politique, pas une tâche ; elle a désormais sa première
materialisation. Preuve : `src/components/ls/draw.tsx`.

---

## Le rejugement

Le tribunal constate que **le paquet des injonctions 1 à 7 — celui qui
conditionnait la prochaine exposition publique — est exécuté au complet**,
et que les injonctions 8 à 11, qui ne coûtaient presque rien tant que
rien n'existait, sont gravées avant la première ligne de code des étages
correspondants. L'injonction 12, déclarée « une politique », possède sa
première incarnation visible. Le sursis prononcé contre la vitrine est
donc **levé** : la vitrine affiche désormais ses effectifs, ses
intervalles, ses bases distinctes, sa réconciliation de compteurs et ses
lignes de base — le standard qu'elle exigeait des juges, elle se
l'applique.

Le tribunal rappelle néanmoins ce que cette exécution ne fait pas :
elle ne gonfle pas les effectifs (Jackson reste à 153 voix ; l'écart
vedette reste p = 0,040 non corrigé, et le site, désormais, l'écrit
lui-même à côté du chiffre) ; elle ne fait pas tourner le notebook sur
GPU ; elle ne code pas le module darwinien. Elle aligne les paroles de la
vitrine sur les preuves du fond. La suite appartient à la Phase 1 : le
run Colab, lu avec la gate à trois conditions telle qu'elle est
pré-enregistrée — sans réinterprétation, quel qu'en soit le verdict.

*Un projet qui veut résister aux commentaires des autres doit d'abord
survivre aux siens. Instruction close en attendant le run.*
