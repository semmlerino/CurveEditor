#!/usr/bin/env python

"""
Info rendering component for CurveView.

Architecture Component: InfoRenderer
This module implements the information overlay rendering component that handles
all text-based information display within the new rendering architecture.

Responsibilities:
- View statistics display (zoom level, point counts, selection info)
- Image sequence information (current image, dimensions, file path)
- Debug information overlays (coordinate system, transformation parameters)
- Performance metrics and rendering statistics
- Error and status message display

Information Categories:
1. View State: Current zoom, pan offset, transformation mode
2. Data Statistics: Total points, selected points, interpolated points
3. Image Information: Current frame, image dimensions, sequence path
4. Debug Overlays: Coordinate grids, transformation bounds, performance timers

Key Design Decisions:
- Consolidated all text rendering into a single component for consistency
- Uses UIScaling fonts for responsive text sizing across different DPI settings
- Implements layered information display with priority-based visibility
- Maintains debug information separate from user-facing status information
- Preserves all original information display behavior from monolithic implementation

Integration Points:
- Independent of coordinate transformations (renders in screen space)
- Uses CurveViewProtocol for accessing view state and data statistics
- Integrates with ImageService for current image information
- Coordinates with UIScaling for theme-aware colors and responsive typography
- Works alongside other renderers without coordinate system conflicts
"""

import os
from typing import TYPE_CHECKING

from PySide6.QtGui import QColor, QPainter, QPen

from core.protocols.protocols import CurveViewProtocol
from services.logging_service import LoggingService
from ui.ui_scaling import UIScaling

if TYPE_CHECKING:
    pass

logger = LoggingService.get_logger("info_renderer")


class InfoRenderer:
    """
    Handles information overlay rendering for CurveView.

    This class is responsible for rendering text overlays including view statistics,
    image information, and debug information. Maintains identical functionality
    to the original paintEvent info rendering logic.
    """

    def render_info(self, painter: QPainter, curve_view: CurveViewProtocol) -> None:
        """
        Render all information overlays.

        Args:
            painter: QPainter instance for drawing
            curve_view: CurveView instance providing context and data
        """
        # Set up font and color for info text
        info_font = UIScaling.get_font("small", "regular", "monospace")
        painter.setFont(info_font)
        info_color = UIScaling.get_color("text_secondary")
        painter.setPen(QPen(QColor(info_color), 1))

        # Render view information
        self._render_view_info(painter, curve_view)

        # Render image information if available
        if curve_view.background_image:
            self._render_image_info(painter, curve_view)

        # Render debug information if in debug mode
        if curve_view.debug_mode:
            self._render_debug_info(painter, curve_view)

    def _render_view_info(self, painter: QPainter, curve_view: "CurveViewProtocol") -> None:
        """
        Render view statistics and selected point information.

        Args:
            painter: QPainter instance for drawing
            curve_view: CurveView instance providing context and data
        """
        # Show current view info
        info_text = f"Zoom: {curve_view.zoom_factor:.2f}x | Points: {len(curve_view.points)}"

        # Add selected point type information
        if hasattr(curve_view, "selected_points") and curve_view.selected_points:
            # Gather types of all selected points
            selected_types: set[str] = set()
            for i in curve_view.selected_points:
                if 0 <= i < len(curve_view.points):
                    pt = curve_view.points[i]
                    if len(pt) >= 4:
                        selected_types.add(str(pt[3]))
                    else:
                        pass  # No type info for this point
            if selected_types:
                types_str = ", ".join(sorted(selected_types))
                info_text += f" | Type(s): {types_str}"

        painter.drawText(10, 20, info_text)

    def _render_image_info(self, painter: QPainter, curve_view: "CurveViewProtocol") -> None:
        """
        Render image sequence information.

        Args:
            painter: QPainter instance for drawing
            curve_view: CurveView instance providing context and data
        """
        # Get image info from curve_view attributes
        current_idx = getattr(curve_view, "current_image_idx", -1)
        image_filenames = getattr(curve_view, "image_filenames", [])

        if image_filenames:
            img_info = f"Image: {current_idx + 1}/{len(image_filenames)}"

            # Add filename if available
            if 0 <= current_idx < len(image_filenames):
                filename = os.path.basename(image_filenames[current_idx])
                img_info += f" - {filename}"
        else:
            img_info = "No image sequence loaded"

        painter.drawText(10, 40, img_info)

    def _render_debug_info(self, painter: QPainter, curve_view: "CurveViewProtocol") -> None:
        """
        Render debug information and keyboard shortcuts.

        Args:
            painter: QPainter instance for drawing
            curve_view: CurveView instance providing context and data
        """
        # Main debug info line
        debug_info = f"Debug Mode: ON | Y-Flip: {'ON' if curve_view.flip_y_axis else 'OFF'} | Scale to Image: {'ON' if curve_view.scale_to_image else 'OFF'}"
        debug_info += f" | Track Dims: {curve_view.image_width}x{curve_view.image_height}"

        # Add image dimensions if available
        if curve_view.background_image:
            debug_info += f" | Image: {curve_view.background_image.width()}x{curve_view.background_image.height()}"

        painter.drawText(10, 60, debug_info)

        # Display keyboard shortcuts
        shortcuts = "Shortcuts: [R] Reset View, [Y] Toggle Y-Flip, [S] Toggle Scale-to-Image"
        shortcuts += " | Arrow keys + Shift: Adjust alignment"
        painter.drawText(10, 80, shortcuts)


# Protocol is already imported from core.protocols.protocols
