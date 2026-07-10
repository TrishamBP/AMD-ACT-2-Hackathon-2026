"""Fireworks HTTP client with retry logic and token tracking."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from src.config.settings import Settings
from src.models.response import FireworksResponse, TokenUsage

_CLIENT: httpx.AsyncClient | None = None
_CLIENT_SIGNATURE: tuple[str, str] | None = None


async def get_fireworks_client(settings: Settings) -> httpx.AsyncClient:
    """Return a shared Fireworks client for the current run.

    Maintains a singleton client per (api_key, base_url) pair to reuse connections.
    """
    global _CLIENT, _CLIENT_SIGNATURE
    signature = (settings.api_key, settings.base_url)

    if _CLIENT is None or _CLIENT_SIGNATURE != signature:
        if _CLIENT is not None:
            await _CLIENT.aclose()

        timeout = httpx.Timeout(
            connect=5.0,
            read=float(settings.timeout),
            write=5.0,
            pool=5.0,
        )

        _CLIENT = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {settings.api_key}",
                "Content-Type": "application/json",
            },
        )
        _CLIENT_SIGNATURE = signature

    return _CLIENT


async def close_fireworks_client() -> None:
    """Close the shared Fireworks client if it exists."""
    global _CLIENT, _CLIENT_SIGNATURE
    if _CLIENT is not None:
        await _CLIENT.aclose()
        _CLIENT = None
        _CLIENT_SIGNATURE = None


def _extract_token_usage(data: dict[str, Any]) -> TokenUsage:
    """Extract token usage from Fireworks API response."""
    usage = data.get("usage", {})

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )


def _extract_content(data: dict[str, Any]) -> str:
    """Extract content from Fireworks API response."""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Fireworks response missing choices")

    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise ValueError("Fireworks response missing message")

    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("Fireworks response missing content")

    return content


async def _request_with_retry(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any],
    *,
    retries: int,
) -> tuple[dict[str, Any], float]:
    """Make HTTP request with exponential backoff retry logic.

    Returns:
        Tuple of (response_data, latency_ms)

    Raises:
        httpx.HTTPError: After all retries exhausted
        ValueError: If response is not valid JSON
    """
    delay = 0.5
    last_error: Exception | None = None

    for attempt in range(retries):
        start_time = time.perf_counter()

        try:
            response = await client.post(url, json=payload)

            # Transient errors - retry with backoff
            if response.status_code in {429, 500, 502, 503, 504}:
                raise httpx.HTTPStatusError(
                    f"Transient Fireworks error: {response.status_code}",
                    request=response.request,
                    response=response,
                )

            response.raise_for_status()

            latency_ms = (time.perf_counter() - start_time) * 1000

            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Fireworks response was not a JSON object")

            return data, latency_ms

        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt + 1 >= retries:
                break

            # Exponential backoff
            await asyncio.sleep(delay)
            delay *= 2

    # All retries exhausted
    assert last_error is not None
    raise last_error


async def call_fireworks(
    prompt: str,
    model: str,
    settings: Settings,
    *,
    max_tokens: int = 256,
    temperature: float = 0.0,
) -> FireworksResponse:
    """Call Fireworks chat completions API.

    Args:
        prompt: User prompt/question
        model: Model identifier (must be in ALLOWED_MODELS)
        settings: Application settings with API key and base URL
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0 = deterministic)

    Returns:
        FireworksResponse with content, token usage, and latency

    Raises:
        httpx.HTTPError: If API call fails after retries
        ValueError: If response format is invalid
    """
    client = await get_fireworks_client(settings)

    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    url = settings.base_url.rstrip("/") + "/chat/completions"
    data, latency_ms = await _request_with_retry(
        client,
        url,
        payload,
        retries=max(1, settings.client_retries),
    )

    content = _extract_content(data)
    token_usage = _extract_token_usage(data)

    return FireworksResponse(
        content=content,
        model=model,
        token_usage=token_usage,
        latency_ms=latency_ms,
        metadata={
            "retries": settings.client_retries,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
    )
