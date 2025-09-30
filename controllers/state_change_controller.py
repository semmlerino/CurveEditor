"""
State change controller for managing various state change events.

This controller handles state changes like selection changes, view state changes,
and undo/redo operations, reducing MainWindow complexity.
"""

import logging
from typing import TYPE_CHECKING

from protocols.ui import MainWindowProtocol

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class StateChangeController:
    """Controller for state change operations."""

    def __init__(self, main_window: "MainWindow"):
        """Initialize the state change controller.

        Args:
            main_window: Reference to the main window
        """
        self.main_window: MainWindowProtocol = main_window

    def handle_modified_changed(self, modified: bool) -> None:
        """Handle modification status changes.

        Args:
            modified: New modification status
        """
        self.main_window.setWindowTitle(self.main_window.state_manager.get_window_title())
        if modified:
            logger.debug("Document marked as modified")

    def handle_selection_changed(self, indices: list[int]) -> None:
        """Handle curve point selection changes.

        Args:
            indices: List of selected point indices
        """
        # Update selection labels through ViewUpdateManager
        self.main_window.view_update_manager.update_selection_labels(indices)  # pyright: ignore[reportAttributeAccessIssue]

        count = len(indices)
        if count == 1:
            # Get actual point data from curve widget
            idx = indices[0]
            if self.main_window.curve_widget and idx < len(self.main_window.curve_widget.curve_data):  # pyright: ignore[reportAttributeAccessIssue]
                point_data = self.main_window.curve_widget.curve_data[idx]  # pyright: ignore[reportAttributeAccessIssue]
                from core.point_types import safe_extract_point

                frame, x, y, _ = safe_extract_point(point_data)

                # Update spinboxes with actual values
                self.main_window.view_update_manager.update_point_spinboxes(x, y, enabled=True)  # pyright: ignore[reportAttributeAccessIssue]

                # Connect spinbox changes to update point
                if getattr(self.main_window, "_point_spinbox_connected", False) is False:
                    self.main_window.view_update_manager.connect_point_spinbox_handlers(  # pyright: ignore[reportAttributeAccessIssue]
                        self.main_window._on_point_x_changed, self.main_window._on_point_y_changed
                    )
                    self.main_window._point_spinbox_connected = True
        else:
            # Disable spinboxes for multiple or no selection
            self.main_window.view_update_manager.update_point_spinboxes(enabled=False)  # pyright: ignore[reportAttributeAccessIssue]

    def handle_view_state_changed(self) -> None:
        """Handle view state changes (zoom, pan, etc)."""
        logger.debug("View state changed")
        # Update UI state when view changes
        self.main_window.update_ui_state()

    def handle_curve_selection_changed(self, indices: list[int]) -> None:
        """Handle curve selection changes from the curve widget.

        Args:
            indices: List of selected curve indices
        """
        logger.debug(f"Curve selection changed: {indices}")
        # Update state manager with new selection using proper method
        self.main_window.state_manager.set_selected_points(indices)

    def handle_curve_view_changed(self) -> None:
        """Handle curve view changes."""
        logger.debug("Curve view changed")
        # Update curve view options when view changes
        self.main_window.update_curve_view_options()

    def handle_curve_zoom_changed(self, zoom: float) -> None:
        """Handle curve zoom level changes.

        Args:
            zoom: New zoom level
        """
        logger.debug(f"Curve zoom changed to: {zoom}")
        # Update zoom label in status bar
        if hasattr(self.main_window.view_update_manager, "update_zoom_label"):
            self.main_window.view_update_manager.update_zoom_label()  # pyright: ignore[reportAttributeAccessIssue]

    def handle_state_frame_changed(self, frame: int) -> None:
        """Handle frame changes from state manager.

        Args:
            frame: New frame number
        """
        logger.debug(f"State frame changed to: {frame}")
        # This is typically handled by frame navigation controller
        # but we log it here for debugging

    def handle_action_undo(self) -> None:
        """Handle undo action."""
        logger.debug("Undo action triggered")
        self.main_window.state_manager.undo()
        # Update UI after undo
        self.main_window.update_ui_state()
        if self.main_window.curve_widget:
            self.main_window.curve_widget.update()  # pyright: ignore[reportAttributeAccessIssue]

    def handle_action_redo(self) -> None:
        """Handle redo action."""
        logger.debug("Redo action triggered")
        self.main_window.state_manager.redo()
        # Update UI after redo
        self.main_window.update_ui_state()
        if self.main_window.curve_widget:
            self.main_window.curve_widget.update()  # pyright: ignore[reportAttributeAccessIssue]
