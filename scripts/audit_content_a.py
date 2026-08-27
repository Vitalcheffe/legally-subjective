# -*- coding: utf-8 -*-
"""Contenu du rapport d'instruction — chapitres 1 a 4.

Bloc = tuple (type, ...). Types : h1, h2, h3, p, bullets, nums, quote,
statrow, callout, table, fig, note. Le texte est du XML ReportLab
(balises <b>, <i> autorisees ; caracteres & < > interdits hors balises).
"""

CH_1_4 = [

# ================================ CHAPITRE 1 ================================
("h1", "1 · Exposé du dossier"),

("p", "Le fondateur a assigné son propre projet à comparaître. Le mandat reçu est sans "
      "ambiguïté : être cruel, être impartial comme un juge, peser le pour et le contre, "
      "plaider contre soi-même — parce qu'un projet trop gentil avec lui-même est un projet "
      "mort, et que la pire version de nous-mêmes doit être écrite par nous avant qu'un "
      "inconnu ne l'écrive à notre place. Le présent rapport exécute ce mandat. Il instruit "
      "à charge d'abord, à décharge ensuite, et ne prononce la sentence qu'après avoir "
      "pesé les deux plateaux de la balance."),

("p", "Le prévenu : <b>Légalement Subjective</b>, projet open source qui prétend mesurer "
      "la subjectivité judiciaire. Sa vitrine publique est une roulette — « YOU DON'T PICK "
      "YOUR JUDGE » — qui fait tomber le nom d'un juge de la Cour suprême des États-Unis "
      "avec un chiffre géant rouge, sur une fenêtre de 237 affaires décidées entre octobre "
      "2020 et août 2026. Son arrière-boutique est un programme de recherche en huit phases "
      "— le « Projet Manhattan du Droit » — dont la Phase 1 oppose un modèle de langage "
      "vierge à un modèle fine-tuné sur 600 affaires criminelles new-yorkaises, et dont la "
      "porte de sortie est un article arXiv, une validation humaine et un module "
      "darwinien auto-découvreur de variables."),

("p", "Le standard de preuve de cette instruction est celui que le projet réclame pour "
      "lui-même : <b>aucun chiffre ne sera cru sur parole</b>. Chaque nombre cité dans ce "
      "rapport a été recalculé par le juge, depuis les fichiers bruts du dépôt, au commit "
      "3ec9f3b (branche main, synchronisée avec origin). Quand la vitrine affiche "
      "« 56,95 % », le juge a recompté les votes. Quand le manifeste annonce "
      "« 600/400 », le juge a rouvert le rapport de découpe. Quand le article de recherche "
      "revendique une AUC de 0,877, le juge a lu l'artefact du modèle. Les pièces sont "
      "décrites à l'Annexe B pour que quiconque puisse refaire ce que ce rapport a fait."),

("p", "Une précision de méthode, pour l'impartialité : ce rapport distingue systématiquement "
      "« la vitrine » (le site public, ses pages, ses chiffres affichés) et « le fond » "
      "(les données, les scripts, l'article de recherche, la feuille de route). Les deux "
      "sont jugés séparément parce qu'ils ne promettent pas la même chose et ne portent pas "
      "le même risque. La vitrine parle à des humains qui risquent la prison ; le fond parle "
      "à des relecteurs qui risquent de dire non. Un projet peut être innocent dans son fond "
      "et coupable dans sa vitrine. C'est précisément la thèse de l'accusation."),

("statrow", [
    ("342", "fichiers Oyez examinés"),
    ("1 677", "affaires criminelles NY dans le corpus"),
    ("8", "chefs d'accusation retenus"),
]),

# ================================ CHAPITRE 2 ================================
("h1", "2 · L'expertise : ce qui existe réellement"),

("h2", "2.1 · La question de l'authenticité, close par les pièces"),

("p", "Le fondateur a confié un jour ne jamais avoir rien exécuté et soupçonner ses propres "
      "données. L'expertise commence donc par la question la plus basse et la plus grave : "
      "le projet est-il réel ? La réponse est oui, et elle mérite d'être écrite noir sur "
      "blanc parce qu'elle conditionne tout le reste. Le dépôt contient 342 fichiers de "
      "cache Oyez dont 329 exploitables, chacun portant son URI source et sa date de "
      "récupération ; 13 requêtes ratées sont archivées comme telles, avec leur suffixe "
      "« .miss », plutôt que dissimulées. La matrice d'accord affichée par le site se "
      "recalcule exactement depuis ces fichiers. Neuf dossiers de juge existent, chacun "
      "avec ses effectifs, ses définitions d'axes et ses limites déclarées."),

("p", "Côté recherche, le corpus criminel new-yorkais est matériellement là : 1 677 "
      "affaires collectées, chaque requête HTTP consignée dans un journal de collecte, "
      "chaque document hashé en sha256. Le test de régression doré — cinq affaires "
      "vérifiées à la main que le prétraitement doit reproduire à l'identique — repasse "
      "« 5/5 » sur la branche principale. Le script d'entraînement existe, tourne, fixe "
      "sa graine, valide par groupes d'affaires, et écrit ses résultats dans un artefact "
      "qui conserve les versions logicielles. Le notebook Colab de la Phase 1 est généré, "
      "validé syntaxiquement, prêt pour un T4. En un mot : <b>le prévenu n'est pas une "
      "façade</b>. C'est l'un des rares projets de ce genre où l'on peut remonter chaque "
      "chiffre public jusqu'aux octets du cache source."),

("h2", "2.2 · Inventaire des pièces"),

("table", {
    "head": ["Pièce", "Contenu vérifié", "État"],
    "rows": [
        ["Oyez (cache)", "342 fichiers ; 329 exploitables ; 232 avec décision et votes exploitables", "réel, traçable"],
        ["Dockets judiciaires", "9 juges ; 5 axes mesurés ; axe orality « données insuffisantes » assumé", "réel"],
        ["Matrice d'accord", "36 paires ; n de 149 à 232 ; fenêtre oct. 2020 – août 2026", "recalculée, conforme"],
        ["Corpus criminel NY", "1 677 affaires ; journal de collecte ; sha256 des documents", "réel"],
        ["Dataset Phase 1", "1 677 → 1 027 pool propre → 600 entraînement / 400 test", "conforme au roadmap"],
        ["Modèle entraîné", "régression logistique L2 ; validation croisée groupée ; prédictions hors-fold publiées", "réel, exécutable"],
        ["Article LS-R-001", "7 sections, 5 figures, 3 tables, 12 références réelles, section Limitations", "publié sur /paper"],
        ["Site public", "des centaines de pages statiques ; zéro occurrence du mot « convict »", "construit, déployable"],
        ["Git", "18 commits signés du même auteur ; branches d'archive conservées", "discipliné"],
    ],
    "ratios": [0.22, 0.55, 0.23],
    "caption": "Tableau 1 — Inventaire des pièces versées au dossier (commit 3ec9f3b).",
}),

("h2", "2.3 · Ce que le fond a réellement démontré"),

("p", "Le modèle entraîné sur les votes réels de la Cour produit trois résultats solides "
      "que l'accusation ne conteste pas, parce qu'ils sont honnêtement présentés dans "
      "l'article de recherche. Premièrement, le dossier seul ne prédit pas le vote : la "
      "spécification « A », qui ne voit que le dossier, plafonne à une AUC de 0,540 en "
      "direction — à peine mieux qu'un tirage au sort. Deuxièmement, les collègues "
      "prédisent le vote : la spécification « B », qui voit le momentum des huit autres "
      "juges, atteint 0,877. Troisièmement, l'identité du juge compte et l'année ne compte "
      "pas : le khi-deux croisant dissidence et juge vaut 88,04 avec p inférieur à 0,001, "
      "tandis que le khi-deux croisant dissidence et session judiciaire est non "
      "significatif (p = 0,414). Ces trois énoncés sont défendables, publiables, et "
      "vérifiables ligne à ligne grâce aux prédictions hors-fold publiées."),

("p", "La Phase 1 du Projet Manhattan est matériellement avancée au-delà de ce que le "
      "roadmap laissait espérer à sa rédaction : le collecteur a tourné (1 677 affaires), "
      "la découpe 600/400 existe avec une gate anti-fuite vérifiée sur les mille textes, "
      "et le notebook d'expérience attend seulement un GPU. L'expertise prend acte de ce "
      "travail. Mais l'expertise n'est pas un acquittement : elle établit que les "
      "fondations sont réelles. Le réquisitoire qui suit porte sur l'édifice qu'on a "
      "construit dessus, et sur la manière dont il est montré au public."),

("callout", ("p = 0,040", "la significativité exacte de l'écart vedette de la vitrine — "
             "un cran au-dessus du seuil, sans aucune correction de multiplicité. "
             "C'est le nombre le plus dangereux du projet, et le chapitre 3 commence par lui.")),

# ================================ CHAPITRE 3 ================================
("h1", "3 · Le réquisitoire"),

("p", "Le ministère public retient huit chefs d'accusation. Aucun ne reproche au projet "
      "d'avoir inventé : la loi zéro-simulation est respectée, et l'expertise le reconnaît. "
      "Les huit chefs reprochent autre chose — des certitudes affichées que le moteur ne "
      "délivre pas, des protocoles à venir écrits comme s'ils étaient déjà des preuves, "
      "et des coutures invisibles au public. Chaque chef est instruit avec ses pièces."),

("h2", "Chef I — Des chiffres en costume de certitude"),

("statrow", [
    ("z = 2,05", "l'écart vedette de la roue, sous forme de test"),
    ("p = 0,040", "sa significativité, sans correction"),
    ("± 7,9 pts", "l'intervalle à 95 % du chiffre le plus dramatique"),
]),

("p", "La roulette affiche « 58 OUT OF 100 » et « 69 OUT OF 100 » — dix points d'écart "
      "entre Jackson et Kavanaugh, présentés comme « dix points de vie sur le hasard d'un "
      "couloir ». Le juge a recalculé. Kavanaugh : 68,58 % sur 226 votes, intervalle à "
      "95 % plus ou moins 6,1 points. Jackson : 58,11 % sur 148 votes, intervalle plus ou "
      "moins 7,9 points. La différence observée vaut z = 2,05, p = 0,040 — la comparaison "
      "la plus favorable du site, l'opposition des deux extrêmes du banc, passe le seuil "
      "des 5 % avec quatre dixièmes de marge, et <b>les deux intervalles se chevauchent "
      "sur toute la zone 62,5 – 66,1</b>. Toute comparaison intérieure du classement — "
      "Sotomayor contre Roberts, Kagan contre Gorsuch — est statistiquement noyée."),

("fig", "/home/z/my-project/scripts/audit_figs/fig1_forest.png",
        "Figure 1 — L'écart vedette de la roue, recalculé avec ses intervalles à 95 % "
        "(données : dockets LS-J-001 à 009, axe disposition). Les deux extrêmes mis en "
        "avant par la vitrine se chevauchent ; aucun rang intermédiaire n'est distinguable."),

("p", "Il y a plus dur : le banc offre 36 comparaisons par paires. Si l'on corrige la "
      "multiplicité au standard le plus simple — Bonferroni, α = 0,05/36 = 0,0014 — "
      "<b>aucune différence entre juges ne survit sur cet axe</b>. La vitrine vend des "
      "rangs ; les données garantissent à peine un ordre. Et la phrase-totem du site, "
      "« Not an opinion. A count. », est exactement le problème : un compte sans effectif "
      "ni intervalle est un objet en forme d'opinion. Le site applique aux juges un "
      "standard d'honnêteté qu'il refuse de s'appliquer à lui-même."),

("p", "La paire vedette de la page d'accueil cumule les trois défauts. Thomas et Jackson "
      "s'affichent à 56,95 % contre 95,24 % pour Roberts et Kavanaugh — juxtaposés comme "
      "s'ils étaient mesurés sur la même base. Or le premier nombre repose sur 151 "
      "affaires communes et le second sur 231 : ce ne sont pas les mêmes ensembles. Et "
      "l'intervalle du premier, plus ou moins 7,9 points, court de 49,1 à 64,9 : le "
      "« pile ou face » affiché pourrait tout aussi bien être un 65. Le contraste "
      "spectaculairement rhétorique de l'accueil repose sur le nombre le plus fragile du "
      "dossier — celui de la juge la plus récente du banc."),

("p", "Car Jackson est un cas d'école de l'effectif insuffisant : 148 votes, trois "
      "sessions de Cour, contre six pour ses collègues. La littérature empirique documente "
      "par ailleurs un « effet de première session » — les nouveaux juges se déplacent "
      "pendant leurs premières années de service. Le chiffre le plus dramatique du site "
      "est donc, par construction, celui qui comporte le plus d'incertitude de mesure et "
      "le plus d'incertitude de stabilité. Aucun drapeau ne l'annonce au public."),

("h2", "Chef II — Une gate qui ne sait pas distinguer le signal du bruit"),

("p", "La Phase 1 du Projet Manhattan fixe sa règle de succès : le modèle fine-tuné B "
      "doit dépasser le modèle vierge A d'au moins cinq points, faute de quoi le résultat "
      "négatif sera documenté. L'intention est honnête ; la mécanique est défectueuse. "
      "Premier vice : <b>le jeu de test de 400 affaires contient 81 reversals pour 319 "
      "confirmations — un modèle idiot qui répondrait toujours « confirmé » marquerait "
      "79,75 % de précision, et la gate ne le rencontre jamais</b>. Comparer B à A sans "
      "comparer B à la ligne de base du corpus, c'est organiser un match à deux joueurs "
      "en ignorant celui qui gagne sans réfléchir."),

("p", "Deuxième vice : la puissance. À 400 cas et un taux de base de 80 %, l'écart-type "
      "d'une différence de précision entre deux modèles vaut environ 2,8 points. Un écart "
      "réel de cinq points ne produit donc un z observé que de 1,77 : <b>la gate, à son "
      "propre seuil, n'est franchie que 42 fois sur 100 quand l'effet est réel</b> "
      "(figure 2). Autrement dit, la règle de décision choisie a plus de chances de rater "
      "sa propre cible que de l'atteindre. Et si un écart observé de 5,7 points sortait du "
      "notebook, personne — pas même le projet — ne pourrait dire s'il s'agit d'une "
      "découverte ou d'un tirage chanceux : le roadmap ne spécifie aucun test de "
      "significativité, aucun intervalle sur B − A, aucune procédure appariée, alors que "
      "les deux modèles prédisent exactement les mêmes 400 affaires et qu'un test exact "
      "de McNemar s'impose naturellement."),

("fig", "/home/z/my-project/scripts/audit_figs/fig2_power.png",
        "Figure 2 — Puissance de la gate de Phase 1 (n = 400, α = 0,05, taux de base "
        "80 %, approximation à deux proportions). Au seuil de 5 points qu'elle a "
        "elle-même choisi, la gate ne détecte l'effet que dans 42 % des cas."),

("p", "Le remède coûte une heure avant le lancement sur Colab, et devient impossible à "
      "administrer honnêtement après : ajouter le bras « toujours confirmé », choisir le "
      "test apparié exact, pré-enregistrer la règle de décision complète dans le roadmap. "
      "Le rapport insiste : <b>corriger la gate après avoir vu les résultats ne s'appelle "
      "plus corriger une gate</b>. La fenêtre pour le faire proprement est ouverte "
      "aujourd'hui ; le notebook n'a pas encore tourné."),

("h2", "Chef III — Le procès-verbal dit « condamnation », la Cour dit « pourvoi »"),

("p", "La Cour suprême ne condamne personne. Elle accorde ou refuse des pourvois, "
      "confirme ou infirme des décisions inférieures. L'axe que la vitrine transforme en "
      "score géant mesure en réalité l'« alignement avec le demandeur » — la part des "
      "votes d'un juge allant dans le sens de la partie qui demande réparation. Les "
      "dossiers internes le définissent correctement, avec une honnêteté remarquable ; "
      "mais la vitrine le projette à la taille d'une affiche, et un public qui risque la "
      "prison lira « 69 OUT OF 100 » comme « 69 % de chances que ça se passe mal pour "
      "moi ». Le vocabulaire du site est prudent — le juge a vérifié par recherche "
      "exhaustive que le mot « convict » n'apparaît nulle part — mais la prudence "
      "lexicale ne protège pas d'une lecture que le design invite."),

("p", "L'erreur de catégorie se double d'un biais de sélection structurel : la Cour "
      "suprême choisit les affaires qu'elle juge — environ un pour cent des pourvois, "
      "choisis précisément parce qu'ils sont disputés. Les taux d'accord d'une cour de "
      "certiorari ne sont pas les taux d'une cour de jugement ; ils sont mécaniquement "
      "plus polarisés. Extrapoler « one door down » — le contre-factuel qui donne son "
      "slogan au projet — à un justiciable lambda relève de l'inférence écologique. "
      "L'article de recherche l'écrit lui-même, noir sur blanc : toute généralisation à "
      "des cours où les panels sont tirés au sort « est une inférence, pas une mesure ». "
      "La honnêteté existe donc dans le fond. Elle n'est simplement pas affichée à la "
      "hauteur du chiffre qu'elle devrait accompagner."),

("h2", "Chef IV — Deux univers de données cousus ensemble"),

("p", "Le site public parle fédéral : la Cour suprême, neuf juges, 232 affaires "
      "modélisées. La Phase 1 du Projet Manhattan parle new-yorkais : 1 677 appels "
      "criminels de la division d'appel de l'État de New York, 2015 à 2025, où les "
      "reversals sont de vrais reversals de condamnations. Ces deux univers sont "
      "légitimes — le volume criminel et les issues binaires existent à New York et pas "
      "à la Cour suprême, c'est une raison scientifique valable de commencer là-bas. "
      "Mais le modèle qui apprend à New York n'alimentera jamais les nombres fédéraux de "
      "la vitrine, et réciproquement. La couture est invisible pour le public : rien sur "
      "le site n'explique que l'expérience fondatrice du projet se joue sur une autre "
      "cour, dans un autre État, sur une autre période. Le premier relecteur attentif "
      "la découvrira, et il la nommera « montage »."),

("h2", "Chef V — Le troupeau prédit par le troupeau"),

("p", "La spécification vedette du modèle — « B, plus les collègues » — atteint 0,877 "
      "d'AUC en direction, et l'article en tire le titre le plus fort du projet : le "
      "dossier seul ne prédit pas le vote, les collègues oui. C'est vrai, c'est mesuré, "
      "et c'est présenté honnêtement. Mais il faut nommer ce que c'est : <b>une mesure de "
      "la structure de consensus de la Cour, pas une mesure du jugement</b>. Quand les "
      "huit autres juges ont voté, le neuvième est prévisible — cela s'appelle la "
      "dynamique de panel et la littérature la connaît depuis longtemps. Présenter cette "
      "AUC sans expliquer qu'elle est ex post — irrutilisable avant le vote — donne au "
      "public l'image d'une machine qui « appelle » les décisions, alors qu'elle constate "
      "la cohérence du banc après coup."),

("p", "Le chef d'accusation se durcit sur la dissidence. L'accuracy du modèle B y vaut "
      "83,4 % — <b>inférieure à la ligne de base « ne jamais prédire une dissidence », "
      "qui vaut 84,1 %</b> (figure 3). Le modèle gagne en AUC et en log-loss, métriques "
      "où il est effectivement meilleur, et c'est scientifiquement défendable ; mais la "
      "page publique de chaque affaire affiche des tampons binaires « called it » / "
      "« missed it » — exactement la métrique où le modèle est battu par une pièce de "
      "monnaie qui dirait toujours « majorité ». Un contradicteur de bonne foi le "
      "trouvera en dix minutes ; un contradicteur de mauvaise foi en fera un titre."),

("fig", "/home/z/my-project/scripts/audit_figs/fig3_ab.png",
        "Figure 3 — Résultats réels du modèle (artefact model.json, graine 20260827). "
        "(a) AUC par spécification et par tâche. (b) Précision sur la dissidence : la "
        "spécification B (83,4 %) perd contre la ligne de base « jamais dissident » "
        "(84,1 %) sur la métrique binaire que le site affiche."),

("h2", "Chef VI — Le module darwinien, une machine à p-hacking en puissance"),

("p", "L'étage 4 du Projet Manhattan prévoit une population de 200 cellules — de petites "
      "fonctions lisant les données et produisant un score — soumises à sélection, "
      "mutation et survie des plus aptes, jusqu'à produire des « variables découvertes » "
      "que personne n'a pensées. L'ambition est fascinante ; la spécification actuelle "
      "est un générateur garanti de faux positifs. La question décisive — <b>sur quelles "
      "données la fitness est-elle calculée ?</b> — n'est tranchée nulle part. Si la "
      "fitness voit les mêmes données qui ont fait naître les cellules, alors "
      "l'évolution trouvera des motifs dans le bruit avec une certitude mathématique : "
      "c'est sa définition. Deux cents prédicteurs soumis à sélection multiple "
      "produisent des survivants même sur des données purement aléatoires."),

("p", "La gate proposée aggrave le cas au lieu de le corriger : « au moins trois "
      "cellules survivantes traduisibles en phrases humaines non triviales ». "
      "Traduisible n'est pas vrai ; l'humain est une machine à narrativiser le bruit — "
      "on appelle cela l'apophénie — et une gate qui mesure la traduisibilité mesure la "
      "rhétorique, pas la réalité. Sans jeu de test scellé, évalué une seule fois, sans "
      "contrôle du taux de faux découvertes et sans réplication sur une deuxième "
      "fenêtre de données, toute « variable découverte » par ce module devra être "
      "publiée comme hypothèse, jamais comme résultat. Le roadmap doit l'écrire avant "
      "que la première ligne de code ne soit écrite ; sinon, ce seront les relecteurs "
      "qui l'écriront à notre place, en une phrase."),

("h2", "Chef VII — Une « validation humaine » qui n'en est pas une"),

("p", "L'étage 5 prévoit de faire juger 400 affaires en aveugle par un ami juriste, puis "
      "de comparer l'humain à la machine dans un triangle : l'IA gagne, l'humain gagne, "
      "ou les deux échouent — ce dernier cas étant promu « résultat le plus précieux : "
      "certaines affaires sont intrinsèquement non-jugeables ». L'idée du triangle est "
      "belle. Le protocole, lui, n'existe pas : un seul évaluateur, aucun critère écrit "
      "d'aveuglement, aucune double annotation, aucun accord inter-annotateurs, aucune "
      "puissance calculée. Avec un évaluateur unique, on mesure autant la personne que "
      "la méthode. Publier cela sous le nom de « validation croisée humaine » offrirait "
      "à la critique exactement ce que le projet prétend fermer : la démonstration qu'on "
      "confond un témoignage et une mesure. Il faut soit écrire le protocole complet, "
      "soit avoir l'honnêteté de l'appeler un pilote."),

("h2", "Chef VIII — L'exposition : captures d'écran, juges nommés, étude contestée"),

("p", "Le site est conçu pour être partagé — c'est sa directive fondatrice, assumée, "
      "revendiquée. Il faut donc en tirer la conséquence logique : <b>il sera partagé "
      "hors contexte</b>. Une capture de « YOU DREW KAVANAUGH — 69 OUT OF 100 » en "
      "caractères géants rouges, sans le n, sans l'intervalle, sans la définition de "
      "l'axe, est un titre d'article qui s'écrit tout seul : « le site qui prédit vos "
      "chances devant chaque juge ». Le disclaimer et le reçu existent sur la page ; la "
      "capture d'écran, par définition, ne les emporte pas. Le seul remède est de rendre "
      "le chiffre lui-même in-capturable sans son incertitude — ou d'assumer le risque "
      "en connaissance de cause, ce qui est un choix, pas un accident."),

("p", "S'y ajoute la question du vocabulaire appliqué à des personnes nommées, vivantes, "
      "en fonction. « BLIND SPOTS » — angles morts — est un jugement de valeur habillé "
      "en mesure : il suggère une déficience là où les données montrent une divergence. "
      "Les neuf dossiers sont factuels, sourcés, prudents ; l'étiquette, elle, éditorialise. "
      "Enfin, la couche 4 du roadmap mobilise l'étude israélienne des juges et des pauses "
      "repas comme motivation pour les effets d'horaire. Cette étude, célèbre, a été "
      "fortement contestée par les ré-analyses qui ont suivi — données corrigées, effet "
      "très atténué. L'invoquer sans précaution, c'est offrir aux relecteurs un flanc "
      "facile sur un projet qui prétend justement corriger la science trop vite acceptée."),

("note", "Pièce D, versée au dossier du chef VIII : dans le schéma des dockets, le champ "
         "« ci95 » contient les bornes du rang centile (par exemple 61 et 94 autour d'un "
         "83<super>e</super> rang), et non l'intervalle de confiance de la valeur mesurée. "
         "Un lecteur qui voit « ci95 : 61 – 94 » à côté de « 68,14 % » croit lire un "
         "intervalle de confiance et conclut que la mesure est dix fois plus précise "
         "qu'elle n'est. Une étiquette mensongère dans le schéma de données est le détail "
         "exact qu'un contradicteur utilise pour disqualifier l'ensemble du projet."),

# ================================ CHAPITRE 4 ================================
("h1", "4 · La plaidoirie (circonstances atténuantes)"),

("p", "La défense parle après l'accusation, parce que c'est l'ordre et parce que le "
      "prévenu en vaut la peine. Car tout ce que le réquisitoire vient de dire repose "
      "sur un fait rare et décisif : <b>le projet mérite d'être jugé sévèrement "
      "précisément parce qu'il est sérieux</b>. On n'instruit pas un projet de façade "
      "avec huit chefs d'accusation ; on l'ignore. Voici ce que l'accusation concède "
      "à la défense, et elle le concède parce que c'est vérifié."),

("p", "Premier chef des circonstances atténuantes : la discipline de provenance. Chaque "
      "chiffre public remonte jusqu'aux octets du cache source — URI, date de "
      "récupération, empreinte sha256 pour le corpus new-yorkais, journal complet des "
      "requêtes HTTP, y compris les échecs archivés au lieu d'être masqués. La loi "
      "zéro-simulation n'est pas un slogan marketing : c'est une architecture, et elle "
      "fonctionne. Dans un écosystème rempli de projets « IA juridique » qui inventent "
      "leurs chiffres, ce seul fait vaut un classement à part."),

("p", "Deuxième chef : la gate anti-fuite de la Phase 1, dans sa conception même. Face "
      "au problème « le verdict suinte dans le récit », le projet a choisi l'exclusion "
      "plutôt que le maquillage : 316 affaires dont le texte contenait un mot de verdict "
      "résiduel ont été purement et simplement sacrifiées — 19 % du corpus — et la "
      "vérification a été rejouée sur chacun des mille textes livrés. On aurait pu "
      "supprimer la phrase fautive et garder l'affaire ; on a préféré perdre des "
      "données que de risquer une fuite. C'est la définition même de l'honnêteté "
      "opérationnelle, et elle contraste avec la pratique dominante du domaine."),

("p", "Troisième chef : la rigueur expérimentale du fond. Validation croisée groupée "
      "par affaire — aucune affaire ne chevauche entraînement et test, la fuite croisée "
      "classique est fermée par construction. Prédictions hors-fold publiées juge par "
      "juge et affaire par affaire, ce qui rend l'article vérifiable ligne à ligne par "
      "n'importe qui. Graine fixée, versions logicielles archivées dans l'artefact, "
      "reproduction par une seule commande. Le test de régression doré garantit le "
      "déterminisme de toute la chaîne d'extraction. C'est le standard des publications "
      "sérieuses, tenu par un projet sans laboratoire derrière lui."),

("p", "Quatrième chef : l'honnêteté écrite là où elle coûte. L'article de recherche "
      "comporte une section Limitations réelle — corpus petit, champ du parti gagnant "
      "en texte libre, absence de codage thématique, cour terminale sans axe de "
      "réversibilité, « toutes les associations sont observationnelles, rien ici "
      "n'identifie un effet causal du juge », et ces percentiles « grossiers par "
      "construction — propriété affichée sur chaque dossier plutôt que cachée ». Les "
      "douze références sont réelles, Martin-Quinn 2002 en tête. L'axe oralité est "
      "affiché « données insuffisantes » au lieu d'être estimé par bravade. Et la gate "
      "de Phase 1 prévoit explicitement d'honorer un résultat négatif. Une culture qui "
      "écrit à l'avance comment elle échouera mérite qu'on la croie quand elle réussit."),

("p", "Cinquième chef : la méthode casier. La « Méthode 2 » de simulation croisée — "
      "recherche sémantique des affaires les plus similaires dans le casier d'un juge, "
      "puis rapport des taux réels sans prédiction — est inattaquable par construction : "
      "c'est une base de données descriptive avec une interface honnête. Elle ne prédit "
      "rien, elle ne simule rien, elle ne peut pas halluciner. C'est la forteresse du "
      "projet, et la défense demandera au tribunal d'en faire l'ossature officielle de "
      "la vitrine. Tout ce qui est fragile dans Légalement Subjective est inférentiel ; "
      "tout ce qui est inflexible est descriptif. La sentence devra en tirer les "
      "conséquences."),

("p", "La défense conclut sans pathos. Le prévenu n'est pas un escroc : c'est un "
      "instrument honnête dont la vitrine parle plus fort que le moteur. Les défauts "
      "listés au chapitre 3 sont réels, chiffrables, et — c'est le point décisif — "
      "<b>presque tous réparables avant la prochaine exposition publique</b>. La suite "
      "du rapport dit comment, à quel prix, et dans quel ordre."),
]
