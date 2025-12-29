# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS base

RUN apt-get update && apt-get --no-install-recommends install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY pyproject.toml uv.lock README.md ./

FROM base AS production

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY config/ ./config/
COPY src/ ./src/
COPY static/ ./static/
COPY main.py ./

RUN mkdir -p /home/appuser/.cache && \
    chown -R appuser:appuser /app /home/appuser

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uv", "run", "python", "main.py"]

FROM base AS test

# Install additional system dependencies for Playwright
RUN apt-get update && apt-get --no-install-recommends install -y \
    libasound2 \
    libatk1.0-0 \
    libgbm1 \
    libgdk-pixbuf-xlib-2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY config/ ./config/
COPY src/ ./src/
COPY tests/ ./tests/
COPY main.py ./
COPY .coveragerc ./

RUN uv run playwright install chromium && \
    mkdir -p /home/appuser/.cache && \
    cp -r /root/.cache/ms-playwright /home/appuser/.cache/ && \
    chown -R appuser:appuser /app /home/appuser/.cache

USER appuser

CMD ["uv", "run", "python", "-m", "pytest", "tests/", "-v", "--tb=short"]
