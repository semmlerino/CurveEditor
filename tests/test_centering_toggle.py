"""Test suite for the centering toggle feature.

Following UNIFIED_TESTING_GUIDE principles:
- Test behavior, not implementation
- Use real components where possible
- Mock only at system boundaries
"""

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy

from core.models import CurvePoint
from core.type_aliases import CurveDataList
from ui.curve_view_widget import CurveViewWidget


class TestCenteringToggle:
    """Unit tests for centering mode toggle functionality."""

    def test_initial_state(self, qtbot):
        """Test that centering mode is OFF initially."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        assert not widget.centering_mode

    def test_toggle_with_c_key(self, qtbot):
        """Test that C key toggles centering mode through global shortcut system."""
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtWidgets import QApplication

        from ui.main_window import MainWindow

        # Create a full MainWindow with global shortcuts initialized
        window = MainWindow()
        qtbot.addWidget(window)

        widget = window.curve_widget
        if widget is None:
            import pytest

            pytest.skip("CurveViewWidget not available in MainWindow")

        # Add some test data and selection so centering can work
        test_data: CurveDataList = [
            (1, 100.0, 100.0),
            (2, 200.0, 200.0),
            (3, 300.0, 300.0),
        ]
        widget.set_curve_data(test_data)
        widget._select_point(1, add_to_selection=False)  # Select a point for centering

        # Initial state
        assert not widget.centering_mode

        # Create key event and send through application (global shortcut system)
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(widget, key_event)
        qtbot.wait(10)  # Allow event processing

        # Should toggle centering mode ON
        assert widget.centering_mode

        # Press C again to disable
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_C, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(widget, key_event)
        qtbot.wait(10)  # Allow event processing

        # Should toggle centering mode OFF
        assert not widget.centering_mode

    def test_centering_on_frame_change_when_enabled(self, qtbot):
        """Test that view centers on frame when mode is enabled."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Add test data
        points = [
            CurvePoint(1, 100.0, 200.0),
            CurvePoint(2, 150.0, 250.0),
            CurvePoint(3, 200.0, 300.0),
        ]
        widget.set_curve_data([p.to_tuple3() for p in points])

        # Enable centering mode
        widget.centering_mode = True

        # Store initial pan offset
        initial_offset_x = widget.pan_offset_x
        initial_offset_y = widget.pan_offset_y

        # Trigger frame change
        widget.on_frame_changed(2)

        # View should have changed (exact values depend on widget size)
        # Verify that the pan offset changed when centering occurred
        assert (
            widget.pan_offset_x != initial_offset_x or widget.pan_offset_y != initial_offset_y
        ), "Pan offset should change when centering on frame"
        assert widget.centering_mode  # Mode should still be enabled

    def test_no_centering_when_disabled(self, qtbot):
        """Test that view doesn't center when mode is disabled."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Add test data
        points = [
            CurvePoint(1, 100.0, 200.0),
            CurvePoint(2, 150.0, 250.0),
            CurvePoint(3, 200.0, 300.0),
        ]
        widget.set_curve_data([p.to_tuple3() for p in points])

        # Ensure centering mode is disabled
        widget.centering_mode = False

        # Store initial pan offset
        initial_offset_x = widget.pan_offset_x
        initial_offset_y = widget.pan_offset_y

        # Trigger frame change
        widget.on_frame_changed(2)

        # Pan offset should remain unchanged
        assert widget.pan_offset_x == initial_offset_x
        assert widget.pan_offset_y == initial_offset_y

    def test_centering_with_no_data(self, qtbot):
        """Test that centering handles empty data gracefully."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        widget.centering_mode = True

        # Should not crash with no data
        widget.on_frame_changed(1)

        assert widget.centering_mode  # Mode should still be enabled

    def test_centering_with_missing_frame(self, qtbot):
        """Test centering with frame not in data."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Add test data
        points = [
            CurvePoint(1, 100.0, 200.0),
            CurvePoint(3, 200.0, 300.0),  # No frame 2
        ]
        widget.set_curve_data([p.to_tuple3() for p in points])

        widget.centering_mode = True

        # Should handle missing frame gracefully
        widget.on_frame_changed(2)

        assert widget.centering_mode  # Mode should still be enabled


class TestCenteringIntegration:
    """Integration tests for centering with other features."""

    def test_centering_with_view_signals(self, qtbot):
        """Test that centering emits proper view change signals."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Add test data
        points = [
            CurvePoint(1, 100.0, 200.0),
            CurvePoint(2, 150.0, 250.0),
        ]
        widget.set_curve_data([p.to_tuple3() for p in points])

        # Set up signal spy
        spy = QSignalSpy(widget.view_changed)

        widget.centering_mode = True
        widget.on_frame_changed(2)

        # View change signal should be emitted when centering
        assert spy.count() > 0

    def test_centering_mode_persists_through_data_changes(self, qtbot):
        """Test that centering mode persists when curve data changes."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Enable centering mode
        widget.centering_mode = True

        # Change curve data
        points = [
            CurvePoint(1, 100.0, 200.0),
            CurvePoint(2, 150.0, 250.0),
        ]
        widget.set_curve_data([p.to_tuple3() for p in points])

        # Mode should still be enabled
        assert widget.centering_mode

        # Clear data
        widget.set_curve_data([])

        # Mode should still be enabled
        assert widget.centering_mode

    def test_centering_with_selection(self, qtbot):
        """Test that centering works independently of selection."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Add test data
        points = [
            CurvePoint(1, 100.0, 200.0),
            CurvePoint(2, 150.0, 250.0),
            CurvePoint(3, 200.0, 300.0),
        ]
        widget.set_curve_data([p.to_tuple3() for p in points])

        # Select first point
        widget._select_point(0)

        # Enable centering and move to different frame
        widget.centering_mode = True
        widget.on_frame_changed(3)

        # Selection should be maintained
        assert widget.selected_indices == {0}
        # Centering mode should still be active
        assert widget.centering_mode


class TestCenteringStability:
    """Regression tests for centering stability (no jumps when switching frames)."""

    def test_no_jump_when_centering_on_same_position(self, qtbot):
        """Test that centering on frames at the same position doesn't cause jumps."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Add test data with two frames at the SAME position
        points = [
            CurvePoint(1, 100.0, 200.0),
            CurvePoint(2, 100.0, 200.0),  # Same position as frame 1
        ]
        widget.set_curve_data([p.to_tuple3() for p in points])

        # Enable centering mode
        widget.centering_mode = True

        # Center on frame 1
        widget.on_frame_changed(1)
        offset_x_after_frame1 = widget.pan_offset_x
        offset_y_after_frame1 = widget.pan_offset_y

        # Switch to frame 2 (same position)
        widget.on_frame_changed(2)
        offset_x_after_frame2 = widget.pan_offset_x
        offset_y_after_frame2 = widget.pan_offset_y

        # Pan offset should be IDENTICAL (no jump) since positions are the same
        assert (
            abs(offset_x_after_frame2 - offset_x_after_frame1) < 0.01
        ), f"Pan offset X changed by {abs(offset_x_after_frame2 - offset_x_after_frame1):.4f}, expected no change"
        assert (
            abs(offset_y_after_frame2 - offset_y_after_frame1) < 0.01
        ), f"Pan offset Y changed by {abs(offset_y_after_frame2 - offset_y_after_frame1):.4f}, expected no change"

    def test_repeated_centering_on_same_frame_is_stable(self, qtbot):
        """Test that repeatedly centering on the same frame doesn't accumulate offset changes."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        points = [
            CurvePoint(1, 100.0, 200.0),
            CurvePoint(2, 150.0, 250.0),
        ]
        widget.set_curve_data([p.to_tuple3() for p in points])

        widget.centering_mode = True

        # Center on frame 1 multiple times
        widget.on_frame_changed(1)
        offset_x_first = widget.pan_offset_x
        offset_y_first = widget.pan_offset_y

        widget.on_frame_changed(1)
        offset_x_second = widget.pan_offset_x
        offset_y_second = widget.pan_offset_y

        widget.on_frame_changed(1)
        offset_x_third = widget.pan_offset_x
        offset_y_third = widget.pan_offset_y

        # All offsets should be identical (stable)
        assert abs(offset_x_second - offset_x_first) < 0.01, "Second centering on same frame changed offset"
        assert abs(offset_y_second - offset_y_first) < 0.01, "Second centering on same frame changed offset"
        assert abs(offset_x_third - offset_x_first) < 0.01, "Third centering on same frame changed offset"
        assert abs(offset_y_third - offset_y_first) < 0.01, "Third centering on same frame changed offset"

    def test_smooth_centering_between_nearby_frames(self, qtbot):
        """Test that centering smoothly tracks between frames with small position changes."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Frames with small incremental position changes
        points = [
            CurvePoint(1, 100.0, 200.0),
            CurvePoint(2, 101.0, 201.0),  # +1 pixel in each direction
            CurvePoint(3, 102.0, 202.0),  # +1 pixel in each direction
        ]
        widget.set_curve_data([p.to_tuple3() for p in points])

        widget.centering_mode = True

        # Center on each frame and track offset changes
        widget.on_frame_changed(1)
        offset_x_1 = widget.pan_offset_x
        offset_y_1 = widget.pan_offset_y

        widget.on_frame_changed(2)
        offset_x_2 = widget.pan_offset_x
        offset_y_2 = widget.pan_offset_y

        widget.on_frame_changed(3)
        offset_x_3 = widget.pan_offset_x
        offset_y_3 = widget.pan_offset_y

        # Calculate deltas
        delta_x_1to2 = offset_x_2 - offset_x_1
        delta_y_1to2 = offset_y_2 - offset_y_1
        delta_x_2to3 = offset_x_3 - offset_x_2
        delta_y_2to3 = offset_y_3 - offset_y_2

        # Deltas should be consistent (smooth tracking)
        # Since data points move by 1 pixel each time, pan offset changes should be similar
        assert abs(delta_x_1to2 - delta_x_2to3) < 0.5, "Pan offset changes should be consistent for uniform motion"
        assert abs(delta_y_1to2 - delta_y_2to3) < 0.5, "Pan offset changes should be consistent for uniform motion"

    def test_no_accumulation_when_switching_back_and_forth(self, qtbot):
        """Test that switching between two frames doesn't accumulate drift."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        points = [
            CurvePoint(1, 100.0, 200.0),
            CurvePoint(2, 150.0, 250.0),
        ]
        widget.set_curve_data([p.to_tuple3() for p in points])

        widget.centering_mode = True

        # Record offsets when centering on frame 1
        widget.on_frame_changed(1)
        frame1_offset_x_initial = widget.pan_offset_x
        frame1_offset_y_initial = widget.pan_offset_y

        # Switch to frame 2 and back to frame 1 multiple times
        for _ in range(5):
            widget.on_frame_changed(2)
            widget.on_frame_changed(1)

        frame1_offset_x_final = widget.pan_offset_x
        frame1_offset_y_final = widget.pan_offset_y

        # After switching back and forth, returning to frame 1 should give same offset
        assert (
            abs(frame1_offset_x_final - frame1_offset_x_initial) < 0.01
        ), "Switching back and forth accumulated drift in X offset"
        assert (
            abs(frame1_offset_y_final - frame1_offset_y_initial) < 0.01
        ), "Switching back and forth accumulated drift in Y offset"

    def test_production_conditions_with_background_and_large_widget(self, qtbot):
        """Test centering stability with production-realistic conditions.

        Production conditions that might expose bugs not caught by simple tests:
        - Realistic widget dimensions (1280x720 instead of minimal test size)
        - Background image loaded (affects center_offset calculation)
        - scale_to_image=True (default production setting)

        This test should reproduce the centering jump bug if it exists.
        """
        from PySide6.QtCore import Qt as QtCore
        from PySide6.QtGui import QImage, QPixmap

        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Set realistic production widget size
        widget.setFixedSize(1280, 720)

        # Force Qt to process geometry changes
        widget.show()
        qtbot.waitExposed(widget)

        # Create and load a background image (1280x720 to match widget)
        image = QImage(1280, 720, QImage.Format.Format_RGB888)
        image.fill(QtCore.GlobalColor.gray)
        pixmap = QPixmap.fromImage(image)
        widget.set_background_image(pixmap)

        # Ensure scale_to_image is enabled (production default)
        widget.scale_to_image = True

        # Add test data at same position
        points = [
            CurvePoint(1, 640.0, 360.0),  # Center of 1280x720
            CurvePoint(2, 640.0, 360.0),  # Same position
        ]
        widget.set_curve_data([p.to_tuple3() for p in points])

        widget.centering_mode = True

        # Center on frame 1
        widget.on_frame_changed(1)
        qtbot.wait(50)  # Allow rendering to complete
        offset_x_frame1 = widget.pan_offset_x
        offset_y_frame1 = widget.pan_offset_y

        # Switch to frame 2 (same position - should have identical offset)
        widget.on_frame_changed(2)
        qtbot.wait(50)
        offset_x_frame2 = widget.pan_offset_x
        offset_y_frame2 = widget.pan_offset_y

        # Switch back to frame 1
        widget.on_frame_changed(1)
        qtbot.wait(50)
        offset_x_frame1_return = widget.pan_offset_x
        offset_y_frame1_return = widget.pan_offset_y

        # Offsets should be IDENTICAL since positions are the same
        assert (
            abs(offset_x_frame2 - offset_x_frame1) < 0.01
        ), f"Pan offset X jumped by {abs(offset_x_frame2 - offset_x_frame1):.4f} when switching to same position"
        assert (
            abs(offset_y_frame2 - offset_y_frame1) < 0.01
        ), f"Pan offset Y jumped by {abs(offset_y_frame2 - offset_y_frame1):.4f} when switching to same position"

        # Returning to frame 1 should give identical offset
        assert (
            abs(offset_x_frame1_return - offset_x_frame1) < 0.01
        ), f"Pan offset X drifted by {abs(offset_x_frame1_return - offset_x_frame1):.4f} when returning to frame 1"
        assert (
            abs(offset_y_frame1_return - offset_y_frame1) < 0.01
        ), f"Pan offset Y drifted by {abs(offset_y_frame1_return - offset_y_frame1):.4f} when returning to frame 1"

    def test_production_conditions_switching_different_positions(self, qtbot):
        """Test for unexpected jumps when switching between frames at different positions.

        The user reports "switching to another frame causes a slight jump". This test
        checks if pan_offset changes are consistent with expected position changes,
        or if there are unexpected additional jumps/drift.
        """
        from PySide6.QtCore import Qt as QtCore
        from PySide6.QtGui import QImage, QPixmap

        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Production-realistic setup
        widget.setFixedSize(1280, 720)
        widget.show()
        qtbot.waitExposed(widget)

        # Load background image
        image = QImage(1280, 720, QImage.Format.Format_RGB888)
        image.fill(QtCore.GlobalColor.gray)
        pixmap = QPixmap.fromImage(image)
        widget.set_background_image(pixmap)
        widget.scale_to_image = True

        # Create points with small movements (typical animation scenario)
        points = [
            CurvePoint(1, 640.0, 360.0),
            CurvePoint(2, 645.0, 365.0),  # Move 5 pixels in each direction
            CurvePoint(3, 650.0, 370.0),  # Another 5 pixels
        ]
        widget.set_curve_data([p.to_tuple3() for p in points])
        widget.centering_mode = True

        # Record offsets at each frame multiple times
        measurements = []
        for frame in [1, 2, 3, 2, 1, 2, 1]:  # Switch back and forth
            widget.on_frame_changed(frame)
            qtbot.wait(50)
            measurements.append((frame, widget.pan_offset_x, widget.pan_offset_y))

        # Extract measurements for each frame
        frame1_measurements = [(x, y) for f, x, y in measurements if f == 1]
        frame2_measurements = [(x, y) for f, x, y in measurements if f == 2]
        frame3_measurements = [(x, y) for f, x, y in measurements if f == 3]

        # Each frame should have consistent offsets across multiple visits
        for frame_num, frame_meas in [(1, frame1_measurements), (2, frame2_measurements), (3, frame3_measurements)]:
            if len(frame_meas) > 1:
                x_values = [x for x, y in frame_meas]
                y_values = [y for x, y in frame_meas]
                x_variance = max(x_values) - min(x_values)
                y_variance = max(y_values) - min(y_values)

                assert (
                    x_variance < 0.01
                ), f"Frame {frame_num} X offset varied by {x_variance:.4f} across visits (unstable/jumping)"
                assert (
                    y_variance < 0.01
                ), f"Frame {frame_num} Y offset varied by {y_variance:.4f} across visits (unstable/jumping)"
