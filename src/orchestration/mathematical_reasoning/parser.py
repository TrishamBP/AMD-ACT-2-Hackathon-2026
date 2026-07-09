"""Problem parser for math tasks."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.orchestration.mathematical_reasoning.classifier import ProblemClassifier
from src.orchestration.mathematical_reasoning.schemas import MathProblem, ParsedProblem


@dataclass(slots=True)
class ProblemParser:
    """Extract structured math problem details."""

    classifier: ProblemClassifier = field(default_factory=ProblemClassifier)

    def parse(self, problem: MathProblem) -> ParsedProblem:
        classified = self.classifier.classify(problem)
        text = problem.statement
        lower = text.lower()
        numbers = [float(match) for match in re.findall(r"-?\d+(?:\.\d+)?", text)]
        variables = sorted(set(re.findall(r"\b[a-z]\b", lower)))
        operators = [op for op in "+-*/=^" if op in text]
        equations = []
        for segment in re.split(r"[;.\n]", text):
            if "=" not in segment:
                continue
            cleaned = re.sub(
                r"^(solve|simplify|evaluate|compute|find|determine|prove)\s+",
                "",
                segment.strip(),
                flags=re.IGNORECASE,
            )
            equations.append(cleaned)
        constraints = []
        for phrase in ("integer", "positive", "negative", "non-negative", "whole number", "prime", "distinct"):
            if phrase in lower:
                constraints.append(phrase)
        units = []
        for unit in ("cm", "mm", "m", "km", "kg", "g", "lb", "oz", "ft", "in", "mile", "miles", "l", "ml"):
            if re.search(rf"\b{re.escape(unit)}\b", lower):
                units.append(unit)
        requested_outputs = []
        for phrase in ("solve", "simplify", "evaluate", "compute", "find", "determine", "prove"):
            if phrase in lower:
                requested_outputs.append(phrase)

        return classified.model_copy(
            update={
                "numbers": numbers,
                "variables": variables,
                "operators": operators,
                "equations": equations,
                "constraints": constraints,
                "units": units,
                "requested_outputs": requested_outputs,
            }
        )
