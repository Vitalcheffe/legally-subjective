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
