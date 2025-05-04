import pytest
from unittest.mock import MagicMock, patch
from typing import Generator, Tuple
from main_window import MainWindow
import sys

# Assume QApplication is needed for Qt widgets
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QAction

# We need to patch the imports before any imports that depend on them
# Important: Patch CurveView *before* importing MainWindow to avoid metaclass conflict
curve_view_mock = MagicMock()
menu_bar_mock = MagicMock()
ui_components_mock = MagicMock()
shortcut_manager_mock = MagicMock()
signal_registry_mock = MagicMock()
config_mock = MagicMock()
track_quality_ui_mock = MagicMock()
load_3de_track_mock = MagicMock(return_value=("", 0, 0, []))
estimate_dimensions_mock = MagicMock(return_value=(1920, 1080))
get_image_files_mock = MagicMock(return_value=[])

# Apply patches to modules that will be imported by main_window
sys.modules['curve_view'] = MagicMock()
sys.modules['curve_view'].CurveView = curve_view_mock

# Mock other dependencies
sys.modules['menu_bar'] = MagicMock()
sys.modules['menu_bar'].MenuBar = menu_bar_mock

sys.modules['ui_components'] = MagicMock()
sys.modules['ui_components'].UIComponents = ui_components_mock

sys.modules['keyboard_shortcuts'] = MagicMock()
sys.modules['keyboard_shortcuts'].ShortcutManager = shortcut_manager_mock

sys.modules['signal_registry'] = MagicMock()
sys.modules['signal_registry'].SignalRegistry = signal_registry_mock

sys.modules['config'] = config_mock

sys.modules['track_quality'] = MagicMock()
sys.modules['track_quality'].TrackQualityUI = track_quality_ui_mock

sys.modules['utils'] = MagicMock()
sys.modules['utils'].load_3de_track = load_3de_track_mock
sys.modules['utils'].estimate_image_dimensions = estimate_dimensions_mock
sys.modules['utils'].get_image_files = get_image_files_mock

@pytest.fixture


def main_window_fixture() -> Generator[Tuple[MainWindow, MagicMock], None, None]:
    """Pytest fixture to create a MainWindow instance for testing."""
    with patch('main_window.ZoomOperations') as mock_zoom_operations: # Use context manager
        # Need a QApplication instance for Qt widgets
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        # Import MainWindow *after* patches are applied
        from main_window import MainWindow

        window = MainWindow()
        # Mock the menu action that set_centering_enabled interacts with
        window.auto_center_action = MagicMock(spec=QAction)
        window.auto_center_action.setChecked = MagicMock() # Mock the setChecked method

        # Mock the curve_view instance and its selected_point_idx
        window.curve_view = MagicMock()
        window.curve_view.selected_point_idx = -1 # Default to no selection

        # Return the window instance AND the mock created by the context manager
        yield window, mock_zoom_operations # Use yield for fixtures with context managers

# Test functions using the fixture, updated to unpack the returned tuple
@pytest.mark.skip(reason="Needs updating for CurveViewProtocol changes")
def test_set_centering_enabled_true_with_selection(main_window_fixture: Tuple[MainWindow, MagicMock]) -> None:
    """Test enabling auto-centering when a point is selected."""
    window, mock_zoom_ops = main_window_fixture # Unpack fixture result
    window.curve_view.selected_point_idx = 0 # Simulate point selection
    mock_zoom_ops.reset_mock() # Reset mock before action

    window.set_centering_enabled(True)

    assert window.auto_center_enabled is True
    window.auto_center_action.setChecked.assert_called_once_with(True)
    mock_zoom_ops.center_on_selected_point.assert_called_once_with(window.curve_view)

@pytest.mark.skip(reason="Needs updating for CurveViewProtocol changes")
def test_set_centering_enabled_true_without_selection(main_window_fixture: Tuple[MainWindow, MagicMock]) -> None:
    """Test enabling auto-centering when NO point is selected."""
    window, mock_zoom_ops = main_window_fixture # Unpack fixture result
    curve_view: MagicMock = window.curve_view
    curve_view.selected_point_idx = -1 # Ensure no selection
    mock_zoom_ops.reset_mock() # Reset mock before action

    window.set_centering_enabled(True)

    assert window.auto_center_enabled is True
    window.auto_center_action.setChecked.assert_called_once_with(True)
    mock_zoom_ops.center_on_selected_point.assert_not_called() # Should not be called

@pytest.mark.skip(reason="Needs updating for CurveViewProtocol changes")
def test_set_centering_enabled_false(main_window_fixture: Tuple[MainWindow, MagicMock]) -> None:
    """Test disabling auto-centering."""
    window, mock_zoom_ops = main_window_fixture # Unpack fixture result
    window.curve_view.selected_point_idx = 0 # Simulate point selection
    # Set initial state to True to test toggling off
    window.auto_center_enabled = True
    auto_center_action: MagicMock = window.auto_center_action
    setChecked = auto_center_action.setChecked
    reset_mock = setChecked.reset_mock
    reset_mock() # Reset mock from potential fixture setup
    reset_mock_zoom = mock_zoom_ops.reset_mock
    reset_mock_zoom() # Reset ZoomOperations mock

    window.set_centering_enabled(False)

    assert window.auto_center_enabled is False
    window.auto_center_action.setChecked.assert_called_once_with(False)
    mock_zoom_ops.center_on_selected_point.assert_not_called() # Should not be called

@pytest.mark.skip(reason="Needs updating for CurveViewProtocol changes")
def test_set_centering_enabled_idempotent_true(main_window_fixture: Tuple[MainWindow, MagicMock]) -> None:
    """Test enabling auto-centering when already enabled."""
    window, mock_zoom_ops = main_window_fixture # Unpack fixture result
    window.curve_view.selected_point_idx = 0 # Simulate point selection
    window.auto_center_enabled = True # Start enabled
    auto_center_action: MagicMock = window.auto_center_action
    setChecked = auto_center_action.setChecked
    reset_mock = setChecked.reset_mock
    reset_mock()
    reset_mock_zoom = mock_zoom_ops.reset_mock
    reset_mock_zoom()

    set_centering_enabled = window.set_centering_enabled
    set_centering_enabled(True) # Call again with True

    assert window.auto_center_enabled is True # Should remain True
    setChecked = window.auto_center_action.setChecked
    assert_called_once_with = setChecked.assert_called_once_with
    assert_called_once_with(True) # Should still update action state
    curve_view: MagicMock = window.curve_view
    center_on_selected_point = mock_zoom_ops.center_on_selected_point
    assert_called_once_with = center_on_selected_point.assert_called_once_with
    assert_called_once_with(curve_view) # Should still be called

@pytest.mark.skip(reason="Needs updating for CurveViewProtocol changes")
def test_set_centering_enabled_idempotent_false(main_window_fixture: Tuple[MainWindow, MagicMock]) -> None:
    """Test disabling auto-centering when already disabled."""
    window, mock_zoom_ops = main_window_fixture # Unpack fixture result
    window.curve_view.selected_point_idx = 0 # Simulate point selection
    window.auto_center_enabled = False # Start disabled
    auto_center_action: MagicMock = window.auto_center_action
    setChecked = auto_center_action.setChecked
    reset_mock = setChecked.reset_mock
    reset_mock()
    reset_mock_zoom = mock_zoom_ops.reset_mock
    reset_mock_zoom()

    set_centering_enabled = window.set_centering_enabled
    set_centering_enabled(False) # Call again with False

    assert window.auto_center_enabled is False # Should remain False
    setChecked = window.auto_center_action.setChecked
    assert_called_once_with = setChecked.assert_called_once_with
    assert_called_once_with(False) # Should still update action state
    mock_zoom_ops.center_on_selected_point.assert_not_called() # Should not be called