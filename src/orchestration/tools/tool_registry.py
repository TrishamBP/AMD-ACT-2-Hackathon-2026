"""Tool registry for category-owned tool sets."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from src.orchestration.tools.base_tool import ToolProtocol, ToolSpec


@dataclass(slots=True)
class ToolRegistry:
    """Registry of tools keyed by agent name."""

    _tools: dict[str, list[ToolProtocol]] = field(default_factory=dict)

    def register(self, agent_name: str, tools: Iterable[ToolProtocol]) -> None:
        """Register tools for a category agent."""
        self._tools[agent_name] = list(tools)

    def get(self, agent_name: str) -> list[ToolProtocol]:
        """Return the tools registered for an agent."""
        return list(self._tools.get(agent_name, []))

    def specs(self, agent_name: str) -> list[ToolSpec]:
        """Return serializable tool specs for an agent."""
        return [
            ToolSpec(name=tool.name, description=tool.description)
            for tool in self.get(agent_name)
        ]
