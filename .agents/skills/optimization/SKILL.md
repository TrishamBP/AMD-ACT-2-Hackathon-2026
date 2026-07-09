---
name: optimization
description: Use when looking for token reduction, latency improvements, duplicate/redundant prompt calls, or unnecessary retries in the agent pipeline. Covers concrete optimization techniques, not just philosophy.
---

# Optimization

- Batch independent tasks with `asyncio.gather` / `TaskGroup` instead of awaiting sequentially
- Deduplicate identical or near-identical prompts across tasks before calling the API
- Cache nothing that varies per evaluation run (no hardcoded answers), but do reuse a single
  client/session and shared prompt templates within a run
- Cut prompt length first; it reduces both latency and tokens
- Limit concurrent in-flight requests with a semaphore to avoid rate-limit retries, which cost
  tokens
- Measure before and after every change with `commands/benchmark.md` — don't assume an
  optimization helped
