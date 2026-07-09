"""Logical reasoning category agent."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from src.orchestration.logging import log_node_event
from src.orchestration.logical_reasoning.guardrails import LogicalReasoningGuardrails
from src.orchestration.logical_reasoning.prompt_builder import (
    build_logical_reasoning_prompt,
    build_logical_reasoning_repair_prompt,
)
from src.orchestration.logical_reasoning.schemas import (
    LogicalReasoningConfig,
    LogicalReasoningInput,
    LogicalReasoningOutput,
    ParsedLogicalProblem,
    ReasoningDecision,
    ReasoningSolution,
    TokenUsage,
    ValidationResult,
)
from src.orchestration.logical_reasoning.solvers import SolverRegistry
from src.orchestration.logical_reasoning.tools import LogicalReasoningToolSet
from src.orchestration.state.agent_state import AgentState
from src.orchestration.tracing import track_tokens, trace_node


class LogicalReasoningClient(Protocol):
    """Injected model client contract for logical fallback."""

    async def generate(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> str:
        """Generate a logic answer."""


@dataclass(slots=True)
class LogicalReasoningAgent:
    """Deterministic logical reasoning node with Fireworks fallback only when required."""

    client: LogicalReasoningClient | None = None
    tools: LogicalReasoningToolSet = field(default_factory=LogicalReasoningToolSet)
    solvers: SolverRegistry = field(default_factory=SolverRegistry)
    guardrails: LogicalReasoningGuardrails = field(default_factory=LogicalReasoningGuardrails)
    config: LogicalReasoningConfig = field(default_factory=LogicalReasoningConfig)
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("src.orchestration.logical_reasoning")
    )

    @property
    def tool_names(self) -> list[str]:
        """Return registered tool names."""
        return self.tools.names()

    def _build_input(self, state: AgentState) -> LogicalReasoningInput:
        return LogicalReasoningInput(
            request=state.original_prompt,
            context=state.execution_metadata.get("context"),
            preferred_format=state.execution_metadata.get("preferred_format"),
        )

    def _seed_state(
        self,
        state: AgentState,
        prompt: str,
        parsed: ParsedLogicalProblem,
    ) -> AgentState:
        return state.model_copy(
            update={
                "category": "logical_reasoning",
                "selected_agent": "LogicalReasoningAgent",
                "prompt_template": prompt,
                "available_tools": self.tool_names,
                "execution_metadata": {
                    **state.execution_metadata,
                    "logical_reasoning": {
                        "reasoning_type": parsed.reasoning_type,
                        "confidence": parsed.confidence,
                        "evidence": parsed.evidence,
                    },
                },
            }
        )

    def _validate_answer(self, answer: str, parsed: ParsedLogicalProblem) -> ValidationResult:
        normalized = " ".join(answer.replace("\u2212", "-").split())
        errors: list[str] = []
        if not normalized:
            errors.append("empty_answer")
        if parsed.reasoning_type in {"truth_tables", "deductive_reasoning", "rule_based_reasoning"} and not normalized:
            errors.append("expected_nonempty_answer")
        return ValidationResult(
            valid=not errors,
            errors=errors,
            normalized_answer=normalized,
            consistent=not errors,
            constraint_satisfied=not errors,
        )

    def _build_output(
        self,
        *,
        task_id: str | None,
        answer: str,
        parsed: ParsedLogicalProblem,
        decision: ReasoningDecision,
        validation: ValidationResult,
        solution: ReasoningSolution | None,
        repaired: bool,
    ) -> LogicalReasoningOutput:
        return LogicalReasoningOutput(
            answer=answer,
            parsed_problem=parsed,
            solution=solution,
            decision=decision,
            validation=validation,
            metadata={
                "task_id": task_id,
                "node_name": "LogicalReasoningAgent",
                "category": "logical_reasoning",
                "selected_model": self.config.model,
                "selected_agent": "LogicalReasoningAgent",
                "confidence": decision.confidence,
                "evidence": [*parsed.evidence, *(solution.evidence if solution else [])],
                "tools": self.tool_names,
                "extra": {
                    "reasoning_type": parsed.reasoning_type,
                    "selected_solver": solution.solver_name if solution else None,
                    "solver_confidence": decision.confidence,
                    "fallback_used": solution is None or not decision.solved,
                    "repair_attempts": 1 if repaired else 0,
                },
            },
            token_usage=TokenUsage(),
            repaired=repaired,
            extra={"reasoning_type": parsed.reasoning_type},
        )

    async def _generate(self, prompt: str, model: str, *, repair: bool = False) -> str:
        if self.client is None:
            return ""
        max_tokens = self.config.repair_max_tokens if repair else self.config.max_tokens
        return await self.client.generate(
            prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
        )

    @trace_node("LogicalReasoningAgent")
    @track_tokens
    async def __call__(self, state: AgentState) -> AgentState:
        """Solve logic tasks deterministically and fall back only when needed."""
        payload = self.guardrails.validate_input(self._build_input(state))
        parsed = await self.tools.constraint_extractor.arun(payload.request)
        results = await self.solvers.run(parsed)
        ordered = sorted(results, key=lambda item: (item.confidence, item.solved), reverse=True)
        best = ordered[0] if ordered else None
        prompt = build_logical_reasoning_prompt(payload, parsed)
        working_state = self._seed_state(state, prompt, parsed)
        decision = ReasoningDecision(
            confidence=best.confidence if best else 0.0,
            winner=best,
            evidence=[*parsed.evidence, *(best.evidence if best else [])],
            scores={item.solver_name: item.confidence for item in ordered},
            solved=bool(best and best.solved and best.confidence >= self.config.confidence_threshold),
        )

        if best and best.solved and decision.solved:
            validation = self._validate_answer(best.result, parsed)
            if validation.valid:
                output = self._build_output(
                    task_id=state.task_id,
                    answer=validation.normalized_answer,
                    parsed=parsed,
                    decision=decision,
                    validation=validation,
                    solution=best,
                    repaired=False,
                )
                validated_output = self.guardrails.validate_output(output)
                log_node_event(
                    "logical_reasoning_solved_deterministically",
                    task_id=state.task_id,
                    node="LogicalReasoningAgent",
                    reasoning_type=parsed.reasoning_type,
                    solver=best.solver_name,
                    confidence=decision.confidence,
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
                update={"errors": [*working_state.errors, "logical_reasoning_model_client_not_configured"]}
            )

        model = state.selected_model or self.config.model
        if model is None:
            return working_state.model_copy(
                update={"errors": [*working_state.errors, "selected_model_missing"]}
            )

        raw_answer = await self._generate(prompt, model)
        validation = self._validate_answer(raw_answer, parsed)
        repaired = False
        if not validation.valid:
            repair_prompt = build_logical_reasoning_repair_prompt(
                payload,
                parsed,
                raw_answer,
                validation.errors,
            )
            raw_answer = await self._generate(repair_prompt, model, repair=True)
            validation = self._validate_answer(raw_answer, parsed)
            repaired = True

        output = self._build_output(
            task_id=state.task_id,
            answer=validation.normalized_answer or raw_answer,
            parsed=parsed,
            decision=decision,
            validation=validation,
            solution=best,
            repaired=repaired,
        )
        validated_output = self.guardrails.validate_output(output)
        log_node_event(
            "logical_reasoning_fallback_used",
            task_id=state.task_id,
            node="LogicalReasoningAgent",
            reasoning_type=parsed.reasoning_type,
            solver=best.solver_name if best else "fireworks",
            confidence=decision.confidence,
            repaired=repaired,
        )
        return working_state.model_copy(
            update={
                "llm_response": validation.normalized_answer or raw_answer,
                "validated_response": validated_output.model_dump(),
                "token_usage": validated_output.token_usage,
                "errors": [*working_state.errors, *validation.errors],
            }
        )
