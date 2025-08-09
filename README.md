# auto-grade

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

The API will be available at `http://localhost:8080/api` and the web interface at `http://localhost:8080`

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
# Run unit and integration tests
docker compose --profile test run --build --rm -e PLAYWRIGHT_BASE_URL=http://auto-grade:8080 test

# Run only unit tests
docker compose --profile test run --build --rm test python -m pytest tests/unit/ -v

# Run only integration tests
docker compose --profile test run --build --rm test python -m pytest tests/integration/ -v

# Run E2E tests
docker compose --profile test run --rm -e PLAYWRIGHT_BASE_URL=http://auto-grade:8080 test python -m pytest tests/e2e/ -v

# Run tests with coverage report
docker compose --profile test run --build --rm test python -m pytest tests/unit/ tests/integration/ tests/e2e -v --cov=src --cov=config --cov-report=term
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

The project includes comprehensive testing with multiple layers:

- **Unit Tests**: Test individual components in isolation (`tests/unit/`)
- **Integration Tests**: Test component interactions (`tests/integration/`)
- **E2E Tests**: Test complete user workflows using Playwright (`tests/e2e/`)

### Test Architecture
- Unit and integration tests run in a dedicated Docker container
- E2E tests run in a separate Playwright container that communicates with the main application
- All tests are automatically run in the CI/CD pipeline
- Coverage reports are generated and uploaded to Codecov

The testing setup ensures reliable validation across all application layers, from individual functions to complete user interactions.

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