"""
Service layer protocols for CurveEditor.

This module contains Protocol definitions for services like TransformService,
DataService, InteractionService, and UIService. These protocols define the
interface contracts that services must implement.
"""

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PySide6.QtGui import QPixmap

from protocols.data import CurveDataList


class ServiceProtocol(Protocol):
    """Base protocol for all services."""

    def initialize(self) -> None:
        """Initialize the service."""
        ...

    def clear_cache(self) -> None:
        """Clear any cached data."""
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


class TransformServiceProtocol(Protocol):
    """Protocol for transform service."""

    def create_transform_from_view_state(self, view_state: object) -> object:
        """Create transform from view state."""
        ...

    def get_cache_info(self) -> dict[str, object]:
        """Get cache statistics."""
        ...

    def clear_cache(self) -> None:
        """Clear transform cache."""
        ...

    def data_to_screen(self, x: float, y: float) -> tuple[float, float]:
        """Transform data coordinates to screen coordinates."""
        ...

    def screen_to_data(self, x: float, y: float) -> tuple[float, float]:
        """Transform screen coordinates to data coordinates."""
        ...


class DataServiceProtocol(Protocol):
    """Protocol for data service."""

    def load_tracking_data(self, file_path: str) -> CurveDataList:
        """Load tracking data from file."""
        ...

    def save_tracking_data(self, file_path: str, data: CurveDataList) -> bool:
        """Save tracking data to file."""
        ...

    def load_image(self, file_path: str) -> "QPixmap | None":
        """Load image from file."""
        ...

    def get_supported_formats(self) -> list[str]:
        """Get list of supported file formats."""
        ...

    def analyze_data(self, data: CurveDataList) -> dict[str, object]:
        """Analyze curve data for statistics."""
        ...

    def clear_cache(self) -> None:
        """Clear data cache."""
        ...


class InteractionServiceProtocol(Protocol):
    """Protocol for interaction service."""

    def handle_point_selection(self, point_idx: int) -> None:
        """Handle point selection."""
        ...

    def handle_point_move(self, point_idx: int, x: float, y: float) -> None:
        """Handle point movement."""
        ...

    def handle_rubber_band_selection(self, start: object, end: object) -> list[int]:
        """Handle rubber band selection."""
        ...

    def find_point_at(self, x: float, y: float, tolerance: float = 5.0) -> int:
        """Find point at given coordinates."""
        ...

    def get_spatial_index_stats(self) -> dict[str, object]:
        """Get spatial index statistics."""
        ...

    def clear_cache(self) -> None:
        """Clear interaction cache."""
        ...


class UIServiceProtocol(Protocol):
    """Protocol for UI service."""

    def show_dialog(self, dialog_type: str, **kwargs: object) -> object:
        """Show a dialog."""
        ...

    def update_status(self, message: str) -> None:
        """Update status bar."""
        ...

    def refresh_ui(self) -> None:
        """Refresh UI components."""
        ...

    def get_theme(self) -> str:
        """Get current theme."""
        ...

    def set_theme(self, theme: str) -> None:
        """Set UI theme."""
        ...


class FileLoadWorkerProtocol(Protocol):
    """Protocol for file loading worker threads."""

    @property
    def tracking_file_path(self) -> str | None:
        """Get current tracking file path."""
        ...

    def stop(self) -> None:
        """Request the worker to stop processing."""
        ...

    def run(self) -> None:
        """Main worker method that runs in background thread."""
        ...

    def start_work(self, tracking_file: str | None = None, image_dir: str | None = None) -> None:
        """Start the background work thread."""
        ...

    def load_file(self, file_path: str) -> object:
        """Load file data from the specified path."""
        ...

    def queue_tracking_file(self, file_path: str) -> None:
        """Queue a tracking file for loading."""
        ...

    def queue_image_directory(self, dir_path: str) -> None:
        """Queue an image directory for loading."""
        ...


class SessionManagerProtocol(Protocol):
    """Protocol for session management."""

    def save_session(self, session_data: dict[str, object]) -> bool:
        """Save session data to file."""
        ...

    def load_session(self) -> dict[str, object] | None:
        """Load session data from file."""
        ...

    def create_session_data(
        self,
        tracking_file: str | None = None,
        image_directory: str | None = None,
        current_frame: int = 0,
        zoom_level: float | None = None,
        pan_offset: tuple[float, float] | None = None,
        window_geometry: object = None,
        active_points: list[str] | None = None,
    ) -> dict[str, object]:
        """Create session data dictionary."""
        ...


class ServicesProtocol(Protocol):
    """Protocol for service container."""

    data_service: DataServiceProtocol
    transform_service: TransformServiceProtocol
    interaction_service: InteractionServiceProtocol
    ui_service: UIServiceProtocol

    def initialize_all(self) -> None:
        """Initialize all services."""
        ...

    def shutdown_all(self) -> None:
        """Shutdown all services."""
        ...

    # Methods needed by file_operations_manager.py
    def confirm_action(self, message: str, parent: object | None) -> bool:
        """Confirm action with user."""
        ...

    def save_track_data(self, data: object, parent: object | None) -> bool:
        """Save tracking data to file."""
        ...

    def load_track_data_from_file(self, file_path: str) -> object | None:
        """Load tracking data from file."""
        ...

    def show_warning(self, message: str) -> None:
        """Show warning message to user."""
        ...


class SignalProtocol(Protocol):
    """Protocol for Qt signal objects.

    Note: This is duplicated in ui.py for import convenience,
    but the authoritative definition is here.
    """

    def emit(self, *args: object) -> None:
        """Emit the signal with arguments."""
        ...

    def connect(self, slot: object) -> object:
        """Connect signal to slot."""
        ...

    def disconnect(self, slot: object | None = None) -> None:
        """Disconnect signal from slot."""
        ...

    def receivers(self) -> int:
        """Return the number of connected receivers (Qt-like interface)."""
        ...
