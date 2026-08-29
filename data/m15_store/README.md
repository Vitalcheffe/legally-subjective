# data/m15_store/ — clôture M1.5 via API CourtListener

Provenance des textes d'opinions, étape finale de M1.5.

## Répertoires

- `api/` — réponses brutes de l'API v4 (`resp_*.json`), un fichier par lot
  `id__in` (100 ids). État du fetch : `api/state.json` (compteur de budget,
  ids déjà récupérés, resumable). Le token n'est JAMAIS commité (hors repo,
  à `/home/z/my-project/legally-subjective/.cl_token`).
- `final/` — sortie canonique :
  - `opinion_texts_v2.jsonl.gz` — un enregistrement par opinion du corpus
    (1778), champs : `opinion_id, plain_text, n_chars, source, type, term,
    cluster_id, case_name, date_filed, author_id, per_curiam, joined_by_ids`.
  - `stats.json` — couverture par terme/type, par source, ids manquants.

## Priorité des sources (merge)

1. `api:plain_text` — texte natif de l'API (canonique CourtListener)
2. `api:html|xml_harvard|…` — champ alternatif, converti en texte brut
   (`html_to_text`, bs4, script/style retirés)
3. `legacy:*` — store des voies B (bulk S3) et C (slip PDFs), conservé
   comme repli quand l'API n'a pas de texte pour l'id

## Miroir builder

`m15_api_merge.py` réécrit aussi `data/raw/opinion_texts/opinions_text.jsonl.gz`
(schéma `id/plain_text` compris par `m3_build_datasets.py`). Ce miroir est
gitignoré (comme tout `data/raw/`) — le fichier canonique est `final/…v2`.

## Chaîne de régénération

```
python3 scripts/m15_api_close.py          # fetch (resumable, budgeté)
python3 scripts/m15_api_merge.py          # fusion + stats
python3 scripts/m3_build_datasets.py      # personas (base)
python3 scripts/m3_augment_segments.py    # personas (+segments slip)
```

La chaîne a été validée par simulation complète (scripts/m15_sim_fake_api.py)
avant l'ouverture de la fenêtre de quota : branches plain_text/html/xml/
vide/hors-corpus/priorité-API toutes vérifiées, reproduction exacte des
personas (156 lignes) sur données réelles.
