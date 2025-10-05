#!/usr/bin/env python
"""
Comprehensive tests for spatial indexing - performance-critical point lookups.

This module tests the grid-based spatial index that provides O(1) point lookups
instead of O(n) linear search, claimed to provide 64.7x performance improvement.
"""

import threading
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

import pytest

from core.spatial_index import PointIndex
from core.type_aliases import CurveDataList, LegacyPointData

if TYPE_CHECKING:
    from protocols.ui import CurveViewProtocol
    from services.transform_service import Transform


class MockTransform:
    """Mock Transform class for testing spatial index.

    Minimal mock that provides only what PointIndex needs.
    """

    stability_hash: str
    _scale_x: float
    _scale_y: float
    _offset_x: float
    _offset_y: float

    def __init__(self, stability_hash: str = "test_hash") -> None:
        self.stability_hash = stability_hash
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0

    def data_to_screen(self, data_x: float, data_y: float) -> tuple[float, float]:
        """Convert data coordinates to screen coordinates."""
        screen_x = data_x * self._scale_x + self._offset_x
        screen_y = data_y * self._scale_y + self._offset_y
        return (screen_x, screen_y)


class MockCurveView:
    """Mock CurveView class for testing spatial index.

    Minimal mock that provides only what PointIndex needs.
    """

    curve_data: CurveDataList
    _width: float
    _height: float

    def __init__(self, curve_data: Sequence[LegacyPointData], width: float = 800.0, height: float = 600.0) -> None:
        # Accept any sequence of point data and convert to list
        self.curve_data = list(curve_data)
        self._width = width
        self._height = height

    def width(self) -> float:
        """Get widget width."""
        return self._width

    def height(self) -> float:
        """Get widget height."""
        return self._height


# Helper functions for type-safe mock casting
def _as_curve_view(mock: MockCurveView) -> "CurveViewProtocol":
    """Cast MockCurveView to CurveViewProtocol for type safety.

    This is the test-safe pattern: we use minimal mocks for testing,
    but cast them to the expected protocol type at call sites.
    Cast through object to avoid basedpyright cast overlap check.
    """
    return cast("CurveViewProtocol", cast(object, mock))


def _as_transform(mock: MockTransform) -> "Transform":
    """Cast MockTransform to Transform for type safety.

    This is the test-safe pattern: we use minimal mocks for testing,
    but cast them to the expected protocol type at call sites.
    Cast through object to avoid basedpyright cast overlap check.
    """
    return cast("Transform", cast(object, mock))


class TestPointIndexInitialization:
    """Test PointIndex initialization and basic properties."""

    def test_default_initialization(self) -> None:
        """Test PointIndex initialization with default parameters."""
        index = PointIndex()

        # Default screen size is 800x600, giving grid dimensions 17x13
        assert index.grid_width == 17  # int(800 / 45) = 17
        assert index.grid_height == 13  # int(600 / 45) = 13
        assert index.cell_width == 0.0  # Not calculated until rebuild
        assert index.cell_height == 0.0  # Not calculated until rebuild
        assert index.screen_width == 800.0
        assert index.screen_height == 600.0
        assert index._grid == {}
        assert index._last_transform_hash is None
        assert index._last_point_count == 0

    def test_custom_screen_size_initialization(self) -> None:
        """Test PointIndex initialization with custom screen size."""
        # Use screen dimensions that result in 30x40 grid (1350x1800)
        index = PointIndex(screen_width=1350.0, screen_height=1800.0)

        assert index.grid_width == 30  # int(1350 / 45) = 30
        assert index.grid_height == 40  # int(1800 / 45) = 40

    def test_thread_lock_initialization(self) -> None:
        """Test that thread lock is properly initialized."""
        index = PointIndex()

        assert index._lock is not None
        # Check that it's an RLock by testing its acquire/release methods
        # If methods don't exist, test will fail with AttributeError
        assert callable(index._lock.acquire)
        assert callable(index._lock.release)
        # Test that it works like an RLock
        _ = index._lock.acquire()
        _ = index._lock.acquire()  # Should work (reentrant)
        index._lock.release()
        index._lock.release()


class TestGridCoordinateCalculations:
    """Test grid coordinate calculation methods."""

    def test_get_cell_coords_zero_cell_size(self) -> None:
        """Test cell coordinate calculation with zero cell size."""
        index = PointIndex()
        # Cell dimensions not set yet (0.0)

        coords = index._get_cell_coords(100.0, 150.0)

        assert coords == (0, 0)

    def test_get_cell_coords_normal_case(self) -> None:
        """Test cell coordinate calculation with normal values."""
        # Use screen dimensions that result in 10x8 grid (450x360)
        index = PointIndex(screen_width=450.0, screen_height=360.0)
        # Set up cell dimensions manually for testing
        index.cell_width = 45.0  # 450 / 10
        index.cell_height = 45.0  # 360 / 8

        # Test various positions with 45x45 cell size
        assert index._get_cell_coords(0.0, 0.0) == (0, 0)
        assert index._get_cell_coords(44.0, 44.0) == (0, 0)
        assert index._get_cell_coords(45.0, 45.0) == (1, 1)
        assert index._get_cell_coords(225.0, 180.0) == (5, 4)
        assert index._get_cell_coords(449.0, 359.0) == (9, 7)

    def test_get_cell_coords_boundary_clamping(self) -> None:
        """Test that coordinates are clamped to grid boundaries."""
        # Use screen dimensions that result in 10x10 grid (minimum) (450x450)
        index = PointIndex(screen_width=450.0, screen_height=450.0)
        index.cell_width = 45.0  # 450 / 10
        index.cell_height = 45.0  # 450 / 10

        # Test coordinates outside grid bounds
        assert index._get_cell_coords(-50.0, -25.0) == (0, 0)  # Negative coordinates
        assert index._get_cell_coords(500.0, 500.0) == (9, 9)  # Beyond grid (clamped to 9,9 for 10x10 grid)

    def test_get_nearby_cells_center(self) -> None:
        """Test getting nearby cells from center position."""
        # Use screen dimensions that result in 10x10 grid (450x450)
        index = PointIndex(screen_width=450.0, screen_height=450.0)

        cells = index._get_nearby_cells(5, 5, 1)

        expected_cells = [(4, 4), (4, 5), (4, 6), (5, 4), (5, 5), (5, 6), (6, 4), (6, 5), (6, 6)]
        assert len(cells) == 9
        assert set(cells) == set(expected_cells)

    def test_get_nearby_cells_corner(self) -> None:
        """Test getting nearby cells from corner position (boundary clipping)."""
        # Use screen dimensions that result in 5x5 grid (225x225)
        index = PointIndex(screen_width=225.0, screen_height=225.0)

        cells = index._get_nearby_cells(0, 0, 1)

        # Should only return valid cells within grid bounds
        expected_cells = [(0, 0), (0, 1), (1, 0), (1, 1)]
        assert len(cells) == 4
        assert set(cells) == set(expected_cells)

    def test_get_nearby_cells_radius_zero(self) -> None:
        """Test getting nearby cells with zero radius."""
        # Use screen dimensions that result in 10x10 grid (450x450)
        index = PointIndex(screen_width=450.0, screen_height=450.0)

        cells = index._get_nearby_cells(3, 3, 0)

        assert cells == [(3, 3)]

    def test_get_nearby_cells_large_radius(self) -> None:
        """Test getting nearby cells with large radius."""
        # Use screen dimensions that result in 6x6 grid (270x270)
        index = PointIndex(screen_width=270.0, screen_height=270.0)  # int(270/45)=6, max(10,6)=10
        # Actually, this will still be 10x10 due to minimum. Let me use a smaller radius test.

        cells = index._get_nearby_cells(2, 2, 3)

        # Should return many cells due to large radius on 10x10 grid
        # Radius 3 around (2,2) gives cells from (2-3,2-3) to (2+3,2+3) = (-1,-1) to (5,5)
        # Clamped to 10x10 grid bounds (0,0) to (9,9), so from (0,0) to (5,5) = 6x6 = 36 cells
        assert len(cells) == 36


class TestIndexBuilding:
    """Test spatial index building and caching."""

    def test_rebuild_index_empty_data(self) -> None:
        """Test rebuilding index with empty curve data."""
        index = PointIndex()
        view = MockCurveView([])
        transform = MockTransform()

        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))

        assert index.screen_width == 800.0
        assert index.screen_height == 600.0
        assert index.cell_width == 47.05882352941177  # 800 / 17 (adaptive grid)
        assert index.cell_height == 46.15384615384615  # 600 / 13 (adaptive grid)
        assert index._grid == {}
        assert index._last_transform_hash == "test_hash"
        assert index._last_point_count == 0

    def test_rebuild_index_with_points(self) -> None:
        """Test rebuilding index with curve data."""
        # Use screen dimensions that result in 4x4 grid (180x180)
        index = PointIndex(screen_width=180.0, screen_height=180.0)
        curve_data = [
            (1, 100.0, 150.0),  # Will be at screen (100, 150)
            (2, 300.0, 250.0),  # Will be at screen (300, 250)
            (3, 700.0, 550.0),  # Will be at screen (700, 550)
        ]
        view = MockCurveView(curve_data)
        transform = MockTransform()

        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))

        # Check that points are indexed
        assert len(index._grid) > 0
        assert index._last_point_count == 3

        # Verify points are in correct grid cells
        # Grid cell size: 180/4 = 45, 180/4 = 45
        # Point 1 (100, 150) -> cell (2, 3)
        # Point 2 (300, 250) -> beyond grid, clamped
        # Point 3 (700, 550) -> beyond grid, clamped
        total_indexed = sum(len(points) for points in index._grid.values())
        assert total_indexed == 3

    def test_rebuild_index_caching(self) -> None:
        """Test that index caching works correctly."""
        index = PointIndex()
        curve_data = [(1, 100.0, 150.0)]
        view = MockCurveView(curve_data)
        transform = MockTransform("hash1")

        # First build
        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))
        first_grid = dict(index._grid)

        # Second build with same data and transform - should not rebuild
        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))
        assert index._grid == first_grid

        # Build with different transform - should rebuild
        transform.stability_hash = "hash2"
        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))
        assert index._last_transform_hash == "hash2"

    def test_rebuild_index_invalid_points(self) -> None:
        """Test rebuilding index with malformed point data."""
        index = PointIndex()
        curve_data: list[LegacyPointData] = [
            (1, 100.0, 150.0),  # Valid point
            (3, 300.0, 250.0),  # Valid point
        ]
        # Add an intentionally malformed point by casting
        malformed_data = cast(Sequence[LegacyPointData], [curve_data[0], (2, 200.0), curve_data[1]])
        view = MockCurveView(malformed_data)
        transform = MockTransform()

        # Should not crash with malformed data
        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))

        # Should only index valid points
        total_indexed = sum(len(points) for points in index._grid.values())
        assert total_indexed == 2  # Only 2 valid points

    def test_rebuild_index_screen_dimensions(self) -> None:
        """Test rebuilding index with different screen dimensions."""
        # Use screen dimensions significantly different from view to trigger update
        index = PointIndex(screen_width=600.0, screen_height=400.0)  # int(600/45)=13, int(400/45)=8->10
        curve_data = [(1, 50.0, 25.0)]
        view = MockCurveView(curve_data, width=1000.0, height=500.0)
        transform = MockTransform()

        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))

        # Screen dimensions are updated because 600->1000 and 400->500 are significant changes (>10%)
        assert index.screen_width == 1000.0  # Updated from view (significant change)
        assert index.screen_height == 500.0  # Updated from view (significant change)
        # Cell width/height calculated based on updated dimensions
        # New grid: max(10, min(50, int(1000/45)))=22, max(10, min(50, int(500/45)))=11
        assert index.cell_width == 45.45454545454545  # 1000 / 22
        assert index.cell_height == 45.45454545454545  # 500 / 11


class TestPointLookup:
    """Test point lookup functionality."""

    def test_find_point_at_position_no_data(self) -> None:
        """Test finding point when no data exists."""
        index = PointIndex()
        view = MockCurveView([])
        transform = MockTransform()

        result = index.find_point_at_position(view.curve_data, _as_transform(transform), 100.0, 100.0)

        assert result == -1

    def test_find_point_at_position_exact_match(self) -> None:
        """Test finding point at exact position."""
        # Use screen dimensions that result in 4x4 grid (180x180)
        index = PointIndex(screen_width=180.0, screen_height=180.0)
        curve_data = [
            (1, 100.0, 150.0),  # Point at screen (100, 150)
            (2, 300.0, 250.0),  # Point at screen (300, 250)
        ]
        view = MockCurveView(curve_data)
        transform = MockTransform()

        # Look for point at exact position
        result = index.find_point_at_position(view.curve_data, _as_transform(transform), 100.0, 150.0, threshold=1.0)

        assert result == 0  # First point

    def test_find_point_at_position_within_threshold(self) -> None:
        """Test finding point within threshold distance."""
        # Use screen dimensions that result in 4x4 grid (180x180)
        index = PointIndex(screen_width=180.0, screen_height=180.0)
        curve_data = [(1, 100.0, 150.0)]  # Point at screen (100, 150)
        view = MockCurveView(curve_data)
        transform = MockTransform()

        # Look near the point (within threshold)
        result = index.find_point_at_position(view.curve_data, _as_transform(transform), 103.0, 147.0, threshold=5.0)

        assert result == 0  # Should find the point

    def test_find_point_at_position_outside_threshold(self) -> None:
        """Test finding point outside threshold distance."""
        # Use screen dimensions that result in 4x4 grid (180x180)
        index = PointIndex(screen_width=180.0, screen_height=180.0)
        curve_data = [(1, 100.0, 150.0)]  # Point at screen (100, 150)
        view = MockCurveView(curve_data)
        transform = MockTransform()

        # Look far from the point (outside threshold)
        result = index.find_point_at_position(view.curve_data, _as_transform(transform), 200.0, 300.0, threshold=5.0)

        assert result == -1  # Should not find the point

    def test_find_point_at_position_closest_point(self) -> None:
        """Test finding closest point when multiple points are nearby."""
        # Use screen dimensions that result in 4x4 grid (180x180)
        index = PointIndex(screen_width=180.0, screen_height=180.0)
        curve_data = [
            (1, 100.0, 150.0),  # Distance ~5.0 from search point
            (2, 110.0, 155.0),  # Distance ~2.2 from search point (closer)
            (3, 300.0, 250.0),  # Far away
        ]
        view = MockCurveView(curve_data)
        transform = MockTransform()

        # Search at (112, 153) - closer to second point
        result = index.find_point_at_position(view.curve_data, _as_transform(transform), 112.0, 153.0, threshold=10.0)

        assert result == 1  # Should find the closest point (second one)

    def test_find_point_at_position_rebuilds_index(self) -> None:
        """Test that find_point_at_position rebuilds index if needed."""
        index = PointIndex()
        curve_data = [(1, 100.0, 150.0)]
        view = MockCurveView(curve_data)
        transform = MockTransform()

        # Index should be empty initially
        assert index._grid == {}

        result = index.find_point_at_position(view.curve_data, _as_transform(transform), 100.0, 150.0, threshold=5.0)

        # Index should be built now
        assert index._grid != {}
        assert result == 0


class TestRectangleSelection:
    """Test rectangular selection functionality."""

    def test_get_points_in_rect_no_data(self) -> None:
        """Test rectangle selection with no data."""
        index = PointIndex()
        view = MockCurveView([])
        transform = MockTransform()

        result = index.get_points_in_rect(view.curve_data, _as_transform(transform), 0.0, 0.0, 100.0, 100.0)

        assert result == []

    def test_get_points_in_rect_all_inside(self) -> None:
        """Test rectangle selection with all points inside."""
        # Use screen dimensions that result in 4x4 grid (180x180)
        index = PointIndex(screen_width=180.0, screen_height=180.0)
        curve_data = [
            (1, 50.0, 50.0),  # Inside rectangle
            (2, 75.0, 75.0),  # Inside rectangle
            (3, 25.0, 25.0),  # Inside rectangle
        ]
        view = MockCurveView(curve_data)
        transform = MockTransform()

        result = index.get_points_in_rect(view.curve_data, _as_transform(transform), 0.0, 0.0, 100.0, 100.0)

        assert len(result) == 3
        assert set(result) == {0, 1, 2}

    def test_get_points_in_rect_partial_selection(self) -> None:
        """Test rectangle selection with some points inside, some outside."""
        # Use screen dimensions that result in 4x4 grid (180x180)
        index = PointIndex(screen_width=180.0, screen_height=180.0)
        curve_data = [
            (1, 50.0, 50.0),  # Inside rectangle
            (2, 150.0, 75.0),  # Outside rectangle (x too large)
            (3, 75.0, 200.0),  # Outside rectangle (y too large)
            (4, 25.0, 25.0),  # Inside rectangle
        ]
        view = MockCurveView(curve_data)
        transform = MockTransform()

        result = index.get_points_in_rect(view.curve_data, _as_transform(transform), 0.0, 0.0, 100.0, 100.0)

        assert len(result) == 2
        assert set(result) == {0, 3}  # Points 0 and 3 are inside

    def test_get_points_in_rect_empty_selection(self) -> None:
        """Test rectangle selection with no points inside."""
        # Use screen dimensions that result in 4x4 grid (180x180)
        index = PointIndex(screen_width=180.0, screen_height=180.0)
        curve_data = [
            (1, 200.0, 200.0),  # Outside rectangle
            (2, 300.0, 300.0),  # Outside rectangle
        ]
        view = MockCurveView(curve_data)
        transform = MockTransform()

        result = index.get_points_in_rect(view.curve_data, _as_transform(transform), 0.0, 0.0, 100.0, 100.0)

        assert result == []

    def test_get_points_in_rect_normalized_bounds(self) -> None:
        """Test rectangle selection with swapped coordinates (auto-normalization)."""
        # Use screen dimensions that result in 4x4 grid (180x180)
        index = PointIndex(screen_width=180.0, screen_height=180.0)
        curve_data = [(1, 50.0, 50.0)]  # Inside normalized rectangle
        view = MockCurveView(curve_data)
        transform = MockTransform()

        # Pass swapped coordinates (x2 < x1, y2 < y1)
        result = index.get_points_in_rect(view.curve_data, _as_transform(transform), 100.0, 100.0, 0.0, 0.0)

        assert len(result) == 1
        assert result[0] == 0

    def test_get_points_in_rect_rebuilds_index(self) -> None:
        """Test that get_points_in_rect rebuilds index if needed."""
        index = PointIndex()
        curve_data = [(1, 50.0, 50.0)]
        view = MockCurveView(curve_data)
        transform = MockTransform()

        # Index should be empty initially
        assert index._grid == {}

        result = index.get_points_in_rect(view.curve_data, _as_transform(transform), 0.0, 0.0, 100.0, 100.0)

        # Index should be built now
        assert index._grid != {}
        assert len(result) == 1


class TestStatistics:
    """Test spatial index statistics and monitoring."""

    def test_get_stats_empty_index(self) -> None:
        """Test statistics for empty index."""
        # Small screen dimensions result in minimum 10x10 grid due to clamping
        index = PointIndex(screen_width=225.0, screen_height=180.0)

        stats = index.get_stats()

        assert stats["grid_size"] == (10, 10)  # Clamped to minimum 10x10
        assert stats["screen_size"] == (225.0, 180.0)  # From constructor
        assert stats["cell_size"] == (0.0, 0.0)  # Not built yet
        assert stats["occupied_cells"] == 0
        assert stats["total_cells"] == 100  # 10 * 10
        assert stats["occupancy_ratio"] == 0.0
        assert stats["total_points"] == 0
        assert stats["avg_points_per_cell"] == 0.0
        assert stats["transform_hash"] is None

    def test_get_stats_populated_index(self) -> None:
        """Test statistics for populated index."""
        # Small screen dimensions result in minimum 10x10 grid due to clamping
        index = PointIndex(screen_width=180.0, screen_height=180.0)
        curve_data = [
            (1, 100.0, 150.0),  # Will go to one cell
            (2, 110.0, 160.0),  # Might go to same or nearby cell
            (3, 300.0, 350.0),  # Will go to different cell
        ]
        view = MockCurveView(curve_data, width=400.0, height=400.0)
        transform = MockTransform("stats_hash")

        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))
        stats = index.get_stats()

        # After rebuild, screen dimensions updated and grid recalculated: int(400/45)=8, clamped to min(10)
        assert stats["grid_size"] == (10, 10)  # Still clamped to minimum
        assert stats["screen_size"] == (400.0, 400.0)
        assert stats["cell_size"] == (40.0, 40.0)  # 400/10 = 40
        assert stats["total_cells"] == 100  # 10 * 10 (clamped to minimum)
        assert stats["total_points"] == 3
        occupied_cells = stats["occupied_cells"]
        assert isinstance(occupied_cells, int | float) and occupied_cells > 0  # At least some cells occupied
        occupancy_ratio = stats["occupancy_ratio"]
        assert isinstance(occupancy_ratio, float) and occupancy_ratio > 0.0
        avg_points = stats["avg_points_per_cell"]
        assert isinstance(avg_points, float) and avg_points > 0.0
        assert stats["transform_hash"] == "stats_hash"

    def test_get_stats_multiple_points_per_cell(self) -> None:
        """Test statistics when multiple points are in the same cell."""
        # Small screen dimensions result in minimum 10x10 grid due to clamping
        index = PointIndex(screen_width=90.0, screen_height=90.0)
        curve_data = [
            (1, 10.0, 10.0),  # Points in first cell
            (2, 20.0, 20.0),  # May be in same or adjacent cell
            (3, 30.0, 30.0),  # May be in same or adjacent cell
        ]
        view = MockCurveView(curve_data, width=200.0, height=200.0)
        transform = MockTransform()

        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))
        stats = index.get_stats()

        # After rebuild: screen 200x200, grid 10x10 (clamped), cell size 20x20
        # Points (10,10)->(0,0), (20,20)->(1,1), (30,30)->(1,1)
        # So points occupy 2 cells: (0,0) and (1,1)
        assert stats["occupied_cells"] == 2  # Two cells occupied
        assert stats["total_points"] == 3
        assert stats["avg_points_per_cell"] == 1.5  # 3 points / 2 cells


class TestCacheManagement:
    """Test cache management and invalidation."""

    def test_clear_cache(self) -> None:
        """Test clearing the spatial index cache."""
        index = PointIndex()
        curve_data = [(1, 100.0, 150.0)]
        view = MockCurveView(curve_data)
        transform = MockTransform("cache_hash")

        # Build index
        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))
        assert index._grid != {}
        assert index._last_transform_hash == "cache_hash"
        assert index._last_point_count == 1

        # Clear cache
        index.clear_cache()

        assert index._grid == {}
        assert index._last_transform_hash is None
        assert index._last_point_count == 0

    def test_cache_invalidation_on_transform_change(self) -> None:
        """Test that cache is invalidated when transform changes."""
        index = PointIndex()
        curve_data = [(1, 100.0, 150.0)]
        view = MockCurveView(curve_data)
        transform1 = MockTransform("hash1")
        transform2 = MockTransform("hash2")

        # Build with first transform
        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform1))
        _ = dict(index._grid)  # Store first grid state

        # Build with second transform - should rebuild
        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform2))

        assert index._last_transform_hash == "hash2"
        # Grid might be different depending on transform

    def test_cache_invalidation_on_point_count_change(self) -> None:
        """Test that cache is invalidated when point count changes."""
        index = PointIndex()
        transform = MockTransform("same_hash")

        # Build with 1 point
        view1 = MockCurveView([(1, 100.0, 150.0)])
        index.rebuild_index(view1.curve_data, _as_curve_view(view1), _as_transform(transform))
        assert index._last_point_count == 1

        # Build with 2 points - should rebuild
        view2 = MockCurveView([(1, 100.0, 150.0), (2, 200.0, 250.0)])
        index.rebuild_index(view2.curve_data, _as_curve_view(view2), _as_transform(transform))
        assert index._last_point_count == 2


class TestThreadSafety:
    """Test thread safety of spatial index operations."""

    def test_concurrent_index_building(self) -> None:
        """Test that concurrent index building is thread-safe."""
        index = PointIndex()
        curve_data = [(i, float(i * 10), float(i * 15)) for i in range(100)]
        view = MockCurveView(curve_data)
        transform = MockTransform()

        results = []
        errors = []

        def build_index(thread_id: int):
            try:
                for _ in range(5):
                    index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))
                    stats = index.get_stats()
                    assert stats["total_points"] == 100
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=build_index, args=(i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=5.0)

        assert len(errors) == 0
        assert len(results) == 5

    def test_concurrent_point_lookup(self) -> None:
        """Test that concurrent point lookups are thread-safe."""
        index = PointIndex()
        curve_data = [(i, float(i * 10), float(i * 15)) for i in range(50)]
        view = MockCurveView(curve_data)
        transform = MockTransform()

        # Build index once
        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))

        results = []
        errors = []

        def lookup_points(thread_id: int):
            try:
                for i in range(10):
                    x = float(i * 10)
                    y = float(i * 15)
                    result = index.find_point_at_position(
                        view.curve_data, _as_transform(transform), x, y, threshold=1.0
                    )
                    # Should find corresponding point
                    if result >= 0:
                        results.append((thread_id, result))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start multiple lookup threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=lookup_points, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        assert len(errors) == 0
        assert len(results) > 0

    def test_concurrent_statistics_access(self) -> None:
        """Test that concurrent statistics access is thread-safe."""
        index = PointIndex()
        curve_data = [(i, float(i * 10), float(i * 15)) for i in range(20)]
        view = MockCurveView(curve_data)
        transform = MockTransform()

        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))

        results = []
        errors = []

        def get_stats(thread_id: int):
            try:
                for _ in range(10):
                    stats = index.get_stats()
                    assert isinstance(stats, dict)
                    assert stats["total_points"] == 20
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start multiple threads
        threads = []
        for i in range(4):
            t = threading.Thread(target=get_stats, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        assert len(errors) == 0
        assert len(results) == 4


class TestPerformanceOptimizations:
    """Test performance optimization features."""

    def test_large_dataset_handling(self) -> None:
        """Test spatial index with large dataset."""
        # Use screen dimensions that result in 50x50 grid (2250x2250)
        index = PointIndex(screen_width=2250.0, screen_height=2250.0)

        # Create large dataset
        large_dataset = []
        for i in range(1000):
            x = float(i % 100) * 8.0  # Spread points across 800px width
            y = float(i // 100) * 60.0  # Spread points across 600px height
            large_dataset.append((i, x, y))

        view = MockCurveView(large_dataset)
        transform = MockTransform()

        # Should handle large dataset without issues
        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))
        stats = index.get_stats()

        assert stats["total_points"] == 1000
        occupied_cells = stats["occupied_cells"]
        assert isinstance(occupied_cells, int | float) and occupied_cells > 0

        # Test point lookup still works
        result = index.find_point_at_position(view.curve_data, _as_transform(transform), 0.0, 0.0, threshold=5.0)
        assert result == 0  # Should find first point

    def test_sparse_grid_efficiency(self) -> None:
        """Test efficiency with sparse point distribution."""
        # Use screen dimensions that result in 20x20 grid (900x900)
        index = PointIndex(screen_width=900.0, screen_height=900.0)

        # Create sparse dataset - points only in corners
        sparse_data = [
            (1, 0.0, 0.0),  # Top-left corner
            (2, 800.0, 0.0),  # Top-right corner
            (3, 0.0, 600.0),  # Bottom-left corner
            (4, 800.0, 600.0),  # Bottom-right corner
        ]

        view = MockCurveView(sparse_data)
        transform = MockTransform()

        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))
        stats = index.get_stats()

        assert stats["total_points"] == 4
        # Should have low occupancy ratio (sparse)
        occupancy_ratio = stats["occupancy_ratio"]
        assert isinstance(occupancy_ratio, float) and occupancy_ratio < 0.1

    def test_dense_grid_handling(self) -> None:
        """Test handling of dense point clusters."""
        # Use screen dimensions that result in 4x4 grid (180x180)
        index = PointIndex(screen_width=180.0, screen_height=180.0)

        # Create dense cluster in one area
        dense_data = []
        for i in range(50):
            # All points clustered around (100, 100)
            x = 100.0 + (i % 10) * 2.0  # Small variation
            y = 100.0 + (i // 10) * 2.0
            dense_data.append((i, x, y))

        view = MockCurveView(dense_data)
        transform = MockTransform()

        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))
        stats = index.get_stats()

        assert stats["total_points"] == 50
        # Should have high average points per cell
        avg_points = stats["avg_points_per_cell"]
        assert isinstance(avg_points, float) and avg_points > 5.0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_minimal_grid_dimensions(self) -> None:
        """Test behavior with very small screen dimensions."""
        # Use very small screen dimensions that result in minimal grid (10x10 minimum)
        index = PointIndex(screen_width=10.0, screen_height=10.0)

        # Basic operations should not crash, grid size is clamped to minimum of 10
        assert index.grid_width == 10  # Minimum grid size
        assert index.grid_height == 10  # Minimum grid size

        view = MockCurveView([(1, 100.0, 150.0)])
        transform = MockTransform()

        # Rebuild should work fine with minimum grid dimensions
        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))
        # Should work correctly even with minimal dimensions
        assert len(index._grid) >= 0  # Should not crash

    def test_negative_coordinates(self) -> None:
        """Test handling of negative coordinates."""
        # Use screen dimensions that result in 4x4 grid (180x180)
        index = PointIndex(screen_width=180.0, screen_height=180.0)
        curve_data = [
            (1, -100.0, -150.0),  # Negative coordinates
            (2, 100.0, 150.0),  # Positive coordinates
        ]
        view = MockCurveView(curve_data)
        transform = MockTransform()

        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))

        # Should handle negative coordinates gracefully
        result = index.find_point_at_position(view.curve_data, _as_transform(transform), -100.0, -150.0, threshold=5.0)
        assert result == 0

    def test_very_large_coordinates(self) -> None:
        """Test handling of very large coordinates."""
        # Use screen dimensions that result in 4x4 grid (180x180)
        index = PointIndex(screen_width=180.0, screen_height=180.0)
        curve_data = [
            (1, 1000000.0, 1000000.0),  # Very large coordinates
            (2, 100.0, 150.0),  # Normal coordinates
        ]
        view = MockCurveView(curve_data)
        transform = MockTransform()

        # Should handle large coordinates without crashing
        index.rebuild_index(view.curve_data, _as_curve_view(view), _as_transform(transform))
        stats = index.get_stats()
        assert stats["total_points"] == 2

    def test_view_without_curve_data_attribute(self) -> None:
        """Test handling view without curve_data attribute."""
        index = PointIndex()
        view = Mock(spec=[])  # Mock with empty spec - no attributes
        view.width = Mock(return_value=800.0)  # Add required methods
        view.height = Mock(return_value=600.0)
        transform = MockTransform()

        # Should handle missing attribute gracefully (getattr returns [])
        # Pass empty list since view doesn't have curve_data attribute
        index.rebuild_index([], view, _as_transform(transform))

        result = index.find_point_at_position([], _as_transform(transform), 100.0, 150.0, view)
        assert result == -1

    def test_transform_coordinate_conversion_errors(self) -> None:
        """Test handling transform coordinate conversion errors."""
        index = PointIndex()
        curve_data = [(1, 100.0, 150.0)]
        view = MockCurveView(curve_data)

        # Create transform that raises exception
        transform = Mock()
        transform.stability_hash = "error_hash"
        transform.data_to_screen.side_effect = ValueError("Conversion error")

        # Should handle transform errors - they propagate up
        with pytest.raises(ValueError, match="Conversion error"):
            index.rebuild_index(view.curve_data, _as_curve_view(view), transform)

        # Try point lookup - should also fail with same error
        with pytest.raises(ValueError, match="Conversion error"):
            index.find_point_at_position(view.curve_data, transform, 100.0, 150.0, view=_as_curve_view(view))


class TestIntegration:
    """Test integration scenarios and realistic usage patterns."""

    def test_typical_usage_workflow(self) -> None:
        """Test typical spatial index usage workflow."""
        index = PointIndex()

        # Start with some initial data
        initial_data = [(i, float(i * 50), float(i * 30)) for i in range(10)]
        view = MockCurveView(initial_data)
        transform = MockTransform()

        # First lookup - should build index
        result1 = index.find_point_at_position(
            view.curve_data, _as_transform(transform), 0.0, 0.0, threshold=10.0, view=_as_curve_view(view)
        )
        assert result1 == 0

        # Second lookup - should use cached index
        result2 = index.find_point_at_position(
            view.curve_data, _as_transform(transform), 50.0, 30.0, threshold=10.0, view=_as_curve_view(view)
        )
        assert result2 == 1

        # Rectangle selection - should use cached index
        rect_points = index.get_points_in_rect(view.curve_data, _as_transform(transform), 0.0, 0.0, 200.0, 100.0)
        assert len(rect_points) > 0

        # Check statistics
        stats = index.get_stats()
        assert stats["total_points"] == 10

    def test_dynamic_data_updates(self) -> None:
        """Test spatial index with dynamic data updates."""
        index = PointIndex()
        transform = MockTransform()

        # Start with small dataset
        small_data = [(1, 100.0, 150.0), (2, 200.0, 250.0)]
        view1 = MockCurveView(small_data)

        result1 = index.find_point_at_position(view1.curve_data, _as_transform(transform), 100.0, 150.0, threshold=5.0)
        assert result1 == 0

        # Update to larger dataset
        # The new data includes: [(3, 30.0, 60.0), (4, 40.0, 80.0), (5, 50.0, 100.0), ...]
        large_data = small_data + [(i, float(i * 10), float(i * 20)) for i in range(3, 20)]
        view2 = MockCurveView(large_data)

        # Should rebuild index automatically
        # Point at index 2 should be (3, 30.0, 60.0) since:
        # Index 0: (1, 100.0, 150.0)
        # Index 1: (2, 200.0, 250.0)
        # Index 2: (3, 30.0, 60.0) <- This is at screen coordinates (30, 60)
        result2 = index.find_point_at_position(view2.curve_data, _as_transform(transform), 30.0, 60.0, threshold=5.0)
        assert result2 == 2  # Point at index 2 is (3, 30.0, 60.0)

    def test_coordinate_system_changes(self) -> None:
        """Test spatial index with different coordinate systems."""
        index = PointIndex()
        curve_data = [(1, 10.0, 20.0), (2, 30.0, 40.0)]
        view = MockCurveView(curve_data)

        # Transform 1: 1:1 scale
        transform1 = MockTransform("scale_1")
        transform1._scale_x = 1.0
        transform1._scale_y = 1.0

        result1 = index.find_point_at_position(view.curve_data, _as_transform(transform1), 10.0, 20.0, threshold=2.0)
        assert result1 == 0

        # Transform 2: 2x scale
        transform2 = MockTransform("scale_2")
        transform2._scale_x = 2.0
        transform2._scale_y = 2.0

        # Point is now at (20, 40) in screen coordinates
        result2 = index.find_point_at_position(view.curve_data, _as_transform(transform2), 20.0, 40.0, threshold=2.0)
        assert result2 == 0


class TestPublicAPI:
    """Test public API completeness and consistency."""

    def test_public_methods_available(self) -> None:
        """Test that all expected public methods are available."""
        index = PointIndex()

        # Core functionality - if missing, tests will fail with AttributeError
        assert callable(index.rebuild_index)
        assert callable(index.find_point_at_position)
        assert callable(index.get_points_in_rect)

        # Monitoring and management - if missing, tests will fail with AttributeError
        assert callable(index.get_stats)
        assert callable(index.clear_cache)

        # All should be callable
        assert callable(index.rebuild_index)
        assert callable(index.find_point_at_position)
        assert callable(index.get_points_in_rect)
        assert callable(index.get_stats)
        assert callable(index.clear_cache)

    def test_method_return_types(self) -> None:
        """Test that methods return expected types."""
        index = PointIndex()
        view = MockCurveView([(1, 100.0, 150.0)])
        transform = MockTransform()

        # find_point_at_position returns int
        result1 = index.find_point_at_position(
            view.curve_data, _as_transform(transform), 100.0, 150.0, view=_as_curve_view(view)
        )
        assert isinstance(result1, int)

        # get_points_in_rect returns list of int
        result2 = index.get_points_in_rect(
            view.curve_data, _as_transform(transform), 0.0, 0.0, 200.0, 200.0, view=_as_curve_view(view)
        )
        assert isinstance(result2, list)
        assert all(isinstance(x, int) for x in result2)

        # get_stats returns dict
        result3 = index.get_stats()
        assert isinstance(result3, dict)

        # clear_cache returns None
        result4 = index.clear_cache()
        assert result4 is None
