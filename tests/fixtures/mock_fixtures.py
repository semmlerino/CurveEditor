"""
Mock object fixtures for testing.

Contains fixtures that provide mock objects for various components.
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
    LazyUIMockMainWindow,
    MockMainWindow,
    ProtocolCompliantMockCurveView,
    ProtocolCompliantMockMainWindow,
)


@pytest.fixture
def mock_curve_view() -> BaseMockCurveView:
    """Create a basic mock curve view for testing."""
    return BaseMockCurveView()


@pytest.fixture
def mock_curve_view_with_selection() -> BaseMockCurveView:
    """Create a mock curve view with selected points."""
    return BaseMockCurveView(selected_points={1, 2})


@pytest.fixture
def protocol_compliant_mock_curve_view() -> ProtocolCompliantMockCurveView:
    """Create a fully protocol-compliant mock curve view."""
    return ProtocolCompliantMockCurveView()


@pytest.fixture
def protocol_compliant_mock_main_window() -> ProtocolCompliantMockMainWindow:
    """Create a fully protocol-compliant mock main window."""
    return ProtocolCompliantMockMainWindow()


@pytest.fixture
def mock_main_window() -> MockMainWindow:
    """Create a full mock main window for testing with state_manager and all protocol attributes."""
    return MockMainWindow()


@pytest.fixture
def mock_main_window_with_data() -> MockMainWindow:
    """Create a mock main window with sample curve data."""
    window = MockMainWindow()
    # Set curve data on the curve view
    window.curve_view.curve_data = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]
    window.curve_view.selected_points = {1}
    return window


@pytest.fixture
def lazy_mock_main_window() -> LazyUIMockMainWindow:
    """Create a mock main window with lazy UI component creation."""
    return LazyUIMockMainWindow()
