#!/usr/bin/env python
"""
RenderCacheController - Rendering cache management for CurveViewWidget.

This controller encapsulates all rendering cache operations, managing screen point
positions, visible indices, and update regions for optimized painting performance.

Phase 5 extraction from CurveViewWidget god object refactoring.
"""

# Import cycle with CurveViewWidget is expected and safe - resolved via TYPE_CHECKING
# pyright: reportImportCycles=false

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRect, QRectF

from core.logger_utils import get_logger
from core.point_types import safe_extract_point

if TYPE_CHECKING:
    from ui.curve_view_widget import CurveViewWidget

logger = get_logger("render_cache_controller")


class RenderCacheController:
    """
    Controller for rendering cache management.

    Manages performance-critical caches for rendering:
    - Screen point positions (data coords → screen coords)
    - Visible indices (viewport culling)
    - Update regions (partial repaints)

    Pattern: Controller holds widget reference (Pattern B - like StateSyncController)
    No manual widget.update() calls - caches are passive, queried during paintEvent.

    Attributes:
        widget: Reference to CurveViewWidget for curve data access
        _screen_points_cache: Cached screen positions for points
        _visible_indices_cache: Set of indices visible in viewport
        _update_region: Accumulated region needing repaint
    """

    def __init__(self, widget: CurveViewWidget) -> None:
        """
        Initialize the render cache controller.

        Args:
            widget: CurveViewWidget instance
        """
        self.widget = widget

        # Rendering caches (moved from widget)
        self._screen_points_cache: dict[int, QPointF] = {}
        self._visible_indices_cache: set[int] = set()
        self._update_region: QRectF | None = None

        logger.debug("RenderCacheController initialized")

    # ==================== Cache Invalidation ====================

    def invalidate_all(self) -> None:
        """
        Invalidate all rendering caches.

        Clears screen point cache, visible indices, and update region.
        Note: Transform cache is managed by ViewCameraController (Phase 1).
        """
        self._screen_points_cache.clear()
        self._visible_indices_cache.clear()
        self._update_region = None

        logger.debug("Invalidated all rendering caches")

    def invalidate_point_region(self, index: int) -> None:
        """
        Invalidate region around a specific point.

        Marks the area around a point for repainting without clearing entire cache.
        Useful for incremental updates when a single point changes.

        Args:
            index: Point index to invalidate
        """
        if index in self._screen_points_cache:
            pos = self._screen_points_cache[index]

            # Create update region around point
            margin = self.widget.point_radius + 10
            region = QRectF(pos.x() - margin, pos.y() - margin, margin * 2, margin * 2)

            if self._update_region:
                self._update_region = self._update_region.united(region)
            else:
                self._update_region = region

            logger.debug(f"Invalidated region around point {index}")

    # ==================== Cache Updates ====================

    def update_screen_points_cache(self) -> None:
        """
        Update cached screen positions for all curve points.

        Rebuilds the screen points cache by transforming all curve data points
        from data coordinates to screen coordinates. Only rebuilds if cache is empty.
        """
        if not self._screen_points_cache:
            self._screen_points_cache.clear()

            for idx, point in enumerate(self.widget.curve_data):
                _, x, y, _ = safe_extract_point(point)
                screen_pos = self.widget.data_to_screen(x, y)
                self._screen_points_cache[idx] = screen_pos

    def update_visible_indices(self, rect: QRect) -> None:
        """
        Update cache of visible point indices for viewport culling.

        Determines which points are visible in the given viewport rectangle.
        Expands the rectangle slightly to include points on edges.

        Args:
            rect: Visible rectangle in screen coordinates
        """
        self._visible_indices_cache.clear()

        # Expand rect slightly for points on edges
        expanded = rect.adjusted(
            -self.widget.point_radius,
            -self.widget.point_radius,
            self.widget.point_radius,
            self.widget.point_radius,
        )

        for idx, pos in self._screen_points_cache.items():
            if expanded.contains(pos.toPoint()):
                self._visible_indices_cache.add(idx)

    def update_single_point_cache(self, index: int, x: float, y: float) -> None:
        """
        Update screen position for a single point in the cache.

        Used during point dragging to update cache incrementally without rebuilding.

        Args:
            index: Point index to update
            x: New X coordinate in data space
            y: New Y coordinate in data space
        """
        if index in self._screen_points_cache:
            self._screen_points_cache[index] = self.widget.data_to_screen(x, y)

    # ==================== Cache Queries ====================

    def get_screen_position(self, index: int) -> QPointF | None:
        """
        Get cached screen position for a point.

        Args:
            index: Point index

        Returns:
            Screen position or None if not in cache
        """
        return self._screen_points_cache.get(index)

    def is_point_visible(self, index: int) -> bool:
        """
        Check if a point is in the visible indices cache.

        Args:
            index: Point index

        Returns:
            True if point is visible
        """
        return index in self._visible_indices_cache

    def get_screen_points_items(self) -> list[tuple[int, QPointF]]:
        """
        Get all cached screen points as (index, position) tuples.

        Returns:
            List of (index, screen_position) pairs
        """
        return list(self._screen_points_cache.items())

    def has_cached_position(self, index: int) -> bool:
        """
        Check if screen position is cached for a point.

        Args:
            index: Point index

        Returns:
            True if position is cached
        """
        return index in self._screen_points_cache

    @property
    def update_region(self) -> QRectF | None:
        """Get the accumulated update region."""
        return self._update_region

    @property
    def screen_points_cache(self) -> dict[int, QPointF]:
        """Get the screen points cache (read-only access)."""
        return self._screen_points_cache
