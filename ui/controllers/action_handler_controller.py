#!/usr/bin/env python
"""
Action Handler Controller for CurveEditor.

This controller manages all action-related functionality that was previously
handled directly in MainWindow. It maintains exact compatibility with the
existing ShortcutManager connections and behavior.
"""

import logging
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QInputDialog, QMessageBox

from core.type_aliases import CurveDataList
from services import get_data_service

if TYPE_CHECKING:
    from ui.main_window import MainWindow
    from ui.state_manager import StateManager

logger = logging.getLogger("action_handler_controller")


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
        self.state_manager: "StateManager" = state_manager
        self.main_window: "MainWindow" = main_window
        logger.info("ActionHandlerController initialized")

    # ==================== File Action Handlers ====================

    @Slot()
    def _on_action_new(self) -> None:
        """Handle new file action."""
        if self.main_window.file_operations.new_file():
            # Clear curve widget data
            if self.main_window.curve_widget:
                self.main_window.curve_widget.set_curve_data([])
                self.main_window._update_tracking_panel()

            self.state_manager.reset_to_defaults()
            self.main_window._update_ui_state()
            self.main_window.status_label.setText("New curve created")

    @Slot()
    def _on_action_open(self) -> None:
        """Handle open file action."""
        data = self.main_window.file_operations.open_file(self.main_window)

        if data:
            # Check if it's multi-point data
            if isinstance(data, dict):
                # Successfully loaded multi-point data
                self.main_window.tracked_data = data
                self.main_window.active_points = list(data.keys())[:1]  # Select first point

                # Set up view for pixel-coordinate tracking data BEFORE displaying
                if self.main_window.curve_widget:
                    self.main_window.curve_widget.setup_for_pixel_tracking()

                self.main_window._update_tracking_panel()
                self.main_window._update_curve_display()

                # Update frame range based on first trajectory
                if (
                    self.main_window.active_points
                    and self.main_window.active_points[0] in self.main_window.tracked_data
                ):
                    trajectory = self.main_window.tracked_data[self.main_window.active_points[0]]
                    if trajectory:
                        max_frame = max(point[0] for point in trajectory)
                        if self.main_window.frame_slider:
                            self.main_window.frame_slider.setMaximum(max_frame)
                        if self.main_window.frame_spinbox:
                            self.main_window.frame_spinbox.setMaximum(max_frame)
                        if self.main_window.total_frames_label:
                            self.main_window.total_frames_label.setText(str(max_frame))
                        self.state_manager.total_frames = max_frame
            else:
                # Single curve data
                # Update curve widget with new data
                if self.main_window.curve_widget:
                    self.main_window.curve_widget.set_curve_data(data)
                    self.main_window._update_tracking_panel()

                # Update state manager
                self.state_manager.set_track_data(data, mark_modified=False)  # pyright: ignore[reportArgumentType]

                # Update frame range based on loaded data
                max_frame = max(point[0] for point in data)
                if self.main_window.frame_slider:
                    self.main_window.frame_slider.setMaximum(max_frame)
                if self.main_window.frame_spinbox:
                    self.main_window.frame_spinbox.setMaximum(max_frame)
                if self.main_window.total_frames_label:
                    self.main_window.total_frames_label.setText(str(max_frame))
                # CRITICAL: Update state manager's total frames!
                self.state_manager.total_frames = max_frame

                # Update timeline tabs with frame range and point data
                self.main_window._update_timeline_tabs(data)  # pyright: ignore[reportArgumentType]

            self.main_window._update_ui_state()
            self.main_window.status_label.setText("File loaded successfully")

    @Slot()
    def _on_action_save(self) -> None:
        """Handle save file action."""
        data = self._get_current_curve_data()
        if self.main_window.file_operations.save_file(data):
            self.main_window.status_label.setText("File saved successfully")

    @Slot()
    def _on_action_save_as(self) -> None:
        """Handle save as action."""
        data = self._get_current_curve_data()
        if self.main_window.file_operations.save_file_as(data, self.main_window):
            self.main_window.status_label.setText("File saved successfully")

    @Slot()
    def _on_load_images(self) -> None:
        """Handle load background images action."""
        if self.main_window.file_operations.load_images(self.main_window):
            self.main_window.status_label.setText("Images loaded successfully")

    @Slot()
    def _on_export_data(self) -> None:
        """Handle export curve data action."""
        data = self._get_current_curve_data()
        if self.main_window.file_operations.export_data(data, self.main_window):
            self.main_window.status_label.setText("Data exported successfully")

    # ==================== Edit Action Handlers ====================

    @Slot()
    def _on_action_undo(self) -> None:
        """Handle undo action."""
        self.main_window.services.undo()
        self.main_window.status_label.setText("Undo")

    @Slot()
    def _on_action_redo(self) -> None:
        """Handle redo action."""
        self.main_window.services.redo()
        self.main_window.status_label.setText("Redo")

    @Slot()
    def _on_select_all(self) -> None:
        """Handle select all action."""
        if self.main_window.curve_widget:
            self.main_window.curve_widget._select_all()
            self.main_window.status_label.setText("All points selected")

    @Slot()
    def _on_add_point(self) -> None:
        """Handle add point action."""
        # TODO: Implement add point at current position
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
            self.main_window.curve_widget._invalidate_caches()
            self.main_window.curve_widget.update()
            self.main_window.curve_widget.zoom_changed.emit(new_zoom)
        else:
            # Fallback to state manager
            current_zoom = self.state_manager.zoom_level
            self.state_manager.zoom_level = current_zoom * 1.2
        self._update_zoom_label()

    @Slot()
    def _on_action_zoom_out(self) -> None:
        """Handle zoom out action."""
        if self.main_window.curve_widget:
            # Let curve widget handle zooming directly
            current_zoom = self.main_window.curve_widget.zoom_factor
            new_zoom = max(0.1, min(10.0, current_zoom / 1.2))
            self.main_window.curve_widget.zoom_factor = new_zoom
            self.main_window.curve_widget._invalidate_caches()
            self.main_window.curve_widget.update()
            self.main_window.curve_widget.zoom_changed.emit(new_zoom)
        else:
            # Fallback to state manager
            current_zoom = self.state_manager.zoom_level
            self.state_manager.zoom_level = current_zoom / 1.2
        self._update_zoom_label()

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
        self._update_zoom_label()
        self.main_window.status_label.setText("View reset")

    @Slot()
    def _on_zoom_fit(self) -> None:
        """Handle zoom fit action."""
        if self.main_window.curve_widget:
            self.main_window.curve_widget.fit_to_view()
            self._update_zoom_label()
            self.main_window.status_label.setText("Fitted to view")

    # ==================== Curve Action Handlers ====================

    @Slot()
    def _on_smooth_curve(self) -> None:
        """Handle smooth curve action."""
        # TODO: Implement curve smoothing
        self.main_window.status_label.setText("Smooth curve not yet implemented")

    @Slot()
    def _on_filter_curve(self) -> None:
        """Handle filter curve action."""
        # TODO: Implement curve filtering
        self.main_window.status_label.setText("Filter curve not yet implemented")

    @Slot()
    def _on_analyze_curve(self) -> None:
        """Handle analyze curve action."""
        # TODO: Implement curve analysis
        self.main_window.status_label.setText("Analyze curve not yet implemented")

    # ==================== Complex Operations ====================

    def apply_smooth_operation(self) -> None:
        """Apply smoothing operation to selected points in the curve.

        Shows a dialog to get smoothing parameters and applies smoothing
        to the currently selected points or all points if none selected.
        """
        # curve_widget is Optional
        if self.main_window.curve_widget is None:
            logger.warning("No curve widget available for smoothing")
            return

        # Get the current curve data
        curve_data = getattr(self.main_window.curve_widget, "curve_data", [])
        if not curve_data:
            _ = QMessageBox.information(self.main_window, "No Data", "No curve data to smooth.")
            return

        # Get selected points or use all points
        selected_indices = getattr(self.main_window.curve_widget, "selected_indices", [])
        if not selected_indices:
            # Ask if user wants to smooth all points
            reply = QMessageBox.question(
                self.main_window,
                "No Selection",
                "No points selected. Apply smoothing to all points?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            selected_indices = list(range(len(curve_data)))

        # Get smoothing window size from user
        from services import get_ui_service

        ui_service = get_ui_service()
        if ui_service:
            window_size = ui_service.get_smooth_window_size(self.main_window)
            if window_size is None:
                return  # User cancelled
        else:
            # Fallback to simple input dialog
            window_size, ok = QInputDialog.getInt(
                self.main_window, "Smoothing Window Size", "Enter window size (3-15):", 5, 3, 15
            )
            if not ok:
                return

        # Apply smoothing using DataService
        data_service = get_data_service()
        if data_service:
            # Extract points to smooth
            points_to_smooth = [curve_data[i] for i in selected_indices]

            # Apply smoothing
            smoothed_points = data_service.smooth_moving_average(points_to_smooth, window_size)

            # Update the curve data
            new_curve_data = list(curve_data)
            for i, idx in enumerate(selected_indices):
                if i < len(smoothed_points):
                    new_curve_data[idx] = smoothed_points[i]

            # Set the new data
            self.main_window.curve_widget.set_curve_data(new_curve_data)
            # self._update_point_list_data()  # Method doesn't exist

            # Mark as modified
            # state_manager is always initialized in __init__
            self.state_manager.is_modified = True

            # Update status
            self.main_window.statusBar().showMessage(
                f"Applied smoothing to {len(selected_indices)} points (window size: {window_size})", 3000
            )
            logger.info(f"Smoothing applied to {len(selected_indices)} points")
        else:
            _ = QMessageBox.warning(self.main_window, "Service Error", "Data service not available for smoothing.")

    # ==================== Helper Methods ====================

    def _get_current_curve_data(self) -> CurveDataList:
        """Get current curve data from curve widget or state manager."""
        if self.main_window.curve_widget:
            return self.main_window.curve_widget.curve_data
        return cast(CurveDataList, self.state_manager.track_data)

    def _update_zoom_label(self) -> None:
        """Update the zoom level label in status bar."""
        if self.main_window.curve_widget:
            zoom_percent = int(self.main_window.curve_widget.zoom_factor * 100)
        else:
            zoom_percent = int(self.state_manager.zoom_level * 100)
        self.main_window.zoom_label.setText(f"Zoom: {zoom_percent}%")
