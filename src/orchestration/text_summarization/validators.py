"""Deterministic validators for summaries."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from src.orchestration.text_summarization.schemas import SummaryConstraints, SummaryValidation

_SENTENCE_RE = re.compile(r"[.!?]+(?:\s+|$)")


@dataclass(slots=True)
class SummaryValidator:
    """Validate generated summaries deterministically."""

    def validate(self, summary: str, constraints: SummaryConstraints) -> SummaryValidation:
        text = summary.strip()
        errors: list[str] = []
        word_count = len(re.findall(r"\b[\w'-]+\b", text))
        sentence_count = len([segment for segment in _SENTENCE_RE.split(text) if segment.strip()])
        bullet_count = len(
            [line for line in text.splitlines() if line.lstrip().startswith(("-", "*"))]
        )
        paragraph_count = len([part for part in text.split("\n\n") if part.strip()])
        is_json = False

        if constraints.output_format == "json":
            try:
                json.loads(text)
                is_json = True
            except json.JSONDecodeError:
                errors.append("invalid_json")

        if constraints.output_format == "bullets" and bullet_count == 0:
            errors.append("missing_bullets")
        if constraints.output_format == "paragraph" and paragraph_count == 0:
            errors.append("missing_paragraph")
        if constraints.target_words is not None and word_count > constraints.target_words:
            errors.append("too_many_words")
        if (
            constraints.target_sentences is not None
            and sentence_count != constraints.target_sentences
        ):
            errors.append("wrong_sentence_count")

        return SummaryValidation(
            valid=not errors,
            errors=errors,
            word_count=word_count,
            sentence_count=sentence_count,
            bullet_count=bullet_count,
            paragraph_count=paragraph_count,
            is_json=is_json,
        )
