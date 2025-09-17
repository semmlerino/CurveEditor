#!/usr/bin/env python
"""
Optimized curve renderer with advanced performance techniques for CurveEditor.

This renderer addresses the critical performance issues identified in the analysis:
- Rendering drops to 3.9 FPS with 25K points
- Paint operations dominate rendering time (254ms for 25K points)
- Need for viewport culling, level-of-detail, and vectorized operations
"""

import logging
import time
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np

if TYPE_CHECKING:
    from services.transform_service import Transform
    from ui.state_manager import StateManager
else:
    Transform = object
    StateManager = object

# NumPy array type aliases - performance critical for vectorized operations
# Using Any to suppress type checker warnings while maintaining runtime performance
FloatArray = Any  # Float coordinate arrays (np.ndarray at runtime)
IntArray = Any  # Integer index arrays (np.ndarray at runtime)
from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen  # noqa: E402

from ui.ui_constants import GRID_CELL_SIZE, RENDER_PADDING  # noqa: E402


class CurveViewProtocol(Protocol):
    """Protocol for curve view objects used by the renderer."""

    # Required attributes
    points: list[tuple[int, float, float]] | list[tuple[int, float, float, str]]
    show_background: bool
    background_image: Any  # QImage or QPixmap at runtime
    show_grid: bool
    zoom_factor: float
    pan_offset_x: float
    pan_offset_y: float
    manual_offset_x: float
    manual_offset_y: float
    image_width: int
    image_height: int
    background_opacity: float
    selected_points: set[int]
    point_radius: int
    main_window: "MainWindowProtocol | None"

    # Optional attributes for debugging
    debug_mode: bool
    show_all_frame_numbers: bool
    flip_y_axis: bool

    def width(self) -> int: ...
    def height(self) -> int: ...
    def get_transform(self) -> Transform: ...


class MainWindowProtocol(Protocol):
    """Protocol for main window objects."""

    state_manager: "StateManager"  # Has current_frame attribute


logger = logging.getLogger("optimized_curve_renderer")


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
            return np.array([], dtype=int)  # pyright: ignore[reportPrivateImportUsage]

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
        visible = []

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
            return np.array([], dtype=int)  # pyright: ignore[reportPrivateImportUsage]

        # Vectorized viewport test
        x_coords = points[:, 0]
        y_coords = points[:, 1]

        visible_mask = (
            (x_coords >= viewport.left())
            & (x_coords <= viewport.right())
            & (y_coords >= viewport.top())
            & (y_coords <= viewport.bottom())
        )

        return np.where(visible_mask)[0]  # pyright: ignore[reportPrivateImportUsage]


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
        if visible_indices is not None and len(visible_indices) > 0:
            working_points = points[visible_indices]
        else:
            working_points = points

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
        sampled_indices = np.arange(0, len(working_points), step)  # pyright: ignore[reportPrivateImportUsage]
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
        self.background_opacity: float = 1.0
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

    def render(self, painter: QPainter, event: object | None, curve_view: CurveViewProtocol) -> None:
        """Render complete curve view with optimized performance."""
        start_time = time.perf_counter()
        self._render_count += 1

        # Auto-adjust quality based on performance
        if self._quality_auto_adjust:
            self._adjust_quality_for_performance()

        # Save painter state
        painter.save()

        try:
            # Render background if available
            show_bg = curve_view.show_background
            bg_img = curve_view.background_image
            print(f"[RENDERER] show_background: {show_bg}, has_background_image: {bg_img is not None}")
            if show_bg and bg_img:
                self._render_background_optimized(painter, curve_view)

            # Render grid if needed
            if curve_view.show_grid:
                self._render_grid_optimized(painter, curve_view)

            # Render curve points with advanced optimizations
            # points is defined in CurveViewProtocol
            if curve_view.points:
                self._render_points_ultra_optimized(painter, curve_view)

            # Render info overlay
            self._render_info_optimized(painter, curve_view)

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

    def _render_points_ultra_optimized(self, painter: QPainter, curve_view: CurveViewProtocol) -> None:
        """Ultra-optimized point rendering with all techniques combined."""
        points = curve_view.points
        if not points:
            logger.warning("No points to render - curve_view.points is empty")
            return

        logger.debug(f"Rendering {len(points)} points")

        # Convert to NumPy array for vectorized operations
        if not isinstance(points, np.ndarray):  # pyright: ignore[reportPrivateImportUsage]
            # Convert list of tuples to NumPy array - handle variable tuple lengths
            try:
                # Extract frame, x, y from tuples (ignore optional 4th element)
                point_data = np.array([(p[0], p[1], p[2]) for p in points if len(p) >= 3])  # pyright: ignore[reportPrivateImportUsage]
            except (IndexError, TypeError):
                # Fallback if points format is unexpected
                return
        else:
            point_data = points

        # Get viewport for culling
        viewport = QRectF(0, 0, curve_view.width(), curve_view.height())

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
            # get_transform is defined in CurveViewProtocol
            transform = curve_view.get_transform()
            # Transform each point through the same pipeline as background
            screen_points = np.zeros((len(point_data), 2))  # pyright: ignore[reportPrivateImportUsage]
            for i, point in enumerate(point_data):
                x, y = transform.data_to_screen(point[1], point[2])
                screen_points[i] = [x, y]

            # Debug logging
            if len(screen_points) > 0:
                logger.debug(f"Transformed {len(screen_points)} points using Transform service")
                logger.debug(
                    f"First point: data ({point_data[0][1]:.1f}, {point_data[0][2]:.1f}) -> screen ({screen_points[0][0]:.1f}, {screen_points[0][1]:.1f})"
                )
                logger.debug(f"Viewport: {viewport}")
        else:
            # Fallback to old method if transform not available
            zoom = curve_view.zoom_factor

            # Calculate center offset (like in Transform)
            image_width = curve_view.image_width
            image_height = curve_view.image_height
            scaled_width = image_width * zoom
            scaled_height = image_height * zoom
            center_x = (curve_view.width() - scaled_width) / 2
            center_y = (curve_view.height() - scaled_height) / 2

            # Calculate total offsets (center + pan + manual)
            offset_x = center_x + curve_view.pan_offset_x + curve_view.manual_offset_x
            offset_y = center_y + curve_view.pan_offset_y + curve_view.manual_offset_y

            screen_points = VectorizedTransform.transform_points_batch(
                point_data,
                zoom,
                offset_x,
                offset_y,
                curve_view.flip_y_axis,
                curve_view.height(),
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

        # Render lines with optimized path
        self._render_lines_optimized(painter, lod_points, step)

        # Render points with batching
        self._render_point_markers_optimized(painter, curve_view, lod_points, visible_indices, step)

        # Render frame numbers if enabled (with heavy culling)
        if curve_view.show_all_frame_numbers and self._render_quality == RenderQuality.HIGH:
            self._render_frame_numbers_optimized(painter, curve_view, lod_points, visible_indices, step)

    def _render_lines_optimized(self, painter: QPainter, screen_points: FloatArray, step: int) -> None:
        """Render lines between points using optimized QPainterPath."""
        if len(screen_points) < 2:
            return

        # Set line style
        pen = QPen(QColor(255, 255, 255))
        pen.setWidth(2)
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

    def _render_point_markers_optimized(
        self,
        painter: QPainter,
        curve_view: CurveViewProtocol,
        screen_points: FloatArray,
        visible_indices: IntArray,
        step: int,
    ) -> None:
        """Render point markers with selection and current frame highlighting."""
        if len(screen_points) == 0:
            return

        point_radius = curve_view.point_radius
        selected_points = curve_view.selected_points

        # Get current frame from main window if available
        current_frame = 1
        # main_window is defined in CurveViewProtocol
        if curve_view.main_window is not None:
            # state_manager is always initialized in MainWindow
            current_frame = curve_view.main_window.state_manager.current_frame

        # Get the curve data to check frame numbers
        points_data = curve_view.points

        # Batch points by state for efficient rendering
        normal_points = []
        selected_points_list = []
        current_frame_points = []

        for i, screen_pos in enumerate(screen_points):
            # Map back to original index (accounting for LOD step)
            original_idx = visible_indices[i * step] if i * step < len(visible_indices) else -1

            # Check if this point is on the current frame
            is_current_frame = False
            if 0 <= original_idx < len(points_data):
                point_data = points_data[original_idx]
                # Extract frame from point tuple (frame is first element)
                if len(point_data) >= 3:
                    frame = point_data[0]
                    is_current_frame = frame == current_frame

            if is_current_frame:
                current_frame_points.append(screen_pos)
            elif original_idx in selected_points:
                selected_points_list.append(screen_pos)
            else:
                normal_points.append(screen_pos)

        # Set painter for point drawing
        painter.setPen(Qt.PenStyle.NoPen)

        # Import theme colors
        from ui.ui_constants import COLORS_DARK, CURVE_COLORS

        # Draw normal points in batch
        if normal_points:
            painter.setBrush(QBrush(QColor(CURVE_COLORS["point_normal"])))  # Theme color for normal
            for pos in normal_points:
                painter.drawEllipse(QPointF(pos[0], pos[1]), point_radius, point_radius)

        # Draw selected points in batch
        if selected_points_list:
            painter.setBrush(QBrush(QColor(CURVE_COLORS["point_selected"])))  # Theme color for selected
            for pos in selected_points_list:
                painter.drawEllipse(QPointF(pos[0], pos[1]), point_radius, point_radius)

        # Draw current frame points with larger radius and accent color
        if current_frame_points:
            painter.setBrush(QBrush(QColor(COLORS_DARK["accent_info"])))  # Theme accent for current frame
            current_frame_radius = point_radius + 3  # Larger radius for current frame
            for pos in current_frame_points:
                painter.drawEllipse(QPointF(pos[0], pos[1]), current_frame_radius, current_frame_radius)

    def _render_frame_numbers_optimized(
        self,
        painter: QPainter,
        curve_view: CurveViewProtocol,
        screen_points: FloatArray,
        visible_indices: IntArray,
        step: int,
    ) -> None:
        """Render frame numbers with heavy culling for performance."""
        if len(screen_points) == 0:
            return

        # Only show frame numbers for a subset of points to avoid clutter
        max_labels = 50  # Maximum number of labels to show
        if len(screen_points) > max_labels:
            label_step = len(screen_points) // max_labels
        else:
            label_step = 1

        from ui.ui_constants import COLORS_DARK

        painter.setPen(QPen(QColor(COLORS_DARK["text_primary"])))
        font = QFont("Arial", 8)  # Smaller font for performance
        painter.setFont(font)

        points = curve_view.points
        for i in range(0, len(screen_points), label_step):
            screen_pos = screen_points[i]
            # Map back to original index
            original_idx = visible_indices[i * step] if i * step < len(visible_indices) else -1

            if 0 <= original_idx < len(points):
                frame_num = points[original_idx][0]
                painter.drawText(int(screen_pos[0] + 10), int(screen_pos[1] - 10), f"F{frame_num}")

    def _render_background_optimized(self, painter: QPainter, curve_view: CurveViewProtocol) -> None:
        """Optimized background rendering with proper transformations."""
        print("[RENDERER_BG] _render_background_optimized called")
        background_image = curve_view.background_image
        if not background_image:
            print("[RENDERER_BG] No background image, returning")
            return

        opacity = curve_view.background_opacity
        if opacity < 1.0:
            painter.setOpacity(opacity)

        # Use fast scaling hint for better performance
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self._render_quality == RenderQuality.HIGH)

        # Get the transform from curve_view to apply the same transformations as curve points
        # get_transform is defined in CurveViewProtocol
        print("[RENDERER_BG] Using transform-based rendering")
        transform = curve_view.get_transform()

        from PySide6.QtGui import QImage, QPixmap

        # Cast background_image to proper type for type checker
        bg_image = background_image  # type: QImage | QPixmap  # pyright: ignore[reportAssignmentType]

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

        print(f"[RENDERER_BG] Scale: {scale}, original size: ({bg_image.width()}, {bg_image.height()})")

        # Draw the background image scaled to fit the transformed rectangle
        # This ensures it goes through the exact same transformation as curve points
        # Convert QImage to QPixmap if needed
        if isinstance(bg_image, QImage):
            pixmap = QPixmap.fromImage(bg_image)
        else:
            pixmap = bg_image  # pyright: ignore[reportAssignmentType]
        print(
            f"[RENDERER_BG] Drawing at pos=({int(top_left_x)}, {int(top_left_y)}), size=({int(target_width)}, {int(target_height)})"
        )
        painter.drawPixmap(int(top_left_x), int(top_left_y), int(target_width), int(target_height), pixmap)

        if opacity < 1.0:
            painter.setOpacity(1.0)

    def _render_grid_optimized(self, painter: QPainter, curve_view: CurveViewProtocol) -> None:
        """Optimized grid rendering with adaptive density."""
        from ui.ui_constants import COLORS_DARK

        grid_color = QColor(COLORS_DARK["grid_lines"])
        grid_color.setAlpha(50)
        pen = QPen(grid_color)
        pen.setWidth(1)
        painter.setPen(pen)

        # Adaptive grid spacing based on zoom
        zoom = curve_view.zoom_factor
        base_step = 50
        step = max(25, int(base_step / max(1, zoom / 2)))  # Adjust grid density

        width = curve_view.width()
        height = curve_view.height()

        # Vertical lines
        for x in range(0, width + step, step):
            painter.drawLine(x, 0, x, height)

        # Horizontal lines
        for y in range(0, height + step, step):
            painter.drawLine(0, y, width, y)

    def _render_info_optimized(self, painter: QPainter, curve_view: CurveViewProtocol) -> None:
        """Render info overlay with performance metrics."""
        from ui.ui_constants import COLORS_DARK

        painter.setPen(QPen(QColor(COLORS_DARK["text_primary"])))
        painter.setFont(QFont("Arial", 10))

        points = curve_view.points
        selected_points = curve_view.selected_points
        zoom = curve_view.zoom_factor

        info_text = f"Points: {len(points)}"
        if selected_points:
            info_text += f" | Selected: {len(selected_points)}"
        info_text += f" | Zoom: {zoom:.1f}x"

        # Add performance info
        info_text += f" | {self._last_fps:.1f} FPS"
        info_text += f" | Quality: {self._render_quality.value.upper()}"

        # Add optimization status
        # debug_mode is an optional attribute for debugging
        try:
            if curve_view.debug_mode:
                visible_count = len(self._cached_visible_indices) if self._cached_visible_indices is not None else 0
                info_text += f" | Visible: {visible_count}"
        except AttributeError:
            pass  # debug_mode not available

        painter.drawText(10, 20, info_text)

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
