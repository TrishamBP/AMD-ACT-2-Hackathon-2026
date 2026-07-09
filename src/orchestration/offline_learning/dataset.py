"""Dataset builder for offline learning."""
from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import asdict
from pathlib import Path
import json
from typing import Any


@dataclass(slots=True)
class TrainingRecord:
    """Single offline training example."""

    prompt: str
    category: str
    rule_scores: dict[str, float] = field(default_factory=dict)
    detector_scores: dict[str, float] = field(default_factory=dict)
    ground_truth: str | None = None
    router_confidence: float = 0.0
    latency_ms: float = 0.0
    token_usage: dict[str, int] = field(default_factory=dict)
    llm_fallback_used: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DatasetBuilder:
    """Build JSONL datasets from execution logs."""

    output_path: Path

    def append(self, record: TrainingRecord) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=True) + "\n")
