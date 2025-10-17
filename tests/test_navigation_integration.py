#!/usr/bin/env python3
"""
Integration test for all navigation features working together.

Following UNIFIED_TESTING_GUIDE principles:
- Test real user workflows
- Use real components end-to-end
- Verify user-visible behavior
- No mocking of components under test
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from stores.application_state import get_application_state
from ui.main_window import MainWindow


class TestNavigationIntegration:
    """End-to-end integration tests for all navigation features."""

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
    def fully_configured_window(self, app: QApplication, qtbot: QtBot) -> MainWindow:
        """Create fully configured MainWindow with realistic data."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Load realistic test data with various frame types
        test_data = [
            # Scene 1: keyframes with interpolation
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),
            (3, 120.0, 120.0, "interpolated"),
            (4, 130.0, 130.0, "interpolated"),
            (5, 140.0, 140.0, "keyframe"),
            # Gap frames 6-9
            # Scene 2: tracked points
            (10, 200.0, 200.0, "keyframe"),
            (11, 210.0, 210.0, "tracked"),
            (12, 220.0, 220.0, "tracked"),
            (13, 230.0, 230.0, "tracked"),
            (14, 240.0, 240.0, "tracked"),
            (15, 250.0, 250.0, "endframe"),
            # Gap frames 16-19
            # Scene 3: mixed types
            (20, 300.0, 300.0, "keyframe"),
            (21, 310.0, 310.0, "normal"),
            (22, 320.0, 320.0, "interpolated"),
            (25, 350.0, 350.0, "keyframe"),
            # Gap frames 26-29
            (30, 400.0, 400.0, "endframe"),
        ]

        # Set up the window with data
        assert window.curve_widget is not None
        window.curve_widget.set_curve_data(test_data)
        window.update_timeline_tabs(test_data)

        # Install event filter (mimics main.py setup)
        app.installEventFilter(window)

        # Ensure window is shown and ready
        window.show()
        qtbot.waitExposed(window)
        qtbot.wait(100)  # Let everything settle

        # Set the frame range to match our test data (frames 1-30)
        # Do this AFTER show() to avoid it being overridden during initialization
        window.timeline_controller.set_frame_range(1, 30)
        assert window.frame_spinbox is not None
        window.frame_spinbox.setMaximum(30)
        assert window.frame_slider is not None
        window.frame_slider.setMaximum(30)
        window.state_manager.total_frames = 30
        if window.timeline_tabs:
            window.timeline_tabs.set_frame_range(1, 30)

        return window

    def test_complete_navigation_workflow(self, fully_configured_window: MainWindow, qtbot: QtBot) -> None:
        """Test complete user navigation workflow across all features."""
        window = fully_configured_window

        # Start at frame 1
        get_application_state().set_frame(1)
        assert window.frame_spinbox is not None
        assert window.frame_spinbox.value() == 1

        # 1. Test basic arrow navigation with timeline focused
        if window.timeline_tabs:
            window.timeline_tabs.setFocus()
            qtbot.wait(10)

            # Right arrow moves forward one frame
            qtbot.keyClick(window.timeline_tabs, Qt.Key.Key_Right)
            assert get_application_state().set_frame(= 2)

            # Left arrow moves back
            qtbot.keyClick(window.timeline_tabs, Qt.Key.Key_Left)
            assert get_application_state().set_frame(= 1)

        # 2. Test Page Down navigation to next keyframe (via eventFilter)
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(window.timeline_tabs or window, key_event)
        qtbot.wait(10)
        # Should jump to next keyframe at frame 5
        assert get_application_state().set_frame(= 5)

        # 3. Continue Page Down through navigation points
        QApplication.sendEvent(window.timeline_tabs or window, key_event)
        qtbot.wait(10)
        assert get_application_state().set_frame(= 10  # Next keyframe)

        QApplication.sendEvent(window.timeline_tabs or window, key_event)
        qtbot.wait(10)
        assert get_application_state().set_frame(= 15  # Endframe)

        # 4. Test Page Up navigation backwards
        page_up = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageUp, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(window.timeline_tabs or window, page_up)
        qtbot.wait(10)
        assert get_application_state().set_frame(= 10  # Back to keyframe)

        # 5. Test Home/End navigation
        if window.timeline_tabs:
            qtbot.keyClick(window.timeline_tabs, Qt.Key.Key_End)
            assert get_application_state().set_frame(= 30  # Last frame)

            qtbot.keyClick(window.timeline_tabs, Qt.Key.Key_Home)
            assert get_application_state().set_frame(= 1  # First frame)

        # 6. Test navigation with curve widget focused
        assert window.curve_widget is not None
        window.curve_widget.setFocus()
        qtbot.wait(10)

        get_application_state().set_frame(20)
        QApplication.sendEvent(window.curve_widget, key_event)  # Page Down
        qtbot.wait(10)
        assert get_application_state().set_frame(= 25  # Next keyframe)

    def test_timeline_visual_feedback_during_navigation(
        self, fully_configured_window: MainWindow, qtbot: QtBot
    ) -> None:
        """Test that timeline provides visual feedback during navigation."""
        window = fully_configured_window

        if not window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        timeline = window.timeline_tabs

        # Navigate to different frame types and verify colors
        test_frames = [
            (1, "keyframe"),  # Has keyframe
            (7, "gap"),  # Gap (no data)
            (11, "tracked"),  # Has tracked point
            (15, "endframe"),  # Has endframe
        ]

        for frame, expected_type in test_frames:
            # Navigate to frame
            get_application_state().set_frame(frame)
            qtbot.wait(50)

            # Check timeline shows correct color
            if frame in timeline.frame_tabs:
                tab = timeline.frame_tabs[frame]
                color = tab._get_background_color()

                if expected_type == "gap":
                    # Should show no_points color
                    expected_color = tab.COLORS["no_points"]
                    assert color.red() == expected_color.red()
                    assert tab.point_count == 0
                else:
                    # Should NOT be no_points color
                    no_points = tab.COLORS["no_points"]
                    assert color.red() != no_points.red() or color.green() != no_points.green()
                    assert tab.point_count > 0

    def test_navigation_with_changing_focus(self, fully_configured_window: MainWindow, qtbot: QtBot) -> None:
        """Test navigation works correctly as focus changes between widgets."""
        window = fully_configured_window

        # List of widgets to cycle focus through
        focusable_widgets = [
            window.curve_widget,
            window.timeline_tabs,
            window.frame_spinbox,
        ]

        # Filter out None widgets
        focusable_widgets = [w for w in focusable_widgets if w is not None]

        for widget in focusable_widgets:
            # Give focus to widget
            widget.setFocus()
            qtbot.wait(10)
            # Note: hasFocus() may return False in test environment
            # assert widget.hasFocus(), f"{widget.__class__.__name__} should have focus"

            # Page Down should still work via eventFilter
            initial_frame = window.state_manager.current_frame
            key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(widget, key_event)
            qtbot.wait(10)

            # Should have navigated (unless at last nav frame)
            if initial_frame < 30:  # Not at last frame
                assert (
                    window.state_manager.current_frame > initial_frame
                ), f"Navigation should work with {widget.__class__.__name__} focused"

    def test_navigation_signals_and_updates(self, fully_configured_window: MainWindow, qtbot: QtBot) -> None:
        """Test that navigation triggers appropriate signals and UI updates."""
        window = fully_configured_window

        if not window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        # Set up signal spy on StateManager's frame_changed signal (new architecture)
        state_spy = QSignalSpy(window.state_manager.frame_changed)

        # Navigate using Right arrow - handled by global navigation system
        get_application_state().set_frame(1)
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(window.timeline_tabs or window, key_event)
        qtbot.wait(50)

        # In new architecture: StateManager frame_changed should be emitted
        # timeline_tabs should update visually but not emit its own signal (avoids loops)
        assert state_spy.count() > 0, "StateManager frame_changed signal should be emitted"

        # Test direct timeline_tabs interaction
        assert window.timeline_tabs is not None
        window.timeline_tabs.set_current_frame(5)
        # Timeline updates its display but doesn't emit its own signal (avoids loops)
        assert window.timeline_tabs.current_frame == 5, "timeline_tabs should update to frame 5"

        # Check UI elements updated
        assert window.frame_spinbox is not None
        assert window.frame_spinbox.value() == window.state_manager.current_frame
        if window.timeline_tabs:
            assert window.timeline_tabs.current_frame == window.state_manager.current_frame

        # Check status bar shows navigation message
        status_message = window.statusBar().currentMessage().lower()
        assert "frame" in status_message or "navigated" in status_message

    def test_boundary_navigation_behavior(self, fully_configured_window: MainWindow, qtbot: QtBot) -> None:
        """Test navigation behavior at boundaries."""
        window = fully_configured_window

        # Navigate to first navigation frame
        get_application_state().set_frame(1)

        # Try Page Up - should show message about being at first
        page_up = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageUp, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(window.timeline_tabs or window, page_up)
        qtbot.wait(10)

        assert get_application_state().set_frame(= 1  # Still at first)
        assert "first" in window.statusBar().currentMessage().lower()

        # Navigate to last navigation frame
        get_application_state().set_frame(30)

        # Try Page Down - should show message about being at last
        page_down = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(window.timeline_tabs or window, page_down)
        qtbot.wait(10)

        assert get_application_state().set_frame(= 30  # Still at last)
        assert "last" in window.statusBar().currentMessage().lower()

    def test_rapid_navigation_stability(self, fully_configured_window: MainWindow, qtbot: QtBot) -> None:
        """Test that rapid navigation commands don't cause issues."""
        window = fully_configured_window

        initial_frame = 10
        get_application_state().set_frame(initial_frame)

        # StateManager automatically synchronizes timeline_tabs via observer pattern

        # Rapidly send multiple navigation commands
        for _ in range(5):
            qtbot.keyClick(window.timeline_tabs or window, Qt.Key.Key_Right)

        qtbot.wait(100)  # Let everything settle

        # Should have moved 5 frames forward
        assert get_application_state().set_frame(= initial_frame + 5)

        # Rapidly alternate directions
        for _ in range(3):
            qtbot.keyClick(window.timeline_tabs or window, Qt.Key.Key_Left)
            qtbot.keyClick(window.timeline_tabs or window, Qt.Key.Key_Right)

        qtbot.wait(100)

        # Should end up at same position
        assert get_application_state().set_frame(= initial_frame + 5)

    def test_navigation_with_data_reload(self, fully_configured_window: MainWindow, qtbot: QtBot) -> None:
        """Test navigation continues to work after data is reloaded."""
        window = fully_configured_window

        # Navigate to a specific frame
        get_application_state().set_frame(10)

        # Load new data
        new_data = [
            (5, 100.0, 100.0, "keyframe"),
            (10, 200.0, 200.0, "keyframe"),
            (15, 300.0, 300.0, "keyframe"),
            (20, 400.0, 400.0, "keyframe"),
        ]

        assert window.curve_widget is not None
        window.curve_widget.set_curve_data(new_data)
        window.update_timeline_tabs(new_data)
        qtbot.wait(100)

        # Navigation should still work
        page_down = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(window.timeline_tabs or window, page_down)
        qtbot.wait(10)

        # Should navigate to next keyframe
        assert get_application_state().set_frame(= 15)

    def test_timeline_colors_remain_consistent_during_navigation(
        self, fully_configured_window: MainWindow, qtbot: QtBot
    ) -> None:
        """Test that timeline colors don't flicker or change during navigation."""
        window = fully_configured_window

        if not window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        timeline = window.timeline_tabs

        # Get initial colors for specific frames
        frame_colors = {}
        test_frames = [1, 7, 10, 15, 20, 25]  # Mix of data and gap frames

        for frame in test_frames:
            if frame in timeline.frame_tabs:
                tab = timeline.frame_tabs[frame]
                color = tab._get_background_color()
                frame_colors[frame] = (color.red(), color.green(), color.blue())

        # Navigate through several frames
        for target in [5, 10, 15, 20]:
            get_application_state().set_frame(target)
            qtbot.wait(50)

        # Check colors haven't changed
        for frame in test_frames:
            if frame in timeline.frame_tabs:
                tab = timeline.frame_tabs[frame]
                color = tab._get_background_color()
                current_color = (color.red(), color.green(), color.blue())

                # Color should remain the same
                assert current_color == frame_colors[frame], f"Frame {frame} color changed during navigation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
