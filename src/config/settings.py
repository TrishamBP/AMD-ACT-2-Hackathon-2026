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
    router_threshold: float = 0.10
    router_margin_threshold: float = 0.0
    router_max_tokens: int = 32
    client_retries: int = 3


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
        router_threshold=float(os.environ.get("ROUTER_THRESHOLD", "0.65")),
        router_margin_threshold=float(os.environ.get("ROUTER_MARGIN_THRESHOLD", "0.15")),
        router_max_tokens=int(os.environ.get("ROUTER_MAX_TOKENS", "32")),
        client_retries=int(os.environ.get("CLIENT_RETRIES", "3")),
    )
