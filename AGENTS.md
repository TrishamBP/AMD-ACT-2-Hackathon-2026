# Project Overview

Autonomous AI agent for the Fireworks AI "General-Purpose AI Agent" challenge (Track 1).

Reads tasks from `/input/tasks.json`, writes results to `/output/results.json`, exits cleanly.
All inference goes through Fireworks AI via `FIREWORKS_BASE_URL` — nothing else.

Evaluated across 8 categories: factual knowledge, mathematical reasoning, sentiment
classification, text summarization, named entity recognition, code debugging, logical/deductive
reasoning, code generation.

Scoring: an LLM-judge accuracy gate first, then submissions that pass are ranked ascending by
total tokens. Optimize for both, in that order — accuracy first, tokens second.

# Architecture

Task -> Router -> Prompt Builder -> Fireworks Client -> Parser -> Output Writer

- Router classifies each task into one of the 8 categories and picks the model + prompt template.
- Prompt Builder assembles the final prompt from templates; never does I/O.
- Fireworks Client is the only module that calls Fireworks AI; every call goes through
  `FIREWORKS_BASE_URL`.
- Parser extracts the final answer from the raw model response.
- Output Writer assembles `/output/results.json`.

See `rules/architecture.md` for the layering rules.

# Environment

Read at runtime, never hardcode or bundle a `.env` file in the image:

- `FIREWORKS_API_KEY`
- `FIREWORKS_BASE_URL`
- `ALLOWED_MODELS` (comma-separated; only these model IDs may be called)

# Coding Rules

- Python 3.12, strict typing, async-first
- Never block the event loop
- Composition over inheritance
- Prompts are modular, never duplicated across modules

Full detail: `rules/coding-style.md`, `rules/prompts.md`, `skills/python/SKILL.md`.

# Performance Goals

- Runtime under 10 minutes for the full batch
- Minimize total tokens — this is the ranking metric once accuracy clears the gate
- Stateless, memory-efficient, deterministic where possible

See `rules/token-efficiency.md`.

# Output Rules

- Always valid JSON matching the `/output/results.json` schema exactly
- No markdown, no explanations, unless the task itself asks for them
- Never hallucinate missing fields or invent `task_id`s

# Testing

`pytest`, `ruff`, `mypy` — run before considering any change done.
Run `commands/final-check.md` before every submission.

# Docker

Image reads `/input`, writes `/output`, exits 0 on success, needs no stdin, needs no network
except Fireworks. Max compressed size 10GB. See `rules/docker.md`.

---

Keep this file under 200 lines. Topic-specific detail belongs in `rules/`, `skills/`, or
`agents/` — not here.
