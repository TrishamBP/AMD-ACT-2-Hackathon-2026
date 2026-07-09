"""Validator node wrapper."""
from __future__ import annotations

from dataclasses import dataclass, field

from src.orchestration.state.agent_state import AgentState
from src.orchestration.tracing import track_tokens, trace_node
from src.orchestration.validators.response_validator import ResponseValidator


@dataclass(slots=True)
class ValidatorNode:
    """Final graph node that validates the current state."""

    validator: ResponseValidator = field(default_factory=ResponseValidator)

    @trace_node("Validator")
    @track_tokens
    async def __call__(self, state: AgentState) -> AgentState:
        """Validate the final state and return it unchanged."""
        return self.validator.validate_state(state)
