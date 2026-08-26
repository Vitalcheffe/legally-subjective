# Vision — an infinite construction set

> The constitution (`MANIFEST.md`) fixes what must never change. This
> document maps what is *designed to change forever*. Both are load-
> bearing: a project that cannot grow dies of finish, and a project that
> cannot hold still dies of drift.

## 1. The premise

Every serious research project ends the same way: the last question
answered opens three new ones. Most projects handle this badly — either
they freeze (the dissertation is defended, the repo rots) or they
sprawl (the codebase becomes an archaeological site where nobody dares
delete anything). Legally Subjective is built around a third option:
**the pipeline is a construction set**. Capabilities are bricks. The
base plate is deliberately small. Nothing about the project's future
requires rewriting its past.

This is not an aesthetic preference. The research program — can a
model predict an appeal, does experience teach it, does the simulated
judge change the simulated verdict — is a *frame*, not a finite list.
Each phase answers one question and arms the next. Phase 2's corpus
makes Phase 3's baseline possible; Phase 3's errors tell us what Phase
4 must learn; Phase 4's fine-tuned model is the substrate of Phase 5's
counterfactual judges; Phase 5's judge profiles are the content of
Phase 6's public site. And then: other decades, other states, other
courts, other languages. The construction set is the answer to "what
comes after Phase 6?" — more bricks, not a new foundation.

## 2. The architecture is the strategy

The kernel (`scripts/lib/kernel.py`, ~200 deliberately boring lines)
defines exactly three things: a **Block** (a named, versioned,
single-purpose capability), a **Context** (config + repo + run
manifest), and **run** (execution with timing, manifest records, and
fail-fast semantics). Blocks live in `scripts/blocks/` as ordinary
modules exposing a `BLOCK` instance; the registry discovers them
automatically.

| block | stage | what it does |
|---|---|---|
| `source:courtlistener` | source | collect cases + documents (windows, gates, channels — all config) |
| `extract:structured` | extract | evidence-based fields: panel, disposition, charge, judges, facts |
| `validate:data` | validate | integrity gate: sha256, provenance, schema, secrets |
| `validate:select-human-sample` | validate | stratified R10 review instrument + worksheet |
| `analyze:base-rate` | analyze | class balance with Wilson CIs (the protocol's required measurement) |
| `analyze:power` | analyze | pre-registered McNemar sizing, re-runnable |

Pipelines are *data*, not code: an ordered list in `config.json`
(`"pipelines"`), each step a block name plus parameters. The CLI is
`python scripts/run_pipeline.py corpus-process`. Adding a capability
never touches the kernel, the CLIs, or any other block.

### Adding a brick — a worked example

The 2011–2015 NY decisions exist only as scanned PDFs (Phase 1
finding). Unlocking those ~1,800 cases is one new file,
`scripts/blocks/source_ocr.py`:

```python
BLOCK = Block(
    name="source:ocr",
    stage="source",
    version="0.1.0",
    description="OCR the scanned-PDF years (2011-2015) into text documents",
    run=_run,   # pdftotext/tesseract over cached PDFs, same record schema
)
```

Drop the file in, add `{"block": "source:ocr", "params": {...}}` to a
pipeline, done — the registry, the runner, the manifest, the fail-fast
semantics and the validation gates all apply to it automatically. The
same one-file pattern adds a jurisdiction, an experiment, a report, or
a new analysis. That is the whole growth mechanism, and it is
intentionally hard to make it richer: the moment adding a brick
requires touching the base plate, the project has started to die.

### The invariant that makes growth safe

An infinitely extendable pipeline is only honest if it cannot silently
rewrite its past. The **golden test**
(`scripts/tests/test_golden_sample.py`) pins the hand-verified 5-case
sample: any code path — CLI or block — must reproduce the committed
records' deterministic fields exactly, or the build fails. Growth adds
bricks; it never moves the floor.

## 3. Extension slots — the roadmap without an end

Each slot below is a dimension the project can grow along, the brick
that unlocks it, and what it buys the research. Nothing here is
speculative infrastructure: every slot maps to a question the protocol
already asks, or to a limitation `README.md` already admits.

**S1 — Time.** Backward: the OCR brick unlocks 2011–2015 (≈1,800 more
decisions, doubling the corpus without touching any other block).
Forward: re-running the collector annually extends the dataset with a
new window — the config already treats years as data, not code.

**S2 — Space.** Other jurisdictions are other source bricks plus
jurisdiction-specific extraction patterns (every state appellate court
publishes; CourtListener covers them). One state at a time, the
counterfactual-judge experiment (RQ3) gains cross-state contrast: does
the "judge lottery" measured in New York reproduce in California? That
comparison — same method, different legal culture — is a publishable
result on its own.

**S3 — Depth.** More fields per case: sentence lengths, counsel type,
prior appellate history, concurrent opinions. Each is one more
extractor pattern with its evidence sentence (R8), immediately
sliceable by the analysis bricks. Depth compounds: RQ4's bias analysis
gets sharper with every honest field added.

**S4 — Experiments.** Phases 3–5 are experiment bricks: prompt
calibration on a held-out split, zero-shot baseline (A), QLoRA
fine-tuning (B), judge profiles and the cross-judge counterfactual (C),
bias transmission (D). Each consumes the same corpus and writes
result artifacts the report bricks can cite. An experiment is a brick,
so experiments are removable, comparable, and re-runnable.

**S5 — Interfaces.** Phase 6 bricks: the public site (the "would you
have been guilty with another judge?" experience), the reproducible
notebook, the preprint generator. Interfaces are report-stage blocks
over the same artifacts — no separate codebase to rot.

**S6 — People.** The R10 instrument (stratified human review) is a
brick; the planned `validate:human-agreement` brick scores completed
worksheets. The law-partner review gate (MANIFEST §2) gets a queue, a
worksheet, and an audit trail instead of goodwill.

**S7 — Community.** Dataset releases with provenance, replication
instructions, and third-party bricks: an external contributor's
"source:california" or "extract:italian" follows the same contract.
The block contract is the collaboration contract.

## 4. What never changes

The fixed axles, per the constitution: no mock data (R1), no hidden
parameters (R2), no unverifiable claims (R3), clean history (R4), no
slop (R5), visible limitations (R6), the permanent disclaimer (R7),
evidence with every field (R8), reproducibility (R9), human validation
before scale (R10). The pre-registered protocol; the golden sample;
the honest status line in the README. A brick that violates any of
these is a bug, however well it runs.

## 5. The growth protocol

How a brick enters the project:

1. **Spec** — one paragraph: what question it answers or limitation it
   lifts, and where its evidence comes from.
2. **Implement** — one module in `scripts/blocks/`, parameters from
   config, output with provenance.
3. **Prove** — the golden test still passes; validation bricks still
   pass on existing datasets; new outputs carry evidence (R8).
4. **Commit** — atomic, conventional, telling the story (R4).
5. **Document** — a row in the block table, a line in the phase
   report, an honest status change if one is earned.

That loop is the project's metabolism. It is slow enough to be honest
and fast enough to never stall — which is what "never finished" has to
mean in practice.
