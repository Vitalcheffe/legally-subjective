# Éthique — données publiques, contre-factuels étiquetés, humains d'abord

## Ce que ce projet fait

Il mesure, sur des **données publiques**, la prévisibilité statistique de
décisions judiciaires déjà rendues. Rien de plus. Les données sources —
opinions publiées, plaidoiries enregistrées, votes compilés par des
chercheurs — sont accessibles à toute personne depuis des décennies.

## Les cinq règles

1. **Données publiques uniquement.** Pas de dossiers médicaux, pas de pièces
   scellées, pas de bases privées, pas de scraping agressif. Les sources sont
   CourtListener (Free Law Project), SCDB (université Washington à
   Saint-Louis), et les archives publiques de la Cour. Un token API gratuit
   suffit pour tout.
2. **Aucune donnée personnelle au-delà de la fonction publique.** Les juges et
   les parties des décisions publiées ne sont pas des personnes privées dans
   ce contexte ; nous n'inférons rien sur leur vie privée, leur santé, leurs
   croyances — uniquement sur leurs textes professionnels publics.
3. **Les contre-factuels sont des fictions étiquetées.** L'Arbre des Mondes
   (simuler « et si le juge X avait siégé ? ») produit des scénarios
   contrefactuels. Chaque sortie de ce type porte l'étiquette **« fiction —
   simulation contrefactuelle »** en tête, sans exception. Aucun contrefactuel
   ne sera présenté comme ce qu'un juge « aurait vraiment » décidé.
4. **Pas de déploiement décisionnel.** Ce projet ne conseille personne, ne
   note aucun juge réel, n'alimente aucun outil d'aide à la décision. Un
   « score de juge » n'est ni produit ni publié. La page d'accueil le dit ;
   la licence le dit ; les résultats sont des mesures scientifiques.
5. **Zéro euro, zéro publicité.** Aucune monétisation, aucun pistage, aucun
   compte requis pour lire. L'amateurisme assumé est une protection : un
   projet qui ne peut rien vendre ne peut pas être acheté.

## Sur les personnes citées

Les affaires de la Cour suprême concernent des personnes réelles. Nous
reproduisons leur nom uniquement lorsqu'il fait partie de l'intitulé public de
l'affaire (c'est la convention de citation juridique). Aucune inférence n'est
faite sur les parties ; aucune donnée sur les victimes n'est enrichie.

## Sur les modèles

Nous utilisons Llama 3 8B sous sa licence communautaire, en quantification
QLoRA — le modèle de base n'est jamais rediffusé, seuls les adaptateurs
(quelques centaines de Mo) sont publiés, conformément à la licence Meta. Les
adaptateurs sont des artefacts de recherche ; leurs sorties ne sont pas des
conseils juridiques.

## Si vous êtes chercheur

Ce projet cite ses sources, publie ses scripts, scelle ses tests et rapporte
ses intervalles. Si vous reprenez une partie de ce travail, citez SCDB
(Spaeth et al.) et CourtListener (Free Law Project) — eux ont fait le vrai
travail de fond.
