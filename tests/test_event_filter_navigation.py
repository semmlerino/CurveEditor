#!/usr/bin/env python3
"""
Test eventFilter-based Page Up/Down navigation.

Following UNIFIED_TESTING_GUIDE principles:
- Test behavior, not implementation
- Use real components with real Qt signals
- Mock only external boundaries (not needed here)
- Use qtbot for proper Qt widget testing
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from core.type_aliases import CurveDataList
from ui.main_window import MainWindow


class TestEventFilterNavigation:
    """Test that Page Up/Down works via eventFilter regardless of widget focus."""

    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for widget tests."""
        existing_app = QApplication.instance()
        if existing_app is not None:
            # Type narrowing: ensure we have QApplication, not just QCoreApplication
            app = existing_app if isinstance(existing_app, QApplication) else QApplication([])
        else:
            app = QApplication([])
        return app

    @pytest.fixture
    def main_window_with_data(self, app: QApplication, qtbot: QtBot) -> MainWindow:
        """Create MainWindow with test curve data."""
        window = MainWindow()
        qtbot.addWidget(window)  # Register for cleanup

        # Load test data with keyframes
        test_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "keyframe"),
            (10, 200.0, 200.0, "keyframe"),
            (15, 250.0, 250.0, "keyframe"),
            (20, 300.0, 300.0, "keyframe"),
        ]

        # Use real components
        if window.curve_widget:
            window.curve_widget.set_curve_data(test_data)
        window.update_timeline_tabs(test_data)

        # Install event filter (mimics main.py)
        app.installEventFilter(window)

        # Show window and wait for it to be ready
        window.show()
        qtbot.waitExposed(window)
        qtbot.wait(50)  # Allow UI to update
        return window

    def test_page_down_via_eventfilter_with_timeline_focus(
        self, main_window_with_data: MainWindow, qtbot: QtBot
    ) -> None:
        """Test Page Down works through eventFilter when timeline has focus."""
        window = main_window_with_data

        # Give focus to timeline (simulates user clicking timeline)
        if window.timeline_tabs:
            window.timeline_tabs.setFocus()
            qtbot.wait(10)
            # Note: hasFocus() may return False in test environment
            # But the event should still work

        # Start at frame 1
        window.state_manager.current_frame = 1

        # Create Page Down key event
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)

        # Send event through application (will be caught by eventFilter)
        if window.timeline_tabs:
            QApplication.sendEvent(window.timeline_tabs, key_event)
        qtbot.wait(10)

        # Verify navigation happened (should be at frame 5)
        assert window.state_manager.current_frame == 5
        status_msg = window.statusBar().currentMessage().lower()
        assert "frame" in status_msg and "5" in status_msg

    def test_page_up_via_eventfilter_with_timeline_focus(self, main_window_with_data: MainWindow, qtbot: QtBot) -> None:
        """Test Page Up works through eventFilter when timeline has focus."""
        window = main_window_with_data

        # Give focus to timeline
        if window.timeline_tabs:
            window.timeline_tabs.setFocus()
            qtbot.wait(10)
            # Note: hasFocus() may return False in test environment

        # Start at frame 10
        window.state_manager.current_frame = 10

        # Create Page Up key event
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageUp, Qt.KeyboardModifier.NoModifier)

        # Send event through application
        assert window.timeline_tabs is not None
        QApplication.sendEvent(window.timeline_tabs, key_event)
        qtbot.wait(10)

        # Verify navigation happened (should be at frame 5)
        assert window.state_manager.current_frame == 5
        status_msg = window.statusBar().currentMessage().lower()
        assert "frame" in status_msg and "5" in status_msg

    def test_navigation_with_curve_widget_focus(self, main_window_with_data: MainWindow, qtbot: QtBot) -> None:
        """Test navigation still works when curve widget has focus."""
        window = main_window_with_data

        # Give focus to curve widget
        assert window.curve_widget is not None
        window.curve_widget.setFocus()
        qtbot.wait(10)
        # Note: hasFocus() may return False in test environment

        # Start at frame 5
        window.state_manager.current_frame = 5

        # Page Down
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(window.curve_widget, key_event)
        qtbot.wait(10)

        # Should navigate to frame 10
        assert window.state_manager.current_frame == 10

    def test_navigation_with_spinbox_focus(self, main_window_with_data: MainWindow, qtbot: QtBot) -> None:
        """Test navigation works when frame spinbox has focus."""
        window = main_window_with_data

        if not window.frame_spinbox:
            pytest.skip("Frame spinbox not available")

        # Give focus to frame spinbox
        window.frame_spinbox.setFocus()
        qtbot.wait(10)
        # Note: hasFocus() may return False in test environment

        # Start at frame 15
        window.state_manager.current_frame = 15

        # Page Up
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageUp, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(window.frame_spinbox, key_event)
        qtbot.wait(10)

        # Should navigate to frame 10
        assert window.state_manager.current_frame == 10

    def test_eventfilter_consumes_navigation_events(self, main_window_with_data: MainWindow, qtbot: QtBot) -> None:
        """Test that eventFilter properly consumes Page Up/Down events."""
        window = main_window_with_data

        # Track if event was consumed
        event_consumed = False

        # Create custom event handler to check if event reaches widget
        original_keypressevent = window.timeline_tabs.keyPressEvent if window.timeline_tabs else None

        def track_keypress(event):
            nonlocal event_consumed
            if event.key() in [Qt.Key.Key_PageUp, Qt.Key.Key_PageDown]:
                event_consumed = False  # Event reached widget (not consumed)
            if original_keypressevent:
                original_keypressevent(event)

        if window.timeline_tabs:
            window.timeline_tabs.keyPressEvent = track_keypress
            event_consumed = True  # Start assuming event will be consumed

            # Send Page Down
            key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(window.timeline_tabs, key_event)

            # Event should be consumed by eventFilter (not reach widget)
            assert event_consumed, "Event should be consumed by eventFilter"

    def test_navigation_at_boundaries_with_eventfilter(self, main_window_with_data: MainWindow, qtbot: QtBot) -> None:
        """Test boundary behavior works correctly through eventFilter."""
        window = main_window_with_data

        # Give focus to timeline
        if window.timeline_tabs:
            window.timeline_tabs.setFocus()

        # Start at first keyframe
        window.state_manager.current_frame = 1

        # Try Page Up (should show message, stay at frame 1)
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageUp, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(window.timeline_tabs or window, key_event)
        qtbot.wait(10)

        assert window.state_manager.current_frame == 1
        assert "first" in window.statusBar().currentMessage().lower()

        # Go to last keyframe
        window.state_manager.current_frame = 20

        # Try Page Down (should show message, stay at frame 20)
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(window.timeline_tabs or window, key_event)
        qtbot.wait(10)

        assert window.state_manager.current_frame == 20
        assert "last" in window.statusBar().currentMessage().lower()

    def test_mixed_navigation_frames(self, main_window_with_data: MainWindow, qtbot: QtBot) -> None:
        """Test navigation with mixed frame types (keyframes, endframes, startframes)."""
        # Load data with different frame types
        mixed_data = [
            (1, 100.0, 100.0, "keyframe"),  # Navigation point
            (2, 110.0, 110.0, "interpolated"),
            (3, 120.0, 120.0, "interpolated"),
            (5, 140.0, 140.0, "endframe"),  # Navigation point
            (6, 150.0, 150.0, "interpolated"),
            (10, 200.0, 200.0, "keyframe"),  # Navigation point
        ]

        assert main_window_with_data.curve_widget is not None
        main_window_with_data.curve_widget.set_curve_data(mixed_data)
        main_window_with_data.update_timeline_tabs(mixed_data)
        qtbot.wait(50)

        # Give focus to timeline
        if main_window_with_data.timeline_tabs:
            main_window_with_data.timeline_tabs.setFocus()

        # Start at frame 2 (interpolated)
        main_window_with_data.state_manager.current_frame = 2

        # Page Down should go to endframe at 5
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(main_window_with_data.timeline_tabs or main_window_with_data, key_event)
        qtbot.wait(10)

        assert main_window_with_data.state_manager.current_frame == 5

        # Page Down again should go to keyframe at 10
        QApplication.sendEvent(main_window_with_data.timeline_tabs or main_window_with_data, key_event)
        qtbot.wait(10)

        assert main_window_with_data.state_manager.current_frame == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
