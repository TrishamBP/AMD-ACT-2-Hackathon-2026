"""Code generation category agent."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from src.orchestration.code_generation.guardrails import CodeGenerationGuardrails
from src.orchestration.code_generation.prompt_builder import (
    build_code_generation_prompt,
    build_code_repair_prompt,
)
from src.orchestration.code_generation.templates import match_template
from src.orchestration.code_generation.schemas import (
    CodeGenerationConfig,
    CodeGenerationInput,
    CodeGenerationOutput,
    Metadata,
    SpecSummary,
    TokenUsage,
    ValidationResult,
)
from src.orchestration.code_generation.tools import CodeGenerationToolSet
from src.orchestration.logging import log_node_event
from src.orchestration.state.agent_state import AgentState
from src.orchestration.tracing import track_tokens, trace_node
from src.orchestration.validators.response_validator import ResponseValidator


class CodeGenerationClient(Protocol):
    """Injected model client contract for code generation."""

    async def generate(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> str:
        """Generate a code response."""


@dataclass(slots=True)
class CodeGenerationAgent:
    """Deterministic code generation node with a single Fireworks call."""

    client: CodeGenerationClient | None = None
    tools: CodeGenerationToolSet = field(default_factory=CodeGenerationToolSet)
    guardrails: CodeGenerationGuardrails = field(default_factory=CodeGenerationGuardrails)
    validator: ResponseValidator = field(default_factory=ResponseValidator)
    config: CodeGenerationConfig = field(default_factory=CodeGenerationConfig)
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("src.orchestration.code_generation")
    )

    @property
    def tool_names(self) -> list[str]:
        """Return registered tool names."""
        return self.tools.names()

    def _build_input(self, state: AgentState) -> CodeGenerationInput:
        return CodeGenerationInput(
            request=state.original_prompt,
            context=state.execution_metadata.get("context"),
            preferred_language=state.execution_metadata.get("preferred_language"),
        )

    def _seed_state(self, state: AgentState, prompt: str, spec_language: str) -> AgentState:
        return state.model_copy(
            update={
                "category": "code_generation",
                "selected_agent": "CodeGenerationAgent",
                "prompt_template": prompt,
                "available_tools": self.tool_names,
                "selected_model": state.selected_model or self.config.model,
                "execution_metadata": {
                    **state.execution_metadata,
                    "code_generation": {
                        "language": spec_language,
                        "available_tools": self.tool_names,
                    },
                },
            }
        )

    async def _generate(
        self,
        prompt: str,
        model: str,
        *,
        repair: bool = False,
    ) -> str:
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

    async def _deterministic_pipeline(
        self,
        payload: CodeGenerationInput,
    ) -> tuple[str, str, str, SpecSummary, list[str], list[str], list[str], str]:
        language_spec = await self.tools.language_detector.arun(
            payload.request,
            preferred_language=payload.preferred_language,
        )
        complexity_spec = await self.tools.complexity_detector.arun(payload.request)
        spec = await self.tools.spec_extractor.arun(
            payload.request,
            language_spec,
            complexity_spec,
        )
        prompt = build_code_generation_prompt(payload, spec)
        return (
            language_spec.language,
            complexity_spec.level,
            prompt,
            spec,
            language_spec.evidence,
            complexity_spec.evidence,
            spec.constraints,
            spec.intent,
        )

    async def _validate_and_format(
        self,
        language: str,
        code: str,
    ) -> ValidationResult:
        validation = await self.tools.validator.arun(language, code)
        formatted = await self.tools.formatter.arun(language, validation.formatted_code)
        return validation.model_copy(update={"formatted_code": formatted})

    @trace_node("CodeGenerationAgent")
    @track_tokens
    async def __call__(self, state: AgentState) -> AgentState:
        """Generate deterministic code with a single LLM call and optional repair."""
        payload = self.guardrails.validate_input(self._build_input(state))

        # Try template matching first (0 tokens)
        template_code = match_template(state.original_prompt)
        if template_code is not None:
            log_node_event(
                "code_template_hit",
                task_id=state.task_id,
                node="CodeGenerationAgent",
                method="template",
            )
            # Return simple response bypassing complex schemas
            return state.model_copy(
                update={
                    "llm_response": template_code,
                    "validated_response": {"code": template_code, "template_matched": True},
                    "token_usage": TokenUsage(),
                }
            )

        # Fallback to LLM
        (
            language,
            complexity,
            prompt,
            spec,
            lang_evidence,
            comp_evidence,
            constraints,
            intent,
        ) = (
            await self._deterministic_pipeline(payload)
        )
        working_state = self._seed_state(state, prompt, language)
        working_state = working_state.model_copy(
            update={
                "execution_metadata": {
                    **working_state.execution_metadata,
                    "code_generation": {
                        "language": language,
                        "complexity": complexity,
                        "spec": spec.model_dump(),
                        "language_evidence": lang_evidence,
                        "complexity_evidence": comp_evidence,
                        "constraints": constraints,
                        "intent": intent,
                    },
                }
            }
        )

        if self.client is None:
            return working_state.model_copy(
                update={"errors": [*working_state.errors, "code_model_client_not_configured"]}
            )

        model = working_state.selected_model or self.config.model
        if model is None:
            return working_state.model_copy(
                update={"errors": [*working_state.errors, "selected_model_missing"]}
            )

        raw_code = await self._generate(prompt, model)
        validation = await self._validate_and_format(language, raw_code)
        repaired = False

        if not validation.valid:
            repair_prompt = build_code_repair_prompt(
                payload,
                spec,
                raw_code,
                validation.errors,
            )
            raw_code = await self._generate(repair_prompt, model, repair=True)
            validation = await self._validate_and_format(language, raw_code)
            repaired = True

        output = CodeGenerationOutput(
            code=raw_code,
            formatted_code=validation.formatted_code,
            spec=spec,
            validation=validation,
            repaired=repaired,
            metadata=Metadata(
                task_id=state.task_id,
                node_name="CodeGenerationAgent",
                category="code_generation",
                selected_model=model,
                selected_agent="CodeGenerationAgent",
                tools=self.tool_names,
                extra={
                    "language": language,
                    "complexity": complexity,
                },
            ),
            token_usage=TokenUsage(),
            extra={
                "repair_attempted": repaired,
            },
        )
        validated_output = self.guardrails.validate_output(output)
        log_node_event(
            "code_generation_output_validated",
            task_id=state.task_id,
            node="CodeGenerationAgent",
            category="code_generation",
            selected_model=model,
            repaired=repaired,
        )
        return working_state.model_copy(
            update={
                "llm_response": raw_code,
                "validated_response": validated_output.model_dump(),
                "token_usage": validated_output.token_usage,
                "errors": [*working_state.errors, *validation.errors],
            }
        )
