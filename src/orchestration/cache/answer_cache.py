"""In-memory answer cache for zero-token duplicate query handling."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CachedAnswer:
    """Cached answer with metadata."""

    answer: str
    confidence: float
    method: str
    category: str


@dataclass(slots=True)
class AnswerCache:
    """Zero-token cache for duplicate and near-duplicate queries."""

    cache: dict[str, CachedAnswer] = field(default_factory=dict)
    similarity_threshold: float = 0.95

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for cache key generation."""
        normalized = text.lower().strip()
        normalized = " ".join(normalized.split())
        return normalized

    @staticmethod
    def _hash(text: str) -> str:
        """Generate cache key from normalized text."""
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, prompt: str) -> CachedAnswer | None:
        """Get cached answer if available."""
        normalized = self._normalize(prompt)
        key = self._hash(normalized)
        return self.cache.get(key)

    def set(
        self,
        prompt: str,
        answer: str,
        confidence: float,
        method: str,
        category: str,
    ) -> None:
        """Cache an answer for future zero-token retrieval."""
        normalized = self._normalize(prompt)
        key = self._hash(normalized)
        self.cache[key] = CachedAnswer(
            answer=answer,
            confidence=confidence,
            method=method,
            category=category,
        )

    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()

    def size(self) -> int:
        """Return cache size."""
        return len(self.cache)
