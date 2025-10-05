#!/usr/bin/env python

"""
Service protocols for CurveEditor.

This module defines Protocol interfaces for dependency injection and type safety.
Minimal implementation for startup compatibility.
"""
# pyright: reportImportCycles=false

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PySide6.QtWidgets import QStatusBar

    # Note: Transform import moved to avoid circular dependency
    # Transform will be imported as needed in individual methods

from core.type_aliases import (
    CurveDataList,
)
from protocols.services import SignalProtocol  # noqa: F401  # pyright: ignore[reportUnusedImport] - re-exported

# Import consolidated protocol definitions from protocols.ui and protocols.services
from protocols.ui import (  # noqa: F401 - re-exported for backward compat
    CurveViewProtocol,
    MainWindowProtocol,  # pyright: ignore[reportUnusedImport]
    StateManagerProtocol,  # pyright: ignore[reportUnusedImport]
)


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


# StateManagerProtocol, CurveViewProtocol, MainWindowProtocol imported from protocols.ui (see line 28)


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
