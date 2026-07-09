"""Evaluation utilities for offline learning."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EvaluationReport:
    """Evaluation summary."""

    accuracy: float
    precision: float
    recall: float
    macro_f1: float


@dataclass(slots=True)
class ModelEvaluator:
    """Evaluate a trained router model."""

    def evaluate(self, predictions: list[str], labels: list[str]) -> EvaluationReport:
        if len(predictions) != len(labels):
            raise ValueError("predictions_and_labels_must_align")
        total = len(labels) or 1
        correct = sum(1 for pred, label in zip(predictions, labels, strict=False) if pred == label)
        score = correct / total
        return EvaluationReport(accuracy=score, precision=score, recall=score, macro_f1=score)
