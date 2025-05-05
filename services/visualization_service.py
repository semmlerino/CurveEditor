#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
VisualizationService: Handles visualization operations for the CurveEditor.
Provides methods for toggling display features and manipulating the view.
"""

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
import os
import re
from services.centering_zoom_service import CenteringZoomService
from services.logging_service import LoggingService
from services.protocols import CurveViewProtocol, MainWindowProtocol, PointsList
from typing import List, Tuple, Optional, Union, cast, TYPE_CHECKING

# Configure logger for this module
logger = LoggingService.get_logger("visualization_service")

class VisualizationService:
    """Service for visualization operations in the curve editor."""

    @staticmethod
    def toggle_background_visible(curve_view: CurveViewProtocol, visible: bool) -> None:
        """Toggle visibility of background image."""
        curve_view.show_background = visible
        curve_view.update()

    @staticmethod
    def toggle_grid(curve_view: CurveViewProtocol, enabled: Optional[bool] = None) -> None:
        """Toggle grid visibility."""
        if enabled is None:
            curve_view.show_grid = not getattr(curve_view, 'show_grid', False)
        else:
            curve_view.show_grid = enabled
        curve_view.update()

    @staticmethod
    def toggle_velocity_vectors(curve_view: CurveViewProtocol, enabled: bool) -> None:
        """Toggle velocity vector display."""
        curve_view.show_velocity_vectors = enabled
        curve_view.update()

    @staticmethod
    def toggle_all_frame_numbers(curve_view: CurveViewProtocol, enabled: bool) -> None:
        """Toggle display of all frame numbers."""
        curve_view.show_all_frame_numbers = enabled
        curve_view.update()

    @staticmethod
    def toggle_crosshair(curve_view: CurveViewProtocol, enabled: bool) -> None:
        """Toggle crosshair visibility."""
        curve_view.show_crosshair = enabled
        curve_view.update()

    @staticmethod
    def set_background_opacity(curve_view: CurveViewProtocol, opacity: float) -> None:
        """Set the opacity of the background image.

        Args:
            curve_view: The curve view instance
            opacity: Opacity value between 0.0 and 1.0
        """
        curve_view.background_opacity = max(0.0, min(1.0, opacity))
        curve_view.update()

    @staticmethod
    def pan_view(curve_view: CurveViewProtocol, dx: float, dy: float) -> None:
        """Pan the view by the specified delta.

        Args:
            curve_view: The curve view instance
            dx: Change in x position
            dy: Change in y position
        """
        # Apply the pan offset
        curve_view.x_offset = int(curve_view.x_offset + dx)
        curve_view.y_offset = int(curve_view.y_offset + dy)

        # Update the view
        curve_view.update()

    @staticmethod
    def set_point_radius(curve_view: CurveViewProtocol, radius: int) -> None:
        """Set the radius for points in the curve view.

        Args:
            curve_view: The curve view instance
            radius: Point radius in pixels
        """
        curve_view.point_radius = max(1, radius)  # Ensure minimum size of 1
        curve_view.update()

    @staticmethod
    def set_grid_color(curve_view: CurveViewProtocol, color: QColor) -> None:
        """Set the color of the grid lines.

        Args:
            curve_view: The curve view instance
            color: QColor for the grid lines
        """
        curve_view.grid_color = color
        curve_view.update()

    @staticmethod
    def set_grid_line_width(curve_view: CurveViewProtocol, width: int) -> None:
        """Set the width of grid lines.

        Args:
            curve_view: The curve view instance
            width: Width in pixels
        """
        curve_view.grid_line_width = max(1, width)
        curve_view.update()

    @staticmethod
    def update_timeline_for_image(index: int, curve_view: CurveViewProtocol, image_filenames: List[str]) -> None:
        """Update the timeline for the current image.

        This method extracts the frame number from an image filename and updates
        the timeline slider and related UI elements to match the current image.
        It also selects the point in the curve data that corresponds to the frame.

        Args:
            index: Index of the current image in the image_filenames list
            curve_view: The curve view instance
            image_filenames: List of image filenames
        """
        try:
            if not image_filenames:
                logger.warning("No image filenames available")
                return

            if index < 0 or index >= len(image_filenames):
                logger.warning(f"Invalid index {index}")
                return

            # Extract frame number
            filename = os.path.basename(image_filenames[index])
            frame_match = re.search(r'(\d+)', filename)
            if not frame_match:
                logger.warning(f"Could not extract frame from {filename}")
                return

            frame_num = int(frame_match.group(1))
            logger.debug(f"Extracted frame {frame_num} from {filename}")

            # Update frame marker position if it exists
            VisualizationService.update_frame_marker_position(curve_view, frame_num)

            # Find and update selected point
            if hasattr(curve_view, 'curve_data') and curve_view.curve_data:
                closest_frame = min(curve_view.curve_data, key=lambda point: abs(point[0] - frame_num))[0]

                for i, point in enumerate(curve_view.curve_data):
                    if point[0] == closest_frame:
                        # Update selection
                        if hasattr(curve_view, 'selected_point_idx'):
                            curve_view.selected_point_idx = i
                            curve_view.selected_points = {i}
                            curve_view.update()
                            logger.debug(f"Updated selected point to {i}")
                        break
        except Exception as e:
            logger.error(f"Error updating timeline: {str(e)}")

    @staticmethod
    def update_frame_marker_position(curve_view: CurveViewProtocol, frame: int) -> None:
        """Update the position of the frame marker based on current frame.

        Args:
            curve_view: The curve view instance
            frame: The current frame number
        """
        # Update the marker position if it exists
        if hasattr(curve_view, 'frame_marker_label') and curve_view.frame_marker_label is not None:
            # Calculate position based on frame
            if hasattr(curve_view, 'timeline_slider') and curve_view.timeline_slider is not None:
                slider = curve_view.timeline_slider
                min_frame = slider.minimum()
                max_frame = slider.maximum()

                # Only update if we have a valid range
                if max_frame > min_frame:
                    _frame_range = max_frame - min_frame  # Not used, so prefixed with _ to avoid lint error
                    # Ensure the frame is within valid range
                    current_frame = max(min_frame, min(max_frame, frame))
                    # Update the tooltip to show the current frame
                    curve_view.frame_marker_label.setToolTip(f"Frame: {current_frame}")

    @staticmethod
    def set_points(
        curve_view: CurveViewProtocol,
        points: PointsList,
        image_width: int,
        image_height: int,
        preserve_view: bool = False
    ) -> None:
        """Set the points to display and adjust view accordingly.

        Args:
            curve_view: The curve view instance
            points: List of points in format [(frame, x, y), ...] or [(frame, x, y, status), ...]
            image_width: Width of the image/workspace
            image_height: Height of the image/workspace
            preserve_view: If True, maintain current view position
        """
        # Store current view state if preserving view
        view_state = None
        if preserve_view:
            view_state = {
                'zoom_factor': curve_view.zoom_factor,
                'x_offset': curve_view.x_offset,
                'y_offset': curve_view.y_offset
            }

        # Update data
        curve_view.points = points
        curve_view.image_width = image_width
        curve_view.image_height = image_height

        # Reset view if not preserving
        if not preserve_view:
            CenteringZoomService.reset_view(curve_view)
        else:
            # Restore view state
            if view_state:
                curve_view.zoom_factor = view_state['zoom_factor']
                curve_view.x_offset = int(view_state['x_offset'])
                curve_view.y_offset = int(view_state['y_offset'])

        curve_view.update()

    @staticmethod
    def jump_to_frame_by_click(curve_view: CurveViewProtocol, position: int) -> None:
        """
        Jump to a frame by clicking on the timeline (if implemented).

        Args:
            curve_view: The curve view instance
            position: The position of the click in the timeline
        """
        # Placeholder for future implementation
        pass

    @staticmethod
    def center_on_selected_point_from_main_window(main_window: MainWindowProtocol) -> None:
        """Center the view on the selected point from the main window.

        Args:
            main_window: The main window instance
        """
        curve_view = main_window.curve_view
        CenteringZoomService.center_on_selected_point(curve_view)

    @staticmethod
    def toggle_crosshair_internal(curve_view: CurveViewProtocol, enabled: bool) -> None:
        """Internal implementation of toggle_crosshair.

        Args:
            curve_view: The curve view instance
            enabled: Whether to enable or disable the crosshair
        """
        VisualizationService.toggle_crosshair(curve_view, enabled)
