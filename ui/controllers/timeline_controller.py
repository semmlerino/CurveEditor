#!/usr/bin/env python
"""
Timeline Controller for CurveEditor.

This controller manages the timeline tabs widget, including frame navigation,
status updates, and synchronization with curve data changes.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Slot

if TYPE_CHECKING:
    from ui.main_window import MainWindow

from core.logger_utils import get_logger
from core.type_aliases import CurveDataList
from services import get_data_service
from stores import get_store_manager

logger = get_logger("timeline_controller")


class TimelineController:
    """
    Controller for managing timeline tabs functionality.

    Extracted from MainWindow to centralize all timeline-related logic,
    including frame status updates, navigation, and data synchronization.
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Initialize the timeline controller.

        Args:
            main_window: Reference to the main window for UI access
        """
        self.main_window = main_window

        # Get reactive data store
        self._store_manager = get_store_manager()
        self._curve_store = self._store_manager.get_curve_store()

        logger.info("TimelineController initialized")

    @Slot(int)
    def on_timeline_tab_clicked(self, frame: int) -> None:
        """
        Handle timeline tab click to navigate to frame.

        Args:
            frame: Frame number that was clicked
        """
        # Update spinbox which will trigger frame change
        if self.main_window.frame_spinbox:
            self.main_window.frame_spinbox.setValue(frame)
        logger.debug(f"Timeline tab clicked: navigating to frame {frame}")

    @Slot(int)
    def on_timeline_tab_hovered(self, frame: int) -> None:
        """
        Handle timeline tab hover for preview.

        Currently a placeholder for future functionality like
        showing frame preview on hover.

        Args:
            frame: Frame number being hovered
        """
        # Could be used to show frame preview in the future
        pass

    def update_for_tracking_data(self, num_images: int) -> None:
        """
        DEPRECATED: Timeline now updates automatically from store signals.

        This method is kept for compatibility but does nothing.
        Timeline frame range is determined by curve data in the store.

        Args:
            num_images: Total number of images in the sequence (ignored)
        """
        # Timeline updates automatically from store signals
        # No manual update needed
        logger.debug(f"update_for_tracking_data called with {num_images} images (ignored - using store data)")

    def update_for_current_frame(self, frame: int) -> None:
        """
        Update timeline to show current frame.

        Args:
            frame: Current frame number
        """
        if self.main_window.timeline_tabs:
            self.main_window.timeline_tabs.set_current_frame(frame)

    def update_timeline_tabs(self, curve_data: CurveDataList | None = None) -> None:
        """
        Update timeline tabs with curve point data and status.

        This method calculates the frame range and point status for each frame,
        then updates the timeline widget to display the appropriate colors
        and states for each frame tab.

        Args:
            curve_data: Optional curve data to use. If None, gets from store.
        """
        if not self.main_window.timeline_tabs:
            return

        # Get data from store if not provided
        if curve_data is None:
            curve_data = self._curve_store.get_data()

        if not curve_data:
            return

        # Calculate frame range - validate data first
        frames: list[int] = []
        for point in curve_data:
            if len(point) >= 3:
                try:
                    # Ensure frame number is an integer
                    frame = int(point[0])
                    frames.append(frame)
                except (ValueError, TypeError):
                    # Skip invalid data
                    continue

        if not frames:
            return

        min_frame = min(frames)
        max_frame = max(frames)

        # Limit timeline tabs to a reasonable number (performance issue with thousands of tabs)
        # Only create tabs for up to 200 frames to avoid UI freezing
        max_timeline_frames = 200
        if max_frame - min_frame + 1 > max_timeline_frames:
            # Only show first 200 frames in timeline tabs
            max_frame = min_frame + max_timeline_frames - 1
            logger.warning(
                f"Timeline limited to {max_timeline_frames} frames for performance. "
                f"Full range: {min(frames)}-{max(frames)}"
            )

        # Update timeline widget frame range
        self.main_window.timeline_tabs.set_frame_range(min_frame, max_frame)

        # Get point status for all frames using DataService
        try:
            data_service = get_data_service()

            # Get comprehensive status for all frames that have points
            frame_status = data_service.get_frame_range_point_status(curve_data)  # pyright: ignore[reportArgumentType]

            # Update timeline tabs with comprehensive point status
            for frame, status_data in frame_status.items():
                # Unpack all status fields from the enhanced DataService response
                (
                    keyframe_count,
                    interpolated_count,
                    tracked_count,
                    endframe_count,
                    normal_count,
                    is_startframe,
                    is_inactive,
                    has_selected,
                ) = status_data

                self.main_window.timeline_tabs.update_frame_status(
                    frame,
                    keyframe_count=keyframe_count,
                    interpolated_count=interpolated_count,
                    tracked_count=tracked_count,
                    endframe_count=endframe_count,
                    normal_count=normal_count,
                    is_startframe=is_startframe,
                    is_inactive=is_inactive,
                    has_selected=has_selected,
                )

            # Explicitly mark frames without points to show "no_points" color
            # This ensures gaps in the curve are visually represented in the timeline
            all_frames = set(range(min_frame, max_frame + 1))
            frames_with_points = set(frame_status.keys())
            empty_frames = all_frames - frames_with_points

            for frame in empty_frames:
                self.main_window.timeline_tabs.update_frame_status(
                    frame,
                    keyframe_count=0,
                    interpolated_count=0,
                    tracked_count=0,
                    endframe_count=0,
                    normal_count=0,
                    is_startframe=False,
                    is_inactive=False,
                    has_selected=False,
                )

            logger.debug(
                f"Updated timeline tabs: {len(frame_status)} frames with data, " f"{len(empty_frames)} empty frames"
            )

        except Exception as e:
            logger.warning(f"Could not update timeline tabs with point data: {e}")

    def connect_signals(self) -> None:
        """
        Connect timeline-related signals.

        This should be called after the timeline tabs widget is created.
        """
        if self.main_window.timeline_tabs:
            # Connect timeline tab signals
            _ = self.main_window.timeline_tabs.frame_changed.connect(self.on_timeline_tab_clicked)
            _ = self.main_window.timeline_tabs.frame_hovered.connect(self.on_timeline_tab_hovered)
            logger.info("Timeline tabs signals connected")

    def set_frame_range(self, min_frame: int, max_frame: int) -> None:
        """
        Set the timeline frame range.

        Args:
            min_frame: Minimum frame number
            max_frame: Maximum frame number
        """
        if self.main_window.timeline_tabs:
            self.main_window.timeline_tabs.set_frame_range(min_frame, max_frame)
            logger.debug(f"Timeline frame range set to {min_frame}-{max_frame}")

    def clear(self) -> None:
        """Clear the timeline tabs."""
        if self.main_window.timeline_tabs:
            self.main_window.timeline_tabs.set_frame_range(0, 0)
            logger.debug("Timeline tabs cleared")
