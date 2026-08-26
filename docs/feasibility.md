# Feasibility — QLoRA fine-tuning on a free Colab T4

Every number below is a calculation, not a guess. Model assumed: Mistral-7B
(v0.1 architecture, 32 layers, hidden 4096, intermediate 14336, 32 query
heads, 8 KV heads). Llama-3-8B numbers are ~15% higher across the board.

## 1. Memory budget (why this fits on a 16 GB T4)

### 1.1 Base model in 4-bit NF4

7.2 B params × ~0.55 byte/param (4-bit weights + NF4 scales/zero-points
overhead, bitsandbytes packing) ≈ **3.9 GB**.

### 1.2 LoRA adapters, r = 16 on all 7 linear projections of every layer

Trainable parameters per layer (r × (fan_in + fan_out)):

| projection | shape | LoRA params |
|---|---|---|
| q_proj | 4096 → 4096 | 16×8192 = 131,072 |
| k_proj | 4096 → 1024 (GQA) | 16×5120 = 81,920 |
| v_proj | 4096 → 1024 (GQA) | 16×5120 = 81,920 |
| o_proj | 4096 → 4096 | 131,072 |
| gate_proj | 4096 → 14336 | 16×18432 = 294,912 |
| up_proj | 4096 → 14336 | 294,912 |
| down_proj | 14336 → 4096 | 294,912 |
| **per layer** | | **1,310,720** |
| **× 32 layers** | | **41.9 M trainable** |

Adapter memory (fp16 weights + fp16 grads + 2×fp32 AdamW moments):
42M × (2+2+8) bytes ≈ **0.5 GB**.

### 1.3 Activations, with gradient checkpointing (bsz 1, seq 2048)

Stored layer boundaries: 32 layers × 2048 tokens × 4096 hidden × 2 bytes
≈ 0.54 GB, plus recompute buffers and attention workspace ≈ **1.0 GB**.

### 1.4 Total

| component | GB |
|---|---|
| base model (4-bit) | 3.9 |
| adapters + optimizer | 0.5 |
| activations (checkpointed) | 1.0 |
| CUDA context + fragmentation | ~1.5 |
| **total** | **≈ 7.0 / 16** |

Headroom ≈ 9 GB → batch size 2–4 (via accumulation) or seq 4096 both fit.
No T4 out-of-memory risk at the protocol's settings (batch 8 effective,
seq 2048).

## 2. Wall-clock estimate

Throughput of QLoRA on T4 with checkpointing (no flash-attn on Turing
compute capability 7.5; memory-efficient attention instead): measured
ballpark **1,500–3,500 tokens/s**; we budget 2,500.

- Train tokens/epoch: 600 examples × ~1,600 tokens (≈1,400 in + ≈200 out)
  ≈ **0.96 M** → epoch ≈ 6.4 min → **3 epochs ≈ 20 min**, + optimizer and
  occasional eval ≈ **30–45 min**.
- Model download on Colab (≈50–100 MB/s): 4-bit prequantized snapshot
  ≈ 4.5 GB → **5–10 min** (prefer a prequantized repo; downloading 14 GB
  fp16 and quantizing on-device doubles this but still fits).
- **Experiment B total: ≈ 45–75 min** — comfortably inside a free Colab
  session (~4 h GPU). Two full reruns with different seeds still fit.

## 3. Experiment A (zero-shot) and C (cross-judge) cost

- A on 400 test cases: ~1,700 tokens generated per case (1,400 prompt +
  300 decoded at ~25–40 tok/s decode on T4) ≈ **12–20 s/case → 1.3–2.2 h**
  on a T4. Fits one session.
- C (400 cases × 10 judge profiles = 4,000 inferences): ≈ 13–22 h of T4
  decode — **too slow on free Colab**. Options, in preference order:
  1. restrict to a 100-case stratified subset × 10 profiles (≈ 3–5 h,
     two sessions), CI ±10 pp on the swap rate — acceptable for a first
     paper table;
  2. batched inference with `batch_size=8` and short outputs (≈4× speedup);
  3. an API-hosted open model for inference-only runs (cost ≈ a few
     dollars for the whole matrix) — keeps weights open, moves compute.

## 4. Storage

1,000 raw opinions ≈ 20 KB each ≈ **20 MB** raw; structured JSONL ≈ 3 MB;
final dataset (text + labels + evidence) < 100 MB total — fits the repo
once validated, or a GitHub release asset if we keep the repo lean.

## 5. Decision

Phase 4 (Experiment B) is feasible on free Colab T4 with margin. The only
genuinely constrained step is Experiment C at full scale; the protocol
already documents the subset fallback (`docs/protocol.md` §5).
