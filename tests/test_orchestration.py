from __future__ import annotations

import pytest

from src.orchestration.category.factual_agent import FactualKnowledgeAgent
from src.orchestration.factual_knowledge.prompt_builder import build_factual_prompt
from src.orchestration.factual_knowledge.schemas import (
    FactualKnowledgeConfig,
    FactualKnowledgeInput,
)
from src.orchestration.graph import OrchestrationDependencies, build_graph
from src.orchestration.nodes.routing_agent import RoutingAgent
from src.orchestration.state.agent_state import AgentState


def test_agent_state_serializes_cleanly() -> None:
    state = AgentState(
        task_id="task-1",
        original_prompt="Explain TCP/IP.",
    )

    payload = state.model_dump()

    assert payload["task_id"] == "task-1"
    assert payload["available_tools"] == []
    assert payload["errors"] == []


def test_factual_prompt_builder_is_compact() -> None:
    prompt = build_factual_prompt(
        FactualKnowledgeInput(question="What is TCP/IP?", context="Networking basics"),
    )

    assert "Example:" in prompt
    assert "Question: What is TCP/IP?" in prompt
    assert "Context: Networking basics" in prompt


@pytest.mark.asyncio
async def test_routing_agent_selects_factual_knowledge() -> None:
    state = AgentState(task_id="task-2", original_prompt="Explain TCP/IP.")

    routed = await RoutingAgent()(state)

    assert routed.category == "factual_knowledge"
    assert routed.selected_agent == "FactualKnowledgeAgent"
    assert routed.confidence > 0
    assert routed.execution_metadata["routing_evidence"]


@pytest.mark.asyncio
async def test_factual_agent_seeds_state_without_client() -> None:
    agent = FactualKnowledgeAgent(config=FactualKnowledgeConfig(model="demo-model"))
    state = AgentState(
        task_id="task-3",
        original_prompt="Explain TCP/IP.",
        selected_model="demo-model",
    )

    result = await agent(state)

    assert result.category == "factual_knowledge"
    assert result.selected_agent == "FactualKnowledgeAgent"
    assert result.prompt_template is not None
    assert result.available_tools == []
    assert "factual_model_client_not_configured" in result.errors
    assert result.trace


@pytest.mark.asyncio
async def test_graph_compiles_and_runs() -> None:
    graph = build_graph(OrchestrationDependencies())
    state = AgentState(
        task_id="task-4",
        original_prompt="Explain TCP/IP.",
    )

    result = await graph.ainvoke(state)

    assert result.category == "factual_knowledge"
    assert result.selected_agent == "FactualKnowledgeAgent"


@pytest.mark.asyncio
async def test_graph_routes_to_code_generation_node() -> None:
    graph = build_graph(OrchestrationDependencies())
    state = AgentState(
        task_id="task-5",
        original_prompt="Write a Python function that adds two numbers.",
    )

    result = await graph.ainvoke(state)

    assert result.category == "code_generation"
    assert result.selected_agent == "CodeGenerationAgent"
    assert "code_model_client_not_configured" in result.errors


@pytest.mark.asyncio
async def test_graph_routes_to_summarization_node() -> None:
    graph = build_graph(OrchestrationDependencies())
    state = AgentState(
        task_id="task-6",
        original_prompt="Summarize the following article in one sentence.",
    )

    result = await graph.ainvoke(state)

    assert result.category == "text_summarization"
    assert result.selected_agent == "TextSummarizationAgent"
    assert "summary_model_client_not_configured" in result.errors
