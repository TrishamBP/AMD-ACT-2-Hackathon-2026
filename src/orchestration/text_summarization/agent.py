"""Text summarization category agent."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from src.orchestration.logging import log_node_event
from src.orchestration.state.agent_state import AgentState
from src.orchestration.summarization.extractive import extractive_summarize
from src.orchestration.text_summarization.guardrails import SummaryGuardrails
from src.orchestration.text_summarization.preprocessing import (
    ConstraintExtractor,
    DocumentAnalyzer,
    TextNormalizer,
)
from src.orchestration.text_summarization.prompt_builder import (
    build_summary_prompt,
    build_summary_repair_prompt,
)
from src.orchestration.text_summarization.schemas import (
    DocumentProfile,
    ExecutionMetadata,
    SummaryConstraints,
    SummaryRequest,
    SummaryResponse,
    SummaryValidation,
    TokenUsage,
)
from src.orchestration.text_summarization.validators import SummaryValidator
from src.orchestration.tracing import track_tokens, trace_node


class SummaryClient(Protocol):
    """Injected model client contract for summarization."""

    async def generate(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> str:
        """Generate a summary."""


@dataclass(slots=True)
class TextSummarizationAgent:
    """Deterministic summarization node with one generation call and one repair attempt."""

    client: SummaryClient | None = None
    normalizer: TextNormalizer = field(default_factory=TextNormalizer)
    constraint_extractor: ConstraintExtractor = field(default_factory=ConstraintExtractor)
    analyzer: DocumentAnalyzer = field(default_factory=DocumentAnalyzer)
    validator: SummaryValidator = field(default_factory=SummaryValidator)
    guardrails: SummaryGuardrails = field(default_factory=SummaryGuardrails)
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("src.orchestration.text_summarization")
    )
    default_max_tokens: int = 120
    repair_max_tokens: int = 80
    temperature: float = 0.0
    top_p: float = 1.0

    def _build_request(self, state: AgentState) -> SummaryRequest:
        return SummaryRequest(
            text=state.original_prompt,
            context=state.execution_metadata.get("context"),
            preferred_language=state.execution_metadata.get("preferred_language"),
            preferred_format=state.execution_metadata.get("preferred_format"),
        )

    def _seed_state(
        self,
        state: AgentState,
        prompt: str,
        constraints: SummaryConstraints,
        profile: DocumentProfile,
    ) -> AgentState:
        return state.model_copy(
            update={
                "category": "text_summarization",
                "selected_agent": "TextSummarizationAgent",
                "prompt_template": prompt,
                "available_tools": [],
                "execution_metadata": {
                    **state.execution_metadata,
                    "summary": {
                        "constraints": constraints.model_dump(),
                        "profile": profile.model_dump(),
                    },
                },
            }
        )

    async def _generate(self, prompt: str, model: str, *, repair: bool = False) -> str:
        if self.client is None:
            return ""
        max_tokens = self.repair_max_tokens if repair else self.default_max_tokens
        return await self.client.generate(
            prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
        )

    def _build_output(
        self,
        summary: str,
        constraints: SummaryConstraints,
        validation: SummaryValidation,
        metadata: ExecutionMetadata,
        repaired: bool,
        profile: DocumentProfile,
    ) -> SummaryResponse:
        return SummaryResponse(
            summary=summary,
            constraints=constraints,
            validation=validation,
            metadata=metadata,
            token_usage=TokenUsage(),
            repaired=repaired,
            extra={"document_profile": profile.model_dump()},
        )

    @trace_node("TextSummarizationAgent")
    @track_tokens
    async def __call__(self, state: AgentState) -> AgentState:
        """Summarize text with deterministic preprocessing and one repair attempt."""
        request = self.guardrails.validate_input(self._build_request(state))
        normalized_text, removed_blanks = self.normalizer.normalize(request.text)
        profile = self.analyzer.analyze(request.text)
        constraints, evidence = self.constraint_extractor.extract(
            normalized_text,
            preferred_format=request.preferred_format,
        )
        constraints.evidence = [*constraints.evidence, *evidence]

        # Try extractive summarization first (0 tokens)
        # Extract the actual text to summarize from the prompt
        text_to_summarize = normalized_text
        if "summarize" in normalized_text.lower() or "summary" in normalized_text.lower():
            # Extract text after "summarize:" or similar markers
            import re
            match = re.search(r'(?:summarize|summary)[^:]*:\s*(.+)', normalized_text, re.IGNORECASE | re.DOTALL)
            if match:
                text_to_summarize = match.group(1).strip()

        # Try extractive summarization
        if len(text_to_summarize) > 50:  # Only for substantial text
            extractive_summary = extractive_summarize(text_to_summarize, max_sentences=1)
            if len(extractive_summary) > 20:  # Ensure meaningful summary
                log_node_event(
                    "summary_extractive_hit",
                    task_id=state.task_id,
                    node="TextSummarizationAgent",
                    method="extractive",
                )
                # Build minimal validation and output
                validation = SummaryValidation(
                    valid=True,
                    errors=[],
                    word_count=len(extractive_summary.split()),
                    sentence_count=1,
                )
                metadata = ExecutionMetadata(
                    task_id=state.task_id,
                    node_name="TextSummarizationAgent",
                    selected_model="extractive",
                    repair_attempts=0,
                    summary_length=len(extractive_summary),
                )
                output = self._build_output(
                    summary=extractive_summary,
                    constraints=constraints,
                    validation=validation,
                    metadata=metadata,
                    repaired=False,
                    profile=profile,
                )
                validated_output = self.guardrails.validate_output(output)
                return state.model_copy(
                    update={
                        "llm_response": extractive_summary,
                        "validated_response": validated_output.model_dump(),
                        "token_usage": validated_output.token_usage,
                    }
                )

        # Fallback to LLM
        prompt = build_summary_prompt(request, constraints, profile)
        working_state = self._seed_state(state, prompt, constraints, profile)
        working_state = working_state.model_copy(
            update={
                "execution_metadata": {
                    **working_state.execution_metadata,
                    "summary": {
                        **working_state.execution_metadata.get("summary", {}),
                        "normalized_text": normalized_text,
                        "removed_blank_lines": removed_blanks,
                    },
                }
            }
        )

        if self.client is None:
            return working_state.model_copy(
                update={"errors": [*working_state.errors, "summary_model_client_not_configured"]}
            )

        model = working_state.selected_model
        if model is None:
            return working_state.model_copy(
                update={"errors": [*working_state.errors, "selected_model_missing"]}
            )

        summary_text = await self._generate(prompt, model)
        validation = self.validator.validate(summary_text, constraints)
        repaired = False

        if not validation.valid:
            repair_prompt = build_summary_repair_prompt(
                request,
                constraints,
                summary_text,
                validation.errors,
            )
            summary_text = await self._generate(repair_prompt, model, repair=True)
            validation = self.validator.validate(summary_text, constraints)
            repaired = True

        metadata = ExecutionMetadata(
            task_id=state.task_id,
            node_name="TextSummarizationAgent",
            selected_model=model,
            repair_attempts=1 if repaired else 0,
            summary_length=len(summary_text),
        )
        output = self._build_output(
            summary=summary_text,
            constraints=constraints,
            validation=validation,
            metadata=metadata,
            repaired=repaired,
            profile=profile,
        )
        validated_output = self.guardrails.validate_output(output)
        log_node_event(
            "summary_validated",
            task_id=state.task_id,
            node="TextSummarizationAgent",
            selected_model=model,
            summary_length=len(summary_text),
            repair_attempts=metadata.repair_attempts,
        )
        return working_state.model_copy(
            update={
                "llm_response": summary_text,
                "validated_response": validated_output.model_dump(),
                "token_usage": validated_output.token_usage,
                "execution_metadata": {
                    **working_state.execution_metadata,
                    "summary": {
                        **working_state.execution_metadata.get("summary", {}),
                        "execution_metadata": metadata.model_dump(),
                        "validation": validation.model_dump(),
                    },
                },
            }
        )
