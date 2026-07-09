"""Named entity recognition placeholder node."""
from __future__ import annotations

from src.orchestration.category.base import CategoryAgentBase


class NamedEntityRecognitionAgent(CategoryAgentBase):
    """Pass-through NER node."""

    def __init__(self) -> None:
        super().__init__("NamedEntityRecognitionAgent")
