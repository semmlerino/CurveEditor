"""Frame manipulation utilities.

Provides utilities for frame clamping, validation, and range extraction
to eliminate code duplication across the codebase.
"""

from core.type_aliases import CurveDataInput


def clamp_frame(frame: int, min_frame: int, max_frame: int) -> int:
    """Clamp frame value to valid range [min_frame, max_frame].

    Args:
        frame: Frame number to clamp
        min_frame: Minimum valid frame (inclusive)
        max_frame: Maximum valid frame (inclusive)

    Returns:
        Clamped frame value

    Examples:
        >>> clamp_frame(5, 1, 10)
        5
        >>> clamp_frame(0, 1, 10)
        1
        >>> clamp_frame(15, 1, 10)
        10
    """
    return max(min_frame, min(max_frame, frame))


def is_frame_in_range(frame: int, min_frame: int, max_frame: int) -> bool:
    """Check if frame is within valid range.

    Args:
        frame: Frame number to check
        min_frame: Minimum valid frame (inclusive)
        max_frame: Maximum valid frame (inclusive)

    Returns:
        True if frame is in range

    Examples:
        >>> is_frame_in_range(5, 1, 10)
        True
        >>> is_frame_in_range(0, 1, 10)
        False
    """
    return min_frame <= frame <= max_frame


def get_frame_range_from_curve(curve_data: CurveDataInput) -> tuple[int, int] | None:
    """Extract min/max frame numbers from curve data.

    Args:
        curve_data: List of curve points (frame, x, y, ...) tuples

    Returns:
        (min_frame, max_frame) or None if no valid frames found

    Examples:
        >>> data = [(1, 10.0, 20.0), (5, 15.0, 25.0), (3, 12.0, 22.0)]
        >>> get_frame_range_from_curve(data)
        (1, 5)
        >>> get_frame_range_from_curve([])
        None
    """
    if not curve_data:
        return None

    frames = [int(point[0]) for point in curve_data if len(point) >= 3]
    if not frames:
        return None

    return (min(frames), max(frames))


def get_frame_range_with_limits(
    curve_data: CurveDataInput,
    max_range: int = 200,
) -> tuple[int, int] | None:
    """Extract frame range with optional limiting for performance.

    Args:
        curve_data: List of curve points
        max_range: Maximum frame range allowed (for UI performance)

    Returns:
        (min_frame, limited_max_frame) or None

    Examples:
        >>> data = [(1, 0, 0), (1000, 0, 0)]  # Very wide range
        >>> get_frame_range_with_limits(data, max_range=200)
        (1, 200)  # Limited to 200 frames
    """
    range_result = get_frame_range_from_curve(curve_data)
    if range_result is None:
        return None

    min_frame, max_frame = range_result

    # Limit range for performance
    if max_frame - min_frame + 1 > max_range:
        max_frame = min_frame + max_range - 1

    return (min_frame, max_frame)
