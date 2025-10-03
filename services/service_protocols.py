#!/usr/bin/env python

"""
Service protocols for CurveEditor.

This module defines Protocol interfaces for dependency injection and type safety.
Minimal implementation for startup compatibility.
"""
# pyright: reportImportCycles=false

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PySide6.QtWidgets import QRubberBand, QStatusBar

    # Note: Transform import moved to avoid circular dependency
    # Transform will be imported as needed in individual methods

from core.type_aliases import (
    CurveDataInput,
    CurveDataList,
    QtPointF,
)

# Import consolidated protocol definitions from protocols.ui
from protocols.ui import MainWindowProtocol, StateManagerProtocol  # noqa: F401 - re-exported for backward compat


class SignalProtocol(Protocol):
    """Protocol for Qt signal objects with emit method."""

    def emit(self, *args: object) -> None:
        """Emit the signal with arguments."""
        ...

    def connect(self, slot: Callable[..., object]) -> object:
        """Connect signal to slot."""
        ...

    def disconnect(self, slot: Callable[..., object] | None = None) -> None:
        """Disconnect signal from slot."""
        ...


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

    def log_debug(self, message: str) -> None:
        """Log a debug message."""
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


# StateManagerProtocol imported from protocols.ui (see line 29)


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
    pan_offset_x: float
    pan_offset_y: float
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
    main_window: object  # MainWindowProtocol - avoid circular import

    # Qt signals (properly typed for type safety)
    point_selected: SignalProtocol  # Signal[int]
    point_moved: SignalProtocol  # Signal[int, float, float]

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

    def get_transform(self) -> object:  # Transform - avoid circular import
        """Get transform object (alias for compatibility)."""
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

    def set_curve_data(self, data: CurveDataInput) -> None:
        """Set the curve data."""
        ...

    def setPoints(self, data: CurveDataList, width: int, height: int) -> None:
        """Set points with image dimensions (legacy compatibility)."""
        ...

    def set_selected_indices(self, indices: list[int]) -> None:
        """Set the selected point indices."""
        ...


# MainWindowProtocol imported from protocols.ui (see line 29)


class BatchEditableProtocol(Protocol):
    """Protocol for batch-editable parent components.

    Defines the interface that parent widgets must implement
    to support batch editing operations.
    """

    # UI component references
    point_edit_layout: object | None  # QLayout
    batch_edit_group: object | None  # QGroupBox
    curve_view: CurveViewProtocol | None

    # Data attributes
    selected_indices: list[int]
    image_width: int
    image_height: int

    # Methods for batch operations
    def statusBar(self) -> "QStatusBar":
        """Get status bar widget."""
        ...

    def update_curve_data(self, data: CurveDataList) -> None:
        """Update curve data."""
        ...

    def add_to_history(self) -> None:
        """Add current state to history."""
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

    def log_debug(self, message: str) -> None:
        """Log a debug message."""
        logging.getLogger("app").debug(message)


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
