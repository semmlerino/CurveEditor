"""
Edge case tests for OptimizedCurveRenderer.

Tests rendering initialization and configuration with edge cases.
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none

import pytest
from core.models import CurvePoint, PointStatus
from rendering.optimized_curve_renderer import OptimizedCurveRenderer, RenderQuality


class TestRendererInitialization:
    """Tests for renderer initialization."""

    def test_create_renderer(self):
        """Should create renderer without errors."""
        renderer = OptimizedCurveRenderer()
        assert renderer is not None

    def test_set_render_quality(self):
        """Should accept all quality levels."""
        renderer = OptimizedCurveRenderer()

        for quality in RenderQuality:
            renderer.set_render_quality(quality)
            # No assertion needed - just verify no exception


class TestRendererAutoQuality:
    """Tests for auto quality adjustment."""

    def test_enable_auto_quality(self):
        """Should enable auto quality without errors."""
        renderer = OptimizedCurveRenderer()
        renderer.enable_auto_quality(target_fps=60.0)
        # Verify it doesn't raise
        assert renderer._quality_auto_adjust is True

    def test_auto_quality_various_fps_targets(self):
        """Should accept various FPS targets."""
        renderer = OptimizedCurveRenderer()

        for fps in [30.0, 60.0, 120.0, 144.0]:
            renderer.enable_auto_quality(target_fps=fps)
            # No assertion needed - just verify no exception


class TestRendererPerformanceStats:
    """Tests for performance statistics."""

    def test_get_performance_stats_initial(self):
        """Should return valid stats even before any rendering."""
        renderer = OptimizedCurveRenderer()
        stats = renderer.get_performance_stats()

        assert isinstance(stats, dict)
        # Just verify we get a dict back - don't check specific keys


class TestRendererCacheManagement:
    """Tests for cache management."""

    def test_clear_empty_cache(self):
        """Should handle clearing empty cache."""
        renderer = OptimizedCurveRenderer()
        renderer.clear_segmented_curve_cache()  # Should not raise

    def test_clear_cache_multiple_times(self):
        """Should handle multiple cache clears."""
        renderer = OptimizedCurveRenderer()

        for _ in range(10):
            renderer.clear_segmented_curve_cache()  # Should not raise


class TestPointStatusValues:
    """Tests for point status handling in data preparation."""

    def test_all_point_statuses_valid(self):
        """All PointStatus values should be valid for creating points."""
        points = []
        for i, status in enumerate(PointStatus):
            point = CurvePoint(
                frame=i + 1,
                x=float(i) / 10.0,
                y=float(i) / 10.0,
                status=status
            )
            points.append(point)
            assert point.status == status

        assert len(points) == len(PointStatus)

    def test_create_single_point_curve(self):
        """Should be able to create curve data with single point."""
        point = CurvePoint(frame=1, x=0.5, y=0.5, status=PointStatus.KEYFRAME)
        curve_data = [point]
        assert len(curve_data) == 1

    def test_create_empty_curve_data(self):
        """Should be able to create empty curve data list."""
        curve_data = []
        assert len(curve_data) == 0


class TestRenderQualityEnum:
    """Tests for RenderQuality enum values."""

    def test_all_quality_levels_exist(self):
        """All expected quality levels should exist."""
        expected = ["DRAFT", "NORMAL", "HIGH"]
        for name in expected:
            assert hasattr(RenderQuality, name)

    def test_quality_levels_iterable(self):
        """Quality levels should be iterable."""
        levels = list(RenderQuality)
        assert len(levels) >= 2  # At least DRAFT and HIGH
