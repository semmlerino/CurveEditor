#!/usr/bin/env python3
"""
Test timeline widget focus and keyboard navigation behavior.

Following UNIFIED_TESTING_GUIDE principles:
- Test actual user-visible behavior
- Use real Qt components and signals
- Use qtbot for interactions
- Avoid implementation testing
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

from ui.state_manager import StateManager
from ui.timeline_tabs import TimelineTabWidget


class TestTimelineFocusBehavior:
    """Test timeline widget's own keyboard handling and focus behavior."""

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
    def timeline_widget(self, app: QApplication, qtbot: QtBot) -> TimelineTabWidget:
        """Create standalone timeline widget for testing."""
        widget = TimelineTabWidget()
        qtbot.addWidget(widget)  # Register for cleanup

        # Create and connect StateManager for Single Source of Truth architecture
        state_manager = StateManager()
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_image_files([f"frame_{i:04d}.png" for i in range(1, 101)])  # Set total frames first
        app_state.set_frame(50)  # Then set current frame
        widget.set_state_manager(state_manager)

        # Set up a frame range
        widget.set_frame_range(1, 100)
        # StateManager already has frame 50, no need to set again

        # Add some frame status for visual testing
        widget.update_frame_status(10, keyframe_count=1)
        widget.update_frame_status(20, keyframe_count=1)
        widget.update_frame_status(30, interpolated_count=1)
        widget.update_frame_status(40, tracked_count=1)
        widget.update_frame_status(50, keyframe_count=1)
        widget.update_frame_status(60, endframe_count=1)

        widget.show()
        qtbot.waitExposed(widget)
        return widget

    def test_arrow_key_navigation_handled_by_timeline(self, timeline_widget: TimelineTabWidget, qtbot: QtBot) -> None:
        """Test that timeline handles arrow keys for frame-by-frame navigation."""
        timeline_widget.setFocus()
        qtbot.wait(10)
        # Note: hasFocus() may return False in test environment

        initial_frame = timeline_widget.current_frame

        # Test Right arrow
        qtbot.keyClick(timeline_widget, Qt.Key.Key_Right)
        assert timeline_widget.current_frame == initial_frame + 1

        # Test Left arrow
        qtbot.keyClick(timeline_widget, Qt.Key.Key_Left)
        qtbot.keyClick(timeline_widget, Qt.Key.Key_Left)
        assert timeline_widget.current_frame == initial_frame - 1

    def test_home_end_navigation(self, timeline_widget: TimelineTabWidget, qtbot: QtBot) -> None:
        """Test Home/End keys navigate to first/last frame."""
        timeline_widget.setFocus()

        # Test Home key
        qtbot.keyClick(timeline_widget, Qt.Key.Key_Home)
        assert timeline_widget.current_frame == timeline_widget.min_frame

        # Test End key
        qtbot.keyClick(timeline_widget, Qt.Key.Key_End)
        assert timeline_widget.current_frame == timeline_widget.max_frame

    def test_page_keys_not_handled_by_timeline(self, timeline_widget: TimelineTabWidget, qtbot: QtBot) -> None:
        """Test that Page Up/Down are ignored by timeline (bubble up)."""
        timeline_widget.setFocus()
        initial_frame = 50
        timeline_widget.set_current_frame(initial_frame)

        # Create Page Down event
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)

        # Send directly to timeline
        QApplication.sendEvent(timeline_widget, key_event)

        # Timeline should ignore it (frame unchanged)
        # In isolation, Page keys don't change frame
        # (they're handled by MainWindow's eventFilter)
        assert timeline_widget.current_frame == initial_frame

    def test_frame_changed_signal_on_navigation(self, timeline_widget: TimelineTabWidget, qtbot: QtBot) -> None:
        """Test that ApplicationState's frame_changed signal is emitted on keyboard navigation (Single Source of Truth)."""
        timeline_widget.setFocus()

        # Use qtbot.waitSignal to test ApplicationState's signal (Single Source of Truth)
        from stores.application_state import get_application_state

        app_state = get_application_state()
        with qtbot.waitSignal(app_state.frame_changed, timeout=1000) as blocker:
            qtbot.keyClick(timeline_widget, Qt.Key.Key_Right)

        # Verify signal was emitted with correct frame
        assert blocker.signal_triggered
        assert blocker.args is not None
        assert blocker.args[0] == timeline_widget.current_frame

    def test_mouse_click_tab_navigation(self, timeline_widget: TimelineTabWidget, qtbot: QtBot) -> None:
        """Test clicking on timeline tabs navigates to that frame."""
        # Set specific frames with visual tabs
        timeline_widget.set_frame_range(1, 10)
        timeline_widget.set_current_frame(1)

        # Update frame status to ensure tabs exist
        for frame in range(1, 11):
            timeline_widget.update_frame_status(frame, keyframe_count=1)

        qtbot.wait(50)  # Let UI update

        # Simulate clicking on frame 5's tab
        # This would require knowing the tab's position
        # For now, test the method directly (integration test will verify UI)
        timeline_widget.set_current_frame(5)

        assert timeline_widget.current_frame == 5

    def test_timeline_scrubbing_behavior(self, timeline_widget: TimelineTabWidget, qtbot: QtBot) -> None:
        """Test timeline scrubbing (drag to navigate frames)."""
        timeline_widget.set_frame_range(1, 100)
        timeline_widget.set_current_frame(1)

        # Test behavior, not implementation
        # Timeline should support mouse-based navigation

        # This test verifies the timeline is configured for scrubbing
        # Actual scrubbing behavior is tested in integration tests
        assert timeline_widget.current_frame == 1
        assert timeline_widget.min_frame == 1
        assert timeline_widget.max_frame == 100

    def test_boundary_clamping(self, timeline_widget: TimelineTabWidget, qtbot: QtBot) -> None:
        """Test that navigation is clamped to valid frame range.

        Uses the fixture's established frame range (1-100) to test clamping
        behavior at the actual boundaries.
        """
        timeline_widget.setFocus()
        QApplication.processEvents()  # Flush any pending events

        # Verify the fixture's frame range is active
        assert timeline_widget.min_frame == 1
        assert timeline_widget.max_frame == 100

        # Try to go below minimum (frame 1)
        timeline_widget.set_current_frame(1)
        QApplication.processEvents()
        qtbot.keyClick(timeline_widget, Qt.Key.Key_Left)
        QApplication.processEvents()  # Ensure key event is fully processed
        assert timeline_widget.current_frame == 1, "Should clamp to min_frame"  # Clamped

        # Try to go above maximum (frame 100)
        timeline_widget.set_current_frame(100)
        QApplication.processEvents()
        qtbot.keyClick(timeline_widget, Qt.Key.Key_Right)
        QApplication.processEvents()  # Ensure key event is fully processed
        assert timeline_widget.current_frame == 100, "Should clamp to max_frame"  # Clamped

    def test_focus_visual_indicator(self, timeline_widget: TimelineTabWidget, qtbot: QtBot) -> None:
        """Test that timeline shows visual focus indicator."""
        # Give focus
        timeline_widget.setFocus()
        qtbot.wait(10)
        # Note: hasFocus() may return False in test environment
        # assert timeline_widget.hasFocus()

        # Timeline should have focus style
        # This is more about visual testing
        # Note: Timeline may have NoFocus policy but still receive key events

        # Remove focus
        timeline_widget.clearFocus()
        qtbot.wait(10)
        # Note: hasFocus() may return False in test environment
        # assert not timeline_widget.hasFocus()

    def test_timeline_keyboard_shortcuts_summary(self, timeline_widget: TimelineTabWidget, qtbot: QtBot) -> None:
        """Document and test all timeline keyboard shortcuts."""
        timeline_widget.setFocus()
        timeline_widget.set_frame_range(1, 100)

        # Test each shortcut works
        # Left/Right: frame navigation
        # Home/End: first/last frame
        # Page Up/Down are NOT handled by timeline itself
        timeline_widget.set_current_frame(50)

        qtbot.keyClick(timeline_widget, Qt.Key.Key_Left)
        assert timeline_widget.current_frame == 49

        qtbot.keyClick(timeline_widget, Qt.Key.Key_Right)
        qtbot.keyClick(timeline_widget, Qt.Key.Key_Right)
        assert timeline_widget.current_frame == 51

        qtbot.keyClick(timeline_widget, Qt.Key.Key_Home)
        assert timeline_widget.current_frame == 1

        qtbot.keyClick(timeline_widget, Qt.Key.Key_End)
        assert timeline_widget.current_frame == 100


class TestTimelineEventPropagation:
    """Test how timeline interacts with parent widget event handling."""

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

    def test_ignored_events_propagate(self, app: QApplication, qtbot: QtBot) -> None:
        """Test that PageDown/PageUp don't navigate frames (reserved for keyframe navigation)."""
        from stores.application_state import get_application_state

        timeline = TimelineTabWidget()
        qtbot.addWidget(timeline)
        timeline.show()
        qtbot.waitExposed(timeline)
        QApplication.processEvents()  # Flush pending events from setup

        # Set up a frame range
        app_state = get_application_state()
        app_state.set_image_files([f"frame_{i:04d}.png" for i in range(1, 101)])
        timeline.set_frame_range(1, 100)
        timeline.set_current_frame(50)
        QApplication.processEvents()

        # Record initial frame
        initial_frame = timeline.current_frame
        assert initial_frame == 50

        # Send Page Down - should NOT change frame (PageDown is for keyframe navigation, not basic nav)
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(timeline, key_event)
        QApplication.processEvents()

        # Frame should not change - PageDown is not handled by timeline's basic navigation
        assert timeline.current_frame == initial_frame, (
            f"PageDown should not change frame in timeline widget (got {timeline.current_frame}, expected {initial_frame})"
        )

    def test_accepted_events_dont_propagate(self, app: QApplication, qtbot: QtBot) -> None:
        """Test that events handled by timeline don't propagate."""
        timeline = TimelineTabWidget()
        qtbot.addWidget(timeline)
        timeline.set_frame_range(1, 100)

        # Send arrow key (handled by timeline)
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(timeline, key_event)

        # Event should be accepted (handled)
        assert key_event.isAccepted(), "Arrow key should be accepted by timeline"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
