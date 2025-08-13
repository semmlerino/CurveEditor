# Testing Best Practices for CurveEditor

## Overview

This guide documents testing patterns, lessons learned, and best practices established during Sprint 9's test remediation efforts.

## Current Test Status

### Metrics (Sprint 9 Day 6)
- **Total Tests**: 493 (90 added in Sprint 9)
- **Passing**: 350 (71%)
- **Failing**: 118 (24%)
- **Coverage**: 30% overall, 23% for Sprint 8 services

### Test Organization
```
tests/
├── conftest.py                 # Shared fixtures
├── fixtures/                   # Reusable test fixtures
│   ├── data_fixtures.py
│   ├── mock_fixtures.py
│   └── service_fixtures.py
├── test_*.py                   # Test modules
└── archive/                    # Old/broken tests
```

## Testing Patterns

### 1. Service Testing Pattern

Services should be tested in isolation with mocked dependencies:

```python
import unittest
from unittest.mock import Mock, MagicMock
from services.selection_service import SelectionService

class TestSelectionService(unittest.TestCase):
    def setUp(self):
        """Create service and mock view."""
        self.service = SelectionService()
        
        # Create mock view with required attributes
        self.mock_view = Mock()
        self.mock_view.points = [
            (1, 10.0, 20.0),
            (2, 30.0, 40.0)
        ]
        self.mock_view.selected_points = set()
        self.mock_view.update = Mock()
    
    def test_select_point(self):
        """Test point selection."""
        result = self.service.select_point_by_index(self.mock_view, 0)
        self.assertTrue(result)
        self.assertEqual(self.mock_view.selected_points, {0})
```

### 2. Qt Widget Testing Pattern

Qt widgets require special handling:

```python
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import pytest

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()

def test_widget_interaction(qapp, qtbot):
    """Test Qt widget with qtbot."""
    widget = CurveViewWidget()
    qtbot.addWidget(widget)
    
    # Simulate mouse click
    qtbot.mouseClick(widget, Qt.LeftButton)
    
    # Verify behavior
    assert widget.selected_points == {0}
```

### 3. Mock Complex Dependencies

For complex Qt dependencies, create typed mocks:

```python
class MockCurveView:
    """Typed mock for CurveViewProtocol."""
    
    def __init__(self, points=None):
        self.points = points or []
        self.selected_points = set()
        self.transform = Mock()
        self.update = Mock()
    
    def repaint(self):
        """Mock repaint method."""
        pass

def test_with_typed_mock():
    view = MockCurveView(points=[(1, 10.0, 20.0)])
    service = SelectionService()
    service.select_all(view)
    assert len(view.selected_points) == 1
```

### 4. Test Data Builders

Create builders for complex test data:

```python
class TestDataBuilder:
    """Builder for test data."""
    
    @staticmethod
    def curve_data(num_points=10, start_frame=1):
        """Create sample curve data."""
        return [
            (start_frame + i, float(i * 10), float(i * 20))
            for i in range(num_points)
        ]
    
    @staticmethod
    def point_with_status(frame, x, y, status="tracked"):
        """Create point with status."""
        return (frame, x, y, status)

# Usage
def test_large_dataset():
    data = TestDataBuilder.curve_data(num_points=1000)
    assert len(data) == 1000
```

### 5. Parameterized Testing

Use pytest's parametrize for multiple test cases:

```python
import pytest

@pytest.mark.parametrize("index,expected", [
    (0, True),   # Valid index
    (-1, False), # Negative index
    (100, False) # Out of range
])
def test_select_point_validation(index, expected):
    service = SelectionService()
    view = MockCurveView(points=[(1, 10.0, 20.0)])
    
    result = service.select_point_by_index(view, index)
    assert result == expected
```

## Test Coverage Strategies

### 1. Critical Path Coverage

Focus on user-critical paths first:

```python
def test_complete_workflow():
    """Test full user workflow."""
    # 1. Load data
    service = DataService()
    data = service.load_json("test.json")
    
    # 2. Select points
    selection = SelectionService()
    selection.select_all(view)
    
    # 3. Modify points
    manipulation = PointManipulationService()
    manipulation.move_selected_points(view, 10, 20)
    
    # 4. Save data
    service.save_json("output.json", view.points)
```

### 2. Edge Case Testing

Always test boundaries and edge cases:

```python
def test_edge_cases():
    """Test boundary conditions."""
    service = HistoryService()
    
    # Empty state
    assert service.undo() is None
    
    # Single item
    service.add_to_history([(1, 10.0, 20.0)])
    assert service.can_undo()
    
    # Maximum items
    for i in range(100):  # Max history size
        service.add_to_history([(i, 10.0, 20.0)])
    assert service.get_history_size() <= 100
```

### 3. Error Handling Tests

Test error conditions explicitly:

```python
def test_error_handling():
    """Test error conditions."""
    service = FileIOService()
    
    # Invalid file path
    with pytest.raises(FileNotFoundError):
        service.load_json("/invalid/path.json")
    
    # Corrupted data
    with pytest.raises(ValueError):
        service.parse_data("not json")
    
    # Permission denied
    with pytest.raises(PermissionError):
        service.save_json("/root/forbidden.json", [])
```

## Running Tests

### Basic Test Run
```bash
source venv/bin/activate
export QT_QPA_PLATFORM=offscreen  # For headless Qt testing
python -m pytest tests/
```

### With Coverage
```bash
python -m pytest tests/ --cov=services --cov=ui --cov=core \
    --cov-report=term-missing --cov-report=html
```

### Run Specific Tests
```bash
# Single test file
python -m pytest tests/test_selection_service.py

# Single test method
python -m pytest tests/test_selection_service.py::TestSelectionService::test_select_point

# Tests matching pattern
python -m pytest -k "select"
```

### Parallel Testing
```bash
python -m pytest -n auto  # Use all CPU cores
```

### Verbose Output
```bash
python -m pytest -v  # Verbose
python -m pytest -vv # Very verbose
```

## Common Testing Issues and Solutions

### Issue 1: Qt Platform Error
**Problem**: `qt.qpa.plugin: Could not load the Qt platform plugin`

**Solution**: Set environment variable:
```bash
export QT_QPA_PLATFORM=offscreen
```

### Issue 2: Import Errors
**Problem**: Tests can't import modules

**Solution**: Ensure proper Python path:
```python
# In conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Issue 3: Async/Thread Issues
**Problem**: Tests fail due to threading

**Solution**: Use Qt's test event loop:
```python
def test_async_operation(qtbot):
    widget = MyWidget()
    
    with qtbot.waitSignal(widget.finished, timeout=1000):
        widget.start_async_operation()
    
    assert widget.result is not None
```

### Issue 4: Test Isolation
**Problem**: Tests affect each other

**Solution**: Reset state in tearDown:
```python
def tearDown(self):
    """Clean up after each test."""
    # Clear singletons
    ServiceRegistry.clear()
    
    # Reset environment
    os.environ.pop("USE_NEW_SERVICES", None)
    
    # Clear caches
    get_transform_service.cache_clear()
```

## Test Maintenance

### When Refactoring Code
1. **Run tests first** - Ensure they pass
2. **Refactor code** - Make changes
3. **Update tests** - Fix broken tests
4. **Add new tests** - Cover new functionality

### Test Review Checklist
- [ ] Tests are independent (no shared state)
- [ ] Tests have descriptive names
- [ ] Edge cases are covered
- [ ] Error conditions are tested
- [ ] Mocks are properly configured
- [ ] No hardcoded paths or data
- [ ] Tests run in CI/CD environment

### Performance Testing
```python
import pytest
import time

@pytest.mark.benchmark
def test_performance(benchmark):
    """Benchmark critical operations."""
    service = TransformService()
    data = TestDataBuilder.curve_data(10000)
    
    result = benchmark(service.transform_points, data)
    
    # Assert performance requirements
    assert benchmark.stats['mean'] < 0.1  # Less than 100ms
```

## Test Documentation

### Test Naming Convention
```python
def test_<what>_<condition>_<expected>():
    """Test that <what> <expected> when <condition>."""
    
# Examples:
def test_select_point_valid_index_returns_true():
    """Test that select_point returns True with valid index."""

def test_undo_empty_history_returns_none():
    """Test that undo returns None when history is empty."""
```

### Test Documentation
```python
def test_complex_workflow():
    """
    Test complete point editing workflow.
    
    This test verifies:
    1. Points can be loaded from file
    2. Points can be selected
    3. Selected points can be modified
    4. Changes can be undone/redone
    5. Modified data can be saved
    
    Regression test for issue #123.
    """
```

## Coverage Goals

### Target Coverage by Component

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| Core Services | 30% | 80% | High |
| UI Widgets | 51% | 60% | Medium |
| Utilities | 65% | 80% | Medium |
| Data Processing | 20% | 70% | High |
| Test Files | N/A | N/A | N/A |

### Coverage Commands
```bash
# Generate HTML coverage report
python -m pytest --cov=. --cov-report=html
open htmlcov/index.html

# Show missing lines
python -m pytest --cov=services --cov-report=term-missing

# Coverage for specific module
python -m pytest --cov=services.selection_service
```

## Continuous Integration

### GitHub Actions Configuration
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-qt
    
    - name: Run tests
      env:
        QT_QPA_PLATFORM: offscreen
      run: |
        python -m pytest tests/ --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Conclusion

Testing the CurveEditor requires handling Qt widgets, complex service interactions, and legacy code patterns. Focus on:

1. **Critical paths first** - Test what users actually do
2. **Isolation** - Mock dependencies properly  
3. **Pragmatism** - Some tests are better than no tests
4. **Maintenance** - Keep tests updated with code changes

Remember: Tests are code too - keep them clean, maintainable, and well-documented.

---

*Last Updated: Sprint 9 Day 6*
*Test Framework: pytest 8.4.1*
*Coverage Tool: pytest-cov 6.2.1*