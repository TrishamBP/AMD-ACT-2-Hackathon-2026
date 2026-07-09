"""Deterministic validators for math answers."""
from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction

from src.orchestration.mathematical_reasoning.schemas import ParsedProblem, ValidationResult


@dataclass(slots=True)
class MathValidator:
    """Validate generated math answers deterministically."""

    def validate(self, answer: str, parsed: ParsedProblem) -> ValidationResult:
        text = answer.strip()
        errors: list[str] = []
        normalized = self._normalize(text)
        numeric_value = self._parse_numeric(normalized)
        is_equation = "=" in normalized

        if not normalized:
            errors.append("empty_answer")
        if parsed.problem_type in {"arithmetic", "percentages", "fractions", "probability", "statistics", "number_theory"}:
            if numeric_value is None and not is_equation:
                errors.append("expected_numeric_answer")
        if parsed.problem_type in {"algebra", "equation", "proportions"} and not is_equation:
            if numeric_value is None and not re.search(r"[a-z]\s*=", normalized.lower()):
                errors.append("expected_equation_or_expression")

        return ValidationResult(
            valid=not errors,
            errors=errors,
            normalized_answer=normalized,
            numeric_value=numeric_value,
            units=self._extract_units(normalized),
            is_equation=is_equation,
        )

    def _normalize(self, text: str) -> str:
        return " ".join(text.replace("\u2212", "-").split())

    def _parse_numeric(self, text: str) -> float | None:
        fraction_match = re.fullmatch(r"(-?\d+)\s*/\s*(\d+)", text)
        if fraction_match:
            numerator = int(fraction_match.group(1))
            denominator = int(fraction_match.group(2))
            return float(Fraction(numerator, denominator))
        try:
            return float(text)
        except ValueError:
            return None

    def _extract_units(self, text: str) -> str | None:
        match = re.search(r"\b(?:cm|mm|m|km|kg|g|lb|oz|ft|in|mile|miles|l|ml|%)\b", text.lower())
        if match:
            return match.group(0)
        return None
