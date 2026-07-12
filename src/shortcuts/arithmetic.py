"""Deterministic, zero-token math shortcuts.

Every function here returns a final answer string ONLY when the result is
provably exact. On any ambiguity it returns ``None`` so the caller falls back
to the LLM. This guarantees the shortcut can never lower accuracy.
"""
from __future__ import annotations

import ast
import operator
import re
from collections.abc import Callable
from fractions import Fraction
from typing import Any

# Safe binary/unary operators for arithmetic evaluation.
_BIN_OPS: dict[type[ast.AST], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARY_OPS: dict[type[ast.AST], Callable[[Any], Any]] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Lead-in phrases we strip before deciding a prompt is a bare expression.
_LEADINS = (
    "what is",
    "what's",
    "calculate",
    "compute",
    "evaluate",
    "find the value of",
    "find",
    "solve",
    "the value of",
    "how much is",
    "result of",
)

# Length units -> metres (exact where possible).
_LENGTH: dict[str, Fraction] = {
    "mm": Fraction(1, 1000),
    "cm": Fraction(1, 100),
    "m": Fraction(1),
    "km": Fraction(1000),
    "in": Fraction(254, 10000),
    "inch": Fraction(254, 10000),
    "inches": Fraction(254, 10000),
    "ft": Fraction(3048, 10000),
    "foot": Fraction(3048, 10000),
    "feet": Fraction(3048, 10000),
    "yd": Fraction(9144, 10000),
    "yard": Fraction(9144, 10000),
    "yards": Fraction(9144, 10000),
}
_MASS: dict[str, Fraction] = {
    "mg": Fraction(1, 1000),
    "g": Fraction(1),
    "kg": Fraction(1000),
    "t": Fraction(1_000_000),
    "tonne": Fraction(1_000_000),
    "tonnes": Fraction(1_000_000),
}
_TIME: dict[str, Fraction] = {
    "s": Fraction(1),
    "sec": Fraction(1),
    "second": Fraction(1),
    "seconds": Fraction(1),
    "min": Fraction(60),
    "minute": Fraction(60),
    "minutes": Fraction(60),
    "h": Fraction(3600),
    "hr": Fraction(3600),
    "hour": Fraction(3600),
    "hours": Fraction(3600),
    "day": Fraction(86400),
    "days": Fraction(86400),
}
_UNIT_MAPS = (_LENGTH, _MASS, _TIME)


def _format_number(value: float | int | Fraction) -> str:
    """Render a numeric result without spurious floating-point noise."""
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return str(value.numerator)
        as_float = float(value)
        return _format_number(as_float)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        # Round to a stable precision, then trim trailing zeros.
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def _safe_eval(expr: str) -> float | int | Fraction | None:
    """Evaluate an arithmetic expression using a restricted AST walker."""
    try:
        node = ast.parse(expr, mode="eval")
    except (SyntaxError, ValueError):
        return None

    def _eval(sub: ast.AST) -> float | int | Fraction:
        if isinstance(sub, ast.Expression):
            return _eval(sub.body)
        if isinstance(sub, ast.Constant):
            if isinstance(sub.value, bool) or not isinstance(sub.value, int | float):
                raise ValueError("non_numeric_constant")
            return sub.value
        if isinstance(sub, ast.BinOp):
            op = _BIN_OPS.get(type(sub.op))
            if op is None:
                raise ValueError("unsupported_operator")
            return op(_eval(sub.left), _eval(sub.right))
        if isinstance(sub, ast.UnaryOp):
            op = _UNARY_OPS.get(type(sub.op))
            if op is None:
                raise ValueError("unsupported_unary")
            return op(_eval(sub.operand))
        raise ValueError("unsupported_expression")

    try:
        return _eval(node)
    except (ValueError, ZeroDivisionError, OverflowError, TypeError):
        return None


def _normalize(prompt: str) -> str:
    text = prompt.strip()
    # Drop a single trailing question mark / period and surrounding whitespace.
    text = text.rstrip("?. \t\n")
    lowered = text.lower()
    for lead in _LEADINS:
        if lowered.startswith(lead):
            text = text[len(lead):].lstrip(" :")
            break
    return text.strip()


def _try_percent_of(text: str) -> str | None:
    """Handle 'X% of Y' exactly."""
    match = re.fullmatch(
        r"\s*(-?\d+(?:\.\d+)?)\s*%\s*of\s*(-?\d+(?:\.\d+)?)\s*",
        text,
        re.IGNORECASE,
    )
    if match is None:
        return None
    pct = Fraction(match.group(1)) / 100
    base = Fraction(match.group(2))
    return _format_number(pct * base)


def _try_bare_expression(text: str) -> str | None:
    """Evaluate a prompt that is purely an arithmetic expression.

    Fires only when every character is part of a number, operator, or bracket
    (plus an optional trailing '%' converted to '/100'). Any stray letter or
    word means the prompt is a word problem -> return None.
    """
    candidate = text.strip()
    if not candidate:
        return None
    # Convert a trailing standalone percent like "20% of" is handled elsewhere;
    # here we only accept pure math with no letters at all.
    normalized = candidate.replace("^", "**").replace("x", "*").replace("×", "*").replace("÷", "/")
    if not re.fullmatch(r"[\d\s+\-*/().%]+", normalized):
        return None
    if not re.search(r"\d", normalized):
        return None
    # Require at least one operator so we don't "answer" a lone number.
    if not re.search(r"[+\-*/%]", normalized):
        return None
    # Turn a standalone '%' operator into '/100' (e.g. "50%" -> "(50/100)").
    normalized = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", normalized)
    result = _safe_eval(normalized)
    if result is None:
        return None
    return _format_number(result)


def _try_unit_conversion(text: str) -> str | None:
    """Handle 'convert A <unit> to <unit>' / 'A <unit> in <unit>' exactly."""
    match = re.search(
        r"(-?\d+(?:\.\d+)?)\s*([a-zA-Z]+)\s+(?:to|in|into)\s+([a-zA-Z]+)",
        text,
    )
    if match is None:
        return None
    value = Fraction(match.group(1))
    source = match.group(2).lower()
    target = match.group(3).lower()
    for unit_map in _UNIT_MAPS:
        if source in unit_map and target in unit_map:
            result = value * unit_map[source] / unit_map[target]
            return _format_number(result)
    return None


def solve_math(prompt: str) -> str | None:
    """Return an exact math answer, or None to defer to the LLM."""
    text = _normalize(prompt)

    for solver in (_try_bare_expression, _try_percent_of, _try_unit_conversion):
        try:
            answer = solver(text)
        except Exception:
            answer = None
        if answer is not None:
            return answer
    return None
