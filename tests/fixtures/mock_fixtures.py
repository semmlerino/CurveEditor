"""
Mock object fixtures for testing.

Contains fixtures that provide mock objects for various components.
"""

import pytest

# Import mock classes from test helpers
from tests.test_helpers import (
    BaseMockCurveView,
    BaseMockMainWindow,
    LazyUIMockMainWindow,
    ProtocolCompliantMockCurveView,
    ProtocolCompliantMockMainWindow,
)


@pytest.fixture
def mock_curve_view():
    """Create a basic mock curve view for testing."""
    return BaseMockCurveView()


@pytest.fixture
def mock_curve_view_with_selection():
    """Create a mock curve view with selected points."""
    return BaseMockCurveView(selected_points={1, 2})


@pytest.fixture
def protocol_compliant_mock_curve_view():
    """Create a fully protocol-compliant mock curve view."""
    return ProtocolCompliantMockCurveView()


@pytest.fixture
def protocol_compliant_mock_main_window():
    """Create a fully protocol-compliant mock main window."""
    return ProtocolCompliantMockMainWindow()


@pytest.fixture
def mock_main_window():
    """Create a basic mock main window for testing."""
    return BaseMockMainWindow()


@pytest.fixture
def mock_main_window_with_data():
    """Create a mock main window with sample curve data."""
    return BaseMockMainWindow(
        curve_data=[(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)], selected_indices=[1]
    )


@pytest.fixture
def lazy_mock_main_window():
    """Create a mock main window with lazy UI component creation."""
    return LazyUIMockMainWindow()
