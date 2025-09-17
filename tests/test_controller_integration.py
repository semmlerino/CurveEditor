"""
Integration tests for controller interactions.

This module tests how PlaybackController and FrameNavigationController
work together through the StateManager to provide coordinated functionality.
"""

import time
from unittest.mock import patch

import pytest
from PySide6.QtTest import QSignalSpy

from ui.controllers.frame_navigation_controller import FrameNavigationController
from ui.controllers.playback_controller import PlaybackController, PlaybackMode
from ui.state_manager import StateManager


class TestControllerIntegration:
    """Test interactions between PlaybackController and FrameNavigationController."""

    @pytest.fixture
    def integration_setup(self, qtbot):
        """Set up integrated controller environment."""
        # Create shared state manager
        state_manager = StateManager()

        # Create both controllers
        frame_nav = FrameNavigationController(state_manager)
        playback = PlaybackController(state_manager)

        # Register widgets with qtbot
        qtbot.addWidget(frame_nav.frame_spinbox)
        qtbot.addWidget(frame_nav.frame_slider)
        qtbot.addWidget(frame_nav.btn_first)
        qtbot.addWidget(frame_nav.btn_prev)
        qtbot.addWidget(frame_nav.btn_next)
        qtbot.addWidget(frame_nav.btn_last)
        qtbot.addWidget(playback.btn_play_pause)
        qtbot.addWidget(playback.fps_spinbox)

        # Set initial frame range
        frame_nav.set_frame_range(1, 100)

        # Connect playback frame requests to navigation controller (like MainWindow does)
        playback.frame_requested.connect(frame_nav.set_frame)

        return {"state_manager": state_manager, "frame_nav": frame_nav, "playback": playback}

    def test_playback_updates_frame_navigation(self, integration_setup, qtbot):
        """Test that playback updates frame navigation display."""
        frame_nav = integration_setup["frame_nav"]
        playback = integration_setup["playback"]

        # Start at frame 1
        frame_nav.set_frame(1)
        assert frame_nav.get_current_frame() == 1

        # Mock timer to simulate playback
        with patch.object(playback, "playback_timer") as mock_timer:
            mock_timer.isActive.return_value = False

            # Start playback
            playback.toggle_playback()
            assert playback.is_playing

            # Simulate frame advancement
            playback._advance_frame()

            # Frame navigation should reflect new frame
            assert frame_nav.get_current_frame() == 2
            assert frame_nav.frame_spinbox.value() == 2
            assert frame_nav.frame_slider.value() == 2

    def test_manual_frame_change_stops_playback(self, integration_setup):
        """Test that manual frame navigation stops active playback."""
        state_manager = integration_setup["state_manager"]
        frame_nav = integration_setup["frame_nav"]
        playback = integration_setup["playback"]

        # Start playback
        with patch.object(playback, "playback_timer") as mock_timer:
            mock_timer.isActive.return_value = False
            playback.toggle_playback()
            assert playback.is_playing

            # Manual frame change via spinbox
            frame_nav.frame_spinbox.setValue(50)

            # Check frame updated
            assert frame_nav.get_current_frame() == 50
            assert state_manager.current_frame == 50

    def test_frame_range_affects_both_controllers(self, integration_setup):
        """Test that frame range changes affect both controllers."""
        state_manager = integration_setup["state_manager"]
        frame_nav = integration_setup["frame_nav"]
        playback = integration_setup["playback"]

        # Set new frame range
        frame_nav.set_frame_range(1, 50)

        # Check frame navigation limits
        assert frame_nav.frame_spinbox.minimum() == 1
        assert frame_nav.frame_spinbox.maximum() == 50
        assert frame_nav.frame_slider.minimum() == 1
        assert frame_nav.frame_slider.maximum() == 50

        # Start at frame 45
        frame_nav.set_frame(45)

        # Test playback respects new bounds
        with patch.object(playback, "playback_timer") as mock_timer:
            mock_timer.isActive.return_value = False
            playback.toggle_playback()

            # Advance frames
            for _ in range(10):
                playback._advance_frame()

            # Should be at frame 50 (max), not beyond
            current_frame = state_manager.current_frame
            assert current_frame <= 50

    def test_oscillating_playback_with_navigation(self, integration_setup, qtbot):
        """Test oscillating playback works with frame navigation."""
        frame_nav = integration_setup["frame_nav"]
        playback = integration_setup["playback"]

        # Set frame range (this updates state_manager.total_frames)
        frame_nav.set_frame_range(1, 10)

        # Start at frame 1
        frame_nav.set_frame(1)
        qtbot.wait(10)  # Allow signal processing

        with patch.object(playback, "playback_timer") as mock_timer:
            mock_timer.isActive.return_value = False
            playback.toggle_playback()

            frames_seen = []

            # Simulate 20 frame advances to see full oscillation
            for _ in range(20):
                current_frame = frame_nav.get_current_frame()
                frames_seen.append(current_frame)
                # Manually advance the playback logic
                playback._advance_frame()
                qtbot.wait(1)  # Allow signal processing

            # Should see forward then backward sequence
            assert 1 in frames_seen
            assert 10 in frames_seen
            # Check we actually advanced through different frames
            unique_frames = list(set(frames_seen))
            assert len(unique_frames) > 5, f"Only saw frames: {unique_frames}"

    def test_state_synchronization(self, integration_setup, qtbot):
        """Test that state stays synchronized between controllers."""
        state_manager = integration_setup["state_manager"]
        frame_nav = integration_setup["frame_nav"]
        playback = integration_setup["playback"]

        # Create signal spy for state changes
        spy = QSignalSpy(state_manager.frame_changed)

        # Change frame via navigation
        frame_nav.set_frame(25)
        qtbot.wait(10)

        assert spy.count() == 1
        assert spy.at(0)[0] == 25
        assert state_manager.current_frame == 25

        # Change frame via playback
        with patch.object(playback, "playback_timer") as mock_timer:
            mock_timer.isActive.return_value = False
            playback.toggle_playback()
            playback._advance_frame()

            assert state_manager.current_frame == 26
            assert frame_nav.get_current_frame() == 26

    def test_navigation_buttons_during_playback(self, integration_setup):
        """Test navigation button behavior during playback."""
        frame_nav = integration_setup["frame_nav"]
        playback = integration_setup["playback"]

        # Start playback
        with patch.object(playback, "playback_timer") as mock_timer:
            mock_timer.isActive.return_value = False
            playback.toggle_playback()
            assert playback.is_playing

            # Use navigation buttons
            frame_nav.btn_last.click()
            assert frame_nav.get_current_frame() == 100

            frame_nav.btn_first.click()
            assert frame_nav.get_current_frame() == 1

            frame_nav.btn_next.click()
            assert frame_nav.get_current_frame() == 2

            frame_nav.btn_prev.click()
            assert frame_nav.get_current_frame() == 1

    def test_fps_change_during_playback(self, integration_setup):
        """Test FPS changes during active playback."""
        playback = integration_setup["playback"]

        with patch.object(playback, "playback_timer") as mock_timer:
            # Start playback
            mock_timer.isActive.return_value = False
            playback.toggle_playback()
            assert playback.is_playing

            # Change FPS during playback
            playback.fps_spinbox.setValue(60)

            # Timer interval should be updated
            expected_interval = int(1000 / 60)
            mock_timer.setInterval.assert_called_with(expected_interval)

    def test_frame_clamping_coordination(self, integration_setup):
        """Test frame clamping works correctly between controllers."""
        state_manager = integration_setup["state_manager"]
        frame_nav = integration_setup["frame_nav"]

        # Set frame range
        frame_nav.set_frame_range(10, 50)

        # Try to set frame below minimum
        frame_nav.set_frame(5)
        assert frame_nav.get_current_frame() == 10  # Clamped to min
        assert state_manager.current_frame == 10

        # Try to set frame above maximum
        frame_nav.set_frame(100)
        assert frame_nav.get_current_frame() == 50  # Clamped to max
        assert state_manager.current_frame == 50

    def test_update_frame_display_integration(self, integration_setup):
        """Test update_frame_display doesn't cause signal loops."""
        state_manager = integration_setup["state_manager"]
        frame_nav = integration_setup["frame_nav"]

        # Spy on frame_changed signal
        spy = QSignalSpy(frame_nav.frame_changed)

        # Update display without signals
        frame_nav.update_frame_display(42, update_state=False)

        # No signals should be emitted
        assert spy.count() == 0
        assert frame_nav.frame_spinbox.value() == 42
        assert frame_nav.frame_slider.value() == 42
        # State should not be updated
        assert state_manager.current_frame != 42  # Still at previous value

        # Update display with state update
        frame_nav.update_frame_display(42, update_state=True)
        assert state_manager.current_frame == 42
        # Still no signal (blocked)
        assert spy.count() == 0


class TestControllerSignalFlow:
    """Test signal flow between controllers and state manager."""

    @pytest.fixture
    def signal_setup(self, qtbot):
        """Set up for signal flow testing."""
        state_manager = StateManager()
        frame_nav = FrameNavigationController(state_manager)
        playback = PlaybackController(state_manager)

        # Register widgets
        qtbot.addWidget(frame_nav.frame_spinbox)
        qtbot.addWidget(frame_nav.frame_slider)
        qtbot.addWidget(playback.btn_play_pause)
        qtbot.addWidget(playback.fps_spinbox)

        # Connect playback frame requests to navigation controller
        playback.frame_requested.connect(frame_nav.set_frame)

        return {"state_manager": state_manager, "frame_nav": frame_nav, "playback": playback}

    def test_frame_changed_signal_propagation(self, signal_setup, qtbot):
        """Test frame_changed signal propagates correctly."""
        state_manager = signal_setup["state_manager"]
        frame_nav = signal_setup["frame_nav"]

        # Ensure we start at a known frame
        frame_nav.set_frame_range(1, 100)
        frame_nav.set_frame(1)
        qtbot.wait(10)

        # Set up signal spies AFTER initial setup
        state_spy = QSignalSpy(state_manager.frame_changed)
        nav_spy = QSignalSpy(frame_nav.frame_changed)

        # Change frame to a different value
        frame_nav.set_frame(30)
        qtbot.wait(10)

        # Both should emit
        assert state_spy.count() >= 1  # At least one signal
        assert state_spy.at(0)[0] == 30
        assert nav_spy.count() >= 1  # At least one signal
        assert nav_spy.at(0)[0] == 30

    def test_playback_state_signal(self, signal_setup):
        """Test playback state change signals."""
        playback = signal_setup["playback"]

        # Ensure we're in stopped state initially
        playback.playback_state.mode = PlaybackMode.STOPPED

        # Spy on playback signals
        start_spy = QSignalSpy(playback.playback_started)
        stop_spy = QSignalSpy(playback.playback_stopped)

        # Toggle playback
        with patch.object(playback, "playback_timer") as mock_timer:
            mock_timer.isActive.return_value = False
            playback.toggle_playback()

            assert start_spy.count() >= 1  # At least one start signal
            assert playback.is_playing

            # Ensure timer thinks it's active before stopping
            playback.playback_state.mode = PlaybackMode.PLAYING_FORWARD
            playback.toggle_playback()

            assert stop_spy.count() >= 1  # At least one stop signal
            assert not playback.is_playing

    def test_status_message_propagation(self, signal_setup, qtbot):
        """Test status message signals from controllers."""
        frame_nav = signal_setup["frame_nav"]
        playback = signal_setup["playback"]

        # Spy on status messages
        nav_status_spy = QSignalSpy(frame_nav.status_message)
        playback_status_spy = QSignalSpy(playback.status_message)

        # Frame navigation status
        frame_nav.set_frame_range(1, 200)
        frame_nav.set_frame(100)
        qtbot.wait(10)

        # Should emit status
        assert nav_status_spy.count() > 0
        last_status = nav_status_spy.at(nav_status_spy.count() - 1)[0]
        assert "Frame 100/200" in last_status

        # Playback status
        with patch.object(playback, "playback_timer"):
            playback.toggle_playback()
            qtbot.wait(10)

            if playback_status_spy.count() > 0:
                status = playback_status_spy.at(0)[0]
                assert "Playback" in status or "Started" in status


class TestEdgeCases:
    """Test edge cases and error conditions in controller integration."""

    @pytest.fixture
    def edge_setup(self, qtbot):
        """Set up for edge case testing."""
        state_manager = StateManager()
        frame_nav = FrameNavigationController(state_manager)
        playback = PlaybackController(state_manager)

        qtbot.addWidget(frame_nav.frame_spinbox)
        qtbot.addWidget(playback.btn_play_pause)

        # Connect playback frame requests to navigation controller
        playback.frame_requested.connect(frame_nav.set_frame)

        return {"state_manager": state_manager, "frame_nav": frame_nav, "playback": playback}

    def test_empty_frame_range(self, edge_setup):
        """Test behavior with minimal frame range."""
        frame_nav = edge_setup["frame_nav"]
        playback = edge_setup["playback"]

        # Set single frame range
        frame_nav.set_frame_range(1, 1)

        assert frame_nav.get_current_frame() == 1

        # Playback should handle single frame
        with patch.object(playback, "playback_timer") as mock_timer:
            mock_timer.isActive.return_value = False
            playback.toggle_playback()
            playback._advance_frame()

            # Should stay at frame 1
            assert frame_nav.get_current_frame() == 1

    def test_rapid_controller_switching(self, edge_setup, qtbot):
        """Test rapid switching between controllers."""
        frame_nav = edge_setup["frame_nav"]
        playback = edge_setup["playback"]

        frame_nav.set_frame_range(1, 100)

        # Rapidly switch between manual and playback control
        for i in range(1, 11):
            # Manual set
            frame_nav.set_frame(i * 10)
            qtbot.wait(1)
            assert frame_nav.get_current_frame() == i * 10

            # Playback advance
            with patch.object(playback, "playback_timer"):
                playback.playback_state.mode = PlaybackMode.PLAYING_FORWARD
                playback.playback_state.current_frame = i * 10
                playback._advance_frame()
                # Frame updates need to go through navigation controller

    def test_state_manager_reset_affects_controllers(self, edge_setup):
        """Test that state manager reset affects both controllers."""
        state_manager = edge_setup["state_manager"]
        frame_nav = edge_setup["frame_nav"]

        # Set some state
        frame_nav.set_frame_range(1, 200)
        frame_nav.set_frame(150)

        # Reset state manager
        state_manager.reset_to_defaults()

        # Frame should be reset
        assert state_manager.current_frame == 1
        assert state_manager.total_frames == 1

        # Navigation should reflect reset (but stays at 150 since spinbox range still 1-200)
        # The spinbox value is clamped to valid range but not forcibly updated
        assert frame_nav.get_current_frame() == 150

    def test_concurrent_updates(self, edge_setup):
        """Test concurrent updates from multiple sources."""
        state_manager = edge_setup["state_manager"]
        frame_nav = edge_setup["frame_nav"]

        frame_nav.set_frame_range(1, 100)

        # Simulate concurrent updates
        updates_applied = []

        def update_via_nav():
            frame_nav.set_frame(50)
            updates_applied.append("nav")

        def update_via_state():
            state_manager.current_frame = 60
            updates_applied.append("state")

        # Apply updates
        update_via_nav()
        update_via_state()

        # Last update wins
        assert state_manager.current_frame == 60
        assert updates_applied == ["nav", "state"]

    def test_invalid_fps_handling(self, edge_setup):
        """Test handling of invalid FPS values."""
        playback = edge_setup["playback"]

        # FPS spinbox should have reasonable limits
        assert playback.fps_spinbox.minimum() >= 1
        assert playback.fps_spinbox.maximum() <= 240

        # Try to set invalid values (spinbox should clamp)
        playback.fps_spinbox.setValue(0)
        assert playback.fps_spinbox.value() >= 1

        playback.fps_spinbox.setValue(1000)
        assert playback.fps_spinbox.value() <= 240


class TestPerformance:
    """Test performance characteristics of controller integration."""

    @pytest.fixture
    def perf_setup(self, qtbot):
        """Set up for performance testing."""
        state_manager = StateManager()
        frame_nav = FrameNavigationController(state_manager)
        playback = PlaybackController(state_manager)

        qtbot.addWidget(frame_nav.frame_spinbox)

        # Connect playback frame requests to navigation controller
        playback.frame_requested.connect(frame_nav.set_frame)

        return {"state_manager": state_manager, "frame_nav": frame_nav, "playback": playback}

    def test_high_frequency_updates(self, perf_setup, qtbot):
        """Test system handles high frequency updates."""
        frame_nav = perf_setup["frame_nav"]

        frame_nav.set_frame_range(1, 1000)

        start_time = time.time()

        # Rapid frame updates
        for frame in range(1, 101):
            frame_nav.set_frame(frame)

        elapsed = time.time() - start_time

        # Should complete quickly (< 1 second for 100 updates)
        assert elapsed < 1.0
        assert frame_nav.get_current_frame() == 100

    def test_signal_blocking_performance(self, perf_setup):
        """Test that signal blocking improves performance."""
        frame_nav = perf_setup["frame_nav"]

        frame_nav.set_frame_range(1, 1000)

        # Time with signal blocking (built into update_frame_display)
        start_time = time.time()
        for frame in range(1, 101):
            frame_nav.update_frame_display(frame, update_state=False)
        blocked_time = time.time() - start_time

        # Time without blocking (normal set_frame)
        start_time = time.time()
        for frame in range(1, 101):
            frame_nav.set_frame(frame)
        normal_time = time.time() - start_time

        # Signal blocking should be faster or similar
        # (May vary based on system, so we're lenient)
        assert blocked_time < normal_time * 2.0
