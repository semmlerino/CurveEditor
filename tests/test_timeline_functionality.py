#!/usr/bin/env python3
"""
Tests for Timeline Tab functionality.

Following UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md best practices:
- Test behavior, not implementation
- Use real components with mocked boundaries
- Test with available qapp fixture
- Mock only external dependencies
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from ui.frame_tab import FrameTab
from ui.timeline_tabs import FrameStatusCache, TimelineTabWidget


class TestFrameTab:
    """Test suite for individual frame tab functionality."""

    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def frame_tab(self, app: QApplication, qtbot: QtBot) -> FrameTab:
        """Create real FrameTab for testing."""
        tab = FrameTab(15)
        qtbot.addWidget(tab)
        return tab

    def test_frame_tab_initialization(self, frame_tab: FrameTab) -> None:
        """Test frame tab initializes with correct properties."""
        assert frame_tab.frame_number == 15
        assert frame_tab.point_count == 0
        assert frame_tab.keyframe_count == 0
        assert frame_tab.interpolated_count == 0
        assert not frame_tab.is_current_frame
        assert not frame_tab.is_hovered
        assert not frame_tab.has_selected_points

    def test_frame_tab_size(self, frame_tab: FrameTab) -> None:
        """Test frame tab has correct size constraints."""
        # Set a width within the valid range
        frame_tab.set_tab_width(30)
        assert FrameTab.MIN_WIDTH <= frame_tab.width() <= FrameTab.MAX_WIDTH
        assert frame_tab.height() == FrameTab.TAB_HEIGHT

        # Test extremes
        frame_tab.set_tab_width(1)  # Below min
        assert frame_tab.width() == FrameTab.MIN_WIDTH

        frame_tab.set_tab_width(100)  # Above max
        assert frame_tab.width() == FrameTab.MAX_WIDTH

    def test_set_point_status_no_points(self, frame_tab: FrameTab) -> None:
        """Test setting point status when no points exist."""
        frame_tab.set_point_status()

        assert frame_tab.point_count == 0
        assert frame_tab.keyframe_count == 0
        assert frame_tab.interpolated_count == 0
        assert not frame_tab.has_selected_points

    def test_set_point_status_keyframe_points(self, frame_tab: FrameTab) -> None:
        """Test setting point status with keyframe points."""
        frame_tab.set_point_status(keyframe_count=3, interpolated_count=0)

        assert frame_tab.point_count == 3
        assert frame_tab.keyframe_count == 3
        assert frame_tab.interpolated_count == 0
        assert not frame_tab.has_selected_points

    def test_set_point_status_interpolated_points(self, frame_tab: FrameTab) -> None:
        """Test setting point status with interpolated points."""
        frame_tab.set_point_status(keyframe_count=0, interpolated_count=2)

        assert frame_tab.point_count == 2
        assert frame_tab.keyframe_count == 0
        assert frame_tab.interpolated_count == 2

    def test_set_point_status_mixed_points(self, frame_tab: FrameTab) -> None:
        """Test setting point status with mixed point types."""
        frame_tab.set_point_status(keyframe_count=2, interpolated_count=3, has_selected=True)

        assert frame_tab.point_count == 5
        assert frame_tab.keyframe_count == 2
        assert frame_tab.interpolated_count == 3
        assert frame_tab.has_selected_points

    def test_set_current_frame(self, frame_tab: FrameTab) -> None:
        """Test setting current frame status."""
        assert not frame_tab.is_current_frame

        frame_tab.set_current_frame(True)
        assert frame_tab.is_current_frame

        frame_tab.set_current_frame(False)
        assert not frame_tab.is_current_frame

    def test_background_color_no_points(self, frame_tab: FrameTab) -> None:
        """Test background color when no points exist."""
        color = frame_tab._get_background_color()
        expected = FrameTab.COLORS["no_points"]
        assert color == expected

    def test_background_color_keyframe_points(self, frame_tab: FrameTab) -> None:
        """Test background color with keyframe points."""
        frame_tab.set_point_status(keyframe_count=2)
        color = frame_tab._get_background_color()
        expected = FrameTab.COLORS["keyframe"]
        assert color == expected

    def test_background_color_interpolated_points(self, frame_tab: FrameTab) -> None:
        """Test background color with interpolated points."""
        frame_tab.set_point_status(interpolated_count=1)
        color = frame_tab._get_background_color()
        expected = FrameTab.COLORS["interpolated"]
        assert color == expected

    def test_background_color_mixed_points(self, frame_tab: FrameTab) -> None:
        """Test background color with mixed point types."""
        frame_tab.set_point_status(keyframe_count=1, interpolated_count=1)
        color = frame_tab._get_background_color()
        expected = FrameTab.COLORS["mixed"]
        assert color == expected

    def test_background_color_current_frame_priority(self, frame_tab: FrameTab) -> None:
        """Test current frame doesn't change background color (uses border instead)."""
        frame_tab.set_point_status(keyframe_count=2)
        frame_tab.set_current_frame(True)

        # Current frame is highlighted with border, not background color
        # Background color should still be keyframe color
        color = frame_tab._get_background_color()
        expected = FrameTab.COLORS["keyframe"]
        assert color == expected

    def test_background_color_selected_priority(self, frame_tab: FrameTab) -> None:
        """Test selected points color takes highest priority."""
        frame_tab.set_point_status(keyframe_count=2, has_selected=True)
        frame_tab.set_current_frame(True)

        color = frame_tab._get_background_color()
        expected = FrameTab.COLORS["selected"]
        assert color == expected

    def test_tooltip_no_points(self, frame_tab: FrameTab) -> None:
        """Test tooltip text when no points exist."""
        frame_tab.set_point_status()
        expected = "Frame 15: No tracked points"
        assert frame_tab.toolTip() == expected

    def test_tooltip_keyframe_points(self, frame_tab: FrameTab) -> None:
        """Test tooltip text with keyframe points."""
        frame_tab.set_point_status(keyframe_count=3)
        expected = "Frame 15: 3 keyframe points"
        assert frame_tab.toolTip() == expected

    def test_tooltip_mixed_points(self, frame_tab: FrameTab) -> None:
        """Test tooltip text with mixed point types."""
        frame_tab.set_point_status(keyframe_count=2, interpolated_count=1)
        expected = "Frame 15: 2 keyframe, 1 interpolated points"
        assert frame_tab.toolTip() == expected

    def test_tooltip_selected_points(self, frame_tab: FrameTab) -> None:
        """Test tooltip text includes selection status."""
        frame_tab.set_point_status(keyframe_count=2, has_selected=True)
        expected = "Frame 15: 2 keyframe points (selected)"
        assert frame_tab.toolTip() == expected

    def test_frame_clicked_signal(self, frame_tab: FrameTab, qtbot: QtBot) -> None:
        """Test frame clicked signal emission."""
        with qtbot.waitSignal(frame_tab.frame_clicked, timeout=1000) as blocker:
            # Simulate left mouse click
            qtbot.mouseClick(frame_tab, Qt.MouseButton.LeftButton)

        # Check signal was emitted with correct frame number
        assert blocker.args == [15]

    def test_frame_hovered_signal(self, frame_tab: FrameTab, qtbot: QtBot) -> None:
        """Test frame hovered signal emission."""
        # Test hover signal by directly calling enterEvent
        # Mouse events in tests don't always trigger enterEvent reliably
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QEnterEvent

        with qtbot.waitSignal(frame_tab.frame_hovered, timeout=1000) as blocker:
            # Manually trigger enterEvent since mouse simulation doesn't work reliably in tests
            enter_event = QEnterEvent(
                QPointF(10, 10),  # localPos
                QPointF(10, 10),  # windowPos
                QPointF(10, 10),  # screenPos
            )
            frame_tab.enterEvent(enter_event)

        # The signal should be emitted with the frame number
        assert blocker.args == [15]


class TestFrameStatusCache:
    """Test suite for frame status caching functionality."""

    @pytest.fixture
    def cache(self) -> FrameStatusCache:
        """Create fresh cache for testing."""
        return FrameStatusCache()

    def test_empty_cache_returns_none(self, cache: FrameStatusCache) -> None:
        """Test empty cache returns None for any frame."""
        result = cache.get_status(1)
        assert result is None

    def test_set_and_get_status(self, cache: FrameStatusCache) -> None:
        """Test setting and getting frame status."""
        cache.set_status(10, keyframe_count=2, interpolated_count=1, has_selected=False)

        result = cache.get_status(10)
        assert result == (2, 1, False)

    def test_get_status_different_frame(self, cache: FrameStatusCache) -> None:
        """Test getting status for non-cached frame returns None."""
        cache.set_status(10, keyframe_count=2, interpolated_count=1, has_selected=False)

        result = cache.get_status(20)
        assert result is None

    def test_invalidate_frame(self, cache: FrameStatusCache) -> None:
        """Test invalidating specific frame."""
        cache.set_status(10, keyframe_count=2, interpolated_count=1, has_selected=False)
        cache.invalidate_frame(10)

        # Status should still be retrievable (invalidation just marks for update)
        result = cache.get_status(10)
        assert result == (2, 1, False)

    def test_clear_cache(self, cache: FrameStatusCache) -> None:
        """Test clearing entire cache."""
        cache.set_status(10, keyframe_count=2, interpolated_count=1, has_selected=False)
        cache.set_status(20, keyframe_count=1, interpolated_count=0, has_selected=True)

        cache.clear()

        assert cache.get_status(10) is None
        assert cache.get_status(20) is None

    def test_invalidate_all(self, cache: FrameStatusCache) -> None:
        """Test invalidating all frames."""
        cache.set_status(10, keyframe_count=2, interpolated_count=1, has_selected=False)
        cache.set_status(20, keyframe_count=1, interpolated_count=0, has_selected=True)

        cache.invalidate_all()

        # Data should still be retrievable (invalidation just marks for update)
        assert cache.get_status(10) == (2, 1, False)
        assert cache.get_status(20) == (1, 0, True)


class TestTimelineTabWidget:
    """Test suite for timeline widget functionality."""

    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def timeline_widget(self, app: QApplication, qtbot: QtBot) -> TimelineTabWidget:
        """Create real TimelineTabWidget for testing."""
        widget = TimelineTabWidget()
        qtbot.addWidget(widget)
        return widget

    def test_timeline_initialization(self, timeline_widget: TimelineTabWidget) -> None:
        """Test timeline initializes with minimal range (expands with data)."""
        assert timeline_widget.current_frame == 1
        assert timeline_widget.total_frames == 1  # Starts minimal, expands when data loaded
        assert timeline_widget.min_frame == 1
        assert timeline_widget.max_frame == 1
        # Note: TimelineTabWidget doesn't have visible_range attribute
        # It dynamically creates tabs as needed

    def test_set_frame_range(self, timeline_widget: TimelineTabWidget) -> None:
        """Test setting frame range updates widget."""
        timeline_widget.set_frame_range(10, 50)

        assert timeline_widget.min_frame == 10
        assert timeline_widget.max_frame == 50
        assert timeline_widget.total_frames == 41

    def test_set_current_frame_within_range(self, timeline_widget: TimelineTabWidget) -> None:
        """Test setting current frame within valid range."""
        timeline_widget.set_frame_range(1, 100)
        timeline_widget.set_current_frame(25)

        assert timeline_widget.current_frame == 25

    def test_set_current_frame_clamps_to_range(self, timeline_widget: TimelineTabWidget) -> None:
        """Test setting current frame outside range gets clamped."""
        timeline_widget.set_frame_range(10, 50)

        # Test lower bound
        timeline_widget.set_current_frame(5)
        assert timeline_widget.current_frame == 10

        # Test upper bound
        timeline_widget.set_current_frame(60)
        assert timeline_widget.current_frame == 50

    def test_frame_changed_signal(self, timeline_widget: TimelineTabWidget, qtbot: QtBot) -> None:
        """Test frame changed signal emission."""
        timeline_widget.set_frame_range(1, 100)

        with qtbot.waitSignal(timeline_widget.frame_changed, timeout=1000) as blocker:
            timeline_widget.set_current_frame(30)

        assert blocker.args == [30]

    def test_update_frame_status(self, timeline_widget: TimelineTabWidget) -> None:
        """Test updating frame status information."""
        # This should not raise an exception
        timeline_widget.update_frame_status(frame=25, keyframe_count=3, interpolated_count=2, has_selected=True)

        # Status should be cached
        cached_status = timeline_widget.status_cache.get_status(25)
        assert cached_status == (3, 2, True)

    def test_invalidate_frame_status(self, timeline_widget: TimelineTabWidget) -> None:
        """Test invalidating frame status triggers update."""
        timeline_widget.update_frame_status(25, keyframe_count=2)

        # Should not raise exception
        timeline_widget.invalidate_frame_status(25)

    def test_invalidate_all_frames(self, timeline_widget: TimelineTabWidget) -> None:
        """Test invalidating all frames."""
        timeline_widget.update_frame_status(20, keyframe_count=1)
        timeline_widget.update_frame_status(25, keyframe_count=2)

        # Should not raise exception
        timeline_widget.invalidate_all_frames()

    def test_visible_range_around_current_frame(self, timeline_widget: TimelineTabWidget) -> None:
        """Test that current frame can be set within range."""
        timeline_widget.set_frame_range(1, 200)
        timeline_widget.set_current_frame(100)

        # Verify current frame was set correctly
        assert timeline_widget.current_frame == 100

        # Test that tabs are created dynamically as needed
        # TimelineTabWidget creates tabs on demand in _rebuild_timeline()
        # which is called by set_frame_range and update_all_frames

    def test_keyboard_navigation(self, timeline_widget: TimelineTabWidget, qtbot: QtBot) -> None:
        """Test keyboard navigation functionality."""
        timeline_widget.set_frame_range(10, 50)
        timeline_widget.set_current_frame(25)

        # Test right arrow (next frame)
        qtbot.keyPress(timeline_widget, Qt.Key.Key_Right)
        assert timeline_widget.current_frame == 26

        # Test left arrow (previous frame)
        qtbot.keyPress(timeline_widget, Qt.Key.Key_Left)
        assert timeline_widget.current_frame == 25

        # Test Home key (first frame)
        qtbot.keyPress(timeline_widget, Qt.Key.Key_Home)
        assert timeline_widget.current_frame == 10

        # Test End key (last frame)
        qtbot.keyPress(timeline_widget, Qt.Key.Key_End)
        assert timeline_widget.current_frame == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
