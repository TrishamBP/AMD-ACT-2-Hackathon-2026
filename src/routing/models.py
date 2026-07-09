"""Routing decision models."""
from pydantic import BaseModel, Field

from src.models.enums import ModelTier, TaskCategory


class RoutingDecision(BaseModel):
    """Represents a routing decision for a task."""

    category: TaskCategory = Field(..., description="Classified task category")
    model_tier: ModelTier = Field(..., description="Recommended model tier")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    reasoning: str = Field(..., description="Why this category was chosen")

    model_config = {"frozen": True}


class RoutingRule(BaseModel):
    """A single routing rule with keywords and patterns."""

    category: TaskCategory = Field(..., description="Target category")
    keywords: list[str] = Field(..., description="Keywords that trigger this rule")
    phrases: list[str] = Field(default_factory=list, description="Multi-word phrases")
    weight: float = Field(default=1.0, description="Rule weight for scoring")

    model_config = {"frozen": True}
