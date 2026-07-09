---
name: "source-command-benchmark"
description: "Run pytest, benchmark token usage, and report latency for the current pipeline."
---

# source-command-benchmark

Use this skill when the user asks to run the migrated source command `benchmark`.

## Command Template

Run and report, in order:

1. `pytest -q` — all tests must pass
2. Token benchmark: run the sample tasks through the full pipeline and sum tokens used per
   category and total
3. Latency: measure wall-clock time for the full batch run, flag if projected to exceed 10
   minutes at full scale
4. Compare totals against the last recorded baseline (`rules/evaluation.md`); report the delta,
   not just absolute numbers
