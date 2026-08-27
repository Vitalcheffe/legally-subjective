# Legally Subjective

**Subjectivity, measured.** The open standard for the measured identity of legal actors.

- The standard: [standards/LS-1.0.md](standards/LS-1.0.md) — the Subjectivity Fingerprint
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
