#!/usr/bin/env python
"""
Type aliases for CurveEditor to improve type safety and readability.

This module provides centralized type aliases for complex types used throughout
the codebase, reducing duplication and improving maintainability.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeAlias

if TYPE_CHECKING:
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QImage, QPixmap
    from PySide6.QtWidgets import QWidget

# Core data types - consolidated point definitions
PointTuple3 = tuple[int, float, float]
PointTuple4 = tuple[int, float, float, str | bool]
PointTuple4Str = tuple[int, float, float, str]
PointTuple4Bool = tuple[int, float, float, bool]
# Use union of specific tuple types for type safety
LegacyPointData = PointTuple3 | PointTuple4
PointData = LegacyPointData  # Alias for compatibility

# CurveDataList: For mutable data stores (properties, attributes) - invariant
CurveDataList = list[LegacyPointData]
PointList = list[PointData]  # Alias for compatibility

# CurveDataInput: For function parameters that accept any compatible sequence - covariant
# Use this for read-only parameters to accept list[PointTuple3], list[PointTuple4], etc.
CurveDataInput = Sequence[LegacyPointData]


# Path types
PathLike = str | Path

# Qt types (with better type handling)
if TYPE_CHECKING:
    QtPointF: TypeAlias = QPoint | QPointF  # Accept both QPoint and QPointF
    QtPixmap: TypeAlias = QPixmap
    QtImage: TypeAlias = QImage
    QtWidget: TypeAlias = QWidget
    QtSignal: TypeAlias = object  # Signal[...] - specific types in protocols
else:
    # Runtime stubs - avoid Any for better type inference
    QtPointF = QtPixmap = QtImage = QtWidget = QtSignal = object

# UI component types
UIComponent = QtWidget
UIContainer = dict[str, QtWidget]

# Service types
ServiceRegistry = dict[str, object]
SignalConnection = object  # Qt signal connection


class HasCurveData(Protocol):
    """Protocol for objects that have curve data."""

    @property
    def curve_data(self) -> CurveDataList:
        """Get the curve data."""
        ...


class HasSelection(Protocol):
    """Protocol for objects that have selection state."""

    @property
    def selected_indices(self) -> list[int]:
        """Get the selected indices."""
        ...


# Callback types
ProgressCallback = Callable[[int, int], None] | None  # (current, total) -> None
StatusCallback = Callable[[str], None] | None  # (message) -> None
ErrorCallback = Callable[[str], None] | None  # (error_message) -> None

# File operation types
FileOperation = str  # "load", "save", "export", etc.
FileResult = dict[str, str | int | bool | list[str]]  # Result of file operations

# Transform types
Coordinates = tuple[float, float]  # (x, y)
ScreenCoordinates = tuple[int, int]  # (x, y) in screen pixels
BoundingBox = tuple[float, float, float, float]  # (min_x, max_x, min_y, max_y)

# History types - more specific than Any
HistoryState = dict[str, CurveDataList | str | int | float | bool]  # State snapshot for undo/redo

# Multi-point tracking types
TrackingPointData = dict[str, CurveDataList | str | bool]  # Single tracking point with metadata
TrackedData = dict[str, TrackingPointData]  # All tracking points keyed by name

# Search mode for multi-curve operations (Phase 8)
from typing import Literal

SearchMode: TypeAlias = Literal["active", "all_visible"]
"""
Search mode for point finding operations.

- "active": Search active curve only (default, backward compatible)
- "all_visible": Search all visible curves (multi-curve mode)
"""
