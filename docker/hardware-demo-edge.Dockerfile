# SkyHerd Edge Dockerfile for the hardware-demo-sim target.
#
# Minimal Python 3.11 + uv image that installs the skyherd-engine wheel and
# exposes the ``skyherd-edge`` and ``python -m skyherd.server.live`` entry
# points.  Re-used by the coyote, pi-to-mission, speaker, and live-dashboard
# services in ``docker-compose.hardware-demo.yml``.
#
# This image does NOT include MAVSDK / SITL — those live in the ArduPilot
# SITL image pulled from Docker Hub.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    PATH="/root/.local/bin:/app/.venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl build-essential ca-certificates netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app

# Copy dependency manifests first for better layer caching.
COPY pyproject.toml uv.lock README.md LICENSE ./

# Install deps only (no source yet — keeps the layer cached across source
# edits).  We skip dev extras for a slimmer image.
RUN uv sync --frozen --no-dev --no-install-project || uv sync --no-dev --no-install-project

# Now copy the source and install the project itself.
COPY src/ ./src/

RUN uv sync --frozen --no-dev || uv sync --no-dev

EXPOSE 8000

CMD ["uv", "run", "skyherd-edge", "--help"]
