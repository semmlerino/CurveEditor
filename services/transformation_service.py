#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TransformationService: Centralized coordinate transformation logic.
Provides methods for mapping between different coordinate spaces in the application.
"""

from typing import Tuple, Optional, TYPE_CHECKING, List, Union, cast
from services.logging_service import LoggingService
from services.centering_zoom_service import CenteringZoomService
from services.protocols import CurveViewProtocol, PointTuple, PointTupleWithStatus, PointsList

# Configure logger for this module
logger = LoggingService.get_logger("transformation_service")

if TYPE_CHECKING:
    from PySide6.QtCore import QPointF


class TransformationService:
    """Service for coordinate transformations between different spaces.

    This service centralizes all coordinate transformation logic in the application,
    ensuring consistent behavior across different components.

    Coordinate Spaces:
    1. Tracking Data Space: Raw (x, y) coordinates from the tracking data
    2. Image Space: Coordinates mapped to the background image dimensions (when using scale_to_image)
    3. Widget Space: Coordinates mapped to the view widget dimensions
    4. Screen Space: Final rendered positions after all transformations
    """

    @staticmethod
    def transform_point_to_widget(
        curve_view: CurveViewProtocol,
        x: float,
        y: float,
        display_width: float,
        display_height: float,
        offset_x: float,
        offset_y: float,
        scale: float
    ) -> Tuple[float, float]:
        """Transform from track coordinates to widget coordinates.

        This function transforms from tracking data coordinates to widget display coordinates,
        taking into account scaling, offsets, and any coordinate system transformations.

        Args:
            curve_view: The curve view instance
            x: X coordinate in tracking data coordinates
            y: Y coordinate in tracking data coordinates
            display_width: Width of the display content area
            display_height: Height of the display content area
            offset_x: Content centering X offset
            offset_y: Content centering Y offset
            scale: Scale factor to apply

        Returns:
            Tuple[float, float]: The transformed (x, y) coordinates in widget space
        """
        # Get any manual offsets applied through panning
        manual_x_offset = getattr(curve_view, 'x_offset', 0)
        manual_y_offset = getattr(curve_view, 'y_offset', 0)

        # Use the image content centered base position
        # This ensures content stays properly centered in the widget
        base_x = offset_x + manual_x_offset
        base_y = offset_y + manual_y_offset

        if hasattr(curve_view, 'background_image') and curve_view.background_image and getattr(curve_view, 'scale_to_image', False):
            # When scaling to image, we need to first convert from curve coordinates to image coordinates
            img_width = getattr(curve_view, 'image_width', 1920)
            img_height = getattr(curve_view, 'image_height', 1080)

            # Convert tracking coordinates to image space
            img_scale_x = display_width / max(img_width, 1)
            img_scale_y = display_height / max(img_height, 1)

            # Apply image-to-tracking coordinate transformation
            # This maps curve points to positions on the background image
            img_x = x * img_scale_x
            img_y = y * img_scale_y

            # Apply Y-flip if enabled
            if getattr(curve_view, 'flip_y_axis', False):
                img_y = display_height - img_y

            # Now scale to widget space and apply centering offset
            tx = base_x + img_x * scale
            ty = base_y + img_y * scale

        else:
            # Direct scaling from tracking coordinates to widget space
            # No image-based transformation, but we still need to handle Y-flip
            if getattr(curve_view, 'flip_y_axis', False):
                # For Y-flip, we need the original data height
                img_height = getattr(curve_view, 'image_height', 1080)
                tx = base_x + (x * scale)
                ty = base_y + (img_height - y) * scale
            else:
                tx = base_x + (x * scale)
                ty = base_y + (y * scale)

        return tx, ty

    @staticmethod
    def transform_widget_to_track(
        curve_view: CurveViewProtocol,
        widget_x: float,
        widget_y: float,
        display_width: float,
        display_height: float,
        offset_x: float,
        offset_y: float,
        scale: float
    ) -> Tuple[float, float]:
        """Transform from widget coordinates to track coordinates.

        This function transforms from widget display coordinates to tracking data coordinates,
        applying the inverse of the transformations used in transform_point_to_widget.

        Args:
            curve_view: The curve view instance
            widget_x: X coordinate in widget space
            widget_y: Y coordinate in widget space
            display_width: Width of the display content area
            display_height: Height of the display content area
            offset_x: Content centering X offset
            offset_y: Content centering Y offset
            scale: Scale factor to apply

        Returns:
            Tuple[float, float]: The transformed (x, y) coordinates in tracking data space
        """
        # Get any manual offsets applied through panning
        manual_x_offset = getattr(curve_view, 'x_offset', 0)
        manual_y_offset = getattr(curve_view, 'y_offset', 0)

        # Adjust for base offsets and manual panning
        base_x = offset_x + manual_x_offset
        base_y = offset_y + manual_y_offset

        # Remove centering offset to get to scaled space
        scaled_x = (widget_x - base_x) / scale if scale != 0 else 0
        scaled_y = (widget_y - base_y) / scale if scale != 0 else 0

        if hasattr(curve_view, 'background_image') and curve_view.background_image and getattr(curve_view, 'scale_to_image', False):
            # Handle image-based transformation
            img_width = getattr(curve_view, 'image_width', 1920)
            img_height = getattr(curve_view, 'image_height', 1080)

            # Apply Y-flip if enabled
            if getattr(curve_view, 'flip_y_axis', False):
                scaled_y = display_height - scaled_y

            # Convert from image space back to tracking coordinates
            img_scale_x = display_width / max(img_width, 1)
            img_scale_y = display_height / max(img_height, 1)

            track_x = scaled_x / img_scale_x if img_scale_x != 0 else 0
            track_y = scaled_y / img_scale_y if img_scale_y != 0 else 0

        else:
            # Direct scaling without image-based transformation
            if getattr(curve_view, 'flip_y_axis', False):
                # Handle Y-flip in direct mode
                img_height = getattr(curve_view, 'image_height', 1080)
                track_x = scaled_x
                track_y = img_height - scaled_y
            else:
                track_x = scaled_x
                track_y = scaled_y

        return track_x, track_y

    @staticmethod
    def transform_point_list(
        curve_view: CurveViewProtocol,
        points: PointsList,
        display_width: float,
        display_height: float,
        offset_x: float,
        offset_y: float,
        scale: float
    ) -> PointsList:
        """Transform a list of points from track coordinates to widget coordinates.

        Args:
            curve_view: The curve view instance
            points: List of points to transform, each as (frame, x, y) or (frame, x, y, status)
            display_width: Width of the display content area
            display_height: Height of the display content area
            offset_x: Content centering X offset
            offset_y: Content centering Y offset
            scale: Scale factor to apply

        Returns:
            List of transformed points in widget coordinates
        """
        transformed_points = []
        for point in points:
            frame = point[0]
            x, y = point[1], point[2]

            # Transform the point coordinates
            tx, ty = TransformationService.transform_point_to_widget(
                curve_view, x, y, display_width, display_height, offset_x, offset_y, scale
            )

            # Preserve additional attributes if present
            if len(point) > 3:
                status = point[3]
                transformed_points.append((frame, tx, ty, status))
            else:
                transformed_points.append((frame, tx, ty))

        return transformed_points

    @staticmethod
    def calculate_display_parameters(
        curve_view: CurveViewProtocol,
        widget_width: int,
        widget_height: int
    ) -> Tuple[float, float, float, float, float]:
        """Calculate display parameters for coordinate transformations.

        This centralized function computes the standard parameters needed for
        coordinate transformations, ensuring consistency across the application.

        Args:
            curve_view: The curve view instance
            widget_width: Width of the widget
            widget_height: Height of the widget

        Returns:
            Tuple with (display_width, display_height, scale, offset_x, offset_y)
        """
        # Get display dimensions
        display_width = getattr(curve_view, 'image_width', 1920)
        display_height = getattr(curve_view, 'image_height', 1080)

        # Use background image dimensions if available
        if hasattr(curve_view, 'background_image') and curve_view.background_image:
            display_width = curve_view.background_image.width()
            display_height = curve_view.background_image.height()

        # Calculate scale
        scale_x = widget_width / display_width
        scale_y = widget_height / display_height
        scale = min(scale_x, scale_y) * getattr(curve_view, 'zoom_factor', 1.0)

        # Calculate centering offsets
        offset_x, offset_y = CenteringZoomService.calculate_centering_offsets(
            widget_width, widget_height,
            display_width * scale, display_height * scale,
            curve_view.x_offset, curve_view.y_offset
        )

        return display_width, display_height, scale, offset_x, offset_y
