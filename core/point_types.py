#!/usr/bin/env python
"""
Type-safe point data handling for CurveEditor.

This module provides comprehensive type safety for point data handling throughout
the codebase. It replaces unsafe tuple unpacking patterns with type-safe alternatives
using TypeGuard functions, overloads, and proper validation.

Key Features:
- TypeGuard functions for runtime type checking
- Overloaded functions for handling both Point3 and Point4 tuples
- Safe point extraction with fallback values
- Comprehensive point validation and normalization
- Full type safety with mypy/basedpyright compatibility

Usage:
    from core.point_types import is_point3, is_point4, safe_extract_point, normalize_point

    # Type-safe point checking
    if is_point3(point):
        frame, x, y = point  # Safe - type checker knows this is Point3

    # Safe extraction with fallbacks
    frame, x, y, status = safe_extract_point(point)

    # Normalized point handling
    normalized = normalize_point(point)
"""

from typing import TypeGuard, overload

# Type aliases for clarity
Point3 = tuple[int, float, float]
Point4 = tuple[int, float, float, str | bool]
PointType = Point3 | Point4
StatusType = str | bool

# Default values for safe extraction
DEFAULT_FRAME = 0
DEFAULT_X = 0.0
DEFAULT_Y = 0.0
DEFAULT_STATUS = "normal"

def is_point3(point: object) -> TypeGuard[Point3]:
    """
    TypeGuard to check if object is a valid Point3 tuple.

    Args:
        point: Object to check

    Returns:
        True if point is a valid (frame, x, y) tuple

    Examples:
        >>> point = (1, 2.0, 3.0)
        >>> if is_point3(point):
        ...     frame, x, y = point  # Type checker knows this is safe
        ...     print(f"Frame {frame} at ({x}, {y})")
    """
    return (
        isinstance(point, tuple)
        and len(point) == 3
        and isinstance(point[0], int)
        and isinstance(point[1], (int, float))
        and isinstance(point[2], (int, float))
    )

def is_point4(point: object) -> TypeGuard[Point4]:
    """
    TypeGuard to check if object is a valid Point4 tuple.

    Args:
        point: Object to check

    Returns:
        True if point is a valid (frame, x, y, status) tuple

    Examples:
        >>> point = (1, 2.0, 3.0, "keyframe")
        >>> if is_point4(point):
        ...     frame, x, y, status = point  # Type checker knows this is safe
        ...     print(f"Frame {frame} at ({x}, {y}) status: {status}")
    """
    return (
        isinstance(point, tuple)
        and len(point) == 4
        and isinstance(point[0], int)
        and isinstance(point[1], (int, float))
        and isinstance(point[2], (int, float))
        and isinstance(point[3], (str, bool))
    )

def is_valid_point(point: object) -> TypeGuard[PointType]:
    """
    TypeGuard to check if object is any valid point tuple.

    Args:
        point: Object to check

    Returns:
        True if point is either Point3 or Point4

    Examples:
        >>> if is_valid_point(some_object):
        ...     # Now we know it's either Point3 or Point4
        ...     frame, x, y, status = safe_extract_point(some_object)
    """
    return is_point3(point) or is_point4(point)

@overload
def safe_extract_point(point: Point3) -> tuple[int, float, float, str]: ...

@overload
def safe_extract_point(point: Point4) -> tuple[int, float, float, str]: ...

@overload
def safe_extract_point(point: object) -> tuple[int, float, float, str]: ...

def safe_extract_point(point: object) -> tuple[int, float, float, str]:
    """
    Safely extract point data with type validation and fallback values.

    This function provides a type-safe way to extract point data that handles
    both Point3 and Point4 tuples, with comprehensive validation and fallback
    values for invalid input.

    Args:
        point: Point tuple to extract data from

    Returns:
        Tuple of (frame, x, y, status) with guaranteed types

    Examples:
        >>> # Safe for any point format
        >>> frame, x, y, status = safe_extract_point((1, 2.0, 3.0))
        >>> # frame=1, x=2.0, y=3.0, status="normal"

        >>> frame, x, y, status = safe_extract_point((1, 2.0, 3.0, "keyframe"))
        >>> # frame=1, x=2.0, y=3.0, status="keyframe"

        >>> # Even handles invalid input safely
        >>> frame, x, y, status = safe_extract_point("invalid")
        >>> # frame=0, x=0.0, y=0.0, status="normal"
    """
    # Handle Point3 case
    if is_point3(point):
        frame, x, y = point
        return frame, float(x), float(y), DEFAULT_STATUS

    # Handle Point4 case
    if is_point4(point):
        frame, x, y, status = point
        # Normalize status to string
        if isinstance(status, bool):
            status_str = "interpolated" if status else "normal"
        else:
            status_str = str(status)
        return frame, float(x), float(y), status_str

    # Fallback for invalid input
    return DEFAULT_FRAME, DEFAULT_X, DEFAULT_Y, DEFAULT_STATUS

@overload
def normalize_point(point: Point3) -> Point4: ...

@overload
def normalize_point(point: Point4) -> Point4: ...

def normalize_point(point: PointType) -> Point4:
    """
    Normalize any point tuple to Point4 format with string status.

    This function ensures consistent Point4 format throughout the codebase
    while preserving all point data and handling status conversion properly.

    Args:
        point: Point tuple in either Point3 or Point4 format

    Returns:
        Point4 tuple with string status

    Raises:
        ValueError: If point format is invalid

    Examples:
        >>> normalize_point((1, 2.0, 3.0))
        (1, 2.0, 3.0, 'normal')

        >>> normalize_point((1, 2.0, 3.0, True))
        (1, 2.0, 3.0, 'interpolated')

        >>> normalize_point((1, 2.0, 3.0, "keyframe"))
        (1, 2.0, 3.0, 'keyframe')
    """
    if is_point3(point):
        frame, x, y = point
        return (frame, x, y, DEFAULT_STATUS)

    if is_point4(point):
        frame, x, y, status = point
        # Normalize status to string
        if isinstance(status, bool):
            status_str = "interpolated" if status else "normal"
        else:
            status_str = str(status)
        return (frame, x, y, status_str)

    # This should never happen with proper TypeGuard usage
    raise ValueError(f"Invalid point format: {point}")

def set_point_status(point: PointType, status: StatusType) -> Point4:
    """
    Return a new point tuple with the specified status.

    Args:
        point: The point to update
        status: The new status (str or bool)

    Returns:
        Point4 tuple with updated status

    Examples:
        >>> set_point_status((1, 2.0, 3.0), "interpolated")
        (1, 2.0, 3.0, 'interpolated')

        >>> set_point_status((1, 2.0, 3.0, "old"), True)
        (1, 2.0, 3.0, 'interpolated')
    """
    frame, x, y, _ = normalize_point(point)

    # Normalize status to string
    if isinstance(status, bool):
        status_str = "interpolated" if status else "normal"
    else:
        status_str = str(status)

    return (frame, x, y, status_str)

def update_point_coords(point: PointType, x: float, y: float) -> Point4:
    """
    Return a new point tuple with updated coordinates, preserving status.

    Args:
        point: The point to update
        x: New x coordinate
        y: New y coordinate

    Returns:
        Point4 tuple with updated coordinates

    Examples:
        >>> update_point_coords((1, 2.0, 3.0), 5.0, 6.0)
        (1, 5.0, 6.0, 'normal')

        >>> update_point_coords((1, 2.0, 3.0, "keyframe"), 5.0, 6.0)
        (1, 5.0, 6.0, 'keyframe')
    """
    frame, _, _, status = normalize_point(point)
    return (frame, x, y, status)

def validate_point_data(points: list[object]) -> list[Point4]:
    """
    Validate and normalize a list of point objects to Point4 format.

    Args:
        points: List of point objects to validate

    Returns:
        List of validated Point4 tuples

    Examples:
        >>> mixed_points = [(1, 2.0, 3.0), (2, 4.0, 5.0, "keyframe"), "invalid"]
        >>> validated = validate_point_data(mixed_points)
        >>> # Returns [(1, 2.0, 3.0, 'normal'), (2, 4.0, 5.0, 'keyframe')]
    """
    validated_points: list[Point4] = []

    for point in points:
        if is_valid_point(point):
            validated_points.append(normalize_point(point))
        # Skip invalid points silently

    return validated_points

def get_point_frame(point: PointType) -> int:
    """
    Safely get the frame number from any point tuple.

    Args:
        point: Point tuple

    Returns:
        Frame number

    Examples:
        >>> get_point_frame((1, 2.0, 3.0))
        1
        >>> get_point_frame((5, 2.0, 3.0, "keyframe"))
        5
    """
    frame, _, _, _ = safe_extract_point(point)
    return frame

def get_point_coords(point: PointType) -> tuple[float, float]:
    """
    Safely get the coordinates from any point tuple.

    Args:
        point: Point tuple

    Returns:
        Tuple of (x, y) coordinates

    Examples:
        >>> get_point_coords((1, 2.0, 3.0))
        (2.0, 3.0)
        >>> get_point_coords((1, 4.0, 5.0, "keyframe"))
        (4.0, 5.0)
    """
    _, x, y, _ = safe_extract_point(point)
    return (x, y)

def get_point_status(point: PointType) -> str:
    """
    Safely get the status from any point tuple.

    Args:
        point: Point tuple

    Returns:
        Status string

    Examples:
        >>> get_point_status((1, 2.0, 3.0))
        'normal'
        >>> get_point_status((1, 2.0, 3.0, "keyframe"))
        'keyframe'
        >>> get_point_status((1, 2.0, 3.0, True))
        'interpolated'
    """
    _, _, _, status = safe_extract_point(point)
    return status

def is_point_interpolated(point: PointType) -> bool:
    """
    Check if a point is marked as interpolated.

    Args:
        point: Point tuple

    Returns:
        True if point is interpolated

    Examples:
        >>> is_point_interpolated((1, 2.0, 3.0))
        False
        >>> is_point_interpolated((1, 2.0, 3.0, "interpolated"))
        True
        >>> is_point_interpolated((1, 2.0, 3.0, True))
        True
    """
    status = get_point_status(point)
    return status == "interpolated"

def create_point3(frame: int, x: float, y: float) -> Point3:
    """
    Create a Point3 tuple with validation.

    Args:
        frame: Frame number
        x: X coordinate
        y: Y coordinate

    Returns:
        Valid Point3 tuple

    Examples:
        >>> create_point3(1, 2.0, 3.0)
        (1, 2.0, 3.0)
    """
    return (int(frame), float(x), float(y))

def create_point4(frame: int, x: float, y: float, status: StatusType = "normal") -> Point4:
    """
    Create a Point4 tuple with validation.

    Args:
        frame: Frame number
        x: X coordinate
        y: Y coordinate
        status: Point status (default: "normal")

    Returns:
        Valid Point4 tuple

    Examples:
        >>> create_point4(1, 2.0, 3.0)
        (1, 2.0, 3.0, 'normal')
        >>> create_point4(1, 2.0, 3.0, "keyframe")
        (1, 2.0, 3.0, 'keyframe')
        >>> create_point4(1, 2.0, 3.0, True)
        (1, 2.0, 3.0, 'interpolated')
    """
    # Normalize status to string
    if isinstance(status, bool):
        status_str = "interpolated" if status else "normal"
    else:
        status_str = str(status)

    return (int(frame), float(x), float(y), status_str)