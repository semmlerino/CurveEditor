#!/usr/bin/env python

"""
Background rendering component for CurveView.

Architecture Component: BackgroundRenderer
This module implements one of the four specialized rendering components that
replaced the monolithic paintEvent method. The BackgroundRenderer is responsible
for all background image rendering operations.

Responsibilities:
- Background image rendering with proper coordinate transformations
- Image scaling and positioning calculations
- Debug visualization overlays (image bounds, coordinate origins)
- Background image opacity and visibility handling
- Integration with the unified transformation system

Key Design Decisions:
- Separated from point and info rendering for clear responsibility boundaries
- Uses immutable transform objects for consistent coordinate mapping
- Maintains debug visualization capabilities for development and troubleshooting
- Handles edge cases like missing images and invalid transformations gracefully

Integration Points:
- Receives transform object from CurveRenderer for coordinate calculations
- Uses CurveViewProtocol interface for accessing view properties
- Integrates with UIScaling for theme-aware colors and DPI handling
"""

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen

from core.protocols.protocols import CurveViewProtocol
from services.logging_service import LoggingService
from ui.ui_scaling import UIScaling

if TYPE_CHECKING:
    pass

logger = LoggingService.get_logger("background_renderer")


class BackgroundRenderer:
    """
    Handles background image rendering for CurveView.

    This class is responsible for rendering background images with proper
    transformation, scaling, and debug visualization. It maintains identical
    functionality to the original paintEvent background rendering logic.
    """

    def render_background(self, painter: QPainter, transform: Any, curve_view: CurveViewProtocol) -> None:
        """
        Render background image with transformation and debug overlays.

        Args:
            painter: QPainter instance for drawing
            transform: Transform object for coordinate mapping
            curve_view: CurveView instance providing context and properties
        """
        # Check if background should be shown and image is available
        if not curve_view.show_background or not curve_view.background_image:
            return

        # Get current transformation parameters
        display_width = curve_view.background_image.width()
        display_height = curve_view.background_image.height()

        # Get the transform parameters for positioning
        params = transform.get_parameters()
        scale = params["scale"]
        # Use individual scale parameters
        image_scale_x = params.get("image_scale_x", 1.0)
        image_scale_y = params.get("image_scale_y", 1.0)

        # Calculate scaled dimensions for the image
        scaled_width = display_width * scale
        scaled_height = display_height * scale

        # Get the image position by directly transforming the origin point (0,0)
        # using the SAME transform method used for curve points
        # This ensures the image and curve use identical transformation logic
        img_x, img_y = transform.apply(0, 0)

        # For debugging, calculate where several key points would appear on screen:
        # 1. Data origin (0,0) - this is now the same as the image position since we're using the same transform
        origin_x, origin_y = img_x, img_y  # img_x, img_y already calculated using transform.apply(0, 0)

        # 2. Data origin (0,0) without image scaling (for comparison only)
        origin_no_scale_x, origin_no_scale_y = origin_x, origin_y

        # 3. Data point at image dimensions (width, height)
        width_pt_x, width_pt_y = transform.apply(curve_view.image_width, curve_view.image_height)

        # Log these points for debugging
        logger.debug(f"Image position = Data origin: ({img_x:.1f}, {img_y:.1f}) - using same transform")
        logger.debug(f"Data origin (without scaling): ({origin_no_scale_x:.1f}, {origin_no_scale_y:.1f})")
        logger.debug(f"Data point at image dims: ({width_pt_x:.1f}, {width_pt_y:.1f})")

        # Calculate offset between with/without scaling for reference
        scale_diff_x = img_x - origin_no_scale_x
        scale_diff_y = img_y - origin_no_scale_y
        logger.debug(f"Difference with vs. without scaling: ({scale_diff_x:.1f}, {scale_diff_y:.1f})")
        logger.debug(f"Scale to image setting: {getattr(curve_view, 'scale_to_image', True)}")

        # Store values for debug visualization
        curve_view.debug_img_pos = (img_x, img_y)
        curve_view.debug_origin_pos = (origin_x, origin_y)
        curve_view.debug_origin_no_scale_pos = (origin_no_scale_x, origin_no_scale_y)
        curve_view.debug_width_pt = (width_pt_x, width_pt_y)

        # Draw the image
        painter.setOpacity(curve_view.background_opacity)
        painter.drawPixmap(int(img_x), int(img_y), int(scaled_width), int(scaled_height), curve_view.background_image)
        painter.setOpacity(1.0)

        # Debugging visuals
        if curve_view.debug_mode:
            self._render_debug_info(
                painter,
                curve_view,
                params,
                img_x,
                img_y,
                scaled_width,
                scaled_height,
                origin_x,
                origin_y,
                origin_no_scale_x,
                origin_no_scale_y,
            )
        else:
            # Display scale info when not scaling to image
            painter.drawText(10, 180, f"Image Scale: ({image_scale_x:.2f}, {image_scale_y:.2f}), Scale to Image: OFF")

    def _render_debug_info(
        self,
        painter: QPainter,
        curve_view: "CurveViewProtocol",
        params: dict[str, Any],
        img_x: float,
        img_y: float,
        scaled_width: float,
        scaled_height: float,
        origin_x: float,
        origin_y: float,
        origin_no_scale_x: float,
        origin_no_scale_y: float,
    ) -> None:
        """
        Render debug information overlays for background image.

        Args:
            painter: QPainter instance for drawing
            curve_view: CurveView instance providing context
            params: Transform parameters dictionary
            img_x, img_y: Image position coordinates
            scaled_width, scaled_height: Scaled image dimensions
            origin_x, origin_y: Origin position with scaling
            origin_no_scale_x, origin_no_scale_y: Origin position without scaling
        """
        scale = params["scale"]
        center_offset_x = params["center_offset_x"]
        center_offset_y = params["center_offset_y"]
        pan_offset_x = params["pan_offset_x"]
        pan_offset_y = params["pan_offset_y"]
        image_scale_x = params.get("image_scale_x", 1.0)
        image_scale_y = params.get("image_scale_y", 1.0)

        # Show alignment info with transform details
        debug_color = UIScaling.get_color("text_error")
        painter.setPen(QPen(QColor(debug_color), 1))
        painter.drawText(10, 100, f"Manual Alignment: X-offset: {curve_view.x_offset}, Y-offset: {curve_view.y_offset}")
        painter.drawText(
            10, 120, f"Transform Scale: {scale:.4f}, Center: ({center_offset_x:.1f}, {center_offset_y:.1f})"
        )
        painter.drawText(10, 140, f"Pan Offset: ({pan_offset_x:.1f}, {pan_offset_y:.1f})")
        painter.drawText(10, 160, f"Final Image Pos: ({img_x:.1f}, {img_y:.1f})")

        # Add more debugging info about image scaling
        scale_to_image = params.get("scale_to_image", True)
        if scale_to_image:
            painter.drawText(10, 180, f"Image Scale: ({image_scale_x:.2f}, {image_scale_y:.2f}), Scale to Image: ON")
            painter.drawText(10, 195, "Using identical transform for both curve and image")
        else:
            painter.drawText(10, 180, f"Image Scale: ({image_scale_x:.2f}, {image_scale_y:.2f}), Scale to Image: OFF")

        painter.drawText(10, 200, "Adjust with arrow keys + Shift/Ctrl")

        # Add alignment grid crosshair for checking if curve is properly aligned with the background
        # Draw at the center of the image
        center_x = img_x + (scaled_width / 2)
        center_y = img_y + (scaled_height / 2)

        # Draw crosshair lines
        crosshair_color = UIScaling.get_color("text_warning")
        painter.setPen(QPen(QColor(crosshair_color), 1, Qt.PenStyle.DashLine))
        painter.drawLine(center_x - 50, center_y, center_x + 50, center_y)  # Horizontal line
        painter.drawLine(center_x, center_y - 50, center_x, center_y + 50)  # Vertical line

        # Draw text label
        painter.setPen(QPen(QColor(crosshair_color), 1))
        painter.drawText(center_x + 10, center_y - 10, "Center")

        # Draw comprehensive alignment debug visualization
        if hasattr(curve_view, "debug_origin_pos"):
            origin_x, origin_y = curve_view.debug_origin_pos

            # Draw a large crosshair at the data origin with scaling
            origin_color = UIScaling.get_color("text_success")
            painter.setPen(QPen(QColor(origin_color), 2, Qt.PenStyle.DashLine))
            painter.drawLine(int(origin_x - 30), int(origin_y), int(origin_x + 30), int(origin_y))  # Horizontal
            painter.drawLine(int(origin_x), int(origin_y - 30), int(origin_x), int(origin_y + 30))  # Vertical

            # Draw a circle at the origin
            painter.setPen(QPen(QColor(origin_color), 2))
            painter.drawEllipse(int(origin_x - 5), int(origin_y - 5), 10, 10)

            # Label the origin (with scaling)
            painter.drawText(int(origin_x + 15), int(origin_y - 15), "Data Origin (with scaling)")

            # Draw the non-scaled origin point (blue)
            if hasattr(curve_view, "debug_origin_no_scale_pos"):
                origin_no_scale_x, origin_no_scale_y = curve_view.debug_origin_no_scale_pos

                # Draw crosshair for non-scaled origin
                no_scale_color = UIScaling.get_color("text_link")
                painter.setPen(QPen(QColor(no_scale_color), 2, Qt.PenStyle.DashLine))
                painter.drawLine(
                    int(origin_no_scale_x - 30),
                    int(origin_no_scale_y),
                    int(origin_no_scale_x + 30),
                    int(origin_no_scale_y),
                )
                painter.drawLine(
                    int(origin_no_scale_x),
                    int(origin_no_scale_y - 30),
                    int(origin_no_scale_x),
                    int(origin_no_scale_y + 30),
                )

                # Draw square at non-scaled origin
                painter.setPen(QPen(QColor(no_scale_color), 2))
                painter.drawRect(int(origin_no_scale_x - 5), int(origin_no_scale_y - 5), 10, 10)

                # Label the non-scaled origin
                painter.drawText(int(origin_no_scale_x + 15), int(origin_no_scale_y - 15), "Data Origin (no scaling)")

            # Calculate and show offset between image position and data origins
            if hasattr(curve_view, "debug_img_pos"):
                img_x, img_y = curve_view.debug_img_pos
                dx = origin_x - img_x
                dy = origin_y - img_y

                # Show offset information
                text_color = UIScaling.get_color("text_primary")
                painter.setPen(QPen(QColor(text_color), 1))
                painter.drawText(10, 220, f"Origin-Image Offset (scaled): ({dx:.1f}, {dy:.1f})")

                if hasattr(curve_view, "debug_origin_no_scale_pos"):
                    # Calculate no-scale offset
                    no_scale_dx = origin_no_scale_x - img_x
                    no_scale_dy = origin_no_scale_y - img_y
                    painter.drawText(
                        10, 240, f"Origin-Image Offset (no scaling): ({no_scale_dx:.1f}, {no_scale_dy:.1f})"
                    )

                painter.drawText(
                    10,
                    260,
                    f"Y-flip: {getattr(curve_view, 'flip_y_axis', False)}, Scale-to-image: {getattr(curve_view, 'scale_to_image', True)}",
                )

                # Draw a line from image corner to each origin point
                painter.setPen(QPen(QColor(debug_color), 1, Qt.PenStyle.DashLine))
                painter.drawLine(int(img_x), int(img_y), int(origin_x), int(origin_y))

                if hasattr(curve_view, "debug_origin_no_scale_pos"):
                    # Add implementation for this condition if needed
                    pass


# Protocol is already imported from core.protocols.protocols
