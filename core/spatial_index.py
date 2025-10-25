#!/usr/bin/env python
"""
Spatial indexing for efficient point lookups in CurveEditor.

This module provides a simple grid-based spatial index for O(1) point
lookups instead of O(n) linear search.
"""
# pyright: reportImportCycles=false

from __future__ import annotations

import math
import threading
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from protocols.ui import CurveViewProtocol
    from services.transform_service import Transform

from core.logger_utils import get_logger
from core.type_aliases import CurveDataList

logger = get_logger("spatial_index")


class HasDimensionsProtocol(Protocol):
    """Minimal protocol for objects that provide width and height."""

    def width(self) -> int:
        """Get widget width."""
        ...

    def height(self) -> int:
        """Get widget height."""
        ...


class PointIndex:
    """
    Simple grid-based spatial index for efficient point lookups.

    Divides the screen space into a grid and stores point indices in each cell
    for O(1) lookup performance instead of O(n) linear search.
    """

    grid_width: int
    grid_height: int
    _lock: threading.RLock

    def __init__(self, screen_width: float = 800.0, screen_height: float = 600.0):
        """
        Initialize the spatial index with adaptive grid size.

        Args:
            screen_width: Screen width in pixels for adaptive grid calculation
            screen_height: Screen height in pixels for adaptive grid calculation
        """
        # Calculate adaptive grid size targeting 40-50 pixels per cell
        target_cell_size = 45.0  # pixels
        self.grid_width = max(10, min(50, int(screen_width / target_cell_size)))
        self.grid_height = max(10, min(50, int(screen_height / target_cell_size)))
        self.cell_width: float = 0.0
        self.cell_height: float = 0.0
        self.screen_width: float = screen_width
        self.screen_height: float = screen_height

        # Cache the target cell size for recalculation
        self._target_cell_size: float = 45.0

        # Grid structure: dict[tuple[int, int], list[int]]
        # Key is (grid_x, grid_y), value is list of point indices
        self._grid: dict[tuple[int, int], list[int]] = {}

        # Track when index was last built
        self._last_transform_hash: str | None = None
        self._last_point_count: int = 0

        # Thread safety
        self._lock = threading.RLock()

    def _get_cell_coords(self, screen_x: float, screen_y: float) -> tuple[int, int]:
        """
        Get grid cell coordinates for screen position.

        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate

        Returns:
            Tuple of (grid_x, grid_y)
        """
        if self.cell_width == 0 or self.cell_height == 0:
            return (0, 0)

        grid_x = min(int(screen_x / self.cell_width), self.grid_width - 1)
        grid_y = min(int(screen_y / self.cell_height), self.grid_height - 1)

        # Ensure coordinates are within bounds
        grid_x = max(0, grid_x)
        grid_y = max(0, grid_y)

        return (grid_x, grid_y)

    def update_screen_dimensions(self, screen_width: float, screen_height: float) -> bool:
        """
        Update screen dimensions and recalculate adaptive grid size if needed.

        Args:
            screen_width: New screen width in pixels
            screen_height: New screen height in pixels

        Returns:
            True if grid was resized, False if no change needed
        """
        with self._lock:
            # Check if dimensions changed significantly
            width_change = abs(screen_width - self.screen_width)
            height_change = abs(screen_height - self.screen_height)

            # Only recalculate if change is significant (>10% or >100 pixels)
            threshold = max(100.0, min(self.screen_width * 0.1, self.screen_height * 0.1))

            if width_change > threshold or height_change > threshold:
                # Update dimensions
                self.screen_width = screen_width
                self.screen_height = screen_height

                # Recalculate adaptive grid size
                old_grid_width = self.grid_width
                old_grid_height = self.grid_height

                self.grid_width = max(10, min(50, int(screen_width / self._target_cell_size)))
                self.grid_height = max(10, min(50, int(screen_height / self._target_cell_size)))

                # Clear index if grid size changed
                if self.grid_width != old_grid_width or self.grid_height != old_grid_height:
                    self._grid.clear()
                    self._last_transform_hash = None  # Force rebuild
                    logger.debug(
                        f"Adaptive grid resized: {old_grid_width}x{old_grid_height} -> "
                        + f"{self.grid_width}x{self.grid_height} for {screen_width}x{screen_height} screen"
                    )
                    return True

            return False

    def _get_nearby_cells(self, grid_x: int, grid_y: int, radius: int = 1) -> list[tuple[int, int]]:
        """
        Get list of nearby grid cells within radius.

        Args:
            grid_x: Center grid X coordinate
            grid_y: Center grid Y coordinate
            radius: Search radius in grid cells

        Returns:
            List of (grid_x, grid_y) tuples
        """
        cells: list[tuple[int, int]] = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx = grid_x + dx
                ny = grid_y + dy
                if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                    cells.append((nx, ny))
        return cells

    def rebuild_index(self, curve_data: CurveDataList, view: HasDimensionsProtocol, transform: Transform) -> None:
        """
        Rebuild the spatial index from curve data.

        Args:
            curve_data: The curve data to index
            view: Object with width() and height() methods (for screen dimensions)
            transform: Transform for coordinate conversion
        """
        with self._lock:
            # Check if rebuild is needed
            current_transform_hash = transform.stability_hash
            current_point_count = len(curve_data)

            if (
                self._last_transform_hash == current_transform_hash
                and self._last_point_count == current_point_count
                and self._grid
            ):
                # Index is still valid
                return

            # Clear existing index
            self._grid.clear()

            # Update screen dimensions and recalculate grid if needed
            new_width = float(getattr(view, "width", lambda: 800.0)())
            new_height = float(getattr(view, "height", lambda: 600.0)())
            _ = self.update_screen_dimensions(new_width, new_height)

            # Calculate cell dimensions
            self.cell_width = self.screen_width / self.grid_width
            self.cell_height = self.screen_height / self.grid_height

            # Build index from curve data
            if curve_data:
                for idx, point in enumerate(curve_data):
                    if len(point) >= 3:
                        # Convert data point to screen coordinates
                        screen_x, screen_y = transform.data_to_screen(point[1], point[2])

                        # Get grid cell
                        grid_x, grid_y = self._get_cell_coords(screen_x, screen_y)

                        # Add point index to cell
                        cell_key = (grid_x, grid_y)
                        if cell_key not in self._grid:
                            self._grid[cell_key] = []
                        self._grid[cell_key].append(idx)

            # Update tracking
            self._last_transform_hash = current_transform_hash
            self._last_point_count = current_point_count

    def find_point_at_position(
        self,
        curve_data: CurveDataList,
        transform: Transform,
        x: float,
        y: float,
        threshold: float = 5.0,
        view: CurveViewProtocol | None = None,
    ) -> int:
        """
        Find point at given screen position using spatial indexing.

        Args:
            curve_data: The curve data to search
            transform: Transform for coordinate conversion
            x: Screen X coordinate
            y: Screen Y coordinate
            threshold: Selection threshold in screen pixels
            view: Optional curve view (for screen dimensions, uses defaults if None)

        Returns:
            Point index or -1 if no point found
        """
        if not curve_data:
            return -1

        # Rebuild index if needed (use view for screen dimensions, or create dummy)
        dimensions_view: HasDimensionsProtocol
        if view is None:
            # Create a minimal view object for dimensions
            class DummyView:
                def width(self) -> int:
                    return 800

                def height(self) -> int:
                    return 600

            dimensions_view = DummyView()
        else:
            dimensions_view = view

        self.rebuild_index(curve_data, dimensions_view, transform)

        # Type-safe curve data access
        typed_curve_data = curve_data

        # Get grid cell for position
        grid_x, grid_y = self._get_cell_coords(x, y)

        # Check nearby cells (threshold might span multiple cells)
        cell_radius = (
            max(1, int(threshold / min(self.cell_width, self.cell_height)) + 1)
            if self.cell_width > 0 and self.cell_height > 0
            else 1
        )
        nearby_cells = self._get_nearby_cells(grid_x, grid_y, cell_radius)

        closest_idx = -1
        closest_distance: float = float("inf")

        # Check points in nearby cells
        with self._lock:
            for cell_key in nearby_cells:
                if cell_key in self._grid:
                    for point_idx in self._grid[cell_key]:
                        if point_idx < len(typed_curve_data):
                            point = typed_curve_data[point_idx]
                            if len(point) >= 3:
                                # Convert to screen coordinates
                                screen_coords = transform.data_to_screen(point[1], point[2])
                                screen_px: float = screen_coords[0]
                                screen_py: float = screen_coords[1]

                                # Calculate distance using math.sqrt for type safety
                                dx = float(screen_px - x)
                                dy = float(screen_py - y)
                                distance = math.sqrt(dx * dx + dy * dy)

                                # Check if within threshold and closer than previous
                                if distance <= threshold and distance < closest_distance:
                                    closest_distance = distance
                                    closest_idx = point_idx
        return closest_idx

    def get_points_in_rect(
        self,
        curve_data: CurveDataList,
        transform: Transform,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        view: CurveViewProtocol | None = None,
    ) -> list[int]:
        """
        Find all points within a rectangular region using spatial indexing.

        Args:
            curve_data: The curve data to search
            transform: Transform for coordinate conversion
            x1, y1: Top-left corner of rectangle (screen coordinates)
            x2, y2: Bottom-right corner of rectangle (screen coordinates)
            view: Optional curve view (for screen dimensions, uses defaults if None)

        Returns:
            List of point indices within the rectangle
        """
        if not curve_data:
            return []

        # Rebuild index if needed
        dimensions_view: HasDimensionsProtocol
        if view is None:
            # Create a minimal view object for dimensions
            class DummyView:
                def width(self) -> int:
                    return 800

                def height(self) -> int:
                    return 600

            dimensions_view = DummyView()
        else:
            dimensions_view = view

        self.rebuild_index(curve_data, dimensions_view, transform)

        # Type-safe curve data access
        typed_curve_data = curve_data

        # Ensure proper bounds
        left = min(x1, x2)
        right = max(x1, x2)
        top = min(y1, y2)
        bottom = max(y1, y2)

        # Get grid cells covering the rectangle
        top_left_cell = self._get_cell_coords(left, top)
        bottom_right_cell = self._get_cell_coords(right, bottom)

        result_indices: list[int] = []

        # Check all cells in the rectangle
        with self._lock:
            for gx in range(top_left_cell[0], bottom_right_cell[0] + 1):
                for gy in range(top_left_cell[1], bottom_right_cell[1] + 1):
                    cell_key = (gx, gy)
                    if cell_key in self._grid:
                        for point_idx in self._grid[cell_key]:
                            if point_idx < len(typed_curve_data):
                                point = typed_curve_data[point_idx]
                                if len(point) >= 3:
                                    # Convert to screen coordinates
                                    screen_px, screen_py = transform.data_to_screen(point[1], point[2])

                                    # Check if point is within rectangle
                                    if left <= screen_px <= right and top <= screen_py <= bottom:
                                        result_indices.append(point_idx)

        return result_indices

    def get_stats(self) -> dict[str, int | float | tuple[int, int] | tuple[float, float] | str | None]:
        """
        Get spatial index statistics.

        Returns:
            Dictionary with index statistics
        """
        with self._lock:
            occupied_cells = len(self._grid)
            total_cells = self.grid_width * self.grid_height
            total_points = sum(len(points) for points in self._grid.values())

            avg_points_per_cell = total_points / occupied_cells if occupied_cells > 0 else 0

            return {
                "grid_size": (self.grid_width, self.grid_height),
                "screen_size": (self.screen_width, self.screen_height),
                "cell_size": (self.cell_width, self.cell_height),
                "occupied_cells": occupied_cells,
                "total_cells": total_cells,
                "occupancy_ratio": occupied_cells / total_cells if total_cells > 0 else 0,
                "total_points": total_points,
                "avg_points_per_cell": avg_points_per_cell,
                "transform_hash": self._last_transform_hash,
            }

    def clear_cache(self) -> None:
        """Clear the spatial index cache to force rebuild on next access."""
        with self._lock:
            self._grid.clear()
            self._last_transform_hash = None
            self._last_point_count = 0
            logger.debug("Spatial index cache cleared")
