---
name: "source-command-profile"
description: "Check CPU, memory, and execution time for the full pipeline run."
---

# source-command-profile

Use this skill when the user asks to run the migrated source command `profile`.

## Command Template

Run and report:

1. Wall-clock time for a full batch run against the 10-minute ceiling
2. Peak memory usage
3. Any single task or category that's disproportionately slow — flag for optimizer
4. Concurrency level actually achieved vs. configured (semaphore limits, gather batch size)
