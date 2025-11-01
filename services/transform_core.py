#!/usr/bin/env python
"""
Core transformation classes for CurveEditor.

Contains the fundamental ViewState and Transform classes that handle
coordinate transformations between data space and screen space.

This module is the foundation of the transformation system and has no
dependencies on other services to avoid circular imports.
"""

import hashlib
import logging
import math
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast
from typing_extensions import override
if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray
else:
    # Runtime fallback for numpy imports
    np = None
    NDArray = None

from core.defaults import DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH


# Simple validation helpers
def validate_finite(value: float, _name: str, default: float = 0.0) -> float:
    """Ensure value is finite, return default if not."""
    if not math.isfinite(value):
        return default
    return value


def validate_scale(
    value: float, _name: str, min_scale: float = 1e-10, max_scale: float = 1e10, default: float = 1.0
) -> float:
    """Validate scale value is positive and within bounds."""
    if not math.isfinite(value) or value <= 0:
        return default
    return max(min_scale, min(max_scale, value))


def validate_point(x: float, y: float, _context: str) -> tuple[float, float]:
    """Validate coordinate pair."""
    # Parameters are already typed as float, so we only need to check finiteness
    if not (math.isfinite(x) and math.isfinite(y)):
        return (0.0, 0.0)
    return (x, y)


# Quantization Constants
DEFAULT_PRECISION = 0.1  # Default precision for quantization (pixels)
ZOOM_PRECISION_FACTOR = 100  # Factor for finer zoom precision
ZOOM_PRECISION = DEFAULT_PRECISION / ZOOM_PRECISION_FACTOR  # 0.001 for zoom
MIN_SCALE_VALUE = 1e-10  # Minimum value for scale factors to prevent division by zero

if TYPE_CHECKING:
    from PySide6.QtCore import QPointF

    from protocols.ui import CurveViewProtocol
else:
    try:
        from PySide6.QtCore import QPointF
    except ImportError:
        # Stub for when PySide6 is not available
        class QPointF:
            def __init__(self, x: float = 0, y: float = 0) -> None:
                self._x: float = x
                self._y: float = y

            def x(self) -> float:
                return self._x

            def y(self) -> float:
                return self._y

            def setX(self, x: float) -> None:
                self._x = x

            def setY(self, y: float) -> None:
                self._y = y


logger = logging.getLogger("transform_core")


@dataclass(frozen=True)
class ValidationConfig:
    """Configuration for validation behavior."""

    enable_full_validation: bool = True
    max_coordinate: float = 1e12
    min_scale: float = 1e-10
    max_scale: float = 1e10

    @classmethod
    def for_production(cls) -> "ValidationConfig":
        """Production config - fast with critical checks only."""
        return cls(enable_full_validation=False)

    @classmethod
    def for_debug(cls) -> "ValidationConfig":
        """Debug config - comprehensive validation."""
        return cls(enable_full_validation=True)

    @classmethod
    def from_environment(cls) -> "ValidationConfig":
        """Create config based on environment variables and debug mode."""
        from core.config import get_config

        config = get_config()

        # Read from environment variable first, then check debug mode
        env_val = os.getenv("CURVE_EDITOR_FULL_VALIDATION", "").lower()
        enable_full = env_val in ("1", "true", "yes") if env_val else __debug__

        # Override with config flag if force_debug_validation is enabled
        if config.force_debug_validation:
            enable_full = True

        # Read other optional config from environment
        max_coord = float(os.getenv("CURVE_EDITOR_MAX_COORDINATE", "1e12"))
        min_scale = float(os.getenv("CURVE_EDITOR_MIN_SCALE", "1e-10"))
        max_scale = float(os.getenv("CURVE_EDITOR_MAX_SCALE", "1e10"))

        return cls(
            enable_full_validation=enable_full, max_coordinate=max_coord, min_scale=min_scale, max_scale=max_scale
        )


def calculate_center_offset(
    widget_width: int,
    widget_height: int,
    display_width: int | float,
    display_height: int | float,
    scale: float,
    flip_y_axis: bool,
    scale_to_image: bool,
) -> tuple[float, float]:
    """
    Calculate center offset for transformations.

    UNIFIED METHOD: Single source of truth for center offset calculation,
    replacing 3 duplicate implementations.

    Args:
        widget_width: Widget width in pixels
        widget_height: Widget height in pixels
        display_width: Display/content width
        display_height: Display/content height
        scale: Scale factor to apply
        flip_y_axis: Whether Y-axis is flipped (e.g., 3DEqualizer data)
        scale_to_image: Whether scaling to image dimensions

    Returns:
        Tuple of (center_x, center_y) offsets
    """
    # Unified logic for all coordinate systems
    if scale == 1.0 and not scale_to_image and not flip_y_axis:
        # Direct 1:1 pixel mapping
        return (0.0, 0.0)
    else:
        # Standard centering calculation for all other cases
        # This ensures content is centered in the widget
        center_x = (widget_width - display_width * scale) / 2
        center_y = (widget_height - display_height * scale) / 2
        return (center_x, center_y)


@dataclass(frozen=True)
class ViewState:
    """
    Immutable class representing the view state for coordinate transformations.

    Encapsulates all parameters that affect coordinate transformations
    between data space and screen space.
    """

    # Core display parameters
    display_width: float  # Changed to float for sub-pixel precision
    display_height: float  # Changed to float for sub-pixel precision
    widget_width: int
    widget_height: int

    # View transformation parameters
    zoom_factor: float = 1.0  # User zoom level only (not compounded)
    fit_scale: float = 1.0  # Scale to fit content in widget (separate from zoom)
    offset_x: float = 0.0
    offset_y: float = 0.0

    # Configuration options
    scale_to_image: bool = True
    flip_y_axis: bool = False

    # Manual adjustments
    manual_x_offset: float = 0.0
    manual_y_offset: float = 0.0

    # Background image reference (optional) - excluded from hash for LRU cache
    background_image: object | None = field(default=None, hash=False)

    # Original data dimensions for scaling
    image_width: int = DEFAULT_IMAGE_WIDTH
    image_height: int = DEFAULT_IMAGE_HEIGHT

    def with_updates(self, **kwargs: object) -> "ViewState":
        """Create a new ViewState with updated values."""
        # Merge current values with updates, ensuring proper types
        updated = dict(self.__dict__)
        updated.update(kwargs)
        # Type ignore for dict unpacking with mixed types
        return ViewState(**updated)  # type: ignore[arg-type]

    def quantized_for_cache(self, precision: float = DEFAULT_PRECISION) -> "ViewState":
        """
        Create a quantized version of ViewState for better cache hit rates.

        Simplified implementation with clear constants and straightforward logic.

        Args:
            precision: Rounding precision for float parameters (default 0.1 pixels)

        Returns:
            ViewState with quantized floating-point values
        """
        from core.error_messages import ValidationError

        # Validate precision parameter
        if precision <= 0:
            raise ValidationError(
                "precision", precision, "must be positive", "Use 0.1 for coarse or 0.01 for fine precision"
            )

        # Simple, clear quantization function
        def quantize_value(value: float, prec: float) -> float:
            """Simple quantization with finite value check."""
            if not math.isfinite(value):
                return 0.0
            return round(value / prec) * prec

        # Use defined constants for clarity
        zoom_precision = precision / ZOOM_PRECISION_FACTOR  # Finer precision for zoom

        # Quantize each value with appropriate precision
        # Special handling for zoom: only apply MIN_SCALE_VALUE if the original value was finite
        quantized_zoom = quantize_value(self.zoom_factor, zoom_precision)
        new_zoom = quantized_zoom if not math.isfinite(self.zoom_factor) else max(quantized_zoom, MIN_SCALE_VALUE)
        new_offset_x = quantize_value(self.offset_x, precision)
        new_offset_y = quantize_value(self.offset_y, precision)
        new_manual_x = quantize_value(self.manual_x_offset, precision)
        new_manual_y = quantize_value(self.manual_y_offset, precision)

        # Always create new ViewState for consistency (removes complex early return logic)
        return ViewState(
            # Display dimensions (float for precision)
            display_width=self.display_width,
            display_height=self.display_height,
            # Widget dimensions (integer)
            widget_width=self.widget_width,
            widget_height=self.widget_height,
            image_width=self.image_width,
            image_height=self.image_height,
            # Boolean parameters - no quantization needed
            scale_to_image=self.scale_to_image,
            flip_y_axis=self.flip_y_axis,
            # Quantized floating-point parameters
            zoom_factor=new_zoom,
            fit_scale=quantize_value(self.fit_scale, zoom_precision),  # Quantize fit_scale too
            offset_x=new_offset_x,
            offset_y=new_offset_y,
            manual_x_offset=new_manual_x,
            manual_y_offset=new_manual_y,
            # Background image - excluded from hash anyway
            background_image=self.background_image,
        )

    def to_dict(self) -> dict[str, object]:
        """Convert the ViewState to a dictionary."""
        return {
            "display_dimensions": (self.display_width, self.display_height),
            "widget_dimensions": (self.widget_width, self.widget_height),
            "image_dimensions": (self.image_width, self.image_height),
            "zoom_factor": self.zoom_factor,
            "offset": (self.offset_x, self.offset_y),
            "scale_to_image": self.scale_to_image,
            "flip_y_axis": self.flip_y_axis,
            "manual_offset": (self.manual_x_offset, self.manual_y_offset),
            "has_background_image": self.background_image is not None,
        }

    @classmethod
    def _get_image_width(cls, curve_view: "CurveViewProtocol") -> int:
        """Get image width with type safety."""
        return curve_view.image_width

    @classmethod
    def _get_image_height(cls, curve_view: "CurveViewProtocol") -> int:
        """Get image height with type safety."""
        return curve_view.image_height

    @classmethod
    def _get_pan_offset_x(cls, curve_view: "CurveViewProtocol") -> float:
        """Get pan offset X with type safety."""
        return curve_view.pan_offset_x

    @classmethod
    def _get_pan_offset_y(cls, curve_view: "CurveViewProtocol") -> float:
        """Get pan offset Y with type safety."""
        return curve_view.pan_offset_y

    @classmethod
    def _get_manual_offset_x(cls, curve_view: "CurveViewProtocol") -> float:
        """Get manual offset X with type safety."""
        return curve_view.manual_offset_x

    @classmethod
    def _get_manual_offset_y(cls, curve_view: "CurveViewProtocol") -> float:
        """Get manual offset Y with type safety."""
        return curve_view.manual_offset_y

    @classmethod
    def _get_background_image(cls, curve_view: "CurveViewProtocol"):
        """Get background image with type safety."""
        return curve_view.background_image

    @classmethod
    def _get_zoom_factor(cls, curve_view: "CurveViewProtocol") -> float:
        """Get zoom factor with type safety."""
        return curve_view.zoom_factor

    @classmethod
    def _get_scale_to_image(cls, curve_view: "CurveViewProtocol") -> bool:
        """Get scale_to_image flag with type safety."""
        return curve_view.scale_to_image

    @classmethod
    def _get_flip_y_axis(cls, curve_view: "CurveViewProtocol") -> bool:
        """Get flip_y_axis flag with type safety."""
        return curve_view.flip_y_axis

    @classmethod
    def from_curve_view(cls, curve_view: "CurveViewProtocol") -> "ViewState":
        """Create a ViewState from a CurveView instance."""
        # Get widget dimensions
        widget_width: int = curve_view.width()
        widget_height: int = curve_view.height()

        # Get original data dimensions with type safety
        image_width: int = cls._get_image_width(curve_view)
        image_height: int = cls._get_image_height(curve_view)

        # Get display dimensions (initially same as image dimensions)
        display_width: int = image_width
        display_height: int = image_height

        # Check for background image dimensions
        background_image = cls._get_background_image(curve_view)
        if background_image:
            display_width = background_image.width()
            display_height = background_image.height()

        # Get and sanitize zoom factor
        raw_zoom = cls._get_zoom_factor(curve_view)
        zoom_factor = validate_scale(raw_zoom, "zoom_factor", min_scale=1e-10, max_scale=1e6, default=1.0)

        # Get and sanitize offsets with fallbacks for attribute variations
        offset_x = validate_finite(cls._get_pan_offset_x(curve_view), "offset_x", 0.0)
        offset_y = validate_finite(cls._get_pan_offset_y(curve_view), "offset_y", 0.0)
        manual_x_offset = validate_finite(cls._get_manual_offset_x(curve_view), "manual_x_offset", 0.0)
        manual_y_offset = validate_finite(cls._get_manual_offset_y(curve_view), "manual_y_offset", 0.0)

        # Create the ViewState
        return cls(
            display_width=display_width,
            display_height=display_height,
            widget_width=widget_width,
            widget_height=widget_height,
            zoom_factor=zoom_factor,
            offset_x=offset_x,
            offset_y=offset_y,
            scale_to_image=cls._get_scale_to_image(curve_view),
            flip_y_axis=cls._get_flip_y_axis(curve_view),
            manual_x_offset=manual_x_offset,
            manual_y_offset=manual_y_offset,
            background_image=background_image,
            image_width=image_width,
            image_height=image_height,
        )


class Transform:
    """
    Unified immutable class representing a coordinate transformation.

    Consolidates all transformation logic with consistent mapping between
    data coordinates and screen coordinates.

    Transformation pipeline:
    1. Image scaling adjustment (if enabled)
    2. Y-axis flipping (optional)
    3. Main scaling
    4. Centering offset application
    5. Pan offset application
    6. Manual offset application
    """

    _parameters: dict[str, float | bool | int]
    _stability_hash: str
    _combined_scale_x: float
    _combined_scale_y: float
    _combined_offset_x: float
    _combined_offset_y: float
    validation_config: ValidationConfig

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
        validation_config: "ValidationConfig | None" = None,
    ):
        """Initialize transformation parameters with conditional validation for performance."""
        # Store validation config
        self.validation_config = validation_config or ValidationConfig.from_environment()

        # STEP 1: Initial sanitization - always prevent NaN/infinity issues
        scale = validate_finite(scale, "scale", 1.0)
        image_scale_x = validate_finite(image_scale_x, "image_scale_x", 1.0)
        image_scale_y = validate_finite(image_scale_y, "image_scale_y", 1.0)
        center_offset_x = validate_finite(center_offset_x, "center_offset_x", 0.0)
        center_offset_y = validate_finite(center_offset_y, "center_offset_y", 0.0)
        pan_offset_x = validate_finite(pan_offset_x, "pan_offset_x", 0.0)
        pan_offset_y = validate_finite(pan_offset_y, "pan_offset_y", 0.0)
        manual_offset_x = validate_finite(manual_offset_x, "manual_offset_x", 0.0)
        manual_offset_y = validate_finite(manual_offset_y, "manual_offset_y", 0.0)

        # STEP 2: CRITICAL VALIDATION - Handle based on validation mode
        if abs(scale) < 1e-10:
            if self.validation_config.enable_full_validation:
                raise ValueError(f"Scale factor too small (near zero): {scale}. Must be >= 1e-10")
            else:
                # Production mode: clamp to minimum safe value
                logger.warning(f"Scale factor too small: {scale}, clamping to 1e-10")
                scale = 1e-10 if scale >= 0 else -1e-10

        # Handle image scale validation similarly
        if abs(image_scale_x) < 1e-10:
            if self.validation_config.enable_full_validation:
                raise ValueError(f"Image scale X too small (near zero): {image_scale_x}. Must be >= 1e-10")
            else:
                logger.warning(f"Image scale X too small: {image_scale_x}, clamping to 1e-10")
                image_scale_x = 1e-10 if image_scale_x >= 0 else -1e-10

        if abs(image_scale_y) < 1e-10:
            if self.validation_config.enable_full_validation:
                raise ValueError(f"Image scale Y too small (near zero): {image_scale_y}. Must be >= 1e-10")
            else:
                logger.warning(f"Image scale Y too small: {image_scale_y}, clamping to 1e-10")
                image_scale_y = 1e-10 if image_scale_y >= 0 else -1e-10

        # STEP 3: CONDITIONAL VALIDATION - Debug mode strict, production mode graceful
        if self.validation_config.enable_full_validation:
            # DEBUG MODE: Strict validation with exceptions

            # Validate reasonable scale ranges to prevent overflow
            max_scale = self.validation_config.max_scale
            if abs(scale) > max_scale:
                raise ValueError(f"Scale factor too large: {scale}. Must be <= {max_scale}")
            if abs(image_scale_x) > max_scale or abs(image_scale_y) > max_scale:
                raise ValueError(
                    f"Image scale factors too large: X={image_scale_x}, Y={image_scale_y}. Must be <= {max_scale}"
                )

            # Validate display dimensions
            if display_height < 0:
                raise ValueError(f"Display height cannot be negative: {display_height}")
            if display_height > 1000000:  # Sanity check for extremely large displays
                raise ValueError(f"Display height too large: {display_height}. Must be <= 1,000,000")

            # Validate coordinate offsets to prevent overflow
            max_offset = 1e9
            for name, value in [
                ("center_offset_x", center_offset_x),
                ("center_offset_y", center_offset_y),
                ("pan_offset_x", pan_offset_x),
                ("pan_offset_y", pan_offset_y),
                ("manual_offset_x", manual_offset_x),
                ("manual_offset_y", manual_offset_y),
            ]:
                if abs(value) > max_offset:
                    raise ValueError(f"Offset {name} too large: {value}. Must be <= {max_offset}")
        else:
            # PRODUCTION MODE: Graceful correction with warnings

            # Validate and clamp scale ranges
            scale = validate_scale(
                scale,
                "scale",
                min_scale=self.validation_config.min_scale,
                max_scale=self.validation_config.max_scale,
                default=1.0,
            )
            image_scale_x = validate_scale(
                image_scale_x,
                "image_scale_x",
                min_scale=self.validation_config.min_scale,
                max_scale=self.validation_config.max_scale,
                default=1.0,
            )
            image_scale_y = validate_scale(
                image_scale_y,
                "image_scale_y",
                min_scale=self.validation_config.min_scale,
                max_scale=self.validation_config.max_scale,
                default=1.0,
            )

            # Validate and correct display dimensions
            if display_height < 0:
                logger.warning(
                    f"Display height negative: {display_height}, using absolute value: {abs(display_height)}"
                )
                display_height = abs(display_height) if display_height != 0 else 1
            elif display_height > 1000000:
                logger.warning(f"Display height too large: {display_height}, clamping to 1,000,000")
                display_height = 1000000

            # Validate and clamp coordinate offsets
            max_offset = 1e9
            offsets = [
                ("center_offset_x", center_offset_x),
                ("center_offset_y", center_offset_y),
                ("pan_offset_x", pan_offset_x),
                ("pan_offset_y", pan_offset_y),
                ("manual_offset_x", manual_offset_x),
                ("manual_offset_y", manual_offset_y),
            ]
            for name, value in offsets:
                if abs(value) > max_offset:
                    clamped = max_offset if value > 0 else -max_offset
                    logger.warning(f"Offset {name} too large: {value}, clamping to {clamped}")
                    # Update the local variable
                    if name == "center_offset_x":
                        center_offset_x = clamped
                    elif name == "center_offset_y":
                        center_offset_y = clamped
                    elif name == "pan_offset_x":
                        pan_offset_x = clamped
                    elif name == "pan_offset_y":
                        pan_offset_y = clamped
                    elif name == "manual_offset_x":
                        manual_offset_x = clamped
                    elif name == "manual_offset_y":
                        manual_offset_y = clamped

        # Store all corrected parameters as immutable private attributes
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

        # Pre-calculate combined values for 3-step pipeline optimization
        # Step 1: Combined scale (main scale * image scale if enabled)
        if scale_to_image:
            self._combined_scale_x = scale * image_scale_x
            self._combined_scale_y = scale * image_scale_y
        else:
            self._combined_scale_x = scale
            self._combined_scale_y = scale

        # Step 2: Combined offset (center + pan + manual)
        self._combined_offset_x = center_offset_x + pan_offset_x + manual_offset_x
        self._combined_offset_y = center_offset_y + pan_offset_y + manual_offset_y

        # Compute stability hash for caching (only in debug builds)
        if self.validation_config.enable_full_validation:
            self._stability_hash = self._compute_stability_hash()
        else:
            # Use simpler hash in production for performance
            self._stability_hash = str(hash((scale, center_offset_x, center_offset_y, flip_y, display_height)))

    def _compute_stability_hash(self) -> str:
        """Compute a hash of the transformation parameters for stability tracking."""
        # Create a string representation of all parameters
        param_str = "|".join(f"{k}:{v}" for k, v in sorted(self._parameters.items()))
        # Return MD5 hash for efficient comparison
        return hashlib.md5(param_str.encode()).hexdigest()

    @property
    def stability_hash(self) -> str:
        """Get the stability hash for this transformation."""
        return self._stability_hash

    @property
    def scale(self) -> float:
        """Get the main scaling factor."""
        return self._parameters["scale"]

    @property
    def center_offset(self) -> tuple[float, float]:
        """Get the centering offset as (x, y) tuple."""
        return (self._parameters["center_offset_x"], self._parameters["center_offset_y"])

    @property
    def pan_offset(self) -> tuple[float, float]:
        """Get the pan offset as (x, y) tuple."""
        return (self._parameters["pan_offset_x"], self._parameters["pan_offset_y"])

    @property
    def manual_offset(self) -> tuple[float, float]:
        """Get the manual offset as (x, y) tuple."""
        return (self._parameters["manual_offset_x"], self._parameters["manual_offset_y"])

    @property
    def flip_y(self) -> bool:
        """Check if Y-axis should be flipped."""
        return cast(bool, self._parameters["flip_y"])

    @property
    def display_height(self) -> int:
        """Get the display height."""
        return cast(int, self._parameters["display_height"])

    @property
    def image_scale(self) -> tuple[float, float]:
        """Get the image scale factors as (x, y) tuple."""
        return (self._parameters["image_scale_x"], self._parameters["image_scale_y"])

    @property
    def scale_to_image(self) -> bool:
        """Check if scaling to image dimensions is enabled."""
        return cast(bool, self._parameters["scale_to_image"])

    def get_parameters(self) -> dict[str, object]:
        """Get all transformation parameters as a dictionary."""
        return cast(dict[str, object], self._parameters.copy())

    def data_to_screen(self, x: float, y: float) -> tuple[float, float]:
        """
        Transform data coordinates to screen coordinates using simplified 3-step pipeline.

        Simplified pipeline:
        1. Flip: Y-axis flipping (if needed)
        2. Scale: Combined scaling (main * image scale)
        3. Offset: Combined offset (center + pan + manual)

        Args:
            x: Data X coordinate
            y: Data Y coordinate

        Returns:
            Tuple of (screen_x, screen_y)

        Raises:
            ValueError: If input coordinates are invalid or would cause overflow
        """
        # CONDITIONAL VALIDATION: Behavior depends on validation mode
        if self.validation_config.enable_full_validation:
            # DEBUG MODE: Strict validation - check for invalid values first, then ranges
            if not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError(f"Input coordinates must be finite: x={x}, y={y}")

            # Validate input coordinates to prevent overflow (expensive range check)
            max_coord = self.validation_config.max_coordinate
            if abs(x) > max_coord or abs(y) > max_coord:
                raise ValueError(f"Input coordinates too large: x={x}, y={y}. Must be <= {max_coord}")
        else:
            # PRODUCTION MODE: Graceful correction using validation utilities
            # This prevents crashes and undefined behavior in production
            x, y = validate_point(x, y, "coordinate_transform")

        # Step 1: Flip - Apply Y-axis flipping (convert from data to display coordinate system)
        if self.flip_y and self.display_height > 0:
            y = self.display_height - y

        # Step 2: Scale - Apply combined scaling (pre-calculated)
        x *= self._combined_scale_x
        y *= self._combined_scale_y

        # Step 3: Offset - Apply combined offset (pre-calculated)
        x += self._combined_offset_x
        y += self._combined_offset_y

        return (x, y)

    def screen_to_data(self, x: float, y: float) -> tuple[float, float]:
        """
        Transform screen coordinates to data coordinates using simplified 3-step pipeline.

        Reverse pipeline:
        1. Offset: Remove combined offset
        2. Scale: Remove combined scaling
        3. Flip: Reverse Y-axis flipping (if needed)

        Args:
            x: Screen X coordinate
            y: Screen Y coordinate

        Returns:
            Tuple of (data_x, data_y)

        Raises:
            ValueError: If input coordinates are invalid or would cause overflow
        """
        # CONDITIONAL VALIDATION: Behavior depends on validation mode
        if self.validation_config.enable_full_validation:
            # DEBUG MODE: Strict validation - check for invalid values first, then ranges
            if not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError(f"Input coordinates must be finite: x={x}, y={y}")

            # Validate input coordinates to prevent overflow (expensive range check)
            max_coord = self.validation_config.max_coordinate
            if abs(x) > max_coord or abs(y) > max_coord:
                raise ValueError(f"Input coordinates too large: x={x}, y={y}. Must be <= {max_coord}")
        else:
            # PRODUCTION MODE: Graceful correction using validation utilities
            # This prevents crashes and undefined behavior in production
            x, y = validate_point(x, y, "coordinate_transform")

        # Reverse Step 3: Remove combined offset
        x -= self._combined_offset_x
        y -= self._combined_offset_y

        # Reverse Step 2: Remove combined scaling with safe division
        if abs(self._combined_scale_x) < 1e-10:
            raise ValueError(f"Cannot perform inverse transform: combined_scale_x too small: {self._combined_scale_x}")
        if abs(self._combined_scale_y) < 1e-10:
            raise ValueError(f"Cannot perform inverse transform: combined_scale_y too small: {self._combined_scale_y}")

        x /= self._combined_scale_x
        y /= self._combined_scale_y

        # Reverse Step 1: Reverse Y-axis flipping (convert from display to data coordinate system)
        if self.flip_y and self.display_height > 0:
            y = self.display_height - y

        return (x, y)

    def data_to_screen_qpoint(self, point: QPointF) -> QPointF:
        """Transform a QPointF from data to screen coordinates."""
        x, y = self.data_to_screen(point.x(), point.y())
        return QPointF(x, y)

    def screen_to_data_qpoint(self, point: QPointF) -> QPointF:
        """Transform a QPointF from screen to data coordinates."""
        x, y = self.screen_to_data(point.x(), point.y())
        return QPointF(x, y)

    def batch_data_to_screen(self, points: "NDArray[np.float64]") -> "NDArray[np.float64]":
        """Transform multiple data points to screen coordinates in batch.

        Args:
            points: Nx2 or Nx3 array where columns are [x, y] or [frame, x, y]

        Returns:
            Nx2 array of screen coordinates [x, y]

        Raises:
            ValueError: If input array has wrong shape or invalid data
        """
        import numpy as np

        # Validate input array
        if points.ndim != 2:
            raise ValueError(f"Expected 2D array, got {points.ndim}D")

        if points.shape[1] == 3:
            # Has frame column, extract x, y
            data_points = points[:, 1:3].copy()
        elif points.shape[1] == 2:
            data_points = points.copy()
        else:
            raise ValueError(f"Expected 2 or 3 columns, got {points.shape[1]}")

        if len(data_points) == 0:
            return np.empty((0, 2), dtype=np.float64)

        # CONDITIONAL VALIDATION: Behavior depends on validation mode
        if self.validation_config.enable_full_validation:
            # DEBUG MODE: Strict validation
            if not np.all(np.isfinite(data_points)):
                raise ValueError("All input coordinates must be finite")

            # Validate coordinate ranges to prevent overflow
            max_coord = self.validation_config.max_coordinate
            if np.any(np.abs(data_points) > max_coord):
                raise ValueError(f"Input coordinates too large. Must be <= {max_coord}")
        else:
            # PRODUCTION MODE: Graceful correction
            # Replace non-finite values with zeros
            mask = ~np.isfinite(data_points)
            if np.any(mask):
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Replacing {np.sum(mask)} non-finite coordinates with zeros")
                data_points[mask] = 0.0

        # Step 1: Apply Y-axis flipping (vectorized)
        if self.flip_y and self.display_height > 0:
            data_points[:, 1] = self.display_height - data_points[:, 1]

        # Step 2: Apply combined scaling (vectorized)
        data_points[:, 0] *= self._combined_scale_x
        data_points[:, 1] *= self._combined_scale_y

        # Step 3: Apply combined offset (vectorized)
        data_points[:, 0] += self._combined_offset_x
        data_points[:, 1] += self._combined_offset_y

        return data_points

    def batch_screen_to_data(self, points: "NDArray[np.float64]") -> "NDArray[np.float64]":
        """Transform multiple screen points to data coordinates in batch.

        Args:
            points: Nx2 array of screen coordinates [x, y]

        Returns:
            Nx2 array of data coordinates [x, y]

        Raises:
            ValueError: If input array has wrong shape or invalid data
        """
        import numpy as np

        # Validate input array
        if points.ndim != 2 or points.shape[1] != 2:
            raise ValueError(f"Expected Nx2 array, got shape {points.shape}")

        if len(points) == 0:
            return np.empty((0, 2), dtype=np.float64)

        data_points = points.copy()

        # CONDITIONAL VALIDATION: Behavior depends on validation mode
        if self.validation_config.enable_full_validation:
            # DEBUG MODE: Strict validation
            if not np.all(np.isfinite(data_points)):
                raise ValueError("All input coordinates must be finite")

            # Validate coordinate ranges to prevent overflow
            max_coord = self.validation_config.max_coordinate
            if np.any(np.abs(data_points) > max_coord):
                raise ValueError(f"Input coordinates too large. Must be <= {max_coord}")
        else:
            # PRODUCTION MODE: Graceful correction
            # Replace non-finite values with zeros
            mask = ~np.isfinite(data_points)
            if np.any(mask):
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Replacing {np.sum(mask)} non-finite coordinates with zeros")
                data_points[mask] = 0.0

        # Validate scale factors for safe division
        if abs(self._combined_scale_x) < 1e-10:
            raise ValueError(f"Cannot perform inverse transform: combined_scale_x too small: {self._combined_scale_x}")
        if abs(self._combined_scale_y) < 1e-10:
            raise ValueError(f"Cannot perform inverse transform: combined_scale_y too small: {self._combined_scale_y}")

        # Reverse Step 3: Remove combined offset (vectorized)
        data_points[:, 0] -= self._combined_offset_x
        data_points[:, 1] -= self._combined_offset_y

        # Reverse Step 2: Remove combined scaling (vectorized)
        data_points[:, 0] /= self._combined_scale_x
        data_points[:, 1] /= self._combined_scale_y

        # Reverse Step 1: Reverse Y-axis flipping (vectorized)
        if self.flip_y and self.display_height > 0:
            data_points[:, 1] = self.display_height - data_points[:, 1]

        return data_points

    def with_updates(self, **kwargs: object) -> "Transform":
        """Create a new Transform with updated parameters."""
        # Merge current parameters with updates
        new_params = dict(self._parameters)

        # Map friendly parameter names to internal names
        param_mapping = {
            "scale": "scale",
            "center_offset_x": "center_offset_x",
            "center_offset_y": "center_offset_y",
            "pan_offset_x": "pan_offset_x",
            "pan_offset_y": "pan_offset_y",
            "manual_offset_x": "manual_offset_x",
            "manual_offset_y": "manual_offset_y",
            "flip_y": "flip_y",
            "display_height": "display_height",
            "image_scale_x": "image_scale_x",
            "image_scale_y": "image_scale_y",
            "scale_to_image": "scale_to_image",
        }

        # Update parameters
        for key, value in kwargs.items():
            if key in param_mapping:
                # Cast the object type to the expected parameter type
                if key in ["flip_y", "scale_to_image"]:
                    new_params[param_mapping[key]] = cast(bool, value)
                elif key == "display_height":
                    new_params[param_mapping[key]] = cast(int, value)
                else:
                    new_params[param_mapping[key]] = cast(float, value)

        # Create new Transform instance
        return Transform(
            scale=cast(float, new_params["scale"]),
            center_offset_x=cast(float, new_params["center_offset_x"]),
            center_offset_y=cast(float, new_params["center_offset_y"]),
            pan_offset_x=cast(float, new_params["pan_offset_x"]),
            pan_offset_y=cast(float, new_params["pan_offset_y"]),
            manual_offset_x=cast(float, new_params["manual_offset_x"]),
            manual_offset_y=cast(float, new_params["manual_offset_y"]),
            flip_y=cast(bool, new_params["flip_y"]),
            display_height=cast(int, new_params["display_height"]),
            image_scale_x=cast(float, new_params["image_scale_x"]),
            image_scale_y=cast(float, new_params["image_scale_y"]),
            scale_to_image=cast(bool, new_params["scale_to_image"]),
        )

    @classmethod
    def from_view_state(cls, view_state: ViewState, validation_config: "ValidationConfig | None" = None) -> "Transform":
        """Create a Transform from a ViewState with optional validation config."""
        # No special Y-flip validation needed with simplified approach

        # Calculate scale: Apply fit_scale first, then user zoom
        # This fixes the zoom-float bug by properly separating the two scales
        scale = view_state.fit_scale * view_state.zoom_factor

        # Calculate center offsets using unified method
        logger.debug(f"[TRANSFORM] flip_y_axis={view_state.flip_y_axis}, scale_to_image={view_state.scale_to_image}")

        # Use unified calculation method for consistency
        center_offset_x, center_offset_y = calculate_center_offset(
            widget_width=view_state.widget_width,
            widget_height=view_state.widget_height,
            display_width=view_state.display_width,
            display_height=view_state.display_height,
            scale=scale,
            flip_y_axis=view_state.flip_y_axis,
            scale_to_image=view_state.scale_to_image,
        )

        logger.info(
            f"[TRANSFORM] Center offsets calculated: ({center_offset_x:.1f}, {center_offset_y:.1f}) with scale={scale:.3f} (fit={view_state.fit_scale:.3f} * zoom={view_state.zoom_factor:.3f})"
        )

        # Calculate image scale factors with safe division
        if view_state.image_width <= 0:
            logger.warning(f"Invalid image width: {view_state.image_width}, using scale factor 1.0")
            image_scale_x = 1.0
        elif view_state.display_width < 0:
            raise ValueError(f"Display width cannot be negative: {view_state.display_width}")
        else:
            image_scale_x = view_state.display_width / view_state.image_width

        if view_state.image_height <= 0:
            logger.warning(f"Invalid image height: {view_state.image_height}, using scale factor 1.0")
            image_scale_y = 1.0
        elif view_state.display_height < 0:
            raise ValueError(f"Display height cannot be negative: {view_state.display_height}")
        else:
            image_scale_y = view_state.display_height / view_state.image_height

        return cls(
            scale=scale,
            center_offset_x=center_offset_x,
            center_offset_y=center_offset_y,
            pan_offset_x=view_state.offset_x,
            pan_offset_y=view_state.offset_y,
            manual_offset_x=view_state.manual_x_offset,
            manual_offset_y=view_state.manual_y_offset,
            flip_y=view_state.flip_y_axis,
            display_height=int(view_state.display_height),
            image_scale_x=image_scale_x,
            image_scale_y=image_scale_y,
            scale_to_image=view_state.scale_to_image,
            validation_config=validation_config,
        )

    @override
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Transform(scale={self.scale:.2f}, "
            f"center_offset=({self._parameters['center_offset_x']:.1f}, {self._parameters['center_offset_y']:.1f}), "
            f"pan_offset=({self._parameters['pan_offset_x']:.1f}, {self._parameters['pan_offset_y']:.1f}), "
            f"flip_y={self.flip_y})"
        )


__all__ = [
    "DEFAULT_PRECISION",
    "MIN_SCALE_VALUE",
    "ZOOM_PRECISION",
    "ZOOM_PRECISION_FACTOR",
    "Transform",
    "ValidationConfig",
    "ViewState",
    "calculate_center_offset",
]
