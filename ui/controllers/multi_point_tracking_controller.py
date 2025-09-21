#!/usr/bin/env python
"""
Multi-Point Tracking Controller for CurveEditor.

This controller manages multi-point tracking data, including loading,
selection, and display of multiple tracking trajectories.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, Slot
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from ui.main_window import MainWindow

from core.logger_utils import get_logger
from core.type_aliases import CurveDataList

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

            # Set up view for pixel-coordinate tracking data BEFORE setting data
            self.main_window.curve_widget.setup_for_pixel_tracking()
            self.main_window.curve_widget.set_curve_data(data)  # pyright: ignore[reportArgumentType]
            self.main_window.state_manager.set_track_data(data, mark_modified=False)  # pyright: ignore[reportArgumentType]
            logger.info(f"Loaded {len(data)} tracking points from background thread")

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
            # Store the multi-point tracking data
            self.tracked_data = multi_data
            self.active_points = list(multi_data.keys())[:1]  # Select first point by default

            logger.info(f"Loaded {len(multi_data)} tracking points from multi-point file")

            # Update the tracking panel with the multi-point data
            self.update_tracking_panel()

            # Display the first point's trajectory
            if self.active_points and self.main_window.curve_widget:
                first_point = self.active_points[0]
                if first_point in self.tracked_data:
                    # Set up view for pixel-coordinate tracking data
                    self.main_window.curve_widget.setup_for_pixel_tracking()
                    trajectory = self.tracked_data[first_point]
                    self.main_window.curve_widget.set_curve_data(trajectory)  # pyright: ignore[reportArgumentType]
                    self.main_window.state_manager.set_track_data(trajectory, mark_modified=False)  # pyright: ignore[reportArgumentType]

                    # Update frame range based on all trajectories
                    self._update_frame_range_from_multi_data()

    def on_tracking_points_selected(self, point_names: list[str]) -> None:
        """
        Handle selection of tracking points from panel.

        Args:
            point_names: List of selected point names
        """
        self.active_points = point_names
        self.update_curve_display()
        logger.debug(f"Selected tracking points: {point_names}")

    def on_point_visibility_changed(self, point_name: str, visible: bool) -> None:
        """
        Handle visibility change for a tracking point.

        Args:
            point_name: Name of the tracking point
            visible: Whether the point should be visible
        """
        # Update display to show/hide the trajectory
        self.update_curve_display()
        logger.debug(f"Point {point_name} visibility changed to {visible}")

    def on_point_color_changed(self, point_name: str, color: str) -> None:
        """
        Handle color change for a tracking point.

        Args:
            point_name: Name of the tracking point
            color: New color for the point
        """
        # Update display with new color
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
            self.update_tracking_panel()
            logger.info(f"Renamed tracking point: {old_name} -> {new_name}")

    def update_tracking_panel(self) -> None:
        """Update tracking panel with current tracking data."""
        if self.main_window.tracking_panel:
            self.main_window.tracking_panel.set_tracked_data(self.tracked_data)

    def update_curve_display(self) -> None:
        """Update curve display with selected tracking points."""
        if not self.main_window.curve_widget:
            return

        # For now, display the first selected point's trajectory
        # TODO: Support multiple trajectory display
        if self.active_points and self.active_points[0] in self.tracked_data:
            trajectory = self.tracked_data[self.active_points[0]]
            self.main_window.curve_widget.set_curve_data(trajectory)
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
