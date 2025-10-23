"""Simple validation utilities."""

import math
from typing import TypeGuard


def is_valid_coordinate(x: object, y: object) -> TypeGuard[tuple[float, float]]:
    """Runtime type guard for coordinates."""
    if not isinstance(x, int | float) or not isinstance(y, int | float):
        return False
    return math.isfinite(x) and math.isfinite(y)


def ensure_valid_scale(scale: float, min_val: float = 1e-10) -> float:
    """Ensure scale is valid, return safe default if not."""
    if math.isfinite(scale) and scale > 0:
        return max(scale, min_val)
    return 1.0


def ensure_positive_dimensions(width: float, height: float) -> tuple[float, float]:
    """Ensure dimensions are positive."""
    safe_width = abs(width) if width != 0 else 1.0
    safe_height = abs(height) if height != 0 else 1.0
    return safe_width, safe_height


def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range."""
    return max(min_val, min(max_val, value))


def sanitize_point_data(points: list[object]) -> list[object]:
    """Ensure all points have valid coordinates."""
    valid_points: list[object] = []
    for point in points:
        # Use getattr with sentinel to avoid type narrowing issues with hasattr
        x = getattr(point, "x", None)
        y = getattr(point, "y", None)
        if x is not None and y is not None:
            if is_valid_coordinate(x, y):
                valid_points.append(point)
    return valid_points


def validate_finite(value: float, _name: str = "", default: float = 0.0) -> float:
    """Validate value is finite, return default if not."""
    if not math.isfinite(value):
        return default
    return value


def validate_point(x: float, y: float) -> tuple[float, float]:
    """Validate point coordinates are finite."""
    safe_x = validate_finite(x, "x", 0.0)
    safe_y = validate_finite(y, "y", 0.0)
    return safe_x, safe_y


def validate_file_path(path: str) -> bool:
    """Check if file path is valid."""
    return bool(path)
