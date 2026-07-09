"""Guardrails skeleton for summarization."""
from __future__ import annotations

from typing import Any

from src.orchestration.text_summarization.schemas import (
    SummaryRequest,
    SummaryResponse,
)
from src.orchestration.text_summarization.validators import SummaryValidator


class SummaryGuardrails:
    """Placeholder guardrails hooks for text summarization."""

    def __init__(self, validator: SummaryValidator | None = None) -> None:
        self._validator = validator or SummaryValidator()

    def validate_input(self, payload: SummaryRequest) -> SummaryRequest:
        """Validate summarization input."""
        return payload

    def validate_output(self, payload: SummaryResponse | dict[str, Any]) -> SummaryResponse:
        """Validate summarization output."""
        if isinstance(payload, SummaryResponse):
            return payload
        return SummaryResponse.model_validate(payload)

    def validate_length(self, summary: str, *, limit: int = 2048) -> bool:
        """Validate summary length."""
        return len(summary) <= limit

    def check_hallucination(self, output: SummaryResponse) -> bool:
        """Placeholder hallucination check."""
        return True

    def validate_schema(self, payload: dict[str, Any]) -> SummaryResponse:
        """Validate summary schema."""
        return SummaryResponse.model_validate(payload)
