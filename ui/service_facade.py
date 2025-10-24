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
from typing import TYPE_CHECKING, Protocol, cast

from core.image_state import ImageState
from core.logger_utils import get_logger
from core.type_aliases import CurveDataList
from protocols.ui import CurveViewProtocol, MainWindowProtocol

if TYPE_CHECKING:
    from services.data_service import DataService
    from services.interaction_service import InteractionService
    from services.transform_service import Transform, TransformService, ViewState
    from services.ui_service import UIService


if TYPE_CHECKING:
    from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
    from PySide6.QtWidgets import QWidget

    class WidgetProtocol(Protocol):
        """Protocol for Qt widget objects."""

        def __init__(self) -> None: ...

    class EventProtocol(Protocol):
        """Protocol for Qt event objects."""

        def __init__(self) -> None: ...


# Import the consolidated services
try:
    from services import get_transform_service
    from services.transform_service import Transform, TransformService, ViewState
except ImportError:
    if not TYPE_CHECKING:
        TransformService = None
        Transform = None
        ViewState = None
    get_transform_service = None

try:
    from services import get_data_service
    from services.data_service import DataService
except ImportError:
    if not TYPE_CHECKING:
        DataService = None
    get_data_service = None

try:
    from services import get_interaction_service
    from services.interaction_service import InteractionService
except ImportError:
    if not TYPE_CHECKING:
        InteractionService = None
    get_interaction_service = None

try:
    from services import get_ui_service
    from services.ui_service import UIService
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

    main_window: MainWindowProtocol | None
    logger: logging.Logger
    image_state: ImageState

    def __init__(self, main_window: MainWindowProtocol | None = None):
        """Initialize the service facade with consolidated services.

        Args:
            main_window: Optional reference to the main application window
        """
        self.main_window = main_window
        self.logger = get_logger("service_facade")

        # Initialize state management
        self.image_state = ImageState()

    # Service properties that always fetch fresh instances
    @property
    def _transform_service(self) -> TransformService | None:
        """Get the current transform service instance."""
        return get_transform_service() if get_transform_service else None

    @property
    def _data_service(self) -> DataService | None:
        """Get the current data service instance."""
        return get_data_service() if get_data_service else None

    @property
    def _interaction_service(self) -> InteractionService | None:
        """Get the current interaction service instance."""
        return get_interaction_service() if get_interaction_service else None

    @property
    def _ui_service(self) -> UIService | None:
        """Get the current UI service instance."""
        return get_ui_service() if get_ui_service else None  # pyright: ignore[reportPossiblyUnboundVariable]

    @property
    def _file_service(self) -> DataService | None:
        """Legacy service reference (FileService -> DataService)."""
        return self._data_service

    @property
    def _history_service(self) -> InteractionService | None:
        """Legacy service reference (HistoryService -> InteractionService)."""
        return self._interaction_service

    # ==================== Transform Service Methods ====================

    @property
    def transform_service(self) -> TransformService | None:
        """Get the transform service instance."""
        return self._transform_service

    def create_view_state(self, curve_view: CurveViewProtocol) -> ViewState | None:
        """Create a ViewState from a CurveView."""
        if self._transform_service:
            return self._transform_service.create_view_state(curve_view)
        return None

    def create_transform(self, view_state: ViewState) -> Transform | None:
        """Create a Transform from a ViewState."""
        if self._transform_service:
            return self._transform_service.create_transform_from_view_state(view_state)
        return None

    def get_transform(self, curve_view: CurveViewProtocol) -> Transform | None:
        """
        Get a Transform directly from a CurveView.

        Convenience method that combines create_view_state() and create_transform().

        Args:
            curve_view: The CurveView instance to create a transform for

        Returns:
            Transform instance or None if service unavailable
        """
        if self._transform_service:
            return self._transform_service.get_transform(curve_view)
        return None

    def transform_to_screen(self, transform: Transform | None, x: float, y: float) -> tuple[float, float]:
        """Transform data coordinates to screen coordinates.

        If transform is None, returns coordinates unchanged (identity transform).
        """
        if transform is None:
            return (x, y)
        return transform.data_to_screen(x, y)

    def transform_to_data(self, transform: Transform | None, x: float, y: float) -> tuple[float, float]:
        """Transform screen coordinates to data coordinates.

        If transform is None, returns coordinates unchanged (identity transform).
        """
        if transform is None:
            return (x, y)
        return transform.screen_to_data(x, y)

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
            from core.type_aliases import CurveDataList  # pyright: ignore[reportUnusedImport]

            # Convert to CurveDataList for service call
            curve_data = cast(CurveDataList, data)
            result = self._data_service.smooth_moving_average(curve_data, window_size)
            # Convert back to expected return type
            return cast(list[tuple[int, float, float]] | list[tuple[int, float, float, str]], result)
        return data

    def filter_curve(
        self,
        data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]],
        filter_type: str = "median",
        param: int = 5,
    ) -> list[tuple[int, float, float]] | list[tuple[int, float, float, str]]:
        """Apply filtering to curve data."""
        if self._data_service:
            from core.type_aliases import CurveDataList  # pyright: ignore[reportUnusedImport]

            # Convert to CurveDataList for service call
            curve_data = cast(CurveDataList, data)
            if filter_type.lower() == "median":
                result = self._data_service.filter_median(curve_data, param)
            elif filter_type.lower() == "butterworth":
                result = self._data_service.filter_butterworth(curve_data, param / 100.0)
            else:
                return data
            # Convert back to expected return type
            return cast(list[tuple[int, float, float]] | list[tuple[int, float, float, str]], result)
        return data

    def fill_gaps(
        self, data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]], max_gap: int = 10
    ) -> list[tuple[int, float, float]] | list[tuple[int, float, float, str]]:
        """Fill gaps in curve data."""
        if self._data_service:
            from core.type_aliases import CurveDataList  # pyright: ignore[reportUnusedImport]

            # Convert to CurveDataList for service call
            curve_data = cast(CurveDataList, data)
            result = self._data_service.fill_gaps(curve_data, max_gap)
            # Convert back to expected return type
            return cast(list[tuple[int, float, float]] | list[tuple[int, float, float, str]], result)
        return data

    def detect_outliers(
        self, data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]], threshold: float = 2.0
    ) -> list[int]:
        """Detect outliers in curve data."""
        if self._data_service:
            from core.type_aliases import CurveDataList  # pyright: ignore[reportUnusedImport]

            # Convert to CurveDataList for service call
            curve_data = cast(CurveDataList, data)
            return self._data_service.detect_outliers(curve_data, threshold)
        return []

    def analyze_curve_bounds(
        self, data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]]
    ) -> dict[str, object]:
        """Analyze curve data and return bounds information."""
        if self._data_service:
            from core.type_aliases import CurveDataList  # pyright: ignore[reportUnusedImport]

            # Convert to CurveDataList for service call
            curve_data = cast(CurveDataList, data)
            return self._data_service.analyze_points(curve_data)
        return {
            "count": 0,
            "min_frame": 0,
            "max_frame": 0,
            "bounds": {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0},
        }

    def load_track_data(
        self, parent_widget: WidgetProtocol | None = None
    ) -> list[tuple[int, float, float]] | list[tuple[int, float, float, str]] | None:
        """Load track data from file."""
        widget = parent_widget or self.main_window
        if self._data_service and widget:
            # Cast protocol to QWidget for service compatibility
            result = self._data_service.load_track_data(cast("QWidget", widget))
            return cast(list[tuple[int, float, float]] | list[tuple[int, float, float, str]] | None, result)
        elif self._file_service and widget:
            # Fallback to legacy service
            result = self._file_service.load_track_data(cast("QWidget", widget))
            return cast(list[tuple[int, float, float]] | list[tuple[int, float, float, str]] | None, result)
        return None

    def load_track_data_from_file(
        self, file_path: str
    ) -> list[tuple[int, float, float]] | list[tuple[int, float, float, str]] | None:
        """Load track data from a specific file path.

        Args:
            file_path: Path to the file to load

        Returns:
            Track data or None if loading fails
        """
        if self._data_service:
            # Determine file type and load appropriately
            if file_path.endswith(".json"):
                result = self._data_service.load_json(file_path)
                return cast(list[tuple[int, float, float]] | list[tuple[int, float, float, str]] | None, result)
            elif file_path.endswith(".csv"):
                result = self._data_service.load_csv(file_path)
                return cast(list[tuple[int, float, float]] | list[tuple[int, float, float, str]] | None, result)
            elif file_path.endswith(".txt"):
                result = self._data_service.load_2dtrack_data(file_path)
                return cast(list[tuple[int, float, float]] | list[tuple[int, float, float, str]] | None, result)
        return None

    def save_track_data(
        self,
        data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]],
        parent_widget: WidgetProtocol | None = None,
    ) -> bool:
        """Save track data to file."""
        widget = parent_widget or self.main_window
        if self._data_service and widget:
            # Cast protocol to QWidget and data to CurveDataList for service compatibility
            return self._data_service.save_track_data(cast("QWidget", widget), cast("CurveDataList", data))
        elif self._file_service and widget:
            # Fallback to legacy service
            return self._file_service.save_track_data(cast("QWidget", widget), cast("CurveDataList", data))
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

    def on_point_selected(self, curve_view: CurveViewProtocol, idx: int) -> None:
        """Handle point selected event."""
        if self._interaction_service and self.main_window:
            self._interaction_service.on_point_selected(curve_view, self.main_window, idx)

    def handle_mouse_press(self, view: CurveViewProtocol, event: EventProtocol) -> None:
        """Handle mouse press event."""
        if self._interaction_service:
            self._interaction_service.handle_mouse_press(view, cast("QMouseEvent", cast(object, event)))

    def handle_mouse_move(self, view: CurveViewProtocol, event: EventProtocol) -> None:
        """Handle mouse move event."""
        if self._interaction_service:
            self._interaction_service.handle_mouse_move(view, cast("QMouseEvent", cast(object, event)))

    def handle_mouse_release(self, view: CurveViewProtocol, event: EventProtocol) -> None:
        """Handle mouse release event."""
        if self._interaction_service:
            self._interaction_service.handle_mouse_release(view, cast("QMouseEvent", cast(object, event)))

    def handle_wheel_event(self, view: CurveViewProtocol, event: EventProtocol) -> None:
        """Handle mouse wheel event."""
        if self._interaction_service:
            self._interaction_service.handle_wheel_event(view, cast("QWheelEvent", cast(object, event)))

    def handle_key_press(self, view: CurveViewProtocol, event: EventProtocol) -> None:
        """Handle key press event."""
        if self._interaction_service:
            self._interaction_service.handle_key_press(view, cast("QKeyEvent", cast(object, event)))

    def add_to_history(self) -> None:
        """Add current state to history."""
        if self._interaction_service and self.main_window:
            self._interaction_service.add_to_history(self.main_window)
        elif self._history_service and self.main_window:
            # Fallback to legacy service
            self._history_service.add_to_history(self.main_window)

    def undo(self) -> None:
        """Undo the last action."""
        self.logger.info(
            (
                f"ServiceFacade.undo called - interaction_service: {self._interaction_service is not None}, "
                f"main_window: {self.main_window is not None}"
            )
        )
        if self._interaction_service and self.main_window:
            self.logger.info("Calling interaction_service.undo")
            self._interaction_service.undo(self.main_window)
        elif self._history_service and self.main_window:
            # Fallback to legacy service
            self.logger.info("Calling legacy history_service.undo")
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

    def show_error(self, message: str, parent: WidgetProtocol | None = None) -> None:
        """Show error message dialog."""
        widget = parent or self.main_window
        if self._ui_service and widget:
            self._ui_service.show_error(cast("QWidget", widget), message)

    def show_warning(self, message: str, parent: WidgetProtocol | None = None) -> None:
        """Show warning message dialog."""
        widget = parent or self.main_window
        if self._ui_service and widget:
            self._ui_service.show_warning(cast("QWidget", widget), message)

    def show_info(self, message: str, parent: WidgetProtocol | None = None) -> None:
        """Show information message dialog."""
        widget = parent or self.main_window
        if self._ui_service and widget:
            self._ui_service.show_info(cast("QWidget", widget), message)

    def confirm_action(self, message: str, parent: WidgetProtocol | None = None) -> bool:
        """Ask for confirmation from user."""
        widget = parent or self.main_window
        if self._ui_service and widget:
            return self._ui_service.confirm_action(cast("QWidget", widget), message)
        return False

    def get_smooth_window_size(self, parent: WidgetProtocol | None = None) -> int | None:
        """Get smoothing window size from user."""
        widget = parent or self.main_window
        if self._ui_service and widget:
            return self._ui_service.get_smooth_window_size(cast("QWidget", widget))
        return None

    def get_filter_params(self, parent: WidgetProtocol | None = None) -> tuple[str, int] | None:
        """Get filter parameters from user."""
        widget = parent or self.main_window
        if self._ui_service and widget:
            return self._ui_service.get_filter_params(cast("QWidget", widget))
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
        # Services are already refreshed automatically via @property getters
        # No caching needed - each property fetches the current service instance
        self.logger.info(f"Services refreshed. Available: {self.get_available_services()}")


# Module-level singleton instance
_facade_instance: ServiceFacade | None = None


def get_service_facade(main_window: MainWindowProtocol | None = None) -> ServiceFacade:
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


def reset_service_facade() -> None:
    """Reset the ServiceFacade singleton (for testing).

    This clears the cached facade instance, allowing tests to start fresh.
    """
    global _facade_instance
    _facade_instance = None
