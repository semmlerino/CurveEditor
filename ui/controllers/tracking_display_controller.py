#!/usr/bin/env python
"""
TrackingDisplayController - Handles visual display of tracking data.

Part of the MultiPointTrackingController split (PLAN TAU Phase 3 Task 3.1).
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Signal, Slot

from core.display_mode import DisplayMode
from core.logger_utils import get_logger
from core.type_aliases import CurveDataInput, CurveDataList, LegacyPointData
from protocols.ui import MainWindowProtocol
from ui.controllers.base_tracking_controller import BaseTrackingController

if TYPE_CHECKING:
    pass

logger = get_logger("tracking_display_controller")


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple.

    Args:
        hex_color: Hex color string (e.g., "#FF0000" or "FF0000")

    Returns:
        RGB tuple (r, g, b) with values 0-255
    """
    # Remove '#' if present
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


class TrackingDisplayController(BaseTrackingController):
    """Handles visual display of tracking data.

    Responsibilities:
        - Update curve view with tracking data
        - Manage curve visibility and colors
        - Sync timeline with tracking data
        - Update tracking panel display
        - Handle display mode changes

    Signals:
        display_updated: Emitted when display refreshed
    """

    display_updated: Signal = Signal()

    def __init__(self, main_window: MainWindowProtocol) -> None:
        """Initialize tracking display controller.

        Args:
            main_window: Main window protocol interface
        """
        super().__init__(main_window)
        logger.info("TrackingDisplayController initialized")

    @Slot(str, list)
    def on_data_loaded(self, curve_name: str, curve_data: CurveDataList) -> None:
        """Handle data loaded signal from TrackingDataController.

        Performs all display updates after data is loaded.

        Args:
            curve_name: Name of the loaded curve
            curve_data: The loaded curve data
        """
        if not self.main_window.curve_widget:
            return

        # Update the tracking panel
        self.update_tracking_panel()

        # Set up view for pixel-coordinate tracking data BEFORE setting data
        self.main_window.curve_widget.setup_for_pixel_tracking()

        # CRITICAL: Set active_curve BEFORE calling set_curve_data
        # Otherwise facade creates duplicate curves
        self._app_state.set_active_curve(curve_name)

        # Use the superior point-level selection system
        self.main_window.curve_widget.set_curve_data(curve_data)

        # ALSO update the multi-curve display to maintain proper side pane synchronization
        # This ensures both the superior point-level system AND the tracking panel stay in sync
        self.update_display_reset_selection()

        # Update frame range based on data
        self._update_frame_range_from_data(curve_data)

        # Sync table selection for file loading case
        if self.main_window.tracking_panel:
            self.main_window.tracking_panel.set_selected_points([curve_name])

        self.display_updated.emit()

    @Slot()
    def on_data_changed(self) -> None:
        """Handle data changed signal from TrackingDataController.

        Refreshes display to reflect data changes.
        """
        self.update_tracking_panel()
        self.update_display_preserve_selection()
        self.display_updated.emit()

    def update_tracking_panel(self) -> None:
        """Update tracking panel with current tracking data."""
        if self.main_window.tracking_panel:
            # Build dict from ApplicationState for tracking panel
            # Cast to Mapping to handle dict invariance (list is Sequence subtype)
            all_tracked_data: dict[str, CurveDataInput] = {}
            for curve_name in self._app_state.get_all_curve_names():
                all_tracked_data[curve_name] = self._app_state.get_curve_data(curve_name)
            self.main_window.tracking_panel.set_tracked_data(all_tracked_data)

    def _prepare_display_data(self) -> tuple[dict[str, CurveDataList], dict[str, dict[str, Any]], str | None]:
        """Prepare curve data for display (common logic).

        Returns:
            Tuple of (all_curves_data, metadata, active_curve)
        """
        active_curve = self._app_state.active_curve

        # Get all curves
        all_curves_data: dict[str, CurveDataList] = {}
        metadata: dict[str, dict[str, Any]] = {}

        for curve_name in self._app_state.get_all_curve_names():
            curve_data = self._app_state.get_curve_data(curve_name)
            if curve_data:
                all_curves_data[curve_name] = curve_data
                # Get metadata from tracking panel if available
                if self.main_window.tracking_panel is not None:
                    metadata[curve_name] = {
                        "visible": self.main_window.tracking_panel.get_point_visibility(curve_name),
                        "color": self.main_window.tracking_panel.get_point_color(curve_name),
                    }

        return all_curves_data, metadata, active_curve

    def update_display_preserve_selection(self) -> None:
        """Update display, preserving current curve selection.

        Use when: Data changed but user's selection context should be maintained.
        Examples: Point edits, smoothing, status changes, visibility/color updates.
        """
        if not self.main_window.curve_widget:
            return

        curves, metadata, active = self._prepare_display_data()

        # Check if curve widget supports multi-curve display
        if not callable(getattr(self.main_window.curve_widget, "set_curves_data", None)):
            # Fallback to single curve display
            if active and active in self._app_state.get_all_curve_names():
                trajectory = self._app_state.get_curve_data(active)
                self.main_window.curve_widget.set_curve_data(trajectory)
            else:
                self.main_window.curve_widget.set_curve_data([])
            return

        # Multi-curve display: preserve existing selection
        self.main_window.curve_widget.set_curves_data(
            curves,
            metadata,
            active,
            # selected_curves omitted - preserves existing selection
        )

    def update_display_with_selection(self, selected: list[str]) -> None:
        """Update display with explicit curve selection.

        Use when: User explicitly selected specific curves.
        Examples: Multi-curve selection from tracking panel.

        Args:
            selected: List of curve names to select
        """
        if not self.main_window.curve_widget:
            return

        curves, metadata, active = self._prepare_display_data()

        # Check if curve widget supports multi-curve display
        if not callable(getattr(self.main_window.curve_widget, "set_curves_data", None)):
            # Fallback to single curve display
            if active and active in self._app_state.get_all_curve_names():
                trajectory = self._app_state.get_curve_data(active)
                self.main_window.curve_widget.set_curve_data(trajectory)
            else:
                self.main_window.curve_widget.set_curve_data([])
            return

        # Multi-curve display: use explicit selection
        self.main_window.curve_widget.set_curves_data(
            curves,
            metadata,
            active,
            selected_curves=selected,
        )

    def update_display_reset_selection(self) -> None:
        """Update display, resetting selection to active curve only.

        Use when: Context changed significantly and selection should reset.
        Examples: Loading new file, switching curves, major state changes.
        """
        if not self.main_window.curve_widget:
            return

        curves, metadata, active = self._prepare_display_data()

        # Check if curve widget supports multi-curve display
        if not callable(getattr(self.main_window.curve_widget, "set_curves_data", None)):
            # Fallback to single curve display
            if active and active in self._app_state.get_all_curve_names():
                trajectory = self._app_state.get_curve_data(active)
                self.main_window.curve_widget.set_curve_data(trajectory)
            else:
                self.main_window.curve_widget.set_curve_data([])
            return

        # Multi-curve display: reset to active curve only
        self.main_window.curve_widget.set_curves_data(
            curves,
            metadata,
            active,
            selected_curves=[active] if active else [],
        )

    def _update_frame_range_from_data(self, data: Sequence[LegacyPointData]) -> None:
        """Update frame range UI elements based on single trajectory data.

        Args:
            data: Trajectory data
        """
        if data:
            max_frame = max(point[0] for point in data)
            try:
                if self.main_window.frame_slider:
                    self.main_window.frame_slider.setMaximum(max_frame)  # pyright: ignore[reportAttributeAccessIssue]  # QSlider method, None already checked
                if self.main_window.frame_spinbox:
                    self.main_window.frame_spinbox.setMaximum(max_frame)  # pyright: ignore[reportAttributeAccessIssue]  # QSpinBox method, None already checked
                if self.main_window.total_frames_label:
                    self.main_window.total_frames_label.setText(str(max_frame))  # pyright: ignore[reportAttributeAccessIssue]  # QLabel method, None already checked
            except RuntimeError:
                # Widgets may have been deleted during application shutdown
                pass

    def _update_frame_range_from_multi_data(self) -> None:
        """Update frame range based on all trajectories in multi-point data."""
        max_frame = 0
        for curve_name in self._app_state.get_all_curve_names():
            traj = self._app_state.get_curve_data(curve_name)
            if traj:
                traj_max = max(point[0] for point in traj)
                max_frame = max(max_frame, traj_max)

        if max_frame > 0:
            try:
                if self.main_window.frame_slider:
                    self.main_window.frame_slider.setMaximum(max_frame)  # pyright: ignore[reportAttributeAccessIssue]  # QSlider method, None already checked
                if self.main_window.frame_spinbox:
                    self.main_window.frame_spinbox.setMaximum(max_frame)  # pyright: ignore[reportAttributeAccessIssue]  # QSpinBox method, None already checked
                if self.main_window.total_frames_label:
                    self.main_window.total_frames_label.setText(str(max_frame))  # pyright: ignore[reportAttributeAccessIssue]  # QLabel method, None already checked
            except RuntimeError:
                # Widgets may have been deleted during application shutdown
                pass

    @Slot(str, bool)
    def on_point_visibility_changed(self, point_name: str, visible: bool) -> None:
        """Handle visibility change for a tracking point.

        Args:
            point_name: Name of the tracking point
            visible: Whether the point should be visible
        """
        # Update curve visibility directly if multi-curve is supported
        if self.main_window.curve_widget is not None and callable(
            getattr(self.main_window.curve_widget, "update_curve_visibility", None)
        ):
            self.main_window.curve_widget.update_curve_visibility(point_name, visible)
        else:
            # Fallback to full display update, preserving selection
            self.update_display_preserve_selection()
        logger.debug(f"Point {point_name} visibility changed to {visible}")

    @Slot(str, str)
    def on_point_color_changed(self, point_name: str, color: str) -> None:
        """Handle color change for a tracking point.

        Args:
            point_name: Name of the tracking point
            color: New color for the point (hex string like "#FF0000")
        """
        # Update curve color directly if multi-curve is supported
        if self.main_window.curve_widget is not None and callable(
            getattr(self.main_window.curve_widget, "update_curve_color", None)
        ):
            # Convert hex color string to RGB tuple
            rgb_color = _hex_to_rgb(color)
            self.main_window.curve_widget.update_curve_color(point_name, rgb_color)
        else:
            # Fallback to full display update, preserving selection
            self.update_display_preserve_selection()
        logger.debug(f"Point {point_name} color changed to {color}")

    def set_display_mode(self, mode: DisplayMode) -> None:
        """Set the display mode for curve rendering.

        Args:
            mode: DisplayMode enum value (ALL_VISIBLE, SELECTED, ACTIVE_ONLY)
        """
        if not self.main_window.curve_widget:
            return

        # Handle mode-specific logic BEFORE updating ApplicationState
        if mode == DisplayMode.SELECTED:
            # If no curves selected, auto-select the active curve
            selected = self._app_state.get_selected_curves()
            active_curve = self._app_state.active_curve

            if not selected and active_curve:
                # Auto-select active curve when switching to SELECTED mode with no selection
                self._app_state.set_selected_curves({active_curve})
                logger.debug(f"Auto-selected active curve '{active_curve}' for SELECTED mode")
            elif not selected and not active_curve:
                # Edge case: No selection and no active curve
                logger.warning(
                    "Cannot switch to SELECTED mode: no curves available. "
                    + "Load curves before using SELECTED display mode."
                )
                return
        elif mode == DisplayMode.ACTIVE_ONLY:
            # Clear selection in ACTIVE_ONLY mode
            self._app_state.set_selected_curves(set())

            # Validation logging
            if not self._app_state.active_curve:
                logger.debug("Switched to ACTIVE_ONLY mode with no active curve (nothing to display)")

        # Update ApplicationState (single source of truth)
        # display_mode is computed from _selected_curves and _show_all_curves
        if mode == DisplayMode.ALL_VISIBLE:
            self._app_state.set_show_all_curves(True)
        elif mode == DisplayMode.SELECTED:
            self._app_state.set_show_all_curves(False)
            # Ensure we have a selection (already handled above)
        elif mode == DisplayMode.ACTIVE_ONLY:
            self._app_state.set_show_all_curves(False)
            # Selection already cleared above

        # Trigger widget update
        self.main_window.curve_widget.update()
        logger.debug(f"Display mode set to: {self._app_state.display_mode}")

    def set_selected_curves(self, curve_names: list[str]) -> None:
        """Set which curves are currently selected for display.

        In SELECTED display mode, only these selected curves will be displayed.
        The last curve in the list becomes the active curve for editing.

        Args:
            curve_names: List of curve names to select and display
        """
        if not self.main_window.curve_widget:
            return

        # Update ApplicationState (single source of truth)
        self._app_state.set_selected_curves(set(curve_names))

        # Widget fields updated automatically via selection_state_changed signal
        # (No manual sync needed - signal handler updates widget._selected_curve_names)
        widget = self.main_window.curve_widget

        # Set the last selected as the active curve for editing
        all_curve_names = self._app_state.get_all_curve_names()
        if curve_names and curve_names[-1] in all_curve_names:
            widget.set_active_curve(curve_names[-1])

        widget.update()
        logger.debug(
            f"Selected curves: {self._app_state.get_selected_curves()}, "
            + f"Active: {self._app_state.active_curve}, "
            + f"Mode: {self._app_state.display_mode}"
        )

    def center_on_selected_curves(self) -> None:
        """Center the view on all selected curves.

        Calculates the bounding box of all selected curves and centers the view on it.
        """
        if not self.main_window.curve_widget:
            return

        widget = self.main_window.curve_widget

        # Get all curve names from ApplicationState
        all_curve_names = self._app_state.get_all_curve_names()
        logger.debug(
            f"center_on_selected_curves called with selected: {widget.selected_curve_names}, ApplicationState curves: {all_curve_names}"
        )
        if not widget.selected_curve_names or not all_curve_names:
            logger.debug("Early return - no selected curves or no data")
            return

        # Collect all points from selected curves
        all_points: list[tuple[float, float]] = []
        for curve_name in widget.selected_curve_names:
            if curve_name in all_curve_names:
                curve_data = self._app_state.get_curve_data(curve_name)
                logger.debug(f"Processing curve {curve_name} with {len(curve_data)} points")
                for point in curve_data:
                    if len(point) >= 3:
                        all_points.append((float(point[1]), float(point[2])))

        if not all_points:
            logger.debug("No points found in selected curves")
            return
        logger.debug(f"Collected {len(all_points)} points for centering")

        # Calculate bounding box
        x_coords = [p[0] for p in all_points]
        y_coords = [p[1] for p in all_points]

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        # Calculate center point
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # Calculate required zoom to fit all points with some padding
        from ui.ui_constants import MAX_ZOOM_FACTOR, MIN_ZOOM_FACTOR

        padding_factor = 1.2
        width_needed = (max_x - min_x) * padding_factor
        height_needed = (max_y - min_y) * padding_factor

        if width_needed > 0 and height_needed > 0:
            zoom_x = widget.width() / width_needed
            zoom_y = widget.height() / height_needed
            optimal_zoom = min(zoom_x, zoom_y, MAX_ZOOM_FACTOR)

            # Apply zoom
            widget.zoom_factor = max(MIN_ZOOM_FACTOR, optimal_zoom)

        # Use the proper centering method that handles coordinate transformation and Y-flip
        widget._center_view_on_point(center_x, center_y)  # pyright: ignore[reportAttributeAccessIssue]  # Accessing concrete CurveViewWidget implementation

        widget.invalidate_caches()  # pyright: ignore[reportAttributeAccessIssue]  # CurveViewWidget method not in protocol
        widget.update()
        widget.view_changed.emit()  # pyright: ignore[reportAttributeAccessIssue]  # Signal not in protocol
