"""
Test fixtures package for CurveEditor.

This package contains organized test fixtures split by domain:
- qt_fixtures: Qt application and widget fixtures
- mock_fixtures: Mock objects for testing
- data_fixtures: Test data generators and builders
- service_fixtures: Service layer test fixtures
"""

from tests.fixtures.component_fixtures import (
    test_curve_view,
    test_curve_view_with_data,
    test_main_window,
    test_main_window_with_data,
)
from tests.fixtures.data_fixtures import (
    keyframe_curve_data,
    large_sample_points,
    sample_curve_data,
    sample_points,
    test_data_builder,
)
from tests.fixtures.mock_fixtures import (
    lazy_mock_main_window,
    mock_curve_view,
    mock_curve_view_with_selection,
    mock_main_window,
    mock_main_window_with_data,
    protocol_compliant_mock_curve_view,
    protocol_compliant_mock_main_window,
)
from tests.fixtures.qt_fixtures import (
    curve_view,
    curve_view_widget,
    qapp,
    qt_cleanup,
    qt_widget_cleanup,
)
from tests.fixtures.service_fixtures import (
    isolated_services,
    memory_monitor,
)

__all__ = [
    # Data fixtures
    "sample_curve_data",
    "keyframe_curve_data",
    "sample_points",
    "large_sample_points",
    "test_data_builder",
    # Mock fixtures
    "mock_curve_view",
    "mock_curve_view_with_selection",
    "mock_main_window",
    "mock_main_window_with_data",
    "protocol_compliant_mock_curve_view",
    "protocol_compliant_mock_main_window",
    "lazy_mock_main_window",
    # Qt fixtures
    "qapp",
    "qt_cleanup",
    "qt_widget_cleanup",
    "curve_view",
    "curve_view_widget",
    # Service fixtures
    "isolated_services",
    "memory_monitor",
    # Component fixtures
    "test_curve_view",
    "test_curve_view_with_data",
    "test_main_window",
    "test_main_window_with_data",
]
