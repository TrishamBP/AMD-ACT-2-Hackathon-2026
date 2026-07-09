from __future__ import annotations

import pytest

from src.config.settings import Settings
from src.models.task import Task
from src.routing.router import _parse_model_metadata, route_task


def test_model_metadata_parsing_handles_moe_and_billion_values() -> None:
    metadata = _parse_model_metadata("Mixtral-8x7B-Instruct")
    assert metadata.params_billion == pytest.approx(56.0)
    assert metadata.instruction is True

    metadata = _parse_model_metadata("Qwen3-1.7B")
    assert metadata.params_billion == pytest.approx(1.7)


@pytest.mark.asyncio
async def test_route_task_uses_rules_when_confident(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        api_key="key",
        base_url="https://example.com",
        allowed_models=["Qwen3-1.7B", "Llama-3.2-3B"],
        router_threshold=0.65,
        router_margin_threshold=0.15,
    )
    task = Task(
        task_id="1",
        prompt=(
            "Summarize the following article in one sentence. "
            "The article explains how hierarchical routers reduce token usage by "
            "letting deterministic heuristics handle obvious tasks and reserving "
            "LLM fallback only for ambiguous cases. It highlights confidence "
            "thresholds, score margins, and explainable evidence as the main "
            "benefits of the design."
        ),
    )

    async def fail_llm(*args: object, **kwargs: object) -> None:
        raise AssertionError("LLM fallback should not be used for a confident rule route")

    monkeypatch.setattr("src.routing.router.call_fireworks", fail_llm)

    decision = await route_task(task, settings)

    assert decision.category == "text_summarization"
    assert decision.route_source == "rules"
    assert decision.model == "Qwen3-1.7B"
    assert decision.confidence >= 0.65


@pytest.mark.asyncio
async def test_route_task_falls_back_to_llm_for_ambiguous_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        api_key="key",
        base_url="https://example.com",
        allowed_models=["Qwen3-1.7B", "Llama-3.2-3B"],
    )
    task = Task(task_id="1", prompt="This is a mixed prompt with code and a question.")

    class DummyResponse:
        content = '{"category":"code_debugging","confidence":0.92}'

    async def fake_llm(*args: object, **kwargs: object) -> DummyResponse:
        return DummyResponse()

    monkeypatch.setattr("src.routing.router.call_fireworks", fake_llm)

    decision = await route_task(task, settings)

    assert decision.route_source == "llm"
    assert decision.category == "code_debugging"
    assert decision.model == "Qwen3-1.7B"
