"""Validation helpers for orchestration responses."""
from __future__ import annotations

from typing import Any

from src.orchestration.factual_knowledge.schemas import (
    FactualKnowledgeInput,
    FactualKnowledgeOutput,
)
from src.orchestration.state.agent_state import AgentState


class ResponseValidator:
    """Skeleton validation layer for node outputs."""

    def validate_state(self, state: AgentState) -> AgentState:
        """Validate generic agent state."""
        return state

    def validate_factual_input(self, payload: FactualKnowledgeInput) -> FactualKnowledgeInput:
        """Validate factual knowledge input."""
        return FactualKnowledgeInput.model_validate(payload.model_dump())

    def validate_factual_output(
        self,
        payload: FactualKnowledgeOutput | dict[str, Any],
    ) -> FactualKnowledgeOutput:
        """Validate factual knowledge output."""
        if isinstance(payload, FactualKnowledgeOutput):
            return payload
        return FactualKnowledgeOutput.model_validate(payload)

    def validate_length(self, text: str, *, limit: int = 2048) -> bool:
        """Validate text length."""
        return len(text) <= limit

    def validate_schema(self, payload: dict[str, Any]) -> FactualKnowledgeOutput:
        """Validate response schema."""
        return FactualKnowledgeOutput.model_validate(payload)

    def check_hallucination(self, output: FactualKnowledgeOutput) -> bool:
        """Placeholder hallucination check."""
        return True
