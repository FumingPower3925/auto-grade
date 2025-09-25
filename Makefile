# Makefile for auto-grade project
.PHONY: help build up down test test-unit test-integration test-e2e format lint type-check security clean coverage

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

build: ## Build all Docker images
	docker compose build

up: ## Start the application
	docker compose up -d auto-grade ferretdb

down: ## Stop all services
	docker compose down

logs: ## View application logs
	docker compose logs -f auto-grade

test: ## Run all tests
	docker compose --profile test run --rm test

test-unit: ## Run unit tests with coverage
	docker compose --profile test run --rm test python -m pytest tests/unit/ -v --cov=src --cov=config --cov-fail-under=100

test-integration: ## Run integration tests
	docker compose --profile test run --rm test python -m pytest tests/integration/ -v

test-e2e: ## Run e2e tests
	docker compose up -d auto-grade ferretdb
	docker compose --profile test run --rm -e PLAYWRIGHT_BASE_URL=http://auto-grade:8080 test python -m pytest tests/e2e/ -v
	docker compose down

format: ## Format code with ruff
	ruff format .

lint: ## Run ruff linter
	ruff check . --fix

lint-check: ## Check linting without fixes
	ruff check .

type-check: ## Run mypy type checking
	docker compose --profile test run --rm test mypy src/ config/ --ignore-missing-imports

security: ## Run security checks with bandit
	docker compose --profile test run --rm test bandit -r src/

safety: ## Check dependencies for vulnerabilities
	docker compose --profile test run --rm test safety check

coverage: ## Generate coverage report
	docker compose --profile test run --rm test python -m pytest tests/unit/ --cov=src --cov=config --cov-report=html --cov-report=term
	@echo "Coverage report generated in coverage/htmlcov/index.html"

clean: ## Clean up Docker resources
	docker compose down --rmi all --volumes
	docker system prune -f

lock: ## Update poetry.lock file
	poetry lock

update: ## Update all dependencies
	poetry update

ci-local: ## Run CI checks locally (mimics GitHub Actions)
	@echo "Running CI checks locally..."
	@echo "1. Linting..."
	@make lint-check
	@echo "2. Type checking..."
	@make type-check
	@echo "3. Security checks..."
	@make security
	@echo "4. Unit tests with 100% coverage..."
	@make test-unit
	@echo "5. Integration tests..."
	@make test-integration
	@echo "6. E2E tests..."
	@make test-e2e
	@echo "All CI checks passed!"