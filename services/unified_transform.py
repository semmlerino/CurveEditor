"""
Unified Transform Module for CurveEditor

This module implements the consolidated transformation system that replaces
the fragmented approach across multiple files. It provides a single, immutable
Transform class with consistent parameter handling and clear transformation
pipeline.

Key improvements:
- Single source of truth for transformation logic
- Immutable design for better consistency
- Clear, documented transformation pipeline
- Enhanced stability tracking
- Type-safe interfaces
"""

import hashlib
from typing import Any

try:
    from PySide6.QtCore import QPointF
except ImportError:
    # Stub for when PySide6 is not available
    class QPointF:
        def __init__(self, x=0, y=0):
            self._x = x
            self._y = y
        def x(self):
            return self._x
        def y(self):
            return self._y
        def setX(self, x):
            self._x = x
        def setY(self, y):
            self._y = y

import logging

logger = logging.getLogger("unified_transform")

class Transform:
    """
    Unified immutable class representing a coordinate transformation.

    This class consolidates all transformation logic previously scattered across
    multiple files. It provides consistent mapping between data coordinates and
    screen coordinates with a clear, documented transformation pipeline.

    The transformation pipeline:
    1. Image scaling adjustment (if enabled)
    2. Y-axis flipping (optional)
    3. Main scaling
    4. Centering offset application
    5. Pan offset application
    6. Manual offset application

    All parameters are immutable once set, ensuring consistent transformations.
    """

    def __init__(
        self,
        scale: float,
        center_offset_x: float,
        center_offset_y: float,
        pan_offset_x: float = 0.0,
        pan_offset_y: float = 0.0,
        manual_offset_x: float = 0.0,
        manual_offset_y: float = 0.0,
        flip_y: bool = False,
        display_height: int = 0,
        image_scale_x: float = 1.0,
        image_scale_y: float = 1.0,
        scale_to_image: bool = True,
    ):
        """
        Initialize transformation parameters.

        Args:
            scale: Main scaling factor to apply
            center_offset_x: X offset for centering content in widget
            center_offset_y: Y offset for centering content in widget
            pan_offset_x: X offset from user panning
            pan_offset_y: Y offset from user panning
            manual_offset_x: Manual X offset adjustment
            manual_offset_y: Manual Y offset adjustment
            flip_y: Whether to flip the Y coordinate
            display_height: Display height (needed for Y-flipping)
            image_scale_x: X scale factor for image-to-data conversion
            image_scale_y: Y scale factor for image-to-data conversion
            scale_to_image: Whether to scale data to match image dimensions
        """
        # Store all parameters as immutable private attributes
        self._parameters = {
            "scale": float(scale),
            "center_offset_x": float(center_offset_x),
            "center_offset_y": float(center_offset_y),
            "pan_offset_x": float(pan_offset_x),
            "pan_offset_y": float(pan_offset_y),
            "manual_offset_x": float(manual_offset_x),
            "manual_offset_y": float(manual_offset_y),
            "flip_y": bool(flip_y),
            "display_height": int(display_height),
            "image_scale_x": float(image_scale_x),
            "image_scale_y": float(image_scale_y),
            "scale_to_image": bool(scale_to_image),
        }

        # Calculate a hash for cache key generation
        self._hash = self._calculate_hash()

        logger.debug(
            f"Created transform: scale={scale:.4f}, center=({center_offset_x:.1f},{center_offset_y:.1f}), "
            f"image_scale=({image_scale_x:.2f},{image_scale_y:.2f})"
        )

    def _calculate_hash(self) -> int:
        """Calculate a hash for this transform for use as cache key."""
        # Create a stable string representation of all parameters
        param_str = str(sorted(self._parameters.items()))
        # Use hashlib for consistent hashing across Python versions
        return int(hashlib.md5(param_str.encode()).hexdigest()[:8], 16)

    @property
    def cache_key(self) -> int:
        """Get a cache key for this transform."""
        return self._hash

    def apply(self, x: float, y: float) -> tuple[float, float]:
        """
        Transform a point from data space to screen space.

        Applies the complete transformation pipeline to convert coordinates
        from data space to screen/widget space.

        Args:
            x: X coordinate in data space
            y: Y coordinate in data space

        Returns: tuple containing the transformed (x, y) coordinates in screen space
        """
        # Step 1: Apply image scaling first if enabled
        tx = x
        ty = y
        if self._parameters["scale_to_image"]:
            tx = x * self._parameters["image_scale_x"]
            ty = y * self._parameters["image_scale_y"]

        # Step 2: Apply Y-flip if needed
        # This needs to happen before scaling to ensure consistent behavior
        if self._parameters["flip_y"]:
            # We need to flip relative to the data height, not the display height
            # This ensures the curve aligns properly with the background image
            if self._parameters["scale_to_image"]:
                # When scaling to image, flip relative to the post-scaled height
                ty = self._parameters["display_height"] - ty
            else:
                # When not scaling, flip relative to the original data height
                ty = self._parameters["display_height"] - ty

        # Step 3: Apply main scaling factor
        tx *= self._parameters["scale"]
        ty *= self._parameters["scale"]

        # Step 4: Apply centering offsets
        tx += self._parameters["center_offset_x"]
        ty += self._parameters["center_offset_y"]

        # Step 5: Apply pan offsets from user interaction
        tx += self._parameters["pan_offset_x"]
        ty += self._parameters["pan_offset_y"]

        # Step 6: Apply manual offsets
        tx += self._parameters["manual_offset_x"]
        ty += self._parameters["manual_offset_y"]

        return tx, ty

    def apply_inverse(self, screen_x: float, screen_y: float) -> tuple[float, float]:
        """
        Transform a point from screen space to data space.

        Applies the inverse transformation to convert coordinates from
        screen/widget space back to data space.

        Args:
            screen_x: X coordinate in screen space
            screen_y: Y coordinate in screen space

        Returns: tuple containing the transformed (x, y) coordinates in data space
        """
        # Reverse the forward transformation pipeline

        # Step 6 (reverse): Remove manual offset
        px = screen_x - self._parameters["manual_offset_x"]
        py = screen_y - self._parameters["manual_offset_y"]

        # Step 5 (reverse): Remove pan offset
        cx = px - self._parameters["pan_offset_x"]
        cy = py - self._parameters["pan_offset_y"]

        # Step 4 (reverse): Remove centering offset
        sx = cx - self._parameters["center_offset_x"]
        sy = cy - self._parameters["center_offset_y"]

        # Step 3 (reverse): Remove main scale
        if self._parameters["scale"] != 0:
            tx = sx / self._parameters["scale"]
            ty = sy / self._parameters["scale"]
        else:
            tx, ty = sx, sy

        # Step 2 (reverse): Remove Y-flip if needed
        if self._parameters["flip_y"]:
            ty = self._parameters["display_height"] - ty

        # Step 1 (reverse): Remove image scaling if enabled
        x = tx
        y = ty
        if self._parameters["scale_to_image"]:
            if self._parameters["image_scale_x"] != 0:
                x = tx / self._parameters["image_scale_x"]
            if self._parameters["image_scale_y"] != 0:
                y = ty / self._parameters["image_scale_y"]

        return x, y

    def apply_qt_point(self, x: float, y: float) -> QPointF:
        """
        Apply transform and return a QPointF.

        Args:
            x: X coordinate in data space
            y: Y coordinate in data space

        Returns:
            QPointF containing the transformed coordinates in screen space
        """
        fx, fy = self.apply(x, y)
        return QPointF(fx, fy)

    def apply_for_image_position(self) -> tuple[float, float]:
        """
        Calculate the correct position for background image placement.

        This method applies the transform to the origin (0,0) to determine
        where the background image should be positioned to align properly
        with transformed curve points.

        Returns: tuple containing the (x, y) top-left position for the background image
        """
        img_x, img_y = self.apply(0.0, 0.0)

        logger.debug(f"Image position: ({img_x:.1f}, {img_y:.1f})")
        return img_x, img_y

    def with_updates(self, **kwargs: object) -> "Transform":
        """
        Create a new Transform with updated parameters.

        This method preserves immutability by creating a new instance with
        the specified parameter changes.

        Args:
            **kwargs: New values for any parameters to update

        Returns:
            A new Transform instance with the specified updates applied
        """
        # Start with current parameters
        new_params = self._parameters.copy()

        # Apply updates
        for key, value in kwargs.items():
            if key in new_params:
                new_params[key] = value
            else:
                raise ValueError(f"Unknown parameter: {key}")

        # Create new instance
        return Transform(
            scale=float(new_params["scale"]),
            center_offset_x=float(new_params["center_offset_x"]),
            center_offset_y=float(new_params["center_offset_y"]),
            pan_offset_x=float(new_params["pan_offset_x"]),
            pan_offset_y=float(new_params["pan_offset_y"]),
            manual_offset_x=float(new_params["manual_offset_x"]),
            manual_offset_y=float(new_params["manual_offset_y"]),
            flip_y=bool(new_params["flip_y"]),
            display_height=int(new_params["display_height"]),
            image_scale_x=float(new_params["image_scale_x"]),
            image_scale_y=float(new_params["image_scale_y"]),
            scale_to_image=bool(new_params["scale_to_image"]),
        )

    def get_parameters(self) -> dict[str, Any]:
        """
        Get a copy of the transform parameters.

        Returns:
            Dictionary containing all transformation parameters
        """
        return self._parameters.copy()

    def __eq__(self, other: object) -> bool:
        """Check equality based on parameters."""
        if not isinstance(other, Transform):
            return False
        return self._parameters == other._parameters

    def __hash__(self) -> int:
        """Return hash based on parameters."""
        return self._hash

    def __repr__(self) -> str:
        """String representation for debugging."""
        params = self._parameters
        return (
            f"Transform(scale={params['scale']:.4f}, "
            f"center=({params['center_offset_x']:.1f},{params['center_offset_y']:.1f}), "
            f"pan=({params['pan_offset_x']:.1f},{params['pan_offset_y']:.1f}), "
            f"manual=({params['manual_offset_x']:.1f},{params['manual_offset_y']:.1f}), "
            f"flip_y={params['flip_y']}, scale_to_image={params['scale_to_image']})"
        )
