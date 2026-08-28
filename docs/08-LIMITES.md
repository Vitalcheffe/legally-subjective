# Limites — ce que ce projet ne peut pas prouver

Une liste honnête vaut mieux qu'une surprise. Voici tout ce que les chiffres
de ce projet **ne disent pas**.

## 1. Le codage SCDB est une interprétation, pas une vérité

Toute notre « vérité terrain » directionnelle (conservateur/libéral) vient du
codage SCDB, fait par des humains selon un guide méthodologique contesté et
contestable. Deux exemples concrets rencontrés pendant M1/M2 :

- `partyWinning` vaut 1 (le pétitionnaire gagne) dans 364 cas sur 368 dans
  notre fenêtre — un codage manifestement peu informatif dans l'édition
  2025_01 ; nous avons écarté la baseline associée.
- La direction « conservateur/libéral » d'une décision sur la procédure
  pure est parfois arbitraire.

Conséquence : nos précisions sont des précisions **par rapport au codage
SCDB**, pas par rapport à une essence juridique. C'est pour ça que les
intervalles de confiance et les κ accompagnent chaque chiffre.

## 2. Le persona n'est pas la personne

Un adapter affiné sur les opinions publiques d'un juge capture au mieux un
*style décisionnel public* : ce que le juge (et ses greffiers) ont bien voulu
écrire. Il ne capture ni les conférences du mercredi, ni les négociations
d'opinion, ni l'évolution personnelle. « B = A » ne signifierait pas « les
juges sont interchangeables » ; seulement que *leurs textes publiés* ne
portent pas de signal prédictif supplémentaire mesurable à cette échelle.

## 3. La taille du corpus

569 affaires, c'est à la fois énorme pour un projet gratuit et minuscule pour
une inférence statistique fine. Avec ~225 affaires de test, un écart de
précision de moins de ~10 points entre deux conditions est difficile à
distinguer du bruit (voir les largeurs d'intervalles). Les effets réels mais
modestes passeront inaperçus. C'est assumé et documenté.

## 4. La sélection du certiorari

Le corpus ne contient que des affaires *plaidées* — celles que la Cour a
choisi d'accepter (~1 % des requêtes). Toute mesure de prévisibilité ne porte
donc que sur ce sous-ensemble très sélectionné, pas sur « la justice » en
général. Le choix lui-même (quelles affaires accepter) est un phénomène
différent, non mesuré ici.

## 5. Les limites des données CourtListener

- Les dockets dupliqués imposent une jointure par jetons de docket —
  robuste mais pas parfaite (8 affaires SCDB sans contrepartie, listées).
- Le fichier bulk des grappes ne couvre pas les années récentes ; nous avons
  basculé sur l'API de recherche, avec date et empreinte consignées.
- Les *slip opinions* ré-ingérés créent des quasi-doublons ; la déduplication
  texte arrive en M1.5 (le compte « 1 778 opinions » est un inventaire, pas
  un compte de documents distincts).

## 6. La fenêtre temporelle est une époque spécifique

OT2015–2023 traverse la mort de Scalia, l'arrivée de trois juges Trump, la
pandémie, le changement de composition de 2020. Les baselines elles-mêmes le
montrent : la classe majoritaire bascule entre le train et le test. Toute
généralisation à une autre époque — ou à une autre cour — est spéculation.

## 7. Le modèle n'est pas le monde

Llama 3 8B quantifié 4 bits est un outil de recherche bon marché, pas une
limite de ce qui est prévisible. Une condition A faible ne prouve pas
l'imprévisibilité ; elle prouve que *ce modèle, ce prompt, ce budget* échoue.
Nous mesurons un plafond atteignable à coût nul — pas le plafond théorique.

## 8. L'auteur

Ce projet est réalisé par un amateur, avec des outils gratuits, en français
documenté et en anglais de travail. Chaque affirmation est vérifiable ; chaque
erreur est une pull request bienvenue. La modestie n'est pas une pose : c'est
la seule position défendable quand on mesure la subjectivité des autres.
