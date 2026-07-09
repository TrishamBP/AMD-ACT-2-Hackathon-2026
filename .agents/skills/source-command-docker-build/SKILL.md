---
name: "source-command-docker-build"
description: "Build the Docker image and verify size, entrypoint, and environment variable handling."
---

# source-command-docker-build

Use this skill when the user asks to run the migrated source command `docker-build`.

## Command Template

Run and report:

1. `docker build` — must succeed
2. Compressed image size — must be under 10GB
3. Entrypoint reads `/input/tasks.json` and writes `/output/results.json` without requiring
   stdin
4. No hardcoded `FIREWORKS_API_KEY`, `FIREWORKS_BASE_URL`, or model IDs anywhere in the image —
   grep the built image/layers for stray secrets
5. Container exits 0 on a successful sample run, non-zero on a forced failure
