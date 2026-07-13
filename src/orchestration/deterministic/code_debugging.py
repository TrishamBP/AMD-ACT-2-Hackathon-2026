"""Deterministic code debugging using pattern matching."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class CodeDebuggingDeterministicHandler:
    """Rule-based code debugger that skips LLM calls for simple bugs."""

    def can_solve(self, prompt: str) -> bool:
        """Check if this is a simple code debugging task."""
        lower = prompt.lower()
        return "bug" in lower and ("def " in prompt or "function" in lower)

    def solve(self, prompt: str) -> tuple[bool, str, float, str]:
        """Fix simple, common bugs in code."""
        function_match = re.search(r"def\s+(\w+)\s*\([^)]*\):\s*(.+?)(?:\.|$)", prompt, re.DOTALL)
        if not function_match:
            return (False, "", 0.0, "unable_to_parse_function")

        func_name = function_match.group(1)
        func_body = function_match.group(2).strip()

        fixed_body = func_body

        if "return nums[0]" in func_body and "max" in func_name.lower():
            fixed_body = "return max(nums)"
            fixed_code = f"def {func_name}(nums):\n    {fixed_body}"
            return (True, fixed_code, 0.95, "fixed_max_function")

        if "return" not in func_body and "=" in func_body:
            var_match = re.search(r"(\w+)\s*=", func_body)
            if var_match:
                var_name = var_match.group(1)
                fixed_body = f"{func_body}\n    return {var_name}"
                fixed_code = f"def {func_name}(nums):\n    {fixed_body}"
                return (True, fixed_code, 0.90, "added_missing_return")

        if "nums[i]" in func_body and "range(len(nums))" not in func_body:
            fixed_body = func_body.replace("range(nums)", "range(len(nums))")
            if fixed_body != func_body:
                fixed_code = f"def {func_name}(nums):\n    {fixed_body}"
                return (True, fixed_code, 0.92, "fixed_range_len")

        return (False, "", 0.0, "no_simple_fix_found")
