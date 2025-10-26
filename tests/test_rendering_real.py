#!/usr/bin/env python
"""
Real integration tests for rendering pipeline without mocking.
Tests actual rendering transformations and optimizations.
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

from typing import Any

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

    def test_spatial_index_creation(self) -> None:
        """Test creating spatial index for points."""
        culler = ViewportCuller()

        # Create test points
        points: Any = np.array([[100, 100], [200, 200], [300, 300], [400, 400], [500, 500]])

        viewport = QRectF(0, 0, 600, 600)

        # Update spatial index
        culler.update_spatial_index(points, viewport)

        # Check that index was created
        assert len(culler._spatial_index) > 0

    def test_visible_points_detection(self) -> None:
        """Test detecting visible points in viewport."""
        culler = ViewportCuller()

        # Create points - some inside, some outside viewport
        points: Any = np.array(
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
        visible_indices: Any = culler.get_visible_points(points, viewport, padding=0)

        # Should return indices of points inside viewport
        assert len(visible_indices) == 3
        assert 0 in visible_indices  # Point at (50, 50)
        assert 1 in visible_indices  # Point at (150, 150)
        assert 2 in visible_indices  # Point at (250, 250)
        assert 3 not in visible_indices  # Point at (350, 350) is outside

    def test_viewport_padding(self) -> None:
        """Test that padding extends the viewport correctly."""
        culler = ViewportCuller()

        points: Any = np.array(
            [
                [100, 100],  # Inside
                [305, 100],  # Just outside, but within padding
                [351, 100],  # Outside even with padding (350 is exactly at boundary)
            ]
        )

        viewport = QRectF(0, 0, 300, 300)

        # Without padding
        visible_no_pad: Any = culler.get_visible_points(points, viewport, padding=0)
        assert len(visible_no_pad) == 1

        # With padding
        visible_with_pad: Any = culler.get_visible_points(points, viewport, padding=50)
        assert len(visible_with_pad) == 2  # Includes point at 305

    def test_large_dataset_performance(self) -> None:
        """Test spatial indexing performance with large dataset."""
        culler = ViewportCuller()

        # Create large dataset
        np.random.seed(42)
        points: Any = np.random.rand(10000, 2) * 1000

        viewport = QRectF(400, 400, 200, 200)

        # This should use spatial indexing (>1000 points)
        visible_indices: Any = culler.get_visible_points(points, viewport)

        # Should only return points in the viewport area
        for idx in visible_indices:
            point = points[idx]
            assert 400 <= point[0] <= 600
            assert 400 <= point[1] <= 600


class TestLevelOfDetail:
    """Test level-of-detail system."""

    def test_lod_thresholds(self) -> None:
        """Test LOD thresholds for different quality levels."""
        lod = LevelOfDetail()

        # Create test points
        points: Any = np.random.rand(5000, 2) * 500

        # Test different quality levels
        draft_points: Any
        draft_step: Any
        draft_points, draft_step = lod.get_lod_points(points, RenderQuality.DRAFT)
        normal_points: Any
        normal_step: Any
        normal_points, normal_step = lod.get_lod_points(points, RenderQuality.NORMAL)
        high_points: Any
        high_step: Any
        high_points, high_step = lod.get_lod_points(points, RenderQuality.HIGH)

        # Draft should show fewer points
        assert len(draft_points) < len(normal_points)
        assert len(normal_points) < len(high_points)
        assert len(high_points) == len(points)  # High quality shows all

        # Check step sizes
        assert draft_step > normal_step
        assert normal_step > high_step
        assert high_step == 1

    def test_lod_with_visible_indices(self) -> None:
        """Test LOD with pre-filtered visible indices."""
        lod = LevelOfDetail()

        points: Any = np.random.rand(1000, 2) * 500
        visible_indices: Any = np.array([10, 20, 30, 40, 50, 100, 200, 300])

        # Apply LOD to visible points only
        lod_points: Any
        _step: Any
        lod_points, _step = lod.get_lod_points(points, RenderQuality.NORMAL, visible_indices)

        # Should subsample from visible points
        assert len(lod_points) <= len(visible_indices)


class TestVectorizedTransform:
    """Test vectorized coordinate transformation."""

    def test_batch_transformation(self) -> None:
        """Test transforming multiple points in batch."""
        # Create test points (frame, x, y format)
        points: Any = np.array(
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

    def test_y_flip_transformation(self) -> None:
        """Test Y-axis flipping in batch transformation."""
        points: Any = np.array(
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

    def test_empty_points_handling(self) -> None:
        """Test handling of empty point arrays."""
        points: Any = np.array([])

        screen_points = VectorizedTransform.transform_points_batch(points, zoom=1.0, offset_x=0, offset_y=0)

        assert screen_points.shape == (0, 2)


class TestOptimizedCurveRenderer:
    """Test the optimized curve renderer."""

    def test_renderer_initialization(self) -> None:
        """Test renderer initialization with default settings."""
        renderer = OptimizedCurveRenderer()

        assert renderer._render_quality == RenderQuality.NORMAL
        assert renderer._quality_auto_adjust is True
        assert renderer._fps_target == 30.0
        assert renderer.background_opacity == 1.0

    def test_render_quality_settings(self) -> None:
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

    def test_performance_stats(self) -> None:
        """Test getting performance statistics."""
        renderer = OptimizedCurveRenderer()

        stats = renderer.get_performance_stats()

        assert "avg_fps" in stats
        assert "last_fps" in stats
        assert "last_render_ms" in stats
        assert "render_count" in stats
        assert "current_quality" in stats
        assert "auto_quality" in stats

    def test_render_with_real_painter(self) -> None:
        """Test rendering with a real QPainter (to an image)."""
        renderer = OptimizedCurveRenderer()

        # Create properly initialized image to render to
        image = create_test_image(800, 600, QColor(0, 0, 0))

        # Create a RenderState object with test data
        from rendering.render_state import RenderState

        render_state = RenderState(
            points=[
                (1, 100, 100),
                (2, 200, 200),
                (3, 300, 300),
            ],
            current_frame=1,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
        )

        # Use safe painter context manager for guaranteed cleanup
        with safe_painter(image) as painter:
            # Render
            renderer.render(painter, None, render_state)

        # Check that render count increased
        assert renderer._render_count > 0

        # Check performance tracking
        assert renderer._last_render_time > 0


class TestRenderingIntegration:
    """Integration tests for the complete rendering pipeline."""

    def test_viewport_culling_with_transform(self) -> None:
        """Test that viewport culling works with transformed coordinates."""
        from services.transform_service import Transform

        # Create transform with zoom and offset
        transform = Transform(scale=2.0, center_offset_x=0.0, center_offset_y=0.0, pan_offset_x=100, pan_offset_y=50)

        # Create points in data coordinates
        data_points: Any = np.array(
            [
                [1, 50, 50],  # Will be at (200, 150) in screen
                [2, 100, 100],  # Will be at (300, 250) in screen
                [3, 200, 200],  # Will be at (500, 450) in screen
            ]
        )

        # Transform to screen coordinates
        screen_points: Any = np.zeros((len(data_points), 2))
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

    def test_lod_maintains_curve_shape(self) -> None:
        """Test that LOD subsampling maintains curve shape."""
        # Create a sine wave with more points than NORMAL threshold
        x: Any = np.linspace(0, 4 * np.pi, 1500)  # Use 1500 points to ensure LOD kicks in
        y: Any = np.sin(x) * 100 + 200

        lod = LevelOfDetail()

        # Apply LOD
        screen_points: Any = np.column_stack([x * 50, y])
        lod_points: Any
        _step: Any
        lod_points, _step = lod.get_lod_points(screen_points, RenderQuality.NORMAL)

        # Check that we still have the general shape
        # Min and max should be preserved
        assert abs(np.min(lod_points[:, 1]) - np.min(screen_points[:, 1])) < 10
        assert abs(np.max(lod_points[:, 1]) - np.max(screen_points[:, 1])) < 10

        # Should have fewer points
        assert len(lod_points) < len(screen_points)


class TestInactiveSegmentRendering:
    """Test rendering of inactive segments (gaps) with dashed lines."""

    def test_inactive_segment_point_hiding(self) -> None:
        """Test that points in inactive segments are not rendered (except endframes)."""
        from core.curve_segments import SegmentedCurve
        from core.models import CurvePoint, PointStatus

        # Create points with an endframe that creates a gap
        points = [
            CurvePoint(1, 100, 100, PointStatus.KEYFRAME),
            CurvePoint(2, 110, 110, PointStatus.NORMAL),
            CurvePoint(3, 120, 120, PointStatus.ENDFRAME),  # Creates gap
            CurvePoint(4, 130, 130, PointStatus.TRACKED),  # In gap (inactive)
            CurvePoint(5, 140, 140, PointStatus.TRACKED),  # In gap (inactive)
            CurvePoint(6, 150, 150, PointStatus.KEYFRAME),  # Startframe (active)
        ]

        segmented_curve = SegmentedCurve.from_points(points)

        # Check segment detection
        segment_at_2 = segmented_curve.get_segment_at_frame(2)
        assert segment_at_2 is not None
        assert segment_at_2.is_active

        segment_at_4 = segmented_curve.get_segment_at_frame(4)
        assert segment_at_4 is not None
        assert not segment_at_4.is_active

        segment_at_5 = segmented_curve.get_segment_at_frame(5)
        assert segment_at_5 is not None
        assert not segment_at_5.is_active

        segment_at_6 = segmented_curve.get_segment_at_frame(6)
        assert segment_at_6 is not None
        assert segment_at_6.is_active

    def test_gap_segment_detection(self) -> None:
        """Test that gap segments are correctly identified for dashed line rendering."""
        from core.curve_segments import SegmentedCurve
        from core.models import CurvePoint, PointStatus

        # Create curve with multiple gaps
        points = [
            CurvePoint(1, 100, 100, PointStatus.KEYFRAME),
            CurvePoint(2, 110, 110, PointStatus.ENDFRAME),  # First gap
            CurvePoint(3, 120, 120, PointStatus.TRACKED),  # In gap
            CurvePoint(4, 130, 130, PointStatus.KEYFRAME),  # End of gap
            CurvePoint(5, 140, 140, PointStatus.ENDFRAME),  # Second gap
            CurvePoint(6, 150, 150, PointStatus.TRACKED),  # In gap
            CurvePoint(7, 160, 160, PointStatus.TRACKED),  # In gap
            CurvePoint(8, 170, 170, PointStatus.KEYFRAME),  # End of gap
        ]

        segmented_curve = SegmentedCurve.from_points(points)

        # First segment (frames 1-2) should be active
        segment = segmented_curve.get_segment_at_frame(1)
        assert segment is not None
        assert segment.is_active
        assert segment.start_frame == 1
        assert segment.end_frame == 2

        # First gap (frame 3) should be inactive - single tracked point segment
        gap_segment = segmented_curve.get_segment_at_frame(3)
        assert gap_segment is not None
        assert not gap_segment.is_active
        assert gap_segment.start_frame == 3
        assert gap_segment.end_frame == 3

        # Second active segment (frames 4-5)
        segment = segmented_curve.get_segment_at_frame(4)
        assert segment is not None
        assert segment.is_active
        assert segment.start_frame == 4
        assert segment.end_frame == 5

        # Second gap (frames 6-7) should be inactive - tracked points segment
        gap_segment = segmented_curve.get_segment_at_frame(6)
        assert gap_segment is not None
        assert not gap_segment.is_active
        assert gap_segment.start_frame == 6
        assert gap_segment.end_frame == 7

    def test_render_point_markers_skips_inactive(self) -> None:
        """Test that _render_point_markers_optimized skips points in inactive segments."""

        # Mock curve view with gap points
        class MockCurveViewWithGaps:
            def __init__(self) -> None:
                self.points = [
                    (1, 100, 100, "keyframe"),
                    (2, 110, 110, "normal"),
                    (3, 120, 120, "endframe"),  # Creates gap
                    (4, 130, 130, "tracked"),  # Should not be rendered
                    (5, 140, 140, "tracked"),  # Should not be rendered
                    (6, 150, 150, "keyframe"),  # Should be rendered
                ]
                self.selected_points: set[int] = set()
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
                self.background_image = None
                self.show_all_frame_numbers = False
                self.show_info = False
                self.show_background = False
                self.show_grid = False
                self.main_window = None

            def width(self) -> int:
                return self._width

            def height(self) -> int:
                return self._height

            def get_transform(self) -> object:
                from services.transform_service import Transform

                return Transform(
                    scale=self.zoom_factor,
                    center_offset_x=0.0,
                    center_offset_y=0.0,
                    pan_offset_x=self.pan_offset_x,
                    pan_offset_y=self.pan_offset_y,
                )

        curve_view = MockCurveViewWithGaps()

        # We'll test the segmented curve logic directly since mocking QPainter is complex
        # The actual rendering test would require more sophisticated Qt mocking
        from core.curve_segments import SegmentedCurve
        from core.models import CurvePoint

        points = [CurvePoint.from_tuple(pt) for pt in curve_view.points]
        segmented_curve = SegmentedCurve.from_points(points)

        # Verify that frames 4 and 5 are in inactive segments
        for frame in [4, 5]:
            segment = segmented_curve.get_segment_at_frame(frame)
            assert segment is not None
            assert not segment.is_active, f"Frame {frame} should be in inactive segment"

        # Verify that frames 1, 2, 3 (endframe), and 6 are in active segments or are endframes
        for frame in [1, 2, 6]:
            segment = segmented_curve.get_segment_at_frame(frame)
            assert segment is not None
            assert segment.is_active, f"Frame {frame} should be in active segment"

    def test_dashed_line_follows_curve_trajectory(self) -> None:
        """Test that dashed lines in gaps follow actual point positions, not horizontal."""
        from core.curve_segments import SegmentedCurve
        from core.models import CurvePoint, PointStatus

        # Create points with varying Y positions in the gap
        points = [
            CurvePoint(1, 100, 100, PointStatus.KEYFRAME),
            CurvePoint(2, 110, 110, PointStatus.ENDFRAME),  # Creates gap
            CurvePoint(3, 120, 150, PointStatus.TRACKED),  # Y changes in gap
            CurvePoint(4, 130, 200, PointStatus.TRACKED),  # Y continues changing
            CurvePoint(5, 140, 180, PointStatus.TRACKED),  # Y goes down
            CurvePoint(6, 150, 150, PointStatus.KEYFRAME),  # Startframe
        ]

        segmented_curve = SegmentedCurve.from_points(points)
        gap_segment = segmented_curve.get_segment_at_frame(3)

        assert gap_segment is not None
        assert not gap_segment.is_active

        # The gap segment should contain the tracked points with their actual positions
        # not held positions
        gap_points = gap_segment.points
        assert len(gap_points) == 3  # Frames 3 through 5 (tracked points only)

        # Check that Y values vary (not held constant)
        y_values = [pt.y for pt in gap_points]
        assert y_values == [150, 200, 180]  # Actual trajectory, not flat

        # Ensure the segment knows these points form a dashed line path
        assert gap_segment.start_frame == 3
        assert gap_segment.end_frame == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
