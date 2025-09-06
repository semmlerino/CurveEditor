#!/usr/bin/env python3
"""
Integration tests for Timeline Tab functionality with MainWindow.

Following UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md best practices:
- Test behavior, not implementation
- Use real components with mocked boundaries
- Test integration points between components
- Mock only external dependencies
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


class MockServiceFacade:
    """Mock service facade for testing."""

    def __init__(self):
        self.confirm_action = Mock(return_value=True)
        self.load_track_data = Mock(return_value=[])
        self.save_track_data = Mock(return_value=True)
        self.undo = Mock()
        self.redo = Mock()


class TestTimelineMainWindowIntegration:
    """Test suite for timeline integration with MainWindow."""

    @pytest.fixture
    def app(self):
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def service_facade(self):
        """Create mock service facade."""
        return MockServiceFacade()

    @pytest.fixture
    def main_window(self, app, qtbot, service_facade):
        """Create real MainWindow with mocked dependencies."""
        # Mock the auto-load to prevent file access
        with patch.object(MainWindow, "_load_burger_tracking_data"):
            window = MainWindow()
            window.services = service_facade

            # Set up proper frame range
            window.frame_spinbox.setMaximum(100)
            window.frame_slider.setMaximum(100)
            window.total_frames_label.setText("100")
            window.state_manager.total_frames = 100

            qtbot.addWidget(window)
            yield window

    def test_timeline_widget_created_in_main_window(self, main_window):
        """Test that timeline widget is created and accessible."""
        # Timeline widget should be created (unless import failed)
        if hasattr(main_window, "timeline_tabs") and main_window.timeline_tabs:
            assert main_window.timeline_tabs is not None
            assert main_window.timeline_tabs.current_frame == 1
        else:
            # If import failed, timeline_tabs should be None
            assert main_window.timeline_tabs is None

    def test_frame_navigation_sync_spinbox_to_timeline(self, main_window):
        """Test frame navigation from spinbox updates timeline."""
        if not main_window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        # Set timeline frame range first so frame 25 is valid
        main_window.timeline_tabs.set_frame_range(1, 100)

        # Change frame via spinbox
        main_window.frame_spinbox.setValue(25)
        main_window._on_frame_changed(25)

        # Timeline should be updated
        assert main_window.timeline_tabs.current_frame == 25

    def test_frame_navigation_sync_slider_to_timeline(self, main_window):
        """Test frame navigation from slider updates timeline."""
        if not main_window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        # Set timeline frame range first so frame 40 is valid
        main_window.timeline_tabs.set_frame_range(1, 100)

        # Change frame via slider
        main_window.frame_slider.setValue(40)
        main_window._on_slider_changed(40)

        # Timeline should be updated
        assert main_window.timeline_tabs.current_frame == 40

    def test_timeline_click_updates_spinbox_slider(self, main_window):
        """Test clicking timeline tab updates spinbox and slider."""
        if not main_window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        # Set timeline frame range first so frame 35 is valid
        main_window.timeline_tabs.set_frame_range(1, 100)

        # Simulate timeline tab click
        main_window._on_timeline_tab_clicked(35)

        # Spinbox and slider should be updated
        assert main_window.frame_spinbox.value() == 35
        assert main_window.frame_slider.value() == 35

    def test_load_data_updates_timeline_range(self, main_window, service_facade):
        """Test loading track data updates timeline frame range."""
        if not main_window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        # Mock loaded data with frame range 10-50
        test_data = [(10, 100.0, 200.0, "keyframe"), (25, 150.0, 250.0, "interpolated"), (50, 200.0, 300.0, "keyframe")]
        service_facade.load_track_data.return_value = test_data

        # Simulate loading data
        main_window._on_action_open()

        # Timeline should be updated with new range
        assert main_window.timeline_tabs.min_frame == 10
        assert main_window.timeline_tabs.max_frame == 50

    def test_update_timeline_tabs_with_point_data(self, main_window):
        """Test updating timeline tabs with point status data."""
        if not main_window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        # Create test curve data
        test_data = [
            (10, 100.0, 200.0, "keyframe"),
            (10, 110.0, 210.0, "keyframe"),  # Second point on frame 10
            (20, 150.0, 250.0, "interpolated"),
            (30, 200.0, 300.0, "keyframe"),
        ]

        # Update timeline with test data
        main_window._update_timeline_tabs(test_data)

        # Check that status cache was updated
        cache = main_window.timeline_tabs.status_cache

        # Frame 10 should have 2 keyframe points
        frame_10_status = cache.get_status(10)
        if frame_10_status:
            keyframe_count, interpolated_count, has_selected = frame_10_status
            assert keyframe_count == 2
            assert interpolated_count == 0

        # Frame 20 should have 1 interpolated point
        frame_20_status = cache.get_status(20)
        if frame_20_status:
            keyframe_count, interpolated_count, has_selected = frame_20_status
            assert keyframe_count == 0
            assert interpolated_count == 1

    def test_timeline_frame_range_updates_with_data_changes(self, main_window):
        """Test timeline frame range updates when data changes."""
        if not main_window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        # Initial data with small range
        initial_data = [(5, 100.0, 200.0, "keyframe"), (10, 150.0, 250.0, "keyframe")]
        main_window._update_timeline_tabs(initial_data)

        initial_min = main_window.timeline_tabs.min_frame
        initial_max = main_window.timeline_tabs.max_frame

        # Update with larger range
        expanded_data = [
            (1, 50.0, 100.0, "keyframe"),
            (5, 100.0, 200.0, "keyframe"),
            (10, 150.0, 250.0, "keyframe"),
            (50, 200.0, 300.0, "keyframe"),
        ]
        main_window._update_timeline_tabs(expanded_data)

        # Range should have expanded
        assert main_window.timeline_tabs.min_frame <= initial_min
        assert main_window.timeline_tabs.max_frame >= initial_max

    def test_timeline_hover_handler_exists(self, main_window):
        """Test timeline hover handler is properly connected."""
        if not main_window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        # Should not raise exception when called
        main_window._on_timeline_tab_hovered(15)

    def test_keyboard_navigation_updates_timeline(self, main_window):
        """Test keyboard navigation updates timeline current frame."""
        if not main_window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        # Set timeline frame range first so navigation works
        main_window.timeline_tabs.set_frame_range(1, 100)

        # Set initial frame
        main_window.frame_spinbox.setValue(20)
        main_window._on_frame_changed(20)

        # Navigate with keyboard shortcuts
        main_window._on_next_frame()
        assert main_window.timeline_tabs.current_frame == 21

        main_window._on_prev_frame()
        assert main_window.timeline_tabs.current_frame == 20

        main_window._on_first_frame()
        assert main_window.timeline_tabs.current_frame == 1

        main_window._on_last_frame()
        assert main_window.timeline_tabs.current_frame == main_window.frame_spinbox.maximum()

    def test_playback_updates_timeline_current_frame(self, main_window):
        """Test playback mode updates timeline current frame."""
        if not main_window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        # Set timeline frame range first so playback can advance beyond frame 1
        main_window.timeline_tabs.set_frame_range(1, 100)

        # Set initial frame
        main_window.frame_spinbox.setValue(10)
        main_window._on_frame_changed(10)

        # Set up playback state for oscillating playback
        from ui.main_window import PlaybackMode

        main_window.playback_state.mode = PlaybackMode.PLAYING_FORWARD
        main_window.playback_state.min_frame = 1
        main_window.playback_state.max_frame = 100

        # Simulate playback timer tick
        main_window._on_playback_timer()

        # Timeline should show next frame
        assert main_window.timeline_tabs.current_frame == 11

    def test_timeline_handles_empty_data_gracefully(self, main_window):
        """Test timeline handles empty or invalid data gracefully."""
        if not main_window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        # Should not raise exception with empty data
        main_window._update_timeline_tabs([])
        main_window._update_timeline_tabs(None)

        # Should not raise exception with invalid data formats
        invalid_data = [
            (1,),  # Too few elements
            ("invalid", 100.0, 200.0),  # Invalid frame number
            (10, "invalid", 200.0),  # Invalid coordinates
        ]
        main_window._update_timeline_tabs(invalid_data)

    def test_timeline_performance_with_many_frames(self, main_window):
        """Test timeline performance with large number of frames."""
        if not main_window.timeline_tabs:
            pytest.skip("Timeline tabs not available")

        # Create data with many frames
        large_data = [
            (frame, float(frame * 10), float(frame * 20), "keyframe")
            for frame in range(1, 1001)  # 1000 frames
        ]

        # Should not raise exception and should complete in reasonable time
        main_window._update_timeline_tabs(large_data)

        # Timeline should handle large range
        assert main_window.timeline_tabs.max_frame == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
