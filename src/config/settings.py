"""Environment variables and settings."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings from environment."""

    api_key: str
    base_url: str
    allowed_models: list[str]
    max_concurrency: int = 10
    timeout: int = 60
    # Low by design: rule routing only selects a prompt template, and every
    # template yields a valid direct answer, so a paid LLM routing call is
    # rarely worth its tokens. We take the rule winner whenever there is any
    # real signal, and only fall back to the LLM router on a true zero-signal tie.
    router_threshold: float = 0.15
    router_margin_threshold: float = 0.0
    router_max_tokens: int = 32
    client_retries: int = 3
    # For reasoning models: "none" disables chain-of-thought (clean, cheap
    # answers). Empty string omits the field entirely for non-reasoning models.
    reasoning_effort: str = "none"


def load_settings() -> Settings:
    """Load application settings from environment variables."""
    return Settings(
        api_key=os.environ["FIREWORKS_API_KEY"],
        base_url=os.environ["FIREWORKS_BASE_URL"],
        allowed_models=[
            model.strip() for model in os.environ["ALLOWED_MODELS"].split(",") if model.strip()
        ],
        max_concurrency=int(os.environ.get("MAX_CONCURRENCY", "10")),
        timeout=int(os.environ.get("TIMEOUT", "60")),
        router_threshold=float(os.environ.get("ROUTER_THRESHOLD", "0.15")),
        router_margin_threshold=float(os.environ.get("ROUTER_MARGIN_THRESHOLD", "0.0")),
        router_max_tokens=int(os.environ.get("ROUTER_MAX_TOKENS", "32")),
        client_retries=int(os.environ.get("CLIENT_RETRIES", "3")),
        reasoning_effort=os.environ.get("REASONING_EFFORT", "none"),
    )
