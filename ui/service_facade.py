#!/usr/bin/env python
"""
Service Facade for 3DE4 Curve Editor.

This module provides a unified interface to all services used throughout the
application. It centralizes service access using the new consolidated 4-service
architecture for improved maintainability and reduced complexity.

Consolidated Services:
1. TransformService - Coordinate transformations and view state
2. DataService - Data operations, analysis, file I/O, images
3. InteractionService - User interactions, point manipulation, history
4. UIService - UI operations, dialogs, status updates
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.data_service import DataService
    from services.interaction_service import InteractionService
    from services.transform_service import Transform, TransformService, ViewState
    from services.ui_service import UIService

# Import core state management
try:
    from core.image_state import ImageState
except ImportError:
    # Stub for startup
    class ImageState:
        def __init__(self):
            pass

        def sync_from_main_window(self, window):
            pass


# Import the consolidated services
try:
    from services.transform_service import Transform, TransformService, ViewState, get_transform_service
except ImportError:
    if not TYPE_CHECKING:
        TransformService = None
        Transform = None
        ViewState = None
    get_transform_service = None

try:
    from services.data_service import DataService, get_data_service
except ImportError:
    if not TYPE_CHECKING:
        DataService = None
    get_data_service = None

try:
    from services.interaction_service import InteractionService, get_interaction_service
except ImportError:
    if not TYPE_CHECKING:
        InteractionService = None
    get_interaction_service = None

try:
    from services.ui_service import UIService, get_ui_service
except ImportError:
    if not TYPE_CHECKING:
        UIService = None
    get_ui_service = None

# Legacy services are now part of the consolidated services
# FileService functionality -> DataService
# HistoryService functionality -> InteractionService


class ServiceFacade:
    """
    Unified facade for accessing all application services.

    This class provides a single entry point for all service operations,
    using the new consolidated 4-service architecture.
    """

    def __init__(self, main_window: Any = None):
        """Initialize the service facade with consolidated services.

        Args:
            main_window: Optional reference to the main application window
        """
        self.main_window = main_window
        self.logger = logging.getLogger("service_facade")

        # Initialize consolidated services
        self._transform_service = get_transform_service() if get_transform_service else None
        self._data_service = get_data_service() if get_data_service else None
        self._interaction_service = get_interaction_service() if get_interaction_service else None
        self._ui_service = get_ui_service() if get_ui_service else None

        # Initialize state management
        self.image_state = ImageState()

        # Legacy service references (now redirect to consolidated services)
        self._file_service = self._data_service  # FileService -> DataService
        self._history_service = self._interaction_service  # HistoryService -> InteractionService

    # ==================== Transform Service Methods ====================

    @property
    def transform_service(self) -> TransformService | None:
        """Get the transform service instance."""
        return self._transform_service

    def create_view_state(self, curve_view: Any) -> ViewState | None:
        """Create a ViewState from a CurveView."""
        if self._transform_service:
            return self._transform_service.create_view_state(curve_view)
        return None

    def create_transform(self, view_state: ViewState) -> Transform | None:
        """Create a Transform from a ViewState."""
        if self._transform_service:
            return self._transform_service.create_transform(view_state)
        return None

    def transform_to_screen(self, transform: Transform, x: float, y: float) -> tuple[float, float]:
        """Transform data coordinates to screen coordinates."""
        if transform:
            return transform.data_to_screen(x, y)
        return (x, y)

    def transform_to_data(self, transform: Transform, x: float, y: float) -> tuple[float, float]:
        """Transform screen coordinates to data coordinates."""
        if transform:
            return transform.screen_to_data(x, y)
        return (x, y)

    def clear_transform_cache(self) -> None:
        """Clear the transform cache."""
        if self._transform_service:
            self._transform_service.clear_cache()

    # ==================== Data Service Methods ====================

    @property
    def data_service(self) -> DataService | None:
        """Get the data service instance."""
        return self._data_service

    def smooth_curve(
        self, data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]], window_size: int = 5
    ) -> list[tuple[int, float, float]] | list[tuple[int, float, float, str]]:
        """Apply smoothing to curve data."""
        if self._data_service:
            return self._data_service.smooth_moving_average(data, window_size)
        return data

    def filter_curve(self, data: list[tuple], filter_type: str = "median", param: int = 5) -> list[tuple]:
        """Apply filtering to curve data."""
        if self._data_service:
            if filter_type.lower() == "median":
                return self._data_service.filter_median(data, param)
            elif filter_type.lower() == "butterworth":
                return self._data_service.filter_butterworth(data, param / 100.0)
        return data

    def fill_gaps(self, data: list[tuple], max_gap: int = 10) -> list[tuple]:
        """Fill gaps in curve data."""
        if self._data_service:
            return self._data_service.fill_gaps(data, max_gap)
        return data

    def detect_outliers(self, data: list[tuple], threshold: float = 2.0) -> list[int]:
        """Detect outliers in curve data."""
        if self._data_service:
            return self._data_service.detect_outliers(data, threshold)
        return []

    def load_track_data(self, parent_widget: Any = None) -> list[tuple] | None:
        """Load track data from file."""
        widget = parent_widget or self.main_window
        if self._data_service and widget:
            return self._data_service.load_track_data(widget)
        elif self._file_service and widget:
            # Fallback to legacy service
            return self._file_service.load_track_data(widget)
        return None

    def save_track_data(self, data: list[tuple], parent_widget: Any = None) -> bool:
        """Save track data to file."""
        widget = parent_widget or self.main_window
        if self._data_service and widget:
            return self._data_service.save_track_data(widget, data)
        elif self._file_service and widget:
            # Fallback to legacy service
            return self._file_service.save_track_data(widget, data)
        return False

    def load_image_sequence(self, directory: str) -> list[str]:
        """Load image sequence from directory."""
        if self._data_service:
            return self._data_service.load_image_sequence(directory)
        return []

    # ==================== Interaction Service Methods ====================

    @property
    def interaction_service(self) -> InteractionService | None:
        """Get the interaction service instance."""
        return self._interaction_service

    def on_point_moved(self, idx: int, x: float, y: float) -> None:
        """Handle point moved event."""
        if self._interaction_service and self.main_window:
            self._interaction_service.on_point_moved(self.main_window, idx, x, y)

    def on_point_selected(self, curve_view: Any, idx: int) -> None:
        """Handle point selected event."""
        if self._interaction_service and self.main_window:
            self._interaction_service.on_point_selected(curve_view, self.main_window, idx)

    def handle_mouse_press(self, view: Any, event: Any) -> None:
        """Handle mouse press event."""
        if self._interaction_service:
            self._interaction_service.handle_mouse_press(view, event)

    def handle_mouse_move(self, view: Any, event: Any) -> None:
        """Handle mouse move event."""
        if self._interaction_service:
            self._interaction_service.handle_mouse_move(view, event)

    def handle_mouse_release(self, view: Any, event: Any) -> None:
        """Handle mouse release event."""
        if self._interaction_service:
            self._interaction_service.handle_mouse_release(view, event)

    def handle_wheel_event(self, view: Any, event: Any) -> None:
        """Handle mouse wheel event."""
        if self._interaction_service:
            self._interaction_service.handle_wheel_event(view, event)

    def handle_key_press(self, view: Any, event: Any) -> None:
        """Handle key press event."""
        if self._interaction_service:
            self._interaction_service.handle_key_press(view, event)

    def add_to_history(self) -> None:
        """Add current state to history."""
        if self._interaction_service and self.main_window:
            self._interaction_service.add_to_history(self.main_window)
        elif self._history_service and self.main_window:
            # Fallback to legacy service
            self._history_service.add_to_history(self.main_window)

    def undo(self) -> None:
        """Undo the last action."""
        if self._interaction_service and self.main_window:
            self._interaction_service.undo(self.main_window)
        elif self._history_service and self.main_window:
            # Fallback to legacy service
            self._history_service.undo(self.main_window)

    def redo(self) -> None:
        """Redo the previously undone action."""
        if self._interaction_service and self.main_window:
            self._interaction_service.redo(self.main_window)
        elif self._history_service and self.main_window:
            # Fallback to legacy service
            self._history_service.redo(self.main_window)

    # ==================== UI Service Methods ====================

    @property
    def ui_service(self) -> UIService | None:
        """Get the UI service instance."""
        return self._ui_service

    def show_error(self, message: str, parent: Any = None) -> None:
        """Show error message dialog."""
        widget = parent or self.main_window
        if self._ui_service and widget:
            self._ui_service.show_error(widget, message)

    def show_warning(self, message: str, parent: Any = None) -> None:
        """Show warning message dialog."""
        widget = parent or self.main_window
        if self._ui_service and widget:
            self._ui_service.show_warning(widget, message)

    def show_info(self, message: str, parent: Any = None) -> None:
        """Show information message dialog."""
        widget = parent or self.main_window
        if self._ui_service and widget:
            self._ui_service.show_info(widget, message)

    def confirm_action(self, message: str, parent: Any = None) -> bool:
        """Ask for confirmation from user."""
        widget = parent or self.main_window
        if self._ui_service and widget:
            return self._ui_service.confirm_action(widget, message)
        return False

    def get_smooth_window_size(self, parent: Any = None) -> int | None:
        """Get smoothing window size from user."""
        widget = parent or self.main_window
        if self._ui_service and widget:
            return self._ui_service.get_smooth_window_size(widget)
        return None

    def get_filter_params(self, parent: Any = None) -> tuple[str, int] | None:
        """Get filter parameters from user."""
        widget = parent or self.main_window
        if self._ui_service and widget:
            return self._ui_service.get_filter_params(widget)
        return None

    def set_status(self, message: str, timeout: int = 0) -> None:
        """Set status bar message."""
        if self._ui_service and self.main_window:
            self._ui_service.set_status(self.main_window, message, timeout)

    def clear_status(self) -> None:
        """Clear status bar message."""
        if self._ui_service and self.main_window:
            self._ui_service.clear_status(self.main_window)

    def update_ui_from_data(self) -> None:
        """Update UI components based on current data state."""
        if self._ui_service and self.main_window:
            self._ui_service.update_ui_from_data(self.main_window)

    # ==================== Convenience Methods ====================

    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available.

        Args:
            service_name: Name of the service to check

        Returns:
            True if the service is available, False otherwise
        """
        service_map = {
            "transform": self._transform_service,
            "data": self._data_service,
            "interaction": self._interaction_service,
            "ui": self._ui_service,
            # Legacy names
            "file": self._file_service,
            "history": self._history_service,
        }
        return service_map.get(service_name.lower()) is not None

    def get_available_services(self) -> list[str]:
        """Get list of available services.

        Returns:
            List of available service names
        """
        available = []
        if self._transform_service:
            available.append("transform")
        if self._data_service:
            available.append("data")
        if self._interaction_service:
            available.append("interaction")
        if self._ui_service:
            available.append("ui")
        return available

    def refresh_services(self) -> None:
        """Refresh service instances (useful after configuration changes)."""
        self._transform_service = get_transform_service() if get_transform_service else None
        self._data_service = get_data_service() if get_data_service else None
        self._interaction_service = get_interaction_service() if get_interaction_service else None
        self._ui_service = get_ui_service() if get_ui_service else None

        self.logger.info(f"Services refreshed. Available: {self.get_available_services()}")


# Module-level singleton instance
_facade_instance: ServiceFacade | None = None


def get_service_facade(main_window: Any = None) -> ServiceFacade:
    """Get or create the singleton ServiceFacade instance.

    Args:
        main_window: Optional main window reference

    Returns:
        The ServiceFacade singleton instance
    """
    global _facade_instance
    if _facade_instance is None:
        _facade_instance = ServiceFacade(main_window)
    elif main_window and _facade_instance.main_window != main_window:
        # Update main window reference if provided
        _facade_instance.main_window = main_window
    return _facade_instance
