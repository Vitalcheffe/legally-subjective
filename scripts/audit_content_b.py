# -*- coding: utf-8 -*-
"""Contenu du rapport d'instruction — chapitres 5 a 8 et annexes."""

CH_5_8 = [

# ================================ CHAPITRE 5 ================================
("h1", "5 · Les témoins à charge"),

("p", "Pour éprouver le projet contre le monde extérieur, l'instruction a convoqué trois "
      "relecteurs hostiles simulés — construits à partir des critiques les plus probables, "
      "dans les registres les plus meurtriers : la statistique, le droit, et la presse. "
      "Chacun prononce sa phrase la plus destructive, celle qu'on peut s'attendre à lire "
      "un jour sous un thread ou dans une revue. À chaque phrase, le rapport dit si le "
      "projet y survit, y cède, ou y survit conditionnellement. C'est l'entraînement au "
      "combat que le fondateur a demandé : la pire version de nous-mêmes, jouée par des "
      "autres."),

("quote", "Vos chiffres vedettes ne survivent à aucune correction de multiplicité. "
         "Trente-six comparaisons par paires, Bonferroni à 0,0014 : rien ne reste. "
         "Votre roulette affiche des entiers sans intervalles sur des effectifs de 150 "
         "à 230. Ce n'est pas de la mesure, c'est du théâtre statistique avec de vraies "
         "données.",
         "La biostatisticienne, relectrice simulée"),

("p", "Verdict de survie : <b>conditionnel</b>. Sur le fond, la chercheuse a "
      "mathématiquement raison — le rapport l'a établi au chef I, chiffres à l'appui, "
      "et aucune parade ne transformera un p = 0,040 en p corrigé. Mais sa phrase "
      "s'effondre contre la moitié du projet qu'elle n'a pas ouverte : l'article de "
      "recherche, ses intervalles, ses limitations écrites, ses tests pré-spécifiés. La "
      "réponse honnête à ce témoin tient en une phrase : « les extrêmes seulement, "
      "p = 0,040 non corrigé, et nous l'écrivons nous-mêmes à côté du chiffre ». "
      "Tant que la vitrine ne l'écrit pas, le témoin gagne. Dès qu'elle l'écrit, il ne "
      "reste au témoin que le fond — et le fond tient."),

("quote", "La Cour suprême ne condamne personne. Vous mesurez l'alignement avec le "
         "demandeur et vous le laissez lire comme une probabilité de condamnation par "
         "un public qui ne sait pas ce qu'est un certiorari. Et vous entraînez vos "
         "modèles sur des appels new-yorkais pendant que votre vitrine parle fédéral : "
         "deux univers, une seule narration.",
         "Le professeur de droit, ancien clerk, relecteur simulé"),

("p", "Verdict de survie : <b>survie lexicale, défaite pédagogique</b>. Le vocabulaire "
      "du site a déjà gagné la moitié du duel : « voted their way », jamais « convict », "
      "jamais « acquitte », la définition exacte dans chaque dossier. Mais le témoin "
      "vise ce que la vitrine ne dit pas : l'encart « ce que ce chiffre n'est pas » "
      "n'existe pas au niveau du chiffre, et la couture New York – Cour suprême "
      "n'apparaît nulle part sur le site public. Ces deux silences sont réparables en "
      "deux heures de travail, et ils convertiraient ce témoin du rang d'accusateur à "
      "celui de contradicteur technique — la meilleure chose qui puisse arriver à un "
      "projet empirique."),

("quote", "Une roulette avec les noms de juges en exercice et un score géant rouge. "
         "Je n'ai pas besoin de votre article de recherche pour mon titre : « l'IA qui "
         "note les juges ». Vous avez construit cette page pour qu'elle soit partagée "
         "hors contexte — elle sera partagée hors contexte.",
         "La journaliste tech, relectrice simulée"),

("p", "Verdict de survie : <b>insolvabilité partielle assumée</b>. Il n'existe aucun "
      "disclaimer qui survit à une capture d'écran ; la défense ne peut pas pretendre le "
      "contraire sans mentir. La seule stratégie réelle est de changer ce que la capture "
      "emporte : un chiffre géant qui lit « 69 ± 6 · 226 votes » est un énoncé "
      "difficultile d'arracher de son contexte, précisément parce que l'incertitude "
      "emblématique y est gravée. À défaut, il reste la stratégie du risque assumé et "
      "documenté : savoir qu'un mauvais thread viendra, avoir la page de réponse prête "
      "(chaîne de garde, définitions, intervalles), et gagner le second round. Le projet "
      "a déjà tout le matériel pour le second round ; il n'a pas encore le réflexe."),

# ================================ CHAPITRE 6 ================================
("h1", "6 · Les scénarios de mort (pré-mortem)"),

("p", "L'exercice du pré-mortem impose d'écrire l'autopsie avant le décès : imaginer "
      "que le projet a échoué, puis remonter la chaîne des causes. Six scénarios "
      "émergent, classés par espérance de dommage — probabilité croisée avec gravité. "
      "Chacun reçoit son signal d'alerte précoce et sa condition de survie. Le "
      "rapport les donne dans l'ordre où ils doivent être redoutés."),

("h2", "6.1 · Mort par capture d'écran"),

("p", "Le scénario dominant, parce qu'il est la conséquence directe de la stratégie de "
      "viralité choisie. Un thread hostile capture la roulette sans son contexte, un "
      "titre « l'IA note les juges et condamne Kavanaugh » fait le tour, et le projet "
      "passe le reste de son existence à répondre à une phrase qu'il n'a jamais dite. "
      "La probabilité est élevée — c'est le prix prévisible du design même — et la "
      "gravité est maximale : la crédibilité scientifique meurt par association. Signal "
      "d'alerte : le premier partage massif dont l'auteur n'a pas ouvert la page. "
      "Condition de survie : l'injonction 12 du dispositif exécutée avant tout effort "
      "de diffusion, et une page « réponses aux malentendus » prête à l'avance."),

("h2", "6.2 · Mort statistique"),

("p", "La gate de Phase 1 échoue — et échoue bruyamment, mal interprétée, parce qu'elle "
      "n'était ni assez puissante ni appariée. Ou bien un contradicteur démontre "
      "publiquement que l'écart vedette de la roue ne survit à aucune correction. Le "
      "projet est alors accusé d'avoir vendu du vent. La probabilité est moyenne, mais "
      "elle est la seule des six que le projet contrôle entièrement : la condition de "
      "survival est la culture du résultat négatif déjà inscrite dans le roadmap, "
      "exécutée publiquement et sans honte — « nous l'avions écrit avant de lancer : "
      "voici le résultat négatif documenté ». Un projet qui assume son échec méthodique "
      "en sort crédibilisé ; un projet qui le maquille en réussite en sort mort."),

("h2", "6.3 · Mort par antériorité"),

("p", "« Les scores de Martin-Quinn existent depuis 2002, la base Spaeth couvre chaque "
      "vote depuis 1946, Empirical SCOTUS publie depuis des années — vous avez "
      "réinventé à quoi, exactement ? » La probabilité que ce commentaire arrive est "
      "proche de un ; sa gravité dépend entièrement de la réponse préparée. La "
      "différence réelle existe : fenêtre courte contre décennies, texte intégral "
      "contre votes seuls, contre-factuel par affaire contre score agrégé, chaîne de "
      "garde publique contre base téléchargée. Mais cette différence n'est écrite nulle "
      "part à la portée du public. Condition de survie : la boîte d'antériorité "
      "(injonction 6), écrite avant le premier partage académique."),

("h2", "6.4 · Mort par périmètre"),

("p", "Huit phases, un bâtisseur, un ratio qualité/temps déclaré infini. La formule du "
      "Projet Manhattan est exactement la formule classique de la mort lente par "
      "extension : chaque étage terminé en révèle deux autres, la moitié des travaux "
      "reste à l'état de promesse, et le projet finit en cimetière de branches. "
      "Espérance de dommage : lente mais quasi certaine si aucune discipline "
      "d'abandon. Condition de survie : respecter les gates du roadmap comme des "
      "contrats de phase — chaque étage a un critère mesurable de passage, chaque "
      "critère non atteint doit pouvoir tuer une branche entière sans négociation. Le "
      "roadmap les a écrits ; il faut avoir le courage de s'y tenir, y compris quand "
      "c'est douloureux."),

("h2", "6.5 · Mort éthique et juridique"),

("p", "Probabilité faible, gravité maximale : une plainte, une pression institutionnelle, "
      "ou simplement un juge nommé contraint de répondre publiquement d'un « angle mort » "
      "que lui aurait assigné un site web. Le droit américain protège fortement la "
      "publication de données factuelles sur des personnes publiques, et le projet ne "
      "publie rien que les sources publiques ne contiennent déjà. Le risque n'est donc "
      "pas juridique au premier chef : il est réputationnel et rhétorique — le camp du "
      "« l'algorithme inattaquable qui juge les juges » n'aura besoin d'aucun procès "
      "pour nuire. Condition de survie : la charte éthique du dispositif "
      "(injonction 11), appliquée au vocabulaire public jusqu'au dernier mot."),

("h2", "6.6 · Mort par silence"),

("p", "Le scénario oublié des projets fiers : personne ne vient. Le site est juste, "
      "honnête, corrigé de tous ses défauts — et invisible. La probabilité est "
      "structurelle dans la distribution de l'attention, et la réponse du projet est "
      "déjà construite : la roulette est un crochet émotionnel de première classe, "
      "les questions humaines parlent au premier visiteur venu, et la fenêtre "
      "d'actualité (les sessions de la Cour) fournit un rythme de publication naturel. "
      "La condition de survie est la patience et l'usage : une pièce par session, "
      "jamais de contenu fabriqué pour remplir le vide — la loi zéro-simulation "
      "interdit justement de singer la vie."),

("table", {
    "head": ["Scénario", "Probabilité", "Gravité", "Premier signal", "Condition de survie"],
    "rows": [
        ["Capture d'écran virale", "élevée", "maximale", "partage massif hors contexte", "IC gravé dans le chiffre (inj. 12)"],
        ["Mort statistique", "moyenne", "forte", "gate échouée ou écart contesté", "résultat négatif assumé (inj. 2)"],
        ["Antériorité MQ/Spaeth", "quasi certaine", "moyenne", "premier commentaire savant", "boîte de positionnement (inj. 6)"],
        ["Périmètre / scope", "moyenne", "forte", "phase en retard de deux gates", "gates exécutoires (roadmap)"],
        ["Éthique / réputation", "faible", "maximale", "un juge nommé interrogé", "charte éthique (inj. 11)"],
        ["Silence / invisibilité", "moyenne", "lente", "trois mois sans visiteurs", "patience + une pièce par session"],
    ],
    "ratios": [0.24, 0.13, 0.12, 0.25, 0.26],
    "caption": "Tableau 2 — Les six scénarios de mort, classés par espérance de dommage.",
}),

# ================================ CHAPITRE 7 ================================
("h1", "7 · Le délibéré"),

("p", "Le tribunal délibère sur une seule question, celle que le fondateur a posée : "
      "sommes-nous trop gentils avec notre projet ? La réponse du délibéré est oui, et "
      "elle est plus précise que l'accusation : <b>la gentillesse n'est pas dans les "
      "données — elles sont exactes, traçables, et l'expertise les a recalculées sans "
      "y trouver une seule erreur — la gentillesse est dans l'affichage</b>. Des "
      "entiers sans intervalles, des juxtapositions sans effectifs, une règle de "
      "décision sans test, un module futur écrit au présent de la preuve, une "
      "validation future écrite comme un fait. À chaque fois, le même mécanisme : le "
      "projet se laisse le bénéfice d'un doute qu'il refuse aux juges qu'il mesure."),

("p", "Le délibéré pèse ensuite l'asymétrie stratégique, parce que c'est elle qui doit "
      "gouverner la suite. Dans Légalement Subjective, tout ce qui est descriptif est "
      "une forteresse : les comptes, la provenance, le casier, la méthode de recherche "
      "documentaire — inattaquables par construction, réparables par définition. Tout "
      "ce qui est inférentiel est du verre : les rangs, les prédictions, les "
      "simulations, les variables découvertes — attaquables par nature, fragiles par "
      "honnesteté statistique. La faute stratégique n'est pas d'avoir du verre ; c'est "
      "de laisser le verre porter la forteresse. Tant que la vitrine vend des rangs "
      "et des scores, elle expose son point le plus faible au premier venu. Le jour "
      "où elle vend des comptes avec leurs intervalles, elle expose son point le plus "
      "fort — et il est invulnérable."),

("p", "Sur la stratégie de viralité elle-même, le délibéré refuse une condamnation "
      "facile. Le choix de vendre l'émotion d'abord — la roulette, le nom du juge, le "
      "chiffre rouge — est un choix de fondateur, assumé dans les directives du "
      "projet, et il a une défense sérieuse : l'émotion est le seul véhicule qui "
      "amène le public jusqu'à la chaîne de garde, et un projet de mesure qui "
      "n'est consulté par personne ne mesure rien. Mais ce choix a un prix, et ce "
      "prix est chiffrable au point près : il s'appelle p = 0,040, plus ou moins "
      "six à huit points, et il est actuellement caché dans la poche du site au "
      "lieu d'être cousu sur son vêtement. La sentence ne demande pas de changer "
      "de vêtement. Elle demande de coudre."),

# ================================ CHAPITRE 8 ================================
("h1", "8 · Le dispositif (la sentence)"),

("p", "Le tribunal, après en avoir délibéré, prononce : relaxe partielle sur le fond, "
      "condamnation avec sursis sur la vitrine, et douze injonctions ordonnées par "
      "priorité décroissante — les sept premières conditionnent la prochaine "
      "exposition publique, les suivantes conditionnent les phases futures du "
      "Projet Manhattan. Chaque injonction porte son coût estimé, parce qu'un "
      "ordre sans coût est un vœu."),

("nums", [
    "<b>Afficher l'effectif et l'intervalle à côté de chaque pourcentage public</b> — "
    "« 69 ± 6 OUT OF 100 · 226 VOTES » partout où un chiffre vitrine apparaît. "
    "Le site ne perd ni son impact ni sa franchise ; il gagne son propre standard. "
    "Coût : deux heures.",
    "<b>Amender la gate de Phase 1 avant le lancement sur Colab</b> — ajouter le bras "
    "de base « toujours confirmé », le test apparié exact de McNemar pour B contre A "
    "sur les mêmes 400 affaires, l'intervalle de confiance sur la différence, et "
    "pré-enregistrer la règle complète dans le roadmap. Après le run, la même "
    "modification s'appellerait une fraude de convenience. Coût : une heure, fenêtre "
    "de tir : avant le premier GPU.",
    "<b>Corriger l'étiquette « ci95 » du schéma des dockets</b> — le champ contient "
    "des bornes de rang centile, pas un intervalle de confiance de la valeur ; le "
    "renommer, et afficher le vrai intervalle de la mesure à côté. Une étiquette "
    "mensongère dans le schéma de données disqualifie tout ce qui l'entoure. "
    "Coût : trente minutes.",
    "<b>Réconcilier publiquement les compteurs</b> — une ligne, visible depuis "
    "l'accueil ou la page science : 342 fichiers interrogés, 329 exploitables, "
    "237 affaires décidées, 232 modélisées, et pourquoi chaque marche existe. "
    "Cinq nombres qui circulent sans réconciliation sont cinq pierres d'attente "
    "pour les contradicteurs. Coût : trente minutes.",
    "<b>Drapeau « mandat court » sur tout ce qui touche Jackson</b> — 148 votes, "
    "trois sessions, effet de première session documenté dans la littérature. "
    "Le chiffre le plus dramatique du site est aussi le moins stabilisé ; le "
    "public doit le savoir au moment où il le lit. Coût : trente minutes.",
    "<b>Boîte d'antériorité sur les pages scientifiques</b> — Martin-Quinn depuis "
    "2002, la base Spaeth, Empirical SCOTUS, et en face : ce que Légalement "
    "Subjective fait de différent (fenêtre courte, texte intégral, contre-factuel "
    "par affaire, chaîne de garde publique). La différence existe ; il faut "
    "l'écrire avant que quelqu'un n'écrive l'inverse. Coût : une heure.",
    "<b>Reformuler « THE MACHINE'S CALL »</b> — dire ce que le modèle a vu avant de "
    "prédire : dossier seul, ou momentum des huit collègues. Et accoler la ligne "
    "de base « jamais dissident » aux tampons « called it / missed it », puisque "
    "c'est la comparaison que ces tampons appellent naturellement. Coût : une heure.",
    "<b>Verrouiller le protocole du module darwinien avant d'écrire une ligne de "
    "code</b> — jeu de test scellé et évalué une seule fois, fitness calculée "
    "exclusivement sur ce jeu, contrôle du taux de faux découvertes sur la "
    "population de cellules, réplication sur une deuxième fenêtre de données, et "
    "requalification officielle : « générateur d'hypothèses », jamais « preuve ». "
    "Coût : deux heures d'écriture qui épargnent un an de rétractation.",
    "<b>Un seul modèle conditionné au juge, pas neuf fine-tunages séparés</b> — "
    "l'identité du juge comme jeton du prompt, la loi commune apprise une fois, "
    "les décalages individuels appris en plus ; le signal discriminant entre "
    "juges ne vit que dans la fraction d'affaires disputées, et le neuf-fois-mêmes-"
    "données est le meilleur moyen de l'étouffer. Coût : une décision de "
    "conception, zéro euro.",
    "<b>Renommer la validation humaine en « pilote », ou lui écrire son protocole</b> — "
    "aveuglement décrit, au moins deux évaluateurs, accord inter-annotateurs "
    "rapporté, puissance calculée. Tant que le protocole n'existe pas, le mot "
    "« validation » est un emprunt indû. Coût : cinq minutes pour l'honnêteté, "
    "une semaine pour le protocole complet.",
    "<b>Charte éthique écrite du vocabulaire public</b> — aucun label normatif sur "
    "un juge nommé : « blind spots » devient « divergence profile », les mots "
    "« soft », « tough », « sévère », « clément » sont bannis, et chaque étiquette "
    "passe le test de la capture : arrachée de son contexte, reste-t-elle "
    "factuelle ? Coût : une heure.",
    "<b>Faire de l'incertitude un élément de marque</b> — la plus dure et la plus "
    "rentable : « ± » affiché à la taille du chiffre, le projet qui montre ses "
    "doutes quand l'écosystème entier cache les siens. Dans un paysage saturé de "
    "scores faux-précis, l'humilité statistique gravée en gros caractères rouges "
    "n'est pas une faiblesse ; c'est le seul luxe que personne d'autre ne peut "
    "se permettre honnêtement. Coût : un design, un principe, une décision.",
]),

("p", "Sur ces douze points, le tribunal note que les injonctions 1 à 7 forment un "
      "paquet cohérent de moins d'une journée de travail qui ferme la totalité du "
      "chapitre 3 exposé au public. Les injonctions 8 à 11 concernent des phases non "
      "encore construites : elles coûtent presque rien maintenant parce que rien "
      "n'existe encore, et elles deviendraient presque impossibles à administrer "
      "après coup. L'injonction 12 n'est pas une tâche mais une politique. Le "
      "sursis de la vitrine est subordonné à l'exécution du paquet — et le rapport "
      "prévoit sa propre révision : au prochain commit majeur, l'instruction se "
      "rouvrira, vérifiera l'exécution, et rejugera. Un projet qui veut résister "
      "aux commentaires des autres doit d'abord survivre aux siens."),

# ================================ ANNEXE A ================================
("h1", "Annexe A · Pièces chiffrées"),

("p", "Toutes les valeurs ci-dessous sont des sorties brutes, recalculées à partir des "
      "fichiers du dépôt au commit 3ec9f3b, selon les méthodes décrites à l'Annexe B. "
      "Les intervalles sont binomiaux, approximation normale à 95 % ; l'effectif est "
      "toujours indiqué. Cette annexe est volontairement présentée dans le format que "
      "le rapport exige du site public : chaque chiffre avec son effectif et son "
      "incertitude."),

("table", {
    "head": ["Juge", "Part favorable au demandeur", "n", "IC 95 %", "Écart à la moyenne"],
    "rows": [
        ["Ketanji Brown Jackson", "58,11 %", "148", "[50,2 – 66,1]", "− 5,3 pts"],
        ["Sonia Sotomayor", "59,56 %", "225", "[53,1 – 66,0]", "− 3,8 pts"],
        ["Clarence Thomas", "59,73 %", "226", "[53,3 – 66,1]", "− 3,6 pts"],
        ["Elena Kagan", "61,06 %", "226", "[54,7 – 67,4]", "− 2,3 pts"],
        ["Samuel A. Alito", "61,43 %", "223", "[55,0 – 67,8]", "− 2,0 pts"],
        ["Amy Coney Barrett", "65,58 %", "215", "[59,2 – 71,9]", "+ 2,2 pts"],
        ["Neil M. Gorsuch", "66,96 %", "224", "[60,8 – 73,1]", "+ 3,6 pts"],
        ["John G. Roberts", "68,14 %", "226", "[62,1 – 74,2]", "+ 4,7 pts"],
        ["Brett M. Kavanaugh", "68,58 %", "226", "[62,5 – 74,6]", "+ 5,2 pts"],
    ],
    "ratios": [0.30, 0.24, 0.08, 0.20, 0.18],
    "caption": "Tableau 3 — Axe disposition par juge (l'axe de la roulette), recalculé avec intervalles. "
               "Écart extrêmes : 10,5 points ; z = 2,05 ; p = 0,040 ; aucune des 36 paires ne survit à Bonferroni.",
}),

("table", {
    "head": ["Paire", "Accord", "n", "IC 95 %"],
    "rows": [
        ["Thomas – Jackson", "56,95 %", "151", "[49,1 – 64,9]"],
        ["Alito – Jackson", "58,39 %", "149", "[50,6 – 66,2]"],
        ["Alito – Kagan", "58,77 %", "228", "[52,4 – 65,1]"],
        ["Barrett – Jackson", "65,77 %", "149", "[58,0 – 73,5]"],
        ["Kagan – Jackson", "88,00 %", "150", "[82,4 – 93,6]"],
        ["Sotomayor – Jackson", "92,72 %", "151", "[88,6 – 96,8]"],
        ["Roberts – Alito", "83,84 %", "229", "[78,9 – 88,8]"],
        ["Alito – Gorsuch", "86,78 %", "227", "[82,3 – 91,3]"],
        ["Thomas – Alito", "86,46 %", "229", "[81,9 – 91,0]"],
        ["Roberts – Kavanaugh", "95,24 %", "231", "[92,5 – 97,9]"],
    ],
    "ratios": [0.34, 0.16, 0.10, 0.40],
    "caption": "Tableau 4 — Paires d'accord clés de la matrice (36 paires au total, n de 149 à 232). "
               "La paire vedette de l'accueil repose sur les effectifs les plus faibles du dossier.",
}),

("table", {
    "head": ["Étape", "Effectif", "Explication"],
    "rows": [
        ["Fichiers Oyez interrogés", "342", "cache complet, URI et dates archivées"],
        ["Requêtes ratées", "13", "suffixe .miss, archivées au lieu d'être masquées"],
        ["Fichiers exploitables", "329", "réponses valides"],
        ["Affaires décidées (chrome du site)", "237", "décision présente dans le fichier"],
        ["Affaires modélisables (paper)", "232", "décision avec votes exploitables"],
        ["Effectif maximal d'une paire", "231", "recouvrement réel Roberts – Kavanaugh"],
    ],
    "ratios": [0.38, 0.12, 0.50],
    "caption": "Tableau 5 — Réconciliation des compteurs : cinq nombres circulent, aucun n'est faux, "
               "aucun n'est réconcilié publiquement.",
}),

("table", {
    "head": ["Étape (Phase 1, New York)", "Effectif", "Détail"],
    "rows": [
        ["Corpus collecté", "1 677", "appels criminels 2015 – 2025, sha256"],
        ["Exclusions par éligibilité", "− 333", "issues non binaires"],
        ["Exclusions par la gate anti-fuite", "− 316", "mot de verdict résiduel — exclusion, pas masquage"],
        ["Pool propre", "1 027", "textes « vus avant la décision »"],
        ["Entraînement", "600", "482 confirmations / 118 reversals"],
        ["Test", "400", "319 confirmations / 81 reversals — base 79,75 %"],
    ],
    "ratios": [0.34, 0.12, 0.54],
    "caption": "Tableau 6 — Flux du dataset Phase 1 (rapport de découpe du dépôt, graine 20260827).",
}),

("table", {
    "head": ["Tâche", "Spécification", "AUC", "Précision", "Ligne de base (précision)"],
    "rows": [
        ["Direction", "A — dossier seul", "0,540", "59,5 %", "63,4 %"],
        ["Direction", "B — plus les collègues", "0,877", "81,3 %", "63,4 %"],
        ["Dissidence", "A — dossier seul", "0,614", "84,0 %", "84,1 %"],
        ["Dissidence", "B — plus les collègues", "0,737", "83,4 %", "84,1 %"],
    ],
    "ratios": [0.16, 0.28, 0.10, 0.14, 0.32],
    "caption": "Tableau 7 — Résultats du modèle (artefact model.json) : en dissidence, la précision "
               "de B est inférieure à la ligne de base « jamais dissident » — sur la métrique que le "
               "site affiche en tampons binaires.",
}),

# ================================ ANNEXE B ================================
("h1", "Annexe B · Protocole de vérification"),

("p", "Ce rapport applique au projet la norme que le projet s'impose : chaque affirmation "
      "est vérifiable depuis les sources. Les recalculs ont été effectués au commit "
      "3ec9f3b, branche principale synchronisée avec origin. Les fichiers utilisés : "
      "data/productions/agreement.json (matrice et fenêtre), data/dockets/LS-J-001 à "
      "LS-J-009.json (axes par juge, effectifs), data/productions/model.json (résultats "
      "du modèle entraîné), phase1/dataset/split_report.json (flux 600/400), et le "
      "comptage direct des fichiers du cache Oyez (342 fichiers dont 13 suffixés "
      "« .miss » ; 232 portant décision et votes exploitables)."),

("p", "Méthode des intervalles : approximation binomiale normale à 95 %, demi-largeur "
      "1,96 fois la racine de p(1−p)/n. La correction de Wilson, plus prudente aux "
      "extrêmes, donnerait des intervalles très proches pour ces effectifs ; le juge "
      "retient l'approximation normale pour la lisibilité et la reproductibilité à la "
      "main. Test de l'écart des extrêmes : z égal à la différence divisée par la racine "
      "de la somme des variances ; p bilatéral exact 0,040. Puissance de la gate : "
      "approximation à deux proportions indépendantes avec taux de base 80 % et "
      "n = 400, seuil bilatéral 5 % — un test apparié de McNemar serait plus puissant, "
      "et c'est précisément l'un des reproches du chef II : le roadmap n'en spécifie "
      "aucun, donc la borne conservative est la seule défendable."),

("p", "Pour re-vérifier ce rapport : compter les fichiers du cache Oyez ; recharger "
      "agreement.json et les neuf dockets ; recalculer les intervalles avec la formule "
      "ci-dessus ; recharger model.json et split_report.json ; relancer le test de "
      "régression doré (cinq affaires, concordance attendue 5/5). Chacune de ces "
      "vérifications tient en quelques commandes, sans dépendance au-delà de la "
      "bibliothèque standard. Le jour où la vitrine affiche ses propres intervalles "
      "avec la même facilité, cette annexe aura rempli son office : elle aura montré "
      "au projet, de l'intérieur, à quoi ressemble la norme qu'il doit atteindre — "
      "et qu'elle ne coûte presque rien à tenir."),
]
