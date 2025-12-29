# auto-grade

<div align="center">

[![CI Pipeline](https://github.com/FumingPower3925/auto-grade/actions/workflows/test.yaml/badge.svg)](https://github.com/FumingPower3925/auto-grade/actions/workflows/test.yaml)
[![codecov](https://codecov.io/github/FumingPower3925/auto-grade/graph/badge.svg?token=RID2DG7P0F)](https://codecov.io/github/FumingPower3925/auto-grade)
[![Code Quality](https://github.com/FumingPower3925/auto-grade/actions/workflows/code-quality.yaml/badge.svg)](https://github.com/FumingPower3925/auto-grade/actions/workflows/code-quality.yaml)
[![Security Scan](https://github.com/FumingPower3925/auto-grade/actions/workflows/security.yaml/badge.svg)](https://github.com/FumingPower3925/auto-grade/actions/workflows/security.yaml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=FumingPower3925_auto-grade&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=FumingPower3925_auto-grade)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=FumingPower3925_auto-grade&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=FumingPower3925_auto-grade)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue)](http://mypy-lang.org/)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)

</div>

A PoC of an automatic bulk assignment grader LLM engine

## Project Status

<div align="center">

| Metric | Status |
|--------|--------|
| **Build Status** | ![Build](https://img.shields.io/github/actions/workflow/status/FumingPower3925/auto-grade/test.yaml?branch=main) |
| **Code Coverage** | ![Coverage](https://img.shields.io/codecov/c/github/FumingPower3925/auto-grade) - **100% Required** |
| **Code Quality** | [![SonarCloud](https://sonarcloud.io/api/project_badges/measure?project=FumingPower3925_auto-grade&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=FumingPower3925_auto-grade) |
| **Technical Debt** | [![Technical Debt](https://sonarcloud.io/api/project_badges/measure?project=FumingPower3925_auto-grade&metric=sqale_index)](https://sonarcloud.io/summary/new_code?id=FumingPower3925_auto-grade) |
| **Dependencies** | ![Dependencies](https://img.shields.io/librariesio/github/FumingPower3925/auto-grade) - Deactivated, waiting for [#784](https://github.com/pyupio/safety/issues/784) |
| **Last Commit** | ![Last Commit](https://img.shields.io/github/last-commit/FumingPower3925/auto-grade) |

</div>

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/FumingPower3925/auto-grade.git
   cd auto-grade
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your secrets
   ```

3. **Run the application**
   ```bash
   make build  # Build Docker images
   make up     # Start the application
   ```

The API will be available at `http://localhost:8080/api` and the web interface at `http://localhost:8080`

## Development Commands

All commands are available through the Makefile. Run `make help` to see all available commands.

### Application Management
```bash
make build          # Build all Docker images
make up             # Start the application
make down           # Stop all services and remove volumes
make logs           # View application logs
```

### Testing
```bash
make test           # Run all tests
make test-unit      # Run unit tests with 100% coverage requirement
make test-integration # Run integration tests
make test-e2e       # Run end-to-end tests with Playwright
```

### Code Quality
```bash
make lint           # Run ruff linter with auto-fix and format
make lint-check     # Check linting without auto-fix
make type-check     # Run mypy type checking
make format         # Format code with ruff
make security       # Run security checks with bandit
```

### Package Management
```bash
uv lock             # Update uv.lock file after changing dependencies
uv sync             # Install/update all dependencies from lock file
```

## Testing

The project includes comprehensive testing with multiple layers:

- **Unit Tests**: Test individual components in isolation (`tests/unit/`)
  - **100% coverage required** - CI will fail if coverage drops below 100%
  - Coverage is only collected from unit tests
- **Integration Tests**: Test component interactions (`tests/integration/`)
  - No coverage requirements
  - Tests API endpoints and database operations
- **E2E Tests**: Test complete user workflows using Playwright (`tests/e2e/`)
  - Browser-based testing
  - Screenshots and videos captured on failure

### Test Architecture
- **Parallel Execution**: All test types run in parallel for faster CI
- Unit and integration tests run in dedicated Docker containers
- E2E tests run with Playwright for browser automation
- All tests are automatically run in the CI/CD pipeline
- Coverage reports are generated and uploaded to Codecov

### CI/CD Pipeline Features
- **Parallel test execution** for faster feedback
- **100% code coverage enforcement** on unit tests
- **Code quality checks** with mypy, ruff, and bandit
- **Security scanning** with Trivy and safety
- **SonarCloud integration** for code quality metrics
- **Multi-platform Docker builds** (AMD64 & ARM64)
- **Artifact uploads** for test results and coverage reports

## Contributing

> **⚠️ Important Notice**
>
> This project is part of my Master's Thesis at [Universitat Politècnica de Catalunya (UPC)](https://www.upc.edu/).
> **Until the thesis is presented and defended, I cannot accept external contributions.**
>
> After the thesis presentation (expected mid-2025), all contributions will be welcome!

### After Thesis Presentation

Once the thesis is complete, contributions will be welcome! Here's how to contribute:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Ensure tests pass with 100% coverage (`make test-unit`)
4. Commit your changes (`git commit -m 'Add some amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Development Requirements
- Python 3.13+
- Docker and Docker Compose
- UV for dependency management
- 100% test coverage for new code

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## Author

**Albert Bausili**
- Email: albert.bausili@gmail.com
- GitHub: [@FumingPower3925](https://github.com/FumingPower3925)