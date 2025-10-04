#!/usr/bin/env python
"""
Multi-Point Tracking Controller for CurveEditor.

This controller manages multi-point tracking data, including loading,
selection, and display of multiple tracking trajectories.
"""

from enum import Enum, auto
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QThread, QTimer, Slot
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from ui.main_window import MainWindow

from core.logger_utils import get_logger
from core.models import TrackingDirection
from core.type_aliases import CurveDataList
from data.tracking_direction_utils import update_keyframe_status_for_tracking_direction
from services.service_protocols import MainWindowProtocol
from stores.application_state import get_application_state


class SelectionContext(Enum):
    """Context for curve display updates to control auto-selection behavior."""

    DATA_LOADING = auto()  # Auto-select during data loading
    MANUAL_SELECTION = auto()  # Don't auto-select, preserve user selection
    CURVE_SWITCHING = auto()  # Auto-select when switching between curves
    DEFAULT = auto()  # Default behavior (auto-select)


logger = get_logger("multi_point_tracking_controller")


class MultiPointTrackingController:
    """
    Controller for managing multi-point tracking data.

    Extracted from MainWindow to centralize all multi-point tracking logic,
    including loading tracking data, managing active points, and updating
    the tracking panel display.
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Initialize the multi-point tracking controller.

        Args:
            main_window: Reference to the main window for UI access
        """
        self.main_window = main_window

        # Get centralized ApplicationState (Week 4 migration)
        self._app_state = get_application_state()

        # Connect to ApplicationState signals for reactive updates
        self._app_state.curves_changed.connect(self._on_curves_changed)
        self._app_state.active_curve_changed.connect(self._on_active_curve_changed)

        # Recursion protection for signal handlers
        self._handling_signal = False

        # Tracking data storage
        # REMOVED: self.tracked_data - migrated to ApplicationState (Week 4)
        # NOTE: active_timeline_point is now managed by StateManager (via main_window.active_timeline_point)
        # This determines which tracking point's timeline is being displayed
        self.point_tracking_directions: dict[str, TrackingDirection] = {}  # Track previous directions
        self._previous_active_curve: str | None = None  # Track previous active curve for data persistence

        logger.info("MultiPointTrackingController initialized")

    @property
    def tracked_data(self) -> dict[str, CurveDataList]:
        """
        Backward-compatible property for accessing tracked data during migration.

        Returns all curves from ApplicationState as a dict, excluding "__default__".
        This property exists for backward compatibility during the Week 4 migration.
        """
        result = {}
        for curve_name in self._app_state.get_all_curve_names():
            # Filter out internal "__default__" curve used for single-curve mode
            if curve_name != "__default__":
                result[curve_name] = self._app_state.get_curve_data(curve_name)
        return result

    @tracked_data.setter
    def tracked_data(self, value: dict[str, CurveDataList]) -> None:
        """
        Backward-compatible setter for tracked data during migration.

        Writes all curves to ApplicationState.
        This setter exists for backward compatibility during the Week 4 migration.
        """
        # Clear existing curves (except "__default__" which is for single-curve mode)
        for curve_name in list(self._app_state.get_all_curve_names()):
            if curve_name != "__default__":
                self._app_state.delete_curve(curve_name)

        # Add all curves from the input dict
        for curve_name, curve_data in value.items():
            self._app_state.set_curve_data(curve_name, curve_data)

    @Slot(list)
    def on_tracking_data_loaded(self, data: list[tuple[int, float, float] | tuple[int, float, float, str]]) -> None:
        """
        Handle single tracking trajectory loaded in background thread.

        Args:
            data: Single trajectory data loaded from file
        """
        current_thread = QThread.currentThread()
        app_instance = QApplication.instance()
        main_thread = app_instance.thread() if app_instance is not None else None
        logger.info(
            f"[THREAD-DEBUG] on_tracking_data_loaded executing in thread: {current_thread} (main={current_thread == main_thread})"
        )

        if data and self.main_window.curve_widget:
            logger.debug(f"[DATA] Loaded {len(data)} points from background thread")
            # Log first few points for debugging
            for i in range(min(3, len(data))):
                logger.debug(f"[DATA] Point {i}: {data[i]}")

            # Add as a new tracking point to multi-point data
            existing_curves = self._app_state.get_all_curve_names()
            if existing_curves:
                # We have existing data - add this as a new point
                base_name = "Track"
                point_name = self._get_unique_point_name(base_name)
                self._app_state.set_curve_data(point_name, data)  # pyright: ignore[reportArgumentType]
                self.main_window.active_timeline_point = point_name  # Set as active timeline point
                # Initialize with default tracking direction
                self.point_tracking_directions[point_name] = TrackingDirection.TRACKING_FW
                logger.info(f"Added single trajectory as '{point_name}' to existing {len(existing_curves)} points")

                # Update the tracking panel to show the new point
                self.update_tracking_panel()
            else:
                # No existing data - create initial data with this trajectory
                self._app_state.set_curve_data("Track1", data)  # pyright: ignore[reportArgumentType]
                self.main_window.active_timeline_point = "Track1"
                # Sync table selection for file loading case
                if self.main_window.tracking_panel:
                    self.main_window.tracking_panel.set_selected_points(["Track1"])
                # Initialize with default tracking direction
                self.point_tracking_directions["Track1"] = TrackingDirection.TRACKING_FW
                logger.info("Loaded single trajectory as 'Track1'")

                # Update the tracking panel
                self.update_tracking_panel()

            # Set up view for pixel-coordinate tracking data BEFORE setting data
            self.main_window.curve_widget.setup_for_pixel_tracking()
            # Use the superior point-level selection system
            self.main_window.curve_widget.set_curve_data(data)  # pyright: ignore[reportArgumentType]
            self.main_window.state_manager.set_track_data(data, mark_modified=False)  # pyright: ignore[reportArgumentType]

            # ALSO update the multi-curve display to maintain proper side pane synchronization
            # This ensures both the superior point-level system AND the tracking panel stay in sync
            self.update_curve_display(SelectionContext.DATA_LOADING)

            # AUTO-SELECT point at current frame for immediate superior selection experience
            self._auto_select_point_at_current_frame()

            # Update frame range based on data
            self._update_frame_range_from_data(data)

    @Slot(dict)
    def on_multi_point_data_loaded(self, multi_data: dict[str, CurveDataList]) -> None:
        """
        Handle multi-point tracking data loaded in background thread.

        Args:
            multi_data: Dictionary of point names to trajectory data
        """
        current_thread = QThread.currentThread()
        app_instance = QApplication.instance()
        main_thread = app_instance.thread() if app_instance is not None else None
        logger.info(
            f"[THREAD-DEBUG] on_multi_point_data_loaded executing in thread: {current_thread} (main={current_thread == main_thread})"
        )

        if multi_data:
            # Merge with existing data instead of replacing
            existing_curves = self._app_state.get_all_curve_names()
            if existing_curves:
                # We have existing data - merge the new points
                logger.info(f"Merging {len(multi_data)} new points with {len(existing_curves)} existing points")

                # Track newly added points for selection
                new_point_names = []

                for point_name, trajectory in multi_data.items():
                    # Check for naming conflicts and resolve them
                    unique_name = self._get_unique_point_name(point_name)
                    self._app_state.set_curve_data(unique_name, trajectory)
                    new_point_names.append(unique_name)
                    # Initialize with default tracking direction
                    self.point_tracking_directions[unique_name] = TrackingDirection.TRACKING_FW

                    if unique_name != point_name:
                        logger.info(f"Renamed duplicate point '{point_name}' to '{unique_name}'")

                # If no timeline point is active, select the first new point
                if not self.main_window.active_timeline_point and new_point_names:
                    self.main_window.active_timeline_point = new_point_names[0]
                    # Sync table selection for file loading case
                    if self.main_window.tracking_panel:
                        self.main_window.tracking_panel.set_selected_points([new_point_names[0]])

                all_curves_after_merge = self._app_state.get_all_curve_names()
                logger.info(f"Total points after merge: {len(all_curves_after_merge)}")
            else:
                # No existing data - use the new data directly
                for point_name, trajectory in multi_data.items():
                    self._app_state.set_curve_data(point_name, trajectory)
                # Set first point as active timeline point by default
                first_point = list(multi_data.keys())[0] if multi_data else None
                self.main_window.active_timeline_point = first_point
                # Sync table selection for file loading case
                if self.main_window.tracking_panel and first_point:
                    self.main_window.tracking_panel.set_selected_points([first_point])
                # Initialize all points with default tracking direction
                for point_name in multi_data.keys():
                    self.point_tracking_directions[point_name] = TrackingDirection.TRACKING_FW
                logger.info(f"Loaded {len(multi_data)} tracking points from multi-point file")

            # Update the tracking panel with the multi-point data
            self.update_tracking_panel()

            # Display the active timeline point's trajectory (could be existing or newly loaded)
            active_point = self.main_window.active_timeline_point
            if active_point and self.main_window.curve_widget:
                if active_point in self._app_state.get_all_curve_names():
                    # Set up view for pixel-coordinate tracking data
                    self.main_window.curve_widget.setup_for_pixel_tracking()
                    trajectory = self._app_state.get_curve_data(active_point)
                    self.main_window.curve_widget.set_curve_data(trajectory)
                    self.main_window.state_manager.set_track_data(trajectory, mark_modified=False)  # pyright: ignore[reportArgumentType]

                    # AUTO-SELECT point at current frame for immediate superior selection experience
                    self._auto_select_point_at_current_frame()

                    # Update frame range based on all trajectories
                    self._update_frame_range_from_multi_data()

    def _get_unique_point_name(self, base_name: str) -> str:
        """
        Generate a unique point name by appending a suffix if needed.

        Args:
            base_name: The desired point name

        Returns:
            A unique point name that doesn't conflict with existing names
        """
        curve_names = self._app_state.get_all_curve_names()
        if base_name not in curve_names:
            return base_name

        # Find a unique suffix
        suffix = 2
        while f"{base_name}_{suffix}" in curve_names:
            suffix += 1

        return f"{base_name}_{suffix}"

    def _auto_select_point_at_current_frame(self) -> None:
        """
        Auto-select the point at the current frame to provide immediate superior selection experience.
        If no point exists at current frame, select the first point as fallback.
        """
        if not self.main_window.curve_widget:
            return

        # Get current frame from state manager (gracefully handle missing state manager for tests)
        current_frame = 1  # Default fallback
        if hasattr(self.main_window, "state_manager") and self.main_window.state_manager:
            current_frame = getattr(self.main_window.state_manager, "current_frame", 1)

        # Try to find and select the point at current frame
        curve_data = self.main_window.curve_widget.curve_data
        if curve_data:
            # Look for point at current frame
            for i, point in enumerate(curve_data):
                frame = point[0]  # First element is frame number
                if frame == current_frame:
                    # Found point at current frame - select it
                    self.main_window.curve_widget._curve_store.select(i)
                    logger.debug(f"Auto-selected point at frame {current_frame} (index {i})")
                    return

            # No point at current frame - select first point as fallback
            if len(curve_data) > 0:
                self.main_window.curve_widget._curve_store.select(0)
                logger.debug(f"No point at frame {current_frame}, auto-selected first point (index 0)")

    def _sync_tracking_selection_to_curve_store(self, point_names: list[str]) -> None:
        """
        Synchronize TrackingPanel selection to CurveDataStore selection state.

        This fixes the TrackingPanel→CurveDataStore gap by ensuring manual selections
        in the tracking panel are reflected in the curve store's selection state.

        Args:
            point_names: List of selected point names from TrackingPanel
        """
        if not self.main_window.curve_widget or not point_names:
            return

        # Get the active curve (last selected point)
        active_curve_name = point_names[-1] if point_names else None
        if not active_curve_name or active_curve_name not in self._app_state.get_all_curve_names():
            return

        # Get current frame to find the appropriate point to select
        current_frame = 1  # Default fallback
        if hasattr(self.main_window, "state_manager") and self.main_window.state_manager:
            current_frame = getattr(self.main_window.state_manager, "current_frame", 1)

        # Find the point at the current frame in the active curve
        curve_data = self._app_state.get_curve_data(active_curve_name)
        for i, point in enumerate(curve_data):
            frame = point[0]
            if frame == current_frame:
                # Select this point in the CurveDataStore
                if hasattr(self.main_window.curve_widget, "_curve_store"):
                    self.main_window.curve_widget._curve_store.select(i)
                    logger.debug(f"Synced TrackingPanel selection to CurveDataStore: point {i} at frame {frame}")
                return

        # If no point at current frame, select the first point as fallback
        if len(curve_data) > 0:
            if hasattr(self.main_window.curve_widget, "_curve_store"):
                self.main_window.curve_widget._curve_store.select(0)
                logger.debug("Synced TrackingPanel selection to CurveDataStore: fallback to first point (index 0)")

    def on_tracking_points_selected(self, point_names: list[str]) -> None:
        """
        Handle selection of tracking points from panel.

        Args:
            point_names: List of selected point names (for multi-selection in panel)
        """
        # Set the last selected point as the active timeline point (last clicked becomes active)
        # Note: point_names can be multiple for visual selection, but only one is "active" for timeline
        self.main_window.active_timeline_point = point_names[-1] if point_names else None

        # Update the curve display with MANUAL_SELECTION context to preserve user selection intent
        # This prevents auto-selection from overriding the user's manual selection
        self.update_curve_display(SelectionContext.MANUAL_SELECTION)

        # Synchronize selection state to CurveDataStore (fix TrackingPanel→CurveDataStore gap)
        self._sync_tracking_selection_to_curve_store(point_names)

        # Synchronize table selection to show all selected points (visual selection)
        if self.main_window.tracking_panel:
            self.main_window.tracking_panel.set_selected_points(point_names)

        # Center view on selected point at current frame
        # Small delay to ensure curve data and point selection are processed
        if self.main_window.curve_widget and point_names:
            if callable(getattr(self.main_window.curve_widget, "center_on_selection", None)):
                # Use small delay to allow widget updates to complete
                def safe_center_on_selection():
                    if self.main_window.curve_widget and not self.main_window.curve_widget.isHidden():
                        self.main_window.curve_widget.center_on_selection()

                QTimer.singleShot(10, safe_center_on_selection)
                logger.debug("Scheduled centering on selected point after 10ms delay")

        logger.debug(f"Selected tracking points: {point_names}")

    def on_curve_selection_changed(self, selection: set[int]) -> None:
        """
        Handle selection changes from CurveDataStore (bidirectional synchronization).

        This provides visual feedback in the tracking panel when point selection changes
        in the curve view, completing the bidirectional sync between systems.

        Args:
            selection: Set of selected point indices from CurveDataStore
        """
        if not self.main_window.tracking_panel:
            return

        # If no selection, clear TrackingPanel selection
        if not selection:
            self.main_window.tracking_panel.set_selected_points([])
            return

        # Find which curve contains the selected points by examining the current active timeline point
        # The CurveDataStore selection represents points in the currently displayed single curve
        active_curve_name = self.main_window.active_timeline_point

        if active_curve_name and active_curve_name in self._app_state.get_all_curve_names():
            # Update TrackingPanel to highlight the curve that contains the selected points
            # This bridges point-level selection (CurveDataStore) with curve-level selection (TrackingPanel)
            selected_curves = [active_curve_name]

            # Ensure active_timeline_point is set (it should already be, but verify consistency)
            if not self.main_window.active_timeline_point:
                self.main_window.active_timeline_point = active_curve_name

            # Update TrackingPanel visual state
            self.main_window.tracking_panel.set_selected_points(selected_curves)

            logger.debug(
                f"Updated tracking panel for curve selection: {len(selection)} points selected in '{active_curve_name}'"
            )
        else:
            logger.debug(f"Could not determine curve for selection: {len(selection)} points selected, no active curve")

    def on_point_visibility_changed(self, point_name: str, visible: bool) -> None:
        """
        Handle visibility change for a tracking point.

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
            # Fallback to full display update
            self.update_curve_display(SelectionContext.DEFAULT)
        logger.debug(f"Point {point_name} visibility changed to {visible}")

    def on_point_color_changed(self, point_name: str, color: str) -> None:
        """
        Handle color change for a tracking point.

        Args:
            point_name: Name of the tracking point
            color: New color for the point
        """
        # Update curve color directly if multi-curve is supported
        if self.main_window.curve_widget is not None and callable(
            getattr(self.main_window.curve_widget, "update_curve_color", None)
        ):
            self.main_window.curve_widget.update_curve_color(point_name, color)
        else:
            # Fallback to full display update
            self.update_curve_display(SelectionContext.DEFAULT)
        logger.debug(f"Point {point_name} color changed to {color}")

    def on_point_deleted(self, point_name: str) -> None:
        """
        Handle deletion of a tracking point.

        Args:
            point_name: Name of the tracking point to delete
        """
        if point_name in self._app_state.get_all_curve_names():
            self._app_state.delete_curve(point_name)
            # If this was the active timeline point, clear it
            if self.main_window.active_timeline_point == point_name:
                self.main_window.active_timeline_point = None
            # Clean up tracking direction mapping
            if point_name in self.point_tracking_directions:
                del self.point_tracking_directions[point_name]
            self.update_tracking_panel()
            self.update_curve_display(SelectionContext.DEFAULT)
            logger.info(f"Deleted tracking point: {point_name}")

    def on_point_renamed(self, old_name: str, new_name: str) -> None:
        """
        Handle renaming of a tracking point.

        Args:
            old_name: Current name of the tracking point
            new_name: New name for the tracking point
        """
        if old_name in self._app_state.get_all_curve_names():
            # Get the curve data before deleting
            curve_data = self._app_state.get_curve_data(old_name)
            curve_metadata = self._app_state.get_curve_metadata(old_name)
            # Delete old name and create new name
            self._app_state.delete_curve(old_name)
            self._app_state.set_curve_data(new_name, curve_data, curve_metadata)
            # If this was the active timeline point, update to new name
            if self.main_window.active_timeline_point == old_name:
                self.main_window.active_timeline_point = new_name
            # Update tracking direction mapping
            if old_name in self.point_tracking_directions:
                self.point_tracking_directions[new_name] = self.point_tracking_directions.pop(old_name)
            self.update_tracking_panel()
            logger.info(f"Renamed tracking point: {old_name} -> {new_name}")

    @Slot(str, object)
    def on_tracking_direction_changed(self, point_name: str, new_direction: object) -> None:
        """
        Handle tracking direction change for a point.

        Updates keyframe statuses based on the new tracking direction,
        mirroring 3DEqualizer's behavior patterns. Creates an undoable
        command for status changes.

        Args:
            point_name: Name of the tracking point
            new_direction: New tracking direction (passed as object from signal)
        """
        if point_name not in self._app_state.get_all_curve_names():
            logger.warning(f"Tracking direction changed for unknown point: {point_name}")
            return

        # Convert object back to TrackingDirection (signal passes as object)
        if not isinstance(new_direction, TrackingDirection):
            logger.error(f"Invalid tracking direction type: {type(new_direction)}")
            return

        # Get previous direction (default to forward if unknown)
        previous_direction = self.point_tracking_directions.get(point_name, TrackingDirection.TRACKING_FW)

        # Skip update if direction hasn't actually changed
        if previous_direction == new_direction:
            logger.debug(f"Tracking direction unchanged for {point_name}: {new_direction.value}")
            return

        logger.info(f"Tracking direction changed for {point_name}: {previous_direction.value} -> {new_direction.value}")

        # Get curve data and calculate what will change
        curve_data = self._app_state.get_curve_data(point_name)
        updated_data = update_keyframe_status_for_tracking_direction(curve_data, new_direction, previous_direction)

        # Detect status changes - build list of (index, old_status, new_status)
        status_changes = []
        for i, (old_point, new_point) in enumerate(zip(curve_data, updated_data)):
            old_status = old_point[3] if len(old_point) > 3 else "keyframe"
            new_status = new_point[3] if len(new_point) > 3 else "keyframe"
            if old_status != new_status:
                status_changes.append((i, old_status, new_status))

        logger.debug(f"Detected {len(status_changes)} status changes for direction change")

        # Create and execute command for undo support (only for active curve)
        if status_changes and self.main_window.active_timeline_point == point_name:
            from core.commands.curve_commands import SetPointStatusCommand
            from services import get_interaction_service

            command = SetPointStatusCommand(
                description=f"Change tracking direction to {new_direction.value}",
                changes=status_changes,
            )

            interaction_service = get_interaction_service()
            if interaction_service:
                success = interaction_service.command_manager.execute_command(
                    command, cast(MainWindowProtocol, cast(object, self.main_window))
                )

                if success:
                    # Sync ApplicationState from curve_store after command executes
                    if self.main_window.curve_widget and hasattr(self.main_window.curve_widget, "_curve_store"):
                        updated_curve_data = self.main_window.curve_widget._curve_store.get_data()
                        self._app_state.set_curve_data(point_name, updated_curve_data)
                        logger.info("Synced ApplicationState from curve store after direction change")
                else:
                    logger.error("Failed to execute direction change command")
                    return
            else:
                logger.warning("InteractionService not available, updating data directly")
                self._app_state.set_curve_data(point_name, updated_data)
        else:
            # Not active curve or no changes - just update ApplicationState
            self._app_state.set_curve_data(point_name, updated_data)

        # Store the new direction
        self.point_tracking_directions[point_name] = new_direction

        # Update the curve display if this is the active timeline point
        if self.main_window.active_timeline_point == point_name:
            # Force repaint to update colors immediately
            if self.main_window.curve_widget:
                self.main_window.curve_widget.update()

        # Update the tracking panel to reflect any status changes
        self.update_tracking_panel()

        logger.info(f"Keyframe status update completed for {point_name}")

    def _should_update_curve_store_data(self, active_curve: str, context: SelectionContext) -> bool:
        """
        Determine if we should overwrite the curve store data with tracking controller data.

        This prevents overwriting curve store data that may have updated status information
        with stale data from the tracking controller.

        Args:
            active_curve: Name of the active curve
            context: Selection context

        Returns:
            True if curve store should be updated, False to preserve existing data
        """
        # Always update for these contexts (switching trajectories or loading new data)
        if context in (SelectionContext.DATA_LOADING, SelectionContext.CURVE_SWITCHING):
            return True

        # For manual selection and default contexts, check if we should preserve existing data
        if not self.main_window.curve_widget or not hasattr(self.main_window.curve_widget, "_curve_store"):
            return True  # Fallback to update if curve store not available

        # Get current curve store data
        current_store_data = self.main_window.curve_widget._curve_store.get_data()
        tracking_data = (
            self._app_state.get_curve_data(active_curve)
            if active_curve in self._app_state.get_all_curve_names()
            else []
        )

        # Handle Mock objects in tests and validate data types
        try:
            if not current_store_data:
                return True

            # Ensure we have list-like objects with len() method
            if not hasattr(current_store_data, "__len__") or not hasattr(tracking_data, "__len__"):
                return True

            # If curve store has different number of points, update it
            if len(current_store_data) != len(tracking_data):
                return True
        except (TypeError, AttributeError):
            # Handle cases where objects don't support len() or comparison
            logger.debug(f"Data comparison failed for trajectory '{active_curve}', defaulting to update")
            return True

        # Check if curve store has the same trajectory (same frame numbers)
        # If so, preserve it to maintain status changes made by user
        try:
            store_frames = set(point[0] for point in current_store_data if len(point) >= 1)
            tracking_frames = set(point[0] for point in tracking_data if len(point) >= 1)

            if store_frames == tracking_frames:
                # Same trajectory - preserve store data to maintain status changes
                logger.debug(
                    f"Trajectory '{active_curve}' already in curve store with same frames, preserving status changes"
                )
                return False
            else:
                # Different trajectory - update with tracking data
                logger.debug("Different trajectory detected, updating curve store")
                return True

        except (IndexError, TypeError, AttributeError) as e:
            logger.warning(f"Error comparing trajectory data: {e}, defaulting to update")
            return True

    def update_tracking_panel(self) -> None:
        """Update tracking panel with current tracking data."""
        if self.main_window.tracking_panel:
            # Build dict from ApplicationState for tracking panel
            all_tracked_data = {}
            for curve_name in self._app_state.get_all_curve_names():
                all_tracked_data[curve_name] = self._app_state.get_curve_data(curve_name)
            self.main_window.tracking_panel.set_tracked_data(all_tracked_data)  # pyright: ignore[reportArgumentType]

    def update_curve_display(self, context: SelectionContext = SelectionContext.DEFAULT) -> None:
        """Update curve display with selected tracking points.

        Args:
            context: Context for this update to control auto-selection behavior
        """
        if not self.main_window.curve_widget:
            return

        # CRITICAL: Save PREVIOUS curve data back to ApplicationState before switching
        # This ensures modifications (endframes, nudges, etc.) are preserved
        if self._previous_active_curve and self._previous_active_curve in self._app_state.get_all_curve_names():
            # Get current data from curve widget's store (contains previous curve's data)
            if hasattr(self.main_window.curve_widget, "_curve_store"):
                current_data = self.main_window.curve_widget._curve_store.get_data()
                if current_data:
                    self._app_state.set_curve_data(self._previous_active_curve, current_data)
                    logger.debug(f"Saved modifications for '{self._previous_active_curve}' back to ApplicationState")

        # Update previous active curve for next switch
        self._previous_active_curve = self.main_window.active_timeline_point

        # Check if curve widget supports multi-curve display
        if self.main_window.curve_widget is not None and callable(
            getattr(self.main_window.curve_widget, "set_curves_data", None)
        ):
            # Get metadata from tracking panel if available
            metadata: dict[str, dict[str, str | bool]] = {}
            if self.main_window.tracking_panel is not None:
                # Use public interface for getting point metadata
                for name in self._app_state.get_all_curve_names():
                    metadata[name] = {
                        "visible": self.main_window.tracking_panel.get_point_visibility(name),
                        "color": self.main_window.tracking_panel.get_point_color(name),
                    }

            # Build curves dict from ApplicationState
            all_curves_data = {}
            for curve_name in self._app_state.get_all_curve_names():
                all_curves_data[curve_name] = self._app_state.get_curve_data(curve_name)

            # Set all curves with the active timeline point - UNIFIED APPROACH
            active_curve = self.main_window.active_timeline_point

            # Only preserve selection for DEFAULT context (general updates like color/visibility changes)
            # For explicit actions (MANUAL_SELECTION, DATA_LOADING, CURVE_SWITCHING), reset selection
            if context == SelectionContext.DEFAULT:
                # Preserve existing selection by not passing selected_curves parameter
                # This supports Ctrl+click multi-curve selection in curve view
                self.main_window.curve_widget.set_curves_data(
                    all_curves_data,
                    metadata,
                    active_curve,
                    # selected_curves omitted - preserves existing selection
                )
            elif context == SelectionContext.MANUAL_SELECTION:
                # For tracking panel selection, use ALL selected curves from panel
                # This fixes the bug where only one curve displays when selecting multiple
                selected_curves_list = []
                if self.main_window.tracking_panel:
                    selected_curves_list = self.main_window.tracking_panel.get_selected_points()

                # Fallback to active curve if no selection available
                if not selected_curves_list and active_curve:
                    selected_curves_list = [active_curve]

                self.main_window.curve_widget.set_curves_data(
                    all_curves_data,
                    metadata,
                    active_curve,
                    selected_curves=selected_curves_list,
                )
            else:
                # Reset selection for other explicit actions (DATA_LOADING, CURVE_SWITCHING)
                self.main_window.curve_widget.set_curves_data(
                    all_curves_data,
                    metadata,
                    active_curve,
                    selected_curves=[active_curve] if active_curve else [],  # Reset to active curve
                )

            # CONDITIONAL AUTO-SELECT: Only auto-select in appropriate contexts for the active curve
            # This provides point-level selection within the multi-curve system
            if (
                active_curve
                and active_curve in self._app_state.get_all_curve_names()
                and context
                in (
                    SelectionContext.DATA_LOADING,
                    SelectionContext.CURVE_SWITCHING,
                    SelectionContext.DEFAULT,
                    SelectionContext.MANUAL_SELECTION,
                )
            ):
                # CRITICAL FIX: Avoid overwriting curve store data with stale data
                # Check if curve store already has the correct trajectory before overwriting
                should_update_curve_data = self._should_update_curve_store_data(active_curve, context)

                if should_update_curve_data:
                    # Switch to single-curve mode for point-level selection
                    active_curve_data = self._app_state.get_curve_data(active_curve)
                    self.main_window.curve_widget.set_curve_data(active_curve_data)
                    logger.debug(f"Updated curve store data for trajectory '{active_curve}' in context {context.name}")
                else:
                    logger.debug(
                        f"Preserved existing curve store data for trajectory '{active_curve}' to maintain status changes"
                    )

                self._auto_select_point_at_current_frame()
        else:
            # Fallback to single curve display for backward compatibility
            active_point = self.main_window.active_timeline_point
            if active_point and active_point in self._app_state.get_all_curve_names():
                trajectory = self._app_state.get_curve_data(active_point)
                self.main_window.curve_widget.set_curve_data(trajectory)

                # CONDITIONAL AUTO-SELECT: Only auto-select in appropriate contexts
                if context in (
                    SelectionContext.DATA_LOADING,
                    SelectionContext.CURVE_SWITCHING,
                    SelectionContext.DEFAULT,
                ):
                    self._auto_select_point_at_current_frame()
            else:
                self.main_window.curve_widget.set_curve_data([])

    def _update_frame_range_from_data(
        self, data: list[tuple[int, float, float] | tuple[int, float, float, str]]
    ) -> None:
        """
        Update frame range UI elements based on single trajectory data.

        Args:
            data: Trajectory data
        """
        if data:
            max_frame = max(point[0] for point in data)
            try:
                if self.main_window.frame_slider:
                    self.main_window.frame_slider.setMaximum(max_frame)
                if self.main_window.frame_spinbox:
                    self.main_window.frame_spinbox.setMaximum(max_frame)
                if self.main_window.total_frames_label:
                    self.main_window.total_frames_label.setText(str(max_frame))
                # Update state manager's total frames
                self.main_window.state_manager.total_frames = max_frame
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
                    self.main_window.frame_slider.setMaximum(max_frame)
                if self.main_window.frame_spinbox:
                    self.main_window.frame_spinbox.setMaximum(max_frame)
                if self.main_window.total_frames_label:
                    self.main_window.total_frames_label.setText(str(max_frame))
                self.main_window.state_manager.total_frames = max_frame
            except RuntimeError:
                # Widgets may have been deleted during application shutdown
                pass

    def clear_tracking_data(self) -> None:
        """Clear all tracking data."""
        # Delete all curves from ApplicationState
        for curve_name in list(self._app_state.get_all_curve_names()):
            self._app_state.delete_curve(curve_name)
        self.main_window.active_timeline_point = None
        self.point_tracking_directions.clear()
        self.update_tracking_panel()
        self.update_curve_display(SelectionContext.DEFAULT)
        logger.info("Cleared all tracking data")

    def get_active_trajectory(self) -> CurveDataList | None:
        """
        Get the currently active trajectory data.

        Returns:
            Active trajectory data or None if no active timeline point
        """
        active_point = self.main_window.active_timeline_point
        if active_point and active_point in self._app_state.get_all_curve_names():
            return self._app_state.get_curve_data(active_point)
        return None

    def has_tracking_data(self) -> bool:
        """
        Check if any tracking data is loaded.

        Returns:
            True if tracking data exists, False otherwise
        """
        return len(self._app_state.get_all_curve_names()) > 0

    def get_tracking_point_names(self) -> list[str]:
        """
        Get list of all tracking point names.

        Returns:
            List of tracking point names
        """
        return list(self._app_state.get_all_curve_names())

    # ==================== Multi-Curve Display Methods (Phase 6) ====================

    def toggle_show_all_curves(self, show_all: bool) -> None:
        """
        Toggle whether to show all curves or just the active one.

        Args:
            show_all: If True, show all visible curves; if False, show only active curve
        """
        if not self.main_window.curve_widget:
            return

        self.main_window.curve_widget.show_all_curves = show_all
        self.main_window.curve_widget.update()
        logger.debug(f"Show all curves: {show_all}")

    def set_selected_curves(self, curve_names: list[str]) -> None:
        """
        Set which curves are currently selected for display.

        When show_all_curves is False, only these selected curves will be displayed.
        The last curve in the list becomes the active curve for editing.

        Args:
            curve_names: List of curve names to select and display
        """
        if not self.main_window.curve_widget:
            return

        widget = self.main_window.curve_widget
        widget.selected_curve_names = set(curve_names)
        widget.selected_curves_ordered = list(curve_names)

        # Set the last selected as the active curve for editing
        all_curve_names = self._app_state.get_all_curve_names()
        if curve_names and curve_names[-1] in all_curve_names:
            widget.set_active_curve(curve_names[-1])

        widget.update()
        logger.debug(f"Selected curves: {widget.selected_curve_names}, Active: {self._app_state.active_curve}")

    def center_on_selected_curves(self) -> None:
        """
        Center the view on all selected curves.

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
        widget._center_view_on_point(center_x, center_y)

        widget.invalidate_caches()
        widget.update()
        widget.view_changed.emit()

    # ==================== ApplicationState Signal Handlers ====================

    def _on_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
        """
        React to curve data changes from ApplicationState.

        This handler is called when any curve data is modified through ApplicationState,
        ensuring the tracking panel and curve display stay synchronized.

        Args:
            curves: Dictionary of all curves in ApplicationState
        """
        # Prevent recursion: If we're already handling a signal, don't process nested signals
        if self._handling_signal:
            return

        try:
            self._handling_signal = True

            # Update tracking panel to reflect data changes
            self.update_tracking_panel()

            # NOTE: Do NOT call update_curve_display() here as it can trigger more
            # set_curve_data() calls, creating a signal loop. The tracking panel
            # update is sufficient for reactive updates.

        finally:
            self._handling_signal = False

    def _on_active_curve_changed(self, curve_name: str) -> None:
        """
        React to active curve changes from ApplicationState.

        This handler is called when the active curve is changed through ApplicationState,
        ensuring the UI reflects the new active state.

        Args:
            curve_name: Name of the newly active curve (empty string if None)
        """
        # Prevent recursion: If we're already handling a signal, don't process nested signals
        if self._handling_signal:
            return

        try:
            self._handling_signal = True

            # Update active timeline point to match ApplicationState
            if curve_name and curve_name != "__default__":
                self.main_window.active_timeline_point = curve_name
                # NOTE: Do NOT call update_curve_display() here to avoid signal loops

        finally:
            self._handling_signal = False
