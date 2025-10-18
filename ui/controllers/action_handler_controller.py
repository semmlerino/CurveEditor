#!/usr/bin/env python
"""
Action Handler Controller for CurveEditor.

This controller manages all action-related functionality that was previously
handled directly in MainWindow. It maintains exact compatibility with the
existing ShortcutManager connections and behavior.
"""

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Slot  # pyright: ignore[reportUnknownVariableType]

from core.type_aliases import CurveDataList
from protocols.ui import MainWindowProtocol
from services import get_data_service

if TYPE_CHECKING:
    from ui.main_window import MainWindow
    from ui.state_manager import StateManager

from core.logger_utils import get_logger

logger = get_logger("action_handler_controller")


class ActionHandlerController:
    """
    Controller for handling all UI actions (file, edit, view, curve operations).

    Extracted from MainWindow to reduce complexity while maintaining exact
    compatibility with existing ShortcutManager connections.
    """

    def __init__(self, state_manager: "StateManager", main_window: "MainWindow"):
        """
        Initialize the action handler controller.

        Args:
            state_manager: Reference to the application state manager
            main_window: Reference to the main window for UI access
        """
        self.state_manager: StateManager = state_manager
        self.main_window: MainWindow = main_window

        logger.info("ActionHandlerController initialized")

    # ==================== File Action Handlers ====================

    @Slot()
    def _on_action_new(self) -> None:
        """Handle new file action."""
        if self.main_window.file_operations.new_file():
            # Clear curve widget data
            if self.main_window.curve_widget:
                self.main_window.curve_widget.set_curve_data([])
                self.main_window.update_tracking_panel()

            self.state_manager.reset_to_defaults()
            self.main_window.update_ui_state()
            if self.main_window.status_label:
                self.main_window.status_label.setText("New curve created")

    @Slot()
    def _on_action_open(self) -> None:
        """Handle open file action."""
        data = self.main_window.file_operations.open_file(self.main_window)

        if data:
            # Check if it's multi-point data
            if isinstance(data, dict):
                # Successfully loaded multi-point data - delegate to tracking controller
                self.main_window.tracking_controller.on_multi_point_data_loaded(data)
            else:
                # Single curve data - also delegate to tracking controller for proper merging
                self.main_window.tracking_controller.on_tracking_data_loaded(data)  # pyright: ignore[reportArgumentType]

                # Update timeline tabs with frame range and point data
                self.main_window.update_timeline_tabs(data)

            self.main_window.update_ui_state()
            if self.main_window.status_label:
                self.main_window.status_label.setText("File loaded successfully")

    @Slot()
    def _on_action_save(self) -> None:
        """Handle save file action."""
        data = self._get_current_curve_data()
        if self.main_window.file_operations.save_file(data):
            if self.main_window.status_label:
                self.main_window.status_label.setText("File saved successfully")

    @Slot()
    def _on_action_save_as(self) -> None:
        """Handle save as action."""
        data = self._get_current_curve_data()
        if self.main_window.file_operations.save_file_as(data, self.main_window):
            if self.main_window.status_label:
                self.main_window.status_label.setText("File saved successfully")

    @Slot()
    def _on_load_images(self) -> None:
        """Handle load background images action."""
        if self.main_window.file_operations.load_images(self.main_window):
            if self.main_window.status_label:
                self.main_window.status_label.setText("Images loaded successfully")

    @Slot()
    def _on_export_data(self) -> None:
        """Handle export curve data action."""
        data = self._get_current_curve_data()
        if self.main_window.file_operations.export_data(data, self.main_window):
            if self.main_window.status_label:
                self.main_window.status_label.setText("Data exported successfully")

    # ==================== Edit Action Handlers ====================

    @Slot()
    def _on_action_undo(self) -> None:
        """Handle undo action."""
        logger.info("ActionHandlerController._on_action_undo called")
        self.main_window.services.undo()
        if self.main_window.status_label:
            self.main_window.status_label.setText("Undo")

    @Slot()
    def _on_action_redo(self) -> None:
        """Handle redo action."""
        self.main_window.services.redo()
        if self.main_window.status_label:
            self.main_window.status_label.setText("Redo")

    @Slot()
    def _on_select_all(self) -> None:
        """Handle select all action."""
        if self.main_window.curve_widget:
            self.main_window.curve_widget.select_all()
            if self.main_window.status_label:
                self.main_window.status_label.setText("All points selected")

    @Slot()
    def _on_add_point(self) -> None:
        """Handle add point action."""
        # TODO: Implement add point at current position
        if self.main_window.status_label:
            self.main_window.status_label.setText("Add point not yet implemented")

    # ==================== View Action Handlers ====================

    @Slot()
    def _on_action_zoom_in(self) -> None:
        """Handle zoom in action."""
        if self.main_window.curve_widget:
            # Let curve widget handle zooming directly
            current_zoom = self.main_window.curve_widget.zoom_factor
            new_zoom = max(0.1, min(10.0, current_zoom * 1.2))
            self.main_window.curve_widget.zoom_factor = new_zoom
            self.main_window.curve_widget.invalidate_caches()
            self.main_window.curve_widget.update()
            self.main_window.curve_widget.zoom_changed.emit(new_zoom)
        else:
            # Fallback to state manager
            current_zoom = self.state_manager.zoom_level
            self.state_manager.zoom_level = current_zoom * 1.2
        self.update_zoom_label()

    @Slot()
    def _on_action_zoom_out(self) -> None:
        """Handle zoom out action."""
        if self.main_window.curve_widget:
            # Let curve widget handle zooming directly
            current_zoom = self.main_window.curve_widget.zoom_factor
            new_zoom = max(0.1, min(10.0, current_zoom / 1.2))
            self.main_window.curve_widget.zoom_factor = new_zoom
            self.main_window.curve_widget.invalidate_caches()
            self.main_window.curve_widget.update()
            self.main_window.curve_widget.zoom_changed.emit(new_zoom)
        else:
            # Fallback to state manager
            current_zoom = self.state_manager.zoom_level
            self.state_manager.zoom_level = current_zoom / 1.2
        self.update_zoom_label()

    @Slot()
    def _on_action_reset_view(self) -> None:
        """Handle reset view action."""
        if self.main_window.curve_widget:
            # Reset view using curve widget's method
            self.main_window.curve_widget.reset_view()
        else:
            # Fallback to state manager
            self.state_manager.zoom_level = 1.0
            self.state_manager.pan_offset = (0.0, 0.0)
        self.update_zoom_label()
        if self.main_window.status_label:
            self.main_window.status_label.setText("View reset")

    @Slot()
    def _on_zoom_fit(self) -> None:
        """Handle zoom fit action."""
        if self.main_window.curve_widget:
            self.main_window.curve_widget.fit_to_view()
            self.update_zoom_label()
            if self.main_window.status_label:
                self.main_window.status_label.setText("Fitted to view")

    # ==================== Curve Action Handlers ====================

    @Slot()
    def _on_smooth_curve(self) -> None:
        """Handle smooth curve action."""
        self.apply_smooth_operation()

    @Slot()
    def _on_filter_curve(self) -> None:
        """Handle filter curve action."""
        # TODO: Implement curve filtering
        if self.main_window.status_label:
            self.main_window.status_label.setText("Filter curve not yet implemented")

    @Slot()
    def _on_analyze_curve(self) -> None:
        """Handle analyze curve action."""
        # TODO: Implement curve analysis
        if self.main_window.status_label:
            self.main_window.status_label.setText("Analyze curve not yet implemented")

    # ==================== Complex Operations ====================

    def apply_smooth_operation(self) -> None:
        """Apply smoothing operation to selected points in the curve.

        Uses the smoothing parameters from the toolbar controls and applies
        smoothing to the currently selected points or all points if none selected.
        """
        # curve_widget is Optional
        if self.main_window.curve_widget is None:
            logger.warning("No curve widget available for smoothing")
            return

        # Get the current curve data
        curve_data = getattr(self.main_window.curve_widget, "curve_data", [])
        if not curve_data:
            self.main_window.statusBar().showMessage("No curve data to smooth", 2000)
            return

        # Get selected points or use all points
        selected_indices = getattr(self.main_window.curve_widget, "selected_indices", [])
        if not selected_indices:
            # Use all points if none selected
            selected_indices = list(range(len(curve_data)))
            self.main_window.statusBar().showMessage("No selection - smoothing all points", 2000)

        # Get smoothing parameters from toolbar/state manager
        window_size = self.state_manager.smoothing_window_size
        filter_type = self.state_manager.smoothing_filter_type

        # Create and execute smooth command
        from core.commands.curve_commands import SmoothCommand
        from services import get_interaction_service

        smooth_command = SmoothCommand(
            description=f"Smooth {len(selected_indices)} points ({filter_type})",
            indices=selected_indices,
            filter_type=filter_type,
            window_size=window_size,
        )

        interaction_service = get_interaction_service()

        # Try command system if available
        if interaction_service is not None:
            logger.info(f"Using command system for smoothing: {len(selected_indices)} points")
            if interaction_service.command_manager.execute_command(
                smooth_command, cast(MainWindowProtocol, cast(object, self.main_window))
            ):
                # Mark as modified
                self.state_manager.is_modified = True

                # Update status with details
                filter_display = {
                    "moving_average": "Moving Average",
                    "median": "Median",
                    "butterworth": "Butterworth",
                }.get(filter_type, filter_type)

                self.main_window.statusBar().showMessage(
                    f"Applied {filter_display} smoothing to {len(selected_indices)} points (size: {window_size})", 3000
                )
                logger.info(f"{filter_display} smoothing applied successfully via command system")
                return  # Command succeeded, exit early

            # Fall through to legacy implementation if command failed
            logger.error("Command system failed to execute smooth command")
        else:
            logger.info("InteractionService not available, using legacy smoothing implementation")

        # Fallback to legacy DataService implementation if command system unavailable or failed

        # Apply smoothing using DataService
        data_service = get_data_service()
        if data_service:
            # Extract points to smooth
            points_to_smooth = [curve_data[i] for i in selected_indices]

            # Apply the appropriate filter based on toolbar selection
            if filter_type == "moving_average":
                smoothed_points = data_service.smooth_moving_average(points_to_smooth, window_size)
            elif filter_type == "median":
                smoothed_points = data_service.filter_median(points_to_smooth, window_size)
            elif filter_type == "butterworth":
                # Butterworth uses window_size as order parameter
                smoothed_points = data_service.filter_butterworth(points_to_smooth, order=window_size // 2)
            else:
                logger.warning(f"Unknown filter type: {filter_type}")
                smoothed_points = points_to_smooth

            # Update the curve data
            new_curve_data = list(curve_data)
            for i, idx in enumerate(selected_indices):
                if i < len(smoothed_points):
                    new_curve_data[idx] = smoothed_points[i]

            # Set the new data
            self.main_window.curve_widget.set_curve_data(new_curve_data)

            # Mark as modified
            self.state_manager.is_modified = True

            # Update status with details
            filter_display = {"moving_average": "Moving Average", "median": "Median", "butterworth": "Butterworth"}.get(
                filter_type, filter_type
            )

            self.main_window.statusBar().showMessage(
                f"Applied {filter_display} smoothing to {len(selected_indices)} points (size: {window_size})", 3000
            )
            logger.info(f"{filter_display} smoothing applied to {len(selected_indices)} points (size: {window_size})")
        else:
            self.main_window.statusBar().showMessage("Data service not available for smoothing", 3000)

    # ==================== Helper Methods ====================

    def _get_current_curve_data(self) -> CurveDataList:
        """Get current curve data from the curve widget."""
        # Get data from curve widget (which uses ApplicationState internally)
        return self.main_window.curve_widget.curve_data if self.main_window.curve_widget else []

    def update_zoom_label(self) -> None:
        """Update the zoom level label in status bar."""
        if self.main_window.curve_widget:
            zoom_percent = int(self.main_window.curve_widget.zoom_factor * 100)
        else:
            zoom_percent = int(self.state_manager.zoom_level * 100)
        if self.main_window.zoom_label:
            self.main_window.zoom_label.setText(f"Zoom: {zoom_percent}%")

    # Protocol compliance aliases
    def _on_zoom_in(self) -> None:
        """Handle zoom in action (Protocol API)."""
        self._on_action_zoom_in()

    def _on_zoom_out(self) -> None:
        """Handle zoom out action (Protocol API)."""
        self._on_action_zoom_out()

    def _on_reset_view(self) -> None:
        """Handle reset view action (Protocol API)."""
        self._on_action_reset_view()
