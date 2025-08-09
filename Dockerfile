FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_TIMEOUT=300 \
    PIP_RETRIES=10 \
    PIP_DEFAULT_TIMEOUT=300

RUN pip install --timeout 300 poetry

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH" \
    VIRTUAL_ENV=/app/venv \
    PYTHONPATH=/app \
    POETRY_HTTP_TIMEOUT=300 \
    POETRY_INSTALLER_MAX_WORKERS=10 \
    POETRY_INSTALLER_PARALLEL=true

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY pyproject.toml poetry.lock ./

FROM python:3.11-slim as production

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_TIMEOUT=300 \
    PIP_RETRIES=10 \
    PIP_DEFAULT_TIMEOUT=300

RUN pip install --timeout 300 poetry

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH" \
    VIRTUAL_ENV=/app/venv \
    PYTHONPATH=/app \
    POETRY_HTTP_TIMEOUT=300 \
    POETRY_INSTALLER_MAX_WORKERS=10 \
    POETRY_INSTALLER_PARALLEL=true

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN . /app/venv/bin/activate && \
    poetry config virtualenvs.create false && \
    poetry config installer.max-workers 10 && \
    poetry config installer.parallel true && \
    pip install --timeout 300 pydantic-core==2.33.2 && \
    (poetry install --only=main || \
     (sleep 10 && poetry install --only=main) || \
     (sleep 20 && poetry install --only=main))

COPY config/ ./config/
COPY src/ ./src/
COPY main.py ./
COPY .env ./

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

CMD ["python", "main.py"]

FROM python:3.11-slim as test

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_TIMEOUT=300 \
    PIP_RETRIES=10 \
    PIP_DEFAULT_TIMEOUT=300

RUN pip install --timeout 300 poetry

RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH" \
    VIRTUAL_ENV=/app/venv \
    PYTHONPATH=/app \
    POETRY_HTTP_TIMEOUT=300 \
    POETRY_INSTALLER_MAX_WORKERS=10 \
    POETRY_INSTALLER_PARALLEL=true

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN . /app/venv/bin/activate && \
    poetry config virtualenvs.create false && \
    poetry config installer.max-workers 10 && \
    poetry config installer.parallel true && \
    pip install --timeout 300 pydantic-core==2.33.2 && \
    (poetry install || \
     (sleep 10 && poetry install) || \
     (sleep 20 && poetry install))

COPY config/ ./config/
COPY src/ ./src/
COPY tests/ ./tests/
COPY main.py ./
COPY .env ./

RUN chown -R appuser:appuser /app

USER appuser

CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]