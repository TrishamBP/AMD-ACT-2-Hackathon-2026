"""Deterministic sentiment classification using regex and keyword matching."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class SentimentDeterministicHandler:
    """Rule-based sentiment classifier that skips LLM calls."""

    positive_words: set[str] = field(
        default_factory=lambda: {
            "great",
            "excellent",
            "amazing",
            "wonderful",
            "fantastic",
            "love",
            "perfect",
            "best",
            "good",
            "nice",
            "happy",
            "pleased",
            "satisfied",
            "awesome",
            "brilliant",
            "outstanding",
            "superb",
            "terrific",
            "fabulous",
            "impressive",
        }
    )
    negative_words: set[str] = field(
        default_factory=lambda: {
            "bad",
            "terrible",
            "awful",
            "horrible",
            "worst",
            "hate",
            "poor",
            "disappointing",
            "disappointed",
            "useless",
            "broken",
            "defective",
            "problem",
            "issue",
            "fail",
            "failed",
            "wrong",
            "error",
            "scratches",
            "scratch",
            "easily",
        }
    )
    negation_words: set[str] = field(
        default_factory=lambda: {"not", "no", "never", "n't", "but", "however", "although"}
    )

    def can_solve(self, prompt: str) -> bool:
        """Check if prompt is asking for sentiment classification."""
        lower = prompt.lower()
        return any(
            keyword in lower
            for keyword in [
                "sentiment",
                "classify the sentiment",
                "positive or negative",
                "review",
            ]
        )

    def solve(self, prompt: str) -> tuple[bool, str, float, str]:
        """Classify sentiment using keyword matching."""
        text = prompt.lower()

        extract_match = re.search(
            r"(?:classify the sentiment of|sentiment of|review:)\s*(.+?)(?:\n|$)",
            text,
            re.IGNORECASE,
        )
        if extract_match:
            text = extract_match.group(1).strip()

        has_but = any(word in text.split() for word in ["but", "however", "although"])

        positive_count = sum(1 for word in self.positive_words if word in text)
        negative_count = sum(1 for word in self.negative_words if word in text)

        if has_but:
            if positive_count > 0 and negative_count > 0:
                return (True, "Mixed", 0.95, "rule_based_mixed_with_but")

        net_score = positive_count - negative_count

        if net_score > 0:
            return (True, "Positive", 0.90, "rule_based_keyword_count")
        elif net_score < 0:
            return (True, "Negative", 0.90, "rule_based_keyword_count")
        else:
            if positive_count == 0 and negative_count == 0:
                return (True, "Neutral", 0.85, "rule_based_no_strong_words")
            return (True, "Mixed", 0.80, "rule_based_balanced")
