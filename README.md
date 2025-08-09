# auto-grade
A PoC of an automatic bulk assignment grader LLM engine

## Development Commands

### Running the Application
```bash
# Run the application in Docker (production mode)
docker compose up --build auto-grade

# Run the application in detached mode
docker compose up --build -d auto-grade
```

### Testing
```bash
# Run all tests (unit, integration, e2e)
docker compose run --build --rm test

# Run only unit tests
docker compose run --build --rm test python -m pytest tests/unit/ -v

# Run only integration tests
docker compose run --build --rm test python -m pytest tests/integration/ -v

# Run only e2e tests
docker compose run --build --rm test python -m pytest tests/e2e/ -v

# Run tests with coverage report
docker compose run --build --rm test python -m pytest tests/ -v --cov=src --cov=config
```

### Package Management
```bash
# Update poetry.lock file after changing dependencies
poetry lock

# Install/update all dependencies from lock file
poetry install
```

### Docker Management
```bash
# Stop all services
docker compose down

# Remove all containers and images
docker compose down --rmi all

# Prune all (suitable to run from time to time)
docker system prune -a
```
