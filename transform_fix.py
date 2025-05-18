"""
Transform fix module for CurveEditor - DEPRECATED

⚠️  DEPRECATION NOTICE ⚠️
This module has been superseded by the unified transformation system.
Please use services/unified_transformation_service.py with stable_transformation_context instead.

Migration path:
- Replace TransformStabilizer with stable_transformation_context
- Use services.transformation_integration for compatibility
- See docs/unified_transformation_system.md for migration guide

This module adds a transform stabilizer mechanism that can be applied to ensure
consistent coordinate transformations across operations, preventing unexpected
curve shifts when applying transformations like smoothing.

DEPRECATED: Will be removed in future version
"""

from typing import Tuple, Optional, Any
from PySide6.QtCore import QPointF

class TransformStabilizer:
    """Utility class to ensure consistent coordinate transformations."""

    @staticmethod
    def calculate_stable_transform(curve_view: Any) -> Tuple[float, float, float, float, float]:
        """
        Calculate stable transform parameters that won't change between operations.

        Args:
            curve_view: The curve view instance

        Returns:
            tuple: (scale, offset_x, offset_y, pan_x, pan_y)
        """
        # Get widget dimensions
        widget_width = curve_view.width()
        widget_height = curve_view.height()

        # Use the background image dimensions if available, otherwise use track dimensions
        display_width = getattr(curve_view, 'image_width', 1920)
        display_height = getattr(curve_view, 'image_height', 1080)

        if hasattr(curve_view, 'background_image') and curve_view.background_image:
            display_width = curve_view.background_image.width()
            display_height = curve_view.background_image.height()

        # Calculate the scale factor consistently
        scale_x = widget_width / display_width
        scale_y = widget_height / display_height
        scale = min(scale_x, scale_y) * getattr(curve_view, 'zoom_factor', 1.0)

        # Calculate centering offsets consistently
        from services.centering_zoom_service import CenteringZoomService
        offset_x, offset_y = CenteringZoomService.calculate_centering_offsets(
            widget_width, widget_height,
            display_width * scale, display_height * scale,
            getattr(curve_view, 'offset_x', 0), getattr(curve_view, 'offset_y', 0))

        # Get pan offsets
        pan_x = getattr(curve_view, 'offset_x', 0)
        pan_y = getattr(curve_view, 'offset_y', 0)

        # Log these parameters for debugging
        from services.logging_service import LoggingService
        logger = LoggingService.get_logger("transform_fix")
        logger.info(f"Stable transform: scale={scale:.4f}, offset=({offset_x},{offset_y}), pan=({pan_x},{pan_y})")

        return scale, offset_x, offset_y, pan_x, pan_y

    @staticmethod
    def transform_point(curve_view: Any, x: float, y: float,
                       params: Optional[Tuple[float, float, float, float, float]] = None) -> QPointF:
        """
        Transform a point using stable parameters.

        Args:
            curve_view: The curve view instance
            x: X coordinate in data space
            y: Y coordinate in data space
            params: Optional pre-calculated transform parameters

        Returns:
            QPointF: Transformed point in widget coordinates
        """
        # Calculate transform parameters if not provided
        if params is None:
            scale, offset_x, offset_y, pan_x, pan_y = TransformStabilizer.calculate_stable_transform(curve_view)
        else:
            scale, offset_x, offset_y, pan_x, pan_y = params

        # Apply Y-axis flip if needed
        ty = y
        if getattr(curve_view, "flip_y_axis", False):
            img_h = getattr(curve_view, "image_height", curve_view.height())
            ty = img_h - y

        # Apply transformations in consistent order
        # 1. Scale
        sx = x * scale
        sy = ty * scale

        # 2. Apply centering offset
        cx = sx + offset_x
        cy = sy + offset_y

        # 3. Apply pan
        px = cx + pan_x
        py = cy + pan_y

        # 4. Apply manual offset
        fx = px + getattr(curve_view, "x_offset", 0)
        fy = py + getattr(curve_view, "y_offset", 0)

        return QPointF(fx, fy)

    @staticmethod
    def install(curve_view: Any) -> None:
        """
        Install the stabilizer in the curve view.

        Args:
            curve_view: The curve view instance
        """
        # Store the original transform_point method if not already stored
        if not hasattr(curve_view, '_original_transform_point'):
            from services.curve_service import CurveService
            curve_view._original_transform_point = CurveService.transform_point

        # Replace with stable transform
        from typing import Any
        def stable_transform_point(cv: Any, x: float, y: float, *args: Any, **kwargs: Any) -> Any:
            return TransformStabilizer.transform_point(cv, x, y)

        from services.curve_service import CurveService
        # Instead of assigning to a method, assign to an attribute on the curve_view instance for monkey-patching
        curve_view.transform_point = stable_transform_point  # type: ignore[attr-defined]

        # Flag as installed
        curve_view._transform_stabilizer_installed = True

        # Log the installation
        from services.logging_service import LoggingService
        logger = LoggingService.get_logger("transform_fix")
        logger.info(f"Transform stabilizer installed in {curve_view.__class__.__name__}")
