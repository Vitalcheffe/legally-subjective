# Vision — la question, l'éthique, le positionnement

## L'expérience de pensée de départ

Donnez à une intelligence artificielle le dossier d'une affaire — les faits,
les arguments, la procédure — mais **pas le verdict**. Demandez-lui de
décider. Puis comparez avec ce que les juges ont réellement décidé.

Maintenant, la variante qui intéresse ce projet : entraînez le modèle sur
**tout ce qu'un juge précis a écrit par le passé**, et testez-le sur **les
affaires futures de ce même juge**. Si le modèle devient meilleur — ne serait-ce
qu'un peu — alors quelque chose du juge est extractible de ses textes
publics. La subjectivité judiciaire, cette chose que l'on dit incommensurable,
laisse une empreinte mesurable.

Si le modèle ne devient pas meilleur, le résultat est tout aussi intéressant :
l'essentiel de la décision ne serait pas dans ce que les juges publient.

**Les deux issues sont des découvertes.** C'est le luxe des questions bien
posées : elles n'ont pas de mauvaise réponse.

## Le pari de l'amateur sérieux

Ce projet s'appelle un « projet de recherche amateur » et assume ce mot.
Sérieux, parce que : corpus gelé avec empreintes, règles écrites avant les
résultats, tests scellés, intervalles de confiance, limites documentées,
tout reproductible pour zéro euro. Amateur, parce que : aucune institution,
aucun budget, aucun enjeu de carrière — juste la question, les données
publiques, et des GPU gratuits.

« Zéro euro pour toujours » n'est pas un argument marketing (il n'y a rien à
vendre) : c'est une contrainte de conception. Elle garantit que n'importe
quel étudiant, enseignant ou curieux peut vérifier, critiquer, prolonger.

## Le nom

*Legally Subjective* — « subjectivité, mesurée ». Le titre assume la tension :
on ne mesure pas la subjectivité elle-même, on mesure **son ombre portée**
sur des décisions publiques. L'ombre suffit pour poser la question ; elle ne
suffit pas pour y répondre définitivement. C'est écrit dans les limites
(`docs/08-LIMITES.md`).

## Les quatre commandements du projet

1. **La règle avant le résultat.** Le corpus et le scellé sont gelés avant
   tout entraînement ; le protocole est écrit avant l'évaluation.
2. **L'intervalle avec le chiffre.** Aucun pourcentage nu, jamais. Un chiffre
   sans incertitude est une opinion déguisée.
3. **La faille avec la réussite.** Chaque défaut connu est documenté au même
   endroit que la statistique qui en dépend.
4. **La porte ouverte.** Scripts courts, données libres, licence permissive,
   contributions bienvenues — le projet appartient à qui veut le vérifier.

## Ce que ce projet n'est pas

- Pas un produit, pas une API commerciale, pas un « LegalAI ».
- Pas un juge de juges : aucun score individuel publié, aucun classement
  d'humains.
- Pas un plaidoyer : ni « les juges sont des machines », ni « l'IA va
  remplacer la justice ». Une mesure, des intervalles, et le droit d'être
  surpris.
