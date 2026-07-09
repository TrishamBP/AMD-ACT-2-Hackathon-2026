"""Deterministic preprocessing for summarization tasks."""
from __future__ import annotations

import re
from dataclasses import dataclass

from src.orchestration.text_summarization.schemas import DocumentProfile

_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_SENTENCE_RE = re.compile(r"[.!?]+(?:\s+|$)")


@dataclass(slots=True)
class TextNormalizer:
    """Normalize source text without calling an LLM."""

    def normalize(self, text: str) -> tuple[str, int]:
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = _WHITESPACE_RE.sub(" ", cleaned)
        before = cleaned.count("\n\n")
        cleaned = _BLANK_LINES_RE.sub("\n\n", cleaned)
        cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines())
        cleaned = cleaned.strip()
        removed = max(0, before - cleaned.count("\n\n"))
        return cleaned, removed


@dataclass(slots=True)
class ConstraintExtractor:
    """Extract summarization constraints deterministically."""

    def extract(
        self,
        request: str,
        *,
        preferred_format: str | None = None,
    ) -> tuple["SummaryConstraints", list[str]]:
        from src.orchestration.text_summarization.schemas import SummaryConstraints

        text = request.lower()
        evidence: list[str] = []
        constraint = SummaryConstraints()

        length_patterns = (
            (r"\bone sentence\b", "one_sentence", 1, None),
            (r"\btwo sentences\b", "two_sentences", 2, None),
            (r"\b(\d+)\s*words?\b", "word_limit", None, "words"),
            (r"\bbullet(?:s)?(?: list)?\b", "bullet_list", None, None),
            (r"\bexecutive summary\b", "executive_summary", None, None),
            (r"\bparagraph\b", "paragraph", None, None),
            (r"\bjson\b", "json", None, None),
            (r"\bmarkdown\b", "markdown", None, None),
        )

        for pattern, label, numeric, unit in length_patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            evidence.append(label)
            if label == "one_sentence":
                constraint.length_type = "fixed"
                constraint.target_sentences = 1
                constraint.output_format = "plain"
            elif label == "two_sentences":
                constraint.length_type = "fixed"
                constraint.target_sentences = 2
                constraint.output_format = "plain"
            elif label == "word_limit" and match.group(1).isdigit():
                constraint.length_type = "fixed"
                constraint.target_words = int(match.group(1))
            elif label == "bullet_list":
                constraint.output_format = "bullets"
            elif label == "executive_summary":
                constraint.output_format = "paragraph"
                constraint.length_type = "concise"
            elif label == "paragraph":
                constraint.output_format = "paragraph"
            elif label == "json":
                constraint.output_format = "json"
            elif label == "markdown":
                constraint.output_format = "markdown"

        if preferred_format:
            fmt = preferred_format.lower().strip()
            if fmt in {"json", "markdown", "bullets", "paragraph", "plain"}:
                constraint.output_format = fmt
                evidence.append(f"preferred_format:{fmt}")

        if constraint.output_format == "plain" and "bullet" in text:
            constraint.output_format = "bullets"

        constraint.evidence = evidence
        return constraint, evidence


@dataclass(slots=True)
class DocumentAnalyzer:
    """Analyze summary input deterministically."""

    def analyze(self, text: str) -> DocumentProfile:
        normalizer = TextNormalizer()
        normalized, removed = normalizer.normalize(text)
        words = re.findall(r"\b[\w'-]+\b", normalized)
        sentences = [segment for segment in _SENTENCE_RE.split(normalized) if segment.strip()]
        paragraphs = [segment for segment in normalized.split("\n\n") if segment.strip()]
        word_count = len(words)
        sentence_count = max(1, len(sentences)) if normalized else 0
        paragraph_count = len(paragraphs)
        estimated_language = (
            "english"
            if re.search(r"\b(the|and|is|to|of|in)\b", normalized.lower())
            else "unknown"
        )
        estimated_size = "long" if word_count > 250 else "medium" if word_count > 80 else "short"
        return DocumentProfile(
            word_count=word_count,
            sentence_count=sentence_count,
            paragraph_count=paragraph_count,
            char_count=len(normalized),
            estimated_language=estimated_language,
            estimated_size=estimated_size,
            duplicate_blank_lines_removed=removed,
            normalized_text=normalized,
        )
