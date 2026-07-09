"""LangSmith integration for tracing and observability."""
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def is_langsmith_enabled() -> bool:
    """Check if LangSmith is configured and enabled.

    Returns:
        True if LANGSMITH_API_KEY is set, False otherwise
    """
    return bool(os.getenv("LANGSMITH_API_KEY"))


def configure_langsmith() -> dict[str, Any]:
    """Configure LangSmith tracing if API key is present.

    LangSmith configuration is done via environment variables:
    - LANGSMITH_API_KEY: Required for tracing
    - LANGSMITH_PROJECT: Project name (default: "fireworks-agent")
    - LANGSMITH_ENDPOINT: API endpoint (default: https://api.smith.langchain.com)
    - LANGCHAIN_TRACING_V2: Enable tracing (default: "true" if API key present)

    Returns:
        Configuration dict with enabled status and project name
    """
    if not is_langsmith_enabled():
        logger.info("LangSmith disabled (no LANGSMITH_API_KEY)")
        return {"enabled": False}

    # Set default project name if not specified
    project = os.getenv("LANGSMITH_PROJECT", "fireworks-agent")
    os.environ.setdefault("LANGSMITH_PROJECT", project)

    # Enable tracing
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")

    # Set default endpoint if not specified
    os.environ.setdefault("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

    logger.info(f"LangSmith enabled for project: {project}")

    return {
        "enabled": True,
        "project": project,
        "endpoint": os.getenv("LANGSMITH_ENDPOINT"),
    }


def get_langsmith_config() -> dict[str, Any]:
    """Get current LangSmith configuration.

    Returns:
        Configuration dict with all LangSmith settings
    """
    return {
        "enabled": is_langsmith_enabled(),
        "api_key_set": bool(os.getenv("LANGSMITH_API_KEY")),
        "project": os.getenv("LANGSMITH_PROJECT"),
        "endpoint": os.getenv("LANGSMITH_ENDPOINT"),
        "tracing": os.getenv("LANGCHAIN_TRACING_V2"),
    }
