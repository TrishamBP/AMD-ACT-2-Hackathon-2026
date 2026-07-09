"""Guardrails skeleton for factual knowledge execution."""
from __future__ import annotations

from typing import Any

from src.orchestration.factual_knowledge.schemas import (
    FactualKnowledgeInput,
    FactualKnowledgeOutput,
)
from src.orchestration.validators.response_validator import ResponseValidator


class FactualKnowledgeGuardrails:
    """Placeholder guardrails hooks for factual knowledge tasks."""

    def __init__(self, validator: ResponseValidator | None = None) -> None:
        self._validator = validator or ResponseValidator()

    def validate_input(self, payload: FactualKnowledgeInput) -> FactualKnowledgeInput:
        """Validate factual knowledge input."""
        return self._validator.validate_factual_input(payload)

    def validate_output(
        self,
        payload: FactualKnowledgeOutput | dict[str, Any],
    ) -> FactualKnowledgeOutput:
        """Validate factual knowledge output."""
        return self._validator.validate_factual_output(payload)

    def validate_length(self, answer: str, *, limit: int = 2048) -> bool:
        """Validate response length."""
        return len(answer) <= limit

    def check_hallucination(self, output: FactualKnowledgeOutput) -> bool:
        """Placeholder hallucination check."""
        return True

    def validate_schema(self, payload: dict[str, Any]) -> FactualKnowledgeOutput:
        """Validate response schema."""
        return self._validator.validate_factual_output(payload)
