"""Test suite for the centering toggle feature.

Following UNIFIED_TESTING_GUIDE principles:
- Test behavior, not implementation
- Use real components where possible
- Mock only at system boundaries
"""

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy

from core.models import CurvePoint
from ui.curve_view_widget import CurveViewWidget


class TestCenteringToggle:
    """Unit tests for centering mode toggle functionality."""

    def test_initial_state(self, qtbot):
        """Test that centering mode is OFF initially."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        assert not widget.centering_mode

    def test_toggle_with_c_key(self, qtbot):
        """Test that C key toggles centering mode."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Initial state
        assert not widget.centering_mode

        # Press C to enable
        qtbot.keyClick(widget, Qt.Key.Key_C)
        assert widget.centering_mode

        # Press C again to disable
        qtbot.keyClick(widget, Qt.Key.Key_C)
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
        widget.selected_indices = {0}

        # Enable centering and move to different frame
        widget.centering_mode = True
        widget.on_frame_changed(3)

        # Selection should be maintained
        assert widget.selected_indices == {0}
        # Centering mode should still be active
        assert widget.centering_mode
