"""
Data model protocols for CurveEditor.

This module contains Protocol definitions for data models like points,
curves, history states, and other data structures. It also imports and
re-exports common type aliases for convenience.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PySide6.QtGui import QImage, QPixmap

# Import and re-export type aliases from core.type_aliases
from core.type_aliases import (
    CurveDataInput,
    CurveDataList,
    HistoryState,
    LegacyPointData,
    PointData,
    PointList,
    PointTuple3,
    PointTuple4Bool,
    PointTuple4Str,
    QtPointF,
    TrackedData,
    TrackingPointData,
)

# Legacy compatibility aliases
Point4 = PointTuple4Str | PointTuple4Bool | PointTuple3


class PointProtocol(Protocol):
    """Protocol for point objects."""

    frame: int
    x: float
    y: float
    status: str | None

    def to_tuple(self) -> tuple[int, float, float, str | None]:
        """Convert to tuple representation."""
        ...


class CurveDataProtocol(Protocol):
    """Protocol for curve data containers."""

    points: CurveDataList
    name: str
    color: str

    def get_point(self, index: int) -> PointData | None:
        """Get point at index."""
        ...

    def add_point(self, point: PointData) -> None:
        """Add a point to the curve."""
        ...

    def remove_point(self, index: int) -> bool:
        """Remove point at index."""
        ...

    def update_point(self, index: int, point: PointData) -> bool:
        """Update point at index."""
        ...

    def get_frame_range(self) -> tuple[int, int]:
        """Get min and max frame numbers."""
        ...


class ImageProtocol(Protocol):
    """Protocol for image objects."""

    width: int
    height: int

    def pixmap(self) -> "QPixmap":
        """Get QPixmap representation."""
        ...

    def image(self) -> "QImage":
        """Get QImage representation."""
        ...

    def is_null(self) -> bool:
        """Check if image is null/empty."""
        ...


class HistoryContainerProtocol(Protocol):
    """Protocol for objects that can be saved and restored in history."""

    # Data attributes
    curve_data: CurveDataList
    point_name: str
    point_color: str

    # History management
    history: list[object]
    history_index: int
    max_history_size: int

    # Component references
    curve_widget: object
    curve_view: object
    services: object
    ui_components: object

    def restore_state(self, state: HistoryState) -> None:
        """Restore state from history."""
        ...


class HistoryCommandProtocol(Protocol):
    """Protocol for history commands that can be undone and redone."""

    def undo(self, container: HistoryContainerProtocol) -> None:
        """Undo this command."""
        ...

    def redo(self, container: HistoryContainerProtocol) -> None:
        """Redo this command."""
        ...

    def get_description(self) -> str:
        """Get human-readable description of the command."""
        ...


class BatchEditableProtocol(Protocol):
    """Protocol for batch-editable parent components."""

    # UI component references
    point_edit_layout: object | None
    batch_edit_group: object | None
    curve_view: object | None

    # Data attributes
    selected_indices: list[int]
    image_width: int
    image_height: int

    def statusBar(self) -> object:
        """Get status bar widget."""
        ...

    def update_curve_data(self, data: CurveDataList) -> None:
        """Update curve data."""
        ...

    def add_to_history(self) -> None:
        """Add current state to history."""
        ...


class PointMovedSignalProtocol(Protocol):
    """Protocol for point moved signal objects."""

    def emit(self, index: int, x: float, y: float) -> None:
        """Emit the signal with point movement data."""
        ...

    def connect(self, slot: object) -> object:
        """Connect signal to slot."""
        ...


class VoidSignalProtocol(Protocol):
    """Protocol for void signal objects."""

    def emit(self) -> None:
        """Emit the signal without arguments."""
        ...

    def connect(self, slot: object) -> object:
        """Connect signal to slot."""
        ...


# Export all type aliases and protocols
__all__ = [
    # Type aliases
    "CurveDataInput",
    "CurveDataList",
    "HistoryState",
    "LegacyPointData",
    "PointData",
    "PointList",
    "PointTuple3",
    "PointTuple4Bool",
    "PointTuple4Str",
    "Point4",
    "QtPointF",
    "TrackingPointData",
    "TrackedData",
    # Protocols
    "PointProtocol",
    "CurveDataProtocol",
    "ImageProtocol",
    "HistoryContainerProtocol",
    "HistoryCommandProtocol",
    "BatchEditableProtocol",
    "PointMovedSignalProtocol",
    "VoidSignalProtocol",
]
