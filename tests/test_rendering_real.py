#!/usr/bin/env python
"""
Real integration tests for rendering pipeline without mocking.
Tests actual rendering transformations and optimizations.
"""

import numpy as np
import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor

from rendering.optimized_curve_renderer import (
    LevelOfDetail,
    OptimizedCurveRenderer,
    RenderQuality,
    VectorizedTransform,
    ViewportCuller,
)
from tests.qt_test_helpers import create_test_image, safe_painter


class TestViewportCuller:
    """Test viewport culling with real data."""

    def test_spatial_index_creation(self):
        """Test creating spatial index for points."""
        culler = ViewportCuller()

        # Create test points
        points = np.array([[100, 100], [200, 200], [300, 300], [400, 400], [500, 500]])

        viewport = QRectF(0, 0, 600, 600)

        # Update spatial index
        culler.update_spatial_index(points, viewport)

        # Check that index was created
        assert len(culler._spatial_index) > 0

    def test_visible_points_detection(self):
        """Test detecting visible points in viewport."""
        culler = ViewportCuller()

        # Create points - some inside, some outside viewport
        points = np.array(
            [
                [50, 50],  # Inside
                [150, 150],  # Inside
                [250, 250],  # Inside
                [350, 350],  # Outside
                [450, 450],  # Outside
                [-50, -50],  # Outside
            ]
        )

        viewport = QRectF(0, 0, 300, 300)

        # Get visible points
        visible_indices = culler.get_visible_points(points, viewport, padding=0)

        # Should return indices of points inside viewport
        assert len(visible_indices) == 3
        assert 0 in visible_indices  # Point at (50, 50)
        assert 1 in visible_indices  # Point at (150, 150)
        assert 2 in visible_indices  # Point at (250, 250)
        assert 3 not in visible_indices  # Point at (350, 350) is outside

    def test_viewport_padding(self):
        """Test that padding extends the viewport correctly."""
        culler = ViewportCuller()

        points = np.array(
            [
                [100, 100],  # Inside
                [305, 100],  # Just outside, but within padding
                [350, 100],  # Outside even with padding
            ]
        )

        viewport = QRectF(0, 0, 300, 300)

        # Without padding
        visible_no_pad = culler.get_visible_points(points, viewport, padding=0)
        assert len(visible_no_pad) == 1

        # With padding
        visible_with_pad = culler.get_visible_points(points, viewport, padding=50)
        assert len(visible_with_pad) == 2  # Includes point at 305

    def test_large_dataset_performance(self):
        """Test spatial indexing performance with large dataset."""
        culler = ViewportCuller()

        # Create large dataset
        np.random.seed(42)
        points = np.random.rand(10000, 2) * 1000

        viewport = QRectF(400, 400, 200, 200)

        # This should use spatial indexing (>1000 points)
        visible_indices = culler.get_visible_points(points, viewport)

        # Should only return points in the viewport area
        for idx in visible_indices:
            point = points[idx]
            assert 400 <= point[0] <= 600
            assert 400 <= point[1] <= 600


class TestLevelOfDetail:
    """Test level-of-detail system."""

    def test_lod_thresholds(self):
        """Test LOD thresholds for different quality levels."""
        lod = LevelOfDetail()

        # Create test points
        points = np.random.rand(5000, 2) * 500

        # Test different quality levels
        draft_points, draft_step = lod.get_lod_points(points, RenderQuality.DRAFT)
        normal_points, normal_step = lod.get_lod_points(points, RenderQuality.NORMAL)
        high_points, high_step = lod.get_lod_points(points, RenderQuality.HIGH)

        # Draft should show fewer points
        assert len(draft_points) < len(normal_points)
        assert len(normal_points) < len(high_points)
        assert len(high_points) == len(points)  # High quality shows all

        # Check step sizes
        assert draft_step > normal_step
        assert normal_step > high_step
        assert high_step == 1

    def test_lod_with_visible_indices(self):
        """Test LOD with pre-filtered visible indices."""
        lod = LevelOfDetail()

        points = np.random.rand(1000, 2) * 500
        visible_indices = np.array([10, 20, 30, 40, 50, 100, 200, 300])

        # Apply LOD to visible points only
        lod_points, step = lod.get_lod_points(points, RenderQuality.NORMAL, visible_indices)

        # Should subsample from visible points
        assert len(lod_points) <= len(visible_indices)


class TestVectorizedTransform:
    """Test vectorized coordinate transformation."""

    def test_batch_transformation(self):
        """Test transforming multiple points in batch."""
        # Create test points (frame, x, y format)
        points = np.array(
            [
                [1, 100, 200],
                [2, 150, 250],
                [3, 200, 300],
                [4, 250, 350],
            ]
        )

        # Transform parameters
        zoom = 2.0
        offset_x = 50.0
        offset_y = 100.0

        # Transform batch
        screen_points = VectorizedTransform.transform_points_batch(
            points, zoom, offset_x, offset_y, flip_y=False, height=0
        )

        # Check results
        assert screen_points.shape == (4, 2)

        # First point: (100 * 2 + 50, 200 * 2 + 100) = (250, 500)
        assert screen_points[0, 0] == 250
        assert screen_points[0, 1] == 500

    def test_y_flip_transformation(self):
        """Test Y-axis flipping in batch transformation."""
        points = np.array(
            [
                [1, 100, 100],
                [2, 200, 200],
            ]
        )

        height = 600
        screen_points = VectorizedTransform.transform_points_batch(
            points, zoom=1.0, offset_x=0, offset_y=0, flip_y=True, height=height
        )

        # Y should be flipped: height - y
        assert screen_points[0, 1] == 500  # 600 - 100
        assert screen_points[1, 1] == 400  # 600 - 200

    def test_empty_points_handling(self):
        """Test handling of empty point arrays."""
        points = np.array([])

        screen_points = VectorizedTransform.transform_points_batch(points, zoom=1.0, offset_x=0, offset_y=0)

        assert screen_points.shape == (0, 2)


class TestOptimizedCurveRenderer:
    """Test the optimized curve renderer."""

    def test_renderer_initialization(self):
        """Test renderer initialization with default settings."""
        renderer = OptimizedCurveRenderer()

        assert renderer._render_quality == RenderQuality.NORMAL
        assert renderer._quality_auto_adjust is True
        assert renderer._fps_target == 30.0
        assert renderer.background_opacity == 1.0

    def test_render_quality_settings(self):
        """Test setting render quality levels."""
        renderer = OptimizedCurveRenderer()

        # Set quality
        renderer.set_render_quality(RenderQuality.DRAFT)
        assert renderer._render_quality == RenderQuality.DRAFT
        assert renderer._quality_auto_adjust is False  # Disabled when manually set

        # Enable auto quality
        renderer.enable_auto_quality(target_fps=60.0)
        assert renderer._quality_auto_adjust is True
        assert renderer._fps_target == 60.0

    def test_performance_stats(self):
        """Test getting performance statistics."""
        renderer = OptimizedCurveRenderer()

        stats = renderer.get_performance_stats()

        assert "avg_fps" in stats
        assert "last_fps" in stats
        assert "last_render_ms" in stats
        assert "render_count" in stats
        assert "current_quality" in stats
        assert "auto_quality" in stats

    def test_render_with_real_painter(self):
        """Test rendering with a real QPainter (to an image)."""
        renderer = OptimizedCurveRenderer()

        # Create properly initialized image to render to
        image = create_test_image(800, 600, QColor(0, 0, 0))

        # Create a mock curve view with minimal required attributes
        class MockCurveView:
            def __init__(self):
                self.points = [
                    (1, 100, 100),
                    (2, 200, 200),
                    (3, 300, 300),
                ]
                self.show_background = False
                self.show_grid = False
                self.selected_points = set()
                self.point_radius = 5
                self.selected_point_radius = 7
                self.zoom_factor = 1.0
                self.pan_offset_x = 0
                self.pan_offset_y = 0
                self.manual_offset_x = 0
                self.manual_offset_y = 0
                self.flip_y_axis = False
                self.image_width = 800
                self.image_height = 600
                self._width = 800
                self._height = 600

            def width(self):
                return self._width

            def height(self):
                return self._height

            def get_transform(self):
                from services.transform_service import Transform

                return Transform(scale=self.zoom_factor, pan_offset_x=self.pan_offset_x, pan_offset_y=self.pan_offset_y)

        curve_view = MockCurveView()

        # Use safe painter context manager for guaranteed cleanup
        with safe_painter(image) as painter:
            # Render
            renderer.render(painter, None, curve_view)

        # Check that render count increased
        assert renderer._render_count > 0

        # Check performance tracking
        assert renderer._last_render_time > 0


class TestRenderingIntegration:
    """Integration tests for the complete rendering pipeline."""

    def test_viewport_culling_with_transform(self):
        """Test that viewport culling works with transformed coordinates."""
        from services.transform_service import Transform

        # Create transform with zoom and offset
        transform = Transform(scale=2.0, pan_offset_x=100, pan_offset_y=50)

        # Create points in data coordinates
        data_points = np.array(
            [
                [1, 50, 50],  # Will be at (200, 150) in screen
                [2, 100, 100],  # Will be at (300, 250) in screen
                [3, 200, 200],  # Will be at (500, 450) in screen
            ]
        )

        # Transform to screen coordinates
        screen_points = np.zeros((len(data_points), 2))
        for i, point in enumerate(data_points):
            x, y = transform.data_to_screen(point[1], point[2])
            screen_points[i] = [x, y]

        # Create viewport that includes only first two points
        viewport = QRectF(0, 0, 400, 400)

        # Test culling
        culler = ViewportCuller()
        visible = culler.get_visible_points(screen_points, viewport)

        assert len(visible) == 2
        assert 0 in visible
        assert 1 in visible
        assert 2 not in visible  # Point at (500, 450) is outside

    def test_lod_maintains_curve_shape(self):
        """Test that LOD subsampling maintains curve shape."""
        # Create a sine wave
        x = np.linspace(0, 4 * np.pi, 1000)
        y = np.sin(x) * 100 + 200
        # Variable 'points' was unused - removed

        lod = LevelOfDetail()

        # Apply LOD
        screen_points = np.column_stack([x * 50, y])
        lod_points, step = lod.get_lod_points(screen_points, RenderQuality.NORMAL)

        # Check that we still have the general shape
        # Min and max should be preserved
        assert abs(np.min(lod_points[:, 1]) - np.min(screen_points[:, 1])) < 10
        assert abs(np.max(lod_points[:, 1]) - np.max(screen_points[:, 1])) < 10

        # Should have fewer points
        assert len(lod_points) < len(screen_points)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
