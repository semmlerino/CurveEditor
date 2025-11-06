#!/usr/bin/env python
"""
TrackingDataController - Handles loading and managing tracking data.

Part of the MultiPointTrackingController split (PLAN TAU Phase 3 Task 3.1).
"""

from typing import cast

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import QApplication

from core.logger_utils import get_logger
from core.models import TrackingDirection
from core.type_aliases import CurveDataInput, CurveDataList
from data.tracking_direction_utils import update_keyframe_status_for_tracking_direction
from protocols.ui import MainWindowProtocol
from ui.controllers.base_tracking_controller import BaseTrackingController

logger = get_logger("tracking_data_controller")


class TrackingDataController(BaseTrackingController):
    """Handles loading and validating tracking data.

    Responsibilities:
        - Load single-point tracking data
        - Load multi-point tracking data
        - Parse and validate tracking files
        - Manage point lifecycle (delete, rename)
        - Handle tracking direction changes
        - Emit signals when data changes

    Signals:
        data_loaded: Emitted when tracking data successfully loaded (curve_name, curve_data)
        load_error: Emitted when loading fails (error_message)
        data_changed: Emitted when any tracking data changes
    """

    data_loaded: Signal = Signal(str, list)  # curve_name, curve_data
    load_error: Signal = Signal(str)
    data_changed: Signal = Signal()

    def __init__(self, main_window: MainWindowProtocol) -> None:
        """Initialize tracking data controller.

        Args:
            main_window: Main window protocol interface
        """
        super().__init__(main_window)

        # Track previous tracking directions for each point
        self.point_tracking_directions: dict[str, TrackingDirection] = {}

        logger.info("TrackingDataController initialized")

    @property
    def tracked_data(self) -> dict[str, CurveDataList]:
        """Get snapshot of all tracked curves.

        Returns a fresh dict on each call. Modifications won't persist.

        CORRECT (bulk replacement):
            controller.tracked_data = loaded_data  # Triggers setter ✓

        INCORRECT (item assignment):
            data = controller.tracked_data
            data[curve_name] = new_data  # Lost! Dict is temporary ✗

        RECOMMENDED (new code):
            Use ApplicationState directly per CLAUDE.md:
            app_state = get_application_state()
            app_state.set_curve_data(curve_name, data)
        """
        result: dict[str, CurveDataList] = {}
        for curve_name in self._app_state.get_all_curve_names():
            result[curve_name] = self._app_state.get_curve_data(curve_name)
        return result

    @tracked_data.setter
    def tracked_data(self, value: dict[str, CurveDataList]) -> None:
        """Set all tracked curve data in ApplicationState.

        Phase 4: Removed __default__ special handling - all curves treated equally.
        """
        # Clear existing curves
        for curve_name in list(self._app_state.get_all_curve_names()):
            self._app_state.delete_curve(curve_name)

        # Add all curves from the input dict
        for curve_name, curve_data in value.items():
            self._app_state.set_curve_data(curve_name, curve_data)

    @Slot(list)
    def on_tracking_data_loaded(self, data: CurveDataInput) -> None:
        """Handle single tracking trajectory loaded in background thread.

        This is a simplified version that only handles data storage.
        Display updates are handled by TrackingDisplayController via signals.

        Args:
            data: Single trajectory data loaded from file
        """
        current_thread = QThread.currentThread()
        app_instance = QApplication.instance()
        main_thread = app_instance.thread() if app_instance is not None else None
        logger.info(
            f"[THREAD-DEBUG] on_tracking_data_loaded executing in thread: {current_thread} (main={current_thread == main_thread})"
        )

        if not data:
            self.load_error.emit("No data loaded")
            return

        logger.debug(f"[DATA] Loaded {len(data)} points from background thread")
        # Log first few points for debugging
        for i in range(min(3, len(data))):
            logger.debug(f"[DATA] Point {i}: {data[i]}")

        # Add as a new tracking point to multi-point data
        existing_curves = self._app_state.get_all_curve_names()
        if existing_curves:
            # We have existing data - add this as a new point
            base_name = "Track"
            point_name = self.get_unique_point_name(base_name)
            self._app_state.set_curve_data(point_name, data)
            self._app_state.set_active_curve(point_name)  # Set as active curve
            # Initialize with default tracking direction
            self.point_tracking_directions[point_name] = TrackingDirection.TRACKING_FW
            logger.info(f"Added single trajectory as '{point_name}' to existing {len(existing_curves)} points")
        else:
            # No existing data - create initial data with this trajectory
            point_name = "Track1"
            self._app_state.set_curve_data(point_name, data)
            self._app_state.set_active_curve(point_name)
            # Initialize with default tracking direction
            self.point_tracking_directions[point_name] = TrackingDirection.TRACKING_FW
            logger.info("Loaded single trajectory as 'Track1'")

        # Emit signal for display controller to handle UI updates
        self.data_loaded.emit(point_name, data)
        self.data_changed.emit()

    @Slot(dict)
    def on_multi_point_data_loaded(self, multi_data: dict[str, CurveDataList]) -> None:
        """Handle multi-point tracking data loaded in background thread.

        This is a simplified version that only handles data storage.
        Display updates are handled by TrackingDisplayController via signals.

        Args:
            multi_data: Dictionary of point names to trajectory data
        """
        current_thread = QThread.currentThread()
        app_instance = QApplication.instance()
        main_thread = app_instance.thread() if app_instance is not None else None
        logger.info(
            f"[THREAD-DEBUG] on_multi_point_data_loaded executing in thread: {current_thread} (main={current_thread == main_thread})"
        )

        if not multi_data:
            self.load_error.emit("No data loaded")
            return

        # Merge with existing data instead of replacing
        existing_curves = self._app_state.get_all_curve_names()
        if existing_curves:
            # We have existing data - merge the new points
            logger.info(f"Merging {len(multi_data)} new points with {len(existing_curves)} existing points")

            # Track newly added points for selection
            new_point_names: list[str] = []

            for point_name, trajectory in multi_data.items():
                # Check for naming conflicts and resolve them
                unique_name = self.get_unique_point_name(point_name)
                self._app_state.set_curve_data(unique_name, trajectory)
                new_point_names.append(unique_name)
                # Initialize with default tracking direction
                self.point_tracking_directions[unique_name] = TrackingDirection.TRACKING_FW

                if unique_name != point_name:
                    logger.info(f"Renamed duplicate point '{point_name}' to '{unique_name}'")

            # If no curve is active, select the first new point
            if not self._app_state.active_curve and new_point_names:
                self._app_state.set_active_curve(new_point_names[0])

            all_curves_after_merge = self._app_state.get_all_curve_names()
            logger.info(f"Total points after merge: {len(all_curves_after_merge)}")

            # Emit for first loaded curve
            if new_point_names:
                first_curve_data = self._app_state.get_curve_data(new_point_names[0])
                self.data_loaded.emit(new_point_names[0], first_curve_data)
        else:
            # No existing data - use the new data directly
            for point_name, trajectory in multi_data.items():
                self._app_state.set_curve_data(point_name, trajectory)
            # Set first point as active curve by default
            first_point = next(iter(multi_data.keys())) if multi_data else None
            self._app_state.set_active_curve(first_point)
            # Initialize all points with default tracking direction
            for point_name in multi_data:
                self.point_tracking_directions[point_name] = TrackingDirection.TRACKING_FW
            logger.info(f"Loaded {len(multi_data)} tracking points from multi-point file")

            # Emit for first loaded curve
            if first_point:
                first_curve_data = self._app_state.get_curve_data(first_point)
                self.data_loaded.emit(first_point, first_curve_data)

        self.data_changed.emit()

    def get_unique_point_name(self, base_name: str) -> str:
        """Generate a unique point name by appending a suffix if needed.

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

    @Slot(str)
    def on_point_deleted(self, point_name: str) -> None:
        """Handle deletion of a tracking point.

        Args:
            point_name: Name of the tracking point to delete
        """
        if point_name in self._app_state.get_all_curve_names():
            self._app_state.delete_curve(point_name)
            # If this was the active curve, clear it
            if self._app_state.active_curve == point_name:
                self._app_state.set_active_curve(None)
            # Clean up tracking direction mapping
            if point_name in self.point_tracking_directions:
                del self.point_tracking_directions[point_name]

            self.data_changed.emit()
            logger.info(f"Deleted tracking point: {point_name}")

    @Slot(str, str)
    def on_point_renamed(self, old_name: str, new_name: str) -> None:
        """Handle renaming of a tracking point.

        Args:
            old_name: Current name of the tracking point
            new_name: New name for the tracking point
        """
        if old_name in self._app_state.get_all_curve_names():
            # Check if this is the active curve BEFORE deleting
            is_active = self._app_state.active_curve == old_name
            # Get the curve data before deleting
            curve_data = self._app_state.get_curve_data(old_name)
            curve_metadata = self._app_state.get_curve_metadata(old_name)
            # Delete old name and create new name
            self._app_state.delete_curve(old_name)
            self._app_state.set_curve_data(new_name, curve_data, curve_metadata)
            # If this was the active curve, update to new name
            if is_active:
                self._app_state.set_active_curve(new_name)
            # Update tracking direction mapping
            if old_name in self.point_tracking_directions:
                self.point_tracking_directions[new_name] = self.point_tracking_directions.pop(old_name)

            self.data_changed.emit()
            logger.info(f"Renamed tracking point: {old_name} -> {new_name}")

    @Slot(str, object)
    def on_tracking_direction_changed(self, point_name: str, new_direction: object) -> None:
        """Handle tracking direction change for a point.

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
        status_changes: list[tuple[int, str, str]] = []
        for i, (old_point, new_point) in enumerate(zip(curve_data, updated_data, strict=True)):
            old_status = str(old_point[3]) if len(old_point) > 3 else "keyframe"
            new_status = str(new_point[3]) if len(new_point) > 3 else "keyframe"
            if old_status != new_status:
                status_changes.append((i, old_status, new_status))

        logger.debug(f"Detected {len(status_changes)} status changes for direction change")

        # Create and execute command for undo support (only for active curve)
        if status_changes and self._app_state.active_curve == point_name:
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
                    # Sync ApplicationState from curve widget after command executes
                    if self.main_window.curve_widget:
                        updated_curve_data = self.main_window.curve_widget.curve_data
                        self._app_state.set_curve_data(point_name, updated_curve_data)
                        logger.info("Synced ApplicationState from curve widget after direction change")
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

        self.data_changed.emit()
        logger.info(f"Keyframe status update completed for {point_name}")

    def clear_tracking_data(self) -> None:
        """Clear all tracking data."""
        # Delete all curves from ApplicationState
        for curve_name in list(self._app_state.get_all_curve_names()):
            self._app_state.delete_curve(curve_name)
        self._app_state.set_active_curve(None)
        self.point_tracking_directions.clear()

        self.data_changed.emit()
        logger.info("Cleared all tracking data")

    def get_active_trajectory(self) -> CurveDataList | None:
        """Get the currently active trajectory data.

        Returns:
            Active trajectory data or None if no active curve
        """
        active_point = self._app_state.active_curve
        if active_point and active_point in self._app_state.get_all_curve_names():
            return self._app_state.get_curve_data(active_point)
        return None

    def has_tracking_data(self) -> bool:
        """Check if any tracking data is loaded.

        Returns:
            True if tracking data exists, False otherwise
        """
        return len(self._app_state.get_all_curve_names()) > 0

    def get_tracking_point_names(self) -> list[str]:
        """Get list of all tracking point names.

        Returns:
            List of tracking point names
        """
        return list(self._app_state.get_all_curve_names())
