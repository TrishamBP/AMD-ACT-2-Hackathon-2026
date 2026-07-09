"""Mathematical reasoning category agent."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from src.orchestration.logging import log_node_event
from src.orchestration.mathematical_reasoning.guardrails import MathGuardrails
from src.orchestration.mathematical_reasoning.classifier import ProblemClassifier
from src.orchestration.mathematical_reasoning.parser import ProblemParser
from src.orchestration.mathematical_reasoning.prompt_builder import (
    build_math_prompt,
    build_math_repair_prompt,
)
from src.orchestration.mathematical_reasoning.schemas import (
    ExecutionMetadata,
    MathProblem,
    MathResponse,
    ParsedProblem,
    SolverResult,
    TokenUsage,
    ValidationResult,
)
from src.orchestration.mathematical_reasoning.solvers import (
    ArithmeticSolver,
    CalculatorTool,
    EquationSolver,
    GeometrySolver,
    NumberTheorySolver,
    ProbabilitySolver,
    ProblemType,
    SolverAggregator,
    SolverProtocol,
    StatisticsSolver,
    SympySolver,
    UnitConverter,
)
from src.orchestration.mathematical_reasoning.validators import MathValidator
from src.orchestration.state.agent_state import AgentState
from src.orchestration.tracing import track_tokens, trace_node


class MathClient(Protocol):
    """Injected model client contract for math fallback."""

    async def generate(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> str:
        """Generate a math answer."""


@dataclass(slots=True)
class MathematicalReasoningAgent:
    """Deterministic math node with Fireworks fallback only when required."""

    client: MathClient | None = None
    classifier: ProblemClassifier = field(default_factory=ProblemClassifier)
    parser: ProblemParser = field(default_factory=ProblemParser)
    calculator: CalculatorTool = field(default_factory=CalculatorTool)
    unit_converter: UnitConverter = field(default_factory=UnitConverter)
    equation_solver: EquationSolver = field(default_factory=EquationSolver)
    geometry_solver: GeometrySolver = field(default_factory=GeometrySolver)
    statistics_solver: StatisticsSolver = field(default_factory=StatisticsSolver)
    probability_solver: ProbabilitySolver = field(default_factory=ProbabilitySolver)
    number_theory_solver: NumberTheorySolver = field(default_factory=NumberTheorySolver)
    sympy_solver: SympySolver = field(default_factory=SympySolver)
    aggregator: SolverAggregator = field(default_factory=SolverAggregator)
    validator: MathValidator = field(default_factory=MathValidator)
    guardrails: MathGuardrails = field(default_factory=MathGuardrails)
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("src.orchestration.mathematical_reasoning")
    )
    selected_model: str | None = None
    fallback_threshold: float = 0.75
    max_tokens: int = 64
    repair_max_tokens: int = 48
    temperature: float = 0.0
    top_p: float = 1.0

    @property
    def tools(self) -> list[str]:
        """Return tool names owned by the agent."""
        return [
            self.calculator.name,
            self.unit_converter.name,
            self.equation_solver.name,
            self.geometry_solver.name,
            self.statistics_solver.name,
            self.probability_solver.name,
            self.number_theory_solver.name,
            self.sympy_solver.name,
        ]

    def _build_problem(self, state: AgentState) -> MathProblem:
        return MathProblem(
            statement=state.original_prompt,
            context=state.execution_metadata.get("context"),
            preferred_units=state.execution_metadata.get("preferred_units"),
        )

    def _seed_state(self, state: AgentState, prompt: str, parsed: ParsedProblem) -> AgentState:
        return state.model_copy(
            update={
                "category": "mathematical_reasoning",
                "selected_agent": "MathematicalReasoningAgent",
                "prompt_template": prompt,
                "available_tools": self.tools,
                "execution_metadata": {
                    **state.execution_metadata,
                    "math": {
                        "problem_type": parsed.problem_type,
                        "confidence": parsed.confidence,
                        "evidence": parsed.evidence,
                    },
                },
            }
        )

    async def _run_deterministic_solvers(self, parsed: ParsedProblem) -> list[SolverResult]:
        solvers: list[SolverProtocol] = []
        if parsed.problem_type == ProblemType.ARITHMETIC:
            solvers.append(self.calculator)
        if parsed.problem_type == ProblemType.UNIT_CONVERSION:
            solvers.append(self.unit_converter)
        if parsed.problem_type in {
            ProblemType.ALGEBRA,
            ProblemType.PROPORTIONS,
            ProblemType.LINEAR_ALGEBRA,
        }:
            solvers.append(self.equation_solver)
        if parsed.problem_type == ProblemType.GEOMETRY:
            solvers.append(self.geometry_solver)
        if parsed.problem_type == ProblemType.STATISTICS:
            solvers.append(self.statistics_solver)
        if parsed.problem_type in {ProblemType.PROBABILITY, ProblemType.COMBINATORICS}:
            solvers.append(self.probability_solver)
        if parsed.problem_type == ProblemType.NUMBER_THEORY:
            solvers.append(self.number_theory_solver)
        if parsed.problem_type == ProblemType.CALCULUS:
            solvers.append(self.sympy_solver)
        if not solvers:
            solvers.append(self.calculator)
            solvers.append(self.sympy_solver)

        results: list[SolverResult] = []
        for solver in solvers:
            results.append(await solver.solve(parsed))
        return results

    async def _generate(self, prompt: str, model: str, *, repair: bool = False) -> str:
        if self.client is None:
            return ""
        max_tokens = self.repair_max_tokens if repair else self.max_tokens
        return await self.client.generate(
            prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
        )

    def _build_response(
        self,
        answer: str,
        parsed: ParsedProblem,
        validation: ValidationResult,
        solver_result: SolverResult | None,
        metadata: ExecutionMetadata,
        repaired: bool,
    ) -> MathResponse:
        return MathResponse(
            answer=answer,
            parsed_problem=parsed,
            solver_result=solver_result,
            validation=validation,
            metadata=metadata,
            token_usage=TokenUsage(),
            repaired=repaired,
            extra={"problem_type": parsed.problem_type},
        )

    @trace_node("MathematicalReasoningAgent")
    @track_tokens
    async def __call__(self, state: AgentState) -> AgentState:
        """Solve math tasks deterministically and fall back only when needed."""
        problem = self.guardrails.validate_input(self._build_problem(state))
        parsed = self.parser.parse(problem)
        deterministic_results = await self._run_deterministic_solvers(parsed)
        best_result, aggregated_confidence, evidence = self.aggregator.aggregate(
            deterministic_results
        )
        prompt = build_math_prompt(problem, parsed)
        working_state = self._seed_state(state, prompt, parsed)
        working_state = working_state.model_copy(
            update={
                "execution_metadata": {
                    **working_state.execution_metadata,
                    "math": {
                        **working_state.execution_metadata.get("math", {}),
                        "aggregated_confidence": aggregated_confidence,
                        "solver_evidence": evidence,
                        "selected_solver": best_result.solver_name if best_result else None,
                    },
                }
            }
        )

        if best_result and best_result.solved and aggregated_confidence >= self.fallback_threshold:
            validation = self.validator.validate(best_result.result, parsed)
            if validation.valid:
                response = self._build_response(
                    answer=validation.normalized_answer,
                    parsed=parsed,
                    validation=validation,
                    solver_result=best_result,
                    metadata=ExecutionMetadata(
                        task_id=state.task_id,
                        node_name="MathematicalReasoningAgent",
                        problem_type=parsed.problem_type,
                        selected_solver=best_result.solver_name,
                        solver_confidence=aggregated_confidence,
                        fallback_used=False,
                    ),
                    repaired=False,
                )
                validated_output = self.guardrails.validate_output(response)
                log_node_event(
                    "math_solved_deterministically",
                    task_id=state.task_id,
                    node="MathematicalReasoningAgent",
                    problem_type=parsed.problem_type,
                    selected_solver=best_result.solver_name,
                    solver_confidence=aggregated_confidence,
                    fallback_used=False,
                )
                return working_state.model_copy(
                    update={
                        "llm_response": validation.normalized_answer,
                        "validated_response": validated_output.model_dump(),
                        "token_usage": validated_output.token_usage,
                    }
                )

        if self.client is None:
            return working_state.model_copy(
                update={"errors": [*working_state.errors, "math_model_client_not_configured"]}
            )

        model = state.selected_model or self.selected_model
        if model is None:
            return working_state.model_copy(
                update={"errors": [*working_state.errors, "selected_model_missing"]}
            )

        fallback_used = True
        raw_answer = await self._generate(prompt, model)
        validation = self.validator.validate(raw_answer, parsed)
        repaired = False

        if not validation.valid:
            repair_prompt = build_math_repair_prompt(
                problem,
                parsed,
                raw_answer,
                validation.errors,
            )
            raw_answer = await self._generate(repair_prompt, model, repair=True)
            validation = self.validator.validate(raw_answer, parsed)
            repaired = True

        response = self._build_response(
            answer=validation.normalized_answer or raw_answer,
            parsed=parsed,
            validation=validation,
            solver_result=best_result,
            metadata=ExecutionMetadata(
                task_id=state.task_id,
                node_name="MathematicalReasoningAgent",
                problem_type=parsed.problem_type,
                selected_solver=best_result.solver_name if best_result else "fireworks",
                solver_confidence=aggregated_confidence,
                fallback_used=fallback_used,
                repair_attempts=1 if repaired else 0,
            ),
            repaired=repaired,
        )
        validated_output = self.guardrails.validate_output(response)
        log_node_event(
            "math_fallback_used",
            task_id=state.task_id,
            node="MathematicalReasoningAgent",
            problem_type=parsed.problem_type,
            selected_solver=best_result.solver_name if best_result else "fireworks",
            solver_confidence=aggregated_confidence,
            fallback_used=True,
            repair_attempts=1 if repaired else 0,
        )
        return working_state.model_copy(
            update={
                "llm_response": validation.normalized_answer or raw_answer,
                "validated_response": validated_output.model_dump(),
                "token_usage": validated_output.token_usage,
                "errors": [*working_state.errors, *validation.errors],
            }
        )
