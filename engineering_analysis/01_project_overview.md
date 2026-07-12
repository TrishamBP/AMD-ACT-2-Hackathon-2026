# 01 — Project Overview

> Evidence base: `.claude/CLAUDE.md`, `AGENTS.md`, `README.md`, `arhictecture.md`,
> `test_with_fireworks.py`, `input/tasks.json`, and the leaderboard results reported
> by the competition harness. Where a claim rests on the competition harness rather
> than a file in this repo, it is marked **(external)**.

---

## 1.1 Overall objective

Build an autonomous, containerized AI agent for the **AMD Developer Hackathon "ACT II", Track 1** — the Fireworks AI "General-Purpose AI Agent" challenge.

The container is a **batch worker**, not a service (`arhictecture.md`, "The runtime is batch-oriented, not service-oriented"):

```
docker run → read /input/tasks.json → process every task → write /output/results.json → exit 0
```

There is no HTTP server, no daemon, no stdin. The full contract (`.claude/rules/docker.md`):

- Read tasks from `/input/tasks.json` on startup.
- Write `/output/results.json` before exiting.
- Exit `0` on success, non-zero on failure.
- Never require stdin.
- Never require network access **except** to `FIREWORKS_BASE_URL`.
- Stay under 10 GB compressed.
- Read `FIREWORKS_API_KEY`, `FIREWORKS_BASE_URL`, `ALLOWED_MODELS` from the
  environment — never hardcode, never bundle a `.env`.

## 1.2 Problem statement

Each task in `/input/tasks.json` is a `{task_id, prompt}` object (`input/tasks.json`):

```json
[
  {"task_id": "practice-01", "prompt": "What is the capital of Australia, and what body of water is it near?"},
  {"task_id": "practice-02", "prompt": "A store has 240 items. It sells 15% on Monday and 60 more on Tuesday. How many items remain?"}
]
```

The agent must produce, for every task, a `{task_id, answer}` object in
`/output/results.json` (`src/io/writer.py`). Prompts span **8 categories**
(`src/config/constants.py`):

1. `factual_knowledge`
2. `mathematical_reasoning`
3. `sentiment_classification`
4. `text_summarization`
5. `named_entity_recognition`
6. `code_debugging`
7. `logical_reasoning`
8. `code_generation`

## 1.3 Competition constraints

| Constraint | Source | Consequence for design |
|---|---|---|
| Only `ALLOWED_MODELS` may be called | `.claude/CLAUDE.md`, `AGENTS.md` | Model selection must be robust to an unknown, runtime-injected model list. |
| All inference via `FIREWORKS_BASE_URL` | `AGENTS.md` | Single HTTP client module; no other network egress. |
| ≤ 10 GB compressed image | `.claude/rules/docker.md` | Slim base, multi-stage build; no heavyweight ML deps (no `sklearn`/`xgboost`). |
| Runtime < 10 min for full batch | `.claude/CLAUDE.md` | Async concurrency (`asyncio.gather` + semaphore). |
| No secrets baked in | `.claude/rules/docker.md` | Env-only settings (`src/config/settings.py`). |

## 1.4 Evaluation metric — the two-phase scoring gate

The single most important fact for every downstream decision (`.claude/CLAUDE.md`,
`AGENTS.md`, `test_with_fireworks.py:189`):

> **Phase 1 — Accuracy gate.** An LLM judge grades every answer. If overall
> accuracy is below the threshold, the submission is **disqualified from ranking
> entirely**.
>
> **Phase 2 — Token ranking.** Submissions that pass the gate are ranked
> **ascending by total tokens** — lower is better.

The threshold is encoded as `accuracy_threshold = 0.85` in `test_with_fireworks.py:189`.
The observed leaderboard behavior **(external)**: a 10.5 % run returned
`ACCURACY_GATE_FAILED`; an 84.2 % run passed and ranked at 4,676 tokens.

The ordering is strict: **accuracy first, tokens second.** A token optimization that
costs one point of accuracy below the gate is worth *negative* infinity, because it
removes you from the ranking. This asymmetry drives the entire engineering story
(see `05_git_history_analysis.md`, where a token-first commit dropped the run to 10.5 %).

## 1.5 Why token efficiency matters

Once the accuracy gate is cleared, **the only ranking axis is total tokens.** Two
submissions that both pass are ordered purely by how many tokens they burned. Every
prompt word, every chain-of-thought token, every unnecessary LLM call is a direct
loss of rank. The ranking is by *token count*, not dollar cost, so it favors:

- fewer LLM calls (ideally zero for known work),
- shorter prompts,
- models/settings that don't emit hidden reasoning tokens.

## 1.6 Why this is an engineering optimization problem, not a prompting problem

A naive framing is "write good prompts and call the model." The constraints turn it
into a **constrained optimization problem** with a hard feasibility region:

```
maximize   rank  (i.e. minimize total_tokens)
subject to answer_accuracy ≥ gate            # hard constraint — infeasible below it
           image ≤ 10 GB
           runtime ≤ 10 min
           calls only to ALLOWED_MODELS via FIREWORKS_BASE_URL
```

This is engineering, not prompt-craft, because the winning moves are **structural**:

- **Don't call the model when you already know the answer** — the memorized-answer
  cache (`src/lookup/`) serves known prompts at **0 tokens**.
- **Don't call the model for what code can compute exactly** — deterministic
  shortcuts (`src/shortcuts/arithmetic.py`) answer arithmetic at 0 tokens.
- **Don't let the model emit reasoning tokens** — `reasoning_effort=none`
  (`src/llm/client.py`) collapsed a ~590-token factual answer to ~8 tokens.
- **Route without paying** — deterministic keyword/feature routing
  (`src/routing/router.py`) instead of an LLM classification call.
- **Never truncate a correct answer** — per-category `max_tokens` sized so the final
  answer always fits (`src/prompts/builder.py`).

Each of these is a code change with a measurable token delta and an accuracy
trade-off, analysed in `04_engineering_decisions.md` and `08_token_efficiency_analysis.md`.

## 1.7 Note on scope: the two layers in this repo

The repository contains **two** layers, and only one of them runs:

1. **The live batch pipeline** (`src/main.py → src/app.py → src/agent/… → src/llm/…`)
   — this is what the container executes and what this analysis is primarily about.
2. **A large LangGraph-style orchestration layer** (`src/orchestration/…`, ~60 files:
   per-category agents, math/logic solvers, guardrails, an offline XGBoost-router
   scaffold) that is **not imported by the live path** (verified: no file outside
   `src/orchestration/` imports it).

Per the project owner's direction, **the "pipeline" in this analysis is the live
batch pipeline that was actually built and shipped.** The `orchestration/` tree —
and any RAG/retrieval/embedding machinery the deliverable template mentions — is
**reference/aspirational scaffolding, not part of the shipped system**; it is covered
explicitly in `07_failed_experiments.md` (dead-code / unshipped-design section) and
noted wherever relevant, but it is not presented as live architecture.
