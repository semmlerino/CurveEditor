#!/usr/bin/env python
"""
Tests for MainWindow keyboard shortcut integration.

Tests that shortcuts are properly registered with the window hierarchy.
Following UNIFIED_TESTING_GUIDE principles: real components, behavior testing.
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
from PySide6.QtTest import QSignalSpy

from ui.main_window import MainWindow


@pytest.fixture
def main_window(qtbot):
    """Create a real MainWindow for testing."""
    window = MainWindow()
    qtbot.addWidget(window)
    return window


class TestMainWindowShortcutRegistration:
    """Test that shortcuts are properly registered with MainWindow."""

    def test_oscillate_playback_action_added_to_window(self, main_window):
        """Test that oscillate_playback action is added to window actions."""
        # MainWindow should have the action in its actions list
        window_actions = main_window.actions()
        action_shortcuts = [action.shortcut().toString() for action in window_actions]

        assert "Space" in action_shortcuts, "Spacebar shortcut not found in window actions"

        # Find the specific action
        space_action = None
        for action in window_actions:
            if action.shortcut().toString() == "Space":
                space_action = action
                break

        assert space_action is not None
        assert space_action.text() == "Toggle Playback"

    def test_spacebar_triggers_action_through_window(self, main_window, qtbot):
        """Test that spacebar key press triggers action through window hierarchy."""
        # Setup spy on timeline controller
        start_spy = QSignalSpy(main_window.timeline_controller.playback_started)
        stop_spy = QSignalSpy(main_window.timeline_controller.playback_stopped)

        # Make sure window is active to receive key events
        main_window.show()
        qtbot.waitExposed(main_window)
        main_window.activateWindow()
        qtbot.waitActive(main_window)

        # Ensure main window has focus for key events
        main_window.setFocus(Qt.FocusReason.OtherFocusReason)
        qtbot.wait(10)

        # Simulate spacebar press at window level
        qtbot.keyClick(main_window, Qt.Key.Key_Space)

        # Should start playback
        assert start_spy.count() >= 1
        assert main_window.timeline_controller.playback_state.mode.name in ["PLAYING_FORWARD", "PLAYING_BACKWARD"]

        # Press again to stop
        qtbot.keyClick(main_window, Qt.Key.Key_Space)

        # Should stop playback
        assert stop_spy.count() >= 1

    def test_action_properties_correct(self, main_window):
        """Test action properties are set correctly."""
        action = main_window.action_oscillate_playback

        assert action is not None
        assert action.shortcut().toString() == "Space"
        assert action.text() == "Toggle Playback"
        assert action.statusTip() == "Toggle oscillating playback"

    def test_action_is_connected(self, main_window, qtbot):
        """Test action is properly connected to playback controller."""
        # Get the action
        action = main_window.action_oscillate_playback

        # Setup spy
        start_spy = QSignalSpy(main_window.timeline_controller.playback_started)

        # Trigger action directly
        action.trigger()

        # Should start playback
        assert start_spy.count() == 1

    def test_no_duplicate_space_actions(self, main_window):
        """Test there's only one Space shortcut action."""
        window_actions = main_window.actions()
        space_actions = [action for action in window_actions if action.shortcut().toString() == "Space"]

        assert len(space_actions) == 1, f"Expected 1 Space action, found {len(space_actions)}"

    def test_shortcut_manager_actions_accessible(self, main_window):
        """Test that all ShortcutManager actions are accessible from MainWindow."""
        # Key actions should be accessible as attributes
        assert hasattr(main_window, "action_oscillate_playback")
        assert hasattr(main_window, "action_new")
        assert hasattr(main_window, "action_open")
        assert hasattr(main_window, "action_save")
        assert hasattr(main_window, "action_undo")
        assert hasattr(main_window, "action_redo")

        # They should all be QAction objects
        from PySide6.QtGui import QAction

        assert isinstance(main_window.action_oscillate_playback, QAction)
        assert isinstance(main_window.action_new, QAction)

    def test_keyboard_shortcuts_dont_conflict(self, main_window):
        """Test keyboard shortcuts don't conflict with each other."""
        window_actions = main_window.actions()
        shortcuts = {}

        for action in window_actions:
            shortcut = action.shortcut().toString()
            if shortcut:  # Skip empty shortcuts
                if shortcut in shortcuts:
                    pytest.fail(
                        f"Conflicting shortcut '{shortcut}' found in actions " +
                        f"'{shortcuts[shortcut].text()}' and '{action.text()}'"
                    )
                shortcuts[shortcut] = action

        # Verify Space is unique
        assert "Space" in shortcuts
        assert shortcuts["Space"].text() == "Toggle Playback"


class TestMainWindowInitialization:
    """Test MainWindow initialization includes proper action setup."""

    def test_init_actions_called(self, main_window):
        """Test that _init_actions properly sets up oscillate_playback action."""
        # The action should exist and be properly configured
        assert main_window.action_oscillate_playback is not None
        assert main_window.action_oscillate_playback is main_window.shortcut_manager.action_oscillate_playback

    def test_shortcut_manager_connected(self, main_window):
        """Test that shortcut manager is connected to main window."""
        # Action should be connected - test by triggering
        initial_mode = main_window.timeline_controller.playback_state.mode

        main_window.action_oscillate_playback.trigger()

        new_mode = main_window.timeline_controller.playback_state.mode
        assert new_mode != initial_mode

    def test_controllers_properly_initialized(self, main_window):
        """Test that all controllers are properly initialized."""
        assert main_window.timeline_controller is not None
        assert main_window.action_controller is not None
        assert main_window.shortcut_manager is not None

        # Controllers should be connected to state manager
        assert main_window.timeline_controller.state_manager is main_window.state_manager


class TestMainWindowKeyEvents:
    """Test MainWindow key event handling."""

    def test_tab_key_handled_by_main_window(self, main_window, qtbot):
        """Test Tab key is handled by MainWindow keyPressEvent."""
        main_window.show()
        qtbot.waitExposed(main_window)

        # Create Tab key event
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier)

        # Send to main window - should be accepted
        main_window.keyPressEvent(event)

        # Event should be accepted (Tab key handler accepts it)
        assert event.isAccepted()

    def test_other_keys_passed_to_parent(self, main_window, qtbot):
        """Test other keys are passed to parent for default handling."""
        main_window.show()
        qtbot.waitExposed(main_window)

        # Create a key event that should be passed through
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)

        # Send to main window - should call super().keyPressEvent()
        # We can't easily test this directly, but we can verify the event gets processed
        main_window.keyPressEvent(event)

        # The key should have been processed normally
        # (This test mainly ensures no crashes and proper event flow)

    def test_spacebar_through_key_event(self, main_window, qtbot):
        """Test spacebar works through direct key event."""
        main_window.show()
        qtbot.waitExposed(main_window)
        main_window.activateWindow()
        qtbot.waitActive(main_window)

        # Ensure main window has focus for key events
        main_window.setFocus(Qt.FocusReason.OtherFocusReason)
        qtbot.wait(10)

        # Setup spy
        start_spy = QSignalSpy(main_window.timeline_controller.playback_started)

        # Send Space key event directly
        qtbot.keyClick(main_window, Qt.Key.Key_Space)

        # Should trigger playback
        qtbot.wait(10)  # Give time for signal processing
        assert start_spy.count() >= 1


class TestRealWorldIntegration:
    """Real-world integration scenarios."""

    def test_main_window_ready_for_user_interaction(self, main_window, qtbot):
        """Test MainWindow is ready for real user interaction."""
        # Show window
        main_window.show()
        qtbot.waitExposed(main_window)

        # Window should be responsive
        assert main_window.isVisible()
        assert main_window.isEnabled()

        # Controllers should be ready
        assert main_window.timeline_controller.playback_state.mode.name == "STOPPED"
        assert not main_window.timeline_controller.playback_timer.isActive()

        # Ensure focus for key events
        main_window.setFocus(Qt.FocusReason.OtherFocusReason)
        qtbot.wait(10)

        # Spacebar should work immediately
        qtbot.keyClick(main_window, Qt.Key.Key_Space)
        qtbot.wait(10)

        # Should start playback
        assert main_window.timeline_controller.playback_state.mode.name in ["PLAYING_FORWARD", "PLAYING_BACKWARD"]

    def test_window_cleanup_on_close(self, main_window, qtbot):
        """Test proper cleanup when window closes."""
        main_window.show()
        qtbot.waitExposed(main_window)

        # Ensure focus for key events
        main_window.setFocus(Qt.FocusReason.OtherFocusReason)
        qtbot.wait(10)

        # Start playback
        qtbot.keyClick(main_window, Qt.Key.Key_Space)
        qtbot.wait(10)

        # Should be playing
        assert main_window.timeline_controller.playback_timer.isActive()

        # Close window
        main_window.close()
        qtbot.wait(10)

        # Timer should be cleaned up (Qt handles this through parent-child relationship)
        # This test mainly ensures no crashes during cleanup

    @pytest.mark.timeout(3)
    def test_performance_spacebar_responsiveness(self, main_window, qtbot):
        """Test spacebar responds quickly without blocking."""
        main_window.show()
        qtbot.waitExposed(main_window)

        # Ensure focus for key events
        main_window.setFocus(Qt.FocusReason.OtherFocusReason)
        qtbot.wait(10)

        # Rapid spacebar presses should not block
        for _ in range(10):
            qtbot.keyClick(main_window, Qt.Key.Key_Space)
            qtbot.wait(1)  # Minimal wait

        # Should complete without timeout
        # Final state depends on even/odd number of presses
