"""
Transform Stabilizer Module for CurveEditor.

This module provides utilities for maintaining stable coordinate transformations
during operations that modify curve data, preventing issues like curve shifting
during smoothing operations.
"""

from typing import Dict, List, Tuple, Any, Optional, Callable
from PySide6.QtCore import QPointF, QTimer

from services.view_state import ViewState
from services.transform import Transform
from services.transformation_service import TransformationService
from services.transformation_shim import install
from services.logging_service import LoggingService

# Configure logger for this module
logger = LoggingService.get_logger("transform_stabilizer")

class TransformStabilizer:
    """
    Utility class to maintain stable coordinate transformations during operations.

    This class helps prevent issues like curve shifting when operations like
    smoothing are applied to curve data.
    """

    @staticmethod
    def stabilize_operation(curve_view: Any,
                           operation_func: Callable,
                           *args,
                           **kwargs) -> Any:
        """
        Execute an operation with stable transformation.

        This method ensures that coordinate transformations remain stable during
        an operation that modifies curve data, preventing unexpected shifts.

        Args:
            curve_view: The curve view instance
            operation_func: The function to execute
            *args: Arguments to pass to the operation function
            **kwargs: Keyword arguments to pass to the operation function

        Returns:
            The result of the operation function
        """
        # 1. Ensure transform system is installed
        install(curve_view)
        logger.info("Transform stabilizer activated for operation")

        # 2. Create view state and stable transform BEFORE operation
        before_state = ViewState.from_curve_view(curve_view)
        stable_transform = TransformationService.calculate_transform(before_state)

        # Log transform parameters
        transform_params = stable_transform.get_parameters()
        logger.info(f"Stable transform parameters: scale={transform_params['scale']:.4f}, "
                   f"center=({transform_params['center_offset'][0]:.1f}, {transform_params['center_offset'][1]:.1f})")

        # 3. Cache original view properties for restoration
        original_zoom = getattr(curve_view, 'zoom_factor', 1.0)
        original_offset_x = getattr(curve_view, 'offset_x', 0)
        original_offset_y = getattr(curve_view, 'offset_y', 0)
        original_scale_to_image = getattr(curve_view, 'scale_to_image', True)
        original_auto_center = getattr(curve_view.main_window, 'auto_center_enabled', False) if hasattr(curve_view, 'main_window') else False

        # Temporarily disable auto-center
        if hasattr(curve_view, 'main_window') and hasattr(curve_view.main_window, 'auto_center_enabled'):
            curve_view.main_window.auto_center_enabled = False

        # 4. Execute the operation function
        try:
            result = operation_func(*args, **kwargs)
            logger.info("Operation completed successfully")
            return result
        finally:
            # 5. Restore original view properties
            curve_view.zoom_factor = original_zoom
            curve_view.offset_x = original_offset_x
            curve_view.offset_y = original_offset_y
            curve_view.scale_to_image = original_scale_to_image

            # 6. Restore auto-center
            if hasattr(curve_view, 'main_window') and hasattr(curve_view.main_window, 'auto_center_enabled'):
                curve_view.main_window.auto_center_enabled = original_auto_center

            # 7. Use a timer to ensure view is updated with stable transform
            QTimer.singleShot(10, lambda: TransformStabilizer._update_view(curve_view))

    @staticmethod
    def _update_view(curve_view: Any) -> None:
        """
        Update the curve view with a small delay.

        This helps ensure all state changes are processed before rendering.

        Args:
            curve_view: The curve view instance
        """
        # Trigger a repaint
        curve_view.update()
        logger.info("View updated with stable transform (delayed)")

    @staticmethod
    def track_reference_points(curve_data: List[Any], transform: Transform) -> Dict[int, QPointF]:
        """
        Track reference points for later comparison.

        Args:
            curve_data: The curve data points
            transform: The transform to apply

        Returns:
            Dict mapping point indices to screen positions
        """
        if not curve_data:
            return {}

        reference_points = {}

        # Track key points (first, middle, last)
        indices = [0]
        if len(curve_data) > 2:
            indices.append(len(curve_data) // 2)
        if len(curve_data) > 1:
            indices.append(len(curve_data) - 1)

        for idx in indices:
            if idx < len(curve_data):
                point = curve_data[idx]
                screen_pos = QPointF(*transform.apply(point[1], point[2]))
                reference_points[idx] = screen_pos
                logger.debug(f"Tracking reference point {idx} at ({point[1]:.2f}, {point[2]:.2f}) -> screen ({screen_pos.x():.2f}, {screen_pos.y():.2f})")

        return reference_points

    @staticmethod
    def verify_reference_points(curve_data: List[Any],
                              reference_points: Dict[int, QPointF],
                              transform: Transform,
                              threshold: float = 1.0) -> bool:
        """
        Verify that reference points haven't shifted significantly.

        Args:
            curve_data: The current curve data points
            reference_points: Dict of reference points from track_reference_points
            transform: The transform to apply
            threshold: Max allowed shift in pixels

        Returns:
            True if all points are within threshold, False otherwise
        """
        if not reference_points or not curve_data:
            return True

        all_within_threshold = True

        for idx, original_pos in reference_points.items():
            if idx < len(curve_data):
                point = curve_data[idx]
                current_pos = QPointF(*transform.apply(point[1], point[2]))

                # Calculate shift distance
                dx = current_pos.x() - original_pos.x()
                dy = current_pos.y() - original_pos.y()
                distance = (dx*dx + dy*dy) ** 0.5

                logger.debug(f"Point {idx} shifted by {distance:.2f} pixels")

                if distance > threshold:
                    logger.warning(f"Point {idx} shifted significantly by {distance:.2f} pixels (threshold: {threshold})")
                    all_within_threshold = False

        return all_within_threshold
