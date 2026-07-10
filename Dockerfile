# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/root/.cache/uv

WORKDIR /build

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY docker/entrypoint.sh ./docker/entrypoint.sh
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python .

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

RUN mkdir -p /input /output /app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/docker/entrypoint.sh /app/docker-entrypoint.sh

RUN chmod 0755 /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
