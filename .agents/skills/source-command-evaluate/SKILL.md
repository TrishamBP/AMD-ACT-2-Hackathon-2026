---
name: "source-command-evaluate"
description: "Run all tests and sample tasks, then compare outputs against expected results for accuracy."
---

# source-command-evaluate

Use this skill when the user asks to run the migrated source command `evaluate`.

## Command Template

Run and report, in order:

1. `pytest -q`, `ruff check .`, `mypy .` — all must pass
2. Run the full sample `tasks.json` through the pipeline, write to a scratch `results.json`
3. Compare each answer against expected intent per category (not exact string match)
4. Report pass rate per category and total tokens used
5. Flag any answer that isn't valid per the output schema
