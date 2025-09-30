"""Controller for point editing operations in the curve editor.

This controller extracts point manipulation logic from MainWindow to improve
separation of concerns and enable command pattern integration.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class PointEditController:
    """Manages point editing operations for the curve editor."""

    def __init__(self, main_window: "MainWindow"):
        """Initialize the point edit controller.

        Args:
            main_window: Reference to the main window
        """
        self.main_window = main_window
        self._last_selected_index: int | None = None
        self._command_manager: Any | None = None  # Will be set when integrated

    def set_command_manager(self, command_manager: Any) -> None:
        """Set the command manager for undoable operations.

        Args:
            command_manager: The command manager instance
        """
        self._command_manager = command_manager

    def on_point_selected(self, index: int) -> None:
        """Handle point selection with error boundaries.

        Args:
            index: Index of the selected point
        """
        try:
            logger.debug(f"Point selected: index={index}")

            # Store last selection for recovery
            self._last_selected_index = index

            # Update UI components
            self._update_point_editor(index)
            self._update_selection_display(index)

            # Sync with tracking panel if available
            self._sync_tracking_panel_selection(index)

            # Update status
            self.main_window.update_status(f"Selected point at index {index}")

        except Exception as e:
            logger.error(f"Error handling point selection: {e}")
            self._handle_selection_error("select point")

    def on_point_moved(self, index: int, x: float, y: float) -> None:
        """Handle point movement with error boundaries.

        Args:
            index: Index of the moved point
            x: New X coordinate
            y: New Y coordinate
        """
        try:
            logger.debug(f"Point moved: index={index}, x={x:.2f}, y={y:.2f}")

            # Validate coordinates
            if not self._validate_coordinates(x, y):
                logger.warning(f"Invalid coordinates for point move: x={x}, y={y}")
                return

            # Update the point (this would be done through a command in full implementation)
            self._update_point_position(index, x, y)

            # Mark as modified
            if hasattr(self.main_window, "state_manager"):
                self.main_window.state_manager.is_modified = True

            # Update status
            self.main_window.update_status(f"Moved point {index} to ({x:.2f}, {y:.2f})")

        except Exception as e:
            logger.error(f"Error handling point movement: {e}")
            self._handle_edit_error("move point")

    def on_point_x_changed(self, value: float) -> None:
        """Handle X coordinate change from spinbox with error boundaries.

        Args:
            value: New X coordinate value
        """
        try:
            if not hasattr(self.main_window, "curve_widget") or not self.main_window.curve_widget:
                return

            selected_indices = self.main_window.curve_widget.selected_indices
            if not selected_indices:
                return

            # Update the selected point's X coordinate
            for index in selected_indices:
                self._update_point_x(index, value)

            # Mark as modified
            if hasattr(self.main_window, "state_manager"):
                self.main_window.state_manager.is_modified = True

            self.main_window.curve_widget.update()

        except Exception as e:
            logger.error(f"Error updating point X coordinate: {e}")
            self._handle_edit_error("update X coordinate")

    def on_point_y_changed(self, value: float) -> None:
        """Handle Y coordinate change from spinbox with error boundaries.

        Args:
            value: New Y coordinate value
        """
        try:
            if not hasattr(self.main_window, "curve_widget") or not self.main_window.curve_widget:
                return

            selected_indices = self.main_window.curve_widget.selected_indices
            if not selected_indices:
                return

            # Update the selected point's Y coordinate
            for index in selected_indices:
                self._update_point_y(index, value)

            # Mark as modified
            if hasattr(self.main_window, "state_manager"):
                self.main_window.state_manager.is_modified = True

            self.main_window.curve_widget.update()

        except Exception as e:
            logger.error(f"Error updating point Y coordinate: {e}")
            self._handle_edit_error("update Y coordinate")

    def delete_selected_points(self) -> None:
        """Delete currently selected points with error boundaries."""
        try:
            if not hasattr(self.main_window, "curve_widget") or not self.main_window.curve_widget:
                logger.warning("No curve widget available")
                return

            selected_indices = self.main_window.curve_widget.selected_indices
            if not selected_indices:
                logger.info("No points selected for deletion")
                return

            # Store current data for undo
            curve_data = getattr(self.main_window.curve_widget, "curve_data", [])
            if not curve_data:
                return

            # Delete points (in reverse order to maintain indices)
            new_data = list(curve_data)
            for index in sorted(selected_indices, reverse=True):
                if 0 <= index < len(new_data):
                    del new_data[index]

            # Apply changes
            self.main_window.curve_widget.set_curve_data(new_data)
            self.main_window.curve_widget.selected_indices = set()

            # Mark as modified
            if hasattr(self.main_window, "state_manager"):
                self.main_window.state_manager.is_modified = True

            # Update UI
            self.main_window.curve_widget.update()
            self.main_window.update_status(f"Deleted {len(selected_indices)} points")

            logger.info(f"Deleted {len(selected_indices)} points")

        except Exception as e:
            logger.error(f"Error deleting points: {e}")
            self._handle_edit_error("delete points")

    def add_point(self, frame: int, x: float, y: float) -> None:
        """Add a new point with error boundaries.

        Args:
            frame: Frame number for the point
            x: X coordinate
            y: Y coordinate
        """
        try:
            if not hasattr(self.main_window, "curve_widget") or not self.main_window.curve_widget:
                logger.warning("No curve widget available")
                return

            # Validate input
            if not self._validate_coordinates(x, y):
                logger.warning(f"Invalid coordinates for new point: x={x}, y={y}")
                return

            # Get current data
            curve_data = getattr(self.main_window.curve_widget, "curve_data", [])
            new_data = list(curve_data)

            # Add new point
            new_point = (frame, x, y)
            new_data.append(new_point)

            # Sort by frame
            new_data.sort(key=lambda p: p[0])

            # Apply changes
            self.main_window.curve_widget.set_curve_data(new_data)

            # Mark as modified
            if hasattr(self.main_window, "state_manager"):
                self.main_window.state_manager.is_modified = True

            # Update UI
            self.main_window.curve_widget.update()
            self.main_window.update_status(f"Added point at frame {frame}")

            logger.info(f"Added point at frame {frame}: ({x:.2f}, {y:.2f})")

        except Exception as e:
            logger.error(f"Error adding point: {e}")
            self._handle_edit_error("add point")

    # Private helper methods

    def _update_point_editor(self, index: int) -> None:
        """Update point editor spinboxes with selected point values.

        Args:
            index: Index of the selected point
        """
        if not hasattr(self.main_window, "curve_widget") or not self.main_window.curve_widget:
            return

        curve_data = getattr(self.main_window.curve_widget, "curve_data", [])
        if 0 <= index < len(curve_data):
            point = curve_data[index]
            frame, x, y = point[:3]

            # Update spinboxes if they exist - check correct UI location
            ui_point_edit = getattr(self.main_window, "ui", None)
            if ui_point_edit:
                ui_point_edit = getattr(ui_point_edit, "point_edit", None)
                if ui_point_edit:
                    point_x_spinbox = getattr(ui_point_edit, "point_x_spinbox", None)
                    if point_x_spinbox:
                        point_x_spinbox.blockSignals(True)
                        point_x_spinbox.setValue(x)
                        point_x_spinbox.blockSignals(False)

                    point_y_spinbox = getattr(ui_point_edit, "point_y_spinbox", None)
                    if point_y_spinbox:
                        point_y_spinbox.blockSignals(True)
                        point_y_spinbox.setValue(y)
                        point_y_spinbox.blockSignals(False)

            # Fallback: also check direct attributes for backward compatibility
            if hasattr(self.main_window, "point_x_spinbox") and self.main_window.point_x_spinbox:
                self.main_window.point_x_spinbox.blockSignals(True)
                self.main_window.point_x_spinbox.setValue(x)
                self.main_window.point_x_spinbox.blockSignals(False)

            if hasattr(self.main_window, "point_y_spinbox") and self.main_window.point_y_spinbox:
                self.main_window.point_y_spinbox.blockSignals(True)
                self.main_window.point_y_spinbox.setValue(y)
                self.main_window.point_y_spinbox.blockSignals(False)

    def _update_selection_display(self, index: int) -> None:
        """Update selection display label.

        Args:
            index: Index of the selected point
        """
        if hasattr(self.main_window, "selected_point_label") and self.main_window.selected_point_label:
            self.main_window.selected_point_label.setText(f"Selected: Point {index}")

    def _sync_tracking_panel_selection(self, index: int) -> None:
        """Sync selection with tracking panel.

        Args:
            index: Index of the selected point
        """
        # This would sync with tracking panel if needed
        pass

    def _validate_coordinates(self, x: float, y: float) -> bool:
        """Validate point coordinates.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if coordinates are valid
        """
        import math

        # Check for NaN or Infinity
        if not math.isfinite(x) or not math.isfinite(y):
            return False

        # Add any domain-specific validation here
        return True

    def _update_point_position(self, index: int, x: float, y: float) -> None:
        """Update a point's position.

        Args:
            index: Point index
            x: New X coordinate
            y: New Y coordinate
        """
        if not hasattr(self.main_window, "curve_widget") or not self.main_window.curve_widget:
            return

        curve_data = getattr(self.main_window.curve_widget, "curve_data", [])
        if 0 <= index < len(curve_data):
            new_data = list(curve_data)
            old_point = new_data[index]
            frame = old_point[0]
            status = old_point[3] if len(old_point) > 3 else None

            if status:
                new_data[index] = (frame, x, y, status)
            else:
                new_data[index] = (frame, x, y)

            self.main_window.curve_widget.set_curve_data(new_data)
            self.main_window.curve_widget.update()

    def _update_point_x(self, index: int, x: float) -> None:
        """Update a point's X coordinate.

        Args:
            index: Point index
            x: New X coordinate
        """
        if not hasattr(self.main_window, "curve_widget") or not self.main_window.curve_widget:
            return

        curve_data = getattr(self.main_window.curve_widget, "curve_data", [])
        if 0 <= index < len(curve_data):
            point = curve_data[index]
            self._update_point_position(index, x, point[1])

    def _update_point_y(self, index: int, y: float) -> None:
        """Update a point's Y coordinate.

        Args:
            index: Point index
            y: New Y coordinate
        """
        if not hasattr(self.main_window, "curve_widget") or not self.main_window.curve_widget:
            return

        curve_data = getattr(self.main_window.curve_widget, "curve_data", [])
        if 0 <= index < len(curve_data):
            point = curve_data[index]
            self._update_point_position(index, point[0], y)

    def _handle_selection_error(self, operation: str) -> None:
        """Handle selection operation errors.

        Args:
            operation: The operation that failed
        """
        error_msg = f"Failed to {operation}"
        logger.error(error_msg)

        # Update status bar
        if hasattr(self.main_window, "statusBar"):
            self.main_window.statusBar().showMessage(error_msg, 3000)

        # Try to recover last selection
        if self._last_selected_index is not None:
            try:
                if hasattr(self.main_window, "curve_widget") and self.main_window.curve_widget:
                    self.main_window.curve_widget.selected_indices = {self._last_selected_index}
                    self.main_window.curve_widget.update()
            except Exception:
                pass

    def _handle_edit_error(self, operation: str) -> None:
        """Handle edit operation errors with graceful degradation.

        Args:
            operation: The operation that failed
        """
        error_msg = f"Failed to {operation}"
        logger.error(error_msg)

        # Update status bar
        if hasattr(self.main_window, "statusBar"):
            self.main_window.statusBar().showMessage(error_msg, 3000)

        # Refresh the view to ensure consistency
        try:
            if hasattr(self.main_window, "curve_widget") and self.main_window.curve_widget:
                self.main_window.curve_widget.update()
        except Exception:
            pass
