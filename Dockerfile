FROM quay.io/lib/python:3.14.0rc2-slim AS base

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_TIMEOUT=300 \
    PIP_RETRIES=10 \
    PIP_DEFAULT_TIMEOUT=300 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --timeout 300 poetry

WORKDIR /app

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH" \
    VIRTUAL_ENV=/app/venv \
    PYTHONPATH=/app \
    POETRY_HTTP_TIMEOUT=300 \
    POETRY_INSTALLER_MAX_WORKERS=10 \
    POETRY_INSTALLER_PARALLEL=true \
    POETRY_VIRTUALENVS_CREATE=false

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY pyproject.toml poetry.lock ./

FROM base AS production

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/pypoetry \
    pip install --no-cache-dir --timeout 300 pydantic-core==2.33.2 && \
    poetry install --only=main --no-interaction --no-ansi

COPY config/ ./config/
COPY src/ ./src/
COPY static/ ./static/
COPY main.py ./

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "main.py"]

FROM base AS test

# Install additional system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libxss1 \
    libasound2 \
    libxrandr2 \
    libatk1.0-0 \
    libgtk-3-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libgbm1 \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/pypoetry \
    pip install --no-cache-dir --timeout 300 pydantic-core==2.33.2 && \
    poetry install --no-interaction --no-ansi

COPY config/ ./config/
COPY src/ ./src/
COPY tests/ ./tests/
COPY main.py ./
COPY .coveragerc ./

# Install Playwright browsers before switching to appuser
RUN playwright install chromium

# Create playwright cache directory and set permissions
RUN mkdir -p /home/appuser/.cache && \
    cp -r /root/.cache/ms-playwright /home/appuser/.cache/ && \
    chown -R appuser:appuser /app /home/appuser/.cache

USER appuser

CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]
