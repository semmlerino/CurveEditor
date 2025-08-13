#!/usr/bin/env python
"""
Mathematical utilities for geometric calculations.

This module provides common mathematical operations used throughout
the application, including rotations, interpolations, and distance calculations.
"""

import math


class GeometryUtils:
    """Common geometric calculations."""

    @staticmethod
    def rotate_point(
        x: float,
        y: float,
        angle_degrees: float,
        center_x: float = 0.0,
        center_y: float = 0.0,
    ) -> tuple[float, float]:
        """Rotate a point around a center.

        Args:
            x: Point X coordinate
            y: Point Y coordinate
            angle_degrees: Rotation angle in degrees
            center_x: Center X coordinate
            center_y: Center Y coordinate

        Returns:
            Tuple of (new_x, new_y) after rotation
        """
        angle_rad = math.radians(angle_degrees)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Translate to origin
        dx = x - center_x
        dy = y - center_y

        # Rotate
        new_x = center_x + dx * cos_a - dy * sin_a
        new_y = center_y + dx * sin_a + dy * cos_a

        return new_x, new_y

    @staticmethod
    def lerp(start: float, end: float, t: float) -> float:
        """Linear interpolation between two values.

        Args:
            start: Starting value
            end: Ending value
            t: Interpolation factor (0.0 to 1.0)

        Returns:
            Interpolated value
        """
        return start + t * (end - start)

    @staticmethod
    def lerp_point(
        p1: tuple[float, float],
        p2: tuple[float, float],
        t: float,
    ) -> tuple[float, float]:
        """Linear interpolation between two points.

        Args:
            p1: Starting point (x, y)
            p2: Ending point (x, y)
            t: Interpolation factor (0.0 to 1.0)

        Returns:
            Interpolated point (x, y)
        """
        return (GeometryUtils.lerp(p1[0], p2[0], t), GeometryUtils.lerp(p1[1], p2[1], t))

    @staticmethod
    def distance(x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate Euclidean distance between two points.

        Args:
            x1: First point X coordinate
            y1: First point Y coordinate
            x2: Second point X coordinate
            y2: Second point Y coordinate

        Returns:
            Distance between the points
        """
        dx = x2 - x1
        dy = y2 - y1
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def distance_squared(x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate squared distance between two points (avoids sqrt).

        Args:
            x1: First point X coordinate
            y1: First point Y coordinate
            x2: Second point X coordinate
            y2: Second point Y coordinate

        Returns:
            Squared distance between the points
        """
        dx = x2 - x1
        dy = y2 - y1
        return dx * dx + dy * dy

    @staticmethod
    def point_in_rect(
        x: float,
        y: float,
        rect_x: float,
        rect_y: float,
        rect_w: float,
        rect_h: float,
    ) -> bool:
        """Check if point is inside rectangle.

        Args:
            x: Point X coordinate
            y: Point Y coordinate
            rect_x: Rectangle X coordinate (top-left)
            rect_y: Rectangle Y coordinate (top-left)
            rect_w: Rectangle width
            rect_h: Rectangle height

        Returns:
            True if point is inside rectangle
        """
        return rect_x <= x <= rect_x + rect_w and rect_y <= y <= rect_y + rect_h

    @staticmethod
    def point_in_circle(
        x: float,
        y: float,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> bool:
        """Check if point is inside circle.

        Args:
            x: Point X coordinate
            y: Point Y coordinate
            center_x: Circle center X
            center_y: Circle center Y
            radius: Circle radius

        Returns:
            True if point is inside circle
        """
        dist_sq = GeometryUtils.distance_squared(x, y, center_x, center_y)
        return dist_sq <= radius * radius

    @staticmethod
    def angle_between(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> float:
        """Calculate angle between two points in degrees.

        Args:
            x1: First point X
            y1: First point Y
            x2: Second point X
            y2: Second point Y

        Returns:
            Angle in degrees (0-360)
        """
        angle_rad = math.atan2(y2 - y1, x2 - x1)
        angle_deg = math.degrees(angle_rad)
        # Normalize to 0-360
        return angle_deg % 360

    @staticmethod
    def centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
        """Calculate centroid of a set of points.

        Args:
            points: List of (x, y) tuples

        Returns:
            Centroid (x, y)
        """
        if not points:
            return (0.0, 0.0)

        sum_x = sum(p[0] for p in points)
        sum_y = sum(p[1] for p in points)
        count = len(points)

        return (sum_x / count, sum_y / count)

    @staticmethod
    def bounding_box(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
        """Calculate bounding box of a set of points.

        Args:
            points: List of (x, y) tuples

        Returns:
            Tuple of (min_x, min_y, max_x, max_y)
        """
        if not points:
            return (0.0, 0.0, 0.0, 0.0)

        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]

        return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))


class InterpolationUtils:
    """Utilities for various interpolation methods."""

    @staticmethod
    def linear(
        frame: int,
        frame1: int,
        frame2: int,
        value1: float,
        value2: float,
    ) -> float:
        """Linear interpolation between two values at specific frames.

        Args:
            frame: Target frame
            frame1: First frame
            frame2: Second frame
            value1: Value at first frame
            value2: Value at second frame

        Returns:
            Interpolated value at target frame
        """
        if frame2 == frame1:
            return value1

        t = (frame - frame1) / (frame2 - frame1)
        return value1 + t * (value2 - value1)

    @staticmethod
    def linear_point(
        frame: int,
        frame1: int,
        frame2: int,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> tuple[float, float]:
        """Linear interpolation between two points at specific frames.

        Args:
            frame: Target frame
            frame1: First frame
            frame2: Second frame
            x1, y1: First point coordinates
            x2, y2: Second point coordinates

        Returns:
            Interpolated point (x, y)
        """
        if frame2 == frame1:
            return (x1, y1)

        t = (frame - frame1) / (frame2 - frame1)
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)

        return (x, y)

    @staticmethod
    def cosine(start: float, end: float, t: float) -> float:
        """Cosine interpolation for smoother transitions.

        Args:
            start: Starting value
            end: Ending value
            t: Interpolation factor (0.0 to 1.0)

        Returns:
            Interpolated value
        """
        t2 = (1 - math.cos(t * math.pi)) / 2
        return start * (1 - t2) + end * t2

    @staticmethod
    def cubic(
        p0: float,
        p1: float,
        p2: float,
        p3: float,
        t: float,
    ) -> float:
        """Cubic interpolation between four points.

        Args:
            p0: Point before p1
            p1: Starting point
            p2: Ending point
            p3: Point after p2
            t: Interpolation factor (0.0 to 1.0)

        Returns:
            Interpolated value
        """
        t2 = t * t
        a0 = p3 - p2 - p0 + p1
        a1 = p0 - p1 - a0
        a2 = p2 - p0
        a3 = p1

        return a0 * t * t2 + a1 * t2 + a2 * t + a3


class ValidationUtils:
    """Common validation utilities."""

    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        """Clamp value to range.

        Args:
            value: Value to clamp
            min_val: Minimum value
            max_val: Maximum value

        Returns:
            Clamped value
        """
        return max(min_val, min(max_val, value))

    @staticmethod
    def is_in_range(
        value: float,
        min_val: float,
        max_val: float,
        inclusive: bool = True,
    ) -> bool:
        """Check if value is in range.

        Args:
            value: Value to check
            min_val: Minimum value
            max_val: Maximum value
            inclusive: Whether to include boundaries

        Returns:
            True if value is in range
        """
        if inclusive:
            return min_val <= value <= max_val
        return min_val < value < max_val

    @staticmethod
    def validate_index(
        index: int,
        collection_size: int,
        allow_negative: bool = False,
    ) -> bool:
        """Validate list index.

        Args:
            index: Index to validate
            collection_size: Size of collection
            allow_negative: Whether to allow negative indices

        Returns:
            True if index is valid
        """
        if allow_negative:
            return -collection_size <= index < collection_size
        return 0 <= index < collection_size

    @staticmethod
    def validate_point(
        x: float,
        y: float,
        x_range: tuple[float, float] | None = None,
        y_range: tuple[float, float] | None = None,
    ) -> bool:
        """Validate point coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            x_range: Optional (min, max) for X
            y_range: Optional (min, max) for Y

        Returns:
            True if point is valid
        """
        if x_range and not ValidationUtils.is_in_range(x, x_range[0], x_range[1]):
            return False
        if y_range and not ValidationUtils.is_in_range(y, y_range[0], y_range[1]):
            return False
        return True

    @staticmethod
    def normalize(value: float, min_val: float, max_val: float) -> float:
        """Normalize value to 0-1 range.

        Args:
            value: Value to normalize
            min_val: Minimum value in range
            max_val: Maximum value in range

        Returns:
            Normalized value (0-1)
        """
        if max_val == min_val:
            return 0.0
        return (value - min_val) / (max_val - min_val)

    @staticmethod
    def denormalize(normalized: float, min_val: float, max_val: float) -> float:
        """Denormalize value from 0-1 range.

        Args:
            normalized: Normalized value (0-1)
            min_val: Minimum value in target range
            max_val: Maximum value in target range

        Returns:
            Denormalized value
        """
        return min_val + normalized * (max_val - min_val)


# Convenience functions
def rotate_point(x: float, y: float, angle: float, cx: float = 0, cy: float = 0) -> tuple[float, float]:
    """Convenience function for point rotation."""
    return GeometryUtils.rotate_point(x, y, angle, cx, cy)


def lerp(start: float, end: float, t: float) -> float:
    """Convenience function for linear interpolation."""
    return GeometryUtils.lerp(start, end, t)


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Convenience function for distance calculation."""
    return GeometryUtils.distance(x1, y1, x2, y2)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Convenience function for value clamping."""
    return ValidationUtils.clamp(value, min_val, max_val)
