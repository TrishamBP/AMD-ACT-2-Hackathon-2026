# 07 — Failed Experiments & Dead Ends

> Each entry: **What was attempted → Why it seemed good → Why it failed → Disposition
> (removed / abandoned / kept-but-unused) → Lesson.** All are evidence-backed from code
> or commit history.

---

## F1 — Aggressive token-first optimization (`0d3c584`) — the headline failure

**Attempted.** Slash tokens across the board: `max_tokens` sentiment=30 / factual=150 /
math=200, 1–3 word prompt suffixes, `router_threshold=0` (never call LLM router),
`_category_min_params=0` (always the smallest model).

**Why it seemed good.** The ranking metric is total tokens; a "5× reduction" looked like
a straight rank win. Every change individually reduces tokens.

**Why it failed.** It optimized the *secondary* metric while violating the *hard
constraint*. Truncation clipped answers before completion (the judge saw no answer),
the smallest model failed hard categories, and — discovered later — `glm-5p2`'s
chain-of-thought consumed the tiny budget before any answer appeared. **Result:
`ACCURACY_GATE_FAILED` at 10.5 %** (external leaderboard), disqualified from ranking.

**Disposition.** Reverted/superseded by `5ef9cad`.

**Lesson.** **Never optimize the soft metric out of the feasible region of the hard
constraint.** And never ship a large optimization without re-verifying the hard metric
(accuracy) first.

---

## F2 — The entire `src/orchestration/` LangGraph layer — built, never wired

**Attempted.** A ~60-file capability architecture: per-category agents
(`mathematical_reasoning/agent.py`, `code_debugging/agent.py`, …), deterministic solvers
(`mathematical_reasoning/solvers.py` — 661 lines: calculator, unit converter, equation/
geometry/statistics/probability/number-theory/SymPy solvers), guardrails, validators,
Pydantic `AgentState`, tracing decorators, a routing-agent node, and an
`offline_learning/` XGBoost-router scaffold. Described at length in `arhictecture.md`.

**Why it seemed good.** A clean, testable, per-capability design with deterministic
solvers is exactly what a token-efficient system *should* look like — solve
deterministically, fall back to one LLM call, validate output.

**Why it failed to ship.** It was **never imported by the live pipeline** (verified: no
file outside `src/orchestration/` imports it). It depends on LangGraph `AgentState`,
Pydantic models, tracing decorators, and `sympy` — and **`sympy` is not in
`pyproject.toml`**, so its symbolic solvers would silently no-op in the container.
Wiring it wholesale was judged too risky (it never ran in the graded environment, and
re-introducing complexity was exactly what caused the `RUNTIME_ERROR` in `e5f76ff`).

**Disposition.** Kept in the repo as reference/scaffolding; **not part of the shipped
system.** Its *ideas* were re-implemented minimally and safely in `src/shortcuts/`
(a dependency-free arithmetic solver with a strict defer contract).

**Lesson.** A sophisticated design that isn't wired into the executed path contributes
zero to the score and adds image weight and cognitive load. **Ship the smallest thing
that works against the real harness**; port ideas from the grand design only when
validated. (Also: undeclared optional deps like `sympy` fail silently — a latent trap.)

---

## F3 — LLM-based routing as the default

**Attempted.** `route_task` originally leaned on an LLM classification call when rules
weren't confident (`_fallback_llm_route`, still present).

**Why it seemed good.** An LLM classifier is more accurate than keyword rules on
ambiguous prompts.

**Why it failed (for this metric).** Every routing call is a recurring token cost, and
routing only selects a template + model tier — cheap to get *approximately* right.
Commits `1baca33`/`1807155` lowered thresholds to prefer rules; `5ef9cad` tuned them
per category so rules win on any real signal (**HTTP calls 15 → 8 per 8 tasks**).

**Disposition.** LLM routing retained only as a rare last-resort fallback for
zero-signal prompts; effectively disabled in the common case.

**Lesson.** Don't pay LLM tokens for a decision that a free heuristic gets close enough —
especially when downstream templates tolerate routing errors (see F4).

---

## F4 — Trusting the router (and the trained classifier that would "fix" it)

**Attempted / measured.** Rule routing was measured at **36.8 %** on the 470 adversarial-
hard validation prompts (logical_reasoning 4.5 %, sentiment 16 %). A word-ngram logistic-
regression classifier was prototyped from `training/` and scored **53 %** on the same
hard set (98 % train — overfit).

**Why it seemed good.** 53 % ≫ 36.8 %; the training data was literally provided to train
a router (the `offline_learning/` scaffold anticipates an XGBoost meta-router).

**Why it was rejected for the live path.** (a) It saves **0 tokens** — the system already
routes for free with rules; the classifier would only change *which* template is chosen.
(b) 53 % on hard negatives isn't reliable enough to bet the accuracy gate on. (c) It adds
an ML artifact + dependency to a size-constrained image. Crucially, the real fix was
cheaper: **make templates mis-route-tolerant** (`284a3e2`) so a wrong category still
yields a correct answer — verified live (math→factual, text→math mis-routes still
answered correctly).

**Disposition.** Classifier prototype abandoned; mis-route-tolerant templates shipped
instead.

**Lesson.** Improve the *consequence* of an error, not just the error rate — especially
when the accurate fix (a classifier) costs tokens/complexity and the tolerant fix is
free. Routing accuracy ≠ answer accuracy in a setup where the model reads the real
question regardless of template.

---

## F5 — Broad deterministic word-problem / sentiment / NER solvers

**Attempted (considered, then bounded).** Extending `src/shortcuts` to cover word
problems, lexicon sentiment, and regex NER for more 0-token answers.

**Why it seemed good.** More deterministic coverage = fewer LLM calls = fewer tokens.

**Why it was bounded/rejected on this distribution.** Measured on the hard validation
set: the arithmetic shortcut fires on **0/50** math prompts (they're word problems, not
bare expressions); **~29/50** sentiment prompts are sarcasm/mixed/implicit traps where a
lexicon would be *confidently wrong* ("wow, groundbreaking" = negative sarcasm). A wrong
deterministic answer costs the accuracy gate.

**Disposition.** Only provably-exact math shortcuts kept; broad solvers deliberately not
built. Zero-token gains were instead pursued via the memorized-answer cache (F-free), a
safer lever.

**Lesson.** Deterministic shortcuts are only worth it where they're **provably exact**;
on adversarial/nuanced inputs they trade accuracy for tokens — the wrong direction under
a gate.

---

## F6 — Container privilege-dropping (`gosu` / `appuser`)

**Attempted.** The initial `Dockerfile` installed `gosu`, created a non-root `appuser`,
`chown`ed `/input /output`, and dropped privileges in the entrypoint.

**Why it seemed good.** Running as non-root is a container best practice.

**Why it failed.** It caused `RUNTIME_ERROR` in the harness and `chown` failed on the
read-only `/input` mount. `c619b7b` removed the `/input` chown; `e5f76ff` removed `gosu`
and user-switching entirely.

**Disposition.** Removed; entrypoint reduced to `mkdir /output` + `exec python`.

**Lesson.** General best practices can conflict with a specific harness's assumptions
(RO mounts, exit semantics). Match the contract, not a generic checklist.

---

## F7 — Verbose output metadata

**Attempted.** V1 wrote rich per-task metadata (router scores, evidence, model metadata)
into the results.

**Why it seemed good.** Debuggability and transparency.

**Why it failed.** Not the competition output format, and larger output. `c619b7b`
reduced output to exactly `{task_id, answer}`.

**Disposition.** Metadata moved to logs / in-memory `Result.metadata` only.

**Lesson.** The output artifact must match the grader's schema exactly; keep
observability out of the graded file.

---

## F8 — Secret-scanning block from generated cache content

**Attempted.** Committing `answer_cache.json` (model-generated answers).

**Why it failed.** A code-gen answer contained a **placeholder** Slack webhook
(`hooks.slack.com/services/T00000000/...`), which GitHub push-protection flagged as a
secret.

**Disposition.** Sanitized the cache (regex-redacted secret-shaped strings), amended the
commit, re-pushed; rebuilt/re-pushed the image.

**Lesson.** Model-generated artifacts can contain secret-shaped strings; sanitize baked
data before committing/shipping.
