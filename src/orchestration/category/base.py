"""Shared base for category nodes."""
from __future__ import annotations

from src.orchestration.state.agent_state import AgentState


class CategoryAgentBase:
    """Minimal pass-through category agent."""

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name

    async def __call__(self, state: AgentState) -> AgentState:
        """Return state unchanged."""
        return state
