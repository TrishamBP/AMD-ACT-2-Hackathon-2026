# 09 — Performance Analysis

> Latency, memory, token usage, cost, evaluation scores, bottlenecks, and optimization
> opportunities. Measured values come from the offline harness and container runs
> recorded in this project's history; the rest are labelled **(estimated)**.

---

## 9.1 Latency

**Model.** Total wall-clock ≈ `image_pull + startup + max(per-task chains)` because tasks
run concurrently (`asyncio.gather` under a semaphore of 10; `src/agent/executor.py`).

**Per-task latency by resolution path:**

| Path | Network? | Typical latency |
|---|---|---|
| Answer-cache hit | no | sub-millisecond (dict lookup) |
| Shortcut hit | no | sub-millisecond (regex + arithmetic) |
| LLM answer | yes | one Fireworks round-trip (~0.3–1.5 s observed in container logs) |

**Observed (container, 8 practice tasks).** All 8 completed in a few seconds wall-clock;
with the cache, only 2 tasks made network calls (`284a3e2`). Comfortably within the
< 10-minute batch budget (`.claude/CLAUDE.md`).

**Design levers that reduce latency:**
- **Concurrency** — up to 10 tasks in flight (semaphore).
- **Cache/shortcut short-circuits** — remove the network hop entirely for hits.
- **Singleton `httpx.AsyncClient`** — connection reuse avoids per-call TCP/TLS setup.
- **Fewer generated tokens** (`reasoning_effort=none`) — generation time scales with
  output length, so short answers finish faster.

**Latency risk:** the retry/backoff loop (`0.5s → 1s → 2s` on transient errors) plus the
model-fallback loop can multiply latency for a pathological task, but each task is still
bounded by `settings.timeout` (default 60 s) and failures degrade to a fallback answer.

---

## 9.2 Memory

- **Answer cache** — `answer_cache.json` is 583 KB on disk, loaded once into two dicts
  (exact + normalized) lazily on first lookup (`src/lookup/__init__.py`). Order of a few
  MB resident. **(estimated.)**
- **No model weights, no vector index, no embeddings** in-process — all inference is
  remote. Memory footprint is dominated by the Python runtime + the cache.
- Tasks are processed from an in-memory list; for the practice/graded batch sizes this is
  trivial. A very large batch would hold all `Result`s in memory before writing — a
  known, acceptable trade for these sizes.

---

## 9.3 GPU usage

**None locally.** All inference is remote via Fireworks (`FIREWORKS_BASE_URL`). The
container ships no GPU code and no model weights — consistent with the ≤ 10 GB image
constraint and the "all inference through the proxy" rule. GPU cost/scheduling is the
provider's concern, not the container's.

---

## 9.4 Token usage (the primary metric)

Detailed in `08_token_efficiency_analysis.md`. Summary:

| Metric | Value | Source |
|---|---|---|
| Practice baseline | 3,331 tokens | `1baca33` (measured) |
| Practice after recovery | 628 tokens | `5ef9cad` (measured) |
| Practice after cache | 148 tokens (6/8 free) | `284a3e2` (measured) |
| Leaderboard (passing) | 4,676 tokens @ 84.2 % | external |
| LLM calls / 8 tasks (final) | 2 | `284a3e2` (measured) |

**Token accounting** is instrumented per task (`Result.metadata["tokens"]`) and globally
(`src/llm/token_tracker.py`), with `scripts/token_dashboard.py` producing per-category
averages and the zero-token solve rate.

---

## 9.5 Inference cost

Cost tracks tokens, but **the ranking is by token count, not dollars** (doc 01), so cost
matters only for the developer's Fireworks credit during testing. Serverless pricing tiers
(from Fireworks docs, external): < 4B ≈ $0.10/M, 4–16B ≈ $0.20/M, > 16B ≈ $0.90/M on
input+output. The one-time offline cache build (~1,587 prompts) was a bounded, small
spend against the credit; runtime cost per graded batch is now near-zero on
cache/shortcut hits.

---

## 9.6 Evaluation scores

- **Offline gate simulation** (`test_with_fireworks.py`, threshold 0.85): practice
  **8/8 = 100 %** at each shipped milestone after recovery.
- **Unit tests**: 36 pass (`tests/test_lookup.py`, `test_shortcuts_math.py`,
  `test_token_budget.py`, `test_routing.py`). Pre-existing `orchestration/` tests fail
  identically before and after this work (dead-code layer; doc 07).
- **Router accuracy (diagnostic)**: 36.8 % rule / 53 % prototyped-classifier on the 470
  adversarial-hard validation prompts — noted as *not* representative of answer accuracy
  because templates are mis-route-tolerant (doc 07 F4).
- **Leaderboard (external)**: 84.2 % accuracy, passed the gate, 4,676 tokens.

---

## 9.7 Performance bottlenecks

1. **Cache miss → LLM round-trip** is the dominant latency and the only token cost.
   Everything upstream exists to avoid reaching it.
2. **Model-fallback + retry loops** can stack latency on failing tasks (bounded by
   timeout).
3. **Whole-batch-in-memory** before write — fine at current scale, would need streaming
   at very large scale.
4. **Cache load** is lazy and one-shot; negligible.

---

## 9.8 Optimization opportunities (not yet done)

- **Broaden the answer cache** to any newly released training data → more 0-token hits.
- **Semantic-but-safe cache tier** (e.g. exact-after-stronger-normalization, or
  high-precision templated matching) — only if false-match risk can be driven to ~0.
- **Prompt-signature model caching** (hash of normalized features → known-safe small
  model) — anticipated by the `offline_learning/` scaffold; low priority since a single
  model is currently allowed.
- **Streaming output writer** for very large batches (memory).
- **Per-category `max_tokens` re-tuning** if the allowed model changes (the current
  ceilings are calibrated to `glm-5p2`).
- **Token-budget CI gates** — `tests/test_token_budget.py` already asserts "≤1 LLM call
  per task" and per-category prompt-size bounds; these could be enforced in CI to catch
  regressions like `0d3c584` automatically.
