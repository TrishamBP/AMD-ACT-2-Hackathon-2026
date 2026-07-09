---
name: fireworks-api
description: Use when configuring the Fireworks AI client, handling environment variables (FIREWORKS_API_KEY, FIREWORKS_BASE_URL, ALLOWED_MODELS), setting timeouts/retries, or parsing Fireworks responses. Covers everything about talking to the Fireworks API correctly and only through the approved base URL.
---

# Fireworks API

- Read `FIREWORKS_API_KEY`, `FIREWORKS_BASE_URL`, `ALLOWED_MODELS` from `os.environ` at
  startup — never hardcode, never bundle a `.env` in the image
- All requests must go through `FIREWORKS_BASE_URL`. Any call that bypasses it scores zero
  tokens for the whole submission
- Only call model IDs present in `ALLOWED_MODELS` — calls to any other model invalidate the
  submission
- Build one shared `httpx.AsyncClient` for the whole run; don't create a new client per request
- Set explicit connect/read timeouts; don't rely on defaults
- Retry on transient errors (429, 5xx) with exponential backoff and a max attempt cap — never
  retry indefinitely
- Parse responses defensively: check for expected fields before indexing into them; a malformed
  response should raise a typed error the router can catch, not crash the process
- Log token usage per call so the total can be tracked, but keep logs off or minimal in the
  final image (see `rules/docker.md`)
