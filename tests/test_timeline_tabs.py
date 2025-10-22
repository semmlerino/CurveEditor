#!/usr/bin/env python
"""
Tests for timeline functionality.

Note: These tests have been adapted to match the actual MainWindow implementation.
The MainWindow uses frame_spinbox and frame_slider for timeline control,
not individual clickable frame tabs.

Following Qt testing best practices:
- Use real components with mocked dependencies
- Test with available qapp fixture since pytest-qt is not available
- Test signals and events manually
- Mock only external dependencies
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

from unittest.mock import Mock, patch

import pytest

from stores.application_state import get_application_state
from ui.file_operations import FileOperations
from ui.main_window import MainWindow


class MockServiceFacade:
    """Mock service facade with minimal implementation."""

    def __init__(self):
        self.confirm_action = Mock(return_value=True)
        self.load_track_data = Mock(return_value=[])
        self.save_track_data = Mock(return_value=True)
        self.undo = Mock()
        self.redo = Mock()
        # Add analyze_curve_bounds method that returns a bounds analysis object
        self.analyze_curve_bounds = Mock(
            return_value={
                "count": 0,  # No points initially
                "bounds": {"min_x": 0.0, "max_x": 1920.0, "min_y": 0.0, "max_y": 1080.0},
                "min_frame": 1,
                "max_frame": 37,
                "frame_count": 37,
            }
        )


class TestTimelineControls:
    """Test suite for timeline controls functionality."""

    @pytest.fixture
    def service_facade(self):
        """Create mock service facade."""
        return MockServiceFacade()

    @pytest.fixture
    def main_window(self, qapp, qtbot, service_facade):
        """Create a real MainWindow with mocked dependencies."""
        # Mock the auto-load to prevent file access
        with patch.object(FileOperations, "load_burger_data_async"):
            window = MainWindow()
            window.services = service_facade

            # Set up proper frame range since we're not loading data
            if window.frame_spinbox:
                window.frame_spinbox.setMaximum(37)  # Default 37 frames
            if window.frame_slider:
                window.frame_slider.setMaximum(37)
            if window.total_frames_label:
                window.total_frames_label.setText("37")
            # Phase 4 TODO: Remove StateManager total_frames setter (deprecated pattern)
            from stores.application_state import get_application_state

            get_application_state().set_image_files([f"frame_{i:04d}.png" for i in range(1, 38)])

            qtbot.addWidget(window)
            yield window

    def test_frame_spinbox_functionality(self, qapp, main_window):
        """Test frame spinbox functionality instead of individual tab clicks."""
        # Verify frame_spinbox exists and is initialized
        assert hasattr(main_window, "frame_spinbox")
        assert main_window.frame_spinbox is not None

        # Test setting frame via spinbox
        target_frame = 10
        main_window.frame_spinbox.setValue(target_frame)
        qapp.processEvents()

        # Check frame was updated
        assert main_window.frame_spinbox.value() == target_frame

        # The frame navigation controller should have updated the state
        # through its valueChanged handler
        assert get_application_state().current_frame == target_frame

        # Test another frame
        target_frame_2 = 15
        main_window.frame_spinbox.setValue(target_frame_2)
        # Controller handles synchronization automatically
        assert main_window.frame_spinbox.value() == target_frame_2
        assert get_application_state().current_frame == target_frame_2

    def test_frame_spinbox_slider_synchronization(self, main_window):
        """Test that frame spinbox and slider stay synchronized."""
        # Test that setting spinbox updates slider
        target_frame = 15
        main_window.frame_spinbox.setValue(target_frame)

        # The frame navigation controller handles synchronization automatically
        # through the valueChanged signal

        # Check that slider is synchronized
        assert main_window.frame_slider.value() == target_frame

        # Test that setting slider updates spinbox
        target_frame_2 = 20
        main_window.frame_slider.setValue(target_frame_2)
        # The frame navigation controller handles synchronization automatically
        # Check that spinbox is synchronized
        assert main_window.frame_spinbox.value() == target_frame_2

    def test_frame_navigation_shortcuts(self, qapp, main_window):
        """Test keyboard shortcuts for frame navigation."""
        # Set initial frame
        main_window.frame_spinbox.setValue(20)

        # Test next frame (Right arrow) - call through controller
        main_window.timeline_controller._on_next_frame()
        assert main_window.frame_spinbox.value() == 21

        # Test previous frame (Left arrow)
        main_window.timeline_controller._on_prev_frame()
        assert main_window.frame_spinbox.value() == 20

        # Test first frame (Home)
        main_window.timeline_controller._on_first_frame()
        assert main_window.frame_spinbox.value() == 1

        # Test last frame (End)
        main_window.timeline_controller._on_last_frame()
        assert main_window.frame_spinbox.value() == 37  # Default max

    def test_frame_bounds_checking(self, main_window):
        """Test that frame navigation respects bounds."""
        # Test lower bound
        main_window.frame_spinbox.setValue(1)
        main_window.timeline_controller._on_prev_frame()
        assert main_window.frame_spinbox.value() == 1  # Should stay at 1

        # Test upper bound
        max_frame = main_window.frame_spinbox.maximum()
        main_window.frame_spinbox.setValue(max_frame)
        main_window.timeline_controller._on_next_frame()
        assert main_window.frame_spinbox.value() == max_frame  # Should stay at max

    def test_timeline_state_persistence(self, main_window):
        """Test that timeline state is properly synchronized with state manager."""
        # Test frame synchronization via spinbox instead of tabs
        target_frame = 25
        main_window.frame_spinbox.setValue(target_frame)

        # The frame navigation controller handles the update automatically

        # Check ApplicationState is updated
        assert get_application_state().current_frame == target_frame

        # Check frame spinbox is updated
        assert main_window.frame_spinbox.value() == target_frame

        # Check frame slider is synchronized
        assert main_window.frame_slider.value() == target_frame
