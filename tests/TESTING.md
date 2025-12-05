# CurveEditor Testing Guide

Comprehensive guide for running, writing, and maintaining tests.

**Configuration**: All test settings are in `pyproject.toml` (`[tool.pytest.ini_options]`).

## Quick Commands

```bash
# Development (stop at first failure - PREFERRED)
uv run pytest tests/ -x -q

# Full validation (pre-commit)
uv run pytest tests/ -v

# Unit tests only (fast, no Qt)
uv run pytest tests/ -m unit -x -q

# Integration tests (Qt widgets)
uv run pytest tests/ -m production -x -q

# Single test debugging (disable parallel execution)
uv run pytest tests/test_foo.py::TestClass::test_method -n0 -v

# Performance benchmarks
uv run pytest tests/ -m performance --benchmark-only

# Coverage report
uv run pytest tests/ --cov=. --cov-report=html
```

## Test Organization

```
tests/
├── conftest.py              # Root fixtures and Qt setup
├── fixtures/                # Shared test fixtures
│   ├── __init__.py          # Re-exports all fixtures
│   ├── qt_fixtures.py       # Qt app, widgets, cleanup
│   ├── mock_fixtures.py     # Mock objects (2 core fixtures)
│   ├── data_fixtures.py     # Test data generators
│   ├── service_fixtures.py  # Service layer fixtures
│   ├── production_fixtures.py  # Production workflow fixtures
│   └── state_helpers.py     # State reset utilities
├── commands/                # Command pattern edge cases
├── controllers/             # UI controller tests
├── core/                    # Core model tests
├── rendering/               # Renderer edge cases
├── services/                # Service layer edge cases
├── stores/                  # ApplicationState tests
├── ui/                      # UI component tests
├── test_*.py               # Feature/integration tests
└── TESTING.md              # This file
```

### Organization Philosophy

- **Subdirectories**: Edge cases and unit tests for specific modules
- **Root-level**: Feature tests, integration tests, and workflow tests
- **Naming**: `test_<feature>_<aspect>.py` (e.g., `test_gap_behavior.py`)

When adding new tests:
- **Edge cases for a module** → Put in appropriate subdirectory
- **Integration/feature tests** → Put at root level
- **Tests matching existing file** → Add to that file

## Fixture Selection Guide

### Quick Decision Tree

```
Need Qt widgets?
├── No  → mock_curve_view (unit test)
└── Yes
    ├── Single state → mock_main_window (integration)
    └── Multiple states → production_widget_factory (workflow)
```

### Core Fixtures (Use These)

| Fixture | Purpose | Qt Required | Use When |
|---------|---------|-------------|----------|
| `mock_curve_view` | Lightweight mock | No | Unit tests, no Qt deps |
| `mock_main_window` | Full mock with widgets | Yes | Integration tests with signals |
| `production_widget_factory` | Factory for states | Yes | Multi-state workflow tests |

### Frame Range Fixtures (Opt-in)

By default, tests start with **no frames loaded**. Use these fixtures when you need frame data:

| Fixture | Frames | Use When |
|---------|--------|----------|
| `with_minimal_frame_range` | 100 | Basic navigation, timeline tests |
| `with_large_frame_range` | 1000 | Stress tests, performance tests |
| `without_dummy_frames` | 0 | Empty state scenarios (explicit) |

### Autouse Fixtures (Automatic)

These run automatically - you don't need to request them:

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `reset_services` | function | Resets all singletons between tests |
| `thread_sweep_per_test` | function | Joins stray threads before cleanup |
| `global_thread_sweep` | session | Session-end thread cleanup |
| `qt_cleanup` | function | Processes Qt events on teardown |

## Writing New Tests

### Basic Test Structure

```python
# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none

import pytest
from tests.fixtures import mock_curve_view, sample_points

class TestMyComponent:
    """Test group for MyComponent functionality."""

    def test_basic_operation(self, mock_curve_view):
        """Test that basic operation works correctly."""
        # Arrange
        view = mock_curve_view

        # Act
        result = view.some_method()

        # Assert
        assert result == expected_value

    def test_with_frame_data(self, mock_main_window, with_minimal_frame_range):
        """Test requiring frame data."""
        # with_minimal_frame_range provides 100 frames
        app_state = with_minimal_frame_range
        app_state.set_frame(50)
        # ...
```

### Qt Event Processing Pattern

When testing code that emits signals, use this pattern instead of `qtbot.wait()`:

```python
from PySide6.QtWidgets import QApplication

def process_qt_events() -> None:
    """Process Qt events to allow signal propagation."""
    for _ in range(3):
        QApplication.processEvents()

# In tests:
def test_signal_propagation(self, mock_main_window):
    app_state = get_application_state()
    app_state.set_curve_data("test", data)
    process_qt_events()  # Instead of qtbot.wait(100)
    assert widget.has_data()
```

### Thread Cleanup Pattern

For tests with background workers:

```python
def test_threaded_operation(self, qtbot, file_load_worker):
    """Test with background thread."""
    worker = file_load_worker

    # Start operation
    worker.load_file("test.csv")

    # Wait for thread to finish (NOT qtbot.wait(500))
    worker.wait(timeout=2000)

    # Verify result
    assert worker.result is not None
```

## Test Categories

### Unit Tests (`-m unit`)

- No Qt widgets required
- Use `mock_curve_view` fixture
- Fast execution (~100ms per test)
- Focus on single component logic

### Integration Tests (`-m production`)

- Require Qt widgets
- Use `mock_main_window` or `curve_view_widget`
- Test signal connections and UI behavior
- May take longer due to Qt event processing

### Performance Tests (`-m performance`)

- Benchmarking and stress tests
- Use `--benchmark-only` flag
- Large datasets (1000+ frames)

## Common Pitfalls

### 1. Arbitrary Waits

```python
# BAD - Arbitrary wait
qtbot.wait(500)

# GOOD - Condition-based wait
qtbot.waitUntil(lambda: widget.is_ready(), timeout=1000)

# GOOD - Signal-based wait
with qtbot.waitSignal(widget.ready_signal, timeout=1000):
    widget.start_operation()

# GOOD - Event processing for signal propagation
process_qt_events()
```

### 2. Direct State Access in Tests

```python
# ACCEPTABLE - Direct state access for test setup
from stores.application_state import get_application_state
state = get_application_state()
state.set_curve_data("test", data)

# BETTER for integration - Through service layer
from services import get_data_service
service = get_data_service()
service.load_csv("/path/to/file.csv")
```

### 3. Missing Frame Data

```python
# BAD - Assumes frames exist
def test_navigation(self, mock_main_window):
    app_state.set_frame(50)  # Fails - no frames loaded

# GOOD - Explicit frame fixture
def test_navigation(self, mock_main_window, with_minimal_frame_range):
    app_state = with_minimal_frame_range
    app_state.set_frame(50)  # Works - 100 frames available
```

### 4. Qt Cleanup Issues

If tests hang or segfault, check for:
- Threads not joined before Qt cleanup
- Modal dialogs left open
- Signals connected to deleted objects

Use `thread_sweep_per_test` fixture (autouse) to prevent most issues.

## Coverage Expectations

| Component | Target | Notes |
|-----------|--------|-------|
| Core models | 90%+ | Pure Python, easy to test |
| Services | 80%+ | Business logic |
| Controllers | 70%+ | Coordination logic |
| UI widgets | 60%+ | Qt-dependent, harder to test |
| Rendering | 50%+ | Visual output verification |

## Debugging Tips

### Run Single Test with Verbose Output

```bash
uv run pytest tests/test_foo.py::test_method -n0 -vvs --log-cli-level=DEBUG
```

### Capture Qt Debug Output

```bash
QT_DEBUG_PLUGINS=1 uv run pytest tests/test_foo.py -n0 -v
```

### Profile Slow Tests

```bash
uv run pytest tests/ --durations=20
```

### Find Flaky Tests

```bash
# Run same test multiple times
uv run pytest tests/test_foo.py --count=10 -x
```

## Fixture Implementation Details

### reset_services (autouse)

Resets ALL service state between tests:
1. Clears caches (image cache, render cache)
2. Resets service singletons
3. Clears ApplicationState
4. Resets StateManager
5. Runs garbage collection

### qt_cleanup (autouse)

Processes pending Qt events after each test:
1. Checks if Qt was actually used
2. Processes events in batches
3. Runs garbage collection for Qt objects

### Thread Sweep Fixtures

Two-level thread cleanup:
1. `thread_sweep_per_test`: Joins threads after each test (1s timeout)
2. `global_thread_sweep`: Session-end cleanup (10ms per thread)

This prevents segfaults from threads accessing Qt objects during cleanup.

---
*See also: CLAUDE.md for architecture and development patterns*
