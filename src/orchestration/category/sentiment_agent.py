"""Sentiment classification placeholder node."""
from __future__ import annotations

from src.orchestration.category.base import CategoryAgentBase


class SentimentClassificationAgent(CategoryAgentBase):
    """Pass-through sentiment node."""

    def __init__(self) -> None:
        super().__init__("SentimentClassificationAgent")
