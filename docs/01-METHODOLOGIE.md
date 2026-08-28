# The Four Conditions and the Decisive Test

## The single question

Does a judge's *persona* — everything expressible in their public writing —
carry predictive signal for their *future* decisions? We isolate this question
with a four-condition design that shares everything except the thing being
tested.

## The conditions

### Condition A — Zero-shot

Llama 3 8B (unmodified base model, 4-bit quantized) receives a structured case
file: parties, question presented, posture, lower-court disposition, oral
argument excerpt. It must output a decision (affirm / reverse / vacate) and a
direction (conservative / liberal). No fine-tuning, no retrieval. This is the
"smart outsider" baseline: what a capable general model infers from the raw
record.

### Condition B — Persona (the heart of the experiment)

The same base model, fine-tuned with QLoRA on the *past* written output of a
single justice: majority opinions, dissents, concurrences — filtered to the
training window only. Tested on that justice's *future* cases (cases decided
after every document in the training set). Nine adapters, one per sitting
justice (La Chambre).

If condition B beats condition A on future cases *of the same justice*, the
persona is extractable from public text. If B equals A, the personality is not
in the data. Both outcomes publish.

### Condition C — Context (RAG)

The same base model with retrieval: at decision time, the model receives the
k most similar *prior* opinions of the Court (embedding similarity on the
question presented). This tests whether the predictive signal lives in the
precedent corpus rather than in the judge.

### Condition D — Statistics

The M2 baselines (majority class, always-conservative, always-reverse,
per-justice ideology priors). These bound what can be known without reading
anything at all.

## The decisive test

B > A on held-out future cases (McNemar's test on paired predictions,
α = 0.05, pre-registered) ⇒ persona is extractable.

B = A ⇒ the justice's individuality does not survive in public text. The
measure — with its confidence intervals — is itself the contribution.

## Anti-memorization discipline

A model trained on a judge's opinions could be recalling rather than
generalizing. We defend with four independent barriers:

1. **Temporal split**: every training document strictly precedes every test
   case (per-justice cutoffs, verified by date, not random shuffling).
2. **Capacity bottleneck**: QLoRA on a 4-bit 8B model with rank 16-64, 1-3
   epochs, early stopping on a validation loss floor. The adapter is too small
   to be a database.
3. **Min-k% probe**: per-token log-probability audit — memorized text shows
   anomalously high probability on low-surprise tokens. Reported per adapter.
4. **Cloze test**: the model completes masked spans from *training* opinions;
   high exact-recall indicates memorization and disqualifies the claim of
   generalization.

## Evaluation

- **Unit of analysis**: the case-level decision (direction + disposition),
  plus per-justice vote direction where SCDB provides ground truth.
- **Metrics**: accuracy with Wilson 95% intervals (never more than one
  decimal), Cohen's κ against the majority baseline, McNemar for paired
  conditions.
- **The final exam** (`docs/04-PROTOCOLE.md`): 50 sealed 5-4 cases, evaluated
  once, reported whatever the outcome.

## What we do NOT claim

We do not claim judges are replaceable, that law is "just politics", or that a
language model "understands" law. We measure how much of the publicly visible
record is predictive — no more, no less. See `docs/08-LIMITES.md`.
