"""Base deterministic handler protocol."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class DeterministicResult:
    """Result from a deterministic handler."""

    solved: bool
    answer: str
    confidence: float
    method: str


class DeterministicHandler(Protocol):
    """Protocol for deterministic task handlers that skip LLM calls."""

    def can_solve(self, prompt: str) -> bool:
        """Check if this handler can solve the task deterministically."""
        ...

    def solve(self, prompt: str) -> DeterministicResult:
        """Solve the task without calling an LLM."""
        ...
