"""
Mock object fixtures for testing.

Contains fixtures that provide mock objects for various components.

Fixture Selection Guide:
- `mock_curve_view`: Lightweight mock for unit tests (no Qt widgets)
- `mock_main_window`: Full mock with Qt widgets for integration tests
- Use `production_widget_factory` from production_fixtures.py for multi-state tests
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

import pytest

# Import mock classes from test helpers
from tests.test_helpers import (
    BaseMockCurveView,
    MockMainWindow,
)
from tests.fixtures.qt_fixtures import mark_qt_used


@pytest.fixture
def mock_curve_view() -> BaseMockCurveView:
    """Create a basic mock curve view for unit testing.

    Use this for tests that don't need Qt widgets - fast and isolated.

    Returns:
        BaseMockCurveView: Lightweight mock implementing CurveViewProtocol
    """
    return BaseMockCurveView()


@pytest.fixture
def mock_main_window(qapp) -> MockMainWindow:
    """Create a full mock main window for integration testing.

    Includes real Qt widgets (QSlider, QSpinBox, etc.) and state_manager.
    Requires QApplication since it creates real Qt widgets.

    Use this for tests that need to verify signal connections and widget behavior.

    Returns:
        MockMainWindow: Mock implementing MainWindowProtocol with real Qt widgets
    """
    mark_qt_used()
    return MockMainWindow()
