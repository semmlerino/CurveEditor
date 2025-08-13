"""
Mock object fixtures for testing.

Contains fixtures that provide mock objects for various components.
"""

from unittest.mock import MagicMock, PropertyMock

import pytest

# Import mock classes from test utilities
from tests.test_utilities import (
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
        curve_data=[(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)],
        selected_indices=[1]
    )


@pytest.fixture
def lazy_mock_main_window():
    """Create a mock main window with lazy UI component creation."""
    return LazyUIMockMainWindow()


@pytest.fixture
def mock_service():
    """Create a generic mock service."""
    service = MagicMock()
    service.is_initialized = True
    service.get_state.return_value = {"status": "ready"}
    return service


@pytest.fixture
def mock_transform_service():
    """Create a mock transform service."""
    service = MagicMock()
    service.get_transform.return_value = MagicMock(
        scale=1.0,
        offset_x=0.0,
        offset_y=0.0,
        data_to_screen=lambda x, y: (x, y),
        screen_to_data=lambda x, y: (x, y),
    )
    return service


@pytest.fixture
def mock_data_service():
    """Create a mock data service."""
    service = MagicMock()
    service.curve_data = PropertyMock(return_value=[])
    service.load_file.return_value = True
    service.save_file.return_value = True
    service.validate_data.return_value = (True, [])
    return service


@pytest.fixture
def mock_interaction_service():
    """Create a mock interaction service."""
    service = MagicMock()
    service.selected_indices = PropertyMock(return_value=set())
    service.handle_mouse_press.return_value = True
    service.handle_mouse_move.return_value = False
    service.handle_mouse_release.return_value = True
    return service


@pytest.fixture
def mock_ui_service():
    """Create a mock UI service."""
    service = MagicMock()
    service.show_dialog.return_value = True
    service.update_status.return_value = None
    service.get_user_input.return_value = "test_input"
    return service


@pytest.fixture
def mock_file_dialog():
    """Create a mock file dialog."""
    dialog = MagicMock()
    dialog.exec.return_value = True
    dialog.selectedFiles.return_value = ["/path/to/file.txt"]
    dialog.selectedFilter.return_value = "Text Files (*.txt)"
    return dialog


@pytest.fixture
def mock_message_box():
    """Create a mock message box."""
    box = MagicMock()
    box.exec.return_value = MagicMock(value=1024)  # QMessageBox.Yes
    box.information = MagicMock()
    box.warning = MagicMock()
    box.critical = MagicMock()
    box.question = MagicMock(return_value=1024)
    return box


@pytest.fixture
def mock_progress_dialog():
    """Create a mock progress dialog."""
    dialog = MagicMock()
    dialog.wasCanceled.return_value = False
    dialog.setValue = MagicMock()
    dialog.setLabelText = MagicMock()
    dialog.setMaximum = MagicMock()
    return dialog


@pytest.fixture
def mock_settings():
    """Create a mock settings object."""
    settings = MagicMock()
    settings.value.return_value = None
    settings.setValue = MagicMock()
    settings.contains.return_value = False
    settings.allKeys.return_value = []
    return settings


@pytest.fixture
def mock_clipboard():
    """Create a mock clipboard."""
    clipboard = MagicMock()
    clipboard.text.return_value = ""
    clipboard.setText = MagicMock()
    clipboard.clear = MagicMock()
    return clipboard
