"""Deterministic mathematical solvers."""
from __future__ import annotations

import ast
import math
import operator
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Protocol

from src.orchestration.mathematical_reasoning.schemas import ParsedProblem, SolverResult

try:  # pragma: no cover - optional dependency
    import sympy as _sympy  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency
    _sympy = None


class SolverProtocol(Protocol):
    """Contract for math solvers."""

    name: str
    problem_types: tuple[str, ...]

    async def solve(self, problem: ParsedProblem) -> SolverResult:
        """Solve a parsed math problem."""


class ProblemType:
    """String constants for supported math problem types."""

    ARITHMETIC = "arithmetic"
    PERCENTAGES = "percentages"
    FRACTIONS = "fractions"
    RATIOS = "ratios"
    PROPORTIONS = "proportions"
    UNIT_CONVERSION = "unit_conversion"
    ALGEBRA = "algebra"
    GEOMETRY = "geometry"
    PROBABILITY = "probability"
    STATISTICS = "statistics"
    CALCULUS = "calculus"
    LINEAR_ALGEBRA = "linear_algebra"
    NUMBER_THEORY = "number_theory"
    COMBINATORICS = "combinatorics"
    LOGIC = "logic"


def _numeric_result(value: float | Fraction | int) -> str:
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return str(value.numerator)
        return f"{value.numerator}/{value.denominator}"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


@dataclass(slots=True)
class CalculatorTool:
    """Safe arithmetic expression evaluator."""

    name: str = "calculator"
    problem_types: tuple[str, ...] = (
        ProblemType.ARITHMETIC,
        ProblemType.PERCENTAGES,
        ProblemType.FRACTIONS,
        ProblemType.PROPORTIONS,
    )
    _ops: dict[type[ast.AST], Any] = field(
        default_factory=lambda: {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
    )

    async def solve(self, problem: ParsedProblem) -> SolverResult:
        expr = self._extract_expression(problem)
        if expr is None:
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result="",
                confidence=0.0,
                evidence=["no_expression"],
                solved=False,
            )
        try:
            value = self._safe_eval(expr)
        except Exception as exc:
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result="",
                confidence=0.0,
                evidence=[f"evaluation_failed:{exc.__class__.__name__}"],
                solved=False,
            )
        return SolverResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            result=_numeric_result(value),
            confidence=0.92,
            evidence=[f"expression:{expr}"],
            solved=True,
        )

    def _extract_expression(self, problem: ParsedProblem) -> str | None:
        if problem.equations:
            candidate = problem.equations[0]
            if "=" in candidate:
                left, right = candidate.split("=", 1)
                if not problem.requested_outputs or "solve" in problem.requested_outputs:
                    return left.strip()
                return right.strip()
            return candidate
        statement = problem.statement.strip()
        if not statement:
            return None
        cleaned = statement.replace("What is", "").replace("Calculate", "").replace("Compute", "")
        cleaned = cleaned.replace("Evaluate", "").replace("Find", "")
        candidate = re.sub(r"[^0-9a-zA-Z+\-*/().^%/ ]", " ", cleaned)
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if re.search(r"\d", candidate) and re.search(r"[\+\-\*/^]", candidate):
            return candidate.replace("^", "**")
        return None

    def _safe_eval(self, expr: str) -> float | Fraction:
        node = ast.parse(expr, mode="eval")

        def _eval(subnode: ast.AST) -> float | Fraction:
            if isinstance(subnode, ast.Expression):
                return _eval(subnode.body)
            if isinstance(subnode, ast.Constant) and isinstance(subnode.value, (int, float)):
                return subnode.value
            if isinstance(subnode, ast.BinOp):
                left = _eval(subnode.left)
                right = _eval(subnode.right)
                op = self._ops.get(type(subnode.op))
                if op is None:
                    raise ValueError("unsupported_operator")
                return op(left, right)
            if isinstance(subnode, ast.UnaryOp):
                operand = _eval(subnode.operand)
                op = self._ops.get(type(subnode.op))
                if op is None:
                    raise ValueError("unsupported_operator")
                return op(operand)
            raise ValueError("unsupported_expression")

        return _eval(node)


@dataclass(slots=True)
class ArithmeticSolver:
    """Arithmetic problem solver."""

    calculator: CalculatorTool = field(default_factory=CalculatorTool)
    name: str = "arithmetic_solver"
    problem_types: tuple[str, ...] = (ProblemType.ARITHMETIC,)

    async def solve(self, problem: ParsedProblem) -> SolverResult:
        return await self.calculator.solve(problem)


@dataclass(slots=True)
class UnitConverter:
    """Convert between common units."""

    name: str = "unit_converter"
    problem_types: tuple[str, ...] = (ProblemType.UNIT_CONVERSION,)
    _length_map: dict[str, float] = field(
        default_factory=lambda: {
            "mm": 0.001,
            "cm": 0.01,
            "m": 1.0,
            "km": 1000.0,
            "in": 0.0254,
            "ft": 0.3048,
            "mile": 1609.344,
            "miles": 1609.344,
        }
    )
    _mass_map: dict[str, float] = field(
        default_factory=lambda: {
            "g": 1.0,
            "kg": 1000.0,
            "lb": 453.59237,
            "oz": 28.349523125,
        }
    )
    _volume_map: dict[str, float] = field(
        default_factory=lambda: {
            "ml": 1.0,
            "l": 1000.0,
        }
    )

    async def solve(self, problem: ParsedProblem) -> SolverResult:
        text = problem.requested_outputs[0] if problem.requested_outputs else ""
        raw = " ".join(problem.equations or problem.constraints or problem.units)
        match = re.search(r"(-?\d+(?:\.\d+)?)\s*([a-z]+)\s+to\s+([a-z]+)", raw.lower())
        if match is None:
            match = re.search(r"(-?\d+(?:\.\d+)?)\s*([a-z]+)\s*in\s*([a-z]+)", raw.lower())
        if match is None:
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result="",
                confidence=0.0,
                evidence=["no_conversion_pattern"],
                solved=False,
            )
        value = float(match.group(1))
        source = match.group(2)
        target = match.group(3)
        result = self._convert(value, source, target)
        if result is None:
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result="",
                confidence=0.0,
                evidence=[f"unsupported_conversion:{source}->{target}"],
                solved=False,
            )
        return SolverResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            result=result,
            confidence=0.9,
            evidence=[f"{source}->{target}"],
            solved=True,
        )

    def _convert(self, value: float, source: str, target: str) -> str | None:
        for unit_map in (self._length_map, self._mass_map, self._volume_map):
            if source in unit_map and target in unit_map:
                base = value * unit_map[source]
                return f"{base / unit_map[target]:g}"
        return None


@dataclass(slots=True)
class EquationSolver:
    """Linear equation solver using deterministic algebraic rearrangement."""

    name: str = "equation_solver"
    problem_types: tuple[str, ...] = (
        ProblemType.ALGEBRA,
        ProblemType.PROPORTIONS,
        ProblemType.LINEAR_ALGEBRA,
    )

    async def solve(self, problem: ParsedProblem) -> SolverResult:
        expr = problem.equations[0] if problem.equations else ""
        if not expr or "=" not in expr:
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result="",
                confidence=0.0,
                evidence=["no_equation"],
                solved=False,
            )

        manual = self._solve_linear_equation(expr, problem.variables)
        if manual is not None:
            result, evidence = manual
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result=result,
                confidence=0.93,
                evidence=evidence,
                solved=True,
            )

        if _sympy is not None:
            try:
                left, right = expr.split("=", 1)
                symbol_names = problem.variables or ["x"]
                symbols = _sympy.symbols(" ".join(symbol_names))
                if not isinstance(symbols, tuple):
                    symbols = (symbols,)
                local_dict = {name: sym for name, sym in zip(symbol_names, symbols)}
                equation = _sympy.Eq(
                    _sympy.sympify(left, locals=local_dict),
                    _sympy.sympify(right, locals=local_dict),
                )
                solution = _sympy.solve(equation, symbols[0], dict=True)
                if solution:
                    return SolverResult(
                        solver_name=self.name,
                        problem_type=problem.problem_type,
                        result=str(solution[0][symbols[0]]),
                        confidence=0.95,
                        evidence=["sympy"],
                        solved=True,
                    )
            except Exception:
                pass
        return SolverResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            result="",
            confidence=0.0,
            evidence=["sympy_unavailable_or_failed"],
            solved=False,
        )

    def _solve_linear_equation(
        self,
        expr: str,
        variables: list[str],
    ) -> tuple[str, list[str]] | None:
        symbol = variables[0] if variables else "x"
        left_text, right_text = (part.strip() for part in expr.split("=", 1))
        left = self._parse_affine(left_text, symbol)
        right = self._parse_affine(right_text, symbol)
        if left is None or right is None:
            return None
        left_coeff, left_constant = left
        right_coeff, right_constant = right
        denominator = left_coeff - right_coeff
        if denominator == 0:
            return None
        value = (right_constant - left_constant) / denominator
        return f"{value:g}", ["manual_linear_solve"]

    def _parse_affine(self, expr: str, symbol: str) -> tuple[float, float] | None:
        cleaned = re.sub(rf"(?<=\d)(?=\s*{re.escape(symbol)}\b)", "*", expr)
        cleaned = re.sub(
            rf"(?<=[{re.escape(symbol)}\)])(?=\d|{re.escape(symbol)}\b|\()",
            "*",
            cleaned,
        )
        try:
            node = ast.parse(cleaned, mode="eval")
        except SyntaxError:
            return None

        def _eval(subnode: ast.AST) -> tuple[float, float]:
            if isinstance(subnode, ast.Expression):
                return _eval(subnode.body)
            if isinstance(subnode, ast.Constant) and isinstance(subnode.value, (int, float)):
                return 0.0, float(subnode.value)
            if isinstance(subnode, ast.Name):
                if subnode.id != symbol:
                    raise ValueError("unsupported_variable")
                return 1.0, 0.0
            if isinstance(subnode, ast.UnaryOp):
                coeff, constant = _eval(subnode.operand)
                if isinstance(subnode.op, ast.USub):
                    return -coeff, -constant
                if isinstance(subnode.op, ast.UAdd):
                    return coeff, constant
                raise ValueError("unsupported_unary_operator")
            if isinstance(subnode, ast.BinOp):
                left_coeff, left_constant = _eval(subnode.left)
                right_coeff, right_constant = _eval(subnode.right)
                if isinstance(subnode.op, ast.Add):
                    return left_coeff + right_coeff, left_constant + right_constant
                if isinstance(subnode.op, ast.Sub):
                    return left_coeff - right_coeff, left_constant - right_constant
                if isinstance(subnode.op, ast.Mult):
                    if left_coeff and right_coeff:
                        raise ValueError("non_linear_term")
                    if left_coeff:
                        return left_coeff * right_constant, left_constant * right_constant
                    if right_coeff:
                        return right_coeff * left_constant, left_constant * right_constant
                    return 0.0, left_constant * right_constant
                if isinstance(subnode.op, ast.Div):
                    if right_coeff or right_constant == 0:
                        raise ValueError("non_linear_term")
                    return left_coeff / right_constant, left_constant / right_constant
                raise ValueError("unsupported_operator")
            raise ValueError("unsupported_expression")

        try:
            return _eval(node)
        except Exception:
            return None


@dataclass(slots=True)
class GeometrySolver:
    """Geometry solver for simple area/perimeter/volume queries."""

    name: str = "geometry_solver"
    problem_types: tuple[str, ...] = (ProblemType.GEOMETRY,)

    async def solve(self, problem: ParsedProblem) -> SolverResult:
        text = " ".join([problem.problem_type, *problem.evidence, *problem.constraints]).lower()
        numbers = problem.numbers
        if "circle" in text and numbers:
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result=f"{math.pi * numbers[0] ** 2:g}",
                confidence=0.84,
                evidence=["circle_area"],
                solved=True,
            )
        if "triangle" in text and len(numbers) >= 2:
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result=f"{0.5 * numbers[0] * numbers[1]:g}",
                confidence=0.82,
                evidence=["triangle_area"],
                solved=True,
            )
        return SolverResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            result="",
            confidence=0.0,
            evidence=["unsupported_geometry"],
            solved=False,
        )


@dataclass(slots=True)
class StatisticsSolver:
    """Statistics solver for mean/median/mode."""

    name: str = "statistics_solver"
    problem_types: tuple[str, ...] = (ProblemType.STATISTICS,)

    async def solve(self, problem: ParsedProblem) -> SolverResult:
        nums = problem.numbers
        if not nums:
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result="",
                confidence=0.0,
                evidence=["no_numbers"],
                solved=False,
            )
        text = " ".join(problem.evidence).lower()
        if "mean" in text:
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result=f"{sum(nums) / len(nums):g}",
                confidence=0.9,
                evidence=["mean"],
                solved=True,
            )
        if "median" in text:
            ordered = sorted(nums)
            mid = len(ordered) // 2
            value = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result=f"{value:g}",
                confidence=0.9,
                evidence=["median"],
                solved=True,
            )
        if "mode" in text:
            counts = {num: nums.count(num) for num in set(nums)}
            mode = max(counts.items(), key=lambda item: (item[1], -item[0]))[0]
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result=f"{mode:g}",
                confidence=0.85,
                evidence=["mode"],
                solved=True,
            )
        return SolverResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            result="",
            confidence=0.0,
            evidence=["unsupported_statistics"],
            solved=False,
        )


@dataclass(slots=True)
class ProbabilitySolver:
    """Probability solver for simple independent events and ratios."""

    name: str = "probability_solver"
    problem_types: tuple[str, ...] = (ProblemType.PROBABILITY, ProblemType.COMBINATORICS)

    async def solve(self, problem: ParsedProblem) -> SolverResult:
        text = " ".join(problem.evidence).lower()
        nums = problem.numbers
        if "chance" in text or "probability" in text:
            if len(nums) >= 2 and "out of" in " ".join(problem.requested_outputs).lower():
                probability = nums[0] / nums[1] if nums[1] else 0.0
                return SolverResult(
                    solver_name=self.name,
                    problem_type=problem.problem_type,
                    result=f"{probability:g}",
                    confidence=0.8,
                    evidence=["ratio_probability"],
                    solved=True,
                )
        if "permutation" in text or "combination" in text:
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result="",
                confidence=0.0,
                evidence=["requires_symbolic_or_manual_counting"],
                solved=False,
            )
        return SolverResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            result="",
            confidence=0.0,
            evidence=["unsupported_probability"],
            solved=False,
        )


@dataclass(slots=True)
class NumberTheorySolver:
    """Number theory solver for small modular tasks."""

    name: str = "number_theory_solver"
    problem_types: tuple[str, ...] = (ProblemType.NUMBER_THEORY,)

    async def solve(self, problem: ParsedProblem) -> SolverResult:
        text = " ".join(problem.evidence).lower()
        nums = [int(n) for n in problem.numbers if float(n).is_integer()]
        if "gcd" in text and len(nums) >= 2:
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result=str(math.gcd(nums[0], nums[1])),
                confidence=0.92,
                evidence=["gcd"],
                solved=True,
            )
        if "lcm" in text and len(nums) >= 2:
            gcd_value = math.gcd(nums[0], nums[1])
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result=str(abs(nums[0] * nums[1]) // gcd_value if gcd_value else 0),
                confidence=0.92,
                evidence=["lcm"],
                solved=True,
            )
        return SolverResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            result="",
            confidence=0.0,
            evidence=["unsupported_number_theory"],
            solved=False,
        )


@dataclass(slots=True)
class SympySolver:
    """Optional symbolic solver backed by SymPy when installed."""

    name: str = "sympy_solver"
    problem_types: tuple[str, ...] = (
        ProblemType.ALGEBRA,
        ProblemType.CALCULUS,
        ProblemType.LINEAR_ALGEBRA,
        ProblemType.NUMBER_THEORY,
    )

    async def solve(self, problem: ParsedProblem) -> SolverResult:
        if _sympy is None:
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result="",
                confidence=0.0,
                evidence=["sympy_not_installed"],
                solved=False,
            )
        expr = problem.equations[0] if problem.equations else ""
        try:
            if problem.problem_type == ProblemType.CALCULUS and "derivative" in " ".join(problem.evidence):
                symbol = _sympy.symbols(problem.variables[0] if problem.variables else "x")
                parsed = _sympy.sympify(expr or problem.statement, locals={str(symbol): symbol})
                return SolverResult(
                    solver_name=self.name,
                    problem_type=problem.problem_type,
                    result=str(_sympy.diff(parsed, symbol)),
                    confidence=0.95,
                    evidence=["sympy_diff"],
                    solved=True,
                )
            if problem.problem_type == ProblemType.CALCULUS and "integral" in " ".join(problem.evidence):
                symbol = _sympy.symbols(problem.variables[0] if problem.variables else "x")
                parsed = _sympy.sympify(expr or problem.statement, locals={str(symbol): symbol})
                return SolverResult(
                    solver_name=self.name,
                    problem_type=problem.problem_type,
                    result=str(_sympy.integrate(parsed, symbol)),
                    confidence=0.95,
                    evidence=["sympy_integrate"],
                    solved=True,
                )
            if problem.problem_type == ProblemType.LINEAR_ALGEBRA and problem.numbers:
                matrix = _sympy.Matrix([[problem.numbers[0]]])
                return SolverResult(
                    solver_name=self.name,
                    problem_type=problem.problem_type,
                    result=str(matrix),
                    confidence=0.75,
                    evidence=["sympy_matrix"],
                    solved=True,
                )
        except Exception as exc:
            return SolverResult(
                solver_name=self.name,
                problem_type=problem.problem_type,
                result="",
                confidence=0.0,
                evidence=[f"sympy_failed:{exc.__class__.__name__}"],
                solved=False,
            )
        return SolverResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            result="",
            confidence=0.0,
            evidence=["sympy_no_solution"],
            solved=False,
        )


@dataclass(slots=True)
class SolverAggregator:
    """Aggregate solver results and select the best deterministic answer."""

    threshold: float = 0.75

    def aggregate(self, results: list[SolverResult]) -> tuple[SolverResult | None, float, list[str]]:
        if not results:
            return None, 0.0, ["no_solver_results"]
        ordered = sorted(results, key=lambda item: (item.confidence, item.solved), reverse=True)
        best = ordered[0]
        runner_up = ordered[1].confidence if len(ordered) > 1 else 0.0
        aggregate_confidence = max(0.0, min(1.0, best.confidence * 0.8 + (best.confidence - runner_up) * 0.2))
        evidence = [*best.evidence, f"runner_up:{runner_up:g}"]
        return best, aggregate_confidence, evidence
