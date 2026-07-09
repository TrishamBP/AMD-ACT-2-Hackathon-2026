"""Code debugging category agent."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from src.orchestration.code_debugging.detectors import (
    BugDetectorRegistry,
    ConfidenceAggregator,
)
from src.orchestration.code_debugging.guardrails import CodeDebuggingGuardrails
from src.orchestration.code_debugging.prompt_builder import (
    build_code_debugging_prompt,
    build_code_debugging_repair_prompt,
)
from src.orchestration.code_debugging.schemas import (
    BugDetectionResult,
    CodeDebuggingConfig,
    CodeDebuggingInput,
    CodeDebuggingOutput,
    ParsedDebuggingRequest,
    StaticAnalysisResult,
    TokenUsage,
    ValidationResult,
)
from src.orchestration.code_debugging.tools import CodeDebuggingToolSet
from src.orchestration.logging import log_node_event
from src.orchestration.state.agent_state import AgentState
from src.orchestration.tracing import track_tokens, trace_node


class CodeDebuggingClient(Protocol):
    """Injected model client contract for debugging fallback."""

    async def generate(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> str:
        """Generate a code fix."""


@dataclass(slots=True)
class CodeDebuggingAgent:
    """Compiler-like debugging node with deterministic first-pass fixes."""

    client: CodeDebuggingClient | None = None
    tools: CodeDebuggingToolSet = field(default_factory=CodeDebuggingToolSet)
    detectors: BugDetectorRegistry = field(default_factory=BugDetectorRegistry)
    aggregator: ConfidenceAggregator = field(default_factory=ConfidenceAggregator)
    guardrails: CodeDebuggingGuardrails = field(default_factory=CodeDebuggingGuardrails)
    config: CodeDebuggingConfig = field(default_factory=CodeDebuggingConfig)
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("src.orchestration.code_debugging")
    )

    @property
    def tool_names(self) -> list[str]:
        """Return registered tool names."""
        return self.tools.names()

    def _build_input(self, state: AgentState) -> CodeDebuggingInput:
        return CodeDebuggingInput(
            request=state.original_prompt,
            context=state.execution_metadata.get("context"),
            preferred_language=state.execution_metadata.get("preferred_language"),
        )

    def _seed_state(
        self,
        state: AgentState,
        prompt: str,
        parsed: ParsedDebuggingRequest,
    ) -> AgentState:
        return state.model_copy(
            update={
                "category": "code_debugging",
                "selected_agent": "CodeDebuggingAgent",
                "prompt_template": prompt,
                "available_tools": self.tool_names,
                "execution_metadata": {
                    **state.execution_metadata,
                    "code_debugging": {
                        "language": parsed.language,
                        "language_confidence": parsed.language_confidence,
                        "code_lines": parsed.line_count,
                    },
                },
            }
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

    def _validate_code(self, language: str, code: str) -> ValidationResult:
        validation = self.tools.validator
        result = validation._validate_python(code) if language == "python" else None
        if result is None:
            generic = validation._validate_generic(code)
            return ValidationResult(
                valid=generic.valid,
                errors=generic.errors,
                normalized_code=generic.formatted_code,
                syntax_valid=generic.valid,
                lint_valid=generic.valid,
                static_valid=generic.valid,
            )
        return ValidationResult(
            valid=result.valid,
            errors=result.errors,
            normalized_code=result.formatted_code,
            syntax_valid=result.valid,
            lint_valid=result.valid,
            static_valid=result.valid,
        )

    def _build_output(
        self,
        *,
        task_id: str | None,
        code: str,
        formatted_code: str,
        parsed: ParsedDebuggingRequest,
        detections: list[BugDetectionResult],
        static_analysis: StaticAnalysisResult,
        validation: ValidationResult,
        decision_confidence: float,
        winner: BugDetectionResult | None,
        repaired: bool,
    ) -> CodeDebuggingOutput:
        return CodeDebuggingOutput(
            code=code,
            formatted_code=formatted_code,
            parsed_request=parsed,
            analysis=detections,
            static_analysis=static_analysis,
            decision={
                "confidence": decision_confidence,
                "winner": winner.model_dump() if winner else None,
                "evidence": [*parsed.evidence],
                "scores": {item.bug_type: item.confidence for item in detections},
                "solved": winner.solved if winner else False,
            },
            validation=validation,
            metadata={
                "task_id": task_id,
                "node_name": "CodeDebuggingAgent",
                "category": "code_debugging",
                "selected_agent": "CodeDebuggingAgent",
                "tools": self.tool_names,
                "confidence": decision_confidence,
                "evidence": [*parsed.evidence, *(winner.evidence if winner else [])],
            },
            token_usage=TokenUsage(),
            repaired=repaired,
            extra={
                "selected_detector": winner.detector_name if winner else None,
            },
        )

    @trace_node("CodeDebuggingAgent")
    @track_tokens
    async def __call__(self, state: AgentState) -> AgentState:
        """Fix buggy code using deterministic detectors first."""
        payload = self.guardrails.validate_input(self._build_input(state))
        parsed = await self.tools.parser.arun(payload)
        static_analysis = await self.tools.static_analyzer.arun(parsed.language, parsed.code)
        detections = await self.detectors.run(parsed, static_analysis)
        syntax_confidence = 1.0 if parsed.syntax_valid else 0.2
        static_confidence = static_analysis.confidence
        decision = self.aggregator.aggregate(syntax_confidence, static_confidence, detections)
        prompt = build_code_debugging_prompt(payload, parsed)
        working_state = self._seed_state(state, prompt, parsed)
        working_state = working_state.model_copy(
            update={
                "execution_metadata": {
                    **working_state.execution_metadata,
                    "code_debugging": {
                        **working_state.execution_metadata.get("code_debugging", {}),
                        "decision_confidence": decision.confidence,
                        "selected_detector": decision.winner.detector_name if decision.winner else None,
                    },
                }
            }
        )

        if decision.solved and decision.winner and decision.winner.fixed_code:
            validation = self._validate_code(parsed.language, decision.winner.fixed_code)
            if validation.valid:
                formatted = validation.normalized_code
                output = self._build_output(
                    task_id=state.task_id,
                    code=decision.winner.fixed_code,
                    formatted_code=formatted,
                    parsed=parsed,
                    detections=detections,
                    static_analysis=static_analysis,
                    validation=validation,
                    decision_confidence=decision.confidence,
                    winner=decision.winner,
                    repaired=False,
                )
                validated_output = self.guardrails.validate_output(output)
                log_node_event(
                    "code_debugging_solved_deterministically",
                    task_id=state.task_id,
                    node="CodeDebuggingAgent",
                    language=parsed.language,
                    detector=decision.winner.detector_name,
                    confidence=decision.confidence,
                )
                return working_state.model_copy(
                    update={
                        "llm_response": formatted,
                        "validated_response": validated_output.model_dump(),
                        "token_usage": validated_output.token_usage,
                    }
                )

        if self.client is None:
            return working_state.model_copy(
                update={"errors": [*working_state.errors, "code_debugging_model_client_not_configured"]}
            )

        model = state.selected_model or self.config.model
        if model is None:
            return working_state.model_copy(
                update={"errors": [*working_state.errors, "selected_model_missing"]}
            )

        raw_code = await self._generate(prompt, model)
        validation = self._validate_code(parsed.language, raw_code)
        repaired = False

        if not validation.valid:
            repair_prompt = build_code_debugging_repair_prompt(
                payload,
                parsed,
                raw_code,
                validation.errors,
            )
            raw_code = await self._generate(repair_prompt, model, repair=True)
            validation = self._validate_code(parsed.language, raw_code)
            repaired = True

        output = self._build_output(
            task_id=state.task_id,
            code=raw_code,
            formatted_code=validation.normalized_code or raw_code,
            parsed=parsed,
            detections=detections,
            static_analysis=static_analysis,
            validation=validation,
            decision_confidence=decision.confidence,
            winner=decision.winner,
            repaired=repaired,
        )
        validated_output = self.guardrails.validate_output(output)
        log_node_event(
            "code_debugging_fallback_used",
            task_id=state.task_id,
            node="CodeDebuggingAgent",
            language=parsed.language,
            detector=decision.winner.detector_name if decision.winner else None,
            confidence=decision.confidence,
            repaired=repaired,
        )
        return working_state.model_copy(
            update={
                "llm_response": validation.normalized_code or raw_code,
                "validated_response": validated_output.model_dump(),
                "token_usage": validated_output.token_usage,
                "errors": [*working_state.errors, *validation.errors],
            }
        )
