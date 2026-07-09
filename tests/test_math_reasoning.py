from __future__ import annotations

import pytest

from src.orchestration.graph import OrchestrationDependencies, build_graph
from src.orchestration.mathematical_reasoning.agent import MathematicalReasoningAgent
from src.orchestration.mathematical_reasoning.classifier import ProblemClassifier
from src.orchestration.mathematical_reasoning.parser import ProblemParser
from src.orchestration.mathematical_reasoning.schemas import MathProblem
from src.orchestration.mathematical_reasoning.solvers import EquationSolver
from src.orchestration.state.agent_state import AgentState


def test_problem_classifier_marks_equation_prompts_as_algebra() -> None:
    problem = MathProblem(statement="Solve 2x + 3 = 7.")

    parsed = ProblemClassifier().classify(problem)

    assert parsed.problem_type == "algebra"
    assert parsed.confidence > 0
    assert "equation_with_variable" in parsed.evidence


def test_problem_parser_extracts_math_structure() -> None:
    problem = MathProblem(statement="Solve 2x + 3 = 7.")

    parsed = ProblemParser().parse(problem)

    assert parsed.statement == "Solve 2x + 3 = 7."
    assert parsed.numbers == [2.0, 3.0, 7.0]
    assert "x" in parsed.variables
    assert parsed.equations == ["Solve 2x + 3 = 7"]


@pytest.mark.asyncio
async def test_equation_solver_handles_simple_linear_equation_without_sympy() -> None:
    parsed = ProblemParser().parse(MathProblem(statement="Solve 2x + 3 = 7."))

    result = await EquationSolver().solve(parsed)

    assert result.solved is True
    assert result.result == "2"
    assert "manual_linear_solve" in result.evidence


@pytest.mark.asyncio
async def test_math_agent_solves_arithmetic_without_client() -> None:
    agent = MathematicalReasoningAgent()
    state = AgentState(
        task_id="math-task-1",
        original_prompt="What is 2 + 3 * 4?",
    )

    result = await agent(state)

    assert result.category == "mathematical_reasoning"
    assert result.selected_agent == "MathematicalReasoningAgent"
    assert result.llm_response == "14"
    assert result.validated_response is not None
    assert result.errors == []


@pytest.mark.asyncio
async def test_graph_routes_to_math_node() -> None:
    graph = build_graph(OrchestrationDependencies())
    state = AgentState(task_id="math-task-2", original_prompt="What is 2 + 3 * 4?")

    result = await graph.ainvoke(state)

    assert result.category == "mathematical_reasoning"
    assert result.selected_agent == "MathematicalReasoningAgent"
    assert result.llm_response == "14"
