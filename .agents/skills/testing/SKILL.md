---
name: testing
description: Use when writing or running tests for the agent pipeline. Covers test philosophy and what to check before considering a change done.
---

# Testing

- `pytest` for all tests, `ruff` for lint, `mypy` for types — all three must pass before a
  change is done
- Unit test each pipeline layer (router, prompt builder, client, parser, output writer)
  independently with mocked boundaries
- Mock the Fireworks client in tests — never hit the real API in unit tests
- Test the full /input -> /output contract with a small fixture `tasks.json` at least once per
  change
- Test malformed-input handling: missing fields, empty prompts, unexpected duplicate `task_id`s
- A change isn't done until `commands/final-check.md` passes
