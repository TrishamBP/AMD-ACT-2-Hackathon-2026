"""Deterministic tools for logical reasoning."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.orchestration.code_generation.tools import LanguageDetectorTool
from src.orchestration.logical_reasoning.schemas import ParsedLogicalProblem


@dataclass(slots=True)
class ReasoningTypeDetectorTool:
    """Detect the type of reasoning required."""

    name: str = "reasoning_type_detector"

    async def arun(self, request: str) -> tuple[str, float, list[str]]:
        text = request.lower()
        scores: dict[str, float] = {
            "constraint_satisfaction": 0.0,
            "truth_tables": 0.0,
            "deductive_reasoning": 0.0,
            "scheduling": 0.0,
            "knights_and_knaves": 0.0,
            "grid_logic": 0.0,
            "symbolic_reasoning": 0.0,
            "transitive_inference": 0.0,
            "rule_based_reasoning": 0.0,
        }
        evidence: dict[str, list[str]] = {key: [] for key in scores}

        def add(key: str, amount: float, reason: str) -> None:
            scores[key] = min(1.0, scores[key] + amount)
            evidence[key].append(reason)

        for phrase in ("must", "cannot", "exactly", "at least", "at most", "different", "distinct"):
            if phrase in text:
                add("constraint_satisfaction", 0.16, phrase)
        for phrase in ("truth table", "boolean", "and", "or", "not", "xor"):
            if phrase in text:
                add("truth_tables", 0.15, phrase)
        for phrase in ("therefore", "implies", "deduce", "infer", "must be true", "must be false"):
            if phrase in text:
                add("deductive_reasoning", 0.18, phrase)
        for phrase in ("schedule", "calendar", "time slot", "meeting", "ordering", "precedence"):
            if phrase in text:
                add("scheduling", 0.18, phrase)
        for phrase in ("knight", "knaves", "liar", "truthful", "lying"):
            if phrase in text:
                add("knights_and_knaves", 0.22, phrase)
        for phrase in ("grid", "row", "column", "arrangement", "puzzle"):
            if phrase in text:
                add("grid_logic", 0.16, phrase)
        for phrase in ("symbolic", "equivalent", "expression", "simplify", "solve"):
            if phrase in text:
                add("symbolic_reasoning", 0.12, phrase)
        for phrase in ("transitive", "before", "after", "older than", "taller than", "greater than"):
            if phrase in text:
                add("transitive_inference", 0.18, phrase)
        for phrase in ("rule", "if", "then", "only if", "unless"):
            if phrase in text:
                add("rule_based_reasoning", 0.10, phrase)

        if "truth table" in text or re.search(r"\b(?:and|or|not|xor)\b", text):
            add("truth_tables", 0.2, "logic operators")
        if re.search(r"\b[a-z]\b", text) and any(op in text for op in ("=", ">", "<")):
            add("symbolic_reasoning", 0.1, "symbols")

        winner = max(scores.items(), key=lambda item: (item[1], item[0]))
        reasoning_type, score = winner
        return reasoning_type, score, evidence[reasoning_type]


@dataclass(slots=True)
class ConstraintExtractorTool:
    """Extract logical constraints from a prompt."""

    name: str = "constraint_extractor"

    async def arun(self, request: str) -> ParsedLogicalProblem:
        detector = ReasoningTypeDetectorTool()
        reasoning_type, confidence, evidence = await detector.arun(request)
        statements = [segment.strip() for segment in re.split(r"[;\n]", request) if segment.strip()]
        variables = sorted(set(re.findall(r"\b[A-Z]\b", request)))
        constraints = []
        objectives = []
        dependencies = []
        relationships = []
        rules = []
        normalized_clauses = []
        lower = request.lower()

        for keyword in ("must", "cannot", "exactly", "at least", "at most", "distinct", "unique"):
            if keyword in lower:
                constraints.append(keyword)
        for keyword in ("determine", "find", "solve", "infer", "deduce", "identify"):
            if keyword in lower:
                objectives.append(keyword)
        for keyword in ("if", "then", "only if", "unless"):
            if keyword in lower:
                rules.append(keyword)
        for keyword in ("before", "after", "older than", "taller than", "greater than"):
            if keyword in lower:
                relationships.append(keyword)
        for keyword in ("depends on", "requires", "given that"):
            if keyword in lower:
                dependencies.append(keyword)
        for segment in statements:
            normalized_clauses.append(segment.strip())

        return ParsedLogicalProblem(
            request=request,
            reasoning_type=reasoning_type,
            confidence=confidence,
            evidence=evidence,
            code="",
            statements=statements,
            rules=rules,
            variables=variables,
            constraints=constraints,
            objectives=objectives,
            dependencies=dependencies,
            relationships=relationships,
            normalized_clauses=normalized_clauses,
            line_count=len(statements),
        )


@dataclass(slots=True)
class LogicalReasoningToolSet:
    """Owned deterministic reasoning tools."""

    language_detector: LanguageDetectorTool = field(default_factory=LanguageDetectorTool)
    reasoning_detector: ReasoningTypeDetectorTool = field(default_factory=ReasoningTypeDetectorTool)
    constraint_extractor: ConstraintExtractorTool = field(default_factory=ConstraintExtractorTool)

    def names(self) -> list[str]:
        """Return registered tool names."""
        return [self.language_detector.name, self.reasoning_detector.name, self.constraint_extractor.name]
