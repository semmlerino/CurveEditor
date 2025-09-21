#!/usr/bin/env python
"""
Comprehensive tests for FrameNavigationController.

Tests frame navigation, spinbox/slider sync, navigation buttons, and signal management.
Following UNIFIED_TESTING_GUIDE principles: real components, behavior testing.
"""

import pytest
from PySide6.QtCore import QObject
from PySide6.QtTest import QSignalSpy

from ui.controllers import FrameNavigationController


class MockStateManager(QObject):
    """Minimal test double for StateManager with only what FrameNavigationController needs."""

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
def frame_nav_controller(qtbot, state_manager):
    """Create a FrameNavigationController with test dependencies."""
    controller = FrameNavigationController(state_manager)
    qtbot.addWidget(controller.frame_spinbox)
    qtbot.addWidget(controller.frame_slider)
    qtbot.addWidget(controller.btn_first)
    qtbot.addWidget(controller.btn_prev)
    qtbot.addWidget(controller.btn_next)
    qtbot.addWidget(controller.btn_last)
    return controller


class TestFrameNavigationControllerInitialization:
    """Test FrameNavigationController initialization and default state."""

    def test_initialization_default_state(self, frame_nav_controller):
        """Test controller initializes with correct default state."""
        assert frame_nav_controller.frame_spinbox.value() == 1
        assert frame_nav_controller.frame_spinbox.minimum() == 1
        assert frame_nav_controller.frame_spinbox.maximum() == 1000

        assert frame_nav_controller.frame_slider.value() == 1
        assert frame_nav_controller.frame_slider.minimum() == 1
        assert frame_nav_controller.frame_slider.maximum() == 1000

    def test_widgets_created(self, frame_nav_controller):
        """Test all navigation widgets are created."""
        assert frame_nav_controller.frame_spinbox is not None
        assert frame_nav_controller.frame_slider is not None
        assert frame_nav_controller.btn_first is not None
        assert frame_nav_controller.btn_prev is not None
        assert frame_nav_controller.btn_next is not None
        assert frame_nav_controller.btn_last is not None

    def test_tooltips_set(self, frame_nav_controller):
        """Test tooltips are properly set."""
        assert frame_nav_controller.frame_spinbox.toolTip() == "Current frame"
        assert frame_nav_controller.frame_slider.toolTip() == "Scrub through frames"
        assert frame_nav_controller.btn_first.toolTip() == "First frame"
        assert frame_nav_controller.btn_prev.toolTip() == "Previous frame"
        assert frame_nav_controller.btn_next.toolTip() == "Next frame"
        assert frame_nav_controller.btn_last.toolTip() == "Last frame"


class TestFrameNavigationSpinboxSliderSync:
    """Test spinbox and slider synchronization."""

    def test_spinbox_updates_slider(self, frame_nav_controller, qtbot):
        """Test changing spinbox updates slider."""
        frame_changed_spy = QSignalSpy(frame_nav_controller.frame_changed)

        # Change spinbox
        frame_nav_controller.frame_spinbox.setValue(50)

        # Check slider updated
        assert frame_nav_controller.frame_slider.value() == 50
        # Check signal emitted
        assert frame_changed_spy.count() == 1
        assert frame_changed_spy.at(0)[0] == 50

    def test_slider_updates_spinbox(self, frame_nav_controller, qtbot):
        """Test changing slider updates spinbox."""
        frame_changed_spy = QSignalSpy(frame_nav_controller.frame_changed)

        # Change slider
        frame_nav_controller.frame_slider.setValue(75)

        # Check spinbox updated
        assert frame_nav_controller.frame_spinbox.value() == 75
        # Check signal emitted
        assert frame_changed_spy.count() == 1
        assert frame_changed_spy.at(0)[0] == 75

    def test_no_signal_feedback_loop(self, frame_nav_controller, qtbot):
        """Test that updating one widget doesn't cause signal feedback loops."""
        frame_changed_spy = QSignalSpy(frame_nav_controller.frame_changed)

        # Change spinbox
        frame_nav_controller.frame_spinbox.setValue(25)

        # Should emit exactly one signal, not multiple due to feedback
        assert frame_changed_spy.count() == 1

    def test_slider_spinbox_stay_synchronized(self, frame_nav_controller):
        """Test slider and spinbox stay synchronized after multiple changes."""
        test_values = [1, 50, 100, 25, 75, 1]

        for value in test_values:
            frame_nav_controller.frame_spinbox.setValue(value)
            assert frame_nav_controller.frame_slider.value() == value

        for value in test_values:
            frame_nav_controller.frame_slider.setValue(value)
            assert frame_nav_controller.frame_spinbox.value() == value


class TestFrameNavigationButtons:
    """Test navigation button functionality."""

    def test_first_frame_button(self, frame_nav_controller, qtbot):
        """Test first frame button jumps to frame 1."""
        # Start at a different frame
        frame_nav_controller.set_frame(50)
        assert frame_nav_controller.frame_spinbox.value() == 50

        frame_changed_spy = QSignalSpy(frame_nav_controller.frame_changed)

        # Click first frame
        frame_nav_controller.btn_first.click()

        assert frame_nav_controller.frame_spinbox.value() == 1
        assert frame_nav_controller.frame_slider.value() == 1
        assert frame_changed_spy.count() == 1
        assert frame_changed_spy.at(0)[0] == 1

    def test_last_frame_button(self, frame_nav_controller, qtbot):
        """Test last frame button jumps to maximum frame."""
        frame_nav_controller.set_frame_range(1, 100)
        frame_nav_controller.set_frame(50)

        frame_changed_spy = QSignalSpy(frame_nav_controller.frame_changed)

        # Click last frame
        frame_nav_controller.btn_last.click()

        assert frame_nav_controller.frame_spinbox.value() == 100
        assert frame_nav_controller.frame_slider.value() == 100
        assert frame_changed_spy.count() == 1
        assert frame_changed_spy.at(0)[0] == 100

    def test_prev_frame_button(self, frame_nav_controller, qtbot):
        """Test previous frame button decrements frame."""
        frame_nav_controller.set_frame(50)

        frame_changed_spy = QSignalSpy(frame_nav_controller.frame_changed)

        # Click prev frame
        frame_nav_controller.btn_prev.click()

        assert frame_nav_controller.frame_spinbox.value() == 49
        assert frame_changed_spy.count() == 1
        assert frame_changed_spy.at(0)[0] == 49

    def test_next_frame_button(self, frame_nav_controller, qtbot):
        """Test next frame button increments frame."""
        frame_nav_controller.set_frame(50)

        frame_changed_spy = QSignalSpy(frame_nav_controller.frame_changed)

        # Click next frame
        frame_nav_controller.btn_next.click()

        assert frame_nav_controller.frame_spinbox.value() == 51
        assert frame_changed_spy.count() == 1
        assert frame_changed_spy.at(0)[0] == 51

    def test_prev_frame_at_minimum(self, frame_nav_controller):
        """Test previous frame button does nothing at frame 1."""
        frame_nav_controller.set_frame(1)

        # Click prev frame
        frame_nav_controller.btn_prev.click()

        # Should stay at 1
        assert frame_nav_controller.frame_spinbox.value() == 1

    def test_next_frame_at_maximum(self, frame_nav_controller):
        """Test next frame button does nothing at maximum frame."""
        frame_nav_controller.set_frame_range(1, 100)
        frame_nav_controller.set_frame(100)

        # Click next frame
        frame_nav_controller.btn_next.click()

        # Should stay at 100
        assert frame_nav_controller.frame_spinbox.value() == 100


class TestFrameNavigationRangeManagement:
    """Test frame range management."""

    def test_set_frame_range(self, frame_nav_controller):
        """Test setting frame range updates both widgets."""
        frame_nav_controller.set_frame_range(10, 200)

        assert frame_nav_controller.frame_spinbox.minimum() == 10
        assert frame_nav_controller.frame_spinbox.maximum() == 200
        assert frame_nav_controller.frame_slider.minimum() == 10
        assert frame_nav_controller.frame_slider.maximum() == 200

    def test_frame_clamped_when_range_changes(self, frame_nav_controller):
        """Test current frame is clamped when range changes."""
        # Set initial frame
        frame_nav_controller.set_frame(150)

        # Reduce range
        frame_nav_controller.set_frame_range(1, 100)

        # Frame should be clamped to new maximum
        assert frame_nav_controller.frame_spinbox.value() == 100

    def test_frame_adjusted_to_new_minimum(self, frame_nav_controller):
        """Test frame adjusts to new minimum when range changes."""
        frame_nav_controller.set_frame(5)

        # Increase minimum
        frame_nav_controller.set_frame_range(20, 100)

        # Frame should adjust to new minimum
        assert frame_nav_controller.frame_spinbox.value() == 20

    def test_set_frame_clamps_to_range(self, frame_nav_controller):
        """Test set_frame clamps values to valid range."""
        frame_nav_controller.set_frame_range(10, 50)

        # Try to set below minimum
        frame_nav_controller.set_frame(5)
        assert frame_nav_controller.frame_spinbox.value() == 10

        # Try to set above maximum
        frame_nav_controller.set_frame(100)
        assert frame_nav_controller.frame_spinbox.value() == 50


class TestFrameNavigationStateIntegration:
    """Test integration with StateManager."""

    def test_frame_updates_state_manager(self, frame_nav_controller, state_manager):
        """Test changing frame updates state manager."""
        frame_nav_controller.set_frame(42)

        assert state_manager.current_frame == 42

    def test_spinbox_updates_state_manager(self, frame_nav_controller, state_manager):
        """Test spinbox change updates state manager."""
        frame_nav_controller.frame_spinbox.setValue(33)

        assert state_manager.current_frame == 33

    def test_slider_updates_state_manager(self, frame_nav_controller, state_manager):
        """Test slider change updates state manager."""
        frame_nav_controller.frame_slider.setValue(77)

        assert state_manager.current_frame == 77

    def test_navigation_buttons_update_state(self, frame_nav_controller, state_manager):
        """Test navigation buttons update state manager."""
        frame_nav_controller.set_frame(50)

        frame_nav_controller.btn_prev.click()
        assert state_manager.current_frame == 49

        frame_nav_controller.btn_next.click()
        assert state_manager.current_frame == 50

        frame_nav_controller.btn_first.click()
        assert state_manager.current_frame == 1


class TestFrameNavigationSignals:
    """Test signal emissions."""

    def test_frame_changed_signal_data(self, frame_nav_controller, qtbot):
        """Test frame_changed signal carries correct frame number."""
        frame_spy = QSignalSpy(frame_nav_controller.frame_changed)

        frame_nav_controller.set_frame(99)

        assert frame_spy.count() == 1
        assert frame_spy.at(0)[0] == 99

    def test_status_message_signal(self, frame_nav_controller, qtbot):
        """Test status_message signal is emitted with correct format."""
        frame_nav_controller.set_frame_range(1, 150)

        status_spy = QSignalSpy(frame_nav_controller.status_message)

        frame_nav_controller.set_frame(75)

        assert status_spy.count() >= 1
        # Check the last status message
        last_message = status_spy.at(status_spy.count() - 1)[0]
        assert "Frame 75/150" in last_message

    def test_multiple_frame_changes(self, frame_nav_controller, qtbot):
        """Test multiple frame changes emit correct signals."""
        frame_spy = QSignalSpy(frame_nav_controller.frame_changed)

        frames = [10, 20, 30, 40, 50]
        for frame in frames:
            frame_nav_controller.set_frame(frame)

        assert frame_spy.count() == len(frames)
        for i, frame in enumerate(frames):
            assert frame_spy.at(i)[0] == frame


class TestFrameNavigationUpdateDisplay:
    """Test update_frame_display functionality."""

    def test_update_display_without_signals(self, frame_nav_controller, qtbot):
        """Test update_frame_display doesn't emit signals."""
        frame_spy = QSignalSpy(frame_nav_controller.frame_changed)

        frame_nav_controller.update_frame_display(88, update_state=False)

        # UI should update but no signals emitted
        assert frame_nav_controller.frame_spinbox.value() == 88
        assert frame_nav_controller.frame_slider.value() == 88
        assert frame_spy.count() == 0

    def test_update_display_with_state(self, frame_nav_controller, state_manager, qtbot):
        """Test update_frame_display can optionally update state."""
        frame_spy = QSignalSpy(frame_nav_controller.frame_changed)

        # Update display with state
        frame_nav_controller.update_frame_display(66, update_state=True)

        assert frame_nav_controller.frame_spinbox.value() == 66
        assert frame_nav_controller.frame_slider.value() == 66
        assert state_manager.current_frame == 66
        assert frame_spy.count() == 0  # Still no signal

    def test_update_display_without_state(self, frame_nav_controller, state_manager):
        """Test update_frame_display without updating state."""
        state_manager.current_frame = 25

        frame_nav_controller.update_frame_display(55, update_state=False)

        assert frame_nav_controller.frame_spinbox.value() == 55
        assert frame_nav_controller.frame_slider.value() == 55
        assert state_manager.current_frame == 25  # State unchanged


class TestFrameNavigationEdgeCases:
    """Test edge cases and error conditions."""

    def test_get_current_frame(self, frame_nav_controller):
        """Test get_current_frame returns correct value."""
        frame_nav_controller.set_frame(42)
        assert frame_nav_controller.get_current_frame() == 42

        frame_nav_controller.frame_spinbox.setValue(17)
        assert frame_nav_controller.get_current_frame() == 17

    def test_single_frame_range(self, frame_nav_controller):
        """Test behavior with single-frame range."""
        frame_nav_controller.set_frame_range(5, 5)

        assert frame_nav_controller.frame_spinbox.value() == 5
        assert frame_nav_controller.frame_spinbox.minimum() == 5
        assert frame_nav_controller.frame_spinbox.maximum() == 5

        # Navigation should have no effect
        frame_nav_controller.btn_next.click()
        assert frame_nav_controller.frame_spinbox.value() == 5

        frame_nav_controller.btn_prev.click()
        assert frame_nav_controller.frame_spinbox.value() == 5

    def test_large_frame_range(self, frame_nav_controller):
        """Test with large frame ranges."""
        frame_nav_controller.set_frame_range(1, 10000)

        frame_nav_controller.set_frame(5000)
        assert frame_nav_controller.frame_spinbox.value() == 5000
        assert frame_nav_controller.frame_slider.value() == 5000

        frame_nav_controller.btn_last.click()
        assert frame_nav_controller.frame_spinbox.value() == 10000

    def test_negative_frame_attempt(self, frame_nav_controller):
        """Test that negative frames are clamped to minimum."""
        frame_nav_controller.set_frame(-10)

        assert frame_nav_controller.frame_spinbox.value() == 1

    def test_rapid_navigation(self, frame_nav_controller):
        """Test rapid navigation doesn't cause issues."""
        # Rapid button clicks
        for _ in range(20):
            frame_nav_controller.btn_next.click()

        current = frame_nav_controller.frame_spinbox.value()
        assert current == 21  # Started at 1, clicked 20 times

        # Rapid prev clicks
        for _ in range(30):
            frame_nav_controller.btn_prev.click()

        assert frame_nav_controller.frame_spinbox.value() == 1  # Clamped at minimum


class TestFrameNavigationIntegration:
    """Integration tests for frame navigation."""

    def test_full_navigation_workflow(self, frame_nav_controller, state_manager, qtbot):
        """Test complete navigation workflow."""
        frame_nav_controller.set_frame_range(1, 100)

        # Start at first
        frame_nav_controller.btn_first.click()
        assert frame_nav_controller.get_current_frame() == 1

        # Navigate forward
        for _ in range(5):
            frame_nav_controller.btn_next.click()
        assert frame_nav_controller.get_current_frame() == 6

        # Jump to last
        frame_nav_controller.btn_last.click()
        assert frame_nav_controller.get_current_frame() == 100

        # Navigate backward
        for _ in range(3):
            frame_nav_controller.btn_prev.click()
        assert frame_nav_controller.get_current_frame() == 97

        # Set specific frame
        frame_nav_controller.set_frame(50)
        assert frame_nav_controller.get_current_frame() == 50
        assert state_manager.current_frame == 50

    def test_mixed_input_methods(self, frame_nav_controller):
        """Test mixing different input methods."""
        # Spinbox input
        frame_nav_controller.frame_spinbox.setValue(25)
        assert frame_nav_controller.get_current_frame() == 25

        # Slider input
        frame_nav_controller.frame_slider.setValue(75)
        assert frame_nav_controller.get_current_frame() == 75

        # Button navigation
        frame_nav_controller.btn_prev.click()
        assert frame_nav_controller.get_current_frame() == 74

        # Programmatic
        frame_nav_controller.set_frame(50)
        assert frame_nav_controller.get_current_frame() == 50

    def test_consistency_after_range_changes(self, frame_nav_controller):
        """Test widgets stay consistent after multiple range changes."""
        ranges = [(1, 100), (10, 50), (1, 1000), (20, 30)]

        for min_f, max_f in ranges:
            frame_nav_controller.set_frame_range(min_f, max_f)

            # Verify consistency
            assert frame_nav_controller.frame_spinbox.minimum() == min_f
            assert frame_nav_controller.frame_spinbox.maximum() == max_f
            assert frame_nav_controller.frame_slider.minimum() == min_f
            assert frame_nav_controller.frame_slider.maximum() == max_f

            # Verify current frame is within range
            current = frame_nav_controller.get_current_frame()
            assert min_f <= current <= max_f

    def test_external_frame_updates(self, frame_nav_controller, qtbot):
        """Test handling external frame updates (e.g., from playback)."""
        frame_spy = QSignalSpy(frame_nav_controller.frame_changed)

        # Simulate external updates (like from playback controller)
        for frame in range(1, 11):
            frame_nav_controller.update_frame_display(frame, update_state=True)

        # Should not emit signals for external updates
        assert frame_spy.count() == 0

        # But UI should be updated
        assert frame_nav_controller.get_current_frame() == 10


class TestFrameNavigationPerformance:
    """Performance tests for frame navigation."""

    @pytest.mark.timeout(1)
    def test_rapid_frame_updates(self, frame_nav_controller):
        """Test controller handles rapid frame updates efficiently."""
        # Simulate rapid playback updates
        for frame in range(1, 501):
            frame_nav_controller.update_frame_display(frame, update_state=False)

        assert frame_nav_controller.get_current_frame() == 500

    def test_signal_blocking_efficiency(self, frame_nav_controller, qtbot):
        """Test signal blocking prevents unnecessary emissions."""
        frame_spy = QSignalSpy(frame_nav_controller.frame_changed)

        # Many updates using update_frame_display
        for i in range(100):
            frame_nav_controller.update_frame_display(i, update_state=False)

        # No signals should be emitted
        assert frame_spy.count() == 0

    def test_memory_stability(self, frame_nav_controller, state_manager):
        """Test memory stability with many operations."""
        # Perform many different operations
        for _ in range(100):
            frame_nav_controller.set_frame_range(1, 1000)
            frame_nav_controller.set_frame(500)
            frame_nav_controller.btn_next.click()
            frame_nav_controller.btn_prev.click()
            frame_nav_controller.frame_slider.setValue(250)
            frame_nav_controller.frame_spinbox.setValue(750)

        # Should complete without issues
        assert frame_nav_controller.get_current_frame() == 750
        assert state_manager.current_frame == 750
