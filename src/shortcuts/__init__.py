"""Deterministic zero-token shortcuts.

Each category may register a solver that returns a final answer string when it
is provably correct, or ``None`` to defer to the LLM. The pipeline consults
:func:`try_shortcut` before making any Fireworks call.
"""
from __future__ import annotations

from collections.abc import Callable

from src.config.constants import (
    MATHEMATICAL_REASONING,
)
from src.shortcuts.arithmetic import solve_math

# Registry of category -> deterministic solver. Categories absent here always
# go to the LLM. Solvers must never raise (the pipeline also guards this) and
# must return None whenever they are not certain.
_SOLVERS: dict[str, Callable[[str], str | None]] = {
    MATHEMATICAL_REASONING: solve_math,
}


def try_shortcut(category: str, prompt: str) -> str | None:
    """Return a deterministic answer for the prompt, or None to defer to LLM."""
    solver = _SOLVERS.get(category)
    if solver is None:
        return None
    try:
        return solver(prompt)
    except Exception:
        return None


__all__ = ["try_shortcut"]
