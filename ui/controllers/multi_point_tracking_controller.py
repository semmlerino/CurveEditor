#!/usr/bin/env python
"""
Multi-Point Tracking Controller for CurveEditor.

This controller manages multi-point tracking data, including loading,
selection, and display of multiple tracking trajectories.

Phase 3.1: Refactored to delegate to specialized sub-controllers:
- TrackingDataController: Data operations (loading, deletion, renaming)
- TrackingDisplayController: Display updates (panel, curves, centering)
- TrackingSelectionController: Selection synchronization (tracking panel ↔ curve store)

This facade provides backward-compatible API while maintaining separation of concerns.
"""
# pyright: reportImportCycles=false

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

if TYPE_CHECKING:
    from protocols.ui import MainWindowProtocol

from core.display_mode import DisplayMode
from core.logger_utils import get_logger
from core.models import TrackingDirection
from core.type_aliases import CurveDataInput, CurveDataList
from stores.application_state import ApplicationState, get_application_state

# Import sub-controllers
from ui.controllers.tracking_data_controller import TrackingDataController
from ui.controllers.tracking_display_controller import TrackingDisplayController
from ui.controllers.tracking_selection_controller import TrackingSelectionController

logger = get_logger("multi_point_tracking_controller")


class MultiPointTrackingController(QObject):
    """
    Facade controller for multi-point tracking operations.

    Delegates to specialized sub-controllers:
    - data_controller: Data operations
    - display_controller: Display updates
    - selection_controller: Selection synchronization

    Phase 3.1: Refactored from 1,166 lines to thin delegation layer.
    """

    def __init__(self, main_window: "MainWindowProtocol"):
        """
        Initialize the multi-point tracking controller.

        Args:
            main_window: Reference to the main window for UI access
        """
        super().__init__()
        self.main_window: MainWindowProtocol = main_window

        # Get centralized ApplicationState
        self._app_state: ApplicationState = get_application_state()

        # Create sub-controllers
        self.data_controller: TrackingDataController = TrackingDataController(main_window)
        self.display_controller: TrackingDisplayController = TrackingDisplayController(main_window)
        self.selection_controller: TrackingSelectionController = TrackingSelectionController(main_window)

        # Wire sub-controllers together
        self._connect_sub_controllers()

        # Tracking data storage (kept at facade level for backward compatibility)
        self.point_tracking_directions: dict[str, TrackingDirection] = {}  # Track previous directions

        logger.info("MultiPointTrackingController initialized with sub-controllers")

    def _connect_sub_controllers(self) -> None:
        """Wire sub-controller signals for coordinated behavior."""
        # Data loaded → Update display
        _ = self.data_controller.data_loaded.connect(self.display_controller.on_data_loaded)

        # Data loaded → Auto-select point
        _ = self.data_controller.data_loaded.connect(self.selection_controller.on_data_loaded)

        # Data changed → Update display
        _ = self.data_controller.data_changed.connect(self.display_controller.on_data_changed)

        logger.debug("Sub-controller signals wired")

    def __del__(self) -> None:
        """Cleanup is now handled by sub-controllers."""
        pass

    # ==================== Property Delegation ====================

    @property
    def tracked_data(self) -> dict[str, CurveDataList]:
        """Delegate to data controller."""
        return self.data_controller.tracked_data

    @tracked_data.setter
    def tracked_data(self, value: dict[str, CurveDataList]) -> None:
        """Delegate to data controller."""
        self.data_controller.tracked_data = value

    # ==================== Data Operations - Delegate to TrackingDataController ====================

    def on_tracking_data_loaded(self, data: CurveDataInput) -> None:
        """
        Handle single tracking trajectory loaded in background thread.

        Args:
            data: Single trajectory data loaded from file
        """
        self.data_controller.on_tracking_data_loaded(data)  # pyright: ignore[reportArgumentType]

    def on_multi_point_data_loaded(self, multi_data: dict[str, CurveDataList]) -> None:
        """
        Handle multi-point tracking data loaded in background thread.

        Args:
            multi_data: Dictionary of point names to trajectory data
        """
        self.data_controller.on_multi_point_data_loaded(multi_data)

    def on_point_deleted(self, point_name: str) -> None:
        """
        Handle deletion of a tracking point.

        Args:
            point_name: Name of the tracking point to delete
        """
        self.data_controller.on_point_deleted(point_name)
        # Clean up tracking direction mapping (kept at facade level)
        if point_name in self.point_tracking_directions:
            del self.point_tracking_directions[point_name]

    def on_point_renamed(self, old_name: str, new_name: str) -> None:
        """
        Handle renaming of a tracking point.

        Args:
            old_name: Current name of the tracking point
            new_name: New name for the tracking point
        """
        self.data_controller.on_point_renamed(old_name, new_name)
        # Update tracking direction mapping (kept at facade level)
        if old_name in self.point_tracking_directions:
            self.point_tracking_directions[new_name] = self.point_tracking_directions.pop(old_name)

    def on_tracking_direction_changed(self, point_name: str, new_direction: object) -> None:
        """
        Handle tracking direction change for a point.

        Args:
            point_name: Name of the tracking point
            new_direction: New tracking direction (passed as object from signal)
        """
        self.data_controller.on_tracking_direction_changed(point_name, new_direction)
        # Update tracking direction mapping (kept at facade level)
        if isinstance(new_direction, TrackingDirection):
            self.point_tracking_directions[point_name] = new_direction

    def clear_tracking_data(self) -> None:
        """Clear all tracking data."""
        self.data_controller.clear_tracking_data()
        self.point_tracking_directions.clear()

    def get_active_trajectory(self) -> CurveDataList | None:
        """
        Get the currently active trajectory data.

        Returns:
            Active trajectory data or None if no active timeline point
        """
        return self.data_controller.get_active_trajectory()

    def has_tracking_data(self) -> bool:
        """
        Check if any tracking data is loaded.

        Returns:
            True if tracking data exists, False otherwise
        """
        return self.data_controller.has_tracking_data()

    def get_tracking_point_names(self) -> list[str]:
        """
        Get list of all tracking point names.

        Returns:
            List of tracking point names
        """
        return self.data_controller.get_tracking_point_names()

    def get_unique_point_name(self, base_name: str) -> str:
        """
        Generate a unique point name by appending a suffix if needed.

        Args:
            base_name: The desired point name

        Returns:
            A unique point name that doesn't conflict with existing names
        """
        return self.data_controller.get_unique_point_name(base_name)

    # ==================== Display Operations - Delegate to TrackingDisplayController ====================

    def update_tracking_panel(self) -> None:
        """Update tracking panel with current tracking data."""
        self.display_controller.update_tracking_panel()

    def update_curve_display(self) -> None:
        """Update curve display, preserving current selection."""
        self.display_controller.update_display_preserve_selection()

    def update_display_preserve_selection(self) -> None:
        """Update display, preserving current curve selection."""
        self.display_controller.update_display_preserve_selection()

    def update_display_with_selection(self, selected: list[str]) -> None:
        """Update display with explicit curve selection.

        Args:
            selected: List of curve names to select
        """
        self.display_controller.update_display_with_selection(selected)

    def update_display_reset_selection(self) -> None:
        """Update display, resetting selection to active curve only."""
        self.display_controller.update_display_reset_selection()

    def on_point_visibility_changed(self, point_name: str, visible: bool) -> None:
        """
        Handle visibility change for a tracking point.

        Args:
            point_name: Name of the tracking point
            visible: Whether the point should be visible
        """
        self.display_controller.on_point_visibility_changed(point_name, visible)

    def on_point_color_changed(self, point_name: str, color: str) -> None:
        """
        Handle color change for a tracking point.

        Args:
            point_name: Name of the tracking point
            color: New color for the point
        """
        self.display_controller.on_point_color_changed(point_name, color)

    def set_display_mode(self, mode: DisplayMode) -> None:
        """
        Set the display mode for curve rendering.

        Args:
            mode: DisplayMode enum value (ALL_VISIBLE, SELECTED, ACTIVE_ONLY)
        """
        self.display_controller.set_display_mode(mode)

    def set_selected_curves(self, curve_names: list[str]) -> None:
        """
        Set which curves are currently selected for display.

        Args:
            curve_names: List of curve names to select and display
        """
        self.display_controller.set_selected_curves(curve_names)

    def center_on_selected_curves(self) -> None:
        """Center the view on all selected curves."""
        self.display_controller.center_on_selected_curves()

    # ==================== Selection Operations - Delegate to TrackingSelectionController ====================

    def on_tracking_points_selected(self, point_names: list[str]) -> None:
        """
        Handle selection of tracking points from panel.

        Args:
            point_names: List of selected point names (for multi-selection in panel)
        """
        self.selection_controller.on_tracking_points_selected(point_names, self.display_controller)

    def on_curve_selection_changed(self, selection: set[int], curve_name: str | None = None) -> None:
        """
        Handle selection changes from CurveDataStore (bidirectional synchronization).

        Args:
            selection: Set of selected point indices from CurveDataStore
            curve_name: Name of curve with selection change (None uses active_timeline_point)
        """
        self.selection_controller.on_curve_selection_changed(selection, curve_name)
