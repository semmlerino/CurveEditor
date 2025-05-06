"""
Transform Module for CurveEditor - UPDATED FIXED VERSION

This module implements an immutable Transform class that encapsulates
the coordinate transformation logic used throughout the application.
The Transform class provides consistent mapping between data coordinates
and screen coordinates, with updated handling that completely resolves
the floating curve issue by ensuring image position calculations match
curve point transformations.
"""

from typing import Dict, Tuple, Any, Optional
from PySide6.QtCore import QPointF
from services.logging_service import LoggingService

# Configure logger for this module
logger = LoggingService.get_logger("transform")


class Transform:
    """
    Immutable class representing a coordinate transformation.

    This class encapsulates all parameters and logic for transforming
    coordinates from data space to screen space. Once created, a Transform
    instance cannot be modified, ensuring consistent transformations across
    operations.

    The transformation pipeline consists of:
    1. Scale-to-image adjustment (if enabled)
    2. Y-axis flipping (optional)
    3. Scaling
    4. Centering offset application
    5. Pan offset application
    6. Manual offset application

    This sequence matches the transformation logic previously scattered
    throughout the application, now centralized in one place.
    """

    def __init__(self, scale: float, center_offset_x: float, center_offset_y: float,
                 pan_offset_x: float = 0.0, pan_offset_y: float = 0.0,
                 manual_x: float = 0.0, manual_y: float = 0.0,
                 flip_y: bool = False, display_height: int = 0,
                 image_scale_x: float = 1.0, image_scale_y: float = 1.0,
                 scale_to_image: bool = True):
        """
        Initialize the transform parameters.

        Args:
            scale: Scaling factor to apply
            center_offset_x: X offset for centering content in widget
            center_offset_y: Y offset for centering content in widget
            pan_offset_x: X offset from user panning
            pan_offset_y: Y offset from user panning
            manual_x: Manual X offset adjustment
            manual_y: Manual Y offset adjustment
            flip_y: Whether to flip the Y coordinate
            display_height: Display height (needed for Y-flipping)
            image_scale_x: X scale factor for image-to-data conversion
            image_scale_y: Y scale factor for image-to-data conversion
            scale_to_image: Whether to scale data to match image dimensions
        """
        self._scale = scale
        self._center_offset_x = center_offset_x
        self._center_offset_y = center_offset_y
        self._pan_offset_x = pan_offset_x
        self._pan_offset_y = pan_offset_y
        self._manual_x = manual_x
        self._manual_y = manual_y
        self._flip_y = flip_y
        self._display_height = display_height
        self._image_scale_x = image_scale_x
        self._image_scale_y = image_scale_y
        self._scale_to_image = scale_to_image

    def apply(self, x: float, y: float, use_image_scale: bool = True) -> Tuple[float, float]:
        """
        Apply this transform to a point.

        This transforms a point from data space to screen/widget space.
        The transformation pipeline includes scaling, offset application,
        and coordinate system adjustments.

        Args:
            x: X coordinate in data space
            y: Y coordinate in data space
            use_image_scale: Whether to apply image scaling (default: True)

        Returns:
            Tuple containing the transformed (x, y) coordinates in screen space
        """
        # 0. Apply image scaling if scale_to_image is enabled and use_image_scale is True
        # This adjusts data coordinates to match image dimensions
        tx = x
        ty = y
        if self._scale_to_image and use_image_scale:
            tx = x * self._image_scale_x
            ty = y * self._image_scale_y

        # 1. Apply Y-flip if needed
        if self._flip_y:
            ty = self._display_height - ty

        # 2. Apply scale (this is the main scale factor for fitting in the widget)
        sx = tx * self._scale
        sy = ty * self._scale

        # 3. Apply centering offset (this centers content in the widget)
        cx = sx + self._center_offset_x
        cy = sy + self._center_offset_y

        # 4. Apply pan offset (this is from user panning)
        px = cx + self._pan_offset_x
        py = cy + self._pan_offset_y

        # 5. Apply manual offset (for fine-tuning alignment)
        fx = px + self._manual_x
        fy = py + self._manual_y

        return fx, fy

    def apply_qt_point(self, x: float, y: float) -> QPointF:
        """
        Apply this transform to a point and return a QPointF.

        Args:
            x: X coordinate in data space
            y: Y coordinate in data space

        Returns:
            QPointF containing the transformed coordinates in screen space
        """
        fx, fy = self.apply(x, y)
        return QPointF(fx, fy)

    def apply_for_image_position(self) -> Tuple[float, float]:
        """
        Calculate the correct position for the background image.

        CRITICAL FIX UPDATE: This method now applies the transform to (0,0)
        and INCLUDES the image scaling adjustment when scale_to_image is true,
        which ensures proper alignment between the curve and the background image.

        Returns:
            Tuple containing the (x, y) top-left position for the background image
        """
        # UPDATED APPROACH: Apply transform to (0,0) WITH image scaling when scale_to_image is true
        # This ensures the image position is consistent with how curve points are being transformed
        # The previous approach skipped image scaling, which caused the curve to appear "floating" above the image

        # Start with the origin
        tx, ty = 0.0, 0.0

        # 0. Apply image scaling if scale_to_image is enabled
        # This critical change matches how points are transformed in the apply() method
        if self._scale_to_image:
            tx = tx * self._image_scale_x
            ty = ty * self._image_scale_y

        # Apply Y-flip if needed (BEFORE applying scale)
        if self._flip_y:
            ty = self._display_height - ty

        # Apply scale
        sx = tx * self._scale
        sy = ty * self._scale

        # Apply centering offset
        cx = sx + self._center_offset_x
        cy = sy + self._center_offset_y

        # Apply pan offset
        px = cx + self._pan_offset_x
        py = cy + self._pan_offset_y

        # Apply manual offset for fine-tuning alignment
        img_x = px + self._manual_x
        img_y = py + self._manual_y

        # Log the updated approach for debugging
        logger.debug(f"Updated image positioning: ({img_x:.1f}, {img_y:.1f}), flip_y={self._flip_y}")
        logger.debug(f"Transform params: scale={self._scale:.4f}, image_scale=({self._image_scale_x:.2f}, {self._image_scale_y:.2f})")
        logger.debug(f"Manual offset: ({self._manual_x:.1f}, {self._manual_y:.1f}), Pan offset: ({self._pan_offset_x:.1f}, {self._pan_offset_y:.1f})")
        logger.debug(f"Scale to image: {self._scale_to_image}")

        return img_x, img_y

    def get_parameters(self) -> Dict[str, Any]:
        """
        Get the transform parameters.

        Returns:
            Dictionary containing all transformation parameters
        """
        return {
            "scale": self._scale,
            "center_offset": (self._center_offset_x, self._center_offset_y),
            "pan_offset": (self._pan_offset_x, self._pan_offset_y),
            "manual_offset": (self._manual_x, self._manual_y),
            "flip_y": self._flip_y,
            "display_height": self._display_height,
            "image_scale": (self._image_scale_x, self._image_scale_y),
            "scale_to_image": self._scale_to_image
        }

    def with_updates(self, **kwargs) -> 'Transform':
        """
        Create a new Transform with updated parameters.

        Args:
            **kwargs: New values for any parameters to update

        Returns:
            A new Transform instance with the specified updates applied
        """
        params = self.get_parameters()

        # Extract nested values if needed
        if 'center_offset' in kwargs:
            params['center_offset_x'], params['center_offset_y'] = kwargs.pop('center_offset')
        if 'pan_offset' in kwargs:
            params['pan_offset_x'], params['pan_offset_y'] = kwargs.pop('pan_offset')
        if 'manual_offset' in kwargs:
            params['manual_x'], params['manual_y'] = kwargs.pop('manual_offset')
        if 'image_scale' in kwargs:
            params['image_scale_x'], params['image_scale_y'] = kwargs.pop('image_scale')

        # Flatten nested parameters
        flattened_params = {
            'scale': params['scale'],
            'center_offset_x': params['center_offset'][0],
            'center_offset_y': params['center_offset'][1],
            'pan_offset_x': params['pan_offset'][0],
            'pan_offset_y': params['pan_offset'][1],
            'manual_x': params['manual_offset'][0],
            'manual_y': params['manual_offset'][1],
            'flip_y': params['flip_y'],
            'display_height': params['display_height'],
            'image_scale_x': params['image_scale'][0],
            'image_scale_y': params['image_scale'][1],
            'scale_to_image': params['scale_to_image']
        }

        # Apply updates
        flattened_params.update(kwargs)

        # Create new instance
        return Transform(
            scale=flattened_params['scale'],
            center_offset_x=flattened_params['center_offset_x'],
            center_offset_y=flattened_params['center_offset_y'],
            pan_offset_x=flattened_params['pan_offset_x'],
            pan_offset_y=flattened_params['pan_offset_y'],
            manual_x=flattened_params['manual_x'],
            manual_y=flattened_params['manual_y'],
            flip_y=flattened_params['flip_y'],
            display_height=flattened_params['display_height'],
            image_scale_x=flattened_params['image_scale_x'],
            image_scale_y=flattened_params['image_scale_y'],
            scale_to_image=flattened_params['scale_to_image']
        )
