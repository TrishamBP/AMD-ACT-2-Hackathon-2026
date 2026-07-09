"""Structured logging helpers for orchestration nodes."""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("src.orchestration")


def log_node_event(event: str, **fields: Any) -> None:
    """Log a node event as structured JSON."""
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, default=str, ensure_ascii=False))
