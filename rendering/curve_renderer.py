#!/usr/bin/env python
"""Consolidated rendering system for curve editor with performance optimizations."""

import logging
import time
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen

logger = logging.getLogger("curve_renderer")


class CoordinateCache:
    """Cache for transformed screen coordinates to avoid redundant calculations."""

    def __init__(self):
        """Initialize the coordinate cache."""
        self._cache: dict[int, list[QPointF]] = {}  # Cache key -> transformed points
        self._last_cache_key: int | None = None
        self._hit_count = 0
        self._miss_count = 0
        self._last_log_time = time.time()

    def get(self, cache_key: int) -> list[QPointF] | None:
        """Get cached coordinates if available."""
        if cache_key in self._cache:
            self._hit_count += 1
            self._log_stats()
            return self._cache[cache_key]
        self._miss_count += 1
        self._log_stats()
        return None

    def set(self, cache_key: int, points: list[QPointF]) -> None:
        """Store transformed points in cache."""
        # Limit cache size to prevent memory issues
        if len(self._cache) > 10:
            # Remove oldest entries
            self._cache.clear()
        self._cache[cache_key] = points
        self._last_cache_key = cache_key

    def invalidate(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._last_cache_key = None
        logger.debug("Coordinate cache invalidated")

    def _log_stats(self) -> None:
        """Log cache statistics periodically."""
        current_time = time.time()
        if current_time - self._last_log_time > 5.0:  # Log every 5 seconds
            total = self._hit_count + self._miss_count
            if total > 0:
                hit_rate = (self._hit_count / total) * 100
                logger.debug(
                    f"Cache stats: {hit_rate:.1f}% hit rate ({self._hit_count} hits, {self._miss_count} misses)"
                )
            self._last_log_time = current_time


class CurveRenderer:
    """Main renderer that handles all curve visualization with performance optimizations."""

    def __init__(self):
        """Initialize renderer with caching and optimization features."""
        self.background_opacity = 1.0
        self._coord_cache = CoordinateCache()
        self._last_render_time = 0.0
        self._render_count = 0
        self._enable_culling = True  # Enable viewport culling by default
        self._enable_caching = True  # Enable coordinate caching by default

    def render(self, painter: QPainter, event: Any, curve_view: Any) -> None:
        """Render complete curve view with performance optimizations.

        Args:
            painter: QPainter for rendering
            event: Paint event (unused but kept for compatibility)
            curve_view: The curve view to render
        """
        # Track render performance
        start_time = time.perf_counter()
        self._render_count += 1

        # Save painter state
        painter.save()

        # Render background if available
        if curve_view.show_background and curve_view.background_image:
            self.render_background(painter, curve_view)

        # Render grid
        if curve_view.show_grid:
            self.render_grid(painter, curve_view)

        # Render curve points with optimizations
        if curve_view.points:
            self.render_points_optimized(painter, curve_view)

        # Render info overlay
        self.render_info(painter, curve_view)

        # Restore painter state
        painter.restore()

        # Log performance metrics periodically
        render_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
        self._last_render_time = render_time
        if self._render_count % 100 == 0:
            logger.debug(f"Render #{self._render_count}: {render_time:.2f}ms")

    def render_background(self, painter: QPainter, curve_view):
        """Render background image."""
        if not curve_view.background_image:
            return

        painter.setOpacity(curve_view.background_opacity)
        painter.drawPixmap(0, 0, curve_view.width(), curve_view.height(), curve_view.background_image)
        painter.setOpacity(1.0)

    def render_grid(self, painter: QPainter, curve_view):
        """Render grid lines."""
        pen = QPen(QColor(100, 100, 100, 50))
        pen.setWidth(1)
        painter.setPen(pen)

        # Vertical lines
        step = 50
        for x in range(0, curve_view.width(), step):
            painter.drawLine(x, 0, x, curve_view.height())

        # Horizontal lines
        for y in range(0, curve_view.height(), step):
            painter.drawLine(0, y, curve_view.width(), y)

    def render_points(self, painter: QPainter, curve_view):
        """Legacy render method for backward compatibility."""
        self.render_points_optimized(painter, curve_view)

    def render_points_optimized(self, painter: QPainter, curve_view):
        """Render curve points and lines with performance optimizations.

        Optimizations:
        1. Coordinate caching to avoid redundant transformations
        2. Visible range culling to skip off-screen points
        3. Batch operations where possible
        """
        if not curve_view.points:
            return

        # Generate cache key based on current transform state
        cache_key = self._generate_cache_key(curve_view)

        # Try to get cached screen coordinates
        screen_points = None
        if self._enable_caching:
            screen_points = self._coord_cache.get(cache_key)

        # If not cached, transform all points
        if screen_points is None:
            screen_points = self._transform_points(curve_view.points, curve_view)
            if self._enable_caching:
                self._coord_cache.set(cache_key, screen_points)

        # Get visible viewport for culling with some padding
        viewport = QRectF(-50, -50, curve_view.width() + 100, curve_view.height() + 100)

        # Early exit optimization: check if any points are visible
        if self._enable_culling and screen_points:
            any_visible = False
            for point in screen_points[::10]:  # Sample every 10th point for quick check
                if viewport.contains(point):
                    any_visible = True
                    break
            if not any_visible:
                # Check bounds more carefully
                min_x = min(p.x() for p in screen_points)
                max_x = max(p.x() for p in screen_points)
                min_y = min(p.y() for p in screen_points)
                max_y = max(p.y() for p in screen_points)
                bounds = QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
                if not viewport.intersects(bounds):
                    return  # Nothing visible, skip rendering

        # Draw lines between points with culling
        pen = QPen(QColor(255, 255, 255))
        pen.setWidth(2)
        painter.setPen(pen)

        # Use path for efficient line drawing
        from PySide6.QtGui import QPainterPath

        line_path = QPainterPath()
        path_started = False

        for i in range(len(screen_points) - 1):
            p1 = screen_points[i]
            p2 = screen_points[i + 1]

            # Check if line segment is visible
            if self._enable_culling:
                if not self._line_intersects_viewport(p1, p2, viewport):
                    path_started = False  # Break the path
                    continue

            # Add to path for batch drawing
            if not path_started:
                line_path.moveTo(p1)
                path_started = True
            line_path.lineTo(p2)

        # Draw all lines at once
        painter.drawPath(line_path)

        # Draw points with culling
        point_radius = 5
        painter.setPen(Qt.PenStyle.NoPen)

        # Batch points by color for efficiency
        normal_points = []
        selected_points = []

        for i, screen_pos in enumerate(screen_points):
            # Skip points outside viewport
            if self._enable_culling:
                if not viewport.contains(screen_pos):
                    continue

            # Group by selection state
            if i in curve_view.selected_points:
                selected_points.append(screen_pos)
            else:
                normal_points.append(screen_pos)

        # Draw normal points in batch
        if normal_points:
            painter.setBrush(QBrush(QColor(255, 0, 0)))  # Red for normal
            for pos in normal_points:
                painter.drawEllipse(pos, point_radius, point_radius)

        # Draw selected points in batch
        if selected_points:
            painter.setBrush(QBrush(QColor(255, 255, 0)))  # Yellow for selected
            for pos in selected_points:
                painter.drawEllipse(pos, point_radius, point_radius)

        # Draw frame numbers if enabled
        if curve_view.show_all_frame_numbers:
            painter.setPen(QPen(QColor(255, 255, 255)))
            for i, screen_pos in enumerate(screen_points):
                if self._enable_culling and not viewport.contains(screen_pos):
                    continue
                painter.drawText(int(screen_pos.x()) + 10, int(screen_pos.y()) - 10, f"F{curve_view.points[i][0]}")

    def render_info(self, painter: QPainter, curve_view):
        """Render information overlay with performance metrics."""
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 10))

        info_text = f"Points: {len(curve_view.points)}"
        if curve_view.selected_points:
            info_text += f" | Selected: {len(curve_view.selected_points)}"
        info_text += f" | Zoom: {curve_view.zoom_factor:.1f}x"

        # Add performance info in debug mode
        if hasattr(curve_view, "debug_mode") and curve_view.debug_mode:
            info_text += f" | Render: {self._last_render_time:.1f}ms"
            if self._enable_caching:
                info_text += " | Cache: ON"
            if self._enable_culling:
                info_text += " | Culling: ON"

        painter.drawText(10, 20, info_text)

    def _generate_cache_key(self, curve_view) -> int:
        """Generate a cache key based on current view state.

        The cache key changes when any transform parameter changes,
        ensuring cache invalidation when needed.
        """
        # Combine all transform-related parameters into a hash
        key_parts = [
            curve_view.zoom_factor,
            curve_view.offset_x,
            curve_view.offset_y,
            curve_view.flip_y_axis,
            curve_view.width(),
            curve_view.height(),
            len(curve_view.points),  # Invalidate if points change
            # Include data bounds to detect data changes
            min(p[1] for p in curve_view.points) if curve_view.points else 0,
            max(p[1] for p in curve_view.points) if curve_view.points else 0,
        ]

        # Create a hash from the key parts
        import hashlib

        key_str = "|".join(str(p) for p in key_parts)
        return int(hashlib.md5(key_str.encode()).hexdigest()[:8], 16)

    def _transform_points(self, points: list[Any], curve_view) -> list[QPointF]:
        """Transform all data points to screen coordinates.

        This is the performance-critical function that benefits most from caching.
        """
        screen_points = []
        zoom = curve_view.zoom_factor
        offset_x = curve_view.offset_x
        offset_y = curve_view.offset_y
        flip_y = curve_view.flip_y_axis
        height = curve_view.height()

        # Transform all points in a tight loop for better performance
        for point in points:
            x = point[1] * zoom + offset_x
            y = point[2] * zoom + offset_y

            if flip_y:
                y = height - y

            screen_points.append(QPointF(x, y))

        return screen_points

    def _line_intersects_viewport(self, p1: QPointF, p2: QPointF, viewport: QRectF) -> bool:
        """Check if a line segment intersects or is contained in the viewport.

        Uses simple bounding box check for performance.
        """
        # Fast path: if either endpoint is in viewport, line is visible
        if viewport.contains(p1) or viewport.contains(p2):
            return True

        # Check if line's bounding box intersects viewport using QRectF
        line_rect = QRectF(p1, p2).normalized()
        return viewport.intersects(line_rect)

    def data_to_screen(self, point: tuple[Any, ...], curve_view) -> QPointF:
        """Convert data coordinates to screen coordinates using TransformService."""
        # Use TransformService for consistent transformations
        if hasattr(curve_view, 'get_current_transform'):
            transform = curve_view.get_current_transform()
            if transform:
                x, y = transform.data_to_screen(point[1], point[2])
                return QPointF(x, y)

        # Fallback for compatibility
        x = point[1] * curve_view.zoom_factor + curve_view.offset_x
        y = point[2] * curve_view.zoom_factor + curve_view.offset_y
        if curve_view.flip_y_axis:
            y = curve_view.height() - y
        return QPointF(x, y)

    def screen_to_data(self, pos: QPointF, curve_view) -> tuple[float, float]:
        """Convert screen coordinates to data coordinates using TransformService."""
        # Use TransformService for consistent transformations
        if hasattr(curve_view, 'get_current_transform'):
            transform = curve_view.get_current_transform()
            if transform:
                return transform.screen_to_data(pos.x(), pos.y())

        # Fallback for compatibility
        x = (pos.x() - curve_view.offset_x) / curve_view.zoom_factor
        y = pos.y()
        if curve_view.flip_y_axis:
            y = curve_view.height() - y
        y = (y - curve_view.offset_y) / curve_view.zoom_factor
        return (x, y)
