"""Deterministic tools for code generation."""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

from src.orchestration.code_generation.schemas import (
    ComplexitySpec,
    LanguageSpec,
    SpecSummary,
    ValidationResult,
)


@dataclass(slots=True)
class LanguageDetectorTool:
    """Detect the requested programming language."""

    name: str = "language_detector"
    description: str = "Detect programming language from the request."

    _patterns: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
        ("python", ("python", "py"), ("def ", "import ", "from ", "class ", "self")),
        (
            "javascript",
            ("javascript", "js", "typescript", "ts"),
            ("console.log", "function ", "=>", "const ", "let "),
        ),
        (
            "java",
            ("java",),
            ("public static void", "System.out.println", "class ", "new "),
        ),
        ("rust", ("rust",), ("fn ", "let mut", "println!", "impl ", "use ")),
        ("go", ("go", "golang"), ("package main", "func ", "fmt.Println", "fmt.Printf")),
        (
            "csharp",
            ("c#", "csharp", "dotnet"),
            ("using ", "namespace ", "Console.WriteLine", "public class"),
        ),
    )

    async def arun(self, request: str, preferred_language: str | None = None) -> LanguageSpec:
        """Detect the language using zero-token heuristics."""
        text = request.lower()
        scores: dict[str, tuple[float, list[str], list[str]]] = {}

        for language, keywords, signals in self._patterns:
            score = 0.0
            evidence: list[str] = []
            for keyword in keywords:
                if keyword in text:
                    score += 0.2
                    evidence.append(f"keyword:{keyword}")
            for signal in signals:
                if signal.lower() in text:
                    score += 0.3
                    evidence.append(f"signal:{signal}")
            scores[language] = (score, evidence, [])

        if preferred_language:
            key = preferred_language.lower().strip()
            if key in scores:
                score, evidence, extensions = scores[key]
                scores[key] = (score + 0.15, [*evidence, "preferred_language"], extensions)

        score, evidence, extensions = scores["python"]
        scores["python"] = (score + 0.10, [*evidence, "default_python"], extensions)

        winner = max(scores.items(), key=lambda item: (item[1][0], item[0]))[0]
        score, evidence, extensions = scores[winner]
        formatter = "python_ast" if winner == "python" else "generic"
        if winner == "python":
            extensions = [".py"]
        elif winner == "javascript":
            extensions = [".js", ".ts"]
        elif winner == "java":
            extensions = [".java"]
        elif winner == "rust":
            extensions = [".rs"]
        elif winner == "go":
            extensions = [".go"]
        elif winner == "csharp":
            extensions = [".cs"]

        return LanguageSpec(
            language=winner,
            confidence=min(1.0, score),
            evidence=evidence,
            formatter=formatter,
            extensions=list(extensions),
        )


@dataclass(slots=True)
class ComplexityDetectorTool:
    """Estimate task complexity from heuristics."""

    name: str = "complexity_detector"
    description: str = "Estimate code task complexity."

    async def arun(self, request: str) -> ComplexitySpec:
        """Estimate complexity from simple signals."""
        text = request.lower()
        score = 0.0
        evidence: list[str] = []

        def add(amount: float, reason: str) -> None:
            nonlocal score
            score += amount
            evidence.append(reason)

        if len(request) > 240:
            add(0.18, "long_request")
        if request.count("\n") >= 4:
            add(0.15, "multi_line_request")
        if re.search(r"\b(function|class|module|service|api|endpoint|parser)\b", text):
            add(0.18, "multiple_code_entities")
        if re.search(r"\b(recursion|recursive|dynamic programming|dp|memo|memoization)\b", text):
            add(0.18, "algorithmic_pattern")
        if re.search(r"\b(concurrent|async|thread|lock|race|network|socket|http|queue)\b", text):
            add(0.20, "systems_constraint")
        if re.search(r"\b(raft|consensus|scheduler|database|compiler|interpreter)\b", text):
            add(0.22, "complex_domain")
        if re.search(
            r"\b(lru cache|balanced tree|topological sort|bfs|dfs|merge sorted|factorial)\b",
            text,
        ):
            add(0.10, "classic_problem")

        level = "simple"
        if score >= 0.45:
            level = "hard"
        elif score >= 0.22:
            level = "medium"

        return ComplexitySpec(level=level, score=min(1.0, score), evidence=evidence)


@dataclass(slots=True)
class SpecExtractorTool:
    """Extract a compact spec from a code request."""

    name: str = "spec_extractor"
    description: str = "Extract inputs, outputs, and constraints."

    async def arun(
        self,
        request: str,
        language: LanguageSpec,
        complexity: ComplexitySpec,
    ) -> SpecSummary:
        """Extract a structured specification."""
        text = request.strip()
        lower = text.lower()
        inputs: list[str] = []
        outputs: list[str] = []
        constraints: list[str] = []
        keywords: list[str] = []

        for pattern, label in (
            (r"takes? ([^.]+?)(?: and| to| that|\.|$)", "input"),
            (r"accepts? ([^.]+?)(?: and| to| that|\.|$)", "input"),
            (r"returns? ([^.]+?)(?: and|\.|$)", "output"),
            (r"produce[s]? ([^.]+?)(?: and|\.|$)", "output"),
        ):
            match = re.search(pattern, lower)
            if match:
                value = match.group(1).strip()
                if label == "input":
                    inputs.append(value)
                else:
                    outputs.append(value)

        constraint_phrases = (
            "o(n)",
            "o(log n)",
            "preserve order",
            "no duplicates",
            "in place",
            "constant space",
            "thread-safe",
            "async",
        )
        for phrase in constraint_phrases:
            if phrase in lower:
                constraints.append(phrase)

        for token in re.findall(r"[A-Za-z_]{3,}", text):
            lowered = token.lower()
            if lowered not in keywords and lowered not in {"write", "code", "function", "return"}:
                keywords.append(lowered)
            if len(keywords) >= 8:
                break

        intent = text.splitlines()[0].strip() if text else "code_generation"
        return SpecSummary(
            intent=intent,
            language=language,
            complexity=complexity,
            inputs=inputs,
            outputs=outputs,
            constraints=constraints,
            keywords=keywords,
        )


@dataclass(slots=True)
class AstValidatorTool:
    """Validate and normalize generated code."""

    name: str = "ast_validator"
    description: str = "Validate syntax and normalize code."

    async def arun(self, language: str, code: str) -> ValidationResult:
        """Validate code for the requested language."""
        cleaned = self._strip_code_fences(code)
        if language == "python":
            return self._validate_python(cleaned)
        return self._validate_generic(cleaned)

    def _validate_python(self, code: str) -> ValidationResult:
        try:
            parsed = ast.parse(code)
        except SyntaxError as exc:
            return ValidationResult(
                valid=False,
                formatted_code=code,
                errors=[f"syntax_error:{exc.msg}"],
            )

        formatted = ast.unparse(parsed)
        return ValidationResult(valid=True, formatted_code=formatted, errors=[])

    def _validate_generic(self, code: str) -> ValidationResult:
        errors: list[str] = []
        if not code.strip():
            errors.append("empty_code")
        if code.count("{") != code.count("}"):
            errors.append("unbalanced_braces")
        if code.count("(") != code.count(")"):
            errors.append("unbalanced_parentheses")
        if code.count("[") != code.count("]"):
            errors.append("unbalanced_brackets")

        formatted = "\n".join(line.rstrip() for line in code.strip().splitlines())
        return ValidationResult(valid=not errors, formatted_code=formatted, errors=errors)

    def _strip_code_fences(self, code: str) -> str:
        stripped = code.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            inner = stripped[3:-3].strip()
            if "\n" in inner:
                inner = inner.split("\n", 1)[1].strip()
            return inner
        return stripped


@dataclass(slots=True)
class FormatterTool:
    """Normalize code output after validation."""

    name: str = "formatter"
    description: str = "Format code for the detected language."

    async def arun(self, language: str, code: str) -> str:
        """Format code with deterministic rules."""
        cleaned = code.strip()
        if language == "python":
            try:
                return ast.unparse(ast.parse(cleaned))
            except SyntaxError:
                return cleaned
        return "\n".join(line.rstrip() for line in cleaned.splitlines())


@dataclass(slots=True)
class CodeGenerationToolSet:
    """Owned tools for the code generation agent."""

    language_detector: LanguageDetectorTool = field(default_factory=LanguageDetectorTool)
    complexity_detector: ComplexityDetectorTool = field(default_factory=ComplexityDetectorTool)
    spec_extractor: SpecExtractorTool = field(default_factory=SpecExtractorTool)
    validator: AstValidatorTool = field(default_factory=AstValidatorTool)
    formatter: FormatterTool = field(default_factory=FormatterTool)

    def names(self) -> list[str]:
        """Return registered tool names."""
        return [
            self.language_detector.name,
            self.complexity_detector.name,
            self.spec_extractor.name,
            self.validator.name,
            self.formatter.name,
        ]
