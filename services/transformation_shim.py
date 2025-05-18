"""
Transformation Shim Module for CurveEditor - DEPRECATED

⚠️  DEPRECATION NOTICE ⚠️
This module has been superseded by the unified transformation system.
Please use services/transformation_integration.py instead.

Migration path:
- Replace TransformationShim with TransformationIntegration
- Use services.transformation_integration for compatibility
- See docs/unified_transformation_system.md for migration guide

This module provides a temporary bridge between the existing transformation code
and the new transformation system. It allows incremental adoption of the new
system without breaking existing functionality.

DEPRECATED: Will be removed in future version
"""

from typing import Any, List, Tuple, Optional
from PySide6.QtCore import QPointF

from services.view_state import ViewState
from services.transform import Transform
from services.transformation_service import TransformationService
from services.logging_service import LoggingService

# Configure logger for this module
logger = LoggingService.get_logger("transformation_shim")

# Feature flag to control which transformation system to use
USE_NEW_TRANSFORMATION_SYSTEM = True

def set_use_new_transformation_system(enabled: bool) -> None:
    """Set whether to use the new transformation system."""
    global USE_NEW_TRANSFORMATION_SYSTEM
    USE_NEW_TRANSFORMATION_SYSTEM = enabled
    logger.info(f"New transformation system {'enabled' if enabled else 'disabled'}")

class TransformationShim:
    """
    Shim class for bridging between old and new transformation systems.

    This class provides methods that match the signature of existing transformation
    methods, but delegates to the new transformation system implementation.

    All methods in this class should use the TransformationService backend,
    allowing for a gradual migration to the new system with minimal code changes.
    """

    @staticmethod
    def transform_point_to_widget(curve_view: Any, x: float, y: float,
                                 display_width: Optional[float] = None,
                                 display_height: Optional[float] = None,
                                 offset_x: Optional[float] = None,
                                 offset_y: Optional[float] = None,
                                 scale: Optional[float] = None) -> Tuple[float, float]:
        """
        Transform from data coordinates to widget coordinates.

        This method acts as a compatibility layer, maintaining the signature of the
        old CurveService.transform_point method but using the TransformationService backend.

        Args:
            curve_view: The curve view instance
            x: X coordinate in data space
            y: Y coordinate in data space
            display_width: Optional override for display width
            display_height: Optional override for display height
            offset_x: Optional override for offset X
            offset_y: Optional override for offset Y
            scale: Optional override for scale

        Returns:
            Tuple containing the transformed (x, y) coordinates in widget space
        """
        # Always use the new transformation system
        return TransformationService.transform_point_to_widget(
            curve_view, x, y, display_width, display_height, offset_x, offset_y, scale
        )

    @staticmethod
    def get_view_state_for_paint(curve_view: Any) -> ViewState:
        """
        Create a ViewState for use in paintEvent.

        This helper method creates a ViewState object from a curve_view for
        use in paintEvent rendering. It handles extracting all necessary parameters.

        Args:
            curve_view: The curve view instance

        Returns:
            A ViewState object containing the current view state
        """
        return ViewState.from_curve_view(curve_view)

    @staticmethod
    def calculate_transform_for_paint(curve_view: Any) -> Transform:
        """
        Calculate a Transform for use in paintEvent.

        This helper method creates a Transform object from a curve_view for
        use in paintEvent rendering. It handles all the necessary conversions.

        Args:
            curve_view: The curve view instance

        Returns:
            A Transform object that can be used for coordinate transformations
        """
        view_state = TransformationShim.get_view_state_for_paint(curve_view)
        return TransformationService.calculate_transform(view_state)

    @staticmethod
    def transform_with_cache(transform: Transform, points: List[Tuple[Any, float, float]]) -> List[QPointF]:
        """
        Transform a list of points using a pre-calculated transform.

        This method is a thin wrapper around the Transform class's application
        to a list of points. It's provided for API compatibility with existing code.

        For new code, consider using TransformationService.transform_points_qt directly.

        Args:
            transform: The Transform to apply
            points: List of points, each with x at index 1 and y at index 2

        Returns:
            List of QPointF objects in screen space
        """
        # Directly apply the transform to all points
        return [QPointF(*transform.apply(p[1], p[2])) for p in points]

    @staticmethod
    def install_transformation_system(curve_view: Any) -> None:
        """
        Install the new transformation system in a curve view.

        This replaces the curve_view's transform_point method with the new system.

        Args:
            curve_view: The curve view instance to modify
        """
        # Patch the transform_point method in CurveService
        from services.curve_service import CurveService

        # Store the original method if not already stored
        if not hasattr(CurveService, '_original_transform_point'):
            CurveService._original_transform_point = CurveService.transform_point

        # Replace with our shim method
        CurveService.transform_point = TransformationShim.transform_point_to_widget

        # Log the installation
        logger.info(f"Transformation system installed in {curve_view.__class__.__name__}")

        # Add a transform method to the curve_view for convenience
        def get_transform(self):
            return TransformationShim.calculate_transform_for_paint(self)

        # Add the method to the curve_view class
        setattr(curve_view.__class__, 'get_transform', get_transform)

# Provide convenience methods at module level for better discoverability
def transform_point(curve_view: Any, x: float, y: float) -> Tuple[float, float]:
    """
    Transform a point to widget coordinates.

    This is a convenience function that delegates to TransformationShim.transform_point_to_widget.
    For transforming multiple points, use transform_points() which is more efficient.
    """
    return TransformationShim.transform_point_to_widget(curve_view, x, y)

def transform_points(curve_view: Any, points: List[Tuple[Any, float, float]]) -> List[QPointF]:
    """
    Transform multiple points to widget coordinates efficiently.

    This calculates the transform only once and applies it to all points.
    """
    transform = TransformationShim.calculate_transform_for_paint(curve_view)
    return TransformationShim.transform_with_cache(transform, points)

def get_transform(curve_view: Any) -> Transform:
    """
    Get the current transform for a curve view.

    This is useful when you need to manually apply transformations
    to multiple points in different contexts.
    """
    return TransformationShim.calculate_transform_for_paint(curve_view)

def install(curve_view: Any) -> None:
    """
    Install the transformation system.

    This must be called before using any transformation functionality.
    It patches the necessary methods in the curve view.
    """
    TransformationShim.install_transformation_system(curve_view)
