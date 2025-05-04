# services/curve_utils.py
"""
Utility functions for curve operations.
These are shared between curve_view_plumbing.py and curve_service.py.
"""

from typing import Any, Tuple, overload, Union

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

    This function transforms from tracking data coordinates to widget display coordinates,
    taking into account scaling, offsets, and any coordinate system transformations.

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
    # Get any manual offsets applied through panning
    manual_x_offset = getattr(curve_view, 'x_offset', 0)
    manual_y_offset = getattr(curve_view, 'y_offset', 0)

    # Use the image content centered base position
    # This ensures content stays properly centered in the widget
    base_x = offset_x + manual_x_offset
    base_y = offset_y + manual_y_offset

    if hasattr(curve_view, 'background_image') and curve_view.background_image and getattr(curve_view, 'scale_to_image', False):
        # When scaling to image, we need to first convert from curve coordinates to image coordinates
        img_width = getattr(curve_view, 'image_width', 1920)
        img_height = getattr(curve_view, 'image_height', 1080)

        # Convert tracking coordinates to image space
        img_scale_x = display_width / max(img_width, 1)
        img_scale_y = display_height / max(img_height, 1)

        # Apply image-to-tracking coordinate transformation
        # This maps curve points to positions on the background image
        img_x = x * img_scale_x
        img_y = y * img_scale_y

        # Apply Y-flip if enabled
        if getattr(curve_view, 'flip_y_axis', False):
            img_y = display_height - img_y

        # Now scale to widget space and apply centering offset
        tx = base_x + img_x * scale
        ty = base_y + img_y * scale

    else:
        # Direct scaling from tracking coordinates to widget space
        # No image-based transformation, but we still need to handle Y-flip
        if getattr(curve_view, 'flip_y_axis', False):
            # For Y-flip, we need the original data height
            img_height = getattr(curve_view, 'image_height', 1080)
            tx = base_x + (x * scale)
            ty = base_y + (img_height - y) * scale
        else:
            tx = base_x + (x * scale)
            ty = base_y + (y * scale)

    return tx, ty
