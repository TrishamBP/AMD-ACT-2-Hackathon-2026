---
name: evaluation
description: Use when benchmarking the agent, checking accuracy against expected outputs, or running regression tests before a submission. Covers metrics and how to compare runs.
---

# Evaluation

- Judge accuracy against intent, not exact string match — the real LLM-judge is intent-based, so
  local checks should be too
- Track two numbers per run: pass rate against the accuracy gate, and total tokens used
- Compare every change against the last known-good baseline; reject changes that raise tokens
  without raising accuracy (see `rules/evaluation.md`)
- Test each of the 8 categories separately — a change that helps math can silently hurt NER
- Re-run with unseen prompt variants, not just the sample tasks, since evaluation uses unseen
  variants
- See `commands/evaluate.md` and `commands/benchmark.md` for the actual run commands
