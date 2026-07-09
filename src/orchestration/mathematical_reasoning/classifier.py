"""Deterministic math problem classifier."""
from __future__ import annotations

import re
from dataclasses import dataclass

from src.orchestration.mathematical_reasoning.schemas import MathProblem, ParsedProblem


@dataclass(slots=True)
class ProblemClassifier:
    """Classify math tasks into deterministic problem types."""

    def classify(self, problem: MathProblem) -> ParsedProblem:
        text = problem.statement.lower()
        scores: dict[str, tuple[float, list[str]]] = {
            "arithmetic": (0.0, []),
            "percentages": (0.0, []),
            "fractions": (0.0, []),
            "ratios": (0.0, []),
            "proportions": (0.0, []),
            "unit_conversion": (0.0, []),
            "algebra": (0.0, []),
            "geometry": (0.0, []),
            "probability": (0.0, []),
            "statistics": (0.0, []),
            "calculus": (0.0, []),
            "linear_algebra": (0.0, []),
            "number_theory": (0.0, []),
            "combinatorics": (0.0, []),
            "logic": (0.0, []),
        }

        def add(problem_type: str, amount: float, reason: str) -> None:
            score, evidence = scores[problem_type]
            scores[problem_type] = (min(1.0, score + amount), [*evidence, reason])

        keyword_map = {
            "percentages": (("percent", 0.35), ("percentage", 0.35), ("discount", 0.12), ("tax", 0.12)),
            "fractions": (("fraction", 0.35), ("numerator", 0.2), ("denominator", 0.2), ("rational", 0.15)),
            "ratios": (("ratio", 0.35), ("proportion", 0.18), ("share", 0.1)),
            "proportions": (("proportion", 0.35), ("scale", 0.12), ("directly proportional", 0.25)),
            "unit_conversion": (("convert", 0.3), ("inches", 0.12), ("meters", 0.12), ("hours", 0.1), ("kg", 0.1)),
            "algebra": (("solve for", 0.3), ("equation", 0.25), ("variable", 0.2), ("x", 0.08)),
            "geometry": (("triangle", 0.25), ("circle", 0.25), ("area", 0.2), ("perimeter", 0.2), ("volume", 0.2)),
            "probability": (("probability", 0.35), ("chance", 0.2), ("random", 0.2), ("expected value", 0.18)),
            "statistics": (("mean", 0.25), ("median", 0.25), ("mode", 0.25), ("variance", 0.2), ("standard deviation", 0.2)),
            "calculus": (("derivative", 0.35), ("integral", 0.35), ("limit", 0.25), ("differentiate", 0.3)),
            "linear_algebra": (("matrix", 0.3), ("vector", 0.25), ("eigen", 0.3), ("determinant", 0.25)),
            "number_theory": (("prime", 0.3), ("divisible", 0.2), ("mod", 0.18), ("gcd", 0.3), ("lcm", 0.3)),
            "combinatorics": (("count", 0.2), ("arrangements", 0.25), ("permutations", 0.3), ("combinations", 0.3)),
            "logic": (("if", 0.08), ("then", 0.08), ("only if", 0.12), ("truth", 0.12), ("prove", 0.15)),
            "arithmetic": (("add", 0.15), ("subtract", 0.15), ("multiply", 0.15), ("divide", 0.15)),
        }

        for problem_type, entries in keyword_map.items():
            for phrase, amount in entries:
                if phrase in text:
                    add(problem_type, amount, f"keyword:{phrase}")

        if re.search(r"[\+\-\*/=^]", text):
            add("arithmetic", 0.2, "operators")
        if re.search(r"\b\d+/\d+\b", text):
            add("fractions", 0.3, "fraction_pattern")
        if re.search(r"\b\d+(?:\.\d+)?%", text):
            add("percentages", 0.35, "percent_pattern")
        if re.search(r"\b(?:cm|mm|m|km|kg|g|lb|oz|ft|in|mile|miles|litre|liter|ml|l)\b", text):
            add("unit_conversion", 0.2, "unit_token")
        if len(re.findall(r"\b[a-z]\b", text)) >= 2:
            add("algebra", 0.12, "variables")
        if "=" in text and (
            re.search(r"\d\s*[a-z]", text) or re.search(r"\b[a-z]\b", text)
        ):
            add("algebra", 0.35, "equation_with_variable")

        winner = max(scores.items(), key=lambda item: (item[1][0], item[0]))
        problem_type, (confidence, evidence) = winner
        return ParsedProblem(
            problem_type=problem_type,
            confidence=min(1.0, confidence),
            evidence=evidence,
            statement=problem.statement,
        )
