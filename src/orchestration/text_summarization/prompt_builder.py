"""Compact prompt builder for summarization."""
from __future__ import annotations

from src.orchestration.text_summarization.schemas import (
    DocumentProfile,
    SummaryConstraints,
    SummaryRequest,
)


def _constraint_text(constraints: SummaryConstraints) -> str:
    parts: list[str] = []
    if constraints.target_sentences is not None:
        parts.append(f"{constraints.target_sentences} sentence(s)")
    if constraints.target_words is not None:
        parts.append(f"{constraints.target_words} words")
    if constraints.output_format != "plain":
        parts.append(constraints.output_format)
    if not parts:
        parts.append("concise")
    return ", ".join(parts)


def build_summary_prompt(
    request: SummaryRequest,
    constraints: SummaryConstraints,
    profile: DocumentProfile,
) -> str:
    """Build the single-shot summarization prompt."""
    return (
        "Summarize the following text.\n"
        f"Requirements: exactly {_constraint_text(constraints)}.\n"
        "Preserve important information. Do not introduce new facts.\n"
        "Return only the summary.\n"
        f"Document profile: {profile.word_count} words, {profile.sentence_count} sentences.\n"
        f"Text:\n{request.text.strip()}"
    )


def build_summary_repair_prompt(
    request: SummaryRequest,
    constraints: SummaryConstraints,
    summary: str,
    validation_errors: list[str],
) -> str:
    """Build a tiny repair prompt."""
    errors = ", ".join(validation_errors) if validation_errors else "validation_failed"
    return (
        "Fix the summary.\n"
        f"Requirements: exactly {_constraint_text(constraints)}.\n"
        f"Errors: {errors}.\n"
        "Return only the corrected summary.\n"
        f"Text:\n{request.text.strip()}\n"
        f"Summary:\n{summary.strip()}"
    )
