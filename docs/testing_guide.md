# CurveEditor Testing Guide

This document provides information about the testing system in CurveEditor, including how to run tests, add new tests, and check code coverage.

## Overview

CurveEditor uses a comprehensive testing approach to ensure the reliability and correctness of its codebase. The testing infrastructure includes:

- Unit tests for individual services and components
- Integration tests for interactions between services
- A test runner with coverage reporting
- Architecture validation tools

## Running Tests

### Using the Test Runner

The primary way to run tests is using the `test_runner.py` script:

```bash
python test_runner.py
```

This will discover and run all tests in the `tests/` directory.

### Command-line Options

The test runner supports several command-line options:

- `--verbose` or `-v`: Show more detailed test output
- `--coverage` or `-c`: Generate a coverage report
- `--validate` or `-a`: Run architecture validation checks
- `--module MODULE` or `-m MODULE`: Run tests for a specific module
- `--pattern PATTERN` or `-p PATTERN`: Run tests matching a pattern

Examples:

```bash
# Run tests with verbose output
python test_runner.py -v

# Run tests and generate coverage report
python test_runner.py -c

# Run tests for a specific service
python test_runner.py -m curve_service

# Run tests matching a pattern
python test_runner.py -p test_curve*
```

### Running Individual Tests

You can also run individual test files directly:

```bash
python -m unittest tests/test_curve_service.py
```

Or run a specific test case:

```bash
python -m unittest tests.test_curve_service.TestCurveService.test_select_point
```

## Test Structure

Tests are organized in the `tests/` directory, with test files following the naming pattern `test_*.py`.

### Test File Organization

Each test file typically follows this structure:

```python
import unittest
from unittest.mock import MagicMock, patch

# Import the service or component being tested
from services.curve_service import CurveService

class TestCurveService(unittest.TestCase):
    def setUp(self):
        # Setup code that runs before each test
        pass

    def tearDown(self):
        # Cleanup code that runs after each test
        pass

    def test_method_name(self):
        # Test a specific method
        result = CurveService.method_name(params)
        self.assertEqual(result, expected_value)

    # More test methods...
```

## Current Test Coverage

The test suite currently includes comprehensive tests for:

- `CurveService`: Point selection, manipulation, and data handling
- `AnalysisService`: Curve smoothing, gap filling, and analysis
- `CenteringZoomService`: View centering and zoom operations

Tests in progress:
- `VisualizationService`
- `ImageService`
- `FileService`

## Adding New Tests

When adding new tests:

1. Create a new test file in the `tests/` directory with the naming pattern `test_*_service.py`
2. Follow the test structure outlined above
3. Focus on testing the public API of the service
4. Use mocks for dependencies to isolate the service being tested
5. Run the test runner to ensure your tests pass

### Example: Adding a New Test File

```python
# tests/test_visualization_service.py
import unittest
from unittest.mock import MagicMock

from services.visualization_service import VisualizationService

class TestVisualizationService(unittest.TestCase):
    def setUp(self):
        self.main_window = MagicMock()
        self.curve_view = MagicMock()

    def test_toggle_grid(self):
        # Test the toggle_grid method
        VisualizationService.toggle_grid(self.main_window, True)
        # Assert that the correct methods were called
        self.curve_view.set_grid_visible.assert_called_with(True)

    # More test methods...
```

## Code Coverage

The test runner can generate code coverage reports using the `--coverage` option:

```bash
python test_runner.py --coverage
```

This will generate a coverage report showing:
- Which lines of code were executed during testing
- Which lines were not executed
- Overall coverage percentage

### Current Coverage Metrics

| Module | Coverage |
|--------|----------|
| CurveService | ~85% |
| AnalysisService | ~80% |
| CenteringZoomService | ~75% |
| Overall | ~35% |

The target is to achieve at least 80% overall coverage.

## Architecture Validation

The test runner includes architecture validation checks that verify the codebase adheres to the service-based architecture:

```bash
python test_runner.py --validate
```

This runs the `refactoring_validation.py` script, which checks for:
- Proper import patterns
- No circular dependencies
- Consistent naming conventions
- Appropriate use of services

## Common Test Patterns

### Testing UI Components

For UI components, use mock objects to simulate the UI environment:

```python
def test_ui_interaction(self):
    # Create mock objects
    mock_window = MagicMock()
    mock_curve_view = MagicMock()

    # Set up the mock to return a specific value
    mock_curve_view.get_selected_points.return_value = [1, 2, 3]

    # Call the service method
    CurveService.update_selection(mock_window, mock_curve_view)

    # Verify the expected interactions
    mock_window.update_point_display.assert_called_once()
```

### Testing Error Handling

For error handling, use the `assertRaises` context manager:

```python
def test_error_handling(self):
    with self.assertRaises(ValueError):
        CurveService.update_point_position(None, None, -1, 0, 0)
```

## Troubleshooting Tests

### Tests Failing

If tests are failing:
1. Check the error message to understand what's failing
2. Use print statements or the debugger to investigate
3. Ensure your mock objects are correctly configured
4. Verify that the test environment matches the expected state

### Mock Objects Not Working

If mock objects aren't behaving as expected:
1. Ensure you're mocking the correct object or method
2. Check that the mock is configured correctly
3. Verify that the mock is being passed to the code under test

## Next Steps for Testing

1. Complete test implementation for all services
2. Add integration tests for key workflows
3. Integrate test coverage reporting with CI/CD
4. Enhance architecture validation
5. Add UI component tests

## Conclusion

Testing is a critical part of the CurveEditor development process. The service-based architecture makes it easier to write comprehensive tests that verify the behavior of individual components and their interactions.
