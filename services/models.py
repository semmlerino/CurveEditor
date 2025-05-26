#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Models module for CurveEditor.

This module provides data models used throughout the application,
following proper object-oriented design principles to reduce redundancy
and improve type safety.
"""

import copy
from dataclasses import dataclass
from typing import Optional, List, Tuple, Iterator, Union, cast

from services.logging_service import LoggingService

logger = LoggingService.get_logger("models")


@dataclass
class Point:
    """
    Represents a tracking point with frame, coordinates, and optional status.

    This class replaces the tuple-based representation (frame, x, y, [status])
    with a proper object that provides type safety and additional functionality.
    """
    frame: int
    x: float
    y: float
    status: Optional[bool] = None

    def as_tuple(self) -> Union[Tuple[int, float, float], Tuple[int, float, float, bool]]:
        """Convert to the traditional tuple format for backward compatibility."""
        if self.status is not None:
            return (self.frame, self.x, self.y, self.status)
        return (self.frame, self.x, self.y)

    @classmethod
    def from_tuple(cls, point_tuple: Union[Tuple[int, float, float], Tuple[int, float, float, bool]]) -> 'Point':
        """Create a Point from a tuple representation."""
        if len(point_tuple) >= 4:
            return cls(frame=point_tuple[0], x=point_tuple[1], y=point_tuple[2], status=point_tuple[3])
        return cls(frame=point_tuple[0], x=point_tuple[1], y=point_tuple[2])

    def __iter__(self) -> Iterator[Union[int, float, bool]]:
        """Support tuple-like unpacking and iteration."""
        yield self.frame
        yield self.x
        yield self.y
        if self.status is not None:
            yield self.status


class PointsCollection:
    """
    Collection class for managing points with type safety and enhanced functionality.

    This provides a bridge between the legacy tuple-based representation and the
    new Point class, allowing gradual migration.
    """
    def __init__(self, points: Optional[Union[List[Tuple[int, float, float]], List[Point]]] = None):
        """Initialize with optional points data."""
        self._points: List[Point] = []

        if points is not None and len(points) > 0:
            if isinstance(points[0], Point):
                # Ensure points is correctly typed as List[Point] before deepcopy
                self._points = copy.deepcopy(cast(List[Point], points))
            else:
                # Convert from legacy tuple format using proper type cast
                point_tuples = cast(List[Union[Tuple[int, float, float], Tuple[int, float, float, bool]]], points)
                self._points = [Point.from_tuple(p) for p in point_tuples]

    def as_tuples(self) -> List[Union[Tuple[int, float, float], Tuple[int, float, float, bool]]]:
        """Get points as tuples for backward compatibility."""
        return [p.as_tuple() for p in self._points]

    def __getitem__(self, idx: int) -> Point:
        """Support list-like indexing."""
        return self._points[idx]

    def __len__(self) -> int:
        """Support len() operation."""
        return len(self._points)

    def __iter__(self) -> Iterator[Point]:
        """Support iteration."""
        return iter(self._points)

    def append(self, point: Union[Point, Tuple[int, float, float]]) -> None:
        """Add a point to the collection."""
        if isinstance(point, Point):
            self._points.append(copy.deepcopy(point))
        else:
            self._points.append(Point.from_tuple(point))

    def sort_by_frame(self) -> None:
        """Sort points by frame number."""
        self._points.sort(key=lambda p: p.frame)
