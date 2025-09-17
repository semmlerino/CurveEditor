"""
End-to-end workflow tests for playback functionality.

This module tests complete user workflows involving playback,
simulating real-world usage scenarios with the oscillating playback controller.
"""

import time

import pytest

from ui.controllers.frame_navigation_controller import FrameNavigationController
from ui.controllers.playback_controller import PlaybackController, PlaybackMode
from ui.state_manager import StateManager


class TestBasicPlaybackWorkflows:
    """Test basic playback workflows that users commonly perform."""

    @pytest.fixture
    def workflow_setup(self, qtbot):
        """Set up complete workflow testing environment."""
        # Create state and controllers
        state_manager = StateManager()
        frame_nav = FrameNavigationController(state_manager)
        playback = PlaybackController(state_manager)

        # Register widgets
        qtbot.addWidget(frame_nav.frame_spinbox)
        qtbot.addWidget(frame_nav.frame_slider)
        qtbot.addWidget(frame_nav.btn_first)
        qtbot.addWidget(frame_nav.btn_last)
        qtbot.addWidget(playback.btn_play_pause)
        qtbot.addWidget(playback.fps_spinbox)

        # Set up initial state
        frame_nav.set_frame_range(1, 100)
        frame_nav.set_frame(1)
        playback.fps_spinbox.setValue(24)

        # Connect playback frame requests to navigation controller (like MainWindow does)
        playback.frame_requested.connect(frame_nav.set_frame)

        return {"state_manager": state_manager, "frame_nav": frame_nav, "playback": playback}

    def test_simple_playback_workflow(self, workflow_setup, qtbot):
        """Test simple start-play-stop workflow."""
        frame_nav = workflow_setup["frame_nav"]
        playback = workflow_setup["playback"]

        # User starts at frame 1
        assert frame_nav.get_current_frame() == 1

        # User clicks play - using real timer with fast interval for testing
        # Set very fast FPS for testing (high speed)
        playback.fps_spinbox.setValue(1000)  # 1000 FPS = 1ms interval

        playback.btn_play_pause.click()
        qtbot.wait(10)

        assert playback.is_playing
        assert playback.playback_timer.isActive()  # Check real timer state

        # Allow some real frame advancement with timer
        qtbot.wait(50)  # Wait for timer to advance a few frames

        # Should have advanced beyond frame 1
        assert frame_nav.get_current_frame() > 1

        # User clicks pause
        playback.btn_play_pause.click()
        qtbot.wait(10)

        assert not playback.is_playing
        assert not playback.playback_timer.isActive()  # Check real timer stopped

    def test_scrubbing_workflow(self, workflow_setup, qtbot):
        """Test manual scrubbing workflow."""
        frame_nav = workflow_setup["frame_nav"]
        playback = workflow_setup["playback"]
        state_manager = workflow_setup["state_manager"]

        # User drags slider to scrub through frames
        test_frames = [1, 25, 50, 75, 100, 75, 50, 25, 1]

        for target_frame in test_frames:
            frame_nav.frame_slider.setValue(target_frame)
            qtbot.wait(10)

            assert frame_nav.get_current_frame() == target_frame
            assert state_manager.current_frame == target_frame

        # Verify playback is not active during scrubbing
        assert not playback.is_playing

    def test_jump_and_play_workflow(self, workflow_setup, qtbot):
        """Test jumping to specific frame and playing."""
        frame_nav = workflow_setup["frame_nav"]
        playback = workflow_setup["playback"]

        # User jumps to middle of sequence
        frame_nav.btn_last.click()
        qtbot.wait(10)
        assert frame_nav.get_current_frame() == 100

        # User jumps back to start
        frame_nav.btn_first.click()
        qtbot.wait(10)
        assert frame_nav.get_current_frame() == 1

        # User types specific frame in spinbox
        frame_nav.frame_spinbox.setValue(42)
        qtbot.wait(10)
        assert frame_nav.get_current_frame() == 42

        # User starts playback from that frame
        # Set fast FPS for testing
        playback.fps_spinbox.setValue(1000)

        playback.toggle_playback()
        qtbot.wait(10)
        assert playback.is_playing
        assert playback.playback_timer.isActive()

        # Allow real timer to advance frames
        qtbot.wait(30)  # Wait for timer to advance a few frames

        # Should have advanced beyond frame 42
        assert frame_nav.get_current_frame() > 42

    def test_oscillating_playback_workflow(self, workflow_setup, qtbot):
        """Test oscillating (ping-pong) playback workflow."""
        frame_nav = workflow_setup["frame_nav"]
        playback = workflow_setup["playback"]

        # Set smaller range for easier testing
        frame_nav.set_frame_range(1, 5)
        frame_nav.set_frame(1)

        # Start playback to activate oscillating mode
        playback.toggle_playback()
        qtbot.wait(10)
        assert playback.is_playing

        # Stop timer for manual frame advancement testing
        playback.playback_timer.stop()

        # Track frame sequence by manually advancing
        frames = []
        for _ in range(10):
            frames.append(frame_nav.get_current_frame())
            playback._advance_frame()

        # Should see pattern like: 1,2,3,4,5,4,3,2,1,2...
        assert frames[0] == 1  # Start
        assert 5 in frames  # Reach end
        # After reaching 5, should reverse
        idx_5 = frames.index(5)
        if idx_5 < len(frames) - 1:
            assert frames[idx_5 + 1] == 4  # Reverses after reaching end

    def test_fps_adjustment_workflow(self, workflow_setup, qtbot):
        """Test FPS adjustment during playback workflow."""
        playback = workflow_setup["playback"]

        # User adjusts FPS before playing
        playback.fps_spinbox.setValue(30)
        assert playback.fps_spinbox.value() == 30

        # Start playback at 30 FPS
        playback.toggle_playback()
        qtbot.wait(10)

        assert playback.is_playing
        assert playback.playback_timer.isActive()
        # Check the timer interval is correct for 30 FPS
        expected_interval = int(1000 / 30)
        assert playback.playback_timer.interval() == expected_interval

        # User adjusts FPS during playback
        playback.fps_spinbox.setValue(60)
        qtbot.wait(10)

        # Timer interval should be updated
        new_interval = int(1000 / 60)
        assert playback.playback_timer.interval() == new_interval
        assert playback.playback_timer.isActive()  # Should still be running


class TestAdvancedWorkflows:
    """Test advanced playback workflows and edge cases."""

    @pytest.fixture
    def advanced_setup(self, qtbot):
        """Set up for advanced workflow testing."""
        state_manager = StateManager()
        frame_nav = FrameNavigationController(state_manager)
        playback = PlaybackController(state_manager)

        # Register essential widgets
        qtbot.addWidget(frame_nav.frame_spinbox)
        qtbot.addWidget(frame_nav.frame_slider)
        qtbot.addWidget(playback.btn_play_pause)

        # Connect playback frame requests to navigation controller
        playback.frame_requested.connect(frame_nav.set_frame)

        return {"state_manager": state_manager, "frame_nav": frame_nav, "playback": playback}

    def test_rapid_start_stop_workflow(self, advanced_setup, qtbot):
        """Test rapid start/stop cycles."""
        frame_nav = advanced_setup["frame_nav"]
        playback = advanced_setup["playback"]

        frame_nav.set_frame_range(1, 100)

        # Rapid toggle cycles using real timer
        for _ in range(5):
            # Start
            playback.toggle_playback()
            qtbot.wait(10)
            assert playback.is_playing
            assert playback.playback_timer.isActive()

            # Quick stop
            playback.toggle_playback()
            qtbot.wait(10)
            assert not playback.is_playing
            assert not playback.playback_timer.isActive()

        # State should remain consistent
        assert not playback.is_playing
        assert frame_nav.get_current_frame() >= 1
        assert frame_nav.get_current_frame() <= 100

    def test_frame_range_change_during_playback(self, advanced_setup, qtbot):
        """Test changing frame range while playing."""
        frame_nav = advanced_setup["frame_nav"]
        playback = advanced_setup["playback"]

        # Start with range 1-100
        frame_nav.set_frame_range(1, 100)
        frame_nav.set_frame(50)

        # Start playback
        playback.toggle_playback()
        qtbot.wait(10)
        assert playback.is_playing
        assert playback.playback_timer.isActive()

        # Change range to smaller (1-30)
        frame_nav.set_frame_range(1, 30)

        # Current frame should be clamped
        assert frame_nav.get_current_frame() == 30

        # Stop timer for manual frame advancement to test logic
        playback.playback_timer.stop()

        # Playback should continue within new range
        playback._advance_frame()

        # In oscillating mode, should reverse at boundary
        assert frame_nav.get_current_frame() <= 30

    def test_keyboard_navigation_workflow(self, advanced_setup, qtbot):
        """Test keyboard-based frame navigation workflow."""
        frame_nav = advanced_setup["frame_nav"]

        frame_nav.set_frame_range(1, 100)
        frame_nav.set_frame(50)

        # Simulate keyboard navigation
        # Note: Actual keyboard events would need MainWindow integration

        # Previous frame (like pressing left arrow)
        frame_nav.btn_prev.click()
        assert frame_nav.get_current_frame() == 49

        # Next frame (like pressing right arrow)
        frame_nav.btn_next.click()
        assert frame_nav.get_current_frame() == 50

        # Jump to first (like pressing Home)
        frame_nav.btn_first.click()
        assert frame_nav.get_current_frame() == 1

        # Jump to last (like pressing End)
        frame_nav.btn_last.click()
        assert frame_nav.get_current_frame() == 100

    def test_precision_frame_stepping(self, advanced_setup, qtbot):
        """Test precise frame-by-frame stepping workflow."""
        frame_nav = advanced_setup["frame_nav"]

        frame_nav.set_frame_range(1, 1000)
        frame_nav.set_frame(500)

        # Precise stepping forward
        for expected in range(501, 506):
            frame_nav.btn_next.click()
            qtbot.wait(10)
            assert frame_nav.get_current_frame() == expected

        # Precise stepping backward
        for expected in range(504, 499, -1):
            frame_nav.btn_prev.click()
            qtbot.wait(10)
            assert frame_nav.get_current_frame() == expected

    def test_state_persistence_workflow(self, advanced_setup, qtbot):
        """Test that playback state persists correctly."""
        frame_nav = advanced_setup["frame_nav"]
        playback = advanced_setup["playback"]
        state_manager = advanced_setup["state_manager"]

        # Set up specific state
        frame_nav.set_frame_range(1, 200)
        frame_nav.set_frame(123)
        playback.fps_spinbox.setValue(48)

        # Verify state
        assert state_manager.current_frame == 123
        assert state_manager.total_frames == 200
        assert playback.fps_spinbox.value() == 48
        assert playback.get_playback_mode() == PlaybackMode.STOPPED  # Initially stopped

        # State should persist through start/stop cycles
        playback.toggle_playback()  # Start
        qtbot.wait(10)
        assert playback.is_playing
        assert playback.playback_timer.isActive()

        playback.toggle_playback()  # Stop
        qtbot.wait(10)
        assert not playback.is_playing
        assert not playback.playback_timer.isActive()

        # Settings should be unchanged
        assert playback.fps_spinbox.value() == 48


class TestErrorHandling:
    """Test error handling in playback workflows."""

    @pytest.fixture
    def error_setup(self, qtbot):
        """Set up for error handling tests."""
        state_manager = StateManager()
        frame_nav = FrameNavigationController(state_manager)
        playback = PlaybackController(state_manager)

        qtbot.addWidget(frame_nav.frame_spinbox)
        qtbot.addWidget(playback.btn_play_pause)

        # Connect playback frame requests to navigation controller
        playback.frame_requested.connect(frame_nav.set_frame)

        return {"state_manager": state_manager, "frame_nav": frame_nav, "playback": playback}

    def test_invalid_frame_recovery(self, error_setup):
        """Test recovery from invalid frame states."""
        frame_nav = error_setup["frame_nav"]
        state_manager = error_setup["state_manager"]

        frame_nav.set_frame_range(1, 100)

        # Try to set invalid frame via navigation
        frame_nav.set_frame(150)  # Beyond max

        # Should be clamped to valid range
        assert frame_nav.get_current_frame() == 100
        assert state_manager.current_frame == 100

        # Try negative frame
        frame_nav.set_frame(-10)
        assert frame_nav.get_current_frame() == 1
        assert state_manager.current_frame == 1

    def test_empty_sequence_handling(self, error_setup, qtbot):
        """Test handling of empty or minimal sequences."""
        frame_nav = error_setup["frame_nav"]
        playback = error_setup["playback"]

        # Single frame sequence
        frame_nav.set_frame_range(1, 1)

        # Should handle playback of single frame
        playback.toggle_playback()
        qtbot.wait(10)
        assert playback.is_playing

        # Stop timer for manual frame advancement
        playback.playback_timer.stop()

        # Advance attempts
        for _ in range(5):
            playback._advance_frame()

        # Should stay at frame 1
        assert frame_nav.get_current_frame() == 1

    def test_concurrent_control_conflict(self, error_setup, qtbot):
        """Test handling of concurrent control attempts."""
        frame_nav = error_setup["frame_nav"]
        playback = error_setup["playback"]
        state_manager = error_setup["state_manager"]

        frame_nav.set_frame_range(1, 100)

        # Start playback
        playback.toggle_playback()
        qtbot.wait(10)
        assert playback.is_playing

        # Stop timer for manual control testing
        playback.playback_timer.stop()

        # Simultaneous updates from multiple sources
        frame_nav.set_frame(25)  # User scrubs
        playback._advance_frame()  # Timer advances
        frame_nav.set_frame(30)  # Another user update

        # Last update wins
        assert frame_nav.get_current_frame() == 30
        assert state_manager.current_frame == 30

        # System should remain stable
        assert frame_nav.frame_spinbox.minimum() == 1
        assert frame_nav.frame_spinbox.maximum() == 100


class TestUserExperience:
    """Test user experience aspects of playback workflows."""

    @pytest.fixture
    def ux_setup(self, qtbot):
        """Set up for UX testing."""
        state_manager = StateManager()
        frame_nav = FrameNavigationController(state_manager)
        playback = PlaybackController(state_manager)

        qtbot.addWidget(frame_nav.frame_spinbox)
        qtbot.addWidget(frame_nav.frame_slider)
        qtbot.addWidget(playback.btn_play_pause)
        qtbot.addWidget(playback.fps_spinbox)

        # Connect playback frame requests to navigation controller
        playback.frame_requested.connect(frame_nav.set_frame)

        return {"state_manager": state_manager, "frame_nav": frame_nav, "playback": playback}

    def test_responsive_controls(self, ux_setup, qtbot):
        """Test that controls remain responsive during playback."""
        frame_nav = ux_setup["frame_nav"]
        playback = ux_setup["playback"]

        frame_nav.set_frame_range(1, 1000)

        # Start playback
        playback.toggle_playback()
        qtbot.wait(10)
        assert playback.is_playing

        # Stop timer for manual control testing
        playback.playback_timer.stop()

        # Controls should respond immediately
        start_time = time.time()
        frame_nav.frame_spinbox.setValue(500)
        response_time = time.time() - start_time

        # Should respond in < 100ms
        assert response_time < 0.1
        assert frame_nav.get_current_frame() == 500

    def test_smooth_scrubbing(self, ux_setup, qtbot):
        """Test smooth scrubbing experience."""
        frame_nav = ux_setup["frame_nav"]

        frame_nav.set_frame_range(1, 100)

        # Simulate smooth scrubbing
        frames = []
        for value in range(1, 101, 5):
            frame_nav.frame_slider.setValue(value)
            frames.append(frame_nav.get_current_frame())
            qtbot.wait(1)  # Small delay for smoothness

        # Should track slider smoothly
        assert frames[0] == 1
        assert frames[-1] in [96, 100]  # Last value depends on range stepping

        # Check monotonic increase
        for i in range(1, len(frames)):
            assert frames[i] >= frames[i - 1]

    def test_visual_feedback_sync(self, ux_setup):
        """Test that visual feedback stays synchronized."""
        frame_nav = ux_setup["frame_nav"]
        state_manager = ux_setup["state_manager"]

        frame_nav.set_frame_range(1, 50)

        test_values = [1, 10, 25, 40, 50]

        for value in test_values:
            frame_nav.set_frame(value)

            # All displays should match
            assert frame_nav.frame_spinbox.value() == value
            assert frame_nav.frame_slider.value() == value
            assert state_manager.current_frame == value

    def test_predictable_playback_behavior(self, ux_setup, qtbot):
        """Test that playback behaves predictably for users."""
        frame_nav = ux_setup["frame_nav"]
        playback = ux_setup["playback"]

        frame_nav.set_frame_range(1, 10)

        # Ensure playback bounds are set
        playback.set_frame_range(1, 10)

        # Test oscillating behavior (the only mode)
        frame_nav.set_frame(8)

        playback.playback_state.mode = PlaybackMode.PLAYING_FORWARD

        expected_sequence = [8, 9, 10, 9, 8, 7]  # Forward then backward
        actual_sequence = [frame_nav.get_current_frame()]

        for _ in range(len(expected_sequence) - 1):
            playback._advance_frame()
            actual_sequence.append(frame_nav.get_current_frame())

        assert actual_sequence == expected_sequence
