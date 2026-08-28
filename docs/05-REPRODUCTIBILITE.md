# Reproductibilité — reconstruire tout, vérifier chaque empreinte

## Philosophie

Chaque transformation de ce projet est un script court, déterministe, et
chaque entrée a une empreinte. La reproductibilité n'est pas une promesse,
c'est une propriété vérifiable :

- **Règle = prédicat** : chaque jeu de données est défini par un prédicat
  explicite (voir `stats_v1.json`, champ `corpus_rule`), pas par un état
  d'esprit.
- **Source = URL + SHA-256** : voir `data/raw/provenance/` et
  `stats_v1.json` (`source_sha256`).
- **Aléatoire = graine** : tout tirage (le scellé des 50 affaires 5-4)
  utilise une graine dérivée par hachage du matériel trié — reproductible par
  construction.

## Vérifier le corpus gelé (2 minutes)

```bash
python3 - <<'EOF'
import gzip, json, hashlib
stats = json.load(open('data/processed/stats_v1.json'))
print("règle :", stats['corpus_rule']['argued_window'])
print("affaires :", stats['n_cases'], "| opinions :", stats['n_opinions'])
print("scellé 5-4 :", stats['five_four_selection']['sealed_sha256'])
# revérifier le scellé depuis la liste
sel = stats['five_four_selection']['cases']
h = hashlib.sha256(json.dumps(sorted(sel)).encode()).hexdigest()
print("revérification :", h, "=> OK" if h == stats['five_four_selection']['sealed_sha256'] else "ERREUR")
n = sum(1 for _ in gzip.open('data/processed/corpus_cases_v1.jsonl.gz', 'rt'))
print("lignes corpus :", n, "=> OK" if n == stats['n_cases'] else "ERREUR")
EOF
```

## Reconstruire le corpus depuis zéro (~2 h, zéro euro)

Prérequis : Python 3.10+, ~10 Go d'espace disque, aucune clé API.

```bash
# 1. dockets SCOTUS (fichier bulk 5 Go, filtré en flux)
python3 scripts/bulk_download.py dockets-2026-06-30.csv.bz2 --budget 500
python3 scripts/segmented_filter.py scan --file data/raw/_bulk/dockets-2026-06-30.csv.bz2
python3 scripts/segmented_filter.py process --file data/raw/_bulk/dockets-2026-06-30.csv.bz2 \
    --keep-cols "id,date_argued,date_reargued,date_reargument_denied,case_name,case_name_short,docket_number,court_id,date_filed,date_terminated,source,nature_of_suit,jurisdiction_type,cause,panel_str,date_cert_granted,date_cert_denied,appeal_from_str,slug" \
    --prefilter "court_id=scotus" --budget 500   # relancer jusqu'à « done »
python3 scripts/segmented_filter.py finalize --file data/raw/_bulk/dockets-2026-06-30.csv.bz2 \
    --out scotus_dockets.jsonl.gz \
    --url "https://com-courtlistener-storage.s3.amazonaws.com/bulk-data/dockets-2026-06-30.csv.bz2" \
    --desc "court_id == 'scotus'"

# 2. plaidoiries (audio + transcriptions)
python3 scripts/bulk_download.py oral-arguments-2026-06-30.csv.bz2 --budget 300
python3 scripts/segmented_filter.py scan --file data/raw/_bulk/oral-arguments-2026-06-30.csv.bz2
python3 scripts/segmented_filter.py process --file data/raw/_bulk/oral-arguments-2026-06-30.csv.bz2 \
    --keep-cols "id,case_name,case_name_short,case_name_full,judges,docket_id,date_created,date_modified,sha1,download_url,duration,processing_complete,stt_status,stt_source,stt_transcript,source" \
    --prefilter-file data/raw/scotus_dockets.jsonl.gz --prefilter-key id --prefilter-col docket_id --budget 300
python3 scripts/segmented_filter.py finalize --file data/raw/_bulk/oral-arguments-2026-06-30.csv.bz2 \
    --out scotus_oral_arguments.jsonl.gz \
    --url "https://com-courtlistener-storage.s3.amazonaws.com/bulk-data/oral-arguments-2026-06-30.csv.bz2" \
    --desc "docket_id ∈ dockets SCOTUS"

# 3. SCDB (http, pas https — voir notes)
curl -L -o SCDB_2025_01_justiceCentered_Citation.csv.zip \
  "http://scdb.wustl.edu/_brickFiles/2025_01/SCDB_2025_01_justiceCentered_Citation.csv.zip"

# 4. grappes par l'API de recherche (anonyme, ~25 min)
python3 scripts/fetch_corpus_search.py        # relancer jusqu'à 550/550
python3 scripts/fetch_corpus_scdb_extra.py    # dockets SCDB complémentaires

# 5. assemblage + gel
python3 scripts/build_corpus.py
python3 scripts/m2_baselines.py
```

## Chaîne de traçabilité

```
S3 CourtListener ──(SHA-256)──> filtres segmentés ──> scotus_dockets.jsonl.gz ─┐
SCDB 2025_01 ─────(SHA-256)──> lecture directe ───────────────────────────────┤
API recherche v4 ─(SHA-256)──> corpus_search_results.jsonl.gz ─┐              ├─> build_corpus.py
Audio bulk ───────(SHA-256)──> filtre docket_id ────────────────┘              │
                                                                               v
                                              data/processed/corpus_*_v1.jsonl.gz + stats_v1.json
```

## Notes d'ingénierie (pour les curieux)

- **Fichiers bulk tronqués** : les `.csv.bz2` du 2026-06-30 sur S3 n'ont pas de
  marqueur de fin de flux bzip2. Le filtre segmenté détecte l'unité finale
  invalide et s'arrête proprement en consignant la position — voir
  `scripts/segmented_filter.py` (mode `process`, gestion `OSError`).
- **Filtre segmenté** : les fichiers bzip2 sont faits de blocs indépendants
  précédés de la magie 48 bits `0x314159265359`. Aux positions alignées sur un
  octet, un pseudo-flux `BZh9 + octets` se décompresse proprement : le fichier
  est donc découpé en unités redémarrant chacune un décompresseur frais —
  c'est ce qui permet de reprendre un filtrage de 5 Go par tranches de
  quelques minutes sans jamais perdre une ligne (la queue partielle de
  l'unité k est préfixée à l'unité k+1).
- **SCDB en http** : `scdb.wustl.edu` refuse https depuis certains réseaux ;
  l'empreinte SHA-256 du zip permet de vérifier l'intégrité du téléchargement.
- **Token API** : aucune étape ci-dessus ne nécessite de token. La collecte
  des **textes** d'opinions (M1.5) utilise le token CourtListener stocké dans
  `.env` (ignoré par git — vérifiez `git check-ignore .env`).

## Environnement

- Python 3.12 testé ; dépendances de la chaîne M1/M2 : aucune (bibliothèque
  standard uniquement).
- Les notebooks d'entraînement (M3, Colab gratuit) arriveront avec
  `requirements-colab.txt`.
