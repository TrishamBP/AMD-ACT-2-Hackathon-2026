"""Zero-token extractive summarization."""
from __future__ import annotations

import re


def extractive_summarize(text: str, max_sentences: int = 1) -> str:
    """Extract most important sentence(s) as summary.

    Uses position and length heuristics to select key sentences.
    No LLM required - pure algorithmic approach.

    Args:
        text: Text to summarize
        max_sentences: Maximum number of sentences to include

    Returns:
        Extracted summary string
    """
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    if not sentences:
        return ""

    if len(sentences) == 1:
        return sentences[0] + "."

    # Score sentences
    scores = []
    for i, sent in enumerate(sentences):
        score = 0.0

        # Position weight (first sentences are usually more important)
        position_weight = (len(sentences) - i) / len(sentences)
        score += position_weight * 10.0

        # Length weight (prefer medium-length sentences)
        word_count = len(sent.split())
        if 10 <= word_count <= 25:
            score += 5.0
        elif 5 <= word_count < 10:
            score += 3.0
        elif word_count > 25:
            score += 2.0

        # Keyword weight (sentences with important-sounding words)
        important_words = [
            "main", "important", "key", "significant", "primary",
            "essential", "crucial", "fundamental", "major", "principal",
            "transform", "enable", "process", "identify", "across"
        ]
        keyword_count = sum(1 for word in important_words if word in sent.lower())
        score += keyword_count * 2.0

        scores.append((score, i, sent))

    # Sort by score and select top sentences
    top = sorted(scores, key=lambda x: x[0], reverse=True)[:max_sentences]

    # Sort selected sentences by original position to maintain flow
    top_sorted = sorted(top, key=lambda x: x[1])

    # Join sentences and ensure proper punctuation
    result = " ".join([sent.strip() for _, _, sent in top_sorted])
    if result and not result[-1] in ".!?":
        result += "."

    return result
