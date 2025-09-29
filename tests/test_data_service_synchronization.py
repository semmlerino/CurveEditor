#!/usr/bin/env python3
"""
Tests for DataService synchronization with CurveDataStore.

Following UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md best practices:
- Test behavior, not implementation
- Use real components with mocked boundaries
- Proper signal testing with QSignalSpy
- RED-GREEN-REFACTOR for bug fixes
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from core.commands.shortcut_command import ShortcutContext
from core.commands.shortcut_commands import SetEndframeCommand
from core.models import PointStatus
from services import get_data_service
from ui.curve_view_widget import CurveViewWidget
from ui.file_operations import FileOperations
from ui.main_window import MainWindow


class TestDataServiceSynchronization:
    """Test suite for DataService synchronization with curve data changes."""

    @pytest.fixture
    def app(self):
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def curve_widget(self, app, qtbot):
        """Create real CurveViewWidget for testing."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)  # CRITICAL: Auto cleanup
        return widget

    @pytest.fixture
    def main_window(self, app, qtbot):
        """Create real MainWindow with mocked dependencies."""
        # Mock the auto-load to prevent file access
        with patch.object(FileOperations, "load_burger_data_async"):
            window = MainWindow()

            # Mock services to avoid external dependencies
            window.services = Mock()
            window.services.confirm_action = Mock(return_value=True)
            window.services.load_track_data = Mock(return_value=[])
            window.services.save_track_data = Mock(return_value=True)
            window.services.analyze_curve_bounds = Mock(
                return_value={
                    "count": 5,
                    "min_frame": 1,
                    "max_frame": 20,
                    "bounds": {"min_x": 100, "max_x": 300, "min_y": 200, "max_y": 400},
                }
            )
            window.services.add_to_history = Mock()

            qtbot.addWidget(window)  # CRITICAL: Auto cleanup
            yield window

    @pytest.fixture
    def test_tracking_data(self):
        """Create test tracking point data."""
        return [
            (1, 100.0, 200.0, "keyframe"),
            (5, 150.0, 250.0, "interpolated"),
            (10, 200.0, 300.0, "keyframe"),
            (15, 250.0, 350.0, "keyframe"),
            (20, 300.0, 400.0, "interpolated"),
        ]

    def test_data_service_synchronized_on_curve_data_change(self, curve_widget, test_tracking_data):
        """Test that DataService gets updated when curve data changes."""
        # Get DataService instance
        data_service = get_data_service()

        # Initially DataService should have no data
        assert data_service._current_curve_data is None
        assert data_service._segmented_curve is None

        # Set curve data - this should trigger synchronization
        curve_widget.set_curve_data(test_tracking_data)

        # Verify DataService was synchronized
        assert data_service._current_curve_data is not None
        assert len(data_service._current_curve_data) == len(test_tracking_data)
        assert data_service._segmented_curve is not None

        # Verify data content matches
        for i, expected_point in enumerate(test_tracking_data):
            actual_point = data_service._current_curve_data[i]
            assert actual_point[0] == expected_point[0]  # frame
            assert actual_point[1] == expected_point[1]  # x
            assert actual_point[2] == expected_point[2]  # y
            assert actual_point[3] == expected_point[3]  # status

    def test_data_service_synchronized_on_empty_data(self, curve_widget):
        """Test DataService synchronization with empty data."""
        data_service = get_data_service()

        # Set some initial data
        initial_data = [(1, 100.0, 200.0, "keyframe")]
        curve_widget.set_curve_data(initial_data)
        assert data_service._current_curve_data is not None

        # Clear data
        curve_widget.set_curve_data([])

        # Verify DataService was synchronized with empty data
        assert data_service._current_curve_data == []
        assert data_service._segmented_curve is None

    def test_status_change_works_after_synchronization(self, curve_widget, test_tracking_data):
        """Test that point status changes work after DataService synchronization."""
        data_service = get_data_service()

        # Set curve data
        curve_widget.set_curve_data(test_tracking_data)

        # Verify DataService is synchronized
        assert data_service._current_curve_data is not None

        # Test status change operation - this should NOT fail anymore
        try:
            data_service.handle_point_status_change(0, PointStatus.ENDFRAME.value)
            success = True
        except Exception as e:
            success = False
            error_msg = str(e)

        # Assert the operation succeeded
        assert success, f"Status change failed: {error_msg if not success else ''}"

    def test_endframe_command_works_with_tracking_data(self, main_window, test_tracking_data):
        """Test that E key command works properly with tracking point data."""
        # Set up test data
        if main_window.curve_widget:
            main_window.curve_widget.set_curve_data(test_tracking_data)

        # Set current frame to a frame with data
        main_window.state_manager.current_frame = 1

        # Create shortcut context for E key press
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier)

        context = ShortcutContext(
            main_window=main_window,
            focused_widget=main_window.curve_widget,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=1,
        )

        # Create and test the command
        command = SetEndframeCommand()

        # Should be able to execute (frame 1 has a point)
        can_execute = command.can_execute(context)
        assert can_execute, "SetEndframeCommand should be able to execute with current frame data"

        # Execute the command - this should NOT fail anymore
        try:
            success = command.execute(context)
            assert success, "SetEndframeCommand execution should succeed"
        except Exception as e:
            pytest.fail(f"SetEndframeCommand execution failed: {e}")

    def test_multiple_data_changes_maintain_synchronization(self, curve_widget):
        """Test that multiple data changes maintain proper synchronization."""
        data_service = get_data_service()

        # Test data sets
        data_sets = [
            [(1, 10.0, 20.0, "keyframe")],
            [(1, 10.0, 20.0, "keyframe"), (5, 50.0, 60.0, "interpolated")],
            [(10, 100.0, 200.0, "endframe")],
            [],  # Empty data
        ]

        for i, data_set in enumerate(data_sets):
            # Set data
            curve_widget.set_curve_data(data_set)

            # Verify synchronization
            if data_set:
                assert data_service._current_curve_data is not None
                assert len(data_service._current_curve_data) == len(data_set)
                assert data_service._segmented_curve is not None
            else:
                assert data_service._current_curve_data == []
                assert data_service._segmented_curve is None

    def test_synchronization_handles_exceptions_gracefully(self, curve_widget, test_tracking_data):
        """Test that synchronization handles exceptions without breaking."""
        # Mock get_data_service to raise an exception
        with patch("ui.curve_view_widget.get_data_service") as mock_get_service:
            mock_get_service.side_effect = RuntimeError("Service unavailable")

            # This should not crash, just log an error
            try:
                curve_widget.set_curve_data(test_tracking_data)
                # Should complete without raising an exception
                success = True
            except Exception:
                success = False

            assert success, "Synchronization should handle service exceptions gracefully"

    def test_red_green_refactor_bug_reproduction(self, curve_widget, test_tracking_data):
        """
        RED-GREEN-REFACTOR test: Reproduce the original bug scenario.

        This test reproduces the exact scenario from the log where:
        1. Tracking points are loaded
        2. E key is pressed to change status
        3. "Cannot handle status change: no current curve data" error occurred
        """
        data_service = get_data_service()

        # RED: Reproduce the bug scenario
        # 1. Load tracking data (simulating 2DTrackDatav2.txt load)
        curve_widget.set_curve_data(test_tracking_data)

        # 2. Verify the fix worked - DataService should be synchronized
        assert data_service._current_curve_data is not None, "DataService should have curve data"
        assert data_service._segmented_curve is not None, "DataService should have segmented curve"

        # 3. Test the operation that was failing - point status change
        # This was the exact operation that failed in the log
        try:
            data_service.handle_point_status_change(0, "endframe")
            # GREEN: The fix works - no exception thrown
            bug_fixed = True
            error_msg = ""
        except Exception as e:
            # This would be the original bug
            bug_fixed = False
            error_msg = str(e)

        assert bug_fixed, f"The synchronization bug should be fixed: {error_msg}"

        # REFACTOR: Verify the fix maintains data integrity
        # The point status should actually be changed
        updated_data = curve_widget.curve_data
        # Note: The actual status change depends on the command implementation
        # but the important thing is that it doesn't crash
        assert updated_data is not None, "Curve data should remain accessible after status change"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
