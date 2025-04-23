import pytest
from unittest.mock import MagicMock, patch

# Assume QApplication is needed for Qt widgets
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QAction

# Mock necessary modules/classes that MainWindow depends on during init
# This avoids needing the full application setup for unit tests
@patch('main_window.MenuBar', MagicMock())
@patch('main_window.UIComponents', MagicMock())
@patch('main_window.ShortcutManager', MagicMock())
@patch('main_window.SignalRegistry', MagicMock())
@patch('main_window.config', MagicMock())
@patch('main_window.TrackQualityUI', MagicMock())
@patch('main_window.CurveView', MagicMock()) # Mock the CurveView class itself
@patch('main_window.load_3de_track', MagicMock(return_value=("", 0, 0, []))) # Mock file loading
@patch('main_window.estimate_image_dimensions', MagicMock(return_value=(1920, 1080)))
@patch('main_window.get_image_files', MagicMock(return_value=[]))
@patch('os.path.exists', MagicMock(return_value=True)) # Assume paths exist
@patch('os.path.expanduser', MagicMock(return_value='/mock/home'))
@pytest.fixture
def main_window_fixture(): # Removed mock argument
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
def test_set_centering_enabled_true_with_selection(main_window_fixture):
    """Test enabling auto-centering when a point is selected."""
    window, mock_zoom_ops = main_window_fixture # Unpack fixture result
    window.curve_view.selected_point_idx = 0 # Simulate point selection
    mock_zoom_ops.reset_mock() # Reset mock before action

    window.set_centering_enabled(True)

    assert window.auto_center_enabled is True
    window.auto_center_action.setChecked.assert_called_once_with(True)
    mock_zoom_ops.center_on_selected_point.assert_called_once_with(window.curve_view)

def test_set_centering_enabled_true_without_selection(main_window_fixture):
    """Test enabling auto-centering when NO point is selected."""
    window, mock_zoom_ops = main_window_fixture # Unpack fixture result
    window.curve_view.selected_point_idx = -1 # Ensure no selection
    mock_zoom_ops.reset_mock() # Reset mock before action

    window.set_centering_enabled(True)

    assert window.auto_center_enabled is True
    window.auto_center_action.setChecked.assert_called_once_with(True)
    mock_zoom_ops.center_on_selected_point.assert_not_called() # Should not be called

def test_set_centering_enabled_false(main_window_fixture):
    """Test disabling auto-centering."""
    window, mock_zoom_ops = main_window_fixture # Unpack fixture result
    window.curve_view.selected_point_idx = 0 # Simulate point selection
    # Set initial state to True to test toggling off
    window.auto_center_enabled = True
    window.auto_center_action.setChecked.reset_mock() # Reset mock from potential fixture setup
    mock_zoom_ops.reset_mock() # Reset ZoomOperations mock

    window.set_centering_enabled(False)

    assert window.auto_center_enabled is False
    window.auto_center_action.setChecked.assert_called_once_with(False)
    mock_zoom_ops.center_on_selected_point.assert_not_called() # Should not be called

def test_set_centering_enabled_idempotent_true(main_window_fixture):
    """Test enabling auto-centering when already enabled."""
    window, mock_zoom_ops = main_window_fixture # Unpack fixture result
    window.curve_view.selected_point_idx = 0 # Simulate point selection
    window.auto_center_enabled = True # Start enabled
    window.auto_center_action.setChecked.reset_mock()
    mock_zoom_ops.reset_mock()

    window.set_centering_enabled(True) # Call again with True

    assert window.auto_center_enabled is True # Should remain True
    window.auto_center_action.setChecked.assert_called_once_with(True) # Should still update action state
    mock_zoom_ops.center_on_selected_point.assert_called_once_with(window.curve_view) # Should still be called

def test_set_centering_enabled_idempotent_false(main_window_fixture):
    """Test disabling auto-centering when already disabled."""
    window, mock_zoom_ops = main_window_fixture # Unpack fixture result
    window.curve_view.selected_point_idx = 0 # Simulate point selection
    window.auto_center_enabled = False # Start disabled
    window.auto_center_action.setChecked.reset_mock()
    mock_zoom_ops.reset_mock()

    window.set_centering_enabled(False) # Call again with False

    assert window.auto_center_enabled is False # Should remain False
    window.auto_center_action.setChecked.assert_called_once_with(False) # Should still update action state
    mock_zoom_ops.center_on_selected_point.assert_not_called() # Should not be called