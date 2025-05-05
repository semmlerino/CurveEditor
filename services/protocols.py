#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Protocols for CurveEditor components.

This module defines structural protocols that enforce interface consistency
across the application. These protocols help ensure type safety while allowing
flexibility in implementation.
"""

from typing import Protocol, Optional, Any, Tuple, List, Dict, Union, TypeVar, cast


class CurveViewProtocol(Protocol):
    """Protocol defining the interface for curve view components."""

    # Common attributes
    x_offset: float
    y_offset: float
    flip_y_axis: bool
    scale_to_image: bool
    background_image: Optional[Any]
    image_width: int
    image_height: int
    zoom_factor: float

    # Required methods
    def update(self) -> None: ...
    def setPoints(self, points: List[Tuple[int, float, float]]) -> None: ...
    def get_selected_points(self) -> List[int]: ...


class MainWindowProtocol(Protocol):
    """Protocol defining the interface for the main window."""

    # Required attributes
    curve_view: CurveViewProtocol

    # Required methods
    def update_status_message(self, message: str) -> None: ...
    def refresh_point_edit_controls(self) -> None: ...


class ImageProtocol(Protocol):
    """Protocol defining the interface for image objects."""

    def width(self) -> int: ...
    def height(self) -> int: ...


class PointDataProtocol(Protocol):
    """Protocol defining the expected structure of point data."""

    frame: int
    x: float
    y: float
    interpolated: bool = False


# Type aliases for common data structures
PointTuple = Tuple[int, float, float]  # frame, x, y
PointTupleWithStatus = Tuple[int, float, float, bool]  # frame, x, y, interpolated
PointsList = List[Union[PointTuple, PointTupleWithStatus]]

# Generic type for service method return values
T = TypeVar('T')
