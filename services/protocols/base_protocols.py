"""
Base protocol definitions for service interfaces.

This module provides the fundamental protocol interfaces used throughout
the service layer to ensure type safety and clear contracts.
"""

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from core.typing_extensions import (
    Coordinate,
    CurveData,
    EventResult,
    Frame,
    PointType,
    SelectionSet,
)

if TYPE_CHECKING:
    from PySide6.QtGui import QMouseEvent

    from services.transform_service import Transform


@runtime_checkable
class CurveViewProtocol(Protocol):
    """Protocol for curve view objects."""

    @property
    def points(self) -> CurveData:
        """Get the curve data points."""
        ...

    @points.setter
    def points(self, value: CurveData) -> None:
        """Set the curve data points."""
        ...

    @property
    def selected_points(self) -> SelectionSet:
        """Get the set of selected point indices."""
        ...

    @selected_points.setter
    def selected_points(self, value: SelectionSet) -> None:
        """Set the selected point indices."""
        ...

    @property
    def transform(self) -> "Transform":
        """Get the view transform."""
        ...

    def update(self) -> None:
        """Update the view display."""
        ...

    def repaint(self) -> None:
        """Repaint the view."""
        ...


@runtime_checkable
class MainWindowProtocol(Protocol):
    """Protocol for main window objects."""

    @property
    def curve_view(self) -> CurveViewProtocol:
        """Get the curve view widget."""
        ...

    def statusBar(self) -> Any:
        """Get the status bar."""
        ...

    def update_ui(self) -> None:
        """Update the UI."""
        ...


@runtime_checkable
class TransformProtocol(Protocol):
    """Protocol for transform objects."""

    def device_to_curve(self, x: float, y: float) -> Coordinate:
        """Convert device coordinates to curve coordinates."""
        ...

    def curve_to_device(self, x: float, y: float) -> tuple[int, int]:
        """Convert curve coordinates to device coordinates."""
        ...

    def get_scale(self) -> tuple[float, float]:
        """Get the current scale factors."""
        ...

    def get_offset(self) -> tuple[float, float]:
        """Get the current offset values."""
        ...


@runtime_checkable
class ServiceProtocol(Protocol):
    """Base protocol for all services."""

    def initialize(self) -> None:
        """Initialize the service."""
        ...

    def shutdown(self) -> None:
        """Shutdown the service."""
        ...


@runtime_checkable
class SelectionServiceProtocol(Protocol):
    """Protocol for selection service."""

    def select_point_by_index(self, view: CurveViewProtocol, idx: int, add_to_selection: bool = False) -> bool:
        """Select a point by its index."""
        ...

    def clear_selection(self, view: CurveViewProtocol) -> None:
        """Clear all selections."""
        ...

    def select_all(self, view: CurveViewProtocol) -> None:
        """Select all points."""
        ...

    def get_selected_indices(self, view: CurveViewProtocol) -> list[int]:
        """Get list of selected indices."""
        ...


@runtime_checkable
class ManipulationServiceProtocol(Protocol):
    """Protocol for point manipulation service."""

    def update_point_position(self, view: CurveViewProtocol, idx: int, x: float, y: float) -> Any:
        """Update a point's position."""
        ...

    def delete_point(self, view: CurveViewProtocol, idx: int) -> PointType | None:
        """Delete a point."""
        ...

    def add_point(self, view: CurveViewProtocol, frame: Frame, x: float, y: float) -> bool:
        """Add a new point."""
        ...


@runtime_checkable
class HistoryServiceProtocol(Protocol):
    """Protocol for history service."""

    def add_to_history(self, state: CurveData, description: str = "") -> None:
        """Add a state to history."""
        ...

    def undo(self) -> CurveData | None:
        """Undo the last action."""
        ...

    def redo(self) -> CurveData | None:
        """Redo the next action."""
        ...

    def can_undo(self) -> bool:
        """Check if undo is available."""
        ...

    def can_redo(self) -> bool:
        """Check if redo is available."""
        ...


@runtime_checkable
class EventHandlerProtocol(Protocol):
    """Protocol for event handler service."""

    def handle_mouse_press(
        self,
        view: CurveViewProtocol,
        event: "QMouseEvent",
        selection_service: SelectionServiceProtocol,
        manipulation_service: ManipulationServiceProtocol,
    ) -> EventResult:
        """Handle mouse press events."""
        ...

    def handle_mouse_move(
        self,
        view: CurveViewProtocol,
        event: "QMouseEvent",
        selection_service: SelectionServiceProtocol,
        manipulation_service: ManipulationServiceProtocol,
    ) -> EventResult:
        """Handle mouse move events."""
        ...

    def handle_mouse_release(
        self,
        view: CurveViewProtocol,
        event: "QMouseEvent",
        selection_service: SelectionServiceProtocol,
        manipulation_service: ManipulationServiceProtocol,
    ) -> EventResult:
        """Handle mouse release events."""
        ...
