# services/curve_utils.py
"""
Utility functions for curve operations.
These are shared between curve_view_plumbing.py and curve_service.py.
"""

from typing import Any, Tuple, overload, Union
from services.transformation_service import TransformationService

Point3 = Tuple[int, float, float]
Point4 = Tuple[int, float, float, str]
PointType = Union[Point3, Point4]

@overload
def normalize_point(point: Point3) -> Point4: ...
@overload
def normalize_point(point: Point4) -> Point4: ...
def normalize_point(point: PointType) -> Point4:
    """Ensure point tuple is (frame, x, y, status)."""
    if len(point) == 3:
        frame, x, y = point
        return frame, x, y, 'normal'
    elif len(point) >= 4:
        return point[0], point[1], point[2], point[3]
    else:
        raise ValueError(f"Invalid point format: {point}")


def set_point_status(point: PointType, status: Any) -> Union[Point3, Point4]:
    """Return a new point tuple with the given status."""
    frame, x, y, _ = normalize_point(point)
    if status == 'normal':
        return frame, x, y
    return frame, x, y, status


def update_point_coords(point: PointType, x: float, y: float) -> Union[Point3, Point4]:
    """Return a new point tuple with updated coordinates preserving status."""
    frame, _, _, status = normalize_point(point)
    if status == 'normal':
        return frame, x, y
    return frame, x, y, status


# Forward the transform_point_to_widget function to TransformationService for backward compatibility
def transform_point_to_widget(
    curve_view: Any,
    x: float,
    y: float,
    display_width: float,
    display_height: float,
    offset_x: float,
    offset_y: float,
    scale: float
) -> Tuple[float, float]:
    """Transform from track coordinates to widget coordinates.

    This is a compatibility wrapper that forwards to TransformationService.
    New code should use TransformationService directly.

    Args:
        curve_view: The curve view instance
        x: X coordinate in tracking data coordinates
        y: Y coordinate in tracking data coordinates
        display_width: Width of the display content area
        display_height: Height of the display content area
        offset_x: Content centering X offset
        offset_y: Content centering Y offset
        scale: Scale factor to apply

    Returns:
        Tuple[float, float]: The transformed (x, y) coordinates in widget space
    """
    return TransformationService.transform_point_to_widget(
        curve_view, x, y, display_width, display_height, offset_x, offset_y, scale
    )
