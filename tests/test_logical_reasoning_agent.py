from __future__ import annotations

import pytest

from src.orchestration.graph import OrchestrationDependencies, build_graph
from src.orchestration.logical_reasoning.agent import LogicalReasoningAgent
from src.orchestration.logical_reasoning.tools import ReasoningTypeDetectorTool
from src.orchestration.runtime.model_selection import ModelSelector, parse_allowed_models
from src.orchestration.state.agent_state import AgentState


@pytest.mark.asyncio
async def test_reasoning_detector_identifies_rule_based_logic() -> None:
    reasoning_type, confidence, evidence = await ReasoningTypeDetectorTool().arun(
        "If A then B. A. Therefore B."
    )

    assert reasoning_type in {"rule_based_reasoning", "deductive_reasoning"}
    assert confidence > 0
    assert evidence


@pytest.mark.asyncio
async def test_logical_reasoning_agent_solves_simple_implication_without_client() -> None:
    agent = LogicalReasoningAgent()
    state = AgentState(
        task_id="logic-task-1",
        original_prompt="If A then B. A. Therefore B.",
    )

    result = await agent(state)

    assert result.category == "logical_reasoning"
    assert result.selected_agent == "LogicalReasoningAgent"
    assert result.llm_response == "b: true"
    assert result.errors == []
    assert result.validated_response is not None


@pytest.mark.asyncio
async def test_graph_routes_to_logical_reasoning_node() -> None:
    graph = build_graph(OrchestrationDependencies())
    state = AgentState(
        task_id="logic-task-2",
        original_prompt="If A then B. A. Therefore B.",
    )

    result = await graph.ainvoke(state)

    assert result.category == "logical_reasoning"
    assert result.selected_agent == "LogicalReasoningAgent"
    assert result.llm_response == "b: true"


def test_model_selector_picks_smallest_compatible_model() -> None:
    models = ["Qwen3-1.7B", "Llama-3.2-3B", "Gemma3-4B"]
    parsed = parse_allowed_models(models)

    assert [model.id for model in parsed] == models
    selected = ModelSelector().choose(models)
    assert selected is not None
    assert selected.id == "Qwen3-1.7B"
