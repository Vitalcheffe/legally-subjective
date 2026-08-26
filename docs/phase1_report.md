# Rapport de Phase 1 — Initialisation technique

Date : 26 août 2026 · Auteur : pipeline Legally Subjective (exécution
complète, journalisée dans `data/sample/FETCH_LOG.json`)

Ce rapport documente ce qui a été vérifié, construit et mesuré, avec les
sorties brutes. Conforme au manifeste : aucun chiffre non reproductible.

## 1. Accès aux sources de données — résultats bruts

### 1.1 Caselaw Access Project (case.law) — Fermé

Le plan initial reposait sur l'API `api.case.law`. Vérification live :

```
$ curl -s -o /dev/null -w "%{http_code} -> %{redirect_url}\n" https://api.case.law/v1/
301 -> https://case.law/docs/
```

Toutes les requêtes vers `api.case.law` redirigent vers la documentation.
Cause confirmée par les sources publiques (case.law, page d'accueil) :

> « the CAP API and search tool were sunset on September 5, 2024. All use
> restrictions for the Caselaw Access Project's data have officially been
> lifted. »

**Décision : pivot vers CourtListener** (Free Law Project), qui a absorbé
la couverture du corpus CAP. Le pivot et sa justification sont documentés
dans `docs/precedents.md` §3.

### 1.2 CourtListener v4 — partiellement ouvert

| endpoint | accès anonyme | résultat |
|---|---|---|
| `GET /api/rest/v4/opinions/` | non | `401 {"detail":"Authentication credentials were not provided."}` |
| `GET /api/rest/v4/dockets/` | non | `401` |
| `GET /api/rest/v4/search/?q=...&type=o&court=nyappdiv` | **oui** | `200`, compte + métadonnées + URLs sources |

La recherche fonctionne en anonyme ; les endpoints REST d'objets exigent
un token gratuit (inscription). Le collecteur utilise la recherche
anonyme et gère le token optionnel via `COURTLISTENER_TOKEN`
(`config.json`, `courtlistener.auth_token_env`).

### 1.3 Documents officiels New York — publics, avec pièges documentés

- Domaine historique `www.courts.state.ny.us` : **403** partout (domaine
  migré) → réécriture automatique vers `www.nycourts.gov`, même chemin :
  vérifié `200`.
- Anciennes décisions du First Department (2014 et avant) : PDFs scannés
  sans couche texte, serveurs officiels morts → la porte de vérification
  criminelle (recherche de mots-clés) ne peut pas s'appliquer ; ces cas
  sont écartés par le pipeline et tracés dans le journal.
- `storage.courtlistener.com` (copies publiques) : accessible, utilisé
  comme repli documenté.

### 1.4 Volumétrie disponible (sondage « judgment of conviction », nyappdiv)

| année | résultats | URL de document présentes (5 premiers) |
|---|---|---|
| 2011 | 249 | 0/5 |
| 2012 | 314 | 2/5 |
| 2013 | 467 | 0/5 |
| 2014 | 517 | 5/5 (PDFs scannés) |
| 2015 | 348 | 0/5 |
| 2016 | 259 | oui |
| 2017 | 245 | oui |
| 2018 | 213 | oui |
| 2019 | 198 | oui |
| 2020 | 186 | oui |

≈ 2 996 décisions publiées pour cette seule requête sur 2011-2020 ; la
cible de 1 000 cas (protocole §2.3) est donc atteignable en privilégiant
2016-2020 et en traitant le stock PDF (OCR) pour les années antérieures —
décision de Phase 2.

## 2. Échantillon de 5 cas — vérifié à la main (R10)

Collecte stratifiée (1 cas par fenêtre 2016/2017/2018/2019/2020, ordre
`dateFiled asc`, première décision passant la porte criminelle). Les cinq
textes ont été lus intégralement avant validation.

| # | affaire | date | département | panel | disposition |
|---|---|---|---|---|---|
| 1 | People v. Rodriguez (135 A.D.3d 456) | 2016-01-07 | 1er | Tom, J.P. ; Mazzarelli, Richter, Gische | confirmée (affirmed) |
| 2 | People v. Janelle (2017 NY Slip Op 00188) | 2017-01-11 | 2e | Leventhal, J.P. ; Cohen, Miller, Connolly | infirmée (reversed) |
| 3 | People v. Baxter (2018 NY Slip Op 00198) | 2018-01-11 | 3e | Garry, P.J. (auteur) ; Lynch, Clark, Aarons, Pritzker | confirmée |
| 4 | People v. Alexander (2019 NY Slip Op 00135) | 2019-01-09 | 2e | Balkin, J.P. ; Chambers, Cohen, Miller | infirmée |
| 5 | People v. Lawrence (2020 NY Slip Op 00004) | 2020-01-02 | 3e | Lynch, J.P. ; Devine (auteur), Clark, Mulvey, Reynolds Fitzgerald | infirmée |

Diversité obtenue : 2 confirmations / 3 infirmations ; 3 départements ;
types de crimes (extraits) : sexual, drug, property, violent, drug ;
genre du prévenu (mentionné dans le texte) : 4 hommes, 1 femme.

Extrait brut du journal de provenance (36 requêtes au total, 22×HTTP 200,
14×HTTP 403 documentant le piège du domaine historique) :

```
{"purpose": "search:2016", "status": 200, ...}
{"purpose": "document:4337785", "url": "http://www.courts.state.ny.us/...", "status": 403}
{"purpose": "document:4337785", "url": "https://www.nycourts.gov/reporter/3dseries/2017/2017_00188.htm", "status": 200, "bytes": 7449}
```

Chaque document est stocké avec son sha256 (`data/sample/cases.jsonl`).

## 3. Extraction structurée — méthode et résultats

Deux étages, chacun avec preuve (R8) :

1. **Règles déterministes** (`preprocess.py`) : panel + président (ligne
   de concordance + signature d'auteur), disposition (formule décrétale
   « Ordered that… », recital inline du 1er Dept, formule de
   radiation — priorité décrétale, garde anti-citations « see … »),
   chef d'accusation (recital « convicting … of … »), juges du premier
   degré (recitals « (Nom, J.) »).
2. **LLM** (prompt figé, `llm_extractor.py`) : résumé factuel **masqué de
   l'issue**, type de crime, genre, et contre-vérification indépendante
   de la disposition.

**Validation croisée : 5/5 accords** règle vs LLM sur la disposition.
Exemple de champ avec preuve (Alexander) :

```json
"disposition": {
  "primary": "reversed",
  "primary_evidence": "Ordered that the judgment is reversed, on the law,
    and the matter is remitted to the Supreme Court, Queens County, for a
    new trial.",
  "primary_method": "rule:decretal",
  "llm_check": "reversed",
  "agreement": true
}
```

Exemple de résumé factuel masqué (Alexander) — l'issue n'y figure pas :

> « The defendant Diamonte Alexander was convicted by a jury in Supreme
> Court, Queens County, of manslaughter in the first degree and criminal
> possession of a weapon in the second degree (two counts). […] The appeal
> challenges the trial court's handling of a Batson challenge regarding
> the prosecutor's peremptory challenge to a prospective black juror. »

Le masquage repose sur l'instruction du prompt ; il sera re-vérifié à la
main sur un échantillon avant la Phase 3 (le protocole exige la
validation humaine de l'entrée modèle).

## 4. Datasets prétraités existants (mission, point 4)

Recherche effectuée (août 2026). Ce qui existe, vérifié :

- **AUEB-NLP/ecthr_cases** (Hugging Face) — 11k cas CEDH, texte + labels
  binaires par article violé ;
- **CAIL2018** — 2,6M+ cas criminels chinois, benchmark de prédiction de
  jugement ;
- **coastalcph/fairlex** — benchmarks d'équité sur plusieurs corpus
  juridiques ;
- **US Supreme Court Database** — ≈250 variables codées par cas, votes
  individuels des juges.

Ce qui n'existe nulle part (et constitue notre contribution) : un dataset
d'appels criminels **américains** texte intégral + issue + **identité du
panel de juges**, l'expérience contrefactuelle du changement de juge, et
le test de transmission des biais A-vs-B. Aucun dataset prétraité
n'étant réutilisable tel quel, le pipeline de preprocessing est bien
nécessaire — il est construit et validé.

## 5. Faisabilité du fine-tuning (mission, point 5)

Calcul complet dans `docs/feasibility.md` (chaque chiffre dérivé) :

- **Mémoire QLoRA** (Mistral-7B, r=16 sur les 7 projections) :
  3,9 Go (base 4-bit) + 0,5 Go (adaptateurs+optimiseur) + 1,0 Go
  (activations checkpointées) + ~1,5 Go (contexte CUDA) ≈ **7,0 Go sur
  16** → marge confortable.
- **Temps** : 0,96M tokens/époque ÷ ~2 500 tokens/s ≈ 6,4 min/époque ;
  3 époques + évaluations + téléchargement ≈ **45-75 min par session
  Colab gratuite**.
- **Contrainte réelle** : l'expérience croisée à pleine échelle
  (400 cas × 10 profils) ≈ 13-22 h de T4 → repli documenté sur un
  sous-ensemble stratifié de 100 cas (protocole §5, option 1).

## 6. Écarts par rapport au plan initial

1. **Source de données** : case.law (fermée) → CourtListener + opinions
   officielles. Journaux à l'appui (§1).
2. **Découpe train/test** : 800/200 (draft) → **600/400** recommandé,
   car l'analyse de puissance montre que 200 cas de test ne détectent pas
   un gain de +5 points (puissance 0,37) ; 400 le font à 0,99 pour +10
   points et 0,70 pour +5 (`docs/protocol.md` §2.3, tableau régénérable
   par script).
3. **Fenêtres d'échantillon** : 2011-2020 prévu → 2016-2020 réalisé, à
   cause des PDFs scannés non textuels de 2011-2015 (documenté §1.4 ;
   extension OCR = décision de Phase 2).

## 7. Prochaines étapes (Phase 2)

1. Collecter les ~1 000 cas (2016-2020 en priorité), checkpoint tous les
   50 cas, journal complet.
2. Validation manuelle d'un échantillon aléatoire de 30 cas (R10).
3. Mesurer le taux de base réel des issues (déséquilibre des classes) et
   figer les pondérations de perte (protocole §4).
4. Décider du traitement OCR du stock 2011-2015.
