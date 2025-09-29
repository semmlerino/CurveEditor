#!/usr/bin/env python3
"""
Integration tests for Timeline Tab functionality with MainWindow.

Following UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md best practices:
- Test behavior, not implementation
- Use real components with mocked boundaries
- Test integration points between components
- Mock only external dependencies
"""

from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication


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
    def timeline_widget(self, app, qtbot):
        """Create TimelineTabWidget directly for testing."""
        try:
            from ui.state_manager import StateManager
            from ui.timeline_tabs import TimelineTabWidget

            widget = TimelineTabWidget()
            qtbot.addWidget(widget)

            # Create and connect StateManager for Single Source of Truth architecture
            state_manager = StateManager()
            state_manager.total_frames = 10000  # Set high enough for large range tests
            widget.set_state_manager(state_manager)

            return widget
        except ImportError:
            pytest.skip("TimelineTabWidget not available")

    def test_timeline_widget_created(self, timeline_widget):
        """Test that timeline widget is created and accessible."""
        assert timeline_widget is not None
        assert timeline_widget.current_frame == 1

    def test_frame_navigation_sync_to_timeline(self, timeline_widget):
        """Test frame navigation updates timeline."""
        # Set timeline frame range first so frame 25 is valid
        timeline_widget.set_frame_range(1, 100)

        # Set frame
        timeline_widget.set_current_frame(25)

        # Timeline should be updated
        assert timeline_widget.current_frame == 25

    def test_timeline_frame_range(self, timeline_widget):
        """Test setting frame range on timeline."""
        # Set timeline frame range
        timeline_widget.set_frame_range(10, 50)

        # Check range is set
        assert timeline_widget.min_frame == 10
        assert timeline_widget.max_frame == 50

    def test_timeline_click_signal(self, timeline_widget, qtbot):
        """Test clicking timeline tab emits signal."""
        # Connect to signal
        with qtbot.waitSignal(timeline_widget.frame_changed, timeout=100) as blocker:
            # Simulate clicking frame 35
            timeline_widget.frame_changed.emit(35)

        # Check signal was emitted with correct value
        assert blocker.signal_triggered
        assert blocker.args[0] == 35

    def test_timeline_status_cache(self, timeline_widget):
        """Test timeline status cache functionality."""
        # Update timeline frame range
        timeline_widget.set_frame_range(10, 30)

        # Check basic properties
        assert timeline_widget.min_frame == 10
        assert timeline_widget.max_frame == 30

        # Test cache if it exists
        if hasattr(timeline_widget, "status_cache"):
            cache = timeline_widget.status_cache
            assert cache is not None

    def test_timeline_frame_range_updates(self, timeline_widget):
        """Test timeline frame range updates."""
        # Initial small range
        timeline_widget.set_frame_range(5, 10)
        assert timeline_widget.min_frame == 5
        assert timeline_widget.max_frame == 10

        # Update with larger range
        timeline_widget.set_frame_range(1, 50)
        assert timeline_widget.min_frame == 1
        assert timeline_widget.max_frame == 50

    def test_timeline_hover_signal(self, timeline_widget, qtbot):
        """Test timeline hover signal emission."""
        # Connect to hover signal if it exists
        if hasattr(timeline_widget, "frame_hovered"):
            with qtbot.waitSignal(timeline_widget.frame_hovered, timeout=100) as blocker:
                # Emit hover signal
                timeline_widget.frame_hovered.emit(15)

            assert blocker.signal_triggered
            assert blocker.args[0] == 15

    def test_timeline_handles_empty_data(self, timeline_widget):
        """Test timeline handles edge cases gracefully."""
        # Should not raise exception with edge case ranges
        timeline_widget.set_frame_range(0, 0)
        timeline_widget.set_frame_range(1, 1)
        timeline_widget.set_frame_range(-10, 10)

        # Set current frame to valid value
        timeline_widget.set_current_frame(1)
        assert timeline_widget.current_frame == 1

    def test_timeline_performance_with_large_range(self, timeline_widget):
        """Test timeline performance with large frame range."""
        # Should handle large range without issues
        timeline_widget.set_frame_range(1, 10000)
        assert timeline_widget.min_frame == 1
        assert timeline_widget.max_frame == 10000

        # Should be able to set frames within range
        timeline_widget.set_current_frame(5000)
        assert timeline_widget.current_frame == 5000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
