# État du scan bulk M1.5 (voie B, sans token)

Copies de sécurité de `data/raw/opinion_texts/` (gitignored) :
- `segments.json` — quels segments du bulk S3 2026-06-30 (54,56 Go) sont faits
- `seg_NNN.found.jsonl` — opinions extraites par segment (schéma du drip)

En cas de reset environnement : recopier vers `data/raw/opinion_texts/`
et relancer `python3 scripts/m15_bulk_segments.py --rounds 99`.
