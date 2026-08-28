# Ressources — données juridiques publiques

Le pipeline de ce projet (`scripts/`) est générique : changer le `court_id`
suffit en principe à changer de juridiction. Cette carte des sources publiques
existe pour deux raisons : permettre à quiconque de **répliquer** l'expérience
ailleurs, et préparer les **extensions** éventuelles (cours d'appel fédérales,
autres cours suprêmes). Elle a été initiée à partir d'une liste suggérée par un
contributeur et est maintenue par le projet.

Critères d'inclusion : accès **gratuit**, données **publiques**, disponibilité
**programmatique** raisonnable (API, bulk ou scrape loyal). Ce document est
informatif — chaque réutilisation doit vérifier elle-même la licence et les
conditions de la source.

## Ce que ce projet utilise

| Source | Rôle ici |
|---|---|
| [CourtListener](https://www.courtlistener.com) (Free Law Project) | Dockets, opinions, plaidoiries audio + transcriptions. Fichiers bulk + API REST v4 (token gratuit). |
| [Supreme Court Database](http://scdb.wustl.edu) (Washington University in St. Louis) | Verdict au sol : vote de chaque juge, direction de la décision, traitement (édition 2025_01, format « justice-centered »). |
| [Oyez](https://www.oyez.org) (IIT Chicago-Kent) | Résumés d'affaires et plaidoiries ; complément de contrôle. |
| Scores de Martin–Quinn | Mesure d'idéologie par juge et par mandat (utilisée par la baseline B4). |

## États-Unis — au-delà de la Cour suprême

- [Caselaw Access Project](https://case.law) (Harvard) — ~6,7 millions de
  décisions étatiales et fédérales historiques, OCRisé, API JSON. Inestimable
  pour les cours d'appel et l'histoire du droit.
- [Pile of Law](https://huggingface.co/datasets/pile-of-law/pile-of-law) —
  grand corpus juridique libre (contrats, lois, jurisprudence) pour l'entraînement.
- [govinfo](https://www.govinfo.gov) — Code des États-Unis, Federal Register,
  CFR, décisions publiées officiellement.
- [RECAP](https://www.courtlistener.com/recap/) (via CourtListener) — archives
  libres des documents PACER des cours fédérales.
- [Federal Judicial Center](https://www.fjc.gov) — statistiques judiciaires
  fédérales agrégées.

## Jeux de données et modèles NLP juridique

- [LexGLUE](https://github.com/coastalcph/lex-glue) — batterie de référence
  multi-tâches pour le NLP juridique (classification d'opinions, similarité,
  etc.).
- [CUAD](https://www.atticusprojectai.org/cuad) — compréhension de contrats
  (extraction de clauses à risque), benchmark public.
- [LEGAL-BERT](https://huggingface.co/nlpaueb/legal-bert-base-uncased) et
  [CaseLaw-BERT](https://huggingface.co/reglab/case-law-bert) — modèles de
  langue pré-entraînés sur du texte juridique.
- Corpora CEDH (Chalkidis et al.) — décisions de la Cour européenne des
  droits de l'homme étiquetées pour la prédiction de violation.
- [MultiLegalPile](https://huggingface.co/joelniklaus/Multi_Legal_Pile) —
  corpus multilingue multi-juridictions pour le pré-entraînement.

## Europe et cours internationales

- [EUR-Lex](https://eur-lex.europa.eu) — droit de l'Union européenne intégral,
  téléchargeable en masse, multilingue.
- [CURIA](https://curia.europa.eu) — jurisprudence de la Cour de justice de
  l'UE (CJUE) ; publications quotidiennes en masse.
- [HUDOC](https://hudoc.echr.coe.int) — base complète de la Cour européenne
  des droits de l'homme, export possible.
- [Légifrance](https://www.legifrance.gouv.fr) — droit français (lois,
  jurisprudence des cours suprêmes et administratives), API ouverte sur
  inscription.
- Royaume-Uni : [legislation.gov.uk](https://www.legislation.gov.uk) et
  [Find Case Law](https://caselaw.nationalarchives.gov.uk) (National
  Archives) — jugements des cours supérieures en formats ouverts.
- Allemagne : [rechtsprechung-im-internet.de](https://www.rechtsprechung-im-internet.de)
  et [gesetze-im-internet.de](https://www.gesetze-im-internet.de) —
  jurisprudence et textes de loi officiels.
- Pays-Bas : [rechtspraak.nl](https://www.rechtspraak.nl) — jugements avec
  API publique.
- Espagne : [CENDOJ](https://www.poderjudicial.es/search/) — répertoire
  officiel de jurisprudence.
- Italie : [Italgiure](https://www.italgiure.giustizia.it) — jurisprudence de
  la Cassation et des cours italiennes.

## Common law ailleurs

- [CanLII](https://www.canlii.org) (Canada) — référence canadienne, accès
  public très complet.
- [AustLII](http://www.austlii.edu.au) et [Jade](https://jade.io)
  (Australie) — jurisprudence australienne ; Jade offre un accès
  programmatique pratique.
- [NZLII](https://www.nzlii.org) (Nouvelle-Zélande).
- [SAFLII](https://www.saflii.org) (Afrique australe) et
  [Kenya Law](https://new.kenyalaw.org) (Kenya) — jurisprudence africaine.
- [Indian Kanoon](https://indiankanoon.org) (Inde) — jugements indiens
  indexés et consultables librement.

## Asie et Amériques

- [China Judgements Online](https://wenshu.court.gov.cn) (中国裁判文书网) —
  jugements chinois (accès contrôlé, volume énorme mais restreint ces
  dernières années).
- [Courts of Japan](https://www.courts.go.jp) — jugements japonais,
  téléchargement en masse proposé.
- [STF](https://jurisprudencia.stf.jus.br) (Brésil) — jurisprudence du
  Supremo Tribunal Federal, API publique.

## Mises en garde héritées de M1

Notre propre collecte a appris trois choses que toute réplication devrait
savoir d'avance :

1. **Les quotas existent** — le token gratuit CourtListener est généreux mais
   épuisable ; prévoir des collectes résumables avec état sur disque (voir
   `scripts/fetch_opinion_texts.py`).
2. **Les archives bulk bougent** — fichiers tronqués, couvertures partielles ;
   tout écart mesuré doit être documenté (voir `stats_v1.json`, notes).
3. **La double source vaut de l'or** — le croisement CourtListener × SCDB a
   révélé et corrigé des erreurs qu'aucune des deux sources n'aurait signalée
   seule. Choisir tôt une seconde source indépendante comme verdict au sol.
