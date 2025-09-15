"""Controller for tracking panel operations in MainWindow.

Manages tracking point data, panel updates, and tracking-related operations.
Part of Phase 3 refactoring to reduce MainWindow complexity.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from PySide6.QtWidgets import QDockWidget

    from ui.curve_view_widget import CurveViewWidget
    from ui.tracking_points_panel import TrackingPointsPanel

logger = logging.getLogger(__name__)


class MainWindowProtocol(Protocol):
    """Protocol defining what TrackingPanelController needs from MainWindow."""

    @property
    def tracked_data(self) -> dict[str, list[Any]]: ...

    @tracked_data.setter
    def tracked_data(self, value: dict[str, list[Any]]) -> None: ...

    @property
    def active_points(self) -> list[str]: ...

    @active_points.setter
    def active_points(self, value: list[str]) -> None: ...

    @property
    def tracking_panel(self) -> TrackingPointsPanel | None: ...

    @property
    def curve_widget(self) -> CurveViewWidget | None: ...

    @property
    def tracking_panel_dock(self) -> QDockWidget | None: ...

    def _update_curve_display(self) -> None: ...


class TrackingPanelController:
    """Controller for tracking panel operations.

    This class consolidates all tracking panel related operations from MainWindow,
    reducing its complexity by ~100 lines while maintaining the same functionality.
    """

    def __init__(self, main_window: MainWindowProtocol):
        """Initialize the tracking panel controller.

        Args:
            main_window: Reference to the main window
        """
        self.main_window: MainWindowProtocol = main_window
        logger.info("TrackingPanelController initialized")

    # =========================================================================
    # TRACKING POINT EVENT HANDLERS
    # =========================================================================

    def on_tracking_points_selected(self, point_names: list[str]) -> None:
        """Handle selection of tracking points from panel.

        Args:
            point_names: List of selected tracking point names
        """
        self.main_window.active_points = point_names
        self.update_curve_display()
        logger.debug(f"Selected tracking points: {point_names}")

    def on_point_visibility_changed(self, point_name: str, visible: bool) -> None:
        """Handle visibility change for a tracking point.

        Args:
            point_name: Name of the tracking point
            visible: Whether the point should be visible
        """
        # Update display to show/hide the trajectory
        self.update_curve_display()
        logger.debug(f"Tracking point '{point_name}' visibility changed to {visible}")

    def on_point_color_changed(self, point_name: str, color: str) -> None:
        """Handle color change for a tracking point.

        Args:
            point_name: Name of the tracking point
            color: New color for the point
        """
        # Update display with new color
        self.update_curve_display()
        logger.debug(f"Tracking point '{point_name}' color changed to {color}")

    def on_point_deleted(self, point_name: str) -> None:
        """Handle deletion of a tracking point.

        Args:
            point_name: Name of the tracking point to delete
        """
        if point_name in self.main_window.tracked_data:
            del self.main_window.tracked_data[point_name]
            if point_name in self.main_window.active_points:
                self.main_window.active_points.remove(point_name)
            self.update_tracking_panel()
            self.update_curve_display()
            logger.info(f"Deleted tracking point: {point_name}")

    def on_point_renamed(self, old_name: str, new_name: str) -> None:
        """Handle renaming of a tracking point.

        Args:
            old_name: Current name of the tracking point
            new_name: New name for the tracking point
        """
        if old_name in self.main_window.tracked_data:
            self.main_window.tracked_data[new_name] = self.main_window.tracked_data.pop(old_name)
            if old_name in self.main_window.active_points:
                idx = self.main_window.active_points.index(old_name)
                self.main_window.active_points[idx] = new_name
            self.update_tracking_panel()
            logger.info(f"Renamed tracking point from '{old_name}' to '{new_name}'")

    # =========================================================================
    # TRACKING PANEL UPDATES
    # =========================================================================

    def update_tracking_panel(self) -> None:
        """Update tracking panel with current tracking data."""
        if self.main_window.tracking_panel is not None:
            self.main_window.tracking_panel.set_tracked_data(self.main_window.tracked_data)
            logger.debug(f"Updated tracking panel with {len(self.main_window.tracked_data)} points")

    def update_curve_display(self) -> None:
        """Update curve display with selected tracking points."""
        if not self.main_window.curve_widget:
            return

        # For now, display the first selected point's trajectory
        # TODO: Support multiple trajectory display
        if self.main_window.active_points and self.main_window.active_points[0] in self.main_window.tracked_data:
            trajectory = self.main_window.tracked_data[self.main_window.active_points[0]]
            self.main_window.curve_widget.set_curve_data(trajectory)
            logger.debug(f"Displaying trajectory for point: {self.main_window.active_points[0]}")
        else:
            self.main_window.curve_widget.set_curve_data([])
            logger.debug("Cleared curve display (no active points)")

    # =========================================================================
    # DATA MANAGEMENT
    # =========================================================================

    def add_tracking_point(self, name: str, data: list[tuple[int, float, float]]) -> None:
        """Add a new tracking point.

        Args:
            name: Name of the tracking point
            data: Trajectory data for the point
        """
        self.main_window.tracked_data[name] = data
        self.update_tracking_panel()
        logger.info(f"Added tracking point '{name}' with {len(data)} frames")

    def clear_tracking_data(self) -> None:
        """Clear all tracking data."""
        self.main_window.tracked_data.clear()
        self.main_window.active_points.clear()
        self.update_tracking_panel()
        self.update_curve_display()
        logger.info("Cleared all tracking data")

    def get_active_trajectory(self) -> list[tuple[int, float, float]] | None:
        """Get the trajectory data for the currently active point.

        Returns:
            Trajectory data or None if no active point
        """
        if self.main_window.active_points and self.main_window.active_points[0] in self.main_window.tracked_data:
            return self.main_window.tracked_data[self.main_window.active_points[0]]
        return None

    def set_active_points(self, point_names: list[str]) -> None:
        """Set the active tracking points programmatically.

        Args:
            point_names: List of tracking point names to activate
        """
        # Validate that points exist
        valid_points = [name for name in point_names if name in self.main_window.tracked_data]
        self.main_window.active_points = valid_points
        self.update_curve_display()

        # Update panel selection if it exists
        if self.main_window.tracking_panel is not None:
            # This would need a method on TrackingPointsPanel to set selection
            # For now, just log
            logger.debug(f"Set active points programmatically: {valid_points}")

    # =========================================================================
    # VISIBILITY CONTROL
    # =========================================================================

    def toggle_panel_visibility(self) -> None:
        """Toggle the tracking panel dock visibility."""
        if hasattr(self.main_window, "tracking_panel_dock"):
            dock = self.main_window.tracking_panel_dock
            if dock is not None:
                dock.setVisible(not dock.isVisible())
                logger.debug(f"Tracking panel visibility toggled to: {dock.isVisible()}")

    def show_panel(self) -> None:
        """Show the tracking panel dock."""
        if hasattr(self.main_window, "tracking_panel_dock"):
            dock = self.main_window.tracking_panel_dock
            if dock is not None:
                dock.setVisible(True)

    def hide_panel(self) -> None:
        """Hide the tracking panel dock."""
        if hasattr(self.main_window, "tracking_panel_dock"):
            dock = self.main_window.tracking_panel_dock
            if dock is not None:
                dock.setVisible(False)
