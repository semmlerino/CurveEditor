#!/usr/bin/env python
"""
Multi-Point Tracking Controller for CurveEditor.

This controller manages multi-point tracking data, including loading,
selection, and display of multiple tracking trajectories.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, QTimer, Slot
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from ui.main_window import MainWindow

from core.logger_utils import get_logger
from core.models import TrackingDirection
from core.type_aliases import CurveDataList
from data.tracking_direction_utils import update_keyframe_status_for_tracking_direction

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

        # Tracking data storage
        self.tracked_data: dict[str, CurveDataList] = {}  # All tracking points
        self.active_points: list[str] = []  # Currently selected points
        self.point_tracking_directions: dict[str, TrackingDirection] = {}  # Track previous directions

        logger.info("MultiPointTrackingController initialized")

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
            if self.tracked_data:
                # We have existing data - add this as a new point
                base_name = "Track"
                point_name = self._get_unique_point_name(base_name)
                self.tracked_data[point_name] = data  # pyright: ignore[reportArgumentType]
                self.active_points = [point_name]  # Select the newly loaded point
                # Initialize with default tracking direction
                self.point_tracking_directions[point_name] = TrackingDirection.TRACKING_FW
                logger.info(
                    f"Added single trajectory as '{point_name}' to existing {len(self.tracked_data) - 1} points"
                )

                # Update the tracking panel to show the new point
                self.update_tracking_panel()
            else:
                # No existing data - create initial tracked_data with this trajectory
                self.tracked_data = {"Track1": data}  # pyright: ignore[reportAttributeAccessIssue]
                self.active_points = ["Track1"]
                # Initialize with default tracking direction
                self.point_tracking_directions["Track1"] = TrackingDirection.TRACKING_FW
                logger.info("Loaded single trajectory as 'Track1'")

                # Update the tracking panel
                self.update_tracking_panel()

            # Set up view for pixel-coordinate tracking data BEFORE setting data
            self.main_window.curve_widget.setup_for_pixel_tracking()
            self.main_window.curve_widget.set_curve_data(data)  # pyright: ignore[reportArgumentType]
            self.main_window.state_manager.set_track_data(data, mark_modified=False)  # pyright: ignore[reportArgumentType]

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
            if self.tracked_data:
                # We have existing data - merge the new points
                logger.info(f"Merging {len(multi_data)} new points with {len(self.tracked_data)} existing points")

                # Track newly added points for selection
                new_point_names = []

                for point_name, trajectory in multi_data.items():
                    # Check for naming conflicts and resolve them
                    unique_name = self._get_unique_point_name(point_name)
                    self.tracked_data[unique_name] = trajectory
                    new_point_names.append(unique_name)
                    # Initialize with default tracking direction
                    self.point_tracking_directions[unique_name] = TrackingDirection.TRACKING_FW

                    if unique_name != point_name:
                        logger.info(f"Renamed duplicate point '{point_name}' to '{unique_name}'")

                # If no points were selected, select the first new point
                if not self.active_points and new_point_names:
                    self.active_points = [new_point_names[0]]

                logger.info(f"Total points after merge: {len(self.tracked_data)}")
            else:
                # No existing data - use the new data directly
                self.tracked_data = multi_data
                self.active_points = list(multi_data.keys())[:1]  # Select first point by default
                # Initialize all points with default tracking direction
                for point_name in multi_data.keys():
                    self.point_tracking_directions[point_name] = TrackingDirection.TRACKING_FW
                logger.info(f"Loaded {len(multi_data)} tracking points from multi-point file")

            # Update the tracking panel with the multi-point data
            self.update_tracking_panel()

            # Display the active trajectory (could be existing or newly loaded)
            if self.active_points and self.main_window.curve_widget:
                first_point = self.active_points[0]
                if first_point in self.tracked_data:
                    # Set up view for pixel-coordinate tracking data
                    self.main_window.curve_widget.setup_for_pixel_tracking()
                    trajectory = self.tracked_data[first_point]
                    self.main_window.curve_widget.set_curve_data(trajectory)
                    self.main_window.state_manager.set_track_data(trajectory, mark_modified=False)  # pyright: ignore[reportArgumentType]

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
        if base_name not in self.tracked_data:
            return base_name

        # Find a unique suffix
        suffix = 2
        while f"{base_name}_{suffix}" in self.tracked_data:
            suffix += 1

        return f"{base_name}_{suffix}"

    def on_tracking_points_selected(self, point_names: list[str]) -> None:
        """
        Handle selection of tracking points from panel.

        Args:
            point_names: List of selected point names
        """
        self.active_points = point_names

        # Update the curve display (which now handles selection properly)
        self.update_curve_display()

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
            self.update_curve_display()
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
            self.update_curve_display()
        logger.debug(f"Point {point_name} color changed to {color}")

    def on_point_deleted(self, point_name: str) -> None:
        """
        Handle deletion of a tracking point.

        Args:
            point_name: Name of the tracking point to delete
        """
        if point_name in self.tracked_data:
            del self.tracked_data[point_name]
            if point_name in self.active_points:
                self.active_points.remove(point_name)
            # Clean up tracking direction mapping
            if point_name in self.point_tracking_directions:
                del self.point_tracking_directions[point_name]
            self.update_tracking_panel()
            self.update_curve_display()
            logger.info(f"Deleted tracking point: {point_name}")

    def on_point_renamed(self, old_name: str, new_name: str) -> None:
        """
        Handle renaming of a tracking point.

        Args:
            old_name: Current name of the tracking point
            new_name: New name for the tracking point
        """
        if old_name in self.tracked_data:
            self.tracked_data[new_name] = self.tracked_data.pop(old_name)
            if old_name in self.active_points:
                idx = self.active_points.index(old_name)
                self.active_points[idx] = new_name
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
        mirroring 3DEqualizer's behavior patterns.

        Args:
            point_name: Name of the tracking point
            new_direction: New tracking direction (passed as object from signal)
        """
        if point_name not in self.tracked_data:
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

        logger.info(f"Tracking direction changed for {point_name}: {previous_direction.value} → {new_direction.value}")

        # Update keyframe statuses based on new direction
        curve_data = self.tracked_data[point_name]
        updated_data = update_keyframe_status_for_tracking_direction(curve_data, new_direction, previous_direction)

        # Update the stored data
        self.tracked_data[point_name] = updated_data

        # Store the new direction
        self.point_tracking_directions[point_name] = new_direction

        # Update the curve display if this is the active point
        if point_name in self.active_points:
            self.update_curve_display()

        # Update the tracking panel to reflect any status changes
        self.update_tracking_panel()

        logger.info(f"Keyframe status update completed for {point_name}")

    def update_tracking_panel(self) -> None:
        """Update tracking panel with current tracking data."""
        if self.main_window.tracking_panel:
            self.main_window.tracking_panel.set_tracked_data(self.tracked_data)

    def update_curve_display(self) -> None:
        """Update curve display with selected tracking points."""
        if not self.main_window.curve_widget:
            return

        # Check if curve widget supports multi-curve display
        if self.main_window.curve_widget is not None and callable(
            getattr(self.main_window.curve_widget, "set_curves_data", None)
        ):
            # Get metadata from tracking panel if available
            metadata: dict[str, dict[str, str | bool]] = {}
            if self.main_window.tracking_panel is not None:
                # Use public interface for getting point metadata
                for name in self.tracked_data:
                    metadata[name] = {
                        "visible": self.main_window.tracking_panel.get_point_visibility(name),
                        "color": self.main_window.tracking_panel.get_point_color(name),
                    }

            # Set all curves with the active points as selected
            active_curve = self.active_points[-1] if self.active_points else None  # Last selected is active
            self.main_window.curve_widget.set_curves_data(
                self.tracked_data,
                metadata,
                active_curve,
                selected_curves=self.active_points,  # Pass selected curves
            )

            # After setting curve data, select point at current frame for better centering
            if (
                active_curve
                and self.main_window.curve_widget is not None
                and callable(getattr(self.main_window.curve_widget, "select_point_at_frame", None))
            ):
                current_frame = getattr(self.main_window, "current_frame", 0)
                self.main_window.curve_widget.select_point_at_frame(current_frame)
                logger.debug(f"Selected point at frame {current_frame} for active curve {active_curve}")
        else:
            # Fallback to single curve display for backward compatibility
            if self.active_points and self.active_points[0] in self.tracked_data:
                trajectory = self.tracked_data[self.active_points[0]]
                self.main_window.curve_widget.set_curve_data(trajectory)

                # Select point at current frame for better centering
                if self.main_window.curve_widget is not None and callable(
                    getattr(self.main_window.curve_widget, "select_point_at_frame", None)
                ):
                    current_frame = getattr(self.main_window, "current_frame", 0)
                    self.main_window.curve_widget.select_point_at_frame(current_frame)
                    logger.debug(f"Selected point at frame {current_frame} for fallback display")
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
        for traj in self.tracked_data.values():
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
        self.tracked_data.clear()
        self.active_points.clear()
        self.point_tracking_directions.clear()
        self.update_tracking_panel()
        self.update_curve_display()
        logger.info("Cleared all tracking data")

    def get_active_trajectory(self) -> CurveDataList | None:
        """
        Get the currently active trajectory data.

        Returns:
            Active trajectory data or None if no active points
        """
        if self.active_points and self.active_points[0] in self.tracked_data:
            return self.tracked_data[self.active_points[0]]
        return None

    def has_tracking_data(self) -> bool:
        """
        Check if any tracking data is loaded.

        Returns:
            True if tracking data exists, False otherwise
        """
        return bool(self.tracked_data)

    def get_tracking_point_names(self) -> list[str]:
        """
        Get list of all tracking point names.

        Returns:
            List of tracking point names
        """
        return list(self.tracked_data.keys())
