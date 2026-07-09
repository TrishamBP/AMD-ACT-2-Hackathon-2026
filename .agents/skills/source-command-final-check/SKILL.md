---
name: "source-command-final-check"
description: "Pre-submission checklist — run before every submission."
---

# source-command-final-check

Use this skill when the user asks to run the migrated source command `final-check`.

## Command Template

Confirm all of the following before submitting:

- [ ] Docker builds cleanly
- [ ] Reads `/input/tasks.json`
- [ ] Writes valid `/output/results.json`
- [ ] Uses `FIREWORKS_API_KEY` / `FIREWORKS_BASE_URL` / `ALLOWED_MODELS` from environment only
- [ ] All Fireworks calls go through `FIREWORKS_BASE_URL` (no bypass)
- [ ] Only `ALLOWED_MODELS` model IDs are called
- [ ] Async client used throughout, no blocking calls
- [ ] Output is valid JSON, no markdown, no stray commentary
- [ ] No hardcoded API keys or cached/precomputed answers
- [ ] Runtime under 10 minutes for the full batch
- [ ] Logs minimal/disabled in the final image
- [ ] Image compressed size under 10GB
- [ ] `pytest`, `ruff`, `mypy` all pass
