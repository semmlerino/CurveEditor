#!/usr/bin/env python
"""Test paint event optimizations for performance improvements."""

import time
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent, QPaintEvent, QWheelEvent

from ui.curve_view_widget import CurveViewWidget, RenderQuality


class TestPaintEventOptimization:
    """Test paint event optimizations."""

    @pytest.fixture
    def widget(self, qtbot):
        """Create test widget."""
        w = CurveViewWidget()
        qtbot.addWidget(w)
        w.resize(800, 600)
        w.show()
        qtbot.waitExposed(w)
        return w

    def test_interaction_state_tracking(self, widget):
        """Test that interaction state is properly tracked."""
        # Initially not interacting
        assert not widget._is_interacting

        # Simulate mouse press - should start interaction
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(100, 100),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.mousePressEvent(event)
        assert widget._is_interacting

        # Simulate mouse release - should end interaction
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(100, 100),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.mouseReleaseEvent(event)
        assert not widget._is_interacting
        assert widget._pending_full_redraw

    def test_render_quality_selection(self, widget):
        """Test that correct render quality is selected based on state."""
        # Mock paint event
        event = QPaintEvent(QRect(0, 0, 100, 100))

        # Normal state - should use NORMAL quality
        widget._is_interacting = False
        widget._pending_full_redraw = False

        with patch.object(widget, "_render_with_quality") as mock_render:
            widget.paintEvent(event)
            # Check that NORMAL quality was used
            args = mock_render.call_args[0]
            assert args[3] == RenderQuality.NORMAL

        # Interacting state - should use DRAFT quality
        widget._is_interacting = True
        widget._last_paint_time = 0  # Ensure frame rate limiting doesn't interfere
        with patch.object(widget, "_render_with_quality") as mock_render:
            widget.paintEvent(event)
            args = mock_render.call_args[0]
            assert args[3] == RenderQuality.DRAFT

        # Pending full redraw - should use HIGH quality
        widget._is_interacting = False
        widget._pending_full_redraw = True
        with patch.object(widget, "_render_with_quality") as mock_render:
            widget.paintEvent(event)
            args = mock_render.call_args[0]
            assert args[3] == RenderQuality.HIGH

    def test_frame_rate_limiting(self, widget):
        """Test that frame rate is limited during interaction."""
        widget._is_interacting = True
        widget._target_fps = 60
        widget._frame_time = 1.0 / 60  # ~16.67ms

        event = QPaintEvent(QRect(0, 0, 100, 100))

        # First paint should go through
        widget._last_paint_time = 0
        with patch.object(widget, "_render_with_quality") as mock_render:
            widget.paintEvent(event)
            assert mock_render.called

        # Immediate second paint should be skipped (too soon)
        widget._last_paint_time = time.perf_counter()
        with patch.object(widget, "_render_with_quality") as mock_render:
            widget.paintEvent(event)
            assert not mock_render.called

    def test_cached_transform_usage(self, widget):
        """Test that cached transform is used during paint."""
        # Reset cache monitor to start fresh
        widget._cache_monitor.hits = 0
        widget._cache_monitor.misses = 0

        # Set up a cached transform
        mock_transform = MagicMock()
        widget._transform_cache = mock_transform

        # Getting cached transform should not create new one
        result = widget._get_cached_transform_for_paint()
        assert result == mock_transform
        assert widget._cache_monitor.hits == 1
        assert widget._cache_monitor.misses == 0

        # Without cache, should record miss
        widget._transform_cache = None
        widget._is_interacting = False
        with patch.object(widget, "get_transform", return_value=mock_transform):
            result = widget._get_cached_transform_for_paint()
            assert widget._cache_monitor.misses == 1

    def test_dirty_region_marking(self, widget):
        """Test dirty region marking for partial updates."""
        # Initially no dirty region
        assert widget._dirty_region.isEmpty()

        # Mark a region as dirty
        rect1 = QRect(10, 10, 50, 50)
        widget._mark_dirty_region(rect1)
        assert not widget._dirty_region.isEmpty()
        assert widget._dirty_region == rect1

        # Mark another region - should unite
        rect2 = QRect(40, 40, 50, 50)
        widget._mark_dirty_region(rect2)
        expected = rect1.united(rect2)
        assert widget._dirty_region == expected

    def test_transform_precalculation(self, widget):
        """Test that transform is pre-calculated outside paint."""
        widget._is_interacting = False

        # Mock the update method
        with patch.object(widget, "_update_transform") as mock_update:
            widget._pre_calculate_transform()
            assert mock_update.called

        # Should store as last valid transform
        mock_transform = MagicMock()
        widget._transform_cache = mock_transform
        with patch.object(widget, "_update_transform"):
            widget._pre_calculate_transform()
        assert widget._last_valid_transform == mock_transform

    def test_performance_logging(self, widget):
        """Test performance metrics logging."""
        # Reset counters
        widget._paint_counter = 0
        widget._paint_start_time = time.perf_counter() - 2.0  # 2 seconds ago

        # First call shouldn't log (not enough time)
        widget._paint_counter = 1
        widget._paint_start_time = time.perf_counter()
        with patch("logging.Logger.debug") as mock_log:
            widget._log_paint_performance()
            assert not mock_log.called

        # After 1 second should log
        widget._paint_counter = 60
        widget._paint_start_time = time.perf_counter() - 1.1
        with patch("logging.Logger.debug") as mock_log:
            widget._log_paint_performance()
            assert mock_log.called
            # Check log message contains FPS and cache stats
            log_message = mock_log.call_args[0][0]
            assert "Paint FPS" in log_message
            assert "Cache hit rate" in log_message

    def test_wheel_event_transform_precalc(self, widget):
        """Test that wheel events pre-calculate transform."""
        widget._is_interacting = False

        # Create wheel event
        delta = QPoint(0, 120)  # Positive for zoom in
        event = QWheelEvent(
            QPointF(400, 300),
            QPointF(400, 300),
            QPoint(0, 0),
            delta,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )

        # Mock pre-calculate
        with patch.object(widget, "_pre_calculate_transform") as mock_precalc:
            widget.wheelEvent(event)
            assert mock_precalc.called

    def test_draft_rendering_in_renderer(self):
        """Test that OptimizedCurveRenderer supports draft rendering."""
        from rendering.optimized_curve_renderer import OptimizedCurveRenderer

        renderer = OptimizedCurveRenderer()
        assert hasattr(renderer, "render_draft")

        # Test draft rendering with mock data
        mock_painter = MagicMock()
        mock_event = MagicMock()
        mock_view = MagicMock()
        mock_view.points = [(0, 0, 0), (1, 10, 10), (2, 20, 20)]
        mock_view.selected_indices = {1}
        mock_transform = MagicMock()
        mock_transform.data_to_screen = lambda x, y: (x * 10, y * 10)

        # Should not raise
        renderer.render_draft(mock_painter, mock_event, mock_view, mock_transform)

        # Should have drawn path
        assert mock_painter.drawPath.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
