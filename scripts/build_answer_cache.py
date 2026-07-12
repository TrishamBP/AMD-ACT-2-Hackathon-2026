#!/usr/bin/env python3
"""Offline builder for the zero-token answer cache.

Runs every unique training/validation prompt through the real answering
pipeline ONCE (answer cache disabled) and stores prompt -> answer in
src/lookup/answer_cache.json. At grade time those answers are served with no
Fireworks call.

Usage:
    export FIREWORKS_API_KEY=...  FIREWORKS_BASE_URL=...  ALLOWED_MODELS=...
    python scripts/build_answer_cache.py training/router_train.jsonl \
        training/router_validation.jsonl training/router_training_synthetic.jsonl

Resumable: existing entries in the output file are kept and skipped.
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import sys
from pathlib import Path

from src.config.settings import load_settings
from src.llm.client import close_fireworks_client
from src.models.task import Task

_OUT = Path("src/lookup/answer_cache.json")
_CONCURRENCY = 8


def _read_prompts(paths: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            prompt = json.loads(line).get("prompt")
            if isinstance(prompt, str) and prompt.strip():
                seen.setdefault(prompt, None)
    return list(seen)


def _load_existing() -> dict[str, str]:
    if not _OUT.exists():
        return {}
    raw = json.loads(_OUT.read_text(encoding="utf-8"))
    entries = raw.get("entries", []) if isinstance(raw, dict) else raw
    return {e["prompt"]: e["answer"] for e in entries if e.get("answer", "").strip()}


def _write(table: dict[str, str]) -> None:
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"entries": [{"prompt": p, "answer": a} for p, a in table.items()]}
    _OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=0), encoding="utf-8")


async def _answer_one(prompt: str, settings: object) -> str | None:
    # Import here so the module loads even when deps differ; disable the cache
    # so we actually generate rather than read a partial table.
    from src.agent.pipeline import process_single_task

    no_cache = dataclasses.replace(settings, use_answer_cache=False)  # type: ignore[arg-type]
    try:
        result = await process_single_task(Task(task_id="cache", prompt=prompt), no_cache)
    except Exception as exc:  # noqa: BLE001 - one failure shouldn't abort the batch
        print(f"  ! failed: {prompt[:60]!r}: {exc}", file=sys.stderr)
        return None
    return result.answer if result.answer.strip() else None


async def main(paths: list[str]) -> int:
    settings = load_settings()
    prompts = _read_prompts(paths)
    table = _load_existing()
    todo = [p for p in prompts if p not in table]
    print(f"{len(prompts)} unique prompts, {len(table)} cached, {len(todo)} to generate")

    sem = asyncio.Semaphore(_CONCURRENCY)
    done = 0

    async def worker(prompt: str) -> None:
        nonlocal done
        async with sem:
            answer = await _answer_one(prompt, settings)
        if answer:
            table[prompt] = answer
        done += 1
        if done % 50 == 0:
            _write(table)
            print(f"  progress {done}/{len(todo)} (cached {len(table)})")

    try:
        await asyncio.gather(*(worker(p) for p in todo))
    finally:
        _write(table)
        await close_fireworks_client()

    print(f"Done. {len(table)} answers cached -> {_OUT}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
