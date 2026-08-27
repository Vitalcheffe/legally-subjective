# Legally Subjective

**Subjectivity, measured.** The open standard for the measured identity of legal actors.

The ambition: the **Manhattan Project of Law** — from the first public data
byte to a system that predicts verdicts, profiles each judge's brain,
simulates "one door down", discovers its own variables, and survives human
validation. The quality/time ratio is infinite: if a phase takes three
months to gain 1% precision, we take the three months.

- The roadmap: [archives/manhattan-roadmap.md](archives/manhattan-roadmap.md) — the 8 phases, the gates, the dependency tree
- The standard: [standards/LS-1.0.md](standards/LS-1.0.md) — the Subjectivity Fingerprint
- Phase 1 (Model A vs Model B): [phase1/](phase1/) — 1,677 real criminal appeals collected, 600/400 split, golden-tested pipeline, Colab notebook
- The engine: [core/](core/) — pure Python, deterministic, zero fabrication
- The window: [web/](web/) — static, 0 EUR/month, prints like a filing

## Zero-fabrication law
Every number traces to a public source URI. Missing data is rendered as missing.
Re-run the build on identical sources: you get bit-identical dockets.

## Reproduce
    git clone <repo> && cd legally-subjective
    make setup   # installs kernel + site
    make build   # ingest -> compute -> file dockets -> export site

License: AGPL-3.0. We fabricate nothing.
