"""
Test fixtures package for CurveEditor.

This package contains organized test fixtures split by domain:
- qt_fixtures: Qt application and widget fixtures
- mock_fixtures: Mock objects for testing
- data_fixtures: Test data generators and builders
- service_fixtures: Service layer test fixtures
- production_fixtures: Production-realistic workflow fixtures
"""

# Component fixtures removed - classes now available directly from test_helpers
from tests.fixtures.data_fixtures import (
    keyframe_curve_data,
    large_sample_points,
    sample_curve_data,
    sample_points,
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
from tests.fixtures.production_fixtures import (
    production_widget_factory,
    safe_test_data_factory,
    user_interaction,
)
from tests.fixtures.qt_fixtures import (
    curve_view_widget,
    file_load_signals,
    file_load_worker,
    qapp,
    qt_cleanup,
    ui_file_load_signals,
    ui_file_load_worker,
)
from tests.fixtures.service_fixtures import (
    all_services,
    app_state,
    curve_with_data,
    isolated_services,
    memory_monitor,
)

__all__ = [
    "all_services",
    "app_state",
    "curve_view_widget",
    "curve_with_data",
    "file_load_signals",
    "file_load_worker",
    "isolated_services",
    "keyframe_curve_data",
    "large_sample_points",
    "lazy_mock_main_window",
    "memory_monitor",
    "mock_curve_view",
    "mock_curve_view_with_selection",
    "mock_main_window",
    "mock_main_window_with_data",
    "production_widget_factory",
    "protocol_compliant_mock_curve_view",
    "protocol_compliant_mock_main_window",
    "qapp",
    "qt_cleanup",
    "safe_test_data_factory",
    "sample_curve_data",
    "sample_points",
    "ui_file_load_signals",
    "ui_file_load_worker",
    "user_interaction",
]
