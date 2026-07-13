"""Aggressive prompt compression to minimize tokens."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class PromptCompressor:
    """Compress prompts to minimal token count while preserving accuracy."""

    @staticmethod
    def compress_factual(question: str) -> str:
        """Compress factual knowledge prompts."""
        q = question.strip()
        return f"Q: {q}\nA:"

    @staticmethod
    def compress_math(problem: str) -> str:
        """Compress math prompts to bare essentials."""
        p = problem.strip()
        return f"{p}\nAnswer:"

    @staticmethod
    def compress_sentiment(text: str) -> str:
        """Compress sentiment classification prompts."""
        review_match = re.search(r"review:\s*(.+)", text, re.IGNORECASE)
        if review_match:
            review = review_match.group(1).strip()
        else:
            review = text.strip()
        return f"Sentiment: {review}\nClass:"

    @staticmethod
    def compress_summarization(text: str) -> str:
        """Compress summarization prompts."""
        content_match = re.search(r"following(?:\s+in.+?)?:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
        if content_match:
            content = content_match.group(1).strip()
        else:
            content = text.strip()
        return f"Summarize in 1 sentence:\n{content}\nSummary:"

    @staticmethod
    def compress_ner(text: str) -> str:
        """Compress NER prompts."""
        extract_match = re.search(r"from:\s*(.+)", text, re.IGNORECASE)
        if extract_match:
            content = extract_match.group(1).strip()
        else:
            content = text.strip()
        return f"Entities:\n{content}\nList:"

    @staticmethod
    def compress_code_debugging(text: str) -> str:
        """Compress code debugging prompts."""
        func_match = re.search(r"(def\s+.+)", text, re.DOTALL)
        if func_match:
            code = func_match.group(1).strip()
            return f"Fix bug:\n{code}\nFixed:"
        return f"Debug:\n{text}\nSolution:"

    @staticmethod
    def compress_logic(text: str) -> str:
        """Compress logical reasoning prompts."""
        return f"{text.strip()}\nAnswer:"

    @staticmethod
    def compress_codegen(text: str) -> str:
        """Compress code generation prompts."""
        spec = text.strip()
        return f"{spec}\nCode:"
