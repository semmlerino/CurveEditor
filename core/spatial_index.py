#!/usr/bin/env python
"""
Spatial indexing for efficient point lookups in CurveEditor.

This module provides a simple grid-based spatial index for O(1) point
lookups instead of O(n) linear search.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.service_protocols import CurveViewProtocol
    from services.transform_service import Transform

logger = logging.getLogger("spatial_index")


class PointIndex:
    """
    Simple grid-based spatial index for efficient point lookups.

    Divides the screen space into a grid and stores point indices in each cell
    for O(1) lookup performance instead of O(n) linear search.
    """

    grid_width: int
    grid_height: int
    _lock: threading.RLock

    def __init__(self, grid_width: int = 20, grid_height: int = 20):
        """
        Initialize the spatial index.

        Args:
            grid_width: Number of grid cells horizontally
            grid_height: Number of grid cells vertically
        """
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.cell_width: float = 0.0
        self.cell_height: float = 0.0
        self.screen_width: float = 0.0
        self.screen_height: float = 0.0

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

    def rebuild_index(self, view: CurveViewProtocol, transform: Transform) -> None:
        """
        Rebuild the spatial index from current curve data.

        Args:
            view: The curve view containing the data
            transform: Transform for coordinate conversion
        """
        with self._lock:
            # Check if rebuild is needed
            current_transform_hash = transform.stability_hash
            current_point_count = len(getattr(view, "curve_data", []))

            if (
                self._last_transform_hash == current_transform_hash
                and self._last_point_count == current_point_count
                and self._grid
            ):
                # Index is still valid
                return

            logger.debug(f"Rebuilding spatial index for {current_point_count} points")

            # Clear existing index
            self._grid.clear()

            # Get screen dimensions
            self.screen_width = float(getattr(view, "width", lambda: 800.0)())
            self.screen_height = float(getattr(view, "height", lambda: 600.0)())

            # Calculate cell dimensions
            self.cell_width = self.screen_width / self.grid_width
            self.cell_height = self.screen_height / self.grid_height

            # Build index from curve data
            curve_data = getattr(view, "curve_data", None)
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

            logger.debug(f"Spatial index built with {len(self._grid)} occupied cells")

    def find_point_at_position(
        self, view: CurveViewProtocol, transform: Transform, x: float, y: float, threshold: float = 5.0
    ) -> int:
        """
        Find point at given screen position using spatial indexing.

        Args:
            view: The curve view containing the data
            transform: Transform for coordinate conversion
            x: Screen X coordinate
            y: Screen Y coordinate
            threshold: Selection threshold in screen pixels

        Returns:
            Point index or -1 if no point found
        """
        # Rebuild index if needed
        self.rebuild_index(view, transform)

        curve_data = getattr(view, "curve_data", None)
        if not curve_data:
            return -1

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
        closest_distance = float("inf")

        # Check points in nearby cells
        with self._lock:
            for cell_key in nearby_cells:
                if cell_key in self._grid:
                    for point_idx in self._grid[cell_key]:
                        if point_idx < len(curve_data):
                            point = curve_data[point_idx]
                            if len(point) >= 3:
                                # Convert to screen coordinates
                                screen_coords = transform.data_to_screen(point[1], point[2])
                                screen_px: float = screen_coords[0]
                                screen_py: float = screen_coords[1]

                                # Calculate distance
                                distance: float = ((screen_px - x) ** 2 + (screen_py - y) ** 2) ** 0.5

                                # Check if within threshold and closer than previous
                                if distance <= threshold and distance < closest_distance:
                                    closest_distance = distance
                                    closest_idx = point_idx
        return closest_idx

    def get_points_in_rect(
        self, view: CurveViewProtocol, transform: Transform, x1: float, y1: float, x2: float, y2: float
    ) -> list[int]:
        """
        Find all points within a rectangular region using spatial indexing.

        Args:
            view: The curve view containing the data
            transform: Transform for coordinate conversion
            x1, y1: Top-left corner of rectangle (screen coordinates)
            x2, y2: Bottom-right corner of rectangle (screen coordinates)

        Returns:
            List of point indices within the rectangle
        """
        # Rebuild index if needed
        self.rebuild_index(view, transform)

        curve_data = getattr(view, "curve_data", None)
        if not curve_data:
            return []

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
                            if point_idx < len(curve_data):
                                point = curve_data[point_idx]
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
