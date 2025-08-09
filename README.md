# auto-grade

[![Test and Coverage](https://github.com/FumingPower/auto-grade/actions/workflows/test.yml/badge.svg)](https://github.com/FumingPower/auto-grade/actions/workflows/test.yaml)
[![codecov](https://codecov.io/github/FumingPower3925/auto-grade/graph/badge.svg?token=RID2DG7P0F)](https://codecov.io/github/FumingPower3925/auto-grade)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)

A PoC of an automatic bulk assignment grader LLM engine

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/FumingPower/auto-grade.git
   cd auto-grade
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your secrets
   ```

3. **Run the application**
   ```bash
   docker compose up --build auto-grade
   ```

The API will be available at `http://localhost:8080`

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

## Testing

The project includes comprehensive testing:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **E2E Tests**: Test complete user workflows

Tests are automatically run in CI/CD pipeline on every push and pull request and a coverage badge is generated.

## Contributing

Any and all contributions are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Albert Bausili**
- Email: albert.bausili@gmail.com