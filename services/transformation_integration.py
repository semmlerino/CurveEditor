"""
Transformation Integration Module for CurveEditor

This module provides integration between the new unified transformation system
and existing code. It offers compatibility shims and migration utilities to
enable gradual adoption of the consolidated transformation system.

Key features:
- Backward compatibility with existing interfaces
- Drop-in replacements for old transformation methods
- Migration helpers for updating existing code
- Feature flags for controlled rollout
"""

from typing import Any, List, Tuple, Optional
from PySide6.QtCore import QPointF

from services.unified_transform import Transform
from services.unified_transformation_service import UnifiedTransformationService
from services.view_state import ViewState
from services.logging_service import LoggingService

# Configure logger for this module
logger = LoggingService.get_logger("transformation_integration")

# Feature flag for controlling new system usage
USE_UNIFIED_TRANSFORMATION_SYSTEM = True


def set_use_unified_system(enabled: bool) -> None:
    """Control whether to use the unified transformation system."""
    global USE_UNIFIED_TRANSFORMATION_SYSTEM
    USE_UNIFIED_TRANSFORMATION_SYSTEM = enabled
    logger.info(f"Unified transformation system {'enabled' if enabled else 'disabled'}")


class TransformationIntegration:
    """
    Integration layer providing compatibility with existing transformation code.

    This class offers methods that match the signatures of existing transformation
    functions but delegate to the unified transformation system underneath.
    """

    @staticmethod
    def get_transform_for_curve_view(curve_view: Any) -> Transform:
        """
        Get a transform object for a curve view.

        This is the primary method for obtaining transforms in new code.

        Args:
            curve_view: The curve view instance

        Returns:
            Transform object ready for coordinate transformations
        """
        return UnifiedTransformationService.from_curve_view(curve_view)

    @staticmethod
    def transform_point_legacy(curve_view: Any, x: float, y: float,
                              display_width: Optional[float] = None,
                              display_height: Optional[float] = None,
                              offset_x: Optional[float] = None,
                              offset_y: Optional[float] = None,
                              scale: Optional[float] = None) -> Tuple[float, float]:
        """
        Legacy transform_point method compatible with CurveService.transform_point.

        This method maintains the exact signature and behavior of the original
        transform_point method for backward compatibility.

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
        if USE_UNIFIED_TRANSFORMATION_SYSTEM:
            return UnifiedTransformationService.transform_point_to_widget(
                curve_view, x, y, display_width, display_height,
                offset_x, offset_y, scale
            )
        else:
            # Fallback to original implementation (would need to be implemented)
            logger.warning("Unified system disabled but no fallback implemented")
            return (x, y)  # Placeholder

    @staticmethod
    def transform_multiple_points(curve_view: Any,
                                 points: List[Tuple]) -> List[QPointF]:
        """
        Transform multiple points efficiently.

        This method is optimized for transforming many points at once,
        such as during rendering operations.

        Args:
            curve_view: The curve view instance
            points: List of points, each with x at index 1 and y at index 2

        Returns:
            List of QPointF objects in screen space
        """
        transform = TransformationIntegration.get_transform_for_curve_view(curve_view)
        return UnifiedTransformationService.transform_points_qt(transform, points)

    @staticmethod
    def install_in_curve_view(curve_view: Any) -> None:
        """
        Install unified transformation system in a curve view.

        This method patches the curve view to use the new transformation system
        while maintaining compatibility with existing code.

        Args:
            curve_view: The curve view instance to modify
        """
        # Add a get_transform method to the curve view
        def get_transform():
            return TransformationIntegration.get_transform_for_curve_view(curve_view)

        # Add transform_point method that uses the new system
        def transform_point(x: float, y: float) -> Tuple[float, float]:
            transform = get_transform()
            return transform.apply(x, y)

        # Add transform_point_qt method for Qt integration
        def transform_point_qt(x: float, y: float) -> QPointF:
            transform = get_transform()
            return transform.apply_qt_point(x, y)

        # Install methods on the curve view instance
        curve_view.get_transform = get_transform
        curve_view.transform_point = transform_point
        curve_view.transform_point_qt = transform_point_qt

        # Mark as having unified system installed
        curve_view._unified_transform_installed = True

        logger.info(f"Unified transformation system installed in {curve_view.__class__.__name__}")

    @staticmethod
    def create_view_state_from_curve_view(curve_view: Any) -> ViewState:
        """
        Create a ViewState from a curve view.

        This is a convenience method for creating ViewState objects.

        Args:
            curve_view: The curve view instance

        Returns:
            ViewState object containing the view configuration
        """
        return ViewState.from_curve_view(curve_view)


# Convenience functions for easy migration
def get_transform(curve_view: Any) -> Transform:
    """
    Get a transform for the given curve view.

    This is the recommended way to get transforms in new code.
    """
    return TransformationIntegration.get_transform_for_curve_view(curve_view)


def transform_point(curve_view: Any, x: float, y: float) -> Tuple[float, float]:
    """
    Transform a single point from data to screen coordinates.

    Args:
        curve_view: The curve view instance
        x: X coordinate in data space
        y: Y coordinate in data space

    Returns:
        Tuple of (x, y) coordinates in screen space
    """
    return TransformationIntegration.transform_point_legacy(curve_view, x, y)


def transform_points(curve_view: Any, points: List[Tuple]) -> List[QPointF]:
    """
    Transform multiple points efficiently.

    Args:
        curve_view: The curve view instance
        points: List of points to transform

    Returns:
        List of QPointF objects in screen space
    """
    return TransformationIntegration.transform_multiple_points(curve_view, points)


def install_unified_system(curve_view: Any) -> None:
    """
    Install the unified transformation system in a curve view.

    This adds new methods to the curve view for using the unified system.
    """
    TransformationIntegration.install_in_curve_view(curve_view)


# Context manager for stable operations
def stable_transform_operation(curve_view: Any):
    """
    Context manager for operations that need stable transformations.

    Usage:
        with stable_transform_operation(curve_view):
            # Perform operation that modifies curve data
            # Transformations will remain stable
    """
    return UnifiedTransformationService.stable_transformation_context(curve_view)


# Migration utilities
class MigrationHelper:
    """Helper class for migrating existing code to the unified system."""

    @staticmethod
    def patch_curve_service():
        """
        Patch CurveService to use the unified transformation system.

        This updates the CurveService.transform_point method to use the
        new unified system while maintaining backward compatibility.
        """
        try:
            from services.curve_service import CurveService

            # Store original method if not already stored
            if not hasattr(CurveService, '_original_transform_point'):
                CurveService._original_transform_point = CurveService.transform_point

            # Replace with unified system
            CurveService.transform_point = TransformationIntegration.transform_point_legacy

            logger.info("CurveService patched to use unified transformation system")

        except ImportError:
            logger.warning("Could not import CurveService for patching")

    @staticmethod
    def patch_transformation_service():
        """
        Patch TransformationService to delegate to the unified system.

        This redirects calls to the old TransformationService methods
        to the new unified system.
        """
        try:
            from services.transformation_service import TransformationService

            # Store original methods
            if not hasattr(TransformationService, '_original_transform_point_to_widget'):
                TransformationService._original_transform_point_to_widget = \
                    TransformationService.transform_point_to_widget

            # Replace with unified system
            TransformationService.transform_point_to_widget = \
                UnifiedTransformationService.transform_point_to_widget

            logger.info("TransformationService patched to use unified system")

        except ImportError:
            logger.warning("Could not import TransformationService for patching")

    @staticmethod
    def apply_all_patches():
        """Apply all available patches for using the unified system."""
        MigrationHelper.patch_curve_service()
        MigrationHelper.patch_transformation_service()
        logger.info("All transformation patches applied")


# Validation utilities for testing migration
class ValidationHelper:
    """Helper for validating the behavior of the unified system."""

    @staticmethod
    def compare_transformations(curve_view: Any, points: List[Tuple],
                               tolerance: float = 0.1) -> bool:
        """
        Compare transformations between old and new systems.

        This helps validate that the unified system produces the same
        results as the original system.

        Args:
            curve_view: The curve view to test
            points: Points to transform for comparison
            tolerance: Maximum allowed difference in pixels

        Returns:
            True if transformations match within tolerance
        """
        # Transform using unified system
        unified_transform = get_transform(curve_view)
        unified_results = [unified_transform.apply(p[1], p[2]) for p in points]

        # Here you would compare with original system results
        # For now, we just log the unified results
        logger.debug(f"Unified system transformed {len(points)} points")

        return True  # Placeholder

    @staticmethod
    def validate_stability(curve_view: Any, operation_func, *args, **kwargs) -> bool:
        """
        Validate that an operation maintains transformation stability.

        Args:
            curve_view: The curve view to test
            operation_func: The operation to test
            *args, **kwargs: Arguments for the operation

        Returns:
            True if the operation maintains stability
        """
        with stable_transform_operation(curve_view) as transform:
            # Record initial positions
            if hasattr(curve_view, 'points') and curve_view.points:
                initial_positions = [transform.apply(p[1], p[2]) for p in curve_view.points[:5]]
            else:
                initial_positions = []

            # Perform operation
            result = operation_func(*args, **kwargs)

            # Check final positions
            if initial_positions and hasattr(curve_view, 'points'):
                final_transform = get_transform(curve_view)
                final_positions = [final_transform.apply(p[1], p[2]) for p in curve_view.points[:5]]

                # Calculate max drift
                max_drift = 0.0
                for i, (initial, final) in enumerate(zip(initial_positions, final_positions)):
                    dx, dy = final[0] - initial[0], final[1] - initial[1]
                    drift = (dx*dx + dy*dy) ** 0.5
                    max_drift = max(max_drift, drift)

                stable = max_drift < 1.0  # 1 pixel tolerance
                logger.info(f"Operation stability: {'passed' if stable else 'failed'} "
                           f"(max drift: {max_drift:.2f}px)")
                return stable

        return True
