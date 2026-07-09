"""Base tool interface for category-owned tools."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.orchestration.state.agent_state import AgentState


class ToolProtocol(Protocol):
    """Tool contract independent of LangGraph."""

    name: str
    description: str

    async def arun(self, state: AgentState) -> AgentState:
        """Execute the tool against the current agent state."""


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Serializable tool metadata."""

    name: str
    description: str
