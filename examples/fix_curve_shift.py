"""
Example script demonstrating how to use the new transformation system
to fix the curve shifting issue during smoothing operations.

This script shows how to:
1. Install the transformation system
2. Apply it during smooth operations
3. Ensure consistent coordinate transformations

Run this script as a reference when integrating the transformation system
into the main application code.
"""

import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PySide6.QtCore import QPointF, QTimer
from main_window import MainWindow
from curve_view import CurveView
from services.view_state import ViewState
from services.unified_transform import Transform
from services.unified_transformation_service import UnifiedTransformationService
from services.unified_transformation_shim import install, transform_points
from services.logging_service import LoggingService

# Set up logging
logger = LoggingService.get_logger("fix_curve_shift")
logger.setLevel(logging.INFO)


def apply_smooth_with_stable_transform(main_window: 'MainWindow') -> None:
    """
    Apply smoothing while maintaining stable coordinate transformations.

    This is a template for modifying the apply_smooth_operation method in
    main_window.py to use the new transformation system.

    Args:
        main_window: The MainWindow instance
    """
    curve_view = main_window.curve_view

    # Ensure transformation system is installed
    install(curve_view)

    # 1. BEFORE ANY CHANGES: Store the view state and create a transform
    logger.info("Creating stable transform before smoothing operation")
    before_state = ViewState.from_curve_view(curve_view)
    stable_transform = UnifiedTransformationService.calculate_transform(before_state)

    # 2. Track positions of reference points before changes
    # This helps verify that points don't shift unexpectedly
    if main_window.curve_data and len(main_window.curve_data) > 0:
        reference_points = [0]  # Track the first point as a reference
        if len(main_window.curve_data) > 1:
            reference_points.append(len(main_window.curve_data) - 1)  # Also track the last point

        before_positions = {}
        for idx in reference_points:
            point = main_window.curve_data[idx]
            screen_pos = QPointF(*stable_transform.apply(point[1], point[2]))
            before_positions[idx] = screen_pos
            logger.info(f"Reference point {idx} at ({point[1]:.2f}, {point[2]:.2f}) -> screen ({screen_pos.x():.2f}, {screen_pos.y():.2f})")

    # 3. Call the actual smoothing logic
    # This is where you would call your existing smooth dialog or function
    # modified_data = DialogService.show_smooth_dialog(...)
    # main_window.curve_data = modified_data

    # 4. AFTER CHANGES: Update the view while using the same transform
    logger.info("Updating view with stable transform after smoothing")

    # 5. Set points WITH preserve_view=True and using stable transform
    main_window.curve_view.setPoints(
        main_window.curve_data,
        main_window.image_width,
        main_window.image_height,
        preserve_view=True
    )

    # 6. Verify reference points after update
    if main_window.curve_data and len(main_window.curve_data) > 0 and 'before_positions' in locals():
        for idx in reference_points:
            if idx < len(main_window.curve_data):
                point = main_window.curve_data[idx]
                screen_pos = QPointF(*stable_transform.apply(point[1], point[2]))
                logger.info(f"After: Reference point {idx} at ({point[1]:.2f}, {point[2]:.2f}) -> screen ({screen_pos.x():.2f}, {screen_pos.y():.2f})")

                # Check if position changed significantly
                if idx in before_positions:
                    before_pos = before_positions[idx]
                    dx = screen_pos.x() - before_pos.x()
                    dy = screen_pos.y() - before_pos.y()
                    distance = (dx*dx + dy*dy) ** 0.5
                    logger.info(f"Point {idx} moved by {distance:.2f} pixels on screen")

                    # If it changed significantly, log a warning
                    if distance > 1.0:  # 1-pixel threshold
                        logger.warning(f"Point {idx} shifted significantly: {distance:.2f} pixels")

    # 7. Use QTimer to ensure a clean update
    def delayed_update():
        # Update with same transform to maintain consistency
        main_window.curve_view.update()
        logger.info("View updated with delayed timer")

    # 10ms delay to ensure all state changes are processed
    QTimer.singleShot(10, delayed_update)


def fix_paintEvent_with_stable_transform(curve_view: 'CurveView') -> None:
    """
    Example of how to modify the paintEvent method to use the transformation system.

    This is a template for refactoring the paintEvent method in curve_view.py
    to use the new transformation system.

    Args:
        curve_view: The CurveView instance
    """
    # Create a consistent transform for all painting operations
    view_state = ViewState.from_curve_view(curve_view)
    transform = UnifiedTransformationService.calculate_transform(view_state)

    logger.info(f"Using transform with scale={transform.get_parameters()['scale']:.4f}")

    # Example of how to use the transform for point transformations
    if curve_view.points:
        # Transform all points in one operation for efficiency
        transformed_points = transform_points(curve_view, curve_view.points)

        # Use transformed points for drawing
        for i, point in enumerate(curve_view.points):
            tx, ty = transformed_points[i].x(), transformed_points[i].y()
            # Draw point at (tx, ty)

    # Example of how to use the transform for image positioning
    if curve_view.background_image:
        # Get parameters from transform
        params = transform.get_parameters()
        scale = params['scale']
        center_offset_x, center_offset_y = params['center_offset']

        # Calculate image position and size
        img_width = curve_view.background_image.width() * scale
        img_height = curve_view.background_image.height() * scale
        img_x = center_offset_x
        img_y = center_offset_y

        # Draw image at (img_x, img_y) with size (img_width, img_height)


if __name__ == "__main__":
    logger.info("This is an example script demonstrating the transformation system.")
    logger.info("Import and call the functions from your application code.")
    logger.info("Refer to the docs/coordinate_transformation_refactoring_plan.md for more details.")
