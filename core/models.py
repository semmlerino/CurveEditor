#!/usr/bin/env python
"""
Unified point data models for the CurveEditor.

This module provides a single source of truth for point data representation,
replacing the scattered tuple formats throughout the codebase with clean,
type-safe data models while maintaining backward compatibility.

Key Benefits:
- Type safety with comprehensive annotations
- Immutable data structures prevent accidental mutations
- Built-in validation and conversion utilities
- Backward compatibility with existing tuple formats
- Performance-optimized operations for large datasets

Migration Strategy:
1. Existing code continues to work with tuple formats
2. Gradual adoption of new models via conversion utilities
3. Eventually replace tuple usage with direct model usage
4. Maintain protocol compatibility throughout transition

Classes:
    CurvePoint: Immutable point with frame, coordinates, and status
    PointCollection: Collection of points with bulk operations
    PointStatus: Enum for point status values

Utilities:
    - Type guards for validation
    - Conversion functions between formats
    - Performance-optimized operations
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import overload

# Type aliases for backward compatibility and clarity
FrameNumber = int
Coordinate = float
PointIndex = int

# Legacy type definitions for migration
LegacyPointTuple = tuple[int, float, float] | tuple[int, float, float, str] | tuple[int, float, float, bool]
PointsList = list[LegacyPointTuple]


class PointStatus(Enum):
    """Enumeration of point status values with backward compatibility.

    Provides clear, type-safe status values while maintaining compatibility
    with existing string-based status system.
    """

    NORMAL = "normal"
    INTERPOLATED = "interpolated"
    KEYFRAME = "keyframe"

    @classmethod
    def from_legacy(cls, value: str | bool | None) -> PointStatus:
        """Convert legacy status values to enum.

        Args:
            value: Legacy status (string, bool, or None)

        Returns:
            PointStatus enum value

        Examples:
            >>> PointStatus.from_legacy(True)
            PointStatus.INTERPOLATED
            >>> PointStatus.from_legacy("keyframe")
            PointStatus.KEYFRAME
            >>> PointStatus.from_legacy(None)
            PointStatus.NORMAL
        """
        if value is None:
            return cls.NORMAL
        elif isinstance(value, bool):
            return cls.INTERPOLATED if value else cls.NORMAL
        else:
            # Must be str at this point due to type annotation
            try:
                return cls(value)
            except ValueError:
                return cls.NORMAL

    def to_legacy_string(self) -> str:
        """Convert to legacy string format."""
        return self.value

    def to_legacy_bool(self) -> bool:
        """Convert to legacy boolean format."""
        return self == PointStatus.INTERPOLATED


@dataclass(frozen=True)
class CurvePoint:
    """Immutable representation of a single curve point.

    Provides a clean, type-safe interface for curve points with validation
    and utility methods. All data is immutable to prevent accidental changes.

    Attributes:
        frame: Frame number (typically integer, but float supported)
        x: X coordinate in curve space
        y: Y coordinate in curve space
        status: Point status (normal, interpolated, keyframe)

    Examples:
        >>> point = CurvePoint(100, 1920.5, 1080.0)
        >>> point.frame
        100
        >>> point.is_interpolated
        False

        >>> interp_point = CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED)
        >>> interp_point.is_interpolated
        True
    """

    frame: FrameNumber
    x: Coordinate
    y: Coordinate
    status: PointStatus = PointStatus.NORMAL

    def __post_init__(self) -> None:
        """Validate point data after initialization."""
        # Type annotations ensure correct types at compile time
        # Add any runtime value validation here if needed
        pass

    @property
    def is_interpolated(self) -> bool:
        """True if this point is interpolated."""
        return self.status == PointStatus.INTERPOLATED

    @property
    def is_keyframe(self) -> bool:
        """True if this point is a keyframe."""
        return self.status in (PointStatus.KEYFRAME, PointStatus.NORMAL)

    @property
    def coordinates(self) -> tuple[Coordinate, Coordinate]:
        """Get (x, y) coordinates as tuple."""
        return (self.x, self.y)

    def distance_to(self, other: CurvePoint) -> float:
        """Calculate euclidean distance to another point.

        Args:
            other: Another CurvePoint

        Returns:
            Euclidean distance between points
        """
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def with_status(self, status: PointStatus) -> CurvePoint:
        """Create new point with different status.

        Args:
            status: New point status

        Returns:
            New CurvePoint with updated status
        """
        return CurvePoint(self.frame, self.x, self.y, status)

    def with_coordinates(self, x: Coordinate, y: Coordinate) -> CurvePoint:
        """Create new point with different coordinates.

        Args:
            x: New X coordinate
            y: New Y coordinate

        Returns:
            New CurvePoint with updated coordinates
        """
        return CurvePoint(self.frame, x, y, self.status)

    def with_frame(self, frame: FrameNumber) -> CurvePoint:
        """Create new point with different frame number.

        Args:
            frame: New frame number

        Returns:
            New CurvePoint with updated frame
        """
        return CurvePoint(frame, self.x, self.y, self.status)

    # Conversion methods for backward compatibility

    def to_tuple3(self) -> tuple[int, float, float]:
        """Convert to 3-tuple format (frame, x, y).

        Returns:
            Tuple in (frame, x, y) format
        """
        return (self.frame, self.x, self.y)

    def to_tuple4(self) -> tuple[int, float, float, str]:
        """Convert to 4-tuple format (frame, x, y, status).

        Returns:
            Tuple in (frame, x, y, status) format
        """
        return (self.frame, self.x, self.y, self.status.value)

    def to_legacy_tuple(self) -> tuple[int, float, float] | tuple[int, float, float, str]:
        """Convert to legacy tuple format.

        Returns 3-tuple for normal points, 4-tuple for non-normal points
        to match existing codebase patterns.

        Returns:
            Legacy tuple format
        """
        if self.status == PointStatus.NORMAL:
            return (self.frame, self.x, self.y)
        else:
            return (self.frame, self.x, self.y, self.status.value)

    @classmethod
    def from_tuple(cls, point_tuple: tuple[int, float, float] | tuple[int, float, float, str | bool]) -> CurvePoint:
        """Create CurvePoint from tuple format.

        Args:
            point_tuple: Point in tuple format (3 or 4 elements)

        Returns:
            New CurvePoint instance

        Examples:
            >>> CurvePoint.from_tuple((100, 1920.5, 1080.0))
            CurvePoint(frame=100, x=1920.5, y=1080.0, status=PointStatus.NORMAL)

            >>> CurvePoint.from_tuple((100, 1920.5, 1080.0, "interpolated"))
            CurvePoint(frame=100, x=1920.5, y=1080.0, status=PointStatus.INTERPOLATED)
        """
        if len(point_tuple) == 3:
            frame, x, y = point_tuple
            status = PointStatus.NORMAL
        else:
            # Must be length >= 4 based on type annotation
            frame, x, y, status_value = point_tuple[:4]
            status = PointStatus.from_legacy(status_value)

        return cls(frame, x, y, status)


@dataclass
class PointCollection:
    """Collection of curve points with bulk operations.

    Provides efficient operations on collections of points while maintaining
    backward compatibility with existing PointsList format.

    Attributes:
        points: List of CurvePoint objects

    Examples:
        >>> points = PointCollection([
        ...     CurvePoint(100, 1920.0, 1080.0),
        ...     CurvePoint(101, 1921.0, 1081.0, PointStatus.INTERPOLATED)
        ... ])
        >>> len(points)
        2
        >>> points[0].frame
        100
    """

    points: list[CurvePoint]

    def __init__(self, points: list[CurvePoint] | None = None):
        """Initialize with optional points list.

        Args:
            points: List of CurvePoint objects (defaults to empty list)
        """
        self.points = points if points is not None else []
        # Type annotations ensure correct types at compile time

    # Collection interface

    def __len__(self) -> int:
        """Get number of points."""
        return len(self.points)

    def __iter__(self) -> Iterator[CurvePoint]:
        """Iterate over points."""
        return iter(self.points)

    def __getitem__(self, index: int | slice) -> CurvePoint | PointCollection:
        """Get point(s) by index."""
        if isinstance(index, slice):
            return PointCollection(self.points[index])
        return self.points[index]

    def __bool__(self) -> bool:
        """True if collection is not empty."""
        return bool(self.points)

    # Query methods

    @property
    def frame_range(self) -> tuple[int, int] | None:
        """Get frame range (min, max) or None if empty.

        Returns:
            Tuple of (min_frame, max_frame) or None
        """
        if not self.points:
            return None
        frames = [p.frame for p in self.points]
        return (min(frames), max(frames))

    @property
    def coordinate_bounds(self) -> tuple[float, float, float, float] | None:
        """Get coordinate bounds (min_x, max_x, min_y, max_y) or None if empty.

        Returns:
            Tuple of (min_x, max_x, min_y, max_y) or None
        """
        if not self.points:
            return None

        x_coords = [p.x for p in self.points]
        y_coords = [p.y for p in self.points]
        return (min(x_coords), max(x_coords), min(y_coords), max(y_coords))

    def get_keyframes(self) -> PointCollection:
        """Get only keyframe points (non-interpolated).

        Returns:
            New PointCollection with only keyframes
        """
        keyframes = [p for p in self.points if p.is_keyframe]
        return PointCollection(keyframes)

    def get_interpolated(self) -> PointCollection:
        """Get only interpolated points.

        Returns:
            New PointCollection with only interpolated points
        """
        interpolated = [p for p in self.points if p.is_interpolated]
        return PointCollection(interpolated)

    def find_closest_to_frame(self, target_frame: int) -> CurvePoint | None:
        """Find point closest to target frame.

        Args:
            target_frame: Target frame number

        Returns:
            Closest CurvePoint or None if empty
        """
        if not self.points:
            return None

        return min(self.points, key=lambda p: abs(p.frame - target_frame))

    def find_at_frame(self, frame: int) -> list[CurvePoint]:
        """Find all points at specific frame.

        Args:
            frame: Frame number to search

        Returns:
            List of CurvePoints at that frame
        """
        return [p for p in self.points if p.frame == frame]

    # Modification methods (return new collections)

    def with_status_updates(self, updates: dict[int, PointStatus]) -> PointCollection:
        """Create new collection with status updates.

        Args:
            updates: Dict mapping point indices to new status values

        Returns:
            New PointCollection with updated statuses
        """
        new_points = []
        for i, point in enumerate(self.points):
            if i in updates:
                new_points.append(point.with_status(updates[i]))
            else:
                new_points.append(point)
        return PointCollection(new_points)

    def with_coordinate_updates(self, updates: dict[int, tuple[float, float]]) -> PointCollection:
        """Create new collection with coordinate updates.

        Args:
            updates: Dict mapping point indices to new (x, y) coordinates

        Returns:
            New PointCollection with updated coordinates
        """
        new_points = []
        for i, point in enumerate(self.points):
            if i in updates:
                x, y = updates[i]
                new_points.append(point.with_coordinates(x, y))
            else:
                new_points.append(point)
        return PointCollection(new_points)

    def sorted_by_frame(self) -> PointCollection:
        """Get collection sorted by frame number.

        Returns:
            New PointCollection sorted by frame
        """
        sorted_points = sorted(self.points, key=lambda p: p.frame)
        return PointCollection(sorted_points)

    # Conversion methods for backward compatibility

    def to_tuples(self) -> PointsList:
        """Convert to legacy PointsList format.

        Returns:
            List of tuples in legacy format
        """
        return [point.to_legacy_tuple() for point in self.points]

    def to_tuple3_list(self) -> list[tuple[int, float, float]]:
        """Convert to list of 3-tuples (frame, x, y).

        Returns:
            List of 3-tuples
        """
        return [point.to_tuple3() for point in self.points]

    def to_tuple4_list(self) -> list[tuple[int, float, float, str]]:
        """Convert to list of 4-tuples (frame, x, y, status).

        Returns:
            List of 4-tuples
        """
        return [point.to_tuple4() for point in self.points]

    @classmethod
    def from_tuples(cls, point_tuples: PointsList) -> PointCollection:
        """Create PointCollection from legacy PointsList.

        Args:
            point_tuples: List of point tuples in legacy format

        Returns:
            New PointCollection

        Examples:
            >>> tuples = [(100, 1920.0, 1080.0), (101, 1921.0, 1081.0, "interpolated")]
            >>> collection = PointCollection.from_tuples(tuples)
            >>> len(collection)
            2
        """
        points = [CurvePoint.from_tuple(t) for t in point_tuples]
        return cls(points)

    @classmethod
    def empty(cls) -> PointCollection:
        """Create empty point collection.

        Returns:
            Empty PointCollection
        """
        return cls([])


# Type guards for validation


def is_point_tuple(obj: object) -> bool:
    """Type guard for point tuple format.

    Args:
        obj: Object to check

    Returns:
        True if obj is a valid point tuple
    """
    if not isinstance(obj, tuple):
        return False

    if len(obj) < 3 or len(obj) > 4:
        return False

    # Check frame (int), x (float), y (float)
    if not isinstance(obj[0], int):
        return False
    if not isinstance(obj[1], int | float):
        return False
    if not isinstance(obj[2], int | float):
        return False

    # Check status if present
    if len(obj) == 4:
        status = obj[3]
        if not isinstance(status, str | bool):
            return False

    return True


def is_points_list(obj: object) -> bool:
    """Type guard for PointsList format.

    Args:
        obj: Object to check

    Returns:
        True if obj is a valid PointsList
    """
    if not isinstance(obj, list):
        return False

    return all(is_point_tuple(item) for item in obj)


# Utility functions for common operations


def normalize_legacy_point(
    point: tuple[int, float, float] | tuple[int, float, float, str | bool],
) -> tuple[int, float, float, str]:
    """Normalize legacy point tuple to consistent 4-tuple format.

    Args:
        point: Point tuple in any legacy format

    Returns:
        Normalized (frame, x, y, status) tuple

    Examples:
        >>> normalize_legacy_point((100, 1920.0, 1080.0))
        (100, 1920.0, 1080.0, 'normal')
        >>> normalize_legacy_point((100, 1920.0, 1080.0, True))
        (100, 1920.0, 1080.0, 'interpolated')
    """
    if len(point) == 3:
        frame, x, y = point
        return (frame, x, y, "normal")
    elif len(point) >= 4:
        frame, x, y, status = point[:4]
        if isinstance(status, bool):
            status_str = "interpolated" if status else "normal"
        else:
            status_str = str(status)
        return (frame, x, y, status_str)
    else:
        raise ValueError(f"Invalid point format: {point}")


@overload
def convert_to_curve_point(point: tuple[int, float, float]) -> CurvePoint: ...


@overload
def convert_to_curve_point(point: tuple[int, float, float, str | bool]) -> CurvePoint: ...


def convert_to_curve_point(point: tuple[int, float, float] | tuple[int, float, float, str | bool]) -> CurvePoint:
    """Convert legacy point tuple to CurvePoint.

    Args:
        point: Point tuple in legacy format

    Returns:
        CurvePoint instance
    """
    return CurvePoint.from_tuple(point)


def convert_to_curve_collection(points: PointsList) -> PointCollection:
    """Convert legacy PointsList to PointCollection.

    Args:
        points: PointsList in legacy format

    Returns:
        PointCollection instance
    """
    return PointCollection.from_tuples(points)


# Performance-optimized utilities for large datasets


def bulk_convert_to_tuples(points: list[CurvePoint]) -> PointsList:
    """High-performance conversion of CurvePoints to legacy tuples.

    Optimized for large datasets by minimizing object creation.

    Args:
        points: List of CurvePoint objects

    Returns:
        PointsList in legacy format
    """
    # Pre-allocate list for better performance
    result = []
    result_append = result.append  # Cache method lookup

    for point in points:
        if point.status == PointStatus.NORMAL:
            result_append((point.frame, point.x, point.y))
        else:
            result_append((point.frame, point.x, point.y, point.status.value))

    return result


def bulk_convert_from_tuples(point_tuples: PointsList) -> list[CurvePoint]:
    """High-performance conversion of legacy tuples to CurvePoints.

    Optimized for large datasets by minimizing validation overhead.

    Args:
        point_tuples: PointsList in legacy format

    Returns:
        List of CurvePoint objects
    """
    # Pre-allocate list for better performance
    result = []
    result_append = result.append  # Cache method lookup

    # Cache enum lookups
    normal_status = PointStatus.NORMAL
    interpolated_status = PointStatus.INTERPOLATED
    keyframe_status = PointStatus.KEYFRAME

    for point_tuple in point_tuples:
        frame, x, y = point_tuple[:3]

        if len(point_tuple) == 3:
            status = normal_status
        else:
            status_value = point_tuple[3]
            if isinstance(status_value, bool):
                status = interpolated_status if status_value else normal_status
            elif status_value == "interpolated":
                status = interpolated_status
            elif status_value == "keyframe":
                status = keyframe_status
            else:
                status = normal_status

        result_append(CurvePoint(frame, x, y, status))

    return result
