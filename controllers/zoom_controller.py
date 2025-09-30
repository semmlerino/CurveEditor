"""Controller for zoom operations in the curve editor.

This controller extracts zoom-related logic from MainWindow to improve
separation of concerns and reduce MainWindow complexity.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class ZoomController:
    """Manages zoom operations for the curve editor."""

    ZOOM_FACTOR = 1.2
    MIN_ZOOM = 0.1
    MAX_ZOOM = 10.0
    DEFAULT_ZOOM = 1.0

    def __init__(self, main_window: "MainWindow"):
        """Initialize the zoom controller.

        Args:
            main_window: Reference to the main window
        """
        self.main_window = main_window
        self._last_zoom_level = self.DEFAULT_ZOOM

    def zoom_in(self) -> None:
        """Handle zoom in action with error boundaries."""
        try:
            if self.main_window.curve_widget:
                # Let curve widget handle zooming directly
                current_zoom = self.main_window.curve_widget.zoom_factor
                new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, current_zoom * self.ZOOM_FACTOR))

                # Apply zoom with error handling
                self._apply_zoom(new_zoom)

                logger.debug(f"Zoomed in from {current_zoom:.2f} to {new_zoom:.2f}")
            else:
                # Fallback to state manager
                self._zoom_in_fallback()

            self.update_zoom_label()

        except Exception as e:
            logger.error(f"Error during zoom in: {e}")
            self._handle_zoom_error("zoom in")

    def zoom_out(self) -> None:
        """Handle zoom out action with error boundaries."""
        try:
            if self.main_window.curve_widget:
                # Let curve widget handle zooming directly
                current_zoom = self.main_window.curve_widget.zoom_factor
                new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, current_zoom / self.ZOOM_FACTOR))

                # Apply zoom with error handling
                self._apply_zoom(new_zoom)

                logger.debug(f"Zoomed out from {current_zoom:.2f} to {new_zoom:.2f}")
            else:
                # Fallback to state manager
                self._zoom_out_fallback()

            self.update_zoom_label()

        except Exception as e:
            logger.error(f"Error during zoom out: {e}")
            self._handle_zoom_error("zoom out")

    def reset_view(self) -> None:
        """Reset the view to default zoom and pan with error boundaries."""
        try:
            if self.main_window.curve_widget:
                # Store current state for potential recovery
                self._store_current_zoom()

                # Reset zoom
                self.main_window.curve_widget.zoom_factor = self.DEFAULT_ZOOM

                # Reset pan
                self.main_window.curve_widget.pan_offset_x = 0.0
                self.main_window.curve_widget.pan_offset_y = 0.0

                # Invalidate caches and update
                self.main_window.curve_widget.invalidate_caches()
                self.main_window.curve_widget.update()

                # Emit signal
                self.main_window.curve_widget.zoom_changed.emit(self.DEFAULT_ZOOM)

                logger.info("View reset to default")
            else:
                # Fallback to state manager
                self._reset_view_fallback()

            self.update_zoom_label()
            self.main_window.update_status("View reset")

        except Exception as e:
            logger.error(f"Error during view reset: {e}")
            self._handle_zoom_error("reset view")
            # Try to recover to last known good state
            self._recover_zoom_state()

    def set_zoom(self, zoom_level: float) -> None:
        """Set zoom to a specific level with validation.

        Args:
            zoom_level: The zoom level to set
        """
        try:
            # Validate zoom level
            zoom_level = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom_level))

            if self.main_window.curve_widget:
                self._apply_zoom(zoom_level)
            else:
                self._set_zoom_fallback(zoom_level)

            self.update_zoom_label()

        except Exception as e:
            logger.error(f"Error setting zoom to {zoom_level}: {e}")
            self._handle_zoom_error("set zoom")

    def get_current_zoom(self) -> float:
        """Get the current zoom level.

        Returns:
            Current zoom factor
        """
        try:
            if self.main_window.curve_widget:
                return self.main_window.curve_widget.zoom_factor
            else:
                return self.main_window.state_manager.zoom_level
        except Exception:
            logger.warning("Could not get zoom level, returning default")
            return self.DEFAULT_ZOOM

    def update_zoom_label(self) -> None:
        """Update the zoom label in the UI."""
        try:
            zoom_level = self.get_current_zoom()
            zoom_percentage = int(zoom_level * 100)

            if hasattr(self.main_window, "zoom_label") and self.main_window.zoom_label:
                self.main_window.zoom_label.setText(f"Zoom: {zoom_percentage}%")

        except Exception as e:
            logger.error(f"Error updating zoom label: {e}")

    # Private helper methods

    def _apply_zoom(self, new_zoom: float) -> None:
        """Apply zoom to curve widget with error handling.

        Args:
            new_zoom: The new zoom level to apply
        """
        if not self.main_window.curve_widget:
            return

        # Store current zoom for recovery
        self._store_current_zoom()

        # Apply new zoom
        self.main_window.curve_widget.zoom_factor = new_zoom
        self.main_window.curve_widget.invalidate_caches()
        self.main_window.curve_widget.update()
        self.main_window.curve_widget.zoom_changed.emit(new_zoom)

    def _zoom_in_fallback(self) -> None:
        """Fallback zoom in using state manager."""
        if hasattr(self.main_window, "state_manager"):
            current_zoom = self.main_window.state_manager.zoom_level
            self.main_window.state_manager.zoom_level = current_zoom * self.ZOOM_FACTOR

    def _zoom_out_fallback(self) -> None:
        """Fallback zoom out using state manager."""
        if hasattr(self.main_window, "state_manager"):
            current_zoom = self.main_window.state_manager.zoom_level
            self.main_window.state_manager.zoom_level = current_zoom / self.ZOOM_FACTOR

    def _reset_view_fallback(self) -> None:
        """Fallback view reset using state manager."""
        if hasattr(self.main_window, "state_manager"):
            self.main_window.state_manager.zoom_level = self.DEFAULT_ZOOM
            # Note: pan_x and pan_y are managed by the curve_widget, not state_manager

    def _set_zoom_fallback(self, zoom_level: float) -> None:
        """Fallback zoom set using state manager.

        Args:
            zoom_level: The zoom level to set
        """
        if hasattr(self.main_window, "state_manager"):
            self.main_window.state_manager.zoom_level = zoom_level

    def _store_current_zoom(self) -> None:
        """Store current zoom level for recovery."""
        try:
            self._last_zoom_level = self.get_current_zoom()
        except Exception:
            self._last_zoom_level = self.DEFAULT_ZOOM

    def _recover_zoom_state(self) -> None:
        """Attempt to recover to last known good zoom state."""
        try:
            if self.main_window.curve_widget:
                self.main_window.curve_widget.zoom_factor = self._last_zoom_level
                self.main_window.curve_widget.update()
                logger.info(f"Recovered zoom to {self._last_zoom_level:.2f}")
        except Exception as e:
            logger.error(f"Failed to recover zoom state: {e}")

    def _handle_zoom_error(self, operation: str) -> None:
        """Handle zoom operation errors with user feedback.

        Args:
            operation: The operation that failed
        """
        error_msg = f"Failed to {operation}"
        logger.error(error_msg)

        # Update status bar with error
        if hasattr(self.main_window, "statusBar"):
            self.main_window.statusBar().showMessage(error_msg, 3000)

    def fit_to_window(self) -> None:
        """Fit the curve view to the window size."""
        try:
            if not self.main_window.curve_widget:
                logger.warning("No curve widget available for fit to window")
                return

            # Get curve bounds
            curve_data = getattr(self.main_window.curve_widget, "curve_data", [])
            if not curve_data:
                logger.info("No curve data to fit")
                return

            # Calculate bounds
            min_x = min(point[0] for point in curve_data)
            max_x = max(point[0] for point in curve_data)
            min_y = min(point[1] for point in curve_data)
            max_y = max(point[1] for point in curve_data)

            # Get widget size
            widget_width = self.main_window.curve_widget.width()
            widget_height = self.main_window.curve_widget.height()

            if widget_width <= 0 or widget_height <= 0:
                logger.warning("Invalid widget dimensions for fit to window")
                return

            # Calculate required zoom
            data_width = max_x - min_x
            data_height = max_y - min_y

            if data_width <= 0 or data_height <= 0:
                logger.warning("Invalid data dimensions for fit to window")
                return

            # Calculate zoom to fit with some margin
            margin = 0.9  # 90% of window size
            zoom_x = (widget_width * margin) / data_width
            zoom_y = (widget_height * margin) / data_height
            new_zoom = min(zoom_x, zoom_y, self.MAX_ZOOM)
            new_zoom = max(new_zoom, self.MIN_ZOOM)

            # Apply zoom and center
            self._apply_zoom(new_zoom)

            # Center the view
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            self.main_window.curve_widget.pan_offset_x = widget_width / 2 - center_x * new_zoom
            self.main_window.curve_widget.pan_offset_y = widget_height / 2 - center_y * new_zoom

            self.main_window.curve_widget.update()
            self.update_zoom_label()
            self.main_window.update_status("Fit to window")

            logger.info(f"Fit to window with zoom {new_zoom:.2f}")

        except Exception as e:
            logger.error(f"Error fitting to window: {e}")
            self._handle_zoom_error("fit to window")
