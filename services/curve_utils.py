# services/curve_utils.py
"""
Utility functions for curve operations.
These are shared between curve_view_plumbing.py and curve_service.py.
"""

from typing import Tuple, overload, Union

Point3 = Tuple[int, float, float]
Point4 = Tuple[int, float, float, Union[str, bool]]
PointType = Union[Point3, Point4]
StatusType = Union[str, bool]

@overload
def normalize_point(point: Point3) -> Point4: ...
@overload
def normalize_point(point: Point4) -> Point4: ...
def normalize_point(point: PointType) -> Point4:
    """Ensure point tuple is (frame, x, y, status).
    
    Args:
        point: A point tuple in either (frame, x, y) or (frame, x, y, status) format
        
    Returns:
        A normalized tuple in (frame, x, y, status) format where status is either str or bool
    """
    if len(point) == 3:
        frame, x, y = point
        return frame, x, y, 'normal'
    elif len(point) >= 4:
        return point[0], point[1], point[2], point[3]
    else:
        raise ValueError(f"Invalid point format: {point}")


def set_point_status(point: PointType, status: StatusType) -> Union[Point3, Point4]:
    """Return a new point tuple with the given status.
    
    Args:
        point: The point to update
        status: The new status (str or bool)
        
    Returns:
        A new point tuple with the updated status
    """
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
