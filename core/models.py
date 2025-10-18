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
from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple, TypeGuard, overload, override

# Type aliases for backward compatibility and clarity
FrameNumber = int
Coordinate = float
PointIndex = int

# Legacy type definitions for migration
LegacyPointTuple = tuple[int, float, float] | tuple[int, float, float, str | bool]
PointsList = list[LegacyPointTuple]


class FrameStatus(NamedTuple):
    """Status information for a single frame in timeline.

    Attributes:
        keyframe_count: Number of keyframe points
        interpolated_count: Number of interpolated points
        tracked_count: Number of tracked points
        endframe_count: Number of endframe points
        normal_count: Number of normal points
        is_startframe: True if this is the first frame with data
        is_inactive: True if frame has no active tracking
        has_selected: True if any points are selected in this frame
    """

    keyframe_count: int
    interpolated_count: int
    tracked_count: int
    endframe_count: int
    normal_count: int
    is_startframe: bool
    is_inactive: bool
    has_selected: bool

    @property
    def total_points(self) -> int:
        """Total number of points in this frame."""
        return (
            self.keyframe_count + self.interpolated_count + self.tracked_count + self.endframe_count + self.normal_count
        )

    @property
    def is_empty(self) -> bool:
        """True if frame has no points."""
        return self.total_points == 0


class PointStatus(Enum):
    """Enumeration of point status values with backward compatibility.

    Provides clear, type-safe status values while maintaining compatibility
    with existing string-based status system.

    Status types:
    - NORMAL: Default state for a point
    - KEYFRAME: User-defined position (manual keyframe)
    - INTERPOLATED: Calculated between keyframes
    - TRACKED: From automatic tracking (e.g., computer vision)
    - ENDFRAME: Marks the end of a curve segment, creating a gap
    """

    NORMAL = "normal"
    INTERPOLATED = "interpolated"
    KEYFRAME = "keyframe"
    TRACKED = "tracked"
    ENDFRAME = "endframe"

    @classmethod
    def from_legacy(cls, value: str | bool | int | None) -> PointStatus:
        """Convert legacy status values to enum.

        Args:
            value: Legacy status (string, bool, int, or None)

        Returns:
            PointStatus enum value

        Examples:
            >>> PointStatus.from_legacy(True)
            PointStatus.INTERPOLATED
            >>> PointStatus.from_legacy("keyframe")
            PointStatus.KEYFRAME
            >>> PointStatus.from_legacy("tracked")
            PointStatus.TRACKED
            >>> PointStatus.from_legacy(None)
            PointStatus.NORMAL
        """
        if value is None:
            return cls.NORMAL
        elif isinstance(value, bool):
            return cls.INTERPOLATED if value else cls.NORMAL
        elif isinstance(value, int):
            # Convert int to corresponding status (0=NORMAL, 1=INTERPOLATED, 2=KEYFRAME, 3=TRACKED, 4=ENDFRAME)
            if value == 1:
                return cls.INTERPOLATED
            elif value == 2:
                return cls.KEYFRAME
            elif value == 3:
                return cls.TRACKED
            elif value == 4:
                return cls.ENDFRAME
            else:
                return cls.NORMAL
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
class PointSearchResult:
    """
    Result of searching for a point in curve view.

    Replaces bare int return type with structured result that includes
    curve context for multi-curve operations.

    Attributes:
        index: Point index in curve, -1 if not found
        curve_name: Curve containing point, None if not found
        distance: Distance to point (for debugging/logging)

    Examples:
        >>> result = service.find_point_at(view, 100, 200)
        >>> if result.found:
        ...     print(f"Point {result.index} in {result.curve_name}")
    """

    index: int
    curve_name: str | None
    distance: float = 0.0

    @property
    def found(self) -> bool:
        """True if point was found."""
        return self.index >= 0

    # Comparison operators for backward compatibility with int comparisons
    @override
    def __eq__(self, other: object) -> bool:
        """Allow comparison with int (compares index)."""
        if isinstance(other, int):
            return self.index == other
        if isinstance(other, PointSearchResult):
            return self.index == other.index and self.curve_name == other.curve_name
        return False

    def __lt__(self, other: int) -> bool:
        """Allow comparison with int (compares index)."""
        return self.index < other

    def __le__(self, other: int) -> bool:
        """Allow comparison with int (compares index)."""
        return self.index <= other

    def __gt__(self, other: int) -> bool:
        """Allow comparison with int (compares index)."""
        return self.index > other

    def __ge__(self, other: int) -> bool:
        """Allow comparison with int (compares index)."""
        return self.index >= other

    def __bool__(self) -> bool:
        """Allow truthiness check (True if found)."""
        return self.found


@dataclass(frozen=True)
class CurveSelection:
    """
    Multi-curve selection state.

    Mirrors ApplicationState's _selection structure for type-safe access.
    Immutable for safety - create new instance to modify.

    Attributes:
        selections: Dict mapping curve_name -> selected indices
        active_curve: Currently active curve name

    Examples:
        >>> selection = CurveSelection({"curve1": {0, 1, 2}}, "curve1")
        >>> selection.total_selected
        3
        >>> selection.active_selection
        {0, 1, 2}
    """

    selections: dict[str, set[int]] = field(default_factory=dict)
    active_curve: str | None = None

    @property
    def total_selected(self) -> int:
        """Total number of selected points across all curves."""
        return sum(len(s) for s in self.selections.values())

    @property
    def active_selection(self) -> set[int]:
        """Get selection for active curve only (backward compat)."""
        if self.active_curve is None:
            return set()
        return self.selections.get(self.active_curve, set()).copy()

    def get_selected_curves(self) -> list[str]:
        """Get list of curves that have selections."""
        return [name for name, sel in self.selections.items() if sel]

    def with_curve_selection(self, curve_name: str, indices: set[int]) -> CurveSelection:
        """Create new selection with updated curve (deep copy for safety)."""
        # Deep copy all sets to prevent aliasing (frozen=True only prevents field reassignment)
        new_selections = {k: v.copy() for k, v in self.selections.items()}
        new_selections[curve_name] = indices.copy()
        return CurveSelection(new_selections, self.active_curve)


class TrackingDirection(Enum):
    """Tracking direction metadata for 3DEqualizer compatibility.

    Indicates how a trajectory was originally tracked. This is metadata
    only and does not affect tracking functionality within the application.
    Used for proper export back to 3DEqualizer.

    Direction types:
    - TRACKING_FW: Forward tracking from reference frame
    - TRACKING_BW: Backward tracking from reference frame
    - TRACKING_FW_BW: Bidirectional tracking (forward and backward)
    """

    TRACKING_FW = "forward"
    TRACKING_BW = "backward"
    TRACKING_FW_BW = "bidirectional"

    @property
    def abbreviation(self) -> str:
        """Get abbreviated display text for UI."""
        if self == TrackingDirection.TRACKING_FW:
            return "FW"
        elif self == TrackingDirection.TRACKING_BW:
            return "BW"
        else:  # TRACKING_FW_BW
            return "FW+BW"

    @property
    def display_name(self) -> str:
        """Get full display name for tooltips."""
        if self == TrackingDirection.TRACKING_FW:
            return "Forward"
        elif self == TrackingDirection.TRACKING_BW:
            return "Backward"
        else:  # TRACKING_FW_BW
            return "Bidirectional"

    @classmethod
    def from_abbreviation(cls, abbrev: str) -> TrackingDirection:
        """Create enum from abbreviation string."""
        abbrev_upper = abbrev.upper()
        if abbrev_upper == "FW":
            return cls.TRACKING_FW
        elif abbrev_upper == "BW":
            return cls.TRACKING_BW
        elif abbrev_upper in ("FW+BW", "FWBW", "FB"):
            return cls.TRACKING_FW_BW
        else:
            return cls.TRACKING_FW_BW  # Default


@dataclass(frozen=True)
class CurvePoint:
    """Immutable representation of a single curve point.

    Provides a clean, type-safe interface for curve points with validation
    and utility methods. All data is immutable to prevent accidental changes.

    Attributes:
        frame: Frame number (must be integer)
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
        # Runtime validation for critical type safety
        # These checks provide defensive programming despite type hints
        if not isinstance(self.frame, int):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Frame must be int")

        # Validate coordinate types (must be numeric)
        if not isinstance(self.x, int | float):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("X coordinate must be numeric")
        if not isinstance(self.y, int | float):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Y coordinate must be numeric")

        # Validate status type
        if not isinstance(self.status, PointStatus):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Status must be PointStatus enum")

    @property
    def is_interpolated(self) -> bool:
        """True if this point is interpolated."""
        return self.status == PointStatus.INTERPOLATED

    @property
    def is_keyframe(self) -> bool:
        """True if this point is a keyframe (user-defined or tracked position)."""
        return self.status in (PointStatus.KEYFRAME, PointStatus.NORMAL, PointStatus.TRACKED)

    @property
    def is_endframe(self) -> bool:
        """True if this point marks the end of a curve segment."""
        return self.status == PointStatus.ENDFRAME

    @property
    def coordinates(self) -> tuple[Coordinate, Coordinate]:
        """Get (x, y) coordinates as tuple."""
        return (self.x, self.y)

    def is_startframe(self, prev_point: CurvePoint | None = None, all_points: list[CurvePoint] | None = None) -> bool:
        """Check if this point is a startframe (first keyframe after a gap).

        A startframe is a keyframe that either:
        - Is the first point in the curve (KEYFRAME or TRACKED, no previous point)
        - Is a KEYFRAME that follows an ENDFRAME point (3DEqualizer behavior)

        In 3DEqualizer behavior, tracked points after endframes stay in gaps,
        and only the first keyframe after the gap becomes the startframe.

        Args:
            prev_point: The immediate previous point in the curve (if any)
            all_points: All points in the curve (used for gap detection)

        Returns:
            True if this is a startframe
        """
        # Must be a keyframe-type point to be a startframe
        if self.status not in (PointStatus.KEYFRAME, PointStatus.TRACKED):
            return False

        # First point in curve can be startframe (KEYFRAME or TRACKED)
        if prev_point is None:
            return True

        # For 3DEqualizer gap behavior: check if this keyframe is the first after an endframe
        if self.status == PointStatus.KEYFRAME and all_points:
            # Find the last endframe before this point
            last_endframe = None
            for point in all_points:
                if point.frame < self.frame and point.is_endframe:
                    if last_endframe is None or point.frame > last_endframe.frame:
                        last_endframe = point

            # If there's an endframe before this keyframe, check if this is the first keyframe after it
            if last_endframe:
                # Check if there are any keyframes between the endframe and this point
                for point in all_points:
                    if last_endframe.frame < point.frame < self.frame and point.status == PointStatus.KEYFRAME:
                        return False  # Not the first keyframe after the gap
                return True  # First keyframe after the endframe gap

        # Immediate previous point logic (original behavior)
        if prev_point and prev_point.is_endframe:
            return self.status == PointStatus.KEYFRAME

        return False

    def get_contextual_status_label(
        self, prev_point: CurvePoint | None = None, all_points: list[CurvePoint] | None = None
    ) -> str:
        """Get the display label for this point's status, considering context.

        Args:
            prev_point: The previous point in the curve (if any)
            all_points: All points in the curve (used for gap detection)

        Returns:
            Status label string for display (e.g., "startframe", "keyframe", "endframe")
        """
        if self.is_startframe(prev_point, all_points):
            return "startframe"
        return self.status.value

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
    def from_tuple(
        cls, point_tuple: tuple[int, float, float] | tuple[int, float, float, str | bool] | tuple[int, ...]
    ) -> CurvePoint:
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
        if len(point_tuple) < 3:
            raise ValueError("Point tuple must have 3 or 4 elements")
        elif len(point_tuple) == 3:
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

        # Validate all points are CurvePoint instances
        for i, point in enumerate(self.points):
            if not isinstance(point, CurvePoint):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise TypeError(f"Point {i} must be CurvePoint")

    # Collection interface

    def __len__(self) -> int:
        """Get number of points."""
        return len(self.points)

    def __iter__(self) -> Iterator[CurvePoint]:
        """Iterate over points."""
        return iter(self.points)

    @overload
    def __getitem__(self, index: int) -> CurvePoint: ...

    @overload
    def __getitem__(self, index: slice) -> PointCollection: ...

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
        new_points: list[CurvePoint] = []
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
        new_points: list[CurvePoint] = []
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


def is_point_tuple(obj: object) -> TypeGuard[LegacyPointTuple]:
    """Type guard for point tuple format.

    Args:
        obj: Object to check

    Returns:
        True if obj is a valid point tuple
    """
    if not isinstance(obj, tuple):
        return False

    # Use len() directly on the known tuple
    obj_len = len(obj)  # pyright: ignore[reportUnknownArgumentType]
    if obj_len < 3 or obj_len > 4:
        return False

    # Check frame (int), x (float), y (float)
    if not isinstance(obj[0], int):
        return False
    if not isinstance(obj[1], int | float):
        return False
    if not isinstance(obj[2], int | float):
        return False

    # Check status if present (we know obj has 4 elements here)
    if obj_len == 4 and not isinstance(obj[3], str | bool):
        return False

    return True


def is_points_list(obj: object) -> TypeGuard[PointsList]:
    """Type guard for PointsList format.

    Args:
        obj: Object to check

    Returns:
        True if obj is a valid PointsList
    """
    if not isinstance(obj, list):
        return False

    # Type check each item individually to help type inference
    for item in obj:  # pyright: ignore[reportUnknownVariableType]
        if not is_point_tuple(item):  # pyright: ignore[reportUnknownArgumentType]
            return False
    return True


# Utility functions for common operations


def normalize_legacy_point(
    point: tuple[int, float, float] | tuple[int, float, float, str | bool] | tuple[int, ...],
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
    result: PointsList = []
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
    result: list[CurvePoint] = []
    result_append = result.append  # Cache method lookup

    # Cache enum lookups
    normal_status = PointStatus.NORMAL
    interpolated_status = PointStatus.INTERPOLATED
    keyframe_status = PointStatus.KEYFRAME
    tracked_status = PointStatus.TRACKED
    endframe_status = PointStatus.ENDFRAME

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
            elif status_value == "tracked":
                status = tracked_status
            elif status_value == "endframe":
                status = endframe_status
            else:
                status = normal_status

        result_append(CurvePoint(frame, x, y, status))

    return result
