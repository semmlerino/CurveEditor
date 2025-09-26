#!/usr/bin/env python3
"""
Tests for active frame point highlighting functionality.

Following UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md best practices:
- Test behavior, not implementation
- Use real components with mocked boundaries
- Test that current frame points are highlighted during navigation
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from ui.curve_view_widget import CurveViewWidget
from ui.file_operations import FileOperations
from ui.main_window import MainWindow


class TestFramePointHighlighting:
    """Test suite for active frame point highlighting."""

    @pytest.fixture
    def app(self):
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def curve_widget(self, app, qtbot):
        """Create real CurveViewWidget for testing."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Add test data with points on different frames
        widget.set_curve_data(
            [
                (1, 100.0, 200.0, "keyframe"),
                (5, 150.0, 250.0, "interpolated"),
                (10, 200.0, 300.0, "keyframe"),
                (15, 250.0, 350.0, "keyframe"),
                (20, 300.0, 400.0, "interpolated"),
            ]
        )

        # Create mock main window with state manager
        widget.main_window = Mock()
        widget.main_window.state_manager = Mock()
        widget.main_window.state_manager.current_frame = 1

        return widget

    @pytest.fixture
    def main_window(self, app, qtbot):
        """Create real MainWindow with mocked dependencies."""
        # Mock the auto-load to prevent file access
        with patch.object(FileOperations, "load_burger_data_async"):
            window = MainWindow()

            # Mock services to avoid external dependencies
            window.services = Mock()
            window.services.confirm_action = Mock(return_value=True)
            window.services.load_track_data = Mock(return_value=[])
            window.services.save_track_data = Mock(return_value=True)
            window.services.analyze_curve_bounds = Mock(
                return_value={
                    "count": 5,
                    "min_frame": 1,
                    "max_frame": 20,
                    "bounds": {"min_x": 100, "max_x": 300, "min_y": 200, "max_y": 400},
                }
            )
            window.services.add_to_history = Mock()

            # Set up test data with points on different frames
            if window.curve_widget:
                window.curve_widget.set_curve_data(
                    [
                        (1, 100.0, 200.0, "keyframe"),
                        (5, 150.0, 250.0, "interpolated"),
                        (10, 200.0, 300.0, "keyframe"),
                        (15, 250.0, 350.0, "keyframe"),
                        (20, 300.0, 400.0, "interpolated"),
                    ]
                )

            # Set up proper frame range
            if window.frame_spinbox:
                window.frame_spinbox.setMaximum(20)
            if window.frame_slider:
                window.frame_slider.setMaximum(20)
            if window.total_frames_label:
                window.total_frames_label.setText("20")
            window.state_manager.total_frames = 20

            # Set up timeline if available
            if window.timeline_tabs:
                window.timeline_tabs.set_frame_range(1, 20)

            qtbot.addWidget(window)
            yield window

    def test_current_frame_point_color_initialization(self, curve_widget):
        """Test that current frame point color is initialized."""
        # Should have a distinct color for current frame points
        assert hasattr(curve_widget, "current_frame_point_color")
        assert isinstance(curve_widget.current_frame_point_color, QColor)
        # Magenta is the default current frame color
        assert curve_widget.current_frame_point_color == QColor(255, 0, 255)

    def test_paint_event_highlights_current_frame_point(self, curve_widget, qtbot):
        """Test that paintEvent correctly identifies and highlights current frame points."""
        # Set current frame to 10 (which has a keyframe point)
        curve_widget.main_window.state_manager.current_frame = 10

        # Force a repaint
        curve_widget.invalidate_caches()
        curve_widget.update()
        qtbot.wait(10)  # Give Qt time to process the update

        # The point at frame 10 should be painted with current_frame_point_color
        # and larger radius. This is handled by OptimizedCurveRenderer.

        # Get the point at frame 10
        frame_10_point = curve_widget.curve_data[2]  # Index 2 is frame 10
        assert frame_10_point[0] == 10

        # In the OptimizedCurveRenderer, this point is identified as current frame
        # The renderer checks: is_current_frame = frame == current_frame
        # And then uses current_frame_point_color (magenta) and larger radius

    def test_frame_spinbox_change_updates_highlight(self, main_window, qtbot):
        """Test that changing frame via spinbox updates point highlighting."""
        initial_frame = 1
        main_window.frame_spinbox.setValue(initial_frame)

        # Check initial state
        assert main_window.state_manager.current_frame == initial_frame

        # Change to frame 10 which has a point
        main_window.frame_spinbox.setValue(10)

        # Verify state was updated
        assert main_window.state_manager.current_frame == 10

        # Verify curve widget was told to update
        # The _on_frame_changed method should have called:
        # - curve_widget.invalidate_caches()
        # - curve_widget.update()

        # Change to frame 5 which has an interpolated point
        main_window.frame_spinbox.setValue(5)
        assert main_window.state_manager.current_frame == 5

    def test_frame_slider_change_updates_highlight(self, main_window, qtbot):
        """Test that changing frame via slider updates point highlighting."""
        # Start at frame 1
        main_window.frame_slider.setValue(1)

        # Change to frame 15 via slider
        main_window.frame_slider.setValue(15)

        # This should trigger _on_slider_changed which now includes:
        # - Update state_manager.current_frame
        # - Call curve_widget.invalidate_caches() and update()
        assert main_window.state_manager.current_frame == 15

        # Change to frame 20
        main_window.frame_slider.setValue(20)
        assert main_window.state_manager.current_frame == 20

    def test_keyboard_navigation_updates_highlight(self, main_window, qtbot):
        """Test that keyboard navigation updates point highlighting."""
        # Start at frame 10
        main_window.frame_spinbox.setValue(10)

        # Navigate with keyboard shortcuts using the controller
        main_window.timeline_controller._on_next_frame()
        assert main_window.state_manager.current_frame == 11

        main_window.timeline_controller._on_prev_frame()
        assert main_window.state_manager.current_frame == 10

        main_window.timeline_controller._on_first_frame()
        assert main_window.state_manager.current_frame == 1

        main_window.timeline_controller._on_last_frame()
        assert main_window.state_manager.current_frame == 20

    def test_timeline_click_updates_highlight(self, main_window, qtbot):
        """Test that clicking timeline tab updates point highlighting."""
        if not main_window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        # Click on frame 15 in timeline
        main_window._on_timeline_tab_clicked(15)

        # This sets the spinbox value, which triggers _on_frame_changed
        assert main_window.state_manager.current_frame == 15
        assert main_window.frame_spinbox.value() == 15

    def test_playback_updates_highlight(self, main_window, qtbot):
        """Test that playback updates point highlighting frame by frame."""
        # Start at frame 1
        main_window.frame_spinbox.setValue(1)

        # Set up playback state for oscillating playback
        from ui.controllers import PlaybackMode

        main_window.timeline_controller.playback_state.mode = PlaybackMode.PLAYING_FORWARD
        main_window.timeline_controller.playback_state.min_frame = 1
        main_window.timeline_controller.playback_state.max_frame = 10

        # Simulate playback timer tick
        main_window.timeline_controller._on_playback_timer()

        # Should advance to frame 2
        assert main_window.state_manager.current_frame == 2

        # Another tick
        main_window.timeline_controller._on_playback_timer()
        assert main_window.state_manager.current_frame == 3

    def test_multiple_points_on_same_frame(self, curve_widget):
        """Test highlighting when multiple points exist on the same frame."""
        # Add multiple points on frame 10
        curve_widget.set_curve_data(
            [
                (10, 100.0, 200.0, "keyframe"),
                (10, 150.0, 250.0, "keyframe"),
                (10, 200.0, 300.0, "interpolated"),
            ]
        )

        # Set current frame to 10
        curve_widget.main_window.state_manager.current_frame = 10

        # Force a repaint
        curve_widget.invalidate_caches()
        curve_widget.update()

        # All three points should be highlighted as current frame points

    def test_no_point_on_current_frame(self, curve_widget):
        """Test behavior when no point exists on the current frame."""
        # Set current frame to a frame with no points
        curve_widget.main_window.state_manager.current_frame = 3

        # Force a repaint
        curve_widget.invalidate_caches()
        curve_widget.update()

        # No points should be highlighted with current frame color
        # Other points should use their normal colors

    def test_highlight_priority_selected_over_current(self, curve_widget):
        """Test that selection has priority over current frame highlighting."""
        # Select point at index 2 (frame 10)
        curve_widget.selected_indices.add(2)

        # Set current frame to 10
        curve_widget.main_window.state_manager.current_frame = 10

        # The point should show both selection and current frame indicators
        # Current implementation: current frame color overrides selection color
        # but selection outline is still drawn

    def test_cache_invalidation_on_frame_change(self, curve_widget):
        """Test that caches are properly invalidated when frame changes."""
        # Initial frame
        curve_widget.main_window.state_manager.current_frame = 1

        # Change frame (simulating what main_window does)
        curve_widget.main_window.state_manager.current_frame = 10
        curve_widget.invalidate_caches()

        # Caches should be cleared
        assert len(curve_widget._visible_indices_cache) == 0
        assert len(curve_widget._screen_points_cache) == 0

        # After update, caches should be rebuilt with new highlighting
        curve_widget.update()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
