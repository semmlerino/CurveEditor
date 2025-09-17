#!/usr/bin/env python
"""
Integration tests for spacebar oscillating playback functionality.

Tests the complete flow: Spacebar -> ShortcutManager -> PlaybackController
Following UNIFIED_TESTING_GUIDE principles: real components, behavior testing.
"""

import pytest
from PySide6.QtTest import QSignalSpy

from ui.controllers.playback_controller import PlaybackController, PlaybackMode
from ui.keyboard_shortcuts import ShortcutManager
from ui.state_manager import StateManager


class TestMainWindowMock:
    """Minimal MainWindow mock for testing action connections."""

    def __init__(self):
        self.state_manager = StateManager(None)
        self.playback_controller = PlaybackController(self.state_manager)
        self.action_calls = []  # Track action calls for verification

    def _on_action_new(self):
        self.action_calls.append("new")

    def _on_action_open(self):
        self.action_calls.append("open")

    def _on_action_save(self):
        self.action_calls.append("save")

    def _on_action_save_as(self):
        self.action_calls.append("save_as")

    def _on_load_images(self):
        self.action_calls.append("load_images")

    def _on_export_data(self):
        self.action_calls.append("export_data")

    def _on_action_undo(self):
        self.action_calls.append("undo")

    def _on_action_redo(self):
        self.action_calls.append("redo")

    def _on_select_all(self):
        self.action_calls.append("select_all")

    def _on_add_point(self):
        self.action_calls.append("add_point")

    def _on_action_zoom_in(self):
        self.action_calls.append("zoom_in")

    def _on_action_zoom_out(self):
        self.action_calls.append("zoom_out")

    def _on_zoom_fit(self):
        self.action_calls.append("zoom_fit")

    def _on_action_reset_view(self):
        self.action_calls.append("reset_view")

    def _on_smooth_curve(self):
        self.action_calls.append("smooth_curve")

    def _on_filter_curve(self):
        self.action_calls.append("filter_curve")

    def _on_analyze_curve(self):
        self.action_calls.append("analyze_curve")

    def close(self):
        self.action_calls.append("close")

    @property
    def frame_nav_controller(self):
        """Mock frame navigation controller."""

        class MockFrameNavController:
            def _on_next_frame(self):
                pass

            def _on_prev_frame(self):
                pass

            def _on_first_frame(self):
                pass

            def _on_last_frame(self):
                pass

        return MockFrameNavController()


@pytest.fixture
def mock_main_window(qtbot):
    """Create a mock MainWindow with real controllers."""
    window = TestMainWindowMock()
    qtbot.addWidget(window.playback_controller.btn_play_pause)
    qtbot.addWidget(window.playback_controller.fps_spinbox)
    return window


@pytest.fixture
def shortcut_manager(mock_main_window):
    """Create ShortcutManager and connect to mock window."""
    manager = ShortcutManager(None)
    manager.connect_to_main_window(mock_main_window)
    return manager


class TestSpacebarOscillatingPlayback:
    """Integration tests for spacebar oscillating playback."""

    def test_spacebar_action_exists_and_configured(self, shortcut_manager):
        """Test spacebar action exists with correct shortcut."""
        action = shortcut_manager.action_oscillate_playback

        assert action is not None
        assert action.shortcut().toString() == "Space"
        assert action.statusTip() == "Toggle oscillating playback"
        assert action.text() == "Toggle Playback"

    def test_spacebar_action_connected_to_playback_controller(self, shortcut_manager, mock_main_window, qtbot):
        """Test spacebar action properly connects to playback controller."""
        # Setup signal spy on playback controller
        start_spy = QSignalSpy(mock_main_window.playback_controller.playback_started)
        stop_spy = QSignalSpy(mock_main_window.playback_controller.playback_stopped)

        # Trigger the action (simulates spacebar press)
        shortcut_manager.action_oscillate_playback.trigger()

        # Should start playback
        assert mock_main_window.playback_controller.playback_state.mode == PlaybackMode.PLAYING_FORWARD
        assert start_spy.count() == 1

        # Trigger again - should stop playback
        shortcut_manager.action_oscillate_playback.trigger()

        assert mock_main_window.playback_controller.playback_state.mode == PlaybackMode.STOPPED
        assert stop_spy.count() == 1

    def test_spacebar_action_only_connected_once(self, shortcut_manager, mock_main_window, qtbot):
        """Test action is connected only once to prevent duplicate calls."""
        # Reset any existing state
        if mock_main_window.playback_controller.playback_state.mode != PlaybackMode.STOPPED:
            mock_main_window.playback_controller.toggle_playback()

        # Setup spy for status messages
        status_spy = QSignalSpy(mock_main_window.playback_controller.status_message)

        # Trigger action once
        shortcut_manager.action_oscillate_playback.trigger()

        # Should get exactly one status message for start
        start_count = 0
        for i in range(status_spy.count()):
            if "Started oscillating playback" in status_spy.at(i)[0]:
                start_count += 1

        assert start_count == 1, f"Expected 1 start message, got {start_count}"
        assert mock_main_window.playback_controller.playback_state.mode == PlaybackMode.PLAYING_FORWARD

    def test_multiple_rapid_spacebar_presses(self, shortcut_manager, mock_main_window, qtbot):
        """Test rapid spacebar presses don't cause issues."""
        initial_mode = mock_main_window.playback_controller.playback_state.mode

        # Rapid fire the action
        for i in range(10):
            shortcut_manager.action_oscillate_playback.trigger()

        # Should end up in opposite state from where we started
        final_mode = mock_main_window.playback_controller.playback_state.mode

        # With even number of presses (10), should be back to original state
        assert final_mode == initial_mode

    def test_shortcut_manager_connects_all_actions(self, shortcut_manager, mock_main_window):
        """Test ShortcutManager connects all actions properly."""
        # Verify some key actions are connected by triggering them
        shortcut_manager.action_new.trigger()
        assert "new" in mock_main_window.action_calls

        shortcut_manager.action_undo.trigger()
        assert "undo" in mock_main_window.action_calls

        shortcut_manager.action_zoom_in.trigger()
        assert "zoom_in" in mock_main_window.action_calls

        # Most importantly, verify playback action works
        initial_mode = mock_main_window.playback_controller.playback_state.mode
        shortcut_manager.action_oscillate_playback.trigger()
        new_mode = mock_main_window.playback_controller.playback_state.mode
        assert new_mode != initial_mode

    def test_action_properties_match_expected_values(self, shortcut_manager):
        """Test action properties are set correctly."""
        action = shortcut_manager.action_oscillate_playback

        # Test key properties
        assert action.text() == "Toggle Playback"
        assert action.statusTip() == "Toggle oscillating playback"
        assert action.shortcut().toString() == "Space"

        # Test it's included in shortcuts dictionary
        all_actions = shortcut_manager.get_all_actions()
        assert "oscillate_playback" in all_actions
        assert all_actions["oscillate_playback"] is action


class TestShortcutManagerIntegration:
    """Integration tests for ShortcutManager behavior."""

    def test_all_expected_actions_exist(self, shortcut_manager):
        """Test all expected actions are created."""
        expected_actions = [
            "new",
            "open",
            "save",
            "save_as",
            "load_images",
            "export_data",
            "quit",
            "undo",
            "redo",
            "select_all",
            "add_point",
            "zoom_in",
            "zoom_out",
            "zoom_fit",
            "reset_view",
            "smooth_curve",
            "filter_curve",
            "analyze_curve",
            "next_frame",
            "prev_frame",
            "first_frame",
            "last_frame",
            "oscillate_playback",
        ]

        all_actions = shortcut_manager.get_all_actions()

        for action_name in expected_actions:
            assert action_name in all_actions, f"Action '{action_name}' not found"
            assert all_actions[action_name] is not None

    def test_action_shortcuts_are_unique(self, shortcut_manager):
        """Test no two actions have the same shortcut."""
        all_actions = shortcut_manager.get_all_actions()
        shortcuts = {}

        for name, action in all_actions.items():
            shortcut = action.shortcut().toString()
            if shortcut:  # Skip empty shortcuts
                if shortcut in shortcuts:
                    pytest.fail(
                        f"Duplicate shortcut '{shortcut}' found in actions '{shortcuts[shortcut]}' and '{name}'"
                    )
                shortcuts[shortcut] = name

        # Verify spacebar is assigned uniquely
        assert "Space" in shortcuts
        assert shortcuts["Space"] == "oscillate_playback"

    def test_connection_to_main_window_completes_without_error(self, mock_main_window):
        """Test connecting to MainWindow doesn't raise exceptions."""
        # This should complete without any exceptions
        manager = ShortcutManager(None)

        # Should not raise
        manager.connect_to_main_window(mock_main_window)

        # Verify a sample connection worked
        manager.action_new.trigger()
        assert "new" in mock_main_window.action_calls


class TestOscillatingPlaybackBehavior:
    """Test the actual oscillating behavior through integration."""

    def test_full_oscillation_cycle_through_spacebar(self, shortcut_manager, mock_main_window, qtbot):
        """Test complete oscillation cycle triggered by spacebar."""
        controller = mock_main_window.playback_controller
        state_manager = mock_main_window.state_manager

        # Set up small frame range for testing
        # Note: update_playback_bounds() will override manual range with state_manager.total_frames
        state_manager.total_frames = 3
        controller.set_frame_range(1, 3)
        state_manager.current_frame = 1

        frame_spy = QSignalSpy(controller.frame_requested)

        # Start playback with spacebar
        shortcut_manager.action_oscillate_playback.trigger()
        assert controller.playback_state.mode == PlaybackMode.PLAYING_FORWARD

        # Simulate oscillation
        # Frame 1 -> 2
        controller._on_playback_timer()
        assert frame_spy.at(0)[0] == 2
        state_manager.current_frame = 2

        # Frame 2 -> 3
        controller._on_playback_timer()
        assert frame_spy.at(1)[0] == 3
        state_manager.current_frame = 3

        # Frame 3 (max) -> reverse to 2
        controller._on_playback_timer()
        assert controller.playback_state.mode == PlaybackMode.PLAYING_BACKWARD
        assert frame_spy.at(2)[0] == 2

        # Stop with spacebar
        shortcut_manager.action_oscillate_playback.trigger()
        assert controller.playback_state.mode == PlaybackMode.STOPPED
        assert not controller.playback_timer.isActive()

    def test_spacebar_during_playback_stops_immediately(self, shortcut_manager, mock_main_window, qtbot):
        """Test spacebar during playback stops immediately."""
        controller = mock_main_window.playback_controller

        # Start playback
        shortcut_manager.action_oscillate_playback.trigger()
        assert controller.playback_timer.isActive()
        assert controller.playback_state.mode == PlaybackMode.PLAYING_FORWARD

        # Let it run briefly
        qtbot.wait(50)

        # Stop with spacebar
        shortcut_manager.action_oscillate_playback.trigger()
        assert not controller.playback_timer.isActive()
        assert controller.playback_state.mode == PlaybackMode.STOPPED

    @pytest.mark.parametrize("fps", [12, 24, 60])
    def test_spacebar_playback_at_different_fps(self, shortcut_manager, mock_main_window, qtbot, fps):
        """Test spacebar playback works at different FPS settings."""
        controller = mock_main_window.playback_controller

        # Set FPS
        controller.fps_spinbox.setValue(fps)

        # Start with spacebar
        shortcut_manager.action_oscillate_playback.trigger()

        # Verify timer interval matches FPS
        expected_interval = int(1000 / fps)
        assert controller.playback_timer.interval() == expected_interval
        assert controller.playback_timer.isActive()

        # Stop
        shortcut_manager.action_oscillate_playback.trigger()
        assert not controller.playback_timer.isActive()


class TestRegressionPrevention:
    """Tests to prevent regression of the duplicate connection issue."""

    def test_no_duplicate_signal_emissions(self, shortcut_manager, mock_main_window, qtbot):
        """Test that action trigger doesn't cause duplicate signal emissions."""
        controller = mock_main_window.playback_controller

        # Use multiple spies to catch any duplicates
        start_spy = QSignalSpy(controller.playback_started)
        stop_spy = QSignalSpy(controller.playback_stopped)
        status_spy = QSignalSpy(controller.status_message)

        # Trigger once - should get exactly one set of signals
        shortcut_manager.action_oscillate_playback.trigger()

        # Give a moment for any delayed signals
        qtbot.wait(10)

        # Should have exactly one start signal and one status message
        assert start_spy.count() == 1

        # Count start status messages
        start_messages = [i for i in range(status_spy.count()) if "Started oscillating playback" in status_spy.at(i)[0]]
        assert len(start_messages) == 1, f"Expected 1 start message, got {len(start_messages)}"

        # Stop and verify single stop signal
        shortcut_manager.action_oscillate_playback.trigger()
        qtbot.wait(10)

        assert stop_spy.count() == 1
        stop_messages = [i for i in range(status_spy.count()) if "Stopped playback" in status_spy.at(i)[0]]
        assert len(stop_messages) == 1, f"Expected 1 stop message, got {len(stop_messages)}"

    def test_action_connection_is_singular(self, shortcut_manager, mock_main_window):
        """Test that action has exactly one connection to toggle_playback."""
        action = shortcut_manager.action_oscillate_playback

        # This is a tricky test - we can't easily inspect signal connections
        # But we can test the behavior: toggle twice should return to original state
        original_mode = mock_main_window.playback_controller.playback_state.mode

        # Two triggers should toggle twice
        action.trigger()
        intermediate_mode = mock_main_window.playback_controller.playback_state.mode
        action.trigger()
        final_mode = mock_main_window.playback_controller.playback_state.mode

        # Should have toggled twice back to original
        assert final_mode == original_mode
        assert intermediate_mode != original_mode
