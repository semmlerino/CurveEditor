"""
Enhanced CurveView Integration for Unified Transformation System

This module demonstrates how to integrate the new unified transformation system
with CurveView components. It provides examples of best practices and shows
how existing paintEvent methods can be updated to use the consolidated system.
"""

from typing import List, Any, Optional, Dict, Set
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor
from PySide6.QtWidgets import QWidget

from services.unified_transformation_service import UnifiedTransformationService
from services.logging_service import LoggingService

# Configure logger
logger = LoggingService.get_logger("enhanced_curve_view")


class UnifiedTransformCurveView(QWidget):
    """
    Example CurveView implementation using the unified transformation system.

    This class demonstrates best practices for integrating the unified
    transformation system with Qt widgets and paintEvent handling.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # Curve data and view state
        self.points: List[Any] = []
        self.selected_points: Set[int] = set()
        self.selected_point_idx: int = -1

        # View configuration
        self.zoom_factor: float = 1.0
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0
        self.flip_y_axis: bool = False
        self.scale_to_image: bool = True
        self.x_offset: float = 0.0  # Manual X offset
        self.y_offset: float = 0.0  # Manual Y offset

        # Image properties
        self.background_image = None
        self.image_width: int = 1920
        self.image_height: int = 1080

        # Unified transformation system is automatically available
        logger.info("Enhanced CurveView initialized with unified transformation system")

    def paintEvent(self, event):
        """
        Enhanced paintEvent using the unified transformation system.

        This demonstrates the optimal way to handle painting with the new system:
        1. Get a single transform for the entire paint operation
        2. Use it consistently for all elements
        3. Cache transformed points for efficiency
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        try:
            # Get the current transform - this is the key improvement
            transform = UnifiedTransformationService.from_curve_view(self)

            # Draw background image if available
            if self.background_image:
                self._draw_background_image(painter, transform)

            # Draw the curve using the transform
            if self.points:
                self._draw_curve(painter, transform)
                self._draw_selected_points(painter, transform)

            # Draw any additional overlays
            self._draw_overlays(painter, transform)

        except Exception as e:
            logger.error(f"Error in paintEvent: {e}")
            # Fallback to basic rendering
            painter.fillRect(self.rect(), QColor(50, 50, 50))

        finally:
            painter.end()

    def _draw_background_image(self, painter: QPainter, transform: Any) -> None:
        """Draw the background image using the unified transform."""
        if not self.background_image:
            return

        # Calculate image position using the transform
        img_x, img_y = transform.apply_for_image_position()

        # Calculate scaled image size
        scale = transform.get_parameters()['scale']

        # Apply image scaling if enabled
        params = transform.get_parameters()
        if params['scale_to_image']:
            image_scale_x = params['image_scale_x']
            image_scale_y = params['image_scale_y']
            scaled_width = self.background_image.width() * scale * image_scale_x
            scaled_height = self.background_image.height() * scale * image_scale_y
        else:
            scaled_width = self.background_image.width() * scale
            scaled_height = self.background_image.height() * scale

        # Draw the image
        target_rect = QRectF(img_x, img_y, scaled_width, scaled_height)
        source_rect = QRectF(self.background_image.rect())
        painter.drawImage(target_rect, self.background_image, source_rect)

        logger.debug(f"Background image drawn at ({img_x:.1f}, {img_y:.1f}) "
                    f"with size ({scaled_width:.1f}, {scaled_height:.1f})")

    def _draw_curve(self, painter: QPainter, transform: Any) -> None:
        """Draw the curve using efficient batch transformation."""
        if not self.points:
            return

        # Transform all points at once for efficiency
        transformed_points = UnifiedTransformationService.transform_points_qt(
            transform, self.points
        )

        # Set up curve appearance
        curve_pen = QPen(QColor(100, 150, 255), 2)
        painter.setPen(curve_pen)

        # Draw curve segments
        for i in range(len(transformed_points) - 1):
            painter.drawLine(transformed_points[i], transformed_points[i + 1])

        # Draw points
        point_pen = QPen(QColor(255, 255, 255), 1)
        point_brush = QBrush(QColor(100, 150, 255))
        painter.setPen(point_pen)
        painter.setBrush(point_brush)

        for point in transformed_points:
            painter.drawEllipse(point, 3, 3)

        logger.debug(f"Drew curve with {len(transformed_points)} points")

    def _draw_selected_points(self, painter: QPainter, transform: Any) -> None:
        """Draw selected points with highlighting."""
        if not self.selected_points or not self.points:
            return

        # Set up selection appearance
        selection_pen = QPen(QColor(255, 255, 0), 2)
        selection_brush = QBrush(QColor(255, 255, 0, 128))
        painter.setPen(selection_pen)
        painter.setBrush(selection_brush)

        # Transform and draw selected points
        for idx in self.selected_points:
            if 0 <= idx < len(self.points):
                point = self.points[idx]
                screen_pos = transform.apply_qt_point(point[1], point[2])
                painter.drawEllipse(screen_pos, 5, 5)

        # Highlight currently selected point
        if 0 <= self.selected_point_idx < len(self.points):
            point = self.points[self.selected_point_idx]
            screen_pos = transform.apply_qt_point(point[1], point[2])

            # Draw larger highlight
            highlight_pen = QPen(QColor(255, 0, 0), 3)
            painter.setPen(highlight_pen)
            painter.setBrush(QBrush())
            painter.drawEllipse(screen_pos, 8, 8)

    def _draw_overlays(self, painter: QPainter, transform: Any) -> None:
        """Draw any additional overlays or UI elements."""
        # Example: Draw coordinate axes
        params = transform.get_parameters()

        # Draw origin if visible
        origin_screen = transform.apply_qt_point(0, 0)
        if self.rect().contains(origin_screen.toPoint()):
            origin_pen = QPen(QColor(255, 255, 255, 128), 1)
            painter.setPen(origin_pen)

            # Draw small cross at origin
            cross_size = 10
            painter.drawLine(
                origin_screen.x() - cross_size, origin_screen.y(),
                origin_screen.x() + cross_size, origin_screen.y()
            )
            painter.drawLine(
                origin_screen.x(), origin_screen.y() - cross_size,
                origin_screen.x(), origin_screen.y() + cross_size
            )

    def mousePressEvent(self, event: Any) -> None:
        """Handle mouse press events with coordinate transformation."""
        if not self.points:
            return

        # Get the transform for coordinate conversion
        transform = UnifiedTransformationService.from_curve_view(self)

        # Convert mouse position to data coordinates
        screen_pos = (event.position().x(), event.position().y())
        data_pos = transform.apply_inverse(screen_pos[0], screen_pos[1])

        # Find the closest point
        closest_idx = -1
        min_distance = float('inf')

        for i, point in enumerate(self.points):
            # Calculate distance in screen space for consistent selection
            point_screen = transform.apply(point[1], point[2])
            dx = point_screen[0] - screen_pos[0]
            dy = point_screen[1] - screen_pos[1]
            distance = (dx*dx + dy*dy) ** 0.5

            if distance < min_distance and distance < 10:  # 10 pixel selection radius
                min_distance = distance
                closest_idx = i

        # Update selection
        if closest_idx >= 0:
            self.selected_point_idx = closest_idx
            self.selected_points = {closest_idx}
            self.update()

            logger.debug(f"Selected point {closest_idx} at data position ({data_pos[0]:.2f}, {data_pos[1]:.2f})")

    def smooth_curve_with_stability(self, smoothing_factor: float = 0.5) -> None:
        """
        Example of performing a curve operation with transformation stability.

        This demonstrates how to use the stable transformation context for
        operations that modify the curve data.
        """
        if not self.points:
            return

        logger.info(f"Starting curve smoothing with factor {smoothing_factor}")

        with UnifiedTransformationService.stable_transformation_context(self) as stable_transform:
            # Record reference points for verification
            reference_indices = [0, len(self.points) // 2, len(self.points) - 1]
            reference_positions = {}

            for ref_idx in reference_indices:
                if 0 <= ref_idx < len(self.points):
                    ref_point: Any = self.points[ref_idx]
                    screen_pos: tuple[float, float] = stable_transform.apply(ref_point[1], ref_point[2])
                    reference_positions[ref_idx] = screen_pos

            # Perform smoothing operation
            self._apply_smoothing(smoothing_factor)

            # Verify that reference points haven't moved significantly
            max_drift = 0.0
            for drift_idx in list(reference_positions.keys()):  # type: ignore
                original_pos = reference_positions[drift_idx]
                if 0 <= drift_idx < len(self.points):
                    drift_point: Any = self.points[drift_idx]
                    new_pos: tuple[float, float] = stable_transform.apply(drift_point[1], drift_point[2])
                    dx: float = float(new_pos[0] - original_pos[0])
                    dy: float = float(new_pos[1] - original_pos[1])
                    drift: float = float((dx*dx + dy*dy) ** 0.5)
                    max_drift: float = max(float(max_drift), float(drift))

            if max_drift > 1.0:
                logger.warning(f"Detected transformation drift: {max_drift:.2f} pixels")
            else:
                logger.info("Curve smoothing completed with stable transformations")

        # Update the view
        self.update()

    def _apply_smoothing(self, factor: float) -> None:
        """Apply smoothing to the curve data (placeholder implementation)."""
        if len(self.points) < 3:
            return

        # Simple smoothing: average each point with its neighbors
        smoothed_points: list[Any] = []

        for i, point in enumerate(self.points):
            if i == 0 or i == len(self.points) - 1:
                # Keep endpoints unchanged
                smoothed_points.append(point)
            else:
                # Average with neighbors
                prev_point = self.points[i - 1]
                next_point = self.points[i + 1]

                # Weighted average
                new_x = (prev_point[1] + point[1] * (1/factor - 2) + next_point[1]) / (1/factor)
                new_y = (prev_point[2] + point[2] * (1/factor - 2) + next_point[2]) / (1/factor)

                # Preserve other point data
                smoothed_point = (point[0], new_x, new_y) + point[3:]
                smoothed_points.append(smoothed_point)

        self.points = smoothed_points

    def set_curve_data(self, points: List[Any]) -> None:
        """Set new curve data and update the view."""
        self.points = points
        self.selected_points.clear()
        self.selected_point_idx = -1
        self.update()

        logger.info(f"Curve data updated with {len(points)} points")

    def get_transform_info(self) -> Dict[str, Any]:
        """Get information about the current transform for debugging."""
        transform = UnifiedTransformationService.from_curve_view(self)
        params = transform.get_parameters()

        return {
            'transform_parameters': params,
            'cache_stats': UnifiedTransformationService.get_cache_stats(),
            'point_count': len(self.points),
            'selected_count': len(self.selected_points)
        }


# Factory function for creating enhanced curve views
def create_enhanced_curve_view(parent: Optional[QWidget] = None,
                              initial_points: Optional[List[Any]] = None) -> UnifiedTransformCurveView:
    """
    Factory function for creating enhanced curve views with the unified system.

    Args:
        parent: Parent widget
        initial_points: Optional initial curve data

    Returns:
        Configured UnifiedTransformCurveView instance
    """
    view = UnifiedTransformCurveView(parent)

    if initial_points:
        view.set_curve_data(initial_points)

    logger.info("Created enhanced curve view with unified transformation system")
    return view


# Example of migrating an existing paintEvent method
def migrate_paint_event_example() -> None:
    """
    Example showing how to migrate an existing paintEvent to use the unified system.

    OLD APPROACH:
    def paintEvent(self, event):
        painter = QPainter(self)

        # Recalculate transform parameters for each element
        for point in self.points:
            tx, ty = some_transform_function(point[1], point[2])
            painter.drawEllipse(tx, ty, 3, 3)

    NEW APPROACH:
    def paintEvent(self, event):
        painter = QPainter(self)

        # Get transform once
        transform = UnifiedTransformationService.from_curve_view(self)

        # Transform all points efficiently
        transformed_points = UnifiedTransformationService.transform_points_qt(
            transform, self.points
        )

        # Draw using transformed points
        for point in transformed_points:
            painter.drawEllipse(point, 3, 3)
    """
    pass


# Utility functions for integration
def convert_legacy_curve_view(legacy_view: Any, enhanced_parent: Optional[QWidget] = None) -> UnifiedTransformCurveView:
    """
    Convert a legacy curve view to use the enhanced unified system.

    Args:
        legacy_view: Existing curve view instance
        enhanced_parent: Parent for the new enhanced view

    Returns:
        New UnifiedTransformCurveView with migrated data
    """
    enhanced_view = UnifiedTransformCurveView(enhanced_parent)

    # Migrate configuration
    if hasattr(legacy_view, 'zoom_factor'):
        enhanced_view.zoom_factor = legacy_view.zoom_factor
    if hasattr(legacy_view, 'offset_x'):
        enhanced_view.offset_x = legacy_view.offset_x
    if hasattr(legacy_view, 'offset_y'):
        enhanced_view.offset_y = legacy_view.offset_y
    if hasattr(legacy_view, 'points'):
        enhanced_view.set_curve_data(legacy_view.points)

    # Migrate additional properties
    property_mappings = {
        'flip_y_axis': 'flip_y_axis',
        'scale_to_image': 'scale_to_image',
        'background_image': 'background_image',
        'image_width': 'image_width',
        'image_height': 'image_height',
        'selected_points': 'selected_points',
        'selected_point_idx': 'selected_point_idx'
    }

    for legacy_prop, enhanced_prop in property_mappings.items():
        if hasattr(legacy_view, legacy_prop):
            setattr(enhanced_view, enhanced_prop, getattr(legacy_view, legacy_prop))

    logger.info("Migrated legacy curve view to enhanced unified system")
    return enhanced_view
