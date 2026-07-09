---
name: "source-command-optimize"
description: "Look for duplicate code, unnecessary prompt calls, blocking I/O, and repeated JSON parsing across the pipeline."
---

# source-command-optimize

Use this skill when the user asks to run the migrated source command `optimize`.

## Command Template

Check for, and report/fix:

1. Duplicate or redundant Fireworks calls across tasks
2. Blocking calls inside async code (`requests`, `time.sleep`, blocking file I/O)
3. Prompt templates that repeat instructions unnecessarily (`skills/prompt-engineering`)
4. Repeated JSON parsing/serialization that could be done once
5. Sequential awaits that could be `asyncio.gather`/`TaskGroup` instead

Every fix must be paired with a before/after benchmark (`commands/benchmark.md`).
