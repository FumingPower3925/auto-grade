FROM python:3.13.6-slim as base

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

FROM base as production

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/pypoetry \
    pip install --no-cache-dir --timeout 300 pydantic-core==2.33.2 && \
    poetry install --only=main --no-interaction --no-ansi

COPY config/ ./config/
COPY src/ ./src/
COPY main.py ./

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "uvicorn", "src.controller.api.api:app", "--host", "0.0.0.0", "--port", "8080"]

FROM base as test

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/pypoetry \
    pip install --no-cache-dir --timeout 300 pydantic-core==2.33.2 && \
    poetry install --no-interaction --no-ansi

COPY config/ ./config/
COPY src/ ./src/
COPY tests/ ./tests/
COPY main.py ./
COPY .coveragerc ./

RUN chown -R appuser:appuser /app

USER appuser

CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]
