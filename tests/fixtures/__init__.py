"""
Test fixtures package for CurveEditor.

This package contains organized test fixtures split by domain:
- qt_fixtures: Qt application and widget fixtures
- mock_fixtures: Mock objects for testing (consolidated to 2 core fixtures)
- data_fixtures: Test data generators and builders
- service_fixtures: Service layer test fixtures
- production_fixtures: Production-realistic workflow fixtures

Fixture Selection Guide:
- Unit tests (no Qt): use `mock_curve_view`
- Integration tests (with Qt widgets): use `mock_main_window`
- Multi-state/workflow tests: use `production_widget_factory`
"""

# Component fixtures removed - classes now available directly from test_helpers
from tests.fixtures.data_fixtures import (
    keyframe_curve_data,
    large_sample_points,
    sample_curve_data,
    sample_points,
)
from tests.fixtures.mock_fixtures import (
    mock_curve_view,
    mock_main_window,
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
    load_curve_data_via_state,
    mark_qt_used,
    qapp,
    qt_cleanup,
    ui_file_load_signals,
    ui_file_load_worker,
)
from tests.fixtures.state_helpers import reset_all_test_state
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
    "load_curve_data_via_state",
    "mark_qt_used",
    "memory_monitor",
    # Mock fixtures (consolidated from 7 to 2)
    "mock_curve_view",
    "mock_main_window",
    # Production fixtures
    "production_widget_factory",
    "qapp",
    "qt_cleanup",
    "reset_all_test_state",
    "safe_test_data_factory",
    "sample_curve_data",
    "sample_points",
    "ui_file_load_signals",
    "ui_file_load_worker",
    "user_interaction",
]
