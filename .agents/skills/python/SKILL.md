---
name: python
description: Use when writing or reviewing any Python code in this project — async patterns, HTTP client usage, typing, file I/O. This is the core implementation skill for the agent's runtime code.
---

# Python

Always use:
- asyncio, `asyncio.gather` / `TaskGroup` for concurrency
- Async context managers (`async with`) for clients and resources
- `httpx.AsyncClient` for HTTP, one shared instance per run
- pathlib for all file paths
- typing (strict) and dataclasses for structured data
- Semaphores to bound concurrency against Fireworks rate limits
- Graceful cancellation/timeout handling around every network call

Avoid:
- `requests` (blocking) — use `httpx.AsyncClient` instead
- `time.sleep()` inside async code — use `asyncio.sleep`
- `threading` / `multiprocessing` unless a specific CPU-bound bottleneck requires it
- Blocking file I/O inside async functions — offload with `asyncio.to_thread` if a blocking call
  is unavoidable
