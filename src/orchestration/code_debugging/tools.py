"""Deterministic tools for code debugging."""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any

from src.orchestration.code_debugging.schemas import (
    CodeDebuggingInput,
    ParsedDebuggingRequest,
    StaticAnalysisResult,
)
from src.orchestration.code_generation.tools import (
    AstValidatorTool,
    FormatterTool,
    LanguageDetectorTool,
)


@dataclass(slots=True)
class CodeParserTool:
    """Extract code and structured hints from a bug report."""

    syntax_checker: AstValidatorTool = field(default_factory=AstValidatorTool)
    language_detector: LanguageDetectorTool = field(default_factory=LanguageDetectorTool)

    async def arun(self, payload: CodeDebuggingInput) -> ParsedDebuggingRequest:
        text = payload.request.strip()
        code_blocks = self._extract_code_blocks(text)
        code = code_blocks[0] if code_blocks else self._extract_inline_code(text)
        language_spec = await self.language_detector.arun(
            text,
            preferred_language=payload.preferred_language,
        )
        syntax = await self.syntax_checker.arun(language_spec.language, code)
        bug_hints = self._extract_bug_hints(text, syntax.errors)
        return ParsedDebuggingRequest(
            request=text,
            language=language_spec.language,
            language_confidence=language_spec.confidence,
            code=code,
            code_blocks=code_blocks,
            syntax_valid=syntax.valid,
            syntax_error=syntax.errors[0] if syntax.errors else None,
            ast_valid=syntax.valid and language_spec.language == "python",
            lint_warnings=[],
            static_findings=[],
            bug_hints=bug_hints,
            evidence=[*language_spec.evidence, *syntax.errors],
            line_count=len(code.splitlines()) if code else 0,
        )

    def _extract_code_blocks(self, text: str) -> list[str]:
        blocks = re.findall(r"```(?:[a-zA-Z0-9_+-]+)?\n(.*?)```", text, flags=re.DOTALL)
        return [block.strip() for block in blocks if block.strip()]

    def _extract_inline_code(self, text: str) -> str:
        match = re.search(r"(?:Code|Snippet|Buggy code)\s*:\s*(.+)", text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return text

    def _extract_bug_hints(self, text: str, syntax_errors: list[str]) -> list[str]:
        hints: list[str] = []
        if syntax_errors:
            hints.extend(syntax_errors)
        for keyword in ("fix", "bug", "error", "fails", "broken", "debug"):
            if keyword in text.lower():
                hints.append(keyword)
        return hints


@dataclass(slots=True)
class StaticAnalysisTool:
    """Lightweight static analysis for Python snippets."""

    async def arun(self, language: str, code: str) -> StaticAnalysisResult:
        if not code.strip():
            return StaticAnalysisResult(
                valid=False,
                errors=["empty_code"],
                confidence=0.0,
                evidence=["no_code"],
            )
        if language != "python":
            return StaticAnalysisResult(
                valid=True,
                warnings=[],
                errors=[],
                confidence=0.3,
                evidence=["generic_static_analysis"],
            )
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return StaticAnalysisResult(
                valid=False,
                errors=[f"syntax_error:{exc.msg}"],
                confidence=0.0,
                evidence=["ast_parse_failed"],
            )
        visitor = _NameVisitor()
        visitor.visit(tree)
        warnings: list[str] = []
        for name in sorted(visitor.loads - visitor.definitions - _BUILTINS):
            warnings.append(f"undefined_name:{name}")
        return StaticAnalysisResult(
            valid=not warnings,
            warnings=warnings,
            errors=[],
            confidence=0.9 if not warnings else 0.55,
            evidence=["ast_parse_ok", f"loads:{len(visitor.loads)}"],
        )


class _NameVisitor(ast.NodeVisitor):
    """Collect names for lightweight static analysis."""

    def __init__(self) -> None:
        self.loads: set[str] = set()
        self.definitions: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.definitions.add(node.name)
        for arg in node.args.args:
            self.definitions.add(arg.arg)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self.definitions.add(node.name)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> Any:
        for target in node.targets:
            self._collect_target(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        self._collect_target(node.target)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> Any:
        self._collect_target(node.target)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            self.definitions.add(alias.asname or alias.name.split(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        for alias in node.names:
            self.definitions.add(alias.asname or alias.name)

    def visit_Name(self, node: ast.Name) -> Any:
        if isinstance(node.ctx, ast.Load):
            self.loads.add(node.id)

    def _collect_target(self, target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self.definitions.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                self._collect_target(item)


_BUILTINS = {
    "abs",
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "float",
    "int",
    "len",
    "list",
    "max",
    "min",
    "print",
    "range",
    "str",
    "sum",
    "zip",
}


@dataclass(slots=True)
class CodeDebuggingToolSet:
    """Owned tools for the debugging agent."""

    parser: CodeParserTool = field(default_factory=CodeParserTool)
    static_analyzer: StaticAnalysisTool = field(default_factory=StaticAnalysisTool)
    validator: AstValidatorTool = field(default_factory=AstValidatorTool)
    formatter: FormatterTool = field(default_factory=FormatterTool)

    def names(self) -> list[str]:
        """Return registered tool names."""
        return [
            "code_parser",
            "static_analyzer",
            self.validator.name,
            self.formatter.name,
        ]
