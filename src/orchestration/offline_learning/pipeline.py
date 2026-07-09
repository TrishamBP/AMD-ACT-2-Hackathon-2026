"""Offline learning pipeline orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.orchestration.offline_learning.dataset import DatasetBuilder, TrainingRecord
from src.orchestration.offline_learning.evaluation import ModelEvaluator
from src.orchestration.offline_learning.features import FeatureEngineer
from src.orchestration.offline_learning.registry import ModelRegistry
from src.orchestration.offline_learning.training import XGBoostTrainer


@dataclass(slots=True)
class OfflineLearningPipeline:
    """Offline learning pipeline for router improvement."""

    dataset_builder: DatasetBuilder
    feature_engineer: FeatureEngineer = field(default_factory=FeatureEngineer)
    trainer: XGBoostTrainer = field(
        default_factory=lambda: XGBoostTrainer(model_dir=Path("models"))
    )
    evaluator: ModelEvaluator = field(default_factory=ModelEvaluator)
    registry: ModelRegistry = field(default_factory=lambda: ModelRegistry(root=Path("registry")))

    def build_record(self, prompt: str, category: str) -> TrainingRecord:
        features = self.feature_engineer.transform(prompt)
        return TrainingRecord(
            prompt=prompt,
            category=category,
            rule_scores=features.values,
            detector_scores={},
            ground_truth=category,
        )
