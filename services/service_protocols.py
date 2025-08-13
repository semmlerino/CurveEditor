#!/usr/bin/env python

"""
Service protocols for CurveEditor.

This module defines Protocol interfaces for dependency injection and type safety.
Minimal implementation for startup compatibility.
"""

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PySide6.QtWidgets import QPushButton, QRubberBand, QStatusBar
    # Note: Transform import moved to avoid circular dependency
    # Transform will be imported as needed in individual methods

from core.type_aliases import (
    CurveDataList,
    HistoryState,
    QtPointF,
)


# TYPE_CHECKING block removed - no imports needed
class LoggingServiceProtocol(Protocol):
    """Protocol for logging service dependency injection."""

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger by name."""
        ...

    def log_info(self, message: str) -> None:
        """Log an info message."""
        ...

    def log_error(self, message: str) -> None:
        """Log an error message."""
        ...

    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        ...


class StatusServiceProtocol(Protocol):
    """Protocol for status service dependency injection."""

    def set_status(self, message: str) -> None:
        """Set status message."""
        ...

    def clear_status(self) -> None:
        """Clear status message."""
        ...

    def show_info(self, message: str) -> None:
        """Show an info message."""
        ...

    def show_error(self, message: str) -> None:
        """Show an error message."""
        ...

    def show_warning(self, message: str) -> None:
        """Show a warning message."""
        ...


class ServiceProtocol(Protocol):
    """Base protocol for all services."""

    def initialize(self) -> None:
        """Initialize the service."""
        ...


class StateManagerProtocol(Protocol):
    """Protocol for state manager."""

    is_modified: bool
    auto_center_enabled: bool


class CurveViewProtocol(Protocol):
    """Protocol for curve view widgets.

    Defines the interface that curve view widgets must implement
    to work with the services layer.
    """

    # Basic attributes commonly used by services
    selected_point_idx: int
    curve_data: CurveDataList
    current_image_idx: int

    # Point management attributes
    points: CurveDataList
    selected_points: set[int]

    # Transform and positioning attributes
    offset_x: float
    offset_y: float
    x_offset: float  # Alias for offset_x
    y_offset: float  # Alias for offset_y
    zoom_factor: float

    # Interaction state attributes
    drag_active: bool
    pan_active: bool
    last_drag_pos: QtPointF | None
    last_pan_pos: QtPointF | None

    # Rubber band selection attributes
    rubber_band: "QRubberBand | None"
    rubber_band_active: bool
    rubber_band_origin: QtPointF

    # Visualization settings
    show_grid: bool
    show_background: bool
    show_velocity_vectors: bool
    show_all_frame_numbers: bool

    # Parent reference
    main_window: "MainWindowProtocol"  # Forward reference

    # Qt signals (typed for better inference)
    point_selected: object  # Signal[int] - avoid circular imports
    point_moved: object  # Signal[int, float, float]

    # Methods that services may call
    def update(self) -> None:
        """Update the view."""
        ...

    def repaint(self) -> None:
        """Repaint the view."""
        ...

    def width(self) -> int:
        """Get widget width."""
        ...

    def height(self) -> int:
        """Get widget height."""
        ...

    def setCursor(self, cursor: object) -> None:
        """Set widget cursor."""
        ...

    def unsetCursor(self) -> None:
        """Unset widget cursor."""
        ...

    def findPointAt(self, pos: QtPointF) -> int:
        """Find point at the given position."""
        ...

    def selectPointByIndex(self, idx: int) -> bool:
        """Select a point by its index."""
        ...

    def get_current_transform(self) -> object:  # Transform - avoid circular import
        """Get current transform object."""
        ...

    def _invalidate_caches(self) -> None:
        """Invalidate any cached data."""
        ...

    def get_point_data(self, idx: int) -> tuple[int, float, float, str | None]:
        """Get point data for the given index."""
        ...

    def toggleBackgroundVisible(self, visible: bool) -> None:
        """Toggle background visibility."""
        ...

    def toggle_point_interpolation(self, idx: int) -> None:
        """Toggle interpolation status of a point."""
        ...


class MainWindowProtocol(Protocol):
    """Protocol for main window widgets.

    Defines the interface that main window widgets must implement
    to work with the services layer.
    """

    # Basic attributes commonly used by services
    selected_indices: list[int]
    current_frame: int
    curve_view: object  # CurveViewProtocol, but avoid circular reference
    curve_data: CurveDataList
    curve_widget: object  # CurveViewWidget

    # History management
    history: list[object]  # list[HistoryState] but avoiding complex types
    history_index: int
    max_history_size: int

    # Point attributes
    point_name: str
    point_color: str

    # UI component references
    undo_button: "QPushButton | None"
    redo_button: "QPushButton | None"
    save_button: "QPushButton | None"
    ui_components: object  # UIComponents container

    # Service references
    services: object  # Service container

    # State management
    state_manager: StateManagerProtocol

    @property
    def is_modified(self) -> bool:
        """Get modified state (proxy to state_manager.is_modified)."""
        ...

    # Methods that services may call
    def add_to_history(self) -> None:
        """Add current state to history."""
        ...

    def restore_state(self, state: HistoryState) -> None:
        """Restore state from history."""
        ...

    def update_status(self, message: str) -> None:
        """Update status bar message."""
        ...

    def setWindowTitle(self, title: str) -> None:
        """Set window title."""
        ...

    def statusBar(self) -> "QStatusBar":
        """Get status bar widget."""
        ...

    def close(self) -> bool:
        """Close the window."""
        ...

    def set_centering_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-centering on frame change."""
        ...

    def apply_smooth_operation(self) -> None:
        """Apply smoothing operation to selected points."""
        ...


class HistoryContainerProtocol(Protocol):
    """Protocol for objects that can be saved and restored in history.

    This consolidates the HistoryContainerProtocol from history_service.py
    to avoid protocol duplication and import issues.
    """

    # Data attributes (writeable for history operations)
    curve_data: CurveDataList
    point_name: str
    point_color: str

    # History management attributes
    history: list[object]  # list[HistoryState]
    history_index: int
    max_history_size: int

    # Component references
    curve_widget: object  # CurveView widget
    curve_view: object  # CurveView widget (alias)
    services: object  # Service container
    ui_components: object  # UI components container

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


# Simple implementations for backward compatibility
class SimpleLoggingService:
    """Simple logging service implementation."""

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger by name."""
        return logging.getLogger(name)

    def log_info(self, message: str) -> None:
        """Log an info message."""
        logging.getLogger("app").info(message)

    def log_error(self, message: str) -> None:
        """Log an error message."""
        logging.getLogger("app").error(message)

    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        logging.getLogger("app").warning(message)


class SimpleStatusService:
    """Simple status service implementation."""

    def set_status(self, message: str) -> None:
        """Set status message."""
        # For startup, just log the status
        logging.getLogger("status").info(f"Status: {message}")

    def clear_status(self) -> None:
        """Clear status message."""
        # For startup, just log
        logging.getLogger("status").debug("Status cleared")

    def show_info(self, message: str) -> None:
        """Show an info message."""
        # For startup, just log the info
        logging.getLogger("status").info(f"Info: {message}")

    def show_error(self, message: str) -> None:
        """Show an error message."""
        # For startup, just log the error
        logging.getLogger("status").error(f"Error: {message}")

    def show_warning(self, message: str) -> None:
        """Show a warning message."""
        # For startup, just log the warning
        logging.getLogger("status").warning(f"Warning: {message}")


# Factory functions for creating simple implementations
def create_simple_logging_service() -> LoggingServiceProtocol:
    """Create a simple logging service."""
    return SimpleLoggingService()


def create_simple_status_service() -> StatusServiceProtocol:
    """Create a simple status service."""
    return SimpleStatusService()
