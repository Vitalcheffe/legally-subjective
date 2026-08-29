# M3a — The structured challenger (results)

*Filed 2026-08-29 · transparent test · sealed 50 untouched*

## The question this milestone answers

Can we train yet? Two answers, both filed:

- **Structured conditions** (case metadata + votes): the data has been complete since the corpus freeze — **trained today, below.**
- **LLM conditions A/B/C** (zero-shot, persona, RAG): they need the opinion texts; M1.5 stands at 112/1778 (dripping at the free-token quota). **Not trainable yet — critical path.**

## Protocol

| Rule | Value |
|---|---|
| Rows | justice×case votes, coded SCDB direction (4569 total) |
| Train | OT2015..OT2019, sealed excluded (2314) |
| Test (transparent) | OT2020..OT2023, sealed excluded (1815) |
| Sealed 50 | excluded from train, every CV fold, and test |
| CV | GroupKFold(5), group = case |
| Features | issue area, lower-court disposition, term, log argument duration, justice identity (all pre-decision) |

## Results (transparent test)

| Model | CV (grouped) | Test all rows | Test on B4 rows | McNemar vs B4 | Brier |
|---|---|---|---|---|---|
| M3a-LR | 56.2% | 58.3% [56.0; 60.5] | 58.6% | +199/−267, p=0.0019 | 0.240 |
| M3a-IX | 57.1% | 59.9% [57.6; 62.1] | 60.4% | +182/−223, p=0.0467 | 0.235 |
| M3a-GB | 56.1% | 58.8% [56.5; 61.0] | 59.8% | +153/−203, p=0.0093 | 0.240 |

| B4 (per-justice ideology), same rows | — | — | **63.1%** [60.6; 65.5] | reference | — |

## Reading

1. Justice identity is the dominant stable signal: B4 (each justice's modal train direction) scores 63.1% on the same rows.
2. Case context (issue area, lower-court disposition, term, argument length) adds no stable generalization across the time split: every structured challenger lands 58-61%, significantly below B4 by McNemar.
3. Interactions (justice×issue) recover part of the signal (60.6%) — justices do specialize by domain — but not enough to clear the bar at this sample size.
4. Consequence for the roadmap: if 63.7% is beatable at vote level, the signal must live in the TEXT of the case and the opinions — conditions A/B/C. M1.5 completion and the M3 LLM conditions are the critical path, not more metadata.

## Ablation (grouped CV on train)

| Features | CV accuracy |
|---|---|
| drop_issue | 57.9% |
| drop_lc | 56.7% |
| drop_term | 56.5% |
| drop_dur | 56.1% |
| drop_justice | 47.6% |
| full | 56.2% |
