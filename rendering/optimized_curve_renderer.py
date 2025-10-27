#!/usr/bin/env python
"""
Optimized curve renderer with advanced performance techniques for CurveEditor.

This renderer addresses the critical performance issues identified in the analysis:
- Rendering drops to 3.9 FPS with 25K points
- Paint operations dominate rendering time (254ms for 25K points)
- Need for viewport culling, level-of-detail, and vectorized operations
"""
# pyright: reportImportCycles=false

import time
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap

from core.curve_segments import CurveSegment, SegmentedCurve
from core.defaults import GRID_CELL_SIZE, RENDER_PADDING
from core.logger_utils import get_logger
from core.models import CurvePoint
from ui.color_constants import CurveColors

if TYPE_CHECKING:
    from services.transform_service import Transform

    from .render_state import RenderState
else:
    Transform = object
    RenderState = object

# NumPy array type aliases - performance critical for vectorized operations
type FloatArray = NDArray[np.float64]  # np.ndarray with float64 elements
type IntArray = NDArray[np.int32]  # np.ndarray with int32 elements

logger = get_logger("optimized_curve_renderer")


class RenderQuality(Enum):
    """Rendering quality levels for adaptive performance."""

    DRAFT = "draft"  # Fast rendering for interaction
    NORMAL = "normal"  # Standard quality
    HIGH = "high"  # High quality for final display


class ViewportCuller:
    """Efficient viewport culling with spatial indexing."""

    def __init__(self):
        self._grid_size: float = GRID_CELL_SIZE  # Grid cell size for spatial indexing
        self._spatial_index: dict[tuple[int, int], list[int]] = {}

    def update_spatial_index(self, points: FloatArray, viewport: QRectF) -> None:  # pyright: ignore[reportUnusedParameter]
        """Update spatial index for the given points."""
        self._spatial_index.clear()

        if len(points) == 0:
            return

        # Create grid-based spatial index
        for i, (x, y) in enumerate(points):
            grid_x = int(x // self._grid_size)
            grid_y = int(y // self._grid_size)
            key = (grid_x, grid_y)

            if key not in self._spatial_index:
                self._spatial_index[key] = []
            self._spatial_index[key].append(i)

    def get_visible_points(self, points: FloatArray, viewport: QRectF, padding: float = 50) -> IntArray:
        """Get indices of points visible in viewport using spatial indexing."""
        if len(points) == 0:
            return np.array([], dtype=int)

        # Expand viewport by padding
        expanded = QRectF(
            viewport.x() - padding,
            viewport.y() - padding,
            viewport.width() + 2 * padding,
            viewport.height() + 2 * padding,
        )

        # Fast path: if we have many points, use spatial indexing
        if len(points) > 1000:
            return self._get_visible_points_spatial(points, expanded)
        else:
            return self._get_visible_points_simple(points, expanded)

    def _get_visible_points_spatial(self, points: FloatArray, viewport: QRectF) -> IntArray:
        """Use spatial index for large datasets."""
        visible: list[int] = []

        # Find grid cells that intersect with viewport
        min_grid_x = int(viewport.left() // self._grid_size) - 1
        max_grid_x = int(viewport.right() // self._grid_size) + 1
        min_grid_y = int(viewport.top() // self._grid_size) - 1
        max_grid_y = int(viewport.bottom() // self._grid_size) + 1

        # Check each intersecting grid cell
        for grid_x in range(min_grid_x, max_grid_x + 1):
            for grid_y in range(min_grid_y, max_grid_y + 1):
                key = (grid_x, grid_y)
                if key in self._spatial_index:
                    for idx in self._spatial_index[key]:
                        # Bounds check to prevent index errors
                        if 0 <= idx < len(points):
                            x, y = points[idx]
                            if viewport.contains(x, y):
                                visible.append(idx)

        return np.array(visible, dtype=int)

    def _get_visible_points_simple(self, points: FloatArray, viewport: QRectF) -> IntArray:
        """Simple viewport culling for smaller datasets."""
        if len(points) == 0:
            return np.array([], dtype=int)

        # Vectorized viewport test
        x_coords = points[:, 0]
        y_coords = points[:, 1]

        visible_mask = (
            (x_coords >= viewport.left())
            & (x_coords <= viewport.right())
            & (y_coords >= viewport.top())
            & (y_coords <= viewport.bottom())
        )

        return np.where(visible_mask)[0].astype(np.int32)


class LevelOfDetail:
    """Level-of-detail system for adaptive rendering."""

    def __init__(self):
        self._lod_thresholds: dict[RenderQuality, int] = {
            RenderQuality.DRAFT: 100,  # Target ~100 points for fast rendering
            RenderQuality.NORMAL: 1000,  # Target ~1000 points for normal quality
            RenderQuality.HIGH: 1,  # Show all points for high quality
        }

    def get_lod_points(
        self, points: FloatArray, quality: RenderQuality, visible_indices: IntArray | None = None
    ) -> tuple[FloatArray, int]:
        """Get points for the specified level of detail."""
        if len(points) == 0:
            return points, 1

        # Use visible indices if provided, otherwise use all points
        working_points = points[visible_indices] if visible_indices is not None and len(visible_indices) > 0 else points

        threshold = self._lod_thresholds[quality]

        # For high quality or small datasets, return all points
        if quality == RenderQuality.HIGH or len(working_points) <= threshold:
            return working_points, 1

        # Calculate step size for sub-sampling to get approximately 'threshold' points
        step = max(1, len(working_points) // threshold)
        # If step is 1, we need to increase it to actually reduce point count
        if step == 1:
            step = max(2, len(working_points) // threshold + 1)

        # Sub-sample points evenly
        sampled_indices = np.arange(0, len(working_points), step)
        lod_points = working_points[sampled_indices]

        return lod_points, step


class VectorizedTransform:
    """Vectorized coordinate transformation using NumPy."""

    @staticmethod
    def transform_points_batch(
        points: FloatArray,
        zoom: float,
        offset_x: float,
        offset_y: float,
        flip_y: bool = False,
        height: int = 0,
    ) -> FloatArray:
        """Transform all points in a single vectorized operation."""
        if len(points) == 0:
            return np.array([]).reshape(0, 2)

        # Extract x and y coordinates
        x_coords = points[:, 1] if points.shape[1] > 1 else points[:, 0]
        y_coords = points[:, 2] if points.shape[1] > 2 else points[:, 1]

        # Vectorized transformation
        screen_x = x_coords * zoom + offset_x
        screen_y = y_coords * zoom + offset_y

        # Apply Y-flip if needed
        if flip_y and height > 0:
            screen_y = height - screen_y

        # Stack coordinates into Nx2 array
        return np.column_stack((screen_x, screen_y))


class OptimizedCurveRenderer:
    """Optimized curve renderer with advanced performance techniques."""

    def __init__(self):
        """Initialize the optimized renderer."""
        self._viewport_culler: ViewportCuller = ViewportCuller()
        self._lod_system: LevelOfDetail = LevelOfDetail()
        self._render_quality: RenderQuality = RenderQuality.NORMAL

        # Performance tracking
        self._last_render_time: float = 0.0
        self._render_count: int = 0
        self._total_render_time: float = 0.0

        # Adaptive quality settings
        self._fps_target: float = 30.0
        self._quality_auto_adjust: bool = True
        self._last_fps: float = 60.0

        # Initialize cache variables
        self._last_point_count: int = 0

        # Caching
        self._last_viewport: QRectF | None = None
        self._cached_visible_indices: IntArray | None = None
        self._cache_valid: bool = False

        logger.info("OptimizedCurveRenderer initialized with adaptive quality")

    def set_render_quality(self, quality: RenderQuality) -> None:
        """Set the rendering quality level."""
        self._render_quality = quality
        self._quality_auto_adjust = False
        logger.info(f"Render quality set to {quality.value}")

    def enable_auto_quality(self, target_fps: float = 30.0) -> None:
        """Enable automatic quality adjustment based on performance."""
        self._quality_auto_adjust = True
        self._fps_target = target_fps
        logger.info(f"Auto quality enabled with {target_fps} FPS target")

    def _calculate_scaled_point_radius(self, base_radius: int | float, zoom_factor: float) -> float:
        """Calculate point radius scaled by zoom factor with constraints.

        Points should scale with zoom to maintain visual consistency - larger when
        zoomed in, smaller when zoomed out. This prevents points from being
        disproportionately large when viewing the full image.

        Args:
            base_radius: Base point radius in pixels at 1x zoom
            zoom_factor: Current zoom level

        Returns:
            Scaled radius constrained to reasonable bounds
        """
        # Scale radius linearly with zoom for more noticeable effect
        # At zoom=1.0, points are at base size
        # At zoom=0.1, points are 10% of base size
        scaled = base_radius * zoom_factor

        # Constrain to prevent points from being too large
        # Minimum 0.25 pixel - allows very small but still visible points when zoomed out
        min_radius = 0.25
        # Maximum respects user's point size preference (slider range: 2-20)
        # Multiplier of 2.5 allows reasonable zoom before clamping
        max_radius = base_radius * 2.5

        result = max(min_radius, min(max_radius, scaled))

        return result

    def _create_transform_from_render_state(self, render_state: "RenderState") -> "Transform":
        """
        Create a Transform object from RenderState properties.

        This method creates a transform that can convert data coordinates to screen coordinates
        using the view parameters stored in the RenderState.

        Args:
            render_state: The render state containing view parameters

        Returns:
            A Transform object for coordinate conversion
        """
        try:
            # Import TransformService to create the transform
            from services import get_transform_service
            from services.transform_service import ViewState

            transform_service = get_transform_service()

            # Create ViewState to match CurveViewWidget's approach
            # This ensures consistent transform behavior between widget and renderer
            display_width = render_state.image_width
            display_height = render_state.image_height

            # If we have a background image, use its dimensions
            if render_state.background_image:
                display_width = render_state.background_image.width()
                display_height = render_state.background_image.height()

            view_state = ViewState(
                display_width=display_width,
                display_height=display_height,
                widget_width=render_state.widget_width,
                widget_height=render_state.widget_height,
                zoom_factor=render_state.zoom_factor,
                offset_x=render_state.pan_offset_x,
                offset_y=render_state.pan_offset_y,
                scale_to_image=True,  # Always true for rendering
                flip_y_axis=render_state.flip_y_axis,
                manual_x_offset=render_state.manual_offset_x,
                manual_y_offset=render_state.manual_offset_y,
                background_image=render_state.background_image,
                image_width=render_state.image_width,
                image_height=render_state.image_height,
            )

            # Use the same method as CurveViewWidget
            return transform_service.create_transform_from_view_state(view_state)
        except Exception as e:
            logger.warning(f"Failed to create transform from render state: {e}")
            # Return a simple mock transform if creation fails
            from types import SimpleNamespace

            return SimpleNamespace(
                data_to_screen=lambda x, y: (x * render_state.zoom_factor, y * render_state.zoom_factor)
            )  # pyright: ignore[reportReturnType]

    def render(self, painter: QPainter, _event: object | None, render_state: "RenderState") -> None:
        """Render complete curve view with optimized performance."""
        start_time = time.perf_counter()
        self._render_count += 1

        # Null safety check - early return if visual settings missing
        if not render_state.visual:
            logger.warning("No visual settings in RenderState - skipping render")
            return

        # Auto-adjust quality based on performance
        if self._quality_auto_adjust:
            self._adjust_quality_for_performance()

        # Save painter state
        painter.save()

        try:
            # Render background if available
            show_bg = render_state.show_background
            bg_img = render_state.background_image
            if show_bg and bg_img:
                self._render_background_optimized(painter, render_state)

            # Render grid if needed
            if render_state.visual.show_grid:
                self._render_grid_optimized(painter, render_state)

            # Check if render_state supports multi-curve rendering
            from core.display_mode import DisplayMode

            has_multi_curve = render_state.curves_data is not None
            is_multi_curve_mode = render_state.display_mode in (DisplayMode.ALL_VISIBLE, DisplayMode.SELECTED)

            if has_multi_curve and render_state.curves_data and is_multi_curve_mode:
                # Render multiple curves (all visible or selected based on display mode)
                self._render_multiple_curves(painter, render_state)
            else:
                # Render single curve with advanced optimizations (backward compatibility)
                if render_state.points:
                    self._render_points_ultra_optimized(painter, render_state)

            # Render info overlay (skip in test environments due to text rendering issues)
            import os

            if os.getenv("PYTEST_CURRENT_TEST") is None:
                self._render_info_optimized(painter, render_state)

        finally:
            # Restore painter state
            painter.restore()

        # Update performance metrics
        render_time = time.perf_counter() - start_time
        self._last_render_time = render_time
        self._total_render_time += render_time

        # Calculate FPS
        if render_time > 0:
            current_fps = 1.0 / render_time
            self._last_fps = 0.9 * self._last_fps + 0.1 * current_fps  # Smoothed FPS

        # Log performance periodically
        if self._render_count % 60 == 0:  # Every 60 frames
            avg_time = self._total_render_time / self._render_count
            avg_fps = 1.0 / avg_time if avg_time > 0 else 0
            logger.debug(
                f"Render stats: {avg_fps:.1f} avg FPS, {render_time * 1000:.2f}ms last frame, quality: {self._render_quality.value}"
            )

    def _render_points_ultra_optimized(self, painter: QPainter, render_state: "RenderState") -> None:
        """Ultra-optimized point rendering with all techniques combined."""
        points = render_state.points
        if not points:
            logger.warning("No points to render - curve_view.points is empty")
            return

        # Convert to NumPy array for vectorized operations
        if not isinstance(points, np.ndarray):
            # Convert list of tuples to NumPy array - handle variable tuple lengths
            try:
                # Extract frame, x, y from tuples (ignore optional 4th element)
                point_data = np.array([(p[0], p[1], p[2]) for p in points if len(p) >= 3])
            except (IndexError, TypeError):
                # Fallback if points format is unexpected
                return
        else:
            point_data = points

        # Get viewport for culling
        viewport = QRectF(0, 0, render_state.widget_width, render_state.widget_height)

        # Check if viewport or point count changed
        viewport_changed = self._last_viewport != viewport
        point_count_changed = self._last_point_count != len(point_data)

        if viewport_changed or point_count_changed:
            self._last_viewport = viewport
            self._last_point_count = len(point_data)
            self._cache_valid = False

            # Initialize point count if not set
            # Initialize cache if not present - _last_point_count is always initialized in __init__
            # This check is redundant but kept for defensive programming

            # Transform all points using the Transform service for consistency with background
            transform = self._create_transform_from_render_state(render_state)
            # Transform each point through the same pipeline as background
            screen_points = np.zeros((len(point_data), 2))
            for i, point in enumerate(point_data):
                x, y = transform.data_to_screen(point[1], point[2])
                screen_points[i] = [x, y]
        else:
            # Fallback to old method if transform not available
            zoom = render_state.zoom_factor

            # Calculate center offset (like in Transform)
            image_width = render_state.image_width
            image_height = render_state.image_height
            scaled_width = image_width * zoom
            scaled_height = image_height * zoom
            center_x = (render_state.widget_width - scaled_width) / 2
            center_y = (render_state.widget_height - scaled_height) / 2

            # Calculate total offsets (center + pan + manual)
            offset_x = center_x + render_state.pan_offset_x + render_state.manual_offset_x
            offset_y = center_y + render_state.pan_offset_y + render_state.manual_offset_y

            screen_points = VectorizedTransform.transform_points_batch(
                point_data,
                zoom,
                offset_x,
                offset_y,
                render_state.flip_y_axis,
                render_state.widget_height,
            )

        # Viewport culling - get visible points
        if not self._cache_valid or viewport_changed or point_count_changed:
            self._cached_visible_indices = self._viewport_culler.get_visible_points(
                screen_points, viewport, padding=RENDER_PADDING
            )
            self._cache_valid = True

        visible_indices = self._cached_visible_indices

        # Early exit if no points are visible
        if visible_indices is None or len(visible_indices) == 0:
            logger.warning(f"No visible points after culling! Total points: {len(screen_points)}, Viewport: {viewport}")
            if len(screen_points) > 0:
                logger.warning(f"Sample screen points: {screen_points[:3]}")
            return

        # Validate indices are within bounds
        max_index = len(screen_points) - 1
        if max_index >= 0:
            # At this point visible_indices is guaranteed to not be None due to check above
            assert visible_indices is not None
            visible_indices = visible_indices[visible_indices <= max_index]

        # Apply level of detail
        visible_screen_points = screen_points[visible_indices]
        lod_points, step = self._lod_system.get_lod_points(visible_screen_points, self._render_quality, None)

        # Get curve data for status checking
        curve_data = render_state.points

        # Render lines using unified method that respects segments and LOD
        # Check ALL points to ensure we detect endframes anywhere in curve
        has_status = any(len(pt) > 3 for pt in curve_data if pt)
        if has_status:
            # Use all points for segmented rendering (preserves segment boundaries)
            self._render_lines_with_segments(
                painter=painter,
                render_state=render_state,
                curve_data=curve_data,
                screen_points=screen_points,
                curve_color=None,  # Use default white
                line_width=2,
            )
        else:
            # Use LOD points for simple rendering (performance optimization for legacy data)
            self._render_lines_with_segments(
                painter=painter,
                render_state=render_state,
                curve_data=curve_data,
                screen_points=lod_points,
                curve_color=None,  # Use default white
                line_width=2,
            )

        # Render points with batching
        self._render_point_markers_optimized(painter, render_state, lod_points, visible_indices, step)

        # Render state labels for selected points and current frame
        if has_status:
            self._render_point_state_labels(painter, render_state, lod_points, visible_indices, curve_data)

        # Render frame numbers if enabled (with heavy culling)
        # Note: show_all_frame_numbers is an optional future feature - not in current RenderState
        # Future enhancement: Add show_all_frame_numbers to RenderState for debug visualization
        # if render_state.show_all_frame_numbers and self._render_quality == RenderQuality.HIGH:
        #     self._render_frame_numbers_optimized(painter, render_state, lod_points, visible_indices, step)

    def _render_lines_optimized(self, painter: QPainter, screen_points: FloatArray, _step: int) -> None:
        """Render lines between points using optimized QPainterPath."""
        if len(screen_points) < 2:
            return

        # Set line style
        pen = CurveColors.get_active_pen()
        painter.setPen(pen)

        # Use QPainterPath for batch line drawing
        line_path = QPainterPath()

        # Start path at first point
        first_point = screen_points[0]
        line_path.moveTo(first_point[0], first_point[1])

        # Add lines to remaining points
        for i in range(1, len(screen_points)):
            point = screen_points[i]
            line_path.lineTo(point[0], point[1])

        # Draw all lines at once
        painter.drawPath(line_path)

    def _render_segmented_lines(
        self,
        painter: QPainter,
        _render_state: "RenderState",
        curve_data: list[
            tuple[int, float, float] | tuple[int, float, float, str] | tuple[int, float, float, str | bool]
        ],
        screen_points: FloatArray,
        _visible_indices: IntArray,
    ) -> None:
        """Render lines respecting curve segments (gaps at ENDFRAME points).

        Args:
            painter: QPainter for rendering
            curve_view: CurveView instance
            curve_data: Original curve data with status
            screen_points: Transformed screen coordinates
            visible_indices: Indices of visible points
        """
        if len(screen_points) < 2 or len(curve_data) < 2:
            return

        # Create segmented curve from data
        points = [CurvePoint.from_tuple(pt) for pt in curve_data]
        segmented_curve = SegmentedCurve.from_points(points)

        # Set line styles for different segment types
        active_pen = CurveColors.get_active_pen()
        inactive_pen = CurveColors.get_inactive_pen()

        # Create frame-to-index mapping for O(1) lookups
        frame_to_index = {pt[0]: i for i, pt in enumerate(curve_data)}

        # Draw each segment separately
        for segment in segmented_curve.segments:
            if segment.point_count == 0:
                continue

            if segment.is_active:
                # Draw active segments with regular line connections
                self._draw_active_segment(painter, segment, screen_points, frame_to_index, active_pen)
            else:
                # Draw inactive segments as held position gaps
                self._draw_gap_segment(painter, segment, segmented_curve, screen_points, frame_to_index, inactive_pen)

    def _draw_active_segment(
        self,
        painter: QPainter,
        segment: "CurveSegment",
        screen_points: FloatArray,
        frame_to_index: dict[int, int],
        pen: QPen,
    ) -> None:
        """Draw an active segment with normal line connections.

        Args:
            painter: Qt painter for drawing
            segment: The active segment to draw
            screen_points: Array of screen coordinates
            frame_to_index: Mapping from frame numbers to indices
            pen: Pen to use for drawing
        """
        if segment.point_count < 2:
            return

        painter.setPen(pen)
        segment_path = QPainterPath()

        # Find screen points for this segment
        first_in_segment = True
        for point in segment.points:
            # Find this point's index in the original data (O(1) lookup)
            point_idx = frame_to_index.get(point.frame, -1)

            if point_idx >= 0 and point_idx < len(screen_points):
                screen_pos = screen_points[point_idx]
                if first_in_segment:
                    segment_path.moveTo(screen_pos[0], screen_pos[1])
                    first_in_segment = False
                else:
                    # Don't connect to ENDFRAME points
                    if not point.is_endframe:
                        segment_path.lineTo(screen_pos[0], screen_pos[1])

        painter.drawPath(segment_path)

    def _draw_gap_segment(
        self,
        painter: QPainter,
        segment: "CurveSegment",
        _segmented_curve: "SegmentedCurve",
        screen_points: FloatArray,
        frame_to_index: dict[int, int],
        pen: QPen,
    ) -> None:
        """Draw an inactive segment with dashed lines following actual tracked positions.

        Shows dashed lines connecting the tracked points in the inactive segment,
        visualizing the tracked data that is held but not active.

        Args:
            painter: Qt painter for drawing
            segment: The inactive segment to draw
            segmented_curve: The complete segmented curve for context
            screen_points: Array of screen coordinates
            frame_to_index: Mapping from frame numbers to indices
            pen: Pen to use for drawing (should be dashed)
        """
        painter.setPen(pen)

        # Draw dashed lines connecting the actual tracked points in the segment
        if segment.point_count > 1:
            gap_path = QPainterPath()
            first_point = True

            for point in segment.points:
                # Get the screen position for this point
                point_idx = frame_to_index.get(point.frame, -1)

                if point_idx >= 0 and point_idx < len(screen_points):
                    screen_x = screen_points[point_idx][0]
                    screen_y = screen_points[point_idx][1]

                    if first_point:
                        gap_path.moveTo(screen_x, screen_y)
                        first_point = False
                    else:
                        gap_path.lineTo(screen_x, screen_y)

            # Draw the dashed path
            if not first_point:  # Only draw if we had at least one valid point
                painter.drawPath(gap_path)

    def _render_lines_with_segments(
        self,
        painter: QPainter,
        render_state: "RenderState",
        curve_data: Sequence[
            tuple[int, float, float] | tuple[int, float, float, str] | tuple[int, float, float, str | bool]
        ],
        screen_points: FloatArray,
        curve_color: QColor | None = None,
        line_width: int = 2,
    ) -> None:
        """Unified line rendering with optional segment support for gaps.

        This method consolidates line rendering logic to ensure consistent behavior
        between single and multi-curve rendering paths. It automatically detects
        whether status information is available and renders accordingly.

        Args:
            painter: Qt painter for drawing
            curve_view: The curve view widget
            curve_data: Original curve data with optional status information
            screen_points: Transformed screen coordinates
            curve_color: Color for the lines (default white)
            line_width: Width of the lines (default 2)
        """
        if len(screen_points) < 2 or len(curve_data) < 2:
            return

        # Set default color if not provided
        if curve_color is None:
            curve_color = CurveColors.WHITE

        # Check if we have status information to determine rendering approach
        # Check ALL points to ensure we detect endframes anywhere in curve
        has_status = any(len(pt) > 3 for pt in curve_data if pt)

        if has_status:
            # Render with segment awareness (gaps at ENDFRAME points)
            self._render_lines_segmented_aware(
                painter, render_state, curve_data, screen_points, curve_color, line_width
            )
        else:
            # Render simple continuous lines
            self._render_lines_simple(painter, screen_points, curve_color, line_width)

    def _render_lines_segmented_aware(
        self,
        painter: QPainter,
        _render_state: "RenderState",
        curve_data: Sequence[
            tuple[int, float, float] | tuple[int, float, float, str] | tuple[int, float, float, str | bool]
        ],
        screen_points: FloatArray,
        curve_color: QColor,
        line_width: int,
    ) -> None:
        """Render lines with segment awareness for gaps at ENDFRAME points."""
        # ALWAYS create SegmentedCurve from the curve_data being rendered
        # This ensures correct segmentation for multi-curve rendering where each curve
        # has its own segment structure (DataService only stores ONE curve's segments)
        points = [CurvePoint.from_tuple(pt) for pt in curve_data]
        segmented_curve = SegmentedCurve.from_points(points)


        # Set line styles for different segment types
        active_pen = CurveColors.get_active_pen(color=curve_color, width=line_width)
        inactive_pen = CurveColors.get_inactive_pen(width=max(1, line_width - 1))

        # Create frame-to-index mapping for O(1) lookups
        frame_to_index = {pt[0]: i for i, pt in enumerate(curve_data)}

        # Draw each segment separately
        for segment in segmented_curve.segments:
            if segment.point_count == 0:
                continue

            if segment.is_active:
                # Draw active segments with regular line connections
                self._draw_active_segment(painter, segment, screen_points, frame_to_index, active_pen)
            else:
                # Draw inactive segments as held position gaps
                self._draw_gap_segment(painter, segment, segmented_curve, screen_points, frame_to_index, inactive_pen)

    def _render_lines_simple(
        self,
        painter: QPainter,
        screen_points: FloatArray,
        curve_color: QColor,
        line_width: int,
    ) -> None:
        """Render simple continuous lines between all points."""
        pen = QPen(curve_color)
        pen.setWidth(line_width)
        painter.setPen(pen)

        # Use QPainterPath for batch line drawing
        line_path = QPainterPath()

        # Start path at first point
        first_point = screen_points[0]
        line_path.moveTo(first_point[0], first_point[1])

        # Add lines to remaining points
        for i in range(1, len(screen_points)):
            point = screen_points[i]
            line_path.lineTo(point[0], point[1])

        # Draw all lines at once
        painter.drawPath(line_path)

    def _render_points_with_status(
        self,
        painter: QPainter,
        render_state: "RenderState",
        screen_points: FloatArray,
        points_data: Sequence[
            tuple[int, float, float] | tuple[int, float, float, str] | tuple[int, float, float, str | bool]
        ],
        visible_indices: IntArray | None = None,
        step: int = 1,
        base_point_radius: float | None = None,
        curve_color: QColor | None = None,
        is_active_curve: bool = True,
    ) -> None:
        """Unified point rendering with status, selection, and current frame highlighting.

        Args:
            painter: Qt painter for drawing
            curve_view: The curve view widget
            screen_points: Array of screen coordinates
            points_data: Original point data with status information
            visible_indices: Indices mapping screen points to original data (for LOD)
            step: Step size for LOD (default 1 for no LOD)
            base_point_radius: Override point radius (uses curve_view.point_radius if None)
            curve_color: Base color for the curve (used for inactive curves)
            is_active_curve: Whether this is the active curve
        """
        if len(screen_points) == 0:
            return

        # Null safety check for visual settings
        if not render_state.visual:
            logger.warning("No visual settings - skipping point rendering")
            return

        # Get base radius (unscaled) - use visual settings directly
        base_radius = base_point_radius if base_point_radius is not None else render_state.visual.point_radius
        # Scale radius based on zoom for visual consistency
        point_radius = self._calculate_scaled_point_radius(base_radius, render_state.zoom_factor)
        selected_points = render_state.selected_points

        # Get current frame directly from render_state
        current_frame = render_state.current_frame

        # Import PointStatus for status checking
        from core.models import PointStatus

        # Create SegmentedCurve to check for inactive segments
        # Only create if we have status information
        # Check ALL points, not just first 100, to ensure we detect endframes anywhere in curve
        segmented_curve = None
        has_status = any(len(pt) > 3 for pt in points_data if pt)
        if has_status:
            points = [CurvePoint.from_tuple(pt) for pt in points_data]
            segmented_curve = SegmentedCurve.from_points(points)

        # Batch points by state for efficient rendering
        points_by_status: dict[str, list[Any]] = {
            "normal": [],
            "keyframe": [],
            "tracked": [],
            "interpolated": [],
            "endframe": [],
        }
        selected_points_list: list[Any] = []
        current_frame_points: list[Any] = []

        for i, screen_pos in enumerate(screen_points):
            # Map back to original index (accounting for LOD step)
            if visible_indices is not None:
                original_idx = visible_indices[i * step] if i * step < len(visible_indices) else -1
            else:
                # Direct mapping when no LOD is used
                original_idx = i

            # Check if this point is on the current frame
            is_current_frame = False
            status = "normal"  # Default status
            frame = -1  # Initialize frame

            if 0 <= original_idx < len(points_data):
                point_data = points_data[original_idx]
                # Extract frame from point tuple (frame is first element)
                if len(point_data) >= 3:
                    frame = point_data[0]
                    is_current_frame = frame == current_frame

                    # Check for status (4th element if present)
                    if len(point_data) > 3:
                        status_value = point_data[3]
                        if isinstance(status_value, str):
                            # Map string status to our categories
                            if status_value == PointStatus.KEYFRAME.value:
                                status = "keyframe"
                            elif status_value == PointStatus.TRACKED.value:
                                status = "tracked"
                            elif status_value == PointStatus.INTERPOLATED.value:
                                status = "interpolated"
                            elif status_value == PointStatus.ENDFRAME.value:
                                status = "endframe"

            # Skip rendering points in inactive segments (show only dashed line)
            if segmented_curve and frame != -1:
                segment = segmented_curve.get_segment_at_frame(frame)
                if segment and not segment.is_active:
                    continue  # Don't render points in inactive gap segments

            if is_current_frame:
                current_frame_points.append(screen_pos)
            elif original_idx in selected_points:
                selected_points_list.append(screen_pos)
            else:
                points_by_status[status].append(screen_pos)

        # Set painter for point drawing
        painter.setPen(Qt.PenStyle.NoPen)

        # Import centralized colors
        from ui.color_manager import SPECIAL_COLORS, get_status_color

        # Draw points in order: endframe, interpolated, normal, tracked, keyframe
        # (so more important statuses appear on top)
        draw_order = ["endframe", "interpolated", "normal", "tracked", "keyframe"]

        for status in draw_order:
            if points_by_status[status]:
                if is_active_curve or status != "normal":
                    # Use status color for active curves or special statuses
                    color = get_status_color(status)
                else:
                    # Use base curve color for normal points on inactive curves
                    color = curve_color.name() if curve_color else get_status_color(status)

                painter.setBrush(QBrush(QColor(color)))
                for pos in points_by_status[status]:
                    painter.drawEllipse(QPointF(pos[0], pos[1]), point_radius, point_radius)

        # Draw selected points on top with larger radius (use visual.selected_point_radius directly)
        if selected_points_list:
            painter.setBrush(QBrush(QColor(SPECIAL_COLORS["selected_point"])))
            # Use visual.selected_point_radius, scaled by zoom for consistency
            selected_radius = self._calculate_scaled_point_radius(
                render_state.visual.selected_point_radius, render_state.zoom_factor
            )
            for pos in selected_points_list:
                painter.drawEllipse(QPointF(pos[0], pos[1]), selected_radius, selected_radius)

        # Draw current frame points with purple color and larger radius
        if current_frame_points:
            painter.setBrush(QBrush(QColor(SPECIAL_COLORS["current_frame"])))  # Magenta for current frame
            # Current frame uses selected_point_radius + 1 for visual hierarchy
            current_frame_radius = self._calculate_scaled_point_radius(
                render_state.visual.selected_point_radius + 1, render_state.zoom_factor
            )
            for pos in current_frame_points:
                painter.drawEllipse(QPointF(pos[0], pos[1]), current_frame_radius, current_frame_radius)

    def _render_point_markers_optimized(
        self,
        painter: QPainter,
        render_state: "RenderState",
        screen_points: FloatArray,
        visible_indices: IntArray,
        step: int,
    ) -> None:
        """Render point markers with selection and current frame highlighting."""
        # Use the unified rendering method
        self._render_points_with_status(
            painter=painter,
            render_state=render_state,
            screen_points=screen_points,
            points_data=render_state.points,
            visible_indices=visible_indices,
            step=step,
        )

    def _render_frame_numbers_optimized(
        self,
        painter: QPainter,
        render_state: "RenderState",
        screen_points: FloatArray,
        visible_indices: IntArray,
        step: int,
    ) -> None:
        """Render frame numbers with heavy culling for performance."""
        if len(screen_points) == 0:
            return

        # Only show frame numbers for a subset of points to avoid clutter
        max_labels = 50  # Maximum number of labels to show
        label_step = len(screen_points) // max_labels if len(screen_points) > max_labels else 1

        from ui.color_manager import COLORS_DARK

        painter.setPen(QPen(QColor(COLORS_DARK["text_primary"])))
        font = QFont("Arial", 8)  # Smaller font for performance
        painter.setFont(font)

        points = render_state.points
        for i in range(0, len(screen_points), label_step):
            screen_pos = screen_points[i]
            # Map back to original index
            original_idx = visible_indices[i * step] if i * step < len(visible_indices) else -1

            if 0 <= original_idx < len(points):
                frame_num = points[original_idx][0]
                painter.drawText(int(screen_pos[0] + 10), int(screen_pos[1] - 10), f"F{frame_num}")

    def _render_point_state_labels(
        self,
        painter: QPainter,
        render_state: "RenderState",
        screen_points: FloatArray,
        visible_indices: IntArray,
        curve_data: list[
            tuple[int, float, float] | tuple[int, float, float, str] | tuple[int, float, float, str | bool]
        ],
    ) -> None:
        """Render state labels next to points (keyframe, tracked, endframe, etc).

        Args:
            painter: QPainter for rendering
            curve_view: CurveView instance
            screen_points: Transformed screen coordinates
            visible_indices: Indices of visible points
            curve_data: Original curve data with status
        """
        if len(screen_points) == 0:
            return

        # Only show labels for selected points and current frame
        selected_points = render_state.selected_points
        # Get current frame directly from render_state
        current_frame = render_state.current_frame

        # Convert to CurvePoints for status checking
        points_list = [CurvePoint.from_tuple(pt) for pt in curve_data]

        # Set up text rendering
        font = QFont("Arial", 9, QFont.Weight.Bold)
        painter.setFont(font)

        # Import centralized colors for state labels
        from ui.color_manager import get_status_color

        # Define colors for different states from centralized source
        state_colors = {}
        for status in ["keyframe", "tracked", "endframe", "interpolated", "normal"]:
            hex_color = get_status_color(status)
            q_color = QColor(hex_color)
            q_color.setAlpha(200)  # Add transparency
            state_colors[status] = q_color
        # Startframe uses keyframe color
        state_colors["startframe"] = state_colors["keyframe"]

        for i, screen_pos in enumerate(screen_points):
            # Map to original index
            original_idx = visible_indices[i] if i < len(visible_indices) else -1

            if 0 <= original_idx < len(points_list):
                point = points_list[original_idx]

                # Only show label for selected or current frame points
                show_label = original_idx in selected_points or point.frame == current_frame

                if show_label:
                    # Get contextual label
                    prev_point = points_list[original_idx - 1] if original_idx > 0 else None
                    label = point.get_contextual_status_label(prev_point)

                    # Set color based on status
                    color = state_colors.get(label, state_colors["normal"])
                    painter.setPen(QPen(color))

                    # Draw label offset from point
                    label_x = int(screen_pos[0] + 15)
                    label_y = int(screen_pos[1] + 5)
                    painter.drawText(label_x, label_y, label.upper())

    def _render_multiple_curves(self, painter: QPainter, render_state: "RenderState") -> None:
        """Render multiple curves with different colors and styles.

        Performance Optimization:
            Uses pre-computed visible_curves set from RenderState instead of
            checking metadata and display mode for each curve. This eliminates
            redundant visibility checks and improves rendering performance.

        Args:
            painter: Qt painter for drawing
            render_state: The render state with multi-curve support and pre-computed visibility
        """
        if not render_state.curves_data:
            logger.warning("_render_multiple_curves: no curves_data in RenderState")
            return

        # Null safety check for visual settings
        if not render_state.visual:
            logger.warning("No visual settings - skipping multi-curve rendering")
            return

        curves_data = render_state.curves_data
        curve_metadata = render_state.curve_metadata or {}
        active_curve = render_state.active_curve_name
        selected_curves_ordered = render_state.selected_curves_ordered or []
        visible_curves = render_state.visible_curves

        # Get transform once for all curves
        transform = self._create_transform_from_render_state(render_state)

        for curve_name, curve_points in curves_data.items():
            if not curve_points:
                continue

            # Visibility check: use pre-computed visibility from RenderState
            if visible_curves is None or curve_name not in visible_curves:
                continue

            # Determine curve styling
            is_active = curve_name == active_curve
            metadata = curve_metadata.get(curve_name, {})

            # Determine if this is the second selected curve for visual differentiation
            is_second_selected = (
                len(selected_curves_ordered) >= 2
                and curve_name == selected_curves_ordered[-2]  # Second-to-last (first non-active)
            )

            # Choose color based on selection order
            if is_second_selected:
                # Second selected curve gets cyan color for differentiation
                curve_color = QColor("#00FFFF")  # Cyan
            else:
                color_str = metadata.get("color", "#FFFFFF")
                curve_color = QColor(color_str)

            # Adjust opacity for inactive curves (but keep second selected more visible)
            if not is_active and not is_second_selected:
                curve_color.setAlpha(128)  # 50% opacity for other inactive curves
            elif is_second_selected:
                curve_color.setAlpha(200)  # 78% opacity for second selected (still highlighted)

            # Convert points to NumPy array
            try:
                point_data = np.array([(p[0], p[1], p[2]) for p in curve_points if len(p) >= 3])
            except (IndexError, TypeError):
                continue

            if len(point_data) == 0:
                continue

            # Transform points to screen coordinates
            screen_points = np.zeros((len(point_data), 2))
            for i, point in enumerate(point_data):
                x, y = transform.data_to_screen(point[1], point[2])
                screen_points[i] = [x, y]

            # Render curve lines using unified segmented rendering
            if len(screen_points) > 1:
                # Use visual.selected_line_width for active curve, visual.line_width for inactive
                line_width = render_state.visual.selected_line_width if is_active else render_state.visual.line_width
                self._render_lines_with_segments(
                    painter=painter,
                    render_state=render_state,
                    curve_data=curve_points,
                    screen_points=screen_points,
                    curve_color=curve_color,
                    line_width=line_width,
                )

            # Render points using unified status-aware rendering
            # Use visual.selected_point_radius for active curve, visual.point_radius for inactive
            point_radius = render_state.visual.selected_point_radius if is_active else render_state.visual.point_radius

            # Use the unified point rendering that handles status, selection, and current frame
            self._render_points_with_status(
                painter=painter,
                render_state=render_state,
                screen_points=screen_points,
                points_data=curve_points,
                visible_indices=None,  # No LOD for multi-curve rendering
                step=1,
                base_point_radius=point_radius,
                curve_color=curve_color,
                is_active_curve=is_active,
            )

            # Label active curve points with frame numbers if in debug mode
            # Future enhancement: Add show_all_frame_numbers to RenderState for debug visualization
            if is_active:
                for i, (x, y) in enumerate(screen_points):
                    # Skip points outside viewport
                    if x < -50 or x > render_state.widget_width + 50 or y < -50 or y > render_state.widget_height + 50:
                        continue
                    frame_num = int(point_data[i][0])
                    painter.drawText(QPointF(x + 10, y - 10), str(frame_num))

    def _render_background_optimized(self, painter: QPainter, render_state: "RenderState") -> None:
        """Optimized background rendering with proper transformations."""
        background_image = render_state.background_image
        if not background_image:
            return

        # Use fast scaling hint for better performance
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self._render_quality == RenderQuality.HIGH)

        # Get the transform from render_state to apply the same transformations as curve points
        transform = self._create_transform_from_render_state(render_state)

        # Cast background_image to proper type for type checker
        bg_image: QImage | QPixmap = background_image

        # Get image position - account for Y-flip
        # When Y-flip is enabled, the image's top-left in data space is at (0, image_height)
        # When Y-flip is disabled, the image's top-left in data space is at (0, 0)
        if transform.flip_y:
            # With Y-flip, image top is at Y=image_height in data space
            top_left_x, top_left_y = transform.data_to_screen(0, bg_image.height())
        else:
            # Without Y-flip, image top is at Y=0 in data space
            top_left_x, top_left_y = transform.data_to_screen(0, 0)

        # Calculate scaled dimensions directly like _paint_background does
        scale: float = transform.get_parameters()["scale"]  # pyright: ignore[reportAssignmentType]
        target_width = int(bg_image.width() * scale)
        target_height = int(bg_image.height() * scale)

        # Draw the background image scaled to fit the transformed rectangle
        # This ensures it goes through the exact same transformation as curve points
        # Convert QImage to QPixmap if needed
        pixmap = QPixmap.fromImage(bg_image) if isinstance(bg_image, QImage) else bg_image
        painter.drawPixmap(int(top_left_x), int(top_left_y), int(target_width), int(target_height), pixmap)

    def _render_grid_optimized(self, painter: QPainter, render_state: RenderState) -> None:
        """Optimized grid rendering with adaptive density, centered on selected points."""
        from ui.color_manager import COLORS_DARK

        grid_color = QColor(COLORS_DARK["grid_lines"])
        grid_color.setAlpha(50)
        pen = QPen(grid_color)
        pen.setWidth(1)
        painter.setPen(pen)

        # Grid spacing from visual settings
        zoom = render_state.zoom_factor
        if render_state.visual:
            base_step = render_state.visual.grid_size
        else:
            base_step = 50  # Fallback
        step = max(10, int(base_step / max(1, zoom / 2)))  # Adjust grid density with zoom

        width = render_state.widget_width
        height = render_state.widget_height

        # Calculate grid center based on selected points
        center_x = width // 2  # Default to widget center
        center_y = height // 2

        if render_state.selected_points:
            # Calculate center of selected points
            selected_indices = render_state.selected_points
            points = render_state.points

            sum_x = 0.0
            sum_y = 0.0
            count = 0

            for idx in selected_indices:
                if 0 <= idx < len(points):
                    point = points[idx]
                    # Handle different point tuple formats
                    if len(point) >= 3:
                        _, data_x, data_y = point[0], point[1], point[2]
                        sum_x += data_x
                        sum_y += data_y
                        count += 1

            if count > 0:
                # Get average position in data coordinates
                avg_x = sum_x / count
                avg_y = sum_y / count

                # Transform to screen coordinates
                transform = self._create_transform_from_render_state(render_state)
                screen_x, screen_y = transform.data_to_screen(avg_x, avg_y)
                center_x = int(screen_x)
                center_y = int(screen_y)

        # Calculate starting positions for grid lines aligned to center
        # This ensures grid lines pass through the center point
        start_x = center_x % step
        start_y = center_y % step

        # Vertical lines
        x = start_x
        while x < width:
            painter.drawLine(x, 0, x, height)
            x += step

        # Horizontal lines
        y = start_y
        while y < height:
            painter.drawLine(0, y, width, y)
            y += step

    def _render_info_optimized(self, painter: QPainter, render_state: "RenderState") -> None:
        """Render info overlay with performance metrics."""
        # Skip info rendering if show_info is explicitly False
        # Note: show_info is an optional future feature - not in current RenderState
        # Future enhancement: Add show_info to RenderState for selective info display

        from ui.color_manager import COLORS_DARK

        painter.setPen(QPen(QColor(COLORS_DARK["text_primary"])))
        painter.setFont(QFont("Arial", 10))

        points = render_state.points
        selected_points = render_state.selected_points
        zoom = render_state.zoom_factor

        info_text = f"Points: {len(points)}"
        if selected_points:
            info_text += f" | Selected: {len(selected_points)}"
        info_text += f" | Zoom: {zoom:.1f}x"

        # Add performance info
        info_text += f" | {self._last_fps:.1f} FPS"
        info_text += f" | Quality: {self._render_quality.value.upper()}"

        # Add optimization status (always show visible count for debugging)
        visible_count = len(self._cached_visible_indices) if self._cached_visible_indices is not None else 0
        info_text += f" | Visible: {visible_count}"

        # Only draw text if painter is active and in safe environment
        try:
            if painter.isActive():
                # Skip text rendering in test environments
                device = painter.device()  # device is non-None QPaintDevice
                if getattr(device, "width", None) is not None:
                    painter.drawText(10, 20, info_text)
        except Exception:
            # Silently skip text rendering if it fails (e.g., in headless tests)
            pass

    def _adjust_quality_for_performance(self) -> None:
        """Automatically adjust rendering quality based on performance."""
        if not self._quality_auto_adjust:
            return

        current_fps = self._last_fps
        target_fps = self._fps_target

        # Hysteresis to prevent oscillation
        if current_fps < target_fps * 0.8:  # 20% below target
            if self._render_quality == RenderQuality.HIGH:
                self._render_quality = RenderQuality.NORMAL
                logger.info(f"Quality reduced to NORMAL (FPS: {current_fps:.1f})")
            elif self._render_quality == RenderQuality.NORMAL:
                self._render_quality = RenderQuality.DRAFT
                logger.info(f"Quality reduced to DRAFT (FPS: {current_fps:.1f})")
        elif current_fps > target_fps * 1.5:  # 50% above target
            if self._render_quality == RenderQuality.DRAFT:
                self._render_quality = RenderQuality.NORMAL
                logger.info(f"Quality increased to NORMAL (FPS: {current_fps:.1f})")
            elif self._render_quality == RenderQuality.NORMAL:
                self._render_quality = RenderQuality.HIGH
                logger.info(f"Quality increased to HIGH (FPS: {current_fps:.1f})")

    def get_performance_stats(self) -> dict[str, float | int | bool | str]:
        """Get current performance statistics."""
        avg_time = self._total_render_time / max(1, self._render_count)
        return {
            "avg_fps": 1.0 / avg_time if avg_time > 0 else 0,
            "last_fps": self._last_fps,
            "last_render_ms": self._last_render_time * 1000,
            "render_count": self._render_count,
            "current_quality": self._render_quality.value,
            "auto_quality": self._quality_auto_adjust,
        }
