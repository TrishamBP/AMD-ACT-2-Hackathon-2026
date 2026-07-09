from __future__ import annotations

import pytest

from src.orchestration.code_debugging.agent import CodeDebuggingAgent
from src.orchestration.code_debugging.schemas import CodeDebuggingInput
from src.orchestration.code_debugging.tools import CodeParserTool
from src.orchestration.graph import OrchestrationDependencies, build_graph
from src.orchestration.state.agent_state import AgentState


@pytest.mark.asyncio
async def test_code_parser_extracts_broken_python_code() -> None:
    payload = await CodeParserTool().arun(
        CodeDebuggingInput(
            request="Fix this Python code:\n```python\ndef add(a, b)\n    return a + b\n```"
        )
    )

    assert payload.language == "python"
    assert "def add(a, b)" in payload.code
    assert payload.syntax_valid is False
    assert payload.syntax_error is not None


@pytest.mark.asyncio
async def test_code_debugging_agent_fixes_missing_colon_without_client() -> None:
    agent = CodeDebuggingAgent()
    state = AgentState(
        task_id="debug-task-1",
        original_prompt="Fix this Python code:\n```python\ndef add(a, b)\n    return a + b\n```",
    )

    result = await agent(state)

    assert result.category == "code_debugging"
    assert result.selected_agent == "CodeDebuggingAgent"
    assert result.llm_response == "def add(a, b):\n    return a + b"
    assert result.errors == []
    assert result.validated_response is not None
    assert result.validated_response["repaired"] is False


@pytest.mark.asyncio
async def test_graph_routes_to_code_debugging_node() -> None:
    graph = build_graph(OrchestrationDependencies())
    state = AgentState(
        task_id="debug-task-2",
        original_prompt="Fix this Python code:\n```python\ndef add(a, b)\n    return a + b\n```",
    )

    result = await graph.ainvoke(state)

    assert result.category == "code_debugging"
    assert result.selected_agent == "CodeDebuggingAgent"
    assert result.llm_response == "def add(a, b):\n    return a + b"
