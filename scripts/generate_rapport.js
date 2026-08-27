// INFINITUM — Rapport de direction UI : cinq metaphores pour la vitrine publique
// Genere avec docx-js selon le skill docx (recette de couverture R1, palette Legal Wood,
// profil de police A, TOC 3 sections, tableaux en pourcentages).
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, PageBreak, Header, Footer, PageNumber, NumberFormat,
  AlignmentType, HeadingLevel, WidthType, BorderStyle, ShadingType,
  TableLayoutType, SectionType, LevelFormat, TableOfContents,
} = require("docx");
const fs = require("fs");

// ---------- Palette Legal Wood (Warm + Heavy + Calm) ----------
const P = {
  primary: "28201C",   // titres
  body: "36302C",      // corps
  secondary: "6E6560", // legendes
  accent: "7A5C3A",    // bronze juridique
  surface: "FBF9F7",   // fonds de tableau
};
const COVER = {
  bg: "28201C", titleColor: "FBF9F7", subtitleColor: "C9BFB4",
  metaColor: "D8CFC5", accent: "B08D5F", footerColor: "9A9086",
};

const noBorders = {
  top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE },
  left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
};
const allNoBorders = {
  top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE },
  left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
  insideHorizontal: { style: BorderStyle.NONE }, insideVertical: { style: BorderStyle.NONE },
};

// ---------- Aides typographiques (profil A, document francais) ----------
const FONT = { ascii: "Times New Roman", eastAsia: "SimSun" };
const HFONT = { ascii: "Times New Roman", eastAsia: "SimHei" };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 400, after: 160, line: 380, lineRule: "atLeast" },
    children: [new TextRun({ text, bold: true, size: 32, color: P.primary, font: HFONT })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 120, line: 340, lineRule: "atLeast" },
    children: [new TextRun({ text, bold: true, size: 28, color: P.primary, font: HFONT })],
  });
}
function body(text, opts) {
  const o = opts || {};
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { firstLine: 400 },
    spacing: { line: 312, after: o.after !== undefined ? o.after : 80 },
    children: [new TextRun({ text, size: 24, color: P.body, font: FONT })],
  });
}
// Paragraphe sans retrait (chapeaux, introductions de tableaux)
function lead(text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: 312, after: 100 },
    children: [new TextRun({ text, size: 24, color: P.body, font: FONT })],
  });
}
// Puce alignee a gauche (jamais justifiee, conformement aux regles)
function bullet(text, boldPrefix) {
  const runs = [];
  if (boldPrefix) {
    runs.push(new TextRun({ text: boldPrefix, bold: true, size: 24, color: P.body, font: FONT }));
    runs.push(new TextRun({ text: text, size: 24, color: P.body, font: FONT }));
  } else {
    runs.push(new TextRun({ text, size: 24, color: P.body, font: FONT }));
  }
  return new Paragraph({
    alignment: AlignmentType.LEFT,
    bullet: { level: 0 },
    spacing: { line: 312, after: 60 },
    children: runs,
  });
}
function numbered(ref, text, boldPrefix) {
  const runs = [];
  if (boldPrefix) runs.push(new TextRun({ text: boldPrefix, bold: true, size: 24, color: P.body, font: FONT }));
  runs.push(new TextRun({ text, size: 24, color: P.body, font: FONT }));
  return new Paragraph({
    alignment: AlignmentType.LEFT,
    numbering: { reference: ref, level: 0 },
    spacing: { line: 312, after: 60 },
    children: runs,
  });
}
function caption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 220, line: 280 },
    children: [new TextRun({ text, size: 21, color: P.secondary, font: FONT, italics: true })],
  });
}
function figure(path, widthPx) {
  const buf = fs.readFileSync(path);
  const w = widthPx || 560;
  const h = Math.round(w * 900 / 1440); // captures 1440x900
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 40 },
    children: [new ImageRun({ data: buf, transformation: { width: w, height: h }, type: "png" })],
  });
}
// Tableau generique : entetes + lignes, largeurs en pourcentage
function makeTable(headers, rows, widths, opts) {
  const o = opts || {};
  const headCells = headers.map((t, i) => new TableCell({
    children: [new Paragraph({
      alignment: AlignmentType.LEFT,
      spacing: { line: 280 },
      children: [new TextRun({ text: t, bold: true, size: 20, color: P.primary, font: HFONT })],
    })],
    shading: { type: ShadingType.CLEAR, fill: "F1EAE2" },
    margins: { top: 70, bottom: 70, left: 110, right: 110 },
    width: { size: widths[i], type: WidthType.PERCENTAGE },
  }));
  const bodyRows = rows.map((r) => new TableRow({
    cantSplit: true,
    children: r.map((cell, i) => new TableCell({
      children: [new Paragraph({
        alignment: AlignmentType.LEFT,
        spacing: { line: 280 },
        children: [new TextRun({ text: cell, size: 20, color: P.body, font: FONT, bold: !!(o.boldFirstCol && i === 0) })],
      })],
      margins: { top: 60, bottom: 60, left: 110, right: 110 },
      width: { size: widths[i], type: WidthType.PERCENTAGE },
    })),
  }));
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    layout: TableLayoutType.FIXED,
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: P.accent },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: P.accent },
      left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: "D8D2C9" },
      insideVertical: { style: BorderStyle.NONE },
    },
    rows: [new TableRow({ tableHeader: true, cantSplit: true, children: headCells }), ...bodyRows],
  });
}
function tableTitle(text) {
  return new Paragraph({
    keepNext: true,
    alignment: AlignmentType.LEFT,
    spacing: { before: 160, after: 80 },
    children: [new TextRun({ text, bold: true, size: 21, color: P.primary, font: FONT })],
  });
}

// ---------- Couverture R1 (Pure Paragraph Left) ----------
function splitTitleLines(title, charsPerLine) {
  if (title.length <= charsPerLine) return [title];
  const breakAfter = new Set([..."\uFF0C\u3002\u3001\uFF1B\uFF1A\uFF01\uFF1F", ..."-_\u2014\u2013\u00B7/", ..." \t"]);
  const lines = [];
  let remaining = title;
  while (remaining.length > charsPerLine) {
    let breakAt = -1;
    for (let i = charsPerLine; i >= Math.floor(charsPerLine * 0.6); i--) {
      if (i < remaining.length && breakAfter.has(remaining[i - 1])) { breakAt = i; break; }
    }
    if (breakAt === -1) {
      const limit = Math.min(remaining.length, Math.ceil(charsPerLine * 1.3));
      for (let i = charsPerLine + 1; i < limit; i++) {
        if (breakAfter.has(remaining[i - 1])) { breakAt = i; break; }
      }
    }
    if (breakAt === -1) breakAt = charsPerLine;
    lines.push(remaining.slice(0, breakAt).trim());
    remaining = remaining.slice(breakAt).trim();
  }
  if (remaining) lines.push(remaining);
  if (lines.length > 1 && lines[lines.length - 1].length <= 2) {
    const last = lines.pop();
    lines[lines.length - 1] += last;
  }
  return lines;
}
function calcTitleLayout(title, maxWidthTwips, preferredPt, minPt) {
  preferredPt = preferredPt || 40; minPt = minPt || 24;
  const charWidth = (pt) => pt * 20;
  const charsPerLine = (pt) => Math.floor(maxWidthTwips / charWidth(pt));
  let titlePt = preferredPt, lines;
  while (titlePt >= minPt) {
    const cpl = charsPerLine(titlePt);
    if (cpl < 2) { titlePt -= 2; continue; }
    lines = splitTitleLines(title, cpl);
    if (lines.length <= 3) break;
    titlePt -= 2;
  }
  if (!lines || lines.length > 3) {
    lines = splitTitleLines(title, charsPerLine(minPt));
    titlePt = minPt;
  }
  return { titlePt, titleLines: lines };
}
function calcCoverSpacing(params) {
  const p = Object.assign({ titleLineCount: 1, titlePt: 36, hasSubtitle: false, hasEnglishLabel: false, metaLineCount: 0, fixedHeight: 800, pageHeight: 16838, marginTop: 0, marginBottom: 0 }, params);
  const SAFETY = 1200;
  const usableHeight = p.pageHeight - p.marginTop - p.marginBottom - SAFETY;
  const titleHeight = p.titleLineCount * (p.titlePt * 23 + 200);
  const subtitleHeight = p.hasSubtitle ? (12 * 23 + 600) : 0;
  const englishLabelHeight = p.hasEnglishLabel ? (9 * 23 + 600) : 0;
  const metaHeight = p.metaLineCount * (10 * 23 + 100);
  const implicitParaHeight = 3 * 300;
  const contentHeight = titleHeight + subtitleHeight + englishLabelHeight + metaHeight + p.fixedHeight + implicitParaHeight;
  const safeRemaining = Math.max(usableHeight - contentHeight, 400);
  const FOOTER_MIN = 800;
  const rawTop = Math.floor(safeRemaining * 0.45);
  const rawBottom = Math.floor(safeRemaining * 0.45);
  const bottomSpacing = Math.max(rawBottom, FOOTER_MIN);
  const topSpacing = Math.max(rawTop - Math.max(0, FOOTER_MIN - rawBottom), 400);
  const midSpacing = Math.max(safeRemaining - topSpacing - bottomSpacing, 0);
  return { topSpacing, midSpacing, bottomSpacing };
}
function buildCoverR1(config) {
  const C = config.palette;
  const padL = 1200, padR = 800;
  const availableWidth = 11906 - padL - padR - 300;
  const { titlePt, titleLines } = calcTitleLayout(config.title, availableWidth, 40, 24);
  const titleSize = titlePt * 2;
  const spacing = calcCoverSpacing({
    titleLineCount: titleLines.length, titlePt,
    hasSubtitle: !!config.subtitle, hasEnglishLabel: !!config.englishLabel,
    metaLineCount: (config.metaLines || []).length,
    fixedHeight: 400,
  });
  const accentLeft = { style: BorderStyle.SINGLE, size: 8, color: C.accent, space: 12 };
  const children = [];
  children.push(new Paragraph({ spacing: { before: spacing.topSpacing } }));
  if (config.englishLabel) {
    children.push(new Paragraph({
      indent: { left: padL, right: padR }, spacing: { after: 500 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.accent, space: 8 } },
      children: [new TextRun({ text: config.englishLabel.split("").join("  "), size: 18, color: C.accent, font: { ascii: "Calibri", eastAsia: "SimHei" }, characterSpacing: 40 })],
    }));
  }
  for (let i = 0; i < titleLines.length; i++) {
    children.push(new Paragraph({
      indent: { left: padL },
      spacing: { after: i < titleLines.length - 1 ? 100 : 300, line: Math.ceil(titlePt * 23), lineRule: "atLeast" },
      children: [new TextRun({ text: titleLines[i], size: titleSize, bold: true, color: C.titleColor, font: { eastAsia: "SimHei", ascii: "Arial" } })],
    }));
  }
  if (config.subtitle) {
    children.push(new Paragraph({
      indent: { left: padL, right: padR }, spacing: { after: 800, line: 340, lineRule: "atLeast" },
      children: [new TextRun({ text: config.subtitle, size: 24, color: C.subtitleColor, font: { eastAsia: "Microsoft YaHei", ascii: "Arial" } })],
    }));
  }
  for (const line of (config.metaLines || [])) {
    children.push(new Paragraph({
      indent: { left: padL + 200, right: padR }, spacing: { after: 80 },
      border: { left: accentLeft },
      children: [new TextRun({ text: line, size: 24, color: C.metaColor, font: { eastAsia: "Microsoft YaHei", ascii: "Arial" } })],
    }));
  }
  children.push(new Paragraph({ spacing: { before: spacing.bottomSpacing } }));
  children.push(new Paragraph({
    indent: { left: padL, right: padR },
    border: { top: { style: BorderStyle.SINGLE, size: 2, color: C.accent, space: 8 } },
    spacing: { before: 200 },
    children: [
      new TextRun({ text: config.footerLeft || "", size: 16, color: C.footerColor, font: { ascii: "Arial" } }),
      new TextRun({ text: "                                        " }),
      new TextRun({ text: config.footerRight || "", size: 16, color: C.footerColor, font: { ascii: "Arial" } }),
    ],
  }));
  return [new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    layout: TableLayoutType.FIXED,
    borders: allNoBorders,
    rows: [new TableRow({
      height: { value: 16838, rule: "exact" },
      children: [new TableCell({
        shading: { type: ShadingType.CLEAR, fill: C.bg }, borders: noBorders,
        children,
      })],
    })],
  })];
}
// ---------- CONTENU : sections 1 a 4 ----------
const bodyChildren = [];

// ===== 1. Resume executif =====
bodyChildren.push(h1("1. Résumé exécutif"));
bodyChildren.push(body("La métaphore jMail — une interface de messagerie électronique appliquée aux données judiciaires — est définitivement écartée comme direction d'interface pour la vitrine publique d'INFINITUM. Elle avait fait ses preuves dans le projet pour lequel elle avait été conçue, où des archives de correspondances réelles prenaient vie dans un cadre familier ; mais son registre, celui de la lettre et du fil de discussion, ne dit rien du profil cognitif d'un juge, et son identité appartient à un autre projet. Le présent rapport documente la décision, la recherche en ligne qui l'accompagne, et le choix d'une nouvelle direction."));
bodyChildren.push(body("Cinq directions candidates, radicalement différentes, ont été conçues et matérialisées dans un prototype jetable consultable : L'Encyclopédie (l'entité judiciaire comme article savant), Le Dossier (la forme native de la procédure), L'Observatoire (le monde judiciaire comme ciel étoilé), L'Anatomie (la carte psycho-neurale comme planche d'atlas) et La Gazette (le quotidien de l'intelligence judiciaire). Chacune respecte les règles non négociables du projet : thème clair et sobre, esthétique juridique professionnelle, données réelles vérifiables, vitrine publique en lecture seule."));
bodyChildren.push(body("La recommandation finale procède par synthèse : adopter L'Encyclopédie comme trame maîtresse de toute la vitrine — chaque juge, avocat, juridiction, affaire ou doctrine devient un article avec notice d'autorité, notes de bas de page et renvois — et réserver aux neuf modules analytiques le traitement en planches savantes, calqué sur la structure historique de l'Encyclopédie de Diderot et d'Alembert, qui comptait onze volumes de planches gravées à côté de ses volumes de texte. La Gazette survit comme page d'accueil éditoriale, le Dossier comme format d'export d'étude. Rien ne se perd, tout se classe."));

// ===== 2. Contexte et objectifs =====
bodyChildren.push(h1("2. Contexte et objectifs de la décision"));
bodyChildren.push(h2("2.1 Pourquoi la métaphore jMail a été écartée"));
bodyChildren.push(body("Le projet jMail avait démontré une idée juste : prendre une interface que tout le monde sait déjà utiliser et y déposer des données réelles, denses et authentiques. Le résultat rendait un fond documentaire austère immédiatement navigable, sans formation ni mode d'emploi. Cette leçon de familiarité reste acquise à INFINITUM et guide l'ensemble des cinq directions étudiées ici."));
bodyChildren.push(body("L'application littérale de la forme Gmail au monde judiciaire soulève en revanche cinq objections décisives. Premièrement, le registre de la correspondance — expéditeur, destinataire, objet, fil — ne correspond à aucune structure naturelle des données du projet : un profil cognitif n'est pas un courrier, et les neuf modules d'analyse ne sont pas des pièces jointes. Deuxièmement, l'identité visuelle de la messagerie est empruntée à un autre projet ; INFINITUM doit naître avec la sienne. Troisièmement, le courriel porte une connotation de communication privée et rapide, difficilement conciliable avec la dignité d'une vitrine juridique de référence. Quatrièmement, le fil de discussion est structurellement plat : il vieillit mal face à des entités multiples (juges, avocats, juridictions, affaires, doctrines) et à des analyses de natures différentes. Cinquièmement, l'effet de surprise d'une boîte de réception judiciaire s'épuise en quelques minutes, alors qu'une vitrine publique doit soutenir la lecture répétée et l'étude."));
bodyChildren.push(h2("2.2 Ce que la vitrine publique doit garantir"));
bodyChildren.push(body("La vitrine est le panorama public d'un travail déjà accompli : elle montre des résultats précalculés, elle ne fait pas tourner le moteur. Cette définition emporte six garanties que toute direction d'interface doit satisfaire, et qui serviront de critères d'évaluation aux cinq candidats étudiés ci-après."));
bodyChildren.push(bullet("Lecture seule intégrale : aucun bouton d'exécution, aucune saisie, aucun paramétrage laissé au visiteur ; les résultats sont publiés, jamais déclenchés.", "Lecture seule. "));
bodyChildren.push(bullet("Zéro donnée simulée : seuls des faits réels et vérifiables sont affichés ; les champs que le moteur réel n'a pas encore calculés restent explicitement vides, avec mention de leur provenance future.", "Zéro simulation. "));
bodyChildren.push(bullet("Thème clair, sobre, professionnel : le registre visuel appartient au droit — papier, encre, filets, gravure — jamais au tableau de bord technologique ; le mode sombre est proscrit.", "Esthétique juridique. "));
bodyChildren.push(bullet("Extensibilité infinie : la structure d'accueil doit pouvoir intégrer toute entité ayant existé sans refonte, conformément au principe directeur du projet.", "Infini. "));
bodyChildren.push(bullet("Capacité à loger les neuf modules d'analyse sans les dénaturer ni les aplatir en vignettes interchangeables.", "Neuf modules. "));
bodyChildren.push(bullet("Provenance visible : chaque affirmation renvoie à sa source publique — biographies officielles, collections jurisprudentielles, statistiques de session.", "Provenance. "));

// ===== 3. Methode et sources =====
bodyChildren.push(h1("3. Méthode de travail et sources"));
bodyChildren.push(body("La présente direction d'interface a été établie en trois temps. D'abord, une recherche en ligne conduite le 27 août 2026 sur les interfaces existantes de l'analyse judiciaire — Lex Machina, Pre/Dicta, Harvey, Lexis+, SCOTUSblog — ainsi que sur les registres publics d'évaluation des juges (Colorado, Utah, Californie) et sur les grands systèmes visuels de référence (vocabulaire visuel du Financial Times, atlas anatomiques historiques de la National Library of Medicine, patterns d'infobox des encyclopédies). Ensuite, un brainstorming structuré a produit cinq directions candidates, chacune issue d'une métaphore native du monde du droit ou de la connaissance savante. Enfin, chaque direction a été matérialisée en maquette haute fidélité dans un prototype jetable."));
bodyChildren.push(body("Ce prototype est un fichier HTML autonome, sans dépendance externe, consultable par double-clic : il présente six vues — un sommaire de choix puis les cinq directions — commutables par une barre flottante, par les touches de direction du clavier ou par le paramètre d'URL. La même fiche témoin, la juge Sonia Sotomayor de la Cour suprême des États-Unis, est traitée par les cinq métaphores afin de comparer à données constantes. Les faits biographiques et jurisprudentiels affichés sont réels et vérifiables auprès des sources publiques de la Cour, du Caselaw Access Project et de CourtListener ; les champs analytiques — scores, prédictions, constellations — portent un marqueur distinctif et restent sans valeur, la maquette n'affichant que leur format. Ce choix traduit en pratique la règle du zéro simulacre du projet. Les captures du prototype ont été auditées visuellement ; trois défauts détectés (deux collisions d'étiquettes en carte du ciel, une marge de notes empiétant sur les pièces du dossier) ont été corrigés avant livraison."));

// ===== 4. Constat concurrentiel =====
bodyChildren.push(h1("4. Le constat concurrentiel issu de la recherche"));
bodyChildren.push(h2("4.1 Ce que font les plateformes d'analyse judiciaire"));
bodyChildren.push(body("Pre/Dicta est l'acteur le plus proche d'INFINITUM par la matière : la plateforme profile le comportement des juges fédéraux américains — affiliation politique, formation, patrimoine, parcours — à partir d'environ quinze millions d'affaires historiques et de cinquante à cent points de données par juge, et revendique une exactitude de l'ordre de quatre-vingt-cinq pour cent sur certaines prédictions de motion. Son interface reste toutefois celle d'un logiciel d'abonnement : tableaux de bord, filtres, rapports. Lex Machina, éditée par LexisNexis, délivre des analyses de juges, cours, avocats et parties avec des graphiques réputés propres ; c'est un outil de stratégie contentieuse pour cabinets, fermé au public. Harvey, enfin, appartient à une autre catégorie : assistant génératif pour la diligence, la rédaction et la recherche, sans vocation descriptive du monde judiciaire."));
bodyChildren.push(body("Côté public et gratuit, SCOTUSblog publie depuis 2002 statistiques et analyses de session de la Cour suprême, avec une rigueur de données remarquable mais une présentation de site d'information classique ; la base de données académique de l'université Washington à Saint-Louis offre plus de deux cent cinquante variables par arrêt depuis 1953, en téléchargement plutôt qu'en exploration. Plus instructifs encore sont les registres officiels d'évaluation des juges : le Colorado et l'Utah publient des évaluations de performance destinées aux électeurs, la Californie tient une base publique de décisions disciplinaires. Ces services prouvent qu'un public existe pour la connaissance publique des juges ; aucun n'offre toutefois de profil cognitif, et aucun ne soigne l'expérience de consultation."));
bodyChildren.push(h2("4.2 Le vide stratégique"));
bodyChildren.push(body("Le constat central de la recherche est un vide : aucune plateforme au monde ne publie, gratuitement et pour tous, une encyclopédie visuelle et navigable du monde judiciaire. Les acteurs commerciaux gardent leurs profils derrière des abonnements ; les acteurs publics présentent des fiches administratives sans dimension analytique ni système visuel. INFINITUM, dont le moteur produira des mesures réelles sur corpus public, serait le premier projet à occuper cet espace — à condition de se donner une identité d'interface qui ne ressemble ni à un tableau de bord SaaS, ni à un site d'information, ni à une messagerie. C'est précisément l'objet des cinq directions suivantes."));
bodyChildren.push(tableTitle("Tableau 1 — Panorama concurrentiel synthétique"));
bodyChildren.push(makeTable(
  ["Acteur", "Nature du produit", "Accès public", "Identité d'interface", "Ce qu'INFINITUM en retient"],
  [
    ["Pre/Dicta", "Prédiction et profilage comportemental des juges", "Non — abonnement", "Tableau de bord SaaS", "La profondeur des points de données par juge ; la preuve que la matière existe"],
    ["Lex Machina (LexisNexis)", "Analytique de contentieux : juges, cours, avocats, parties", "Non — abonnement", "Tableaux de bord, graphiques", "La lisibilité des statistiques de motion ; la rigueur des jeux de données"],
    ["Harvey", "Assistant génératif pour cabinets", "Non — entreprise", "Conversation, assistant", "Rien pour la vitrine : autre catégorie de produit"],
    ["SCOTUSblog", "Journalisme de données sur la Cour suprême", "Oui — gratuit", "Site d'information", "La crédibilité du public gratuit ; les statistiques par session comme source"],
    ["Registres d'évaluation (CO, UT, CA)", "Évaluations officielles et décisions disciplinaires", "Oui — officiel", "Fiches administratives", "La preuve d'un besoin public de connaître les juges ; la prudence de ton"],
    ["Base SCOTUS (Washington University)", "Jeu de données académique, 250+ variables par arrêt", "Oui — téléchargement", "Base de données brute", "La profondeur historique depuis 1953 ; l'esprit scientifique"],
  ],
  [16, 24, 14, 20, 26],
  { boldFirstCol: true }
));
bodyChildren.push(lead("Aucun de ces acteurs ne combine les trois éléments qu'INFINITUM peut réunir : des profils cognitifs calculés sur données réelles, une accessibilité publique gratuite, et une identité visuelle mémorable. Le champ est libre ; il reste à choisir la forme."));
// ---------- CONTENU : sections 5 a 8 ----------

// ===== 5. Cinq directions candidates =====
bodyChildren.push(h1("5. Les cinq directions candidates"));
bodyChildren.push(body("Chaque direction est présentée selon la même grille : le concept, l'architecture d'information qu'il induit, ses forces au regard des six garanties du chapitre 2, et ses risques propres. Les captures du prototype illustrent chacune d'elles ; la fiche témoin reste identique d'une variante à l'autre, ce qui permet de juger la métaphore et non le contenu."));
bodyChildren.push(figure("/home/z/my-project/research/shot_S.png"));
bodyChildren.push(caption("Figure 1 — Le sommaire du prototype : cinq directions présentées au choix, avec rappel des règles du projet et du mode d'emploi."));

bodyChildren.push(h2("5.1 Direction A — L'Encyclopédie"));
bodyChildren.push(body("Le concept : chaque entité du monde judiciaire — juge, avocat, juridiction, affaire, doctrine — devient un article d'encyclopédie savante. L'article s'ouvre sur un chapeau factuel, se déploie en sections numérotées (carrière, jurisprudence marquante, analyses, style), s'accompagne d'une notice d'autorité en marge droite — le pattern d'infobox éprouvé par les encyclopédies en ligne — et se referme sur des notes de bas de page sourcées et des renvois croisés. La navigation latérale reproduit un système des connaissances : entités, analyses, appareil savant. La résonance est directe avec la promesse fondatrice d'INFINITUM, classer tout ce qui a existé et existe dans le monde du droit : c'était exactement le programme de l'Encyclopédie de Diderot et d'Alembert."));
bodyChildren.push(body("Ses forces sont décisives. La familiarité du genre est universelle — chacun sait lire une notice et ses notes — sans emprunter l'identité d'aucun produit existant. La dignité encyclopédique convient à une vitrine juridique de référence, et l'appareil savant (sources, méthode, errata) matérialise la règle du zéro simulation : la provenance n'y est pas un accessoire mais un pilier. La structure est infiniment extensible : tout nouvel objet du monde juridique est par définition un article de plus. Le risque principal tient à la neutralité : une encyclopédie qui publie des mesures sensibles — biais, faiblesses — sur des personnes vivantes s'expose à la controverse ; la réponse réside dans l'avertissement méthodologique permanent, la citation des corpus et la distinction nette entre fait sourcé et mesure calculée. Le second risque, la densité du texte, se traite par la solution du chapitre 6 : les planches."));
bodyChildren.push(figure("/home/z/my-project/research/shot_A.png"));
bodyChildren.push(caption("Figure 2 — Variante A : la juge Sonia Sotomayor en article savant, avec notice d'autorité, sections numérotées, notes de bas de page et renvois."));

bodyChildren.push(h2("5.2 Direction B — Le Dossier"));
bodyChildren.push(body("Le concept : le profil d'une entité se consulte comme un dossier d'étude ouvert au greffe. La page est une chemise à onglets — identification, parcours et pièces, mesures, annexes — dont le contenu se compose de pièces numérotées, tamponnées et sourcées, avec mentions marginales manuscrites. La métaphore est cent pour cent juridique : le dossier est l'unité mentale du monde du droit, celle que juges, avocats et greffiers manipulent tous les jours ; le visiteur y reconnaît immédiatement un univers qui lui appartient. La dramaturgie est forte — un dossier qui se feuillette, des pièces qui s'ajoutent quand le moteur calcule — et l'esthétique papier-encre respecte naturellement la règle du thème clair."));
bodyChildren.push(body("Le risque principal est de ton : un dossier ouvert sur une personne vivante évoque l'enquête et la surveillance ; la version publique doit donc se dire explicitement étude cognitive publique, registre en main, jamais perquisition. Le second risque est l'universalité : la forme excelle pour une personne, moins pour une doctrine ou une juridiction ; et la typographie machine, séduisante en petite dose, fatigue sur des corpus longs. Le verdict du prototype est clair : excellent comme format d'archivage et d'export d'une étude complète — un document que l'on télécharge et que l'on conserve — plus risqué comme trame de navigation quotidienne de toute la vitrine."));
bodyChildren.push(figure("/home/z/my-project/research/shot_B2.png"));
bodyChildren.push(caption("Figure 3 — Variante B : onglets, pièces numérotées, tampon de registre public et marge de notes manuscrites ; les mesures analytiques attendent le moteur."));

bodyChildren.push(h2("5.3 Direction C — L'Observatoire"));
bodyChildren.push(body("Le concept : le monde judiciaire est un ciel que l'on observe. Chaque juge est un astre ; l'ancienneté — donnée réelle et vérifiable — fixe le rayon de son orbite ; les alignements de vote dessinent des constellations ; le corpus juris est le centre de gravité. Une table d'éphémérides rassemble les grandeurs de l'astre observé, et le Radar temps réel, huitième module du projet, devient littéralement une fenêtre d'observation. La métaphore a l'élégance de dire la vérité du projet : observer sans intervenir, mesurer sans toucher — l'observatoire est l'antithèse du tribunal, et cette posture désintéressée protège politiquement la vitrine."));
bodyChildren.push(body("Ses forces : un merveilleux visuel immédiat, la mise en valeur native des données temporelles réelles, et une couverture médiatique facile — une carte du ciel judiciaire se partage. Ses risques : la dérive décorative, où la beauté de la carte dissimule la rigueur des mesures ; la lecture difficile des échelles quantitatives en projection radiale ; et la tentation du spatial sombre, qu'il faut refuser au profit d'une gravure de ciel sur papier clair, traits fins et or discret. Le prototype tranche : l'Observatoire est une planche remarquable pour le Réseau des précédents et la vue d'ensemble d'une juridiction, mais une carte ne peut pas à elle seule porter une fiche biographique complète."));
bodyChildren.push(figure("/home/z/my-project/research/shot_C2.png"));
bodyChildren.push(caption("Figure 4 — Variante C : la carte du ciel de la Cour suprême — orbites d'ancienneté réelles, constellations de vote en attente du moteur, éphémérides de l'astre observé."));

bodyChildren.push(h2("5.4 Direction D — L'Anatomie"));
bodyChildren.push(body("Le concept : la carte psycho-neurale, premier module du projet, devient une planche d'atlas anatomique du dix-neuvième siècle. Le système décisionnel d'un juge se dessine en gravure savante — cortex doctrinal, gyri du précédent, glande empathique, filtre idéologique, muscle rhétorique, système nerveux procédural, mémoire des parties, valve de discorde — chaque structure numérotée, renvoyée à une légende savante et à des notices techniques. Les atlas historiques de la National Library of Medicine fournissent la grammaire visuelle : doubles filets, hachures, numérotation marginale, légendes en italique."));
bodyChildren.push(body("Ses forces : une incarnation parfaite du module le plus distinctif du projet, une vertu pédagogique rare — le schéma légendé explique mieux qu'un tableau de chiffres — et une esthétique premium, claire et mémorable. Ses risques sont de deux ordres. Éthique d'abord : la dissection appliquée à une personne vivante doit se dire métaphore savante et non prétention médicale ; la planche du prototype le fait en précisant que les structures sont des constructions analytiques inférées, non des organes. Scientifique ensuite : la belle gravure peut faire passer pour savoir ce qui n'est encore que modèle ; la légende doit donc toujours distinguer ce qui est mesuré, ce qui est inféré et ce qui est illustratif. L'Anatomie est la meilleure planche possible de la carte psycho-neurale ; elle ne saurait être la trame de tout."));
bodyChildren.push(figure("/home/z/my-project/research/shot_D2.png"));
bodyChildren.push(caption("Figure 5 — Variante D : planche première de l'atlas cognitif — anatomie décisionnelle légendée, hachures, notices techniques et avertissement de modèle."));

bodyChildren.push(h2("5.5 Direction E — La Gazette"));
bodyChildren.push(body("Le concept : INFINITUM paraît en quotidien de l'intelligence judiciaire, sur le registre des grands journaux financiers — titre en caractères hauts, papier saumon, colonnes serrées, filets noirs. Chaque juge y a sa cotation du jour comme une valeur cotée, l'agenda de séance publie les échéances réelles — la reprise de session au premier lundi d'octobre, la publication des ordonnances du vendredi — et la une raconte, en prose de presse d'autorité, l'actualité calculée du monde du droit. Le vocabulaire visuel du Financial Times, documenté dans son vocabulaire public de graphiques, fournit la discipline : un type de figure pour un type de message."));
bodyChildren.push(body("Ses forces : la familiarité de la presse d'autorité, un rythme éditorial qui donne envie de revenir — précieux pour une vitrine — et un cadre naturel pour le Radar temps réel et la veille. Ses risques : la métaphore marchande peut trivialiser la fonction judiciaire — coter un juge comme un titre financier demande d'être redéfini avec précision sur des mesures réelles et expliquées ; la fraîcheur éditoriale exige une production continue, ce qui est un engagement ; et la forme journal vieillit mal pour la consultation de fond. Le verdict : une page d'accueil et une rubrique remarquables, pas une architecture de fonds."));
bodyChildren.push(figure("/home/z/my-project/research/shot_E2.png"));
bodyChildren.push(caption("Figure 6 — Variante E : la une du quotidien — cotation du jour, historique de dissidences en attente du moteur, agenda de séance réel."));

bodyChildren.push(h2("5.6 Lecture comparée"));
bodyChildren.push(tableTitle("Tableau 2 — Comparaison des cinq directions au regard des garanties du projet"));
bodyChildren.push(makeTable(
  ["Direction", "Métaphore mère", "Atout majeur", "Risque majeur", "Affectation recommandée"],
  [
    ["A — L'Encyclopédie", "La connaissance publique", "Familiarité universelle, dignité savante, extensibilité infinie", "Neutralité à défendre face aux mesures sensibles", "Trame maîtresse de la vitrine"],
    ["B — Le Dossier", "La procédure elle-même", "Nativeness juridique totale, dramaturgie du feuilletage", "Connotation d'enquête sur personne vivante", "Export d'étude, archives téléchargeables"],
    ["C — L'Observatoire", "L'observation continue", "Merveille visuel, données temporelles réelles", "Dérive décorative, lecture radiale difficile", "Planches : précédents, vues d'ensemble"],
    ["D — L'Anatomie", "La science du jugement", "Incarnation parfaite du module psycho-neural", "Sensibilité éthique de la dissection", "Planches : carte psycho-neurale"],
    ["E — La Gazette", "La presse d'autorité", "Rythme éditorial, familiarité du quotidien", "Métaphore marchande à redéfinir", "Page d'accueil, radar, veille"],
  ],
  [18, 18, 24, 22, 18],
  { boldFirstCol: true }
));
bodyChildren.push(lead("La lecture comparée fait apparaître que le choix n'a pas à être exclusif. Les cinq métaphores ne s'affrontent pas sur le même terrain : l'une sait classer, l'autre archiver, la troisième observer, la quatrième disséquer, la cinquième raconter. La recommandation qui suit organise leur collaboration au lieu de les départager."));

// ===== 6. Recommandation =====
bodyChildren.push(h1("6. Recommandation — l'Encyclopédie pour trame, les planches pour les modules"));
bodyChildren.push(h2("6.1 Le principe : articles et planches"));
bodyChildren.push(body("L'Encyclopédie historique ne fut pas seulement une suite de volumes de texte : ses éditeurs publièrent onze volumes de planches gravées, montrant les métiers, les machines et les instruments que le texte ne pouvait que décrire. Cette architecture double — des articles pour dire, des planches pour montrer — est exactement la structure dont la vitrine INFINITUM a besoin. Chaque entité du monde judiciaire dispose ainsi d'un article savant, qui porte les faits sourcés, la notice d'autorité et les renvois ; et chaque module analytique dispose d'une planche, c'est-à-dire d'une visualisation de plein droit, dans le registre graphique que la direction C ou D a démontré."));
bodyChildren.push(body("Concrètement, la navigation repose sur le système des connaissances : entités (juges, avocats, juridictions, affaires, doctrines) et analyses (les neuf modules). Un article de juge s'ouvre sur le chapeau factuel et la notice d'autorité ; chaque module s'y atteint comme on tourne une planche : la carte psycho-neurale en gravure anatomique légendée, le réseau des précédents en carte céleste des autorités citées, la matrice des faiblesses en tableau synoptique, la carte thermique des biais en planche statistique, la projection Monte-Carlo en table de projection avec intervalles et hypothèses affichées, le spectre auditif en portée des cadences d'audience, la chronologie cognitive en frise savante, le radar temps réel en fenêtre d'observation datée, le bouclier comparatif en tableau comparatif de notices. La Gazette fournit la page d'accueil et la rubrique de veille ; le Dossier fournit l'export d'une étude complète en document de greffe téléchargeable. Les cinq directions du prototype sont ainsi toutes employées, chacune à sa juste place."));
bodyChildren.push(h2("6.2 Correspondance des neuf modules"));
bodyChildren.push(tableTitle("Tableau 3 — Les neuf modules dans l'architecture articles et planches"));
bodyChildren.push(makeTable(
  ["Module", "Forme dans la vitrine", "Registre visuel"],
  [
    ["I. Carte psycho-neurale", "Planche anatomique légendée de l'article", "Gravure claire, structures numérotées, légende savante"],
    ["II. Matrice des faiblesses", "Tableau synoptique de l'article", "Table à filets, cellules sourcées"],
    ["III. Carte thermique des biais", "Planche statistique", "Échelle sobre à deux couleurs, axes nommés"],
    ["IV. Projection Monte-Carlo", "Table de projection", "Intervalles, hypothèses et effectifs affichés"],
    ["V. Spectre auditif", "Portée savante", "Cadences d'audience en portée musicale annotée"],
    ["VI. Réseau des précédents", "Carte céleste des autorités", "Astres, orbites d'ancienneté, constellations"],
    ["VII. Chronologie cognitive", "Frise savante", "Jalons datés et sourcés"],
    ["VIII. Radar temps réel", "Fenêtre d'observation", "Éphémérides, datation visible, veille"],
    ["IX. Bouclier comparatif", "Tableau comparatif de notices", "Notices alignées, différences signalées"],
  ],
  [26, 37, 37],
  { boldFirstCol: true }
));
bodyChildren.push(h2("6.3 Conformité aux règles du projet"));
bodyChildren.push(body("La solution recommandée satisfait les six garanties du chapitre 2, une à une. La lecture seule est native : une encyclopédie ne demande rien à son lecteur. Le zéro simulacre est architectural : notes, provenances, errata et champs vides explicitement en attente du moteur réel — le marqueur distinctif expérimenté dans le prototype devient un composant à part entière du design system. Le thème clair et sobre est celui du papier, de l'encre et de la gravure, avec la palette bois juridique validée par le présent rapport. L'extensibilité infinie est la propriété même d'un système des connaissances : tout ce qui existera demain dans le monde du droit est un article de plus, une planche de plus. Les neuf modules conservent leur nature propre au lieu d'être aplatis en vignettes. Enfin, la familiarité que jMail avait fait la preuve de reste au cœur du dispositif — mais c'est désormais la familiarité du droit lui-même : le dossier, la notice, la planche, la gazette. INFINITUM ne déguise plus le droit en messagerie ; il habille la connaissance du monde judiciaire dans les vêtements que le monde du droit a lui-même inventés."));

// ===== 7. Feuille de route =====
bodyChildren.push(h1("7. Feuille de route suivante"));
bodyChildren.push(body("La feuille de route traduit la recommandation en séquence d'exécution. Chaque étape est franchissable et vérifiable ; aucune ne dépend d'une donnée simulée, et la vitrine publique ne s'ouvre qu'une fois le moteur réel alimenté."));
bodyChildren.push(numbered("rm1", "Ouvrir le prototype livré, visiter les six vues, trancher la direction avant le 5 septembre 2026 — le trancher seul ou dire quelle combinaison retenir.", "Décision. "));
bodyChildren.push(numbered("rm1", "Initialiser le monorepo INFINITUM sur la base archify, avec la structure de modules légo validée en amont du projet.", "Socle. "));
bodyChildren.push(numbered("rm1", "Constituer le design system de la vitrine : palette bois juridique claire, typographie d'autorité, composants notice, article, planche, marqueur d'attente du moteur, appareil de provenance.", "Design system. "));
bodyChildren.push(numbered("rm1", "Brancher les sources réelles — CourtListener, Caselaw Access Project, registres officiels — avec couches de provenance bout en bout et clés dans l'environnement.", "Données. "));
bodyChildren.push(numbered("rm1", "Construire les modules d'analyse un à un, chacun avec sa planche et ses notices techniques ; publier les mesures réelles à mesure du calcul.", "Moteur. "));
bodyChildren.push(numbered("rm1", "Assembler la vitrine articles et planches, avec la Gazette en page d'accueil et le Dossier en export d'étude.", "Vitrine. "));
bodyChildren.push(numbered("rm1", "Passer l'audit éthique et juridique de publication : personnes publiques, exactitude, proportionnalité, avertissements méthodologiques.", "Audit. "));
bodyChildren.push(numbered("rm1", "Tenir le rapport d'état multi-agents du projet, avec sections accomplies et restant à faire, à jour à chaque étape franchie.", "Gouvernance. "));

// ===== 8. Annexe : sources =====
bodyChildren.push(h1("8. Annexe — sources en ligne consultées"));
bodyChildren.push(lead("Les références suivantes ont été consultées le 27 août 2026 lors de la recherche préparatoire. Elles couvrent les concurrents, les registres publics, les systèmes visuels de référence et les collections historiques qui ont nourri les cinq directions."));
bodyChildren.push(bullet("Lex Machina — LexisNexis : page produit et descriptions fonctionnelles (lexisnexis.com).", "Concurrence. "));
bodyChildren.push(bullet("Pre/Dicta : site officiel, guides et annonces ; LawNext, août 2025 : extension de la modélisation judiciaire, quinze millions d'affaires, cinquante à cent points par juge ; American Bar Association : approche comportementale.", "Concurrence. "));
bodyChildren.push(bullet("Harvey : site officiel et descriptions produit de l'assistant génératif pour cabinets (harvey.ai).", "Concurrence. "));
bodyChildren.push(bullet("SCOTUSblog : statistiques par session et couverture de la Cour suprême (scotusblog.com).", "Public. "));
bodyChildren.push(bullet("Commission on Judicial Performance de Californie : base publique de décisions disciplinaires (cjp.ca.gov) ; Colorado Office of Judicial Performance Evaluation (judicialperformance.colorado.gov) ; Judicial Performance Evaluation Commission de l'Utah (judges.utah.gov).", "Public. "));
bodyChildren.push(bullet("Caselaw Access Project, Harvard Law School (case.law) et CourtListener, Free Law Project (courtlistener.com) : collections jurisprudentielles publiques destinées au moteur.", "Données. "));
bodyChildren.push(bullet("Financial Times — Visual Vocabulary : système public de choix de graphiques (ft-interactive.github.io/visual-vocabulary) ; guide de visualisation de données de la Commission européenne.", "Design. "));
bodyChildren.push(bullet("National Library of Medicine — Historical Anatomies on the Web : atlas anatomiques historiques, grammaire visuelle des planches légendées (nlm.nih.gov).", "Design. "));
bodyChildren.push(bullet("Wikipedia — Manual of Style, Infoboxes : pattern éprouvé de notice de synthèse factuelle.", "Design. "));
// ---------- ASSEMBLAGE ----------
const numberingConfig = {
  config: [
    {
      reference: "rm1",
      levels: [{
        level: 0, format: LevelFormat.DECIMAL, text: "%1.",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }],
    },
  ],
};

function makeHeader() {
  return new Header({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "D8D2C9", space: 4 } },
      children: [new TextRun({ text: "INFINITUM — Rapport de direction UI : cinq métaphores pour la vitrine publique", size: 18, color: "808080", font: FONT })],
    })],
  });
}
function makeFooter() {
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "808080", font: FONT })],
    })],
  });
}

const coverConfig = {
  title: "Cinq métaphores pour la vitrine INFINITUM",
  subtitle: "Remplacer la forme jMail par une identité née du monde judiciaire : recherche en ligne, prototype comparatif et recommandation",
  englishLabel: "INFINITUM",
  metaLines: [
    "Projet : INFINITUM — analyse cognitive et comportementale du monde judiciaire",
    "Document : rapport de direction UI, version 1.0",
    "Auteur : Direction de la Vision",
    "Date : 27 août 2026",
  ],
  footerLeft: "Document de travail — diffusion projet",
  footerRight: "Août 2026",
  palette: COVER,
};

const tocChildren = [
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 480, after: 360 },
    children: [new TextRun({ text: "Table des matières", bold: true, size: 32, font: HFONT, color: P.primary })],
  }),
  new TableOfContents("Table des matières", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({
    spacing: { before: 200 },
    children: [new TextRun({
      text: "Note : cette table des matières est générée par champ Word. Après toute modification du document, faire un clic droit sur la table puis « Mettre à jour les champs » pour actualiser la pagination.",
      italics: true, size: 18, color: "888888", font: FONT,
    })],
  }),
  new Paragraph({ children: [new PageBreak()] }),
];

const doc = new Document({
  creator: "Direction de la Vision — INFINITUM",
  title: "INFINITUM — Rapport de direction UI : cinq métaphores pour la vitrine publique",
  styles: {
    default: {
      document: {
        run: { font: FONT, size: 24, color: P.body },
        paragraph: { spacing: { line: 312 } },
      },
      heading1: {
        run: { font: HFONT, size: 32, bold: true, color: P.primary },
        paragraph: { spacing: { before: 400, after: 160, line: 380 } },
      },
      heading2: {
        run: { font: HFONT, size: 28, bold: true, color: P.primary },
        paragraph: { spacing: { before: 280, after: 120, line: 340 } },
      },
      heading3: {
        run: { font: HFONT, size: 24, bold: true, color: P.primary },
        paragraph: { spacing: { before: 200, after: 100, line: 312 } },
      },
    },
  },
  numbering: numberingConfig,
  sections: [
    {
      properties: {
        page: { size: { width: 11906, height: 16838 }, margin: { top: 0, bottom: 0, left: 0, right: 0 } },
      },
      children: buildCoverR1(coverConfig),
    },
    {
      properties: {
        type: SectionType.NEXT_PAGE,
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 },
          pageNumbers: { start: 1, formatType: NumberFormat.UPPER_ROMAN },
        },
      },
      headers: { default: makeHeader() },
      footers: { default: makeFooter() },
      children: tocChildren,
    },
    {
      properties: {
        type: SectionType.NEXT_PAGE,
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1440, bottom: 1440, left: 1701, right: 1417 },
          pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL },
        },
      },
      headers: { default: makeHeader() },
      footers: { default: makeFooter() },
      children: bodyChildren,
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("/home/z/my-project/download/INFINITUM_Rapport_Direction_UI.docx", buf);
  console.log("OK — docx écrit :", buf.length, "octets");
}).catch((e) => { console.error("ERREUR :", e); process.exit(1); });
