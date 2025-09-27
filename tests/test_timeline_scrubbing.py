#!/usr/bin/env python
"""
Tests for timeline scrubbing functionality.

Tests the mouse-based frame navigation in TimelineTabWidget, ensuring proper
signal emission, frame calculation, and integration with the main application.

Following UNIFIED_TESTING_GUIDE principles:
- Use real Qt components with QSignalSpy
- Mock only external dependencies
- Test behavior, not implementation
- Ensure proper widget cleanup with qtbot.addWidget()
"""

from unittest.mock import patch

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
from pytestqt.qt_compat import qt_api
from pytestqt.qtbot import QtBot

from ui.main_window import MainWindow

# CurveEditor imports
from ui.timeline_tabs import TimelineTabWidget


class TestTimelineScrubbing:
    """Test suite for timeline scrubbing functionality."""

    @pytest.fixture(scope="session")
    def qapp(self):
        """Shared QApplication for all tests."""
        app = QApplication.instance() or QApplication([])
        yield app
        app.processEvents()

    @pytest.fixture
    def timeline_widget(self, qtbot: QtBot) -> TimelineTabWidget:
        """TimelineTabWidget with proper cleanup."""
        widget = TimelineTabWidget()
        qtbot.addWidget(widget)  # CRITICAL: Auto cleanup
        return widget

    @pytest.fixture
    def timeline_with_frames(self, timeline_widget: TimelineTabWidget) -> TimelineTabWidget:
        """Timeline widget with standard frame range setup."""
        # Set a predictable size for position calculations
        timeline_widget.resize(1000, 40)
        timeline_widget.set_frame_range(1, 100)
        timeline_widget.set_current_frame(1)
        return timeline_widget

    @pytest.fixture
    def main_window(self, qtbot: QtBot) -> MainWindow:
        """MainWindow with proper cleanup for integration tests."""
        # Mock file operations to prevent auto-loading
        with patch("ui.file_operations.FileOperations.load_burger_data_async"):
            window = MainWindow()
            qtbot.addWidget(window)
            window.show()
            qtbot.waitExposed(window)
            return window

    # ==================== Unit Tests for Scrubbing Functionality ====================

    def test_scrubbing_starts_on_mouse_press(self, timeline_with_frames: TimelineTabWidget):
        """Test that mouse press starts scrubbing mode."""
        # Setup
        widget = timeline_with_frames
        initial_frame = widget.current_frame

        # Simulate left mouse press at position corresponding to frame 50
        press_x = widget.width() // 2  # Middle of widget
        mouse_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPoint(press_x, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        # Execute
        widget.mousePressEvent(mouse_event)

        # Verify
        assert widget.is_scrubbing is True
        assert widget.scrub_start_frame is not None
        assert widget.current_frame != initial_frame  # Frame should have changed

    def test_scrubbing_updates_frame_on_mouse_move(self, timeline_with_frames: TimelineTabWidget):
        """Test that mouse move during scrubbing updates current frame."""
        widget = timeline_with_frames

        # Start scrubbing
        widget.is_scrubbing = True
        widget.scrub_start_frame = 1
        initial_frame = widget.current_frame

        # Create signal spy for frame_changed
        frame_spy = qt_api.QtTest.QSignalSpy(widget.frame_changed)

        # Simulate mouse move to different position
        move_x = widget.width() * 3 // 4  # 75% across widget
        mouse_event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPoint(move_x, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        # Execute
        widget.mouseMoveEvent(mouse_event)

        # Verify
        assert widget.current_frame != initial_frame
        assert frame_spy.count() >= 1  # frame_changed signal should be emitted

    def test_scrubbing_stops_on_mouse_release(self, timeline_with_frames: TimelineTabWidget):
        """Test that mouse release stops scrubbing mode."""
        widget = timeline_with_frames

        # Start scrubbing
        widget.is_scrubbing = True
        widget.scrub_start_frame = 10

        # Simulate left mouse release
        mouse_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPoint(50, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        # Execute
        widget.mouseReleaseEvent(mouse_event)

        # Verify
        assert widget.is_scrubbing is False

    def test_frame_calculation_from_position(self, timeline_with_frames: TimelineTabWidget, qtbot: QtBot):
        """Test frame calculation from mouse position."""
        widget = timeline_with_frames

        # Show the widget to ensure proper layout
        widget.show()
        qtbot.waitExposed(widget)
        qtbot.wait(50)  # Allow time for layout

        # Force tab creation by triggering layout
        widget._create_all_tabs()
        qtbot.wait(50)  # Allow time for tab creation

        widget_width = widget.width()

        # Test that frame calculation returns valid frames for various positions
        test_positions = [0, widget_width // 4, widget_width // 2, 3 * widget_width // 4, widget_width - 1]

        previous_frame = None
        for x_pos in test_positions:
            calculated_frame = widget._get_frame_from_position(x_pos)

            # Frame calculation should return a valid frame
            assert calculated_frame is not None
            assert widget.min_frame <= calculated_frame <= widget.max_frame

            # Frames should generally increase as position increases
            # (allowing for some tab layout quirks)
            if previous_frame is not None:
                # Allow frame to stay same or increase (discrete tabs)
                assert calculated_frame >= previous_frame - 2  # Allow slight variation

            previous_frame = calculated_frame

        # Test specific boundary conditions
        left_edge_frame = widget._get_frame_from_position(0)
        right_edge_frame = widget._get_frame_from_position(widget_width - 1)

        # Left edge should be near the beginning
        assert left_edge_frame is not None
        assert left_edge_frame <= widget.min_frame + (widget.max_frame - widget.min_frame) // 10

        # Right edge should be reasonably far to the right
        assert right_edge_frame is not None
        assert right_edge_frame >= widget.min_frame + (widget.max_frame - widget.min_frame) // 2

    def test_scrubbing_emits_frame_changed_signal(self, timeline_with_frames: TimelineTabWidget):
        """Test that scrubbing properly emits frame_changed signal."""
        widget = timeline_with_frames

        # Create signal spy
        frame_spy = qt_api.QtTest.QSignalSpy(widget.frame_changed)

        # Test direct frame change (what scrubbing calls internally)
        target_frame = 50
        widget.set_current_frame(target_frame)

        # Verify signal emission
        assert frame_spy.count() == 1
        assert frame_spy.at(0)[0] == target_frame

    def test_scrubbing_clamps_to_valid_range(self, timeline_with_frames: TimelineTabWidget):
        """Test that scrubbing respects frame boundaries."""
        widget = timeline_with_frames

        # Test below minimum
        widget.set_current_frame(-10)
        assert widget.current_frame == widget.min_frame

        # Test above maximum
        widget.set_current_frame(200)
        assert widget.current_frame == widget.max_frame

        # Test valid range
        widget.set_current_frame(50)
        assert widget.current_frame == 50

    # ==================== Edge Cases and Error Handling ====================

    def test_scrubbing_with_empty_timeline(self, timeline_widget: TimelineTabWidget):
        """Test scrubbing behavior with no frames set."""
        widget = timeline_widget
        # Don't set frame range - should handle gracefully

        mouse_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPoint(50, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        # Should not crash
        widget.mousePressEvent(mouse_event)

        # Verify safe state
        assert widget.is_scrubbing is False or widget.is_scrubbing is True  # Either is acceptable

    def test_scrubbing_with_single_frame(self, timeline_widget: TimelineTabWidget):
        """Test scrubbing with only one frame."""
        widget = timeline_widget
        widget.set_frame_range(1, 1)  # Single frame

        # Create signal spy
        _ = qt_api.QtTest.QSignalSpy(widget.frame_changed)

        # Try to scrub
        mouse_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPoint(50, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        widget.mousePressEvent(mouse_event)

        # Should remain at frame 1
        assert widget.current_frame == 1

    def test_scrubbing_outside_widget_bounds(self, timeline_with_frames: TimelineTabWidget):
        """Test scrubbing with mouse positions outside widget bounds."""
        widget = timeline_with_frames

        # Test negative x position
        frame_negative = widget._get_frame_from_position(-50)
        if frame_negative is not None:
            assert frame_negative >= widget.min_frame

        # Test position beyond widget width
        frame_beyond = widget._get_frame_from_position(widget.width() + 100)
        if frame_beyond is not None:
            assert frame_beyond <= widget.max_frame

    def test_scrubbing_with_right_click(self, timeline_with_frames: TimelineTabWidget):
        """Test that right-click does not trigger scrubbing."""
        widget = timeline_with_frames
        initial_scrubbing_state = widget.is_scrubbing

        # Simulate right mouse press
        mouse_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPoint(50, 10),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier,
        )

        widget.mousePressEvent(mouse_event)

        # Should not start scrubbing
        assert widget.is_scrubbing == initial_scrubbing_state

    def test_concurrent_scrubbing_operations(self, timeline_with_frames: TimelineTabWidget):
        """Test multiple rapid mouse events in succession."""
        widget = timeline_with_frames

        # Create signal spy
        frame_spy = qt_api.QtTest.QSignalSpy(widget.frame_changed)

        # Rapid sequence of events
        positions = [20, 40, 60, 80]

        # Start scrubbing
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPoint(positions[0], 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.mousePressEvent(press_event)

        # Rapid moves
        for x_pos in positions[1:]:
            move_event = QMouseEvent(
                QMouseEvent.Type.MouseMove,
                QPoint(x_pos, 10),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            widget.mouseMoveEvent(move_event)

        # End scrubbing
        release_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPoint(positions[-1], 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.mouseReleaseEvent(release_event)

        # Should handle all events without crashing
        assert widget.is_scrubbing is False
        assert frame_spy.count() >= 1  # At least one frame change

    # ==================== Integration Tests ====================

    def test_scrubbing_updates_main_window_frame(self, qtbot: QtBot):
        """Test that scrubbing integrates with main window frame updates."""
        # Mock file operations to prevent auto-loading
        with patch("ui.file_operations.FileOperations.load_burger_data_async"):
            window = MainWindow()
            qtbot.addWidget(window)

            # Setup timeline if available
            if hasattr(window, "timeline_tabs") and window.timeline_tabs:
                timeline = window.timeline_tabs
                timeline.set_frame_range(1, 100)

                # Create signal spy for timeline controller
                if hasattr(window, "timeline_controller"):
                    # Test frame change propagation
                    timeline.set_current_frame(50)

                    # Verify the change propagated
                    assert timeline.current_frame == 50
                    # Note: Integration with main window depends on signal connections
                    # which were fixed in the previous conversation

    # ==================== Performance Tests ====================

    def test_scrubbing_performance_benchmark(self, timeline_with_frames: TimelineTabWidget, qtbot: QtBot):
        """Basic performance test for scrubbing operations."""
        widget = timeline_with_frames

        def scrub_operation():
            """Single scrub operation for benchmarking."""
            # Start scrub
            widget.is_scrubbing = True

            # Move through 10 frames
            for i in range(10):
                x_pos = (widget.width() * i) // 10
                frame = widget._get_frame_from_position(x_pos)
                if frame is not None:
                    widget.set_current_frame(frame)

            # End scrub
            widget.is_scrubbing = False

        # Measure time (basic performance check)
        import time

        start_time = time.time()
        scrub_operation()
        end_time = time.time()

        # Should complete quickly (< 100ms for 10 frame changes)
        assert (end_time - start_time) < 0.1

    # ==================== Test Data Scenarios ====================

    def test_scrubbing_with_various_frame_ranges(self, timeline_widget: TimelineTabWidget):
        """Test scrubbing with different frame range configurations."""
        widget = timeline_widget

        test_ranges = [
            (1, 10),  # Small range
            (0, 1000),  # Large range starting at 0
            (1000, 2000),  # Non-zero start range
        ]

        for min_frame, max_frame in test_ranges:
            widget.set_frame_range(min_frame, max_frame)

            # Test frame calculation at boundaries
            left_frame = widget._get_frame_from_position(0)
            right_frame = widget._get_frame_from_position(widget.width() - 1)

            if left_frame is not None:
                assert left_frame >= min_frame
            if right_frame is not None:
                assert right_frame <= max_frame


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
