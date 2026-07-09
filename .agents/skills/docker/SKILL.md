---
name: docker
description: Use when writing or editing the Dockerfile, checking image size, entrypoint behavior, or container I/O contract. Covers Docker best practices specific to this challenge's constraints.
---

# Docker

- Multi-stage build; final stage has no build tools, no dev dependencies
- Slim base image (e.g. `python:3.12-slim`); avoid full Debian/Ubuntu bases
- Order layers so dependency installation is cached separately from source code copies
- Entrypoint reads `/input/tasks.json`, writes `/output/results.json`, exits 0 on success
- No stdin requirement, no network access except `FIREWORKS_BASE_URL`
- Compressed image must stay under 10GB — check with `docker images` after build, not just
  estimate
- No secrets, API keys, or `.env` files baked into the image — everything comes from injected
  environment variables
- See `commands/docker-build.md` for the actual verification steps
