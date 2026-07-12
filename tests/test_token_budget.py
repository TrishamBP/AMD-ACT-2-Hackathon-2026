"""Token-usage invariants treated as regression tests.

These use a stubbed Fireworks client so they never spend real tokens. They
assert the structural guarantees that keep us cheap:
  * at most ONE Fireworks call per task (no accidental fan-out),
  * math tasks solvable deterministically make ZERO calls,
  * prompt sizes stay within per-category budgets.
"""
from __future__ import annotations

import pytest

from src.agent.executor import execute_tasks
from src.config.settings import Settings
from src.models.response import FireworksResponse, TokenUsage
from src.models.task import Task
from src.prompts.builder import build_prompt
from src.prompts.normalize import estimate_tokens
from src.routing.router import route_task

_MODELS = ["accounts/fireworks/models/glm-5p2"]


def _settings() -> Settings:
    return Settings(api_key="k", base_url="https://x", allowed_models=_MODELS)


class _CallCounter:
    def __init__(self) -> None:
        self.count = 0

    async def __call__(self, prompt: str, model: str, settings: Settings, **kwargs: object) -> FireworksResponse:
        self.count += 1
        return FireworksResponse(
            content="Answer: stub",
            model=model,
            token_usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            latency_ms=1.0,
        )


@pytest.mark.asyncio
async def test_at_most_one_fireworks_call_per_task(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = _CallCounter()
    monkeypatch.setattr("src.agent.pipeline.call_fireworks", counter)
    # A prompt that will NOT be shortcut-solved, forcing exactly one LLM call.
    tasks = [Task(task_id="t1", prompt="Who wrote Hamlet?")]
    results = await execute_tasks(tasks, _settings())
    assert len(results) == 1
    assert counter.count == 1


@pytest.mark.asyncio
async def test_deterministic_math_makes_zero_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = _CallCounter()
    monkeypatch.setattr("src.agent.pipeline.call_fireworks", counter)
    tasks = [Task(task_id="m1", prompt="What is 12 * 12?")]
    results = await execute_tasks(tasks, _settings())
    assert results[0].answer == "144"
    assert counter.count == 0
    assert results[0].metadata.get("tokens") == 0


@pytest.mark.asyncio
async def test_prompt_stays_within_budget() -> None:
    settings = _settings()
    # Oversized summarization input must be trimmed by the builder.
    big = "This is filler content. " * 2000
    task = Task(task_id="s1", prompt=f"Summarize in one sentence: {big}")
    decision = await route_task(task, settings)
    prompt = build_prompt(task, decision)
    # Estimated prompt tokens must stay well under a hard ceiling.
    assert estimate_tokens(prompt) < 2600
