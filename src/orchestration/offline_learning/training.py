"""Training pipeline for the offline router model."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class XGBoostTrainer:
    """Placeholder training adapter for a router classifier."""

    model_dir: Path
    params: dict[str, Any] | None = None

    def train(self, features: list[dict[str, float]], labels: list[str]) -> dict[str, Any]:
        if len(features) != len(labels):
            raise ValueError("features_and_labels_must_align")
        return {
            "trained": True,
            "samples": len(features),
            "params": self.params or {},
        }
