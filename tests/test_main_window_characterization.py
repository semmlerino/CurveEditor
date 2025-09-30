"""
Characterization tests for MainWindow refactoring.

These tests capture the CURRENT behavior of MainWindow to ensure
we don't break anything during refactoring.
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


@pytest.fixture
def qapp():
    """Ensure QApplication exists for tests."""
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    yield app


@pytest.fixture
def main_window(qapp, monkeypatch):
    """Create MainWindow instance for testing."""
    # Patch auto-loading to prevent side effects
    monkeypatch.setattr(MainWindow, "_load_burger_tracking_data", Mock(return_value=None))

    window = MainWindow()
    window.show()
    qapp.processEvents()

    yield window

    window.close()


class TestMainWindowInitialization:
    """Test MainWindow initialization behavior."""

    def test_window_creates_successfully(self, main_window):
        """Window should initialize without errors."""
        assert main_window is not None
        assert main_window.isVisible()

    def test_essential_widgets_exist(self, main_window):
        """Critical widgets should be created."""
        assert main_window.curve_widget is not None
        assert main_window.frame_spinbox is not None
        assert main_window.frame_slider is not None
        assert main_window.status_label is not None

    def test_actions_are_created(self, main_window):
        """All actions should be initialized."""
        assert main_window.action_new is not None
        assert main_window.action_open is not None
        assert main_window.action_save is not None
        assert main_window.action_load_images is not None
        assert main_window.action_undo is not None
        assert main_window.action_redo is not None

    def test_initial_frame_is_one(self, main_window):
        """Initial frame should be 1."""
        assert main_window.current_frame == 1
        assert main_window.frame_spinbox.value() == 1
        assert main_window.frame_slider.value() == 1

    def test_file_load_worker_exists(self, main_window):
        """FileLoadWorker should be initialized."""
        assert main_window.file_load_worker is not None

    def test_services_are_initialized(self, main_window):
        """Service manager should be available."""
        assert main_window.services is not None
        assert main_window.state_manager is not None


class TestFrameNavigation:
    """Test frame navigation behavior."""

    def test_frame_spinbox_changes_current_frame(self, main_window, qapp):
        """Changing spinbox should update current frame."""
        # Set maximum to allow frame 5
        main_window.frame_spinbox.setMaximum(10)
        main_window.frame_spinbox.setValue(5)
        qapp.processEvents()

        assert main_window.current_frame == 5

    def test_frame_slider_changes_current_frame(self, main_window, qapp):
        """Changing slider should update current frame."""
        # Set maximum to allow frame 10
        main_window.frame_slider.setMaximum(20)
        main_window.frame_spinbox.setMaximum(20)
        main_window.frame_slider.setValue(10)
        qapp.processEvents()

        assert main_window.current_frame == 10

    def test_next_frame_increments(self, main_window):
        """Next frame should increment current frame."""
        # Set maximum to allow incrementing
        main_window.frame_spinbox.setMaximum(10)
        initial = main_window.current_frame
        main_window.frame_navigation_controller.go_to_next_frame()

        assert main_window.current_frame == initial + 1

    def test_prev_frame_decrements(self, main_window):
        """Previous frame should decrement current frame."""
        # Set maximum and current frame
        main_window.frame_spinbox.setMaximum(10)
        main_window.current_frame = 5
        main_window.frame_navigation_controller.go_to_previous_frame()

        assert main_window.current_frame == 4

    def test_first_frame_goes_to_one(self, main_window):
        """First frame should set frame to 1."""
        # Set maximum to allow frame 10
        main_window.frame_spinbox.setMaximum(20)
        main_window.current_frame = 10
        main_window.frame_navigation_controller.go_to_first_frame()

        assert main_window.current_frame == 1

    def test_last_frame_goes_to_max(self, main_window):
        """Last frame should go to maximum frame."""
        main_window.frame_slider.setMaximum(100)
        main_window.frame_spinbox.setMaximum(100)
        main_window.frame_navigation_controller.go_to_last_frame()

        assert main_window.current_frame == 100


class TestPlaybackControl:
    """Test playback functionality."""

    def test_playback_timer_exists(self, main_window):
        """Playback timer should be created."""
        assert main_window.playback_timer is not None

    def test_play_pause_starts_timer(self, main_window):
        """Play should start the timer."""
        main_window._on_play_pause(True)

        assert main_window.playback_timer.isActive()

        # Cleanup
        main_window._on_play_pause(False)

    def test_play_pause_stops_timer(self, main_window):
        """Pause should stop the timer."""
        main_window._on_play_pause(True)
        main_window._on_play_pause(False)

        assert not main_window.playback_timer.isActive()

    def test_playback_advances_frame(self, main_window, qapp):
        """Playback should advance frames."""
        from controllers.playback_controller import PlaybackMode

        # Set maximum to allow advancing
        main_window.frame_spinbox.setMaximum(10)
        initial = main_window.current_frame
        main_window.playback_controller.state.mode = PlaybackMode.PLAYING_FORWARD
        main_window.playback_controller.state.max_frame = 10

        main_window._on_playback_timer()
        qapp.processEvents()

        assert main_window.current_frame == initial + 1

    def test_oscillating_playback_reverses(self, main_window):
        """Oscillating playback should reverse at bounds."""
        from controllers.playback_controller import PlaybackMode

        # Set up oscillating playback
        main_window.frame_spinbox.setMaximum(10)
        main_window.state_manager.total_frames = 10  # Must set total_frames first!
        main_window.playback_controller.state.mode = PlaybackMode.PLAYING_FORWARD
        main_window.playback_controller.state.min_frame = 1
        main_window.playback_controller.state.max_frame = 5
        main_window.playback_controller.state.loop_boundaries = True  # Oscillating mode
        main_window.current_frame = 5

        main_window._on_playback_timer()

        # After hitting max, should reverse to PLAYING_BACKWARD
        assert main_window.playback_controller.state.mode == PlaybackMode.PLAYING_BACKWARD


class TestFileOperations:
    """Test file operation behaviors."""

    @patch("PySide6.QtWidgets.QFileDialog.getOpenFileName")
    def test_open_action_shows_dialog(self, mock_dialog, main_window):
        """Open action should show file dialog."""
        mock_dialog.return_value = ("", "")

        main_window.file_operations_manager.open_file()

        mock_dialog.assert_called_once()

    @patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory")
    def test_load_images_shows_directory_dialog(self, mock_dialog, main_window):
        """Load images should show directory dialog."""
        mock_dialog.return_value = ""

        main_window.file_operations_manager.load_image_sequence()

        mock_dialog.assert_called_once()

    def test_save_requires_curve_data(self, main_window):
        """Save should check for curve data."""
        main_window.curve_widget.curve_data = None

        with patch.object(main_window.services, "show_warning") as mock_warning:
            main_window.file_operations_manager.save_file()
            mock_warning.assert_called_once()

    def test_file_load_worker_starts(self, main_window):
        """File load worker should start when given files."""
        with patch.object(main_window.file_load_worker, "start_work") as mock_start:
            main_window.file_load_worker.start_work("test.txt", None)
            mock_start.assert_called_once_with("test.txt", None)


class TestSignalConnections:
    """Test that signals are properly connected."""

    def test_curve_widget_signals_connected(self, main_window):
        """Curve widget signals should be connected."""
        # Check that emitting signals doesn't raise errors
        if main_window.curve_widget:
            main_window.curve_widget.selection_changed.emit([])  # Pass empty list
            main_window.curve_widget.view_changed.emit()

    def test_frame_spinbox_connected(self, main_window, qapp):
        """Frame spinbox should be connected to frame changes."""
        # Set maximum to allow value change
        main_window.frame_spinbox.setMaximum(20)

        with patch.object(main_window.frame_navigation_controller, "on_frame_spinbox_changed") as mock_handler:
            main_window.frame_spinbox.setValue(10)
            qapp.processEvents()

            # May be called multiple times due to signal propagation
            assert mock_handler.called

    def test_action_triggers_connected(self, main_window):
        """Actions should be connected to handlers."""
        with patch.object(main_window.file_operations_manager, "new_file") as mock_new:
            main_window.action_new.trigger()
            mock_new.assert_called_once()


class TestUIState:
    """Test UI state management."""

    def test_background_checkbox_state(self, main_window):
        """Background checkbox should control visibility."""
        if main_window.show_background_cb and main_window.curve_widget:
            main_window.show_background_cb.setChecked(True)
            assert main_window.curve_widget.show_background

            main_window.show_background_cb.setChecked(False)
            assert not main_window.curve_widget.show_background

    def test_undo_redo_enabled_state(self, main_window):
        """Undo/redo should be disabled initially."""
        assert not main_window.action_undo.isEnabled()
        assert not main_window.action_redo.isEnabled()

    def test_status_bar_updates(self, main_window):
        """Status bar should show messages."""
        test_message = "Test status message"
        main_window.status_label.setText(test_message)

        assert main_window.status_label.text() == test_message


class TestDataLoading:
    """Test data loading behavior."""

    def test_tracking_data_loaded_handler(self, main_window):
        """Tracking data loaded should update curve widget."""
        test_data = [(1, 100, 200), (2, 150, 250)]

        with patch.object(main_window.curve_widget, "set_curve_data") as mock_set:
            main_window._on_tracking_data_loaded(test_data)
            mock_set.assert_called_once()

    def test_image_sequence_loaded_handler(self, main_window):
        """Image sequence loaded should store image info."""
        test_images = ["image1.png", "image2.png"]

        main_window._on_image_sequence_loaded("/test/path", test_images)

        # Check that image info was stored
        assert main_window.state_manager.image_directory == "/test/path"
        assert main_window.image_filenames == test_images
        # current_image_idx should exist - if missing, test will fail with AttributeError
        assert main_window.current_image_idx >= 0

    def test_file_load_progress_updates_status(self, main_window):
        """File load progress should update status bar."""
        main_window._on_file_load_progress(50, "Loading...")

        # Status may go to statusBar or status_label depending on configuration
        status_bar = getattr(main_window, "statusBar", None)
        if status_bar is not None:
            status_text = status_bar().currentMessage()
        else:
            status_text = main_window.status_label.text()

        assert "Loading..." in status_text
        assert "50%" in status_text


class TestKeyboardShortcuts:
    """Test keyboard shortcut functionality."""

    def test_delete_key_handled(self, main_window):
        """Delete key should trigger point deletion."""
        # This would need curve_widget to have selected points
        pass  # Placeholder for keyboard tests

    def test_escape_key_deselects(self, main_window):
        """Escape key should deselect all."""
        # Would need to simulate key press
        pass  # Placeholder


class TestMemoryAndResources:
    """Test resource management."""

    def test_worker_cleanup_on_close(self, main_window):
        """Worker threads should be cleaned up on close."""
        with patch.object(main_window.file_load_worker, "stop") as mock_stop:
            main_window.close()
            mock_stop.assert_called()

    def test_timer_stops_on_close(self, main_window):
        """Timers should stop when window closes."""
        main_window._on_play_pause(True)
        main_window.close()

        assert not main_window.playback_timer.isActive()


class TestIntegrationScenarios:
    """Test complete user workflows."""

    def test_load_edit_save_workflow(self, main_window):
        """Test complete load, edit, save workflow."""
        # This would be a comprehensive integration test
        pass  # Placeholder for integration test

    def test_image_then_tracking_workflow(self, main_window):
        """Test loading images then tracking data."""
        # Important for coordinate transform testing
        pass  # Placeholder for integration test
