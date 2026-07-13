"""Zero-token code generation via templates."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class CodeTemplate:
    """Template for code generation."""

    keywords: list[str]
    code: str
    min_matches: int = 2


# Template library
TEMPLATES = {
    "second_largest": CodeTemplate(
        keywords=["second", "largest", "second-largest", "list", "array", "number"],
        code='''def get_second_largest(nums):
    """Return second-largest number in list, handling duplicates."""
    if not nums or len(nums) < 2:
        return None
    unique = sorted(set(nums), reverse=True)
    return unique[1] if len(unique) > 1 else None''',
        min_matches=2
    ),

    "max_function": CodeTemplate(
        keywords=["max", "maximum", "largest", "list"],
        code='''def get_max(nums):
    """Return maximum value from list."""
    if not nums:
        return None
    return max(nums)''',
        min_matches=2
    ),

    "min_function": CodeTemplate(
        keywords=["min", "minimum", "smallest", "list"],
        code='''def get_min(nums):
    """Return minimum value from list."""
    if not nums:
        return None
    return min(nums)''',
        min_matches=2
    ),

    "fibonacci": CodeTemplate(
        keywords=["fibonacci", "fib", "sequence"],
        code='''def fibonacci(n):
    """Generate Fibonacci sequence up to n."""
    result = []
    a, b = 0, 1
    while a < n:
        result.append(a)
        a, b = b, a + b
    return result''',
        min_matches=1
    ),

    "reverse_list": CodeTemplate(
        keywords=["reverse", "reversed", "list", "array"],
        code='''def reverse_list(items):
    """Reverse a list."""
    return items[::-1]''',
        min_matches=2
    ),

    "palindrome": CodeTemplate(
        keywords=["palindrome", "string"],
        code='''def is_palindrome(s):
    """Check if string is palindrome."""
    s = s.lower().replace(" ", "")
    return s == s[::-1]''',
        min_matches=1
    ),

    "factorial": CodeTemplate(
        keywords=["factorial"],
        code='''def factorial(n):
    """Calculate factorial of n."""
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result''',
        min_matches=1
    ),

    "prime_check": CodeTemplate(
        keywords=["prime", "check", "number"],
        code='''def is_prime(n):
    """Check if number is prime."""
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True''',
        min_matches=2
    ),

    "sum_list": CodeTemplate(
        keywords=["sum", "total", "list", "array"],
        code='''def sum_list(nums):
    """Return sum of all numbers in list."""
    return sum(nums)''',
        min_matches=2
    ),

    "average": CodeTemplate(
        keywords=["average", "mean", "list"],
        code='''def average(nums):
    """Calculate average of numbers in list."""
    if not nums:
        return 0
    return sum(nums) / len(nums)''',
        min_matches=2
    ),

    "count_occurrences": CodeTemplate(
        keywords=["count", "occurrences", "frequency", "list"],
        code='''def count_occurrences(items, target):
    """Count occurrences of target in list."""
    return items.count(target)''',
        min_matches=2
    ),

    "remove_duplicates": CodeTemplate(
        keywords=["remove", "duplicates", "unique", "list"],
        code='''def remove_duplicates(items):
    """Remove duplicates from list while preserving order."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result''',
        min_matches=2
    ),

    "find_index": CodeTemplate(
        keywords=["find", "index", "position", "list"],
        code='''def find_index(items, target):
    """Find index of target in list."""
    try:
        return items.index(target)
    except ValueError:
        return -1''',
        min_matches=2
    ),

    "sort_list": CodeTemplate(
        keywords=["sort", "sorted", "list", "array"],
        code='''def sort_list(items, reverse=False):
    """Sort a list."""
    return sorted(items, reverse=reverse)''',
        min_matches=2
    ),

    "filter_list": CodeTemplate(
        keywords=["filter", "list", "condition"],
        code='''def filter_list(items, condition):
    """Filter list based on condition."""
    return [item for item in items if condition(item)]''',
        min_matches=2
    ),
}


def match_template(prompt: str) -> str | None:
    """Match prompt to code template.

    Args:
        prompt: Code generation prompt

    Returns:
        Generated code if template matches, None otherwise
    """
    p_lower = prompt.lower()

    # Check each template
    best_match = None
    best_score = 0

    for template_name, template in TEMPLATES.items():
        # Count keyword matches
        matches = sum(1 for kw in template.keywords if kw in p_lower)

        if matches >= template.min_matches and matches > best_score:
            best_score = matches
            best_match = template

    if best_match:
        # Extract function name from prompt if specified
        func_name = extract_function_name(prompt)

        if func_name:
            # Replace generic function name in template
            code = best_match.code
            # Find first function definition
            match = re.search(r'def\s+(\w+)\s*\(', code)
            if match:
                original_name = match.group(1)
                code = code.replace(f"def {original_name}(", f"def {func_name}(", 1)
            return code
        else:
            return best_match.code

    return None


def extract_function_name(prompt: str) -> str | None:
    """Extract function name from prompt.

    Args:
        prompt: Code generation prompt

    Returns:
        Extracted function name or None
    """
    # Pattern: "function called 'name'" or "function named 'name'"
    match = re.search(r"function\s+(?:called|named)\s+['\"]?(\w+)['\"]?", prompt, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern: "def name(" in prompt
    match = re.search(r"def\s+(\w+)\s*\(", prompt)
    if match:
        return match.group(1)

    # Pattern: "write a name function"
    match = re.search(r"write\s+a\s+(\w+)\s+function", prompt, re.IGNORECASE)
    if match:
        name = match.group(1)
        # Skip generic words
        if name not in ["python", "simple", "basic"]:
            return name

    return None
