# Service Testing Plan

This document outlines a comprehensive strategy for testing the service-based architecture to ensure the refactoring was successful and to establish a foundation for ongoing development.

## Testing Goals

1. **Verify Functionality**: Ensure all functionality works correctly after the refactoring.
2. **Validate Architecture**: Confirm that services are properly separated with clear responsibilities.
3. **Establish Test Coverage**: Create a comprehensive test suite covering all major services.
4. **Detect Regression Issues**: Identify any regressions introduced during the refactoring.

## Testing Strategy

The testing approach will use a combination of:

1. **Unit Tests**: Testing individual service methods
2. **Integration Tests**: Testing service interactions
3. **Functional Tests**: End-to-end testing of key workflows
4. **Validation Scripts**: Automated checks for architectural compliance

## Unit Testing Plan

### Priority Services for Testing

1. **CurveService**
   - Point selection and manipulation
   - View transformations
   - Coordinate systems handling

2. **AnalysisService**
   - Curve smoothing operations
   - Gap filling algorithms
   - Data transformation methods

3. **CenteringZoomService**
   - Zoom operations
   - Centering functions
   - View management

### Test Structure

Each service should have a dedicated test module following this structure:

```python
import unittest
from unittest.mock import Mock, patch
from services.curve_service import CurveService

class TestCurveService(unittest.TestCase):
    def setUp(self):
        # Set up test fixtures
        self.mock_curve_view = Mock()
        self.mock_main_window = Mock()

        # Configure mock objects
        self.mock_curve_view.points = []
        self.mock_curve_view.selected_points = set()
        # etc.

    def test_select_point_by_index(self):
        # Arrange
        self.mock_curve_view.points = [(1, 100, 200), (2, 150, 250), (3, 200, 300)]

        # Act
        result = CurveService.select_point_by_index(self.mock_curve_view, self.mock_main_window, 1)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_curve_view.selected_point_idx, 1)
        self.assertEqual(self.mock_curve_view.selected_points, {1})
        self.mock_curve_view.update.assert_called_once()
```

## Test Cases by Service

### 1. CurveService

| Test Case | Description | Expected Outcome |
|-----------|-------------|------------------|
| `test_select_point_by_index` | Selecting a point by index | Point selected, view updated |
| `test_select_points_in_rect` | Selecting points within a rectangle | All points in rect selected |
| `test_transform_point` | Point coordinate transformation | Correct widget coordinates |
| `test_update_point_position` | Updating point coordinates | Point moved, state updated |
| `test_delete_selected_points` | Deleting selected points | Points removed, view updated |
| `test_nudge_selected_points` | Nudging points with arrow keys | Points moved by correct increment |
| `test_find_point_at` | Finding a point at coordinates | Correct point index returned |

### 2. AnalysisService

| Test Case | Description | Expected Outcome |
|-----------|-------------|------------------|
| `test_smooth_moving_average` | Smoothing with moving average | Correct smoothed values |
| `test_smooth_gaussian` | Smoothing with gaussian filter | Correct smoothed values |
| `test_smooth_savitzky_golay` | Smoothing with SG filter | Correct smoothed values |
| `test_fill_gap_linear` | Filling gaps with linear method | Gap filled with linear points |
| `test_fill_gap_spline` | Filling gaps with spline method | Gap filled with spline points |
| `test_normalize_velocity` | Normalizing point velocities | Points spaced by velocity |
| `test_detect_problems` | Detecting tracking issues | Problems correctly identified |

### 3. CenteringZoomService

| Test Case | Description | Expected Outcome |
|-----------|-------------|------------------|
| `test_reset_view` | Resetting view to default | View reset, zoom=1.0, offset=0 |
| `test_zoom_in` | Zooming in on a point | Zoom increased, centered on point |
| `test_zoom_out` | Zooming out from a view | Zoom decreased, view maintained |
| `test_pan_view` | Panning the view | View offset updated correctly |
| `test_center_on_point` | Centering on a specific point | View centered on point |
| `test_calculate_centering_offsets` | Calculating centering offsets | Correct offset values |

## Integration Testing

| Test Case | Description | Involved Services |
|-----------|-------------|------------------|
| `test_curve_edit_with_history` | Edit points and check history | CurveService, HistoryService |
| `test_smooth_curve_visualization` | Smooth curve and verify display | AnalysisService, VisualizationService |
| `test_file_operations_with_history` | Load/save files with undo support | FileService, HistoryService |
| `test_image_sequence_navigation` | Navigate image sequence | ImageService, InputService |

## Validation Scripts

Expand the existing `refactoring_validation.py` to:

1. **Verify Service Isolation**: Check for improper dependencies between services
2. **Validate Import Patterns**: Ensure all imports follow the standardized pattern
3. **Check Legacy References**: Look for any remaining references to legacy modules
4. **Detect Circular Dependencies**: Identify any potential circular references

## Automated Test Workflow

Create a simple test runner that:

1. Discovers and runs all available tests
2. Generates a coverage report
3. Validates service architecture
4. Reports any issues found

```python
#!/usr/bin/env python
# test_runner.py

import unittest
import coverage
import subprocess
import sys

def run_tests():
    """Run all unit tests and generate coverage report."""
    cov = coverage.Coverage(
        source=['services'],
        omit=['*/__init__.py', '*/test_*.py']
    )
    cov.start()

    # Discover and run all tests
    loader = unittest.TestLoader()
    suite = loader.discover('./tests', pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    cov.stop()
    cov.save()

    # Print coverage report
    print("\nCoverage Report:")
    cov.report()

    # Generate HTML report
    cov.html_report(directory='coverage_html')
    print(f"HTML coverage report generated in: coverage_html/index.html")

    return result.wasSuccessful()

def validate_architecture():
    """Run the architecture validation script."""
    print("\nValidating service architecture...")
    result = subprocess.run([sys.executable, 'refactoring_validation.py'],
                            capture_output=True, text=True)

    print(result.stdout)

    if result.returncode != 0:
        print("Architecture validation failed!")
        return False

    return True

if __name__ == '__main__':
    tests_passed = run_tests()
    architecture_valid = validate_architecture()

    if tests_passed and architecture_valid:
        print("\n✅ All tests passed and architecture validated successfully!")
        sys.exit(0)
    else:
        print("\n❌ Tests or validation failed. See output above for details.")
        sys.exit(1)
```

## Test Implementation Timeline

| Phase | Timeframe | Status | Activities |
|-------|-----------|--------|------------|
| 1 | Week 1 | ✅ Complete | Set up testing framework, create base test classes |
| 2 | Week 2-3 | ✅ Complete | Implement CurveService, AnalysisService, CenteringZoomService tests |
| 3 | Week 4 | ⏳ In Progress | Implement InputService, VisualizationService tests |
| 4 | Week 5 | ⏳ Started | Initial MainWindow tests and validation scripts |
| 5 | Week 6-7 | 🔜 Planned | Implement FileService, ImageService, DialogService tests |
| 6 | Week 8 | 🔜 Planned | Implement HistoryService, SettingsService tests |
| 7 | Week 9-10 | 🔜 Planned | Integration tests between services |
| 8 | Ongoing | 🔄 Continuous | Maintain and expand test coverage with new features |

Current focus is on completing phase 3 with VisualizationService testing as the highest priority.

## Testing Best Practices

1. **Test Independence**: Each test should be independent and not rely on state from other tests.
2. **Mock Dependencies**: Use mocks for dependent services and UI components.
3. **Verify State Changes**: Check both function returns and state changes in objects.
4. **Test Edge Cases**: Include tests for boundary conditions and error handling.
5. **Maintain Test Clarity**: Keep test names descriptive and focused on what they verify.

## Conclusion

This testing plan provides a comprehensive approach to validating the refactored service-based architecture. By implementing these tests, we can ensure the refactoring was successful and establish a foundation for maintaining high code quality as the application evolves.

The plan emphasizes a balanced approach with unit tests for individual services, integration tests for service interactions, and validation scripts to verify architectural compliance. By following this plan, we can have confidence in the application's reliability and maintainability.
