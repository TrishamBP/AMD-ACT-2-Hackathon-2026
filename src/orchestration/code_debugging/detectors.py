"""Deterministic bug detectors and confidence aggregation."""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Protocol

from src.orchestration.code_debugging.schemas import (
    BugDetectionResult,
    DebuggingDecision,
    ParsedDebuggingRequest,
    StaticAnalysisResult,
)


class BugDetector(Protocol):
    """Protocol for bug detectors."""

    name: str
    bug_types: tuple[str, ...]

    async def run(
        self,
        parsed: ParsedDebuggingRequest,
        static_analysis: StaticAnalysisResult,
    ) -> BugDetectionResult:
        """Detect a bug and optionally suggest a fix."""


@dataclass(slots=True)
class MissingColonDetector:
    """Detect missing colons after Python block headers."""

    name: str = "missing_colon_detector"
    bug_types: tuple[str, ...] = ("missing_colon",)

    async def run(
        self,
        parsed: ParsedDebuggingRequest,
        static_analysis: StaticAnalysisResult,
    ) -> BugDetectionResult:
        lines = parsed.code.splitlines()
        fixed_lines: list[str] = []
        changed = False
        for line in lines:
            stripped = line.rstrip()
            if re.match(r"^\s*(if|elif|else|for|while|def|class|try|except|finally|with)\b", stripped):
                if not stripped.endswith(":"):
                    fixed_lines.append(f"{stripped}:")
                    changed = True
                    continue
            fixed_lines.append(line)
        if not changed:
            return BugDetectionResult(
                detector_name=self.name,
                bug_type="missing_colon",
                confidence=0.0,
                evidence=["no_missing_colon"],
                solved=False,
            )
        return BugDetectionResult(
            detector_name=self.name,
            bug_type="missing_colon",
            confidence=0.94,
            evidence=["header_without_colon"],
            suggested_fix="add_colon",
            fixed_code="\n".join(fixed_lines),
            solved=True,
        )


@dataclass(slots=True)
class MissingBodyDetector:
    """Detect a missing body after a Python block header."""

    name: str = "missing_body_detector"
    bug_types: tuple[str, ...] = ("missing_body",)

    async def run(
        self,
        parsed: ParsedDebuggingRequest,
        static_analysis: StaticAnalysisResult,
    ) -> BugDetectionResult:
        lines = parsed.code.splitlines()
        last_header = -1
        for index, line in enumerate(lines):
            if line.rstrip().endswith(":"):
                last_header = index
        if last_header < 0:
            return BugDetectionResult(
                detector_name=self.name,
                bug_type="missing_body",
                confidence=0.0,
                evidence=["no_block_header"],
                solved=False,
            )
        trailing = lines[last_header + 1 :]
        if any(item.strip() for item in trailing):
            return BugDetectionResult(
                detector_name=self.name,
                bug_type="missing_body",
                confidence=0.0,
                evidence=["body_present"],
                solved=False,
            )
        indent = re.match(r"^(\s*)", lines[last_header]).group(1) if lines else ""
        body = f"{indent}    pass"
        fixed = [*lines[: last_header + 1], body, *trailing]
        return BugDetectionResult(
            detector_name=self.name,
            bug_type="missing_body",
            confidence=0.9,
            evidence=["empty_block_body"],
            suggested_fix="insert_pass_body",
            fixed_code="\n".join(fixed),
            solved=True,
        )


@dataclass(slots=True)
class UnbalancedDelimiterDetector:
    """Detect unbalanced delimiters and close the missing ones."""

    name: str = "unbalanced_delimiter_detector"
    bug_types: tuple[str, ...] = ("unbalanced_delimiter",)
    _pairs: dict[str, str] = field(default_factory=lambda: {"(": ")", "[": "]", "{": "}"})

    async def run(
        self,
        parsed: ParsedDebuggingRequest,
        static_analysis: StaticAnalysisResult,
    ) -> BugDetectionResult:
        opens: list[str] = []
        for char in parsed.code:
            if char in self._pairs:
                opens.append(char)
            elif char in self._pairs.values() and opens:
                expected = self._pairs[opens[-1]]
                if char == expected:
                    opens.pop()
        if not opens:
            return BugDetectionResult(
                detector_name=self.name,
                bug_type="unbalanced_delimiter",
                confidence=0.0,
                evidence=["balanced"],
                solved=False,
            )
        closing = "".join(self._pairs[char] for char in reversed(opens))
        return BugDetectionResult(
            detector_name=self.name,
            bug_type="unbalanced_delimiter",
            confidence=0.84,
            evidence=[f"missing:{closing}"],
            suggested_fix="append_missing_delimiters",
            fixed_code=f"{parsed.code.rstrip()}{closing}",
            solved=True,
        )


@dataclass(slots=True)
class UndefinedNameDetector:
    """Detect likely undefined names from static analysis warnings."""

    name: str = "undefined_name_detector"
    bug_types: tuple[str, ...] = ("undefined_name",)

    async def run(
        self,
        parsed: ParsedDebuggingRequest,
        static_analysis: StaticAnalysisResult,
    ) -> BugDetectionResult:
        if not static_analysis.warnings:
            return BugDetectionResult(
                detector_name=self.name,
                bug_type="undefined_name",
                confidence=0.0,
                evidence=["no_warnings"],
                solved=False,
            )
        warnings = [warning for warning in static_analysis.warnings if "undefined_name" in warning]
        if not warnings:
            return BugDetectionResult(
                detector_name=self.name,
                bug_type="undefined_name",
                confidence=0.0,
                evidence=["no_undefined_names"],
                solved=False,
            )
        return BugDetectionResult(
            detector_name=self.name,
            bug_type="undefined_name",
            confidence=min(0.72, 0.35 + 0.1 * len(warnings)),
            evidence=warnings,
            suggested_fix="define_or_import_missing_name",
            solved=False,
        )


@dataclass(slots=True)
class BugDetectorRegistry:
    """Registry of deterministic bug detectors."""

    detectors: list[BugDetector] = field(
        default_factory=lambda: [
            MissingColonDetector(),
            MissingBodyDetector(),
            UnbalancedDelimiterDetector(),
            UndefinedNameDetector(),
        ]
    )

    async def run(
        self,
        parsed: ParsedDebuggingRequest,
        static_analysis: StaticAnalysisResult,
    ) -> list[BugDetectionResult]:
        results: list[BugDetectionResult] = []
        for detector in self.detectors:
            results.append(await detector.run(parsed, static_analysis))
        return results


@dataclass(slots=True)
class ConfidenceAggregator:
    """Combine syntax, static analysis, and detector confidence."""

    threshold: float = 0.75

    def aggregate(
        self,
        syntax_confidence: float,
        static_confidence: float,
        detections: list[BugDetectionResult],
    ) -> DebuggingDecision:
        if not detections:
            return DebuggingDecision(
                confidence=0.0,
                evidence=["no_detections"],
                scores={},
                solved=False,
            )
        ordered = sorted(detections, key=lambda item: (item.confidence, item.solved), reverse=True)
        winner = ordered[0]
        scores = {item.bug_type: item.confidence for item in ordered}
        total = min(1.0, 0.1 * syntax_confidence + 0.05 * static_confidence + 0.85 * winner.confidence)
        evidence = [*winner.evidence, f"syntax:{syntax_confidence:g}", f"static:{static_confidence:g}"]
        return DebuggingDecision(
            confidence=total,
            winner=winner,
            evidence=evidence,
            scores=scores,
            solved=winner.solved and total >= self.threshold,
        )
