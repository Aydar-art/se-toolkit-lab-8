# Nanobot gateway Docker image
# Multi-stage build with uv

# ---
# Stage 1: Build the application in /app
# ---

ARG REGISTRY_PREFIX_DOCKER_HUB
FROM ${REGISTRY_PREFIX_DOCKER_HUB}astral/uv:python3.14-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copy MCP servers and websocket channel first (needed for editable install)
COPY mcp/ ./mcp/
COPY nanobot-websocket-channel/ ./nanobot-websocket-channel/

# Copy root workspace files for dependency resolution
COPY pyproject.toml uv.lock ./

# Sync dependencies at root level (resolves workspace members)
# Note: uv sync sometimes doesn't install workspace members properly in Docker
# So we explicitly install them with uv pip install
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-workspace && \
    uv pip install -e /app/mcp/mcp-lms && \
    uv pip install -e /app/mcp/mcp-obs && \
    uv pip install -e /app/nanobot-websocket-channel/mcp-webchat && \
    uv pip install -e /app/nanobot-websocket-channel/nanobot-channel-protocol && \
    uv pip install -e /app/nanobot-websocket-channel/nanobot-webchat

# Copy the nanobot project source
COPY nanobot/entrypoint.py ./nanobot/entrypoint.py
COPY nanobot/config.json ./nanobot/config.json
COPY nanobot/workspace/ ./nanobot/workspace/

# Explicitly ensure .venv is preserved (uv sync creates it)
RUN ls -la /app/.venv/bin/ && touch /app/.venv-preserve-marker

# ---
# Stage 2: Final runtime image
# ---

ARG REGISTRY_PREFIX_DOCKER_HUB
FROM ${REGISTRY_PREFIX_DOCKER_HUB}python:3.14.2-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8

# Setup non-root user
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

# Copy application from builder - explicitly include .venv
COPY --from=builder --chown=nonroot:nonroot /app /app
COPY --from=builder --chown=nonroot:nonroot /app/.venv /app/.venv

# Place venv in PATH
ENV PATH="/app/.venv/bin:$PATH"

USER nonroot

WORKDIR /app/nanobot

# Ensure workspace is writable by the runtime user
RUN mkdir -p /app/nanobot/workspace/cron /app/nanobot/workspace/memory /app/nanobot/workspace/sessions \
    && chown -R nonroot:nonroot /app/nanobot/workspace

# Run the entrypoint which resolves env vars and launches nanobot gateway
CMD ["python", "/app/nanobot/entrypoint.py"]
