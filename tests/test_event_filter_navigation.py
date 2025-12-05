#!/usr/bin/env python3
"""
Test eventFilter-based Page Up/Down navigation.

Following UNIFIED_TESTING_GUIDE principles:
- Test behavior, not implementation
- Use real components with real Qt signals
- Mock only external boundaries (not needed here)
- Use qtbot for proper Qt widget testing
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from core.type_aliases import CurveDataList
from stores.application_state import get_application_state
from tests.test_utils import process_qt_events, wait_for_frame
from ui.main_window import MainWindow

# Tests in this file require frame navigation
pytestmark = pytest.mark.usefixtures("with_minimal_frame_range")

# Phase 4 TODO: Migrate StateManager current_frame setters (7 occurrences)
# Test file uses setters for test setup - defer migration to Phase 4


class TestEventFilterNavigation:
    """Test that Page Up/Down works via eventFilter regardless of widget focus."""

    # Note: Tests use session-scoped qapp fixture from qt_fixtures.py
    # which ensures proper Qt cleanup via qt_cleanup fixture

    @pytest.fixture
    def main_window_with_data(self, qapp: QApplication, qtbot: QtBot) -> MainWindow:
        """Create MainWindow with test curve data."""
        # auto_load_data=False prevents background file loading during tests
        window = MainWindow(auto_load_data=False)

        def cleanup_event_filter(w):
            """Remove event filters before widget destruction."""
            app_instance = QApplication.instance()
            if app_instance and hasattr(w, "global_event_filter"):
                app_instance.removeEventFilter(w.global_event_filter)

        qtbot.addWidget(window, before_close_func=cleanup_event_filter)  # Register for cleanup

        # Load test data with keyframes
        test_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "keyframe"),
            (10, 200.0, 200.0, "keyframe"),
            (15, 250.0, 250.0, "keyframe"),
            (20, 300.0, 300.0, "keyframe"),
        ]

        # Show window and wait for it to be ready
        window.show()
        qtbot.waitExposed(window)

        # Set up active curve in application state
        state = get_application_state()
        test_curve_name = "TestCurve"
        state.set_curve_data(test_curve_name, test_data)
        state.set_active_curve(test_curve_name)

        # Set active_timeline_point to match active curve (required for Page Up/Down navigation)
        window.active_timeline_point = test_curve_name

        # Verify the setup
        assert state.active_curve == test_curve_name, f"Active curve not set: {state.active_curve}"
        assert state.get_curve_data(test_curve_name) == test_data, "Curve data not set correctly"

        # Update UI components to reflect the data
        window.update_timeline_tabs(test_data)

        # Trigger curve widget update
        if window.curve_widget is not None:
            window.curve_widget.update()

        process_qt_events()  # Allow UI to update
        return window

    def test_page_down_via_eventfilter_with_timeline_focus(
        self, main_window_with_data: MainWindow, qtbot: QtBot
    ) -> None:
        """Test Page Down works through eventFilter when timeline has focus."""
        window = main_window_with_data
        app = QApplication.instance()

        # Give focus to timeline (simulates user clicking timeline)
        if window.timeline_tabs:
            window.timeline_tabs.setFocus()
            process_qt_events()  # Let focus settle
            # Note: hasFocus() may return False in test environment
            # But the event should still work

        # Start at frame 1
        get_application_state().set_frame(1)

        # Create Page Down key event
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)

        # Post event to application event queue to trigger event filters
        if window.timeline_tabs and app:
            app.postEvent(window.timeline_tabs, key_event)
            app.processEvents()  # Process the event queue
        wait_for_frame(qtbot, expected_frame=5)

        # Verify navigation happened (should be at frame 5)
        assert get_application_state().current_frame == 5, \
            f"Expected frame 5, got {get_application_state().current_frame}"
        status_msg = window.statusBar().currentMessage().lower()
        assert "frame" in status_msg
        assert "5" in status_msg

    def test_page_up_via_eventfilter_with_timeline_focus(self, main_window_with_data: MainWindow, qtbot: QtBot) -> None:
        """Test Page Up works through eventFilter when timeline has focus."""
        window = main_window_with_data
        app = QApplication.instance()

        # Give focus to timeline
        if window.timeline_tabs:
            window.timeline_tabs.setFocus()
            process_qt_events()  # Let focus settle
            # Note: hasFocus() may return False in test environment

        # Start at frame 10
        get_application_state().set_frame(10)

        # Create Page Up key event
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageUp, Qt.KeyboardModifier.NoModifier)

        # Post event to application event queue to trigger event filters
        assert window.timeline_tabs is not None
        if app:
            app.postEvent(window.timeline_tabs, key_event)
            app.processEvents()  # Process the event queue
        wait_for_frame(qtbot, expected_frame=5)

        # Verify navigation happened (should be at frame 5)
        assert get_application_state().current_frame == 5, \
            f"Expected frame 5, got {get_application_state().current_frame}"
        status_msg = window.statusBar().currentMessage().lower()
        assert "frame" in status_msg
        assert "5" in status_msg

    def test_navigation_with_curve_widget_focus(self, main_window_with_data: MainWindow, qtbot: QtBot) -> None:
        """Test navigation still works when curve widget has focus."""
        window = main_window_with_data
        app = QApplication.instance()

        # Give focus to curve widget
        assert window.curve_widget is not None
        window.curve_widget.setFocus()
        process_qt_events()  # Let focus settle
        # Note: hasFocus() may return False in test environment

        # Start at frame 5
        get_application_state().set_frame(5)

        # Page Down
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        if app:
            app.postEvent(window.curve_widget, key_event)
            app.processEvents()  # Process the event queue
        wait_for_frame(qtbot, expected_frame=10)

        # Should navigate to frame 10
        assert get_application_state().current_frame == 10, \
            f"Expected frame 10, got {get_application_state().current_frame}"

    def test_navigation_with_spinbox_focus(self, main_window_with_data: MainWindow, qtbot: QtBot) -> None:
        """Test navigation works when frame spinbox has focus."""
        window = main_window_with_data
        app = QApplication.instance()

        if not window.frame_spinbox:
            pytest.skip("Frame spinbox not available")

        # Give focus to frame spinbox
        window.frame_spinbox.setFocus()
        process_qt_events()  # Let focus settle
        # Note: hasFocus() may return False in test environment

        # Start at frame 15
        get_application_state().set_frame(15)

        # Page Up
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageUp, Qt.KeyboardModifier.NoModifier)
        if app:
            app.postEvent(window.frame_spinbox, key_event)
            app.processEvents()  # Process the event queue
        wait_for_frame(qtbot, expected_frame=10)

        # Should navigate to frame 10
        assert get_application_state().current_frame == 10, \
            f"Expected frame 10, got {get_application_state().current_frame}"

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
        app = QApplication.instance()

        # Give focus to timeline
        if window.timeline_tabs:
            window.timeline_tabs.setFocus()
            process_qt_events()  # Let focus settle

        # Start at first keyframe
        get_application_state().set_frame(1)

        # Try Page Up (should show message, stay at frame 1)
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageUp, Qt.KeyboardModifier.NoModifier)
        target = window.timeline_tabs or window
        if app:
            app.postEvent(target, key_event)
            app.processEvents()  # Process the event queue
        process_qt_events()  # Allow status bar update

        assert get_application_state().current_frame == 1, \
            f"Expected frame 1 at boundary, got {get_application_state().current_frame}"
        assert "first" in window.statusBar().currentMessage().lower(), \
            f"Expected 'first' in status, got: {window.statusBar().currentMessage()}"

        # Go to last keyframe
        get_application_state().set_frame(20)

        # Try Page Down (should show message, stay at frame 20)
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        if app:
            app.postEvent(target, key_event)
            app.processEvents()  # Process the event queue
        process_qt_events()  # Allow status bar update

        assert get_application_state().current_frame == 20, \
            f"Expected frame 20 at boundary, got {get_application_state().current_frame}"
        assert "last" in window.statusBar().currentMessage().lower(), \
            f"Expected 'last' in status, got: {window.statusBar().currentMessage()}"

    def test_mixed_navigation_frames(self, main_window_with_data: MainWindow, qtbot: QtBot) -> None:
        """Test navigation with mixed frame types (keyframes, endframes, startframes)."""
        app = QApplication.instance()
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
        process_qt_events()  # Allow UI to update

        # Give focus to timeline
        if main_window_with_data.timeline_tabs:
            main_window_with_data.timeline_tabs.setFocus()
            process_qt_events()  # Let focus settle

        # Start at frame 2 (interpolated)
        get_application_state().set_frame(2)

        # Page Down should go to endframe at 5
        key_event1 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        target = main_window_with_data.timeline_tabs or main_window_with_data
        if app:
            app.postEvent(target, key_event1)
            app.processEvents()  # Process the event queue
        wait_for_frame(qtbot, expected_frame=5)

        assert get_application_state().current_frame == 5, \
            f"Expected frame 5 (endframe), got {get_application_state().current_frame}"

        # Page Down again should go to keyframe at 10
        key_event2 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        if app:
            app.postEvent(target, key_event2)
            app.processEvents()  # Process the event queue
        wait_for_frame(qtbot, expected_frame=10)

        assert get_application_state().current_frame == 10, \
            f"Expected frame 10 (keyframe), got {get_application_state().current_frame}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
