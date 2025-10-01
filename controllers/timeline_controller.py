"""
Timeline controller for managing timeline tab interactions.

This controller handles timeline tab clicks and hover events,
reducing MainWindow complexity.
"""

import logging
from typing import TYPE_CHECKING

from core.type_aliases import CurveDataList

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class TimelineController:
    """Controller for timeline tab operations."""

    def __init__(self, main_window: "MainWindow"):
        """Initialize the timeline controller.

        Args:
            main_window: Reference to the main window
        """
        self.main_window: MainWindow = main_window

    def handle_timeline_tab_clicked(self, frame: int) -> None:
        """Handle timeline tab click event.

        Args:
            frame: Frame number that was clicked
        """
        logger.debug(f"Timeline tab clicked: frame {frame}")
        self.main_window._set_current_frame(frame)

    def handle_timeline_tab_hovered(self, frame: int) -> None:
        """Handle timeline tab hover event.

        Args:
            frame: Frame number being hovered over
        """
        # Currently just logs the hover event
        # Could be extended to show preview or tooltip
        logger.debug(f"Timeline tab hovered: frame {frame}")

    def update_timeline_tabs(self, curve_data: CurveDataList | None = None) -> None:
        """Update timeline tabs with current curve data and frame range.

        Args:
            curve_data: Optional curve data to use for update
        """
        if not self.main_window.timeline_tabs:
            return

        # Get curve data if not provided
        if curve_data is None:
            curve_data = self.main_window._get_current_curve_data()

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

        # Update timeline widget frame range
        self.main_window.timeline_tabs.set_frame_range(min_frame, max_frame)

        # Get point status for all frames using DataService
        try:
            from services import get_data_service

            data_service = get_data_service()

            # Get status for all frames that have points
            frame_status = data_service.get_frame_range_point_status(curve_data)  # pyright: ignore[reportArgumentType]

            # Update timeline tabs with point status
            for frame, status_tuple in frame_status.items():
                (
                    keyframe_count,
                    interpolated_count,
                    tracked_count,
                    endframe_count,
                    normal_count,
                    is_startframe,
                    is_inactive,
                    has_selected,
                ) = status_tuple
                self.main_window.timeline_tabs.update_frame_status(
                    frame, keyframe_count, interpolated_count, has_selected
                )

            logger.debug(f"Updated timeline tabs with {len(frame_status)} frames of point data")

        except Exception as e:
            logger.error(f"Error updating timeline tabs: {e}")
