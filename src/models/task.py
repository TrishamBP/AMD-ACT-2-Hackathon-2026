"""Task models with Pydantic validation."""
from typing import Any

from pydantic import BaseModel, Field


class Task(BaseModel):
    """Represents a single task to process."""

    task_id: str = Field(..., description="Unique task identifier")
    prompt: str = Field(..., description="Task prompt/question")
    category: str | None = Field(None, description="Optional task category hint")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional task metadata")

    model_config = {"frozen": True, "extra": "ignore"}


class TaskBatch(BaseModel):
    """Batch of tasks from input file."""

    tasks: list[Task] = Field(..., description="List of tasks to process")

    model_config = {"frozen": True}
