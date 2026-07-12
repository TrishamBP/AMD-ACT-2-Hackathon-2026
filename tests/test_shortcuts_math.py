"""Tests for the deterministic math shortcut.

The overriding invariant: the shortcut must return a CORRECT answer or None.
It must never return a wrong answer, so word problems and anything ambiguous
must defer to the LLM (return None).
"""
from __future__ import annotations

import pytest

from src.shortcuts import try_shortcut
from src.shortcuts.arithmetic import solve_math


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("What is 2 + 2?", "4"),
        ("Calculate 12 * 12", "144"),
        ("Compute 100 / 4", "25"),
        ("What is 3 ^ 3?", "27"),
        ("Evaluate (5 + 3) * 2", "16"),
        ("7 - 9", "-2"),
        ("What is 15% of 240?", "36"),
        ("50% of 80", "40"),
    ],
)
def test_exact_arithmetic_is_solved(prompt: str, expected: str) -> None:
    assert solve_math(prompt) == expected


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("convert 1000 m to km", "1"),
        ("How much is 2 km in m?", "2000"),
        ("60 minutes in hours", "1"),
        ("convert 2 hours to minutes", "120"),
    ],
)
def test_unit_conversion_is_solved(prompt: str, expected: str) -> None:
    assert solve_math(prompt) == expected


@pytest.mark.parametrize(
    "prompt",
    [
        # Word problems: multi-step, must defer to the LLM.
        "A store has 240 items. It sells 15% on Monday and 60 more on Tuesday. "
        "How many items remain?",
        "If a train travels 60 miles in 2 hours, what is its average speed?",
        "Tom has 3 apples and buys 5 more, then gives away 2. How many are left?",
        # Not math at all.
        "What is the capital of Australia?",
        "Explain why the sky is blue.",
        # Bare number, no operation -> not answerable deterministically.
        "42",
        "What is 7?",
        # Division by zero -> defer rather than crash/guess.
        "What is 5 / 0?",
        # '%' is treated as percent, so bare 'a % b' modulo is ambiguous -> defer.
        "What is 10 % 3?",
    ],
)
def test_ambiguous_or_wordy_defers_to_llm(prompt: str) -> None:
    assert solve_math(prompt) is None


def test_dispatcher_routes_math_category() -> None:
    assert try_shortcut("mathematical_reasoning", "What is 6 * 7?") == "42"


def test_dispatcher_ignores_non_math_categories() -> None:
    assert try_shortcut("factual_knowledge", "What is 6 * 7?") is None
    assert try_shortcut("sentiment_classification", "2 + 2") is None


def test_dispatcher_never_raises_on_garbage() -> None:
    # Must swallow anything weird and defer.
    assert try_shortcut("mathematical_reasoning", "((((") is None
    assert try_shortcut("mathematical_reasoning", "") is None
