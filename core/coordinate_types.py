#!/usr/bin/env python
"""
Coordinate type safety for CurveEditor.

This module provides distinct coordinate types to prevent mixing incompatible
coordinate spaces at compile time. This addresses the issue identified by the
agents where coordinate transformation bugs can occur due to accidentally
mixing data coordinates, screen coordinates, and image coordinates.
"""

from typing import TYPE_CHECKING, NewType

if TYPE_CHECKING:
    from services.transform_service import Transform

# Distinct coordinate types to prevent mixing coordinate spaces
# These types are compile-time only and have no runtime overhead

# Data coordinates - the original coordinate space of tracking data
# For 3DEqualizer: image space with Y=0 at bottom
# For pixel tracking: screen space with Y=0 at top
DataX = NewType("DataX", float)
DataY = NewType("DataY", float)
DataPoint = tuple[DataX, DataY]

# Screen coordinates - Qt widget coordinate space with Y=0 at top
# These are the final coordinates for rendering in the widget
ScreenX = NewType("ScreenX", float)
ScreenY = NewType("ScreenY", float)
ScreenPoint = tuple[ScreenX, ScreenY]

# Image coordinates - background image coordinate space
# Usually with Y=0 at top, width/height in pixels
ImageX = NewType("ImageX", float)
ImageY = NewType("ImageY", float)
ImagePoint = tuple[ImageX, ImageY]


class CoordinateConverter:
    """
    Type-safe coordinate conversion utilities.

    Provides methods to safely convert between different coordinate spaces
    while maintaining type safety and preventing accidental coordinate mixing.
    """

    @staticmethod
    def data_to_screen(point: DataPoint, transform: "Transform") -> ScreenPoint:
        """
        Convert data coordinates to screen coordinates using a transform.

        Args:
            point: Data coordinate point (DataX, DataY)
            transform: Transform instance with data_to_screen method

        Returns:
            Screen coordinate point (ScreenX, ScreenY)
        """
        data_x, data_y = point
        screen_x, screen_y = transform.data_to_screen(float(data_x), float(data_y))
        return (ScreenX(screen_x), ScreenY(screen_y))

    @staticmethod
    def screen_to_data(point: ScreenPoint, transform: "Transform") -> DataPoint:
        """
        Convert screen coordinates to data coordinates using a transform.

        Args:
            point: Screen coordinate point (ScreenX, ScreenY)
            transform: Transform instance with screen_to_data method

        Returns:
            Data coordinate point (DataX, DataY)
        """
        screen_x, screen_y = point
        data_x, data_y = transform.screen_to_data(float(screen_x), float(screen_y))
        return (DataX(data_x), DataY(data_y))

    @staticmethod
    def create_data_point(x: float | int, y: float | int) -> DataPoint:
        """
        Create a type-safe data coordinate point.

        Args:
            x: X coordinate value
            y: Y coordinate value

        Returns:
            Type-safe data coordinate point
        """
        return (DataX(float(x)), DataY(float(y)))

    @staticmethod
    def create_screen_point(x: float | int, y: float | int) -> ScreenPoint:
        """
        Create a type-safe screen coordinate point.

        Args:
            x: X coordinate value
            y: Y coordinate value

        Returns:
            Type-safe screen coordinate point
        """
        return (ScreenX(float(x)), ScreenY(float(y)))

    @staticmethod
    def create_image_point(x: float | int, y: float | int) -> ImagePoint:
        """
        Create a type-safe image coordinate point.

        Args:
            x: X coordinate value
            y: Y coordinate value

        Returns:
            Type-safe image coordinate point
        """
        return (ImageX(float(x)), ImageY(float(y)))

    @staticmethod
    def extract_data_values(point: DataPoint) -> tuple[float, float]:
        """
        Extract raw float values from data coordinate point.

        Args:
            point: Data coordinate point

        Returns:
            Tuple of (x, y) as plain floats
        """
        data_x, data_y = point
        return (float(data_x), float(data_y))

    @staticmethod
    def extract_screen_values(point: ScreenPoint) -> tuple[float, float]:
        """
        Extract raw float values from screen coordinate point.

        Args:
            point: Screen coordinate point

        Returns:
            Tuple of (x, y) as plain floats
        """
        screen_x, screen_y = point
        return (float(screen_x), float(screen_y))

    @staticmethod
    def extract_image_values(point: ImagePoint) -> tuple[float, float]:
        """
        Extract raw float values from image coordinate point.

        Args:
            point: Image coordinate point

        Returns:
            Tuple of (x, y) as plain floats
        """
        image_x, image_y = point
        return (float(image_x), float(image_y))


# Type aliases for common coordinate collections
DataPointList = list[DataPoint]
ScreenPointList = list[ScreenPoint]
ImagePointList = list[ImagePoint]

# Legacy compatibility - these will be gradually replaced
LegacyCoordinate = float | int
LegacyPoint = tuple[LegacyCoordinate, LegacyCoordinate]
