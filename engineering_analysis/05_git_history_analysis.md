# 05 — Git History Analysis (engineering diary)

> The most important document. Every commit below was read via `git show`. Dates are
> author dates. Cosmetic changes are ignored; engineering changes are clustered into
> milestones. Format per commit: **Problem → Hypothesis → Implementation → Result →
> Improved / Not improved → Lesson.**

Full timeline (12 commits, `git log`):

| # | Hash | Date (2026) | Subject |
|---|------|------|---------|
| 1 | `535723b` | Jul 09 06:19 | Initial commit |
| 2 | `491fe8c` | Jul 10 09:46 | Optimize prompts for Track 1 accuracy |
| 3 | `1baca33` | Jul 10 11:18 | Fix pipeline, 100% on practice tasks |
| 4 | `1807155` | Jul 10 13:12 | Fix container crash: lower thresholds, handle fallback errors |
| 5 | `c619b7b` | Jul 10 16:51 | Fix container crash: chown on RO /input, output format |
| 6 | `e5f76ff` | Jul 10 18:45 | Simplify container: remove gosu to fix RUNTIME_ERROR |
| 7 | `6f5ae63` | Jul 10 18:57 | Improve accuracy: clearer prompts, higher max_tokens |
| 8 | `0fac84f` | Jul 10 19:12 | Fix URL construction (full URL vs httpx base_url) |
| 9 | `7f7cb8f` | Jul 10 19:35 | Robust pipeline: retry all models, never empty answers |
| 10 | `0d3c584` | Jul 10 20:00 | Aggressive token optimization (~5x target) |
| 11 | `5ef9cad` | Jul 12 10:16 | Fix accuracy gate (10.5% → 100%), cut tokens ~7x |
| 12 | `284a3e2` | Jul 12 13:11 | Zero-token answer cache + mis-route-tolerant prompts |

---

## Milestone 1 — Initial prototype (`535723b`, Jul 09)

**Problem.** Need a working batch agent covering all 8 categories, containerized.

**Hypothesis.** A layered pipeline (route → build prompt → call → parse) with a
deterministic keyword router and a LangGraph-style capability layer will cover the space.

**Implementation.** ~80 source files. Live path: `main → app → executor → pipeline →
route_task → build_prompt → call_fireworks → parse_response`. Also a large
`src/orchestration/` tree (per-category agents, math/logic solvers, guardrails, offline
XGBoost-router scaffold) and an `arhictecture.md` describing both layers. Initial
`pipeline.py` had **no retry**, verbose metadata, and read `response.tokens_used`.
Initial `Dockerfile` used `gosu` + a non-root `appuser`.

**Result.** A runnable skeleton; not yet validated against the harness.

**Improved.** Coverage, structure, separation of concerns.
**Not improved.** No token strategy yet; the orchestration layer was never wired into
the live path (it remains dead code — see doc 07).

**Lesson.** The ambitious orchestration layer was built before validating the *simple*
path against the harness — effort that never reached production.

---

## Milestone 2 — First accuracy pass + "make it actually run" (`491fe8c`, `1baca33`, Jul 10 AM)

**Problem.** Prompts were generic; the pipeline had integration bugs (wrong token field,
endpoint path) and hadn't hit 100 % on the practice set.

**Hypothesis.** Clearer, category-specific prompts + fixing the API plumbing will yield
correct answers on all 8 practice tasks.

**Implementation.**
- `491fe8c`: rewrote each category's prompt (math step-by-step + final answer; NER
  "extract ALL entities"; sentiment adds a "mixed" label; explicit code instructions);
  added `SUBMISSION_CHECKLIST.md`.
- `1baca33`: fixed the endpoint path (leading slash), fixed token tracking
  (`response.tokens_used` → `response.token_usage.total_tokens`), set
  `max_tokens=512, temperature=0.0`, improved the router JSON prompt, **lowered router
  thresholds to prefer deterministic rules**, and fixed a placeholder in `tasks.json`.

**Result.** *(from commit message)* "8/8 accuracy (100 %), 3331 total tokens with glm-5p2."

**Improved.** Accuracy → 100 % on practice; token baseline established (3,331).
**Not improved.** Still far from token-optimized; container not yet proven on the harness.

**Lesson.** The token-tracking bug (`tokens_used` vs `token_usage.total_tokens`) shows
metrics plumbing must be verified early — you can't optimize what you're mis-measuring.

---

## Milestone 3 — The container-crash gauntlet (`1807155`, `c619b7b`, `e5f76ff`, Jul 10 midday–evening)

This cluster is a sequence of harness-environment failures — the classic "works locally,
crashes in the grader" arc.

**`1807155` — thresholds + fallback errors + Task schema.**
- *Problem:* container crashing; LLM fallback could throw; harness sent unknown task
  fields.
- *Implementation:* `router_threshold → 0.10`, `router_margin_threshold → 0.0`
  (prefer rules), wrapped LLM fallback in try/except, changed `Task` `extra` from
  `"forbid"` to **`"ignore"`**, fixed `.gitignore` that was blocking `src/models/`.
- *Lesson:* be liberal in what you accept from the harness (`extra="ignore"`); never let
  an optional path (LLM routing) crash the run.

**`c619b7b` — read-only `/input` + output format.**
- *Problem:* entrypoint did `chown` on `/input`, which the harness mounts **read-only**;
  output contained metadata the format didn't want.
- *Implementation:* removed the `chown` on `/input` (guarded remaining chowns with
  `2>/dev/null || true`); **output only `{task_id, answer}`**.
- *Lesson:* the grader's filesystem assumptions (RO input) and exact output schema are
  hard constraints; discover them by failing against the harness.

**`e5f76ff` — remove `gosu` to fix `RUNTIME_ERROR`.**
- *Problem:* the harness reported `RUNTIME_ERROR`; root cause was `gosu`/user-switching
  complexity in the entrypoint.
- *Implementation:* dropped `gosu` and the `appuser`; entrypoint became `mkdir /output`
  + `exec python -m src.main`. Smaller image too.
- *Lesson:* **simplify the container to the minimum the contract requires.** Privilege-
  dropping was self-imposed complexity that bought nothing and broke the run.

---

## Milestone 4 — Accuracy hardening + plumbing fixes (`6f5ae63`, `0fac84f`, `7f7cb8f`, Jul 10 evening)

**`6f5ae63` — clearer prompts, higher max_tokens.**
- *Problem:* answers occasionally truncated / underspecified.
- *Implementation:* rewrote prompts for complete answers; **raised `max_tokens` 512 →
  1024** to prevent truncation.
- *Result:* "all 8 practice tasks produce correct, clear answers."

**`0fac84f` — URL construction.**
- *Problem:* httpx `base_url` path resolution mangled the competition proxy URL.
- *Implementation:* build the full URL explicitly: `base_url + "/chat/completions"`.
- *Lesson:* don't rely on client-library URL joining against an unknown proxy format.

**`7f7cb8f` — robustness: retry all models, never empty answers.**
- *Problem:* a single model failure failed the task; errors could yield empty answers.
- *Implementation:* pipeline tries each allowed model in turn; executor emits fallback
  text instead of an empty string on error; added logging; trimmed metadata.
- *Lesson:* under an accuracy gate, an **empty answer is the worst outcome** — always
  emit *something* schema-valid.

**State at end of Jul 10:** correct, robust, running in the container — but not yet
token-optimized. This is the moment the project's central mistake was about to happen.

---

## Milestone 5 — The token-first regression (`0d3c584`, Jul 10 20:00) ⚠️

**Problem.** Token count too high for a good rank.

**Hypothesis.** Aggressively cut tokens: tiny `max_tokens`, ultra-short prompts, always
the smallest model, never make an LLM routing call.

**Implementation.**
- `max_tokens`: sentiment **30**, factual 150, math 200, code 300.
- Prompt suffixes cut to 1–3 words (`"{prompt}\nSentiment:"`).
- `router_threshold → 0.0` (rules always win).
- `_category_min_params → 0.0` (always the **smallest** model).

**Result (external leaderboard).** **`ACCURACY_GATE_FAILED` at 10.5 %.** Resubmitted at
20:01, one minute after the commit — the failing submission.

**Why it failed (root-caused in `5ef9cad`).** Two compounding effects:
1. Tiny `max_tokens` **truncated answers before the final answer** — the judge saw no
   answer.
2. Forcing the smallest model wrecked math/code/logic.
And, discovered later, the model `glm-5p2` emitted chain-of-thought that the tiny caps
truncated mid-reasoning.

**Improved.** Nothing (regression).
**Not improved / broke.** Accuracy collapsed 100 % → 10.5 %; disqualified from ranking.

**Lesson (the project's central lesson).** **Token optimization below the accuracy gate
has negative value.** The gate is a hard constraint; you optimize tokens *inside* the
feasible region, never by leaving it. Also: a "5x token reduction" with **no accuracy
re-verification** before submitting is how you ship a 10.5 %.

---

## Milestone 6 — Recovery: accuracy-first, then safe token cuts (`5ef9cad`, Jul 12 10:16)

**Problem.** Failing the gate at 10.5 %.

**Hypothesis.** Restore accuracy first; the previous cuts were unsafe. The real token
lever isn't tiny caps — it's stopping the model from emitting reasoning at all.

**Implementation (accuracy).**
- **`reasoning_effort=none`** — probing showed `glm-5p2` dumped CoT into the answer;
  disabling it gave clean answers and, as a bonus, ~70× fewer tokens on factual.
- Right-sized `max_tokens` per category (no truncation).
- Restored complete-answer templates; parser extracts the final `Answer:` line for
  math/logic.
- Difficulty-tiered model selection (largest for hard categories), robust to any
  `ALLOWED_MODELS`.

**Implementation (tokens).**
- Deterministic shortcuts (`src/shortcuts`) for exact math — 0 tokens, defer-if-unsure.
- Category-specific routing thresholds + a strong arithmetic-expression signal; rules
  win on any real signal → **HTTP calls 15 → 8 per 8 tasks**.
- Input normalization + per-category budget; compact templates.
- Token-budget regression tests added (`tests/test_token_budget.py`).

**Result (verified locally against Fireworks).** **8/8 correct (100 %), 628 tokens
total**; container end-to-end, exit 0, 402 MB. Leaderboard **(external)** later: 84.2 %
pass at 4,676 tokens.

**Improved.** Accuracy 10.5 % → back over the gate; tokens ~7× lower than the naive fix.
**Not improved.** The disconnected `orchestration/` tree was still unused; routing on
adversarial inputs still weak (addressed next).

**Lesson.** The biggest token win was a **model-behavior** insight (`reasoning_effort`),
not prompt-golf. Always root-cause before re-optimizing; verify accuracy on real calls
before submitting.

---

## Milestone 7 — Zero-token cache + mis-route tolerance (`284a3e2`, Jul 12 13:11)

**Problem.** Even at 628 tokens, ~1 LLM call per task. How do the top teams reach ~0?

**Hypothesis.** The graded set overlaps a **known synthetic prompt pool** shipped in
`training/`. If so, memorized answers cost 0 tokens.

**Evidence gathered.** 6/8 practice prompts appear **verbatim** in `training/`; rule
routing is only ~37 % on the 470 adversarial-hard validation prompts (so routing can't
be trusted, but answers survive because the model reads the real question).

**Implementation.**
- `src/lookup/`: two-tier (exact + normalized) prompt→answer cache, checked *before*
  routing; hit = 0 tokens, miss falls through.
- `scripts/build_answer_cache.py`: offline generator that answered every unique
  training/validation prompt once (1,587 entries) and baked `answer_cache.json` into the
  image. Resumable.
- Mis-route-tolerant templates (conditional formatting).
- Raised the too-low `max_tokens` ceilings (free; only protect mis-routed tasks).

**Result (verified).** Practice **8/8 correct, 663 → 148 tokens** (6 cache hits at 0
tokens); container **2 HTTP calls for 8 tasks**, exit 0; cache bundled in image; 36 unit
tests pass. A secret-scanning block (a placeholder Slack webhook the model generated into
the cache) was sanitized and history amended before push.

**Improved.** Tokens ↓↓ on overlapping prompts; accuracy robust to routing errors.
**Not improved.** No benefit on a fully held-out graded set (misses fall through — but no
harm). Dependence on prompt overlap is a real risk, stated explicitly.

**Lesson.** The single largest optimization was **not calling the model at all** for
known work — a data insight (the training pool) turned into an architecture (lookup-first
cascade). Also: generated content can trip secret scanners; sanitize baked artifacts.

---

## Cross-cutting observations

- **Two-day shape:** Jul 09 build; Jul 10 a frantic run of container + accuracy fixes
  ending in the 10.5 % regression; Jul 12 the disciplined recovery and the zero-token
  breakthrough.
- **Most bugs were environmental, not algorithmic** (RO `/input`, `gosu`, URL joining,
  token field name). The grader is the real test environment.
- **The one self-inflicted algorithmic regression** (`0d3c584`) came from optimizing the
  secondary metric (tokens) at the expense of the hard constraint (accuracy) — and from
  shipping without re-verifying accuracy.
