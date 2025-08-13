"""
Type aliases and extensions for the CurveEditor project.

This module provides standardized type definitions used throughout the codebase
to ensure consistency and reduce type errors.
"""

from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    TypeVar,
)

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPaintEvent
    from PySide6.QtWidgets import QWidget

# ==================== Basic Types ====================

# Point types - the fundamental data structure for curve points
type PointTuple = tuple[int, float, float]
type PointTupleWithStatus = tuple[int, float, float, str | bool]
type PointType = PointTuple | PointTupleWithStatus

# Collections of points
type CurveData = list[PointType]
type CurveDataArray = NDArray[np.float64]
type PointList = list[PointType]
type PointIndices = list[int]

# Coordinate types
type Coordinate = tuple[float, float]
type IntCoordinate = tuple[int, int]
type ScreenCoordinate = IntCoordinate
type CurveCoordinate = Coordinate

# Frame types
type Frame = int
type FrameRange = tuple[Frame, Frame]
type FrameList = list[Frame]

# ==================== Transform Types ====================

# Transform matrix type (3x3 for 2D homogeneous coordinates)
type TransformMatrix = NDArray[np.float64]

# Scale and offset for simple transforms
type ScaleFactors = tuple[float, float]
type OffsetValues = tuple[float, float]

# ==================== UI Types ====================

# Color representations
type ColorRGB = tuple[int, int, int]
type ColorRGBA = tuple[int, int, int, int]
type ColorHex = str
type ColorType = ColorRGB | ColorRGBA | ColorHex | "QColor"

# Size types
type Size = tuple[int, int]
type SizeF = tuple[float, float]

# Rectangle types
type RectTuple = tuple[int, int, int, int]  # x, y, width, height
type RectFTuple = tuple[float, float, float, float]

# ==================== Event Types ====================

# Mouse button types
type MouseButton = int  # Qt.MouseButton value
type KeyboardModifier = int  # Qt.KeyboardModifier value
type KeyCode = int  # Qt.Key value

# Event results
type EventHandled = bool
type EventResult = EventHandled | None

# ==================== File Types ====================

# File paths
type FilePath = str
type DirectoryPath = str
type FilePathList = list[FilePath]

# File formats
type FileFormat = str  # "json", "csv", etc.
type ImageFormat = str  # "png", "jpg", etc.

# ==================== Service Types ====================

# Service state
type ServiceState = dict[str, Any]
type ServiceConfig = dict[str, Any]

# History types
type HistoryState = CurveData
type HistoryEntry = tuple[HistoryState, str]  # (state, description)
type HistoryIndex = int

# Selection types
type SelectionSet = set[int]
type SelectionList = list[int]

# ==================== Callback Types ====================

# Generic callback types
type VoidCallback = Callable[[], None]
type BoolCallback = Callable[[], bool]
type DataCallback = Callable[[CurveData], None]

# Event callbacks
type MouseEventCallback = Callable[["QMouseEvent"], None]
type KeyEventCallback = Callable[["QKeyEvent"], None]
type PaintEventCallback = Callable[["QPaintEvent"], None]

# Update callbacks
type UpdateCallback = Callable[[], None]
type ProgressCallback = Callable[[float], None]  # 0.0 to 1.0

# ==================== Generic Type Variables ====================

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
T_contra = TypeVar('T_contra', contravariant=True)

# Widget type variable
WidgetT = TypeVar('WidgetT', bound='QWidget')

# ==================== Protocol Types ====================

class SupportsTransform(Protocol):
    """Protocol for objects that support coordinate transformation."""

    def device_to_curve(self, x: float, y: float) -> Coordinate: ...
    def curve_to_device(self, x: float, y: float) -> IntCoordinate: ...
    def get_scale(self) -> ScaleFactors: ...
    def get_offset(self) -> OffsetValues: ...


class SupportsPoints(Protocol):
    """Protocol for objects that have point data."""

    @property
    def points(self) -> CurveData: ...

    @points.setter
    def points(self, value: CurveData) -> None: ...

    @property
    def selected_points(self) -> SelectionSet: ...


class SupportsUpdate(Protocol):
    """Protocol for objects that can be updated/refreshed."""

    def update(self) -> None: ...
    def repaint(self) -> None: ...


class SupportsFile(Protocol):
    """Protocol for objects that support file operations."""

    def load(self, path: FilePath) -> bool: ...
    def save(self, path: FilePath) -> bool: ...
    def get_file_path(self) -> FilePath | None: ...


# ==================== Utility Functions ====================

def is_point_with_status(point: PointType) -> bool:
    """Check if a point has status information."""
    return len(point) > 3


def get_point_coordinates(point: PointType) -> Coordinate:
    """Extract x, y coordinates from a point."""
    return (point[1], point[2])


def get_point_frame(point: PointType) -> Frame:
    """Extract frame number from a point."""
    return point[0]


def create_point(frame: Frame, x: float, y: float, status: str | bool | None = None) -> PointType:
    """Create a point tuple with optional status."""
    if status is not None:
        return (frame, x, y, status)
    return (frame, x, y)


# ==================== Type Guards ====================

def is_curve_data(data: Any) -> bool:
    """Type guard for CurveData."""
    if not isinstance(data, list):
        return False
    if not data:
        return True  # Empty list is valid

    first = data[0]
    if not isinstance(first, tuple):
        return False
    if len(first) < 3:
        return False
    if not isinstance(first[0], int):
        return False
    if not isinstance(first[1], int | float):
        return False
    if not isinstance(first[2], int | float):
        return False

    return True


def is_valid_color(color: Any) -> bool:
    """Type guard for color values."""
    if isinstance(color, str):
        # Check hex color
        return color.startswith('#') and len(color) in (7, 9)
    if isinstance(color, tuple):
        if len(color) not in (3, 4):
            return False
        return all(isinstance(c, int) and 0 <= c <= 255 for c in color)
    return False


# ==================== Constants ====================

# Default values
DEFAULT_POINT_COLOR: ColorHex = "#FF0000"
DEFAULT_SELECTED_COLOR: ColorHex = "#00FF00"
DEFAULT_BACKGROUND_COLOR: ColorHex = "#2B2B2B"

# Size limits
MIN_POINT_SIZE: int = 3
MAX_POINT_SIZE: int = 20
DEFAULT_POINT_SIZE: int = 8

# Frame limits
MIN_FRAME: Frame = 0
MAX_FRAME: Frame = 999999
DEFAULT_FRAME_RANGE: FrameRange = (0, 100)

# Selection limits
MAX_SELECTION_SIZE: int = 10000

# File limits
MAX_RECENT_FILES: int = 10
MAX_FILE_SIZE_MB: int = 100

# Cache limits
MAX_CACHE_SIZE: int = 100
MAX_HISTORY_SIZE: int = 100

# Performance thresholds
LARGE_DATASET_THRESHOLD: int = 10000
VERY_LARGE_DATASET_THRESHOLD: int = 100000

# UI Constants
DEFAULT_WINDOW_SIZE: Size = (1200, 800)
MIN_WINDOW_SIZE: Size = (800, 600)
DEFAULT_MARGIN: int = 10
DEFAULT_SPACING: int = 5
