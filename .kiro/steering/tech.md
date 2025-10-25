# CurveEditor Technology Stack

## Core Framework
- **Python 3.12+**: Primary language with type hints required
- **PySide6 6.4.0+**: Qt6-based GUI framework for cross-platform UI
- **typing-extensions**: Backport of typing features for compatibility

## Dependencies
- **Pillow**: Primary image processing for standard formats
- **numpy**: Required for image processing and mathematical operations
- **imageio**: Alternative image loader for various formats
- **OpenEXR**: Official OpenEXR library for EXR file support

## Build System
- **uv**: Modern Python package manager and virtual environment tool
- **pyproject.toml**: Project configuration and dependency management
- **uv.lock**: Dependency lockfile for reproducible builds

## Development Tools
- **pytest**: Testing framework with Qt support (pytest-qt)
- **ruff**: Fast Python linter and formatter
- **basedpyright**: Type checker (Microsoft's Pylance engine)
- **pre-commit**: Git hooks for code quality

## Common Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Activate virtual environment (automatic with uv run)
uv shell
```

### Running the Application
```bash
# Start the application
uv run python main.py

# With debug logging
LOG_LEVEL=DEBUG uv run python main.py
```

### Testing
```bash
# Run all tests
uv run pytest tests/

# Run specific test file
uv run pytest tests/test_curve_service.py -v

# Run with coverage
uv run pytest --cov=. --cov-report=html tests/

# Run tests with timeout (offscreen Qt)
./run_tests.sh
```

### Code Quality
```bash
# Lint and format with Ruff
uv run ruff check .
uv run ruff check . --fix
uv run ruff format .

# Type checking
uv run basedpyright
./run_typecheck.sh

# Run pre-commit hooks
uv run pre-commit run --all-files
```

## Configuration Files
- **pyproject.toml**: Main project configuration
- **pytest.ini**: Test configuration and markers
- **.pre-commit-config.yaml**: Git hooks configuration
- **conftest.py**: Global pytest fixtures and setup