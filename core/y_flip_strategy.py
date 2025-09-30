#!/usr/bin/env python
"""
Y-flip strategy for consolidating coordinate system Y-axis flipping logic.

This module consolidates all Y-flip related operations that were previously
scattered throughout the CurveViewWidget and other transformation code.
"""


class YFlipStrategy:
    """
    Strategy pattern implementation for Y-axis flipping operations.

    Consolidates all Y-flip logic to eliminate code duplication and ensure
    consistent behavior across pan operations, coordinate transformations,
    and display dimension selection.
    """

    @staticmethod
    def apply_to_pan_delta(delta_y: float, flip_y: bool) -> float:
        """
        Apply Y-flip logic to pan delta movement.

        When Y-axis is flipped (3DEqualizer data), invert the pan direction for Y
        to ensure the curve follows the mouse drag direction correctly.

        Args:
            delta_y: The Y delta from mouse movement
            flip_y: Whether Y-axis flipping is enabled

        Returns:
            The adjusted Y delta for pan operations
        """
        return -delta_y if flip_y else delta_y

    @staticmethod
    def apply_to_offset_adjustment(offset_y: float, flip_y: bool) -> float:
        """
        Apply Y-flip logic to offset adjustments (centering, zoom).

        When Y-axis is flipped, invert the offset adjustment for Y to ensure
        centering and zoom operations work consistently with panning behavior.

        Args:
            offset_y: The Y offset adjustment
            flip_y: Whether Y-axis flipping is enabled

        Returns:
            The adjusted Y offset for the operation
        """
        return -offset_y if flip_y else offset_y

    @staticmethod
    def get_display_dimensions(
        flip_y: bool, image_width: int, image_height: int, widget_width: int, widget_height: int
    ) -> tuple[int, int]:
        """
        Get display dimensions based on Y-flip configuration.

        When Y-flip is enabled (3DEqualizer data), use image dimensions for
        the coordinate system. Otherwise use widget dimensions for pixel tracking.

        Args:
            flip_y: Whether Y-axis flipping is enabled
            image_width: Width of the background image
            image_height: Height of the background image
            widget_width: Width of the widget
            widget_height: Height of the widget

        Returns:
            Tuple of (display_width, display_height)
        """
        if flip_y:
            # 3DEqualizer data - use image coordinate space (Y=0 at bottom)
            return (image_width, image_height)
        else:
            # Pixel tracking data - use widget coordinate space (Y=0 at top)
            return (widget_width, widget_height)

    @staticmethod
    def get_image_top_coordinate(flip_y: bool, image_height: int) -> tuple[float, float]:
        """
        Get the data coordinates for the top-left corner of an image.

        Args:
            flip_y: Whether Y-axis flipping is enabled
            image_height: Height of the image

        Returns:
            Tuple of (x, y) data coordinates for the image top-left corner
        """
        if flip_y:
            # With Y-flip, image top is at Y=image_height in data space
            return (0.0, float(image_height))
        else:
            # Without Y-flip, image top is at Y=0 in data space
            return (0.0, 0.0)

    @staticmethod
    def apply_y_flip(y: float, flip_y: bool, display_height: int) -> float:
        """
        Apply Y-axis flipping for coordinate transformation.

        This is the core Y-flip operation for converting between coordinate systems:
        - When flip_y=True: Flip Y-axis for bottom-left origin systems (3DEqualizer, OpenGL)
        - When flip_y=False: No flip for top-left origin systems (Qt, screen coordinates)

        Args:
            y: The Y coordinate to transform
            flip_y: Whether Y-axis flipping is enabled
            display_height: Height of the display area for flip calculation

        Returns:
            The transformed Y coordinate
        """
        if flip_y and display_height > 0:
            return display_height - y
        return y

    @staticmethod
    def validate_flip_configuration(flip_y: bool, scale_to_image: bool) -> None:
        """
        Validate Y-flip configuration for consistency.

        Ensures that Y-flip settings are consistent with the intended use case:
        - flip_y=True should be used with 3DEqualizer data (scale_to_image=True)
        - flip_y=False should be used with pixel tracking data

        Args:
            flip_y: Whether Y-axis flipping is enabled
            scale_to_image: Whether scaling to image is enabled

        Raises:
            ValueError: If configuration is inconsistent or invalid
        """
        # Note: According to the analysis, the OR condition (flip_y_axis OR scale_to_image)
        # was causing issues, so we validate that the configuration makes sense
        if flip_y and not scale_to_image:
            raise ValueError(
                "Inconsistent Y-flip configuration: flip_y=True requires scale_to_image=True "
                "for proper 3DEqualizer coordinate handling"
            )

        # This is valid: flip_y=False with scale_to_image=True for tracking data that scales with background
        # This is valid: flip_y=False with scale_to_image=False for direct pixel tracking
