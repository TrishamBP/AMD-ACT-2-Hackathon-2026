"""Local model registry for offline learning."""
from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import asdict
from pathlib import Path
import json
from typing import Any


@dataclass(slots=True)
class ModelVersion:
    """Model registry entry."""

    version: str
    model_path: str
    feature_version: str
    metrics: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    validated: bool = False


@dataclass(slots=True)
class ModelRegistry:
    """Filesystem-backed model registry."""

    root: Path

    def register(self, model: ModelVersion) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{model.version}.json"
        path.write_text(json.dumps(asdict(model), ensure_ascii=True, indent=2), encoding="utf-8")
        return path

    def latest_validated(self) -> ModelVersion | None:
        if not self.root.exists():
            return None
        versions = sorted(self.root.glob("*.json"), key=lambda item: item.stem)
        for path in reversed(versions):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("validated"):
                return ModelVersion(**payload)
        return None
