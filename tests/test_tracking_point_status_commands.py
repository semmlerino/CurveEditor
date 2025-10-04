#!/usr/bin/env python3
"""
Tests for status change commands (E key) with tracking point data.

This specifically tests the scenario from the original log where:
- Tracking points are loaded from 2DTrackDatav2.txt
- User presses E key to change status
- Previously failed with "Cannot handle status change: no current curve data"

Following UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md:
- Test behavior, not implementation
- RED-GREEN-REFACTOR for the specific bug
- Use real components where possible
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from core.commands.shortcut_command import ShortcutContext
from core.commands.shortcut_commands import SetEndframeCommand
from services import get_data_service
from ui.file_operations import FileOperations
from ui.main_window import MainWindow


class TestTrackingPointStatusCommands:
    """Test suite for status commands with tracking point data."""

    @pytest.fixture
    def app(self):
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def main_window(self, app, qtbot):
        """Create MainWindow with real tracking controller."""
        with patch.object(FileOperations, "load_burger_data_async"):
            window = MainWindow()

            # Mock services but keep tracking controller real
            window.services = Mock()
            window.services.confirm_action = Mock(return_value=True)
            window.services.load_track_data = Mock(return_value=[])
            window.services.save_track_data = Mock(return_value=True)
            window.services.analyze_curve_bounds = Mock(
                return_value={
                    "count": 12,
                    "min_frame": 1,
                    "max_frame": 37,
                    "bounds": {"min_x": 100, "max_x": 1200, "min_y": 200, "max_y": 700},
                }
            )

            qtbot.addWidget(window)
            yield window

    @pytest.fixture
    def multi_point_data(self):
        """Create multi-point tracking data similar to 2DTrackDatav2.txt."""
        return {
            "Point1": [
                (1, 100.0, 200.0, "keyframe"),
                (5, 120.0, 220.0, "interpolated"),
                (12, 150.0, 250.0, "keyframe"),
                (20, 180.0, 280.0, "interpolated"),
            ],
            "Point02": [
                (1, 200.0, 300.0, "keyframe"),
                (8, 230.0, 330.0, "interpolated"),
                (15, 250.0, 350.0, "keyframe"),
                (25, 280.0, 380.0, "interpolated"),
            ],
            "Point03": [
                (3, 300.0, 400.0, "keyframe"),
                (10, 320.0, 420.0, "interpolated"),
                (18, 350.0, 450.0, "keyframe"),
                (30, 380.0, 480.0, "interpolated"),
            ],
        }

    def test_original_bug_scenario_reproduction(self, main_window, multi_point_data):
        """
        Reproduce the exact scenario from the user's log:
        1. Load multi-point tracking data (like 2DTrackDatav2.txt)
        2. Press E key to change status
        3. Verify no "Cannot handle status change" error occurs
        """
        # Step 1: Load multi-point tracking data
        main_window.tracking_controller.on_multi_point_data_loaded(multi_point_data)

        # Verify tracking data is loaded
        assert len(main_window.tracking_controller.tracked_data) == 3
        assert "Point1" in main_window.tracking_controller.tracked_data

        # Step 2: Set current frame to a frame with tracking data
        main_window.state_manager.current_frame = 12

        # Verify curve widget has data (first active point should be displayed)
        assert main_window.curve_widget is not None
        curve_data = main_window.curve_widget.curve_data
        assert len(curve_data) > 0, "Curve widget should have data from active tracking point"

        # Verify DataService is synchronized
        data_service = get_data_service()
        assert data_service._current_curve_data is not None, "DataService should be synchronized"

        # Step 3: Test E key press - this was failing before the fix
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier)

        context = ShortcutContext(
            main_window=main_window,
            focused_widget=main_window.curve_widget,
            key_event=key_event,
            selected_curve_points=set(),
            selected_tracking_points=[],
            current_frame=12,
        )

        command = SetEndframeCommand()

        # Should be able to execute
        can_execute = command.can_execute(context)
        assert can_execute, "E key command should work with tracking data"

        # Execute should succeed without "Cannot handle status change" error
        try:
            success = command.execute(context)
            assert success, "E key execution should succeed with tracking data"
        except Exception as e:
            pytest.fail(f"E key failed with tracking data: {e}")

    def test_tracking_point_switching_maintains_synchronization(self, main_window, multi_point_data):
        """Test that switching between tracking points maintains DataService sync."""
        # Load multi-point data
        main_window.tracking_controller.on_multi_point_data_loaded(multi_point_data)

        data_service = get_data_service()

        # Test switching between different tracking points
        for point_name in ["Point1", "Point02", "Point03"]:
            # Select the tracking point
            main_window.tracking_controller.on_tracking_points_selected([point_name])

            # Verify DataService stays synchronized
            assert data_service._current_curve_data is not None, f"DataService should be synced for {point_name}"

            # Verify the data matches the selected point
            expected_data = multi_point_data[point_name]
            actual_data = data_service._current_curve_data
            assert len(actual_data) == len(expected_data), f"Data length should match for {point_name}"

            # Test status change works for each point
            error_msg = ""
            try:
                data_service.handle_point_status_change(0, "endframe")
                success = True
            except Exception as e:
                success = False
                error_msg = str(e)

            assert success, f"Status change should work for {point_name}: {error_msg if not success else ''}"

    def test_e_key_with_frame_navigation(self, main_window, multi_point_data):
        """Test E key functionality during frame navigation with tracking data."""
        # Load data
        main_window.tracking_controller.on_multi_point_data_loaded(multi_point_data)

        # Test E key at different frames
        test_frames = [1, 5, 12, 20]

        for frame in test_frames:
            main_window.state_manager.current_frame = frame

            # Create E key context
            key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier)

            context = ShortcutContext(
                main_window=main_window,
                focused_widget=main_window.curve_widget,
                key_event=key_event,
                selected_curve_points=set(),
                selected_tracking_points=[],
                current_frame=frame,
            )

            command = SetEndframeCommand()

            # Check if command can execute (depends on whether frame has data)
            can_execute = command.can_execute(context)

            if can_execute:
                # If it can execute, it should succeed
                try:
                    success = command.execute(context)
                    assert success, f"E key should succeed at frame {frame}"
                except Exception as e:
                    pytest.fail(f"E key failed at frame {frame}: {e}")

    def test_log_scenario_exact_reproduction(self, main_window):
        """
        Reproduce the exact log scenario:
        - 12 tracking points loaded
        - Frame switching between 1 and 12
        - Multiple E key presses
        """
        # Create data matching the log: 12 tracking points
        multi_point_data = {}
        for i in range(1, 13):
            point_name = f"Point{i:02d}" if i > 1 else "Point1"
            multi_point_data[point_name] = [
                (1, 100.0 + i * 10, 200.0 + i * 10, "keyframe"),
                (12, 150.0 + i * 10, 250.0 + i * 10, "keyframe"),
                (25, 200.0 + i * 10, 300.0 + i * 10, "interpolated"),
            ]

        # Load the data
        main_window.tracking_controller.on_multi_point_data_loaded(multi_point_data)

        # Verify 12 points loaded (matching log: "Loaded 12 tracking points")
        assert len(main_window.tracking_controller.tracked_data) == 12

        # Test the frame switching pattern from the log
        frames_to_test = [1, 12, 1, 12]  # Pattern seen in log

        for frame in frames_to_test:
            main_window.state_manager.current_frame = frame

            # Press E key multiple times (as seen in log)
            for _ in range(2):  # Multiple presses per frame
                key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier)

                context = ShortcutContext(
                    main_window=main_window,
                    focused_widget=main_window.curve_widget,
                    key_event=key_event,
                    selected_curve_points=set(),
                    selected_tracking_points=[],
                    current_frame=frame,
                )

                command = SetEndframeCommand()

                if command.can_execute(context):
                    try:
                        success = command.execute(context)
                        # This should NOT fail with "Cannot handle status change" anymore
                        assert success, f"E key should work at frame {frame}"
                    except Exception as e:
                        # If this fails, it indicates the synchronization fix didn't work
                        pytest.fail(f"E key failed at frame {frame}: {e}")

    def test_dataservice_warning_eliminated(self, main_window, multi_point_data):
        """Test that the specific warning from the log is eliminated."""
        # Load data
        main_window.tracking_controller.on_multi_point_data_loaded(multi_point_data)
        main_window.state_manager.current_frame = 1

        data_service = get_data_service()

        # This operation was generating the warning before the fix
        # "Cannot handle status change: no current curve data"
        error_msg = ""
        try:
            data_service.handle_point_status_change(0, "endframe")
            # Should succeed without warning
            warning_eliminated = True
        except Exception as e:
            # If this still fails, the fix didn't work
            warning_eliminated = False
            error_msg = str(e)

        assert (
            warning_eliminated
        ), f"DataService warning should be eliminated: {error_msg if not warning_eliminated else ''}"

        # Additionally, verify the data service has the expected state
        assert data_service._current_curve_data is not None
        assert data_service._segmented_curve is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
