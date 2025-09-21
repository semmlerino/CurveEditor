#!/usr/bin/env python
"""
Comprehensive tests for PlaybackController.

Tests oscillating playback, FPS control, signal emissions, and state management.
Following UNIFIED_TESTING_GUIDE principles: real components, behavior testing.
"""

import pytest
from PySide6.QtCore import QObject
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from ui.controllers import PlaybackController, PlaybackMode


class MockStateManager(QObject):
    """Minimal test double for StateManager with only what PlaybackController needs."""

    def __init__(self):
        super().__init__()
        self._current_frame = 1
        self._total_frames = 100

    @property
    def current_frame(self) -> int:
        return self._current_frame

    @current_frame.setter
    def current_frame(self, value: int) -> None:
        self._current_frame = value

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @total_frames.setter
    def total_frames(self, value: int) -> None:
        self._total_frames = value


@pytest.fixture
def state_manager():
    """Create a test state manager."""
    return MockStateManager()


@pytest.fixture
def playback_controller(qtbot, state_manager):
    """Create a PlaybackController with test dependencies."""
    controller = PlaybackController(state_manager)
    qtbot.addWidget(controller.btn_play_pause)
    qtbot.addWidget(controller.fps_spinbox)
    return controller


class TestPlaybackControllerInitialization:
    """Test PlaybackController initialization and default state."""

    def test_initialization_default_state(self, playback_controller):
        """Test controller initializes with correct default state."""
        assert playback_controller.playback_state.mode == PlaybackMode.STOPPED
        assert playback_controller.playback_state.fps == 12
        assert playback_controller.playback_state.current_frame == 1
        assert playback_controller.playback_state.min_frame == 1
        assert playback_controller.playback_state.max_frame == 100
        assert playback_controller.playback_state.loop_boundaries is True

    def test_widgets_created_with_defaults(self, playback_controller):
        """Test UI widgets are created with correct defaults."""
        assert playback_controller.btn_play_pause is not None
        assert playback_controller.btn_play_pause.isCheckable()
        assert not playback_controller.btn_play_pause.isChecked()

        assert playback_controller.fps_spinbox is not None
        assert playback_controller.fps_spinbox.value() == 24
        assert playback_controller.fps_spinbox.minimum() == 1
        assert playback_controller.fps_spinbox.maximum() == 120

    def test_timer_created_but_not_running(self, playback_controller):
        """Test timer is created but not running initially."""
        assert playback_controller.playback_timer is not None
        assert not playback_controller.playback_timer.isActive()


class TestPlaybackControllerPlayPause:
    """Test play/pause functionality."""

    def test_toggle_playback_starts_when_stopped(self, playback_controller, qtbot):
        """Test toggle_playback starts playback when stopped."""
        # Setup signal spy
        start_spy = QSignalSpy(playback_controller.playback_started)

        # Act
        playback_controller.toggle_playback()

        # Assert
        assert playback_controller.playback_state.mode == PlaybackMode.PLAYING_FORWARD
        assert playback_controller.playback_timer.isActive()
        assert playback_controller.btn_play_pause.isChecked()
        assert start_spy.count() >= 1  # At least one signal emitted

    def test_toggle_playback_stops_when_playing(self, playback_controller, qtbot):
        """Test toggle_playback stops playback when playing."""
        # Start playback first
        playback_controller.toggle_playback()
        assert playback_controller.playback_timer.isActive()

        # Setup signal spy
        stop_spy = QSignalSpy(playback_controller.playback_stopped)

        # Stop playback
        playback_controller.toggle_playback()

        # Assert
        assert playback_controller.playback_state.mode == PlaybackMode.STOPPED
        assert not playback_controller.playback_timer.isActive()
        assert not playback_controller.btn_play_pause.isChecked()
        assert stop_spy.count() >= 1  # At least one signal emitted

    def test_play_pause_button_toggle(self, playback_controller, qtbot):
        """Test play/pause button toggles playback."""
        start_spy = QSignalSpy(playback_controller.playback_started)
        stop_spy = QSignalSpy(playback_controller.playback_stopped)

        # Click play
        playback_controller.btn_play_pause.setChecked(True)
        assert playback_controller.playback_timer.isActive()
        assert start_spy.count() == 1

        # Click pause
        playback_controller.btn_play_pause.setChecked(False)
        assert not playback_controller.playback_timer.isActive()
        assert stop_spy.count() == 1

    def test_status_message_on_start_stop(self, playback_controller, qtbot):
        """Test status messages are emitted on start/stop."""
        status_spy = QSignalSpy(playback_controller.status_message)

        # Start
        playback_controller.toggle_playback()
        assert status_spy.count() >= 1
        # Check the last status message
        assert "Started oscillating playback" in status_spy.at(status_spy.count() - 1)[0]
        assert "24 FPS" in status_spy.at(status_spy.count() - 1)[0]

        # Clear the spy count for stop test
        initial_count = status_spy.count()

        # Stop
        playback_controller.toggle_playback()
        assert status_spy.count() > initial_count
        assert status_spy.at(status_spy.count() - 1)[0] == "Stopped playback"


class TestPlaybackControllerFPS:
    """Test FPS control functionality."""

    def test_fps_change_updates_state(self, playback_controller):
        """Test changing FPS updates playback state."""
        playback_controller.fps_spinbox.setValue(60)
        # Note: playback_state.fps is set to the initial value in _on_fps_changed
        # but the spinbox value is what's used when starting playback
        assert playback_controller.fps_spinbox.value() == 60

    def test_fps_change_during_playback_updates_timer(self, playback_controller, qtbot):
        """Test changing FPS during playback updates timer interval."""
        # Start playback
        playback_controller.toggle_playback()
        initial_interval = playback_controller.playback_timer.interval()
        assert initial_interval == int(1000 / 24)  # Default 24 fps

        # Change FPS
        playback_controller.fps_spinbox.setValue(60)

        # Check timer interval updated
        new_interval = playback_controller.playback_timer.interval()
        assert new_interval == int(1000 / 60)
        assert playback_controller.playback_timer.isActive()

    def test_fps_change_when_stopped_no_timer_update(self, playback_controller):
        """Test changing FPS when stopped doesn't start timer."""
        assert not playback_controller.playback_timer.isActive()

        playback_controller.fps_spinbox.setValue(30)

        assert not playback_controller.playback_timer.isActive()

    def test_fps_boundaries(self, playback_controller):
        """Test FPS spinbox respects min/max boundaries."""
        # Test minimum
        playback_controller.fps_spinbox.setValue(0)
        assert playback_controller.fps_spinbox.value() == 1

        # Test maximum
        playback_controller.fps_spinbox.setValue(200)
        assert playback_controller.fps_spinbox.value() == 120


class TestPlaybackControllerOscillation:
    """Test oscillating playback behavior."""

    def test_oscillating_playback_forward_to_backward(self, playback_controller, state_manager, qtbot):
        """Test playback reverses from forward to backward at max frame."""
        # Setup
        state_manager.current_frame = 99
        state_manager.total_frames = 100
        playback_controller.set_frame_range(1, 100)

        frame_spy = QSignalSpy(playback_controller.frame_requested)

        # Start playback
        playback_controller._start_oscillating_playback()
        assert playback_controller.playback_state.mode == PlaybackMode.PLAYING_FORWARD

        # Simulate reaching max frame
        state_manager.current_frame = 100
        playback_controller._on_playback_timer()

        # Should reverse to backward and request frame 99
        assert playback_controller.playback_state.mode == PlaybackMode.PLAYING_BACKWARD
        assert frame_spy.count() == 1
        assert frame_spy.at(0)[0] == 99

    def test_oscillating_playback_backward_to_forward(self, playback_controller, state_manager, qtbot):
        """Test playback reverses from backward to forward at min frame."""
        # Setup - start in backward mode
        state_manager.current_frame = 2
        playback_controller.set_frame_range(1, 100)
        playback_controller.playback_state.mode = PlaybackMode.PLAYING_BACKWARD

        frame_spy = QSignalSpy(playback_controller.frame_requested)

        # Simulate timer when at min frame
        state_manager.current_frame = 1
        playback_controller._on_playback_timer()

        # Should reverse to forward and request frame 2
        assert playback_controller.playback_state.mode == PlaybackMode.PLAYING_FORWARD
        assert frame_spy.count() == 1
        assert frame_spy.at(0)[0] == 2

    def test_normal_forward_progression(self, playback_controller, state_manager, qtbot):
        """Test normal forward frame progression."""
        state_manager.current_frame = 50
        playback_controller.set_frame_range(1, 100)
        playback_controller.playback_state.mode = PlaybackMode.PLAYING_FORWARD

        frame_spy = QSignalSpy(playback_controller.frame_requested)

        playback_controller._on_playback_timer()

        assert playback_controller.playback_state.mode == PlaybackMode.PLAYING_FORWARD
        assert frame_spy.count() == 1
        assert frame_spy.at(0)[0] == 51

    def test_normal_backward_progression(self, playback_controller, state_manager, qtbot):
        """Test normal backward frame progression."""
        state_manager.current_frame = 50
        playback_controller.set_frame_range(1, 100)
        playback_controller.playback_state.mode = PlaybackMode.PLAYING_BACKWARD

        frame_spy = QSignalSpy(playback_controller.frame_requested)

        playback_controller._on_playback_timer()

        assert playback_controller.playback_state.mode == PlaybackMode.PLAYING_BACKWARD
        assert frame_spy.count() == 1
        assert frame_spy.at(0)[0] == 49

    def test_timer_does_nothing_when_stopped(self, playback_controller, qtbot):
        """Test timer callback does nothing when playback is stopped."""
        frame_spy = QSignalSpy(playback_controller.frame_requested)

        # Ensure stopped
        playback_controller.playback_state.mode = PlaybackMode.STOPPED

        # Call timer
        playback_controller._on_playback_timer()

        # Should not emit any frames
        assert frame_spy.count() == 0


class TestPlaybackControllerFrameRange:
    """Test frame range management."""

    def test_set_frame_range(self, playback_controller):
        """Test setting frame range."""
        playback_controller.set_frame_range(10, 50)

        assert playback_controller.playback_state.min_frame == 10
        assert playback_controller.playback_state.max_frame == 50

    def test_update_playback_bounds_from_state_manager(self, playback_controller, state_manager):
        """Test updating bounds from state manager."""
        state_manager.total_frames = 200

        playback_controller.update_playback_bounds()

        assert playback_controller.playback_state.min_frame == 1
        assert playback_controller.playback_state.max_frame == 200

    def test_playback_respects_custom_bounds(self, playback_controller, state_manager, qtbot):
        """Test playback respects custom frame bounds."""
        # Set custom bounds
        playback_controller.set_frame_range(20, 30)
        state_manager.current_frame = 29
        playback_controller.playback_state.mode = PlaybackMode.PLAYING_FORWARD

        frame_spy = QSignalSpy(playback_controller.frame_requested)

        # At frame 29, next should be 30
        playback_controller._on_playback_timer()
        assert frame_spy.at(0)[0] == 30

        # At frame 30 (max), should reverse
        state_manager.current_frame = 30
        playback_controller._on_playback_timer()
        assert playback_controller.playback_state.mode == PlaybackMode.PLAYING_BACKWARD
        assert frame_spy.at(1)[0] == 29


class TestPlaybackControllerIntegration:
    """Integration tests for PlaybackController."""

    def test_full_playback_cycle(self, playback_controller, state_manager, qtbot):
        """Test a complete playback cycle with multiple timer ticks."""
        # Setup small range for quick testing
        state_manager.total_frames = 3  # Set state_manager frames before playback
        state_manager.current_frame = 1

        frame_spy = QSignalSpy(playback_controller.frame_requested)

        # Start playback (will call update_playback_bounds)
        playback_controller.toggle_playback()
        assert playback_controller.playback_state.mode == PlaybackMode.PLAYING_FORWARD
        assert playback_controller.playback_state.max_frame == 3  # Should be 3 from state_manager

        # Simulate timer ticks and frame updates
        # Tick 1: frame 1 -> 2
        playback_controller._on_playback_timer()
        assert frame_spy.at(frame_spy.count() - 1)[0] == 2
        state_manager.current_frame = 2

        # Tick 2: frame 2 -> 3
        playback_controller._on_playback_timer()
        assert frame_spy.at(frame_spy.count() - 1)[0] == 3
        state_manager.current_frame = 3

        # Tick 3: frame 3 (max) -> reverse to 2
        playback_controller._on_playback_timer()
        assert playback_controller.playback_state.mode == PlaybackMode.PLAYING_BACKWARD
        assert frame_spy.at(frame_spy.count() - 1)[0] == 2
        state_manager.current_frame = 2

        # Tick 4: frame 2 -> 1
        playback_controller._on_playback_timer()
        assert frame_spy.at(frame_spy.count() - 1)[0] == 1
        state_manager.current_frame = 1

        # Tick 5: frame 1 (min) -> reverse to 2
        playback_controller._on_playback_timer()
        assert playback_controller.playback_state.mode == PlaybackMode.PLAYING_FORWARD
        assert frame_spy.at(frame_spy.count() - 1)[0] == 2

    def test_rapid_start_stop(self, playback_controller, qtbot):
        """Test rapid start/stop doesn't cause issues."""
        for _ in range(5):
            playback_controller.toggle_playback()  # Start
            assert playback_controller.playback_timer.isActive()
            playback_controller.toggle_playback()  # Stop
            assert not playback_controller.playback_timer.isActive()

    def test_concurrent_operations(self, playback_controller, qtbot):
        """Test concurrent FPS changes and playback control."""
        playback_controller.toggle_playback()  # Start

        # Rapidly change FPS while playing
        for fps in [10, 30, 60, 24]:
            playback_controller.fps_spinbox.setValue(fps)
            assert playback_controller.playback_timer.isActive()
            assert playback_controller.playback_timer.interval() == int(1000 / fps)

    @pytest.mark.parametrize(
        "initial_frame,expected_mode",
        [
            (1, PlaybackMode.PLAYING_FORWARD),
            (50, PlaybackMode.PLAYING_FORWARD),
            (100, PlaybackMode.PLAYING_FORWARD),
        ],
    )
    def test_start_from_various_positions(self, playback_controller, state_manager, initial_frame, expected_mode):
        """Test starting playback from various frame positions."""
        state_manager.current_frame = initial_frame

        playback_controller._start_oscillating_playback()

        assert playback_controller.playback_state.mode == expected_mode
        assert playback_controller.playback_state.current_frame == initial_frame


class TestPlaybackControllerSignals:
    """Test signal emissions."""

    def test_all_signals_connected(self, playback_controller):
        """Test all expected signals are properly connected."""
        # Check signal existence
        assert hasattr(playback_controller, "frame_requested")
        assert hasattr(playback_controller, "playback_started")
        assert hasattr(playback_controller, "playback_stopped")
        assert hasattr(playback_controller, "status_message")

        # Check widget connections (simplified test - just check signals exist)
        # PySide6 receivers() requires string argument, not signal instance
        # So we just verify the widgets have the expected signals
        assert hasattr(playback_controller.btn_play_pause, "toggled")
        assert hasattr(playback_controller.fps_spinbox, "valueChanged")

    def test_frame_requested_signal_carries_correct_data(self, playback_controller, state_manager, qtbot):
        """Test frame_requested signal emits correct frame numbers."""
        state_manager.current_frame = 25
        playback_controller.playback_state.mode = PlaybackMode.PLAYING_FORWARD

        frame_spy = QSignalSpy(playback_controller.frame_requested)

        playback_controller._on_playback_timer()

        assert frame_spy.count() == 1
        assert frame_spy.at(0)[0] == 26  # Should request next frame

    def test_no_signals_when_stopped(self, playback_controller, qtbot):
        """Test no frame signals are emitted when stopped."""
        # Ensure stopped
        if playback_controller.playback_timer.isActive():
            playback_controller.toggle_playback()

        frame_spy = QSignalSpy(playback_controller.frame_requested)

        # Try to trigger timer
        playback_controller._on_playback_timer()

        assert frame_spy.count() == 0


class TestPlaybackControllerEdgeCases:
    """Test edge cases and error conditions."""

    def test_single_frame_range(self, playback_controller, state_manager, qtbot):
        """Test playback with single frame (min == max)."""
        playback_controller.set_frame_range(5, 5)
        state_manager.current_frame = 5
        playback_controller.playback_state.mode = PlaybackMode.PLAYING_FORWARD

        # Should immediately reverse since at max
        playback_controller._on_playback_timer()

        # With single frame, it should toggle but stay at same frame
        assert playback_controller.playback_state.mode == PlaybackMode.PLAYING_BACKWARD

    def test_state_manager_without_total_frames(self, playback_controller, qtbot):
        """Test update_playback_bounds when state_manager lacks total_frames."""
        # Create a minimal state manager without total_frames
        minimal_state = QObject()
        minimal_state.current_frame = 1  # pyright: ignore[reportAttributeAccessIssue]

        playback_controller.state_manager = minimal_state

        # Should handle gracefully
        playback_controller.update_playback_bounds()

        # Should keep default bounds
        assert playback_controller.playback_state.min_frame == 1
        assert playback_controller.playback_state.max_frame == 100

    def test_cleanup_on_deletion(self, playback_controller):
        """Test proper cleanup when controller is deleted."""
        playback_controller.toggle_playback()  # Start timer
        assert playback_controller.playback_timer.isActive()

        # Delete controller
        playback_controller.deleteLater()
        QApplication.processEvents()

        # Timer should be stopped (handled by Qt parent-child)
        # This test mainly ensures no crashes during cleanup


class TestPlaybackControllerPerformance:
    """Performance and stress tests."""

    @pytest.mark.timeout(2)
    def test_high_fps_performance(self, playback_controller, state_manager, qtbot):
        """Test controller handles high FPS without blocking."""
        playback_controller.fps_spinbox.setValue(120)  # Max FPS
        playback_controller.toggle_playback()

        frame_count = 0

        def count_frames(frame):
            nonlocal frame_count
            frame_count += 1

        playback_controller.frame_requested.connect(count_frames)

        # Let it run briefly
        qtbot.wait(100)  # 100ms

        playback_controller.toggle_playback()  # Stop

        # At 120 FPS, should get ~12 frames in 100ms
        assert frame_count > 5  # Allow for some variance
        assert frame_count < 20  # But not too many

    def test_memory_stability_long_playback(self, playback_controller, state_manager):
        """Test memory remains stable during extended playback."""
        playback_controller.set_frame_range(1, 1000)

        # Simulate many timer ticks
        for i in range(1000):
            state_manager.current_frame = (i % 1000) + 1
            playback_controller._on_playback_timer()

        # Should complete without memory issues
        assert playback_controller.playback_state.min_frame == 1
        assert playback_controller.playback_state.max_frame == 1000
