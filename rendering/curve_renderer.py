#!/usr/bin/env python

"""
Main curve rendering orchestrator for CurveView.

Architecture Overview:
This module implements the main rendering pipeline that replaced the original
316-line monolithic paintEvent method. The CurveRenderer class acts as an
orchestrator that coordinates four specialized rendering components:

1. BackgroundRenderer: Handles background image rendering with transformations
2. PointRenderer: Manages curve points, selection highlighting, and labels
3. InfoRenderer: Displays view statistics, image info, and debug information
4. CurveRenderer (this class): Orchestrates the pipeline and painter setup

The rendering pipeline follows this sequence:
- Initial fit handling for proper widget sizing
- Painter configuration (antialiasing, background, focus indicators)
- Empty state detection and rendering
- Stable coordinate transformation creation
- Sequential component rendering (background → points → info)

This architecture provides:
- Clear separation of concerns (Single Responsibility Principle)
- Improved testability through isolated components
- Better maintainability and extensibility
- Consistent coordinate transformations across all rendering
"""

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen

from services.logging_service import LoggingService
from services.transformation_service import TransformationService
from ui.ui_scaling import UIScaling

from .background_renderer import BackgroundRenderer
from .info_renderer import InfoRenderer
from .point_renderer import PointRenderer

if TYPE_CHECKING:
    from curve_view import CurveView

logger = LoggingService.get_logger("curve_renderer")


class CurveRenderer:
    """
    Main rendering orchestrator for CurveView.

    This class coordinates all specialized rendering components and replaces
    the monolithic paintEvent method with a clean, composable rendering pipeline.

    Public API:
        render(painter, event, curve_view): Main rendering entry point

    Usage Example:
        renderer = CurveRenderer()
        # In paintEvent:
        painter = QPainter(self)
        renderer.render(painter, event, self)

    Component Architecture:
        - BackgroundRenderer: Handles background image rendering
        - PointRenderer: Manages curve point visualization
        - InfoRenderer: Displays text overlays and statistics

    Thread Safety:
        This class is not thread-safe. Each CurveView should have its own
        CurveRenderer instance for concurrent usage.
    """

    def __init__(self) -> None:
        """
        Initialize the renderer with all specialized rendering components.

        Creates instances of all four rendering components:
        - BackgroundRenderer for image display
        - PointRenderer for curve point visualization
        - InfoRenderer for text overlays

        Returns:
            None

        Raises:
            ImportError: If required Qt modules are not available
        """
        self.background_renderer: BackgroundRenderer = BackgroundRenderer()
        self.point_renderer: PointRenderer = PointRenderer()
        self.info_renderer: InfoRenderer = InfoRenderer()

    def render(self, painter: QPainter, event: QPaintEvent, curve_view: "CurveView") -> None:
        """
        Main rendering method that orchestrates all rendering components.

        This method implements the complete rendering pipeline that replaced the
        original 316-line monolithic paintEvent. It coordinates all rendering
        components in the correct order to produce the final visualization.

        Rendering Sequence:
        1. Initial fit handling for proper widget sizing
        2. Painter configuration (antialiasing, background, focus)
        3. Empty state detection and rendering
        4. Stable coordinate transformation creation
        5. Background image rendering (if present)
        6. Curve point rendering with selection highlighting
        7. Information overlay rendering

        Args:
            painter (QPainter): Qt painter instance for drawing operations.
                Must be properly initialized and associated with a paint device.
            event (QPaintEvent): Paint event containing the update region.
                Used for optimization and dirty region handling.
            curve_view (CurveView): The CurveView instance providing:
                - Point data and selection state
                - Background image and display properties
                - Zoom, pan, and transformation parameters
                - UI state flags and debug settings

        Returns:
            None

        Raises:
            AttributeError: If curve_view is missing required protocol attributes
            RuntimeError: If coordinate transformation fails

        Example:
            def paintEvent(self, event: QPaintEvent) -> None:
                painter = QPainter(self)
                self._curve_renderer.render(painter, event, self)
                super().paintEvent(event)

        Performance Notes:
            - Uses stable transforms to avoid coordinate system drift
            - Implements early returns for empty states to optimize performance
            - Leverages Qt's built-in clipping for efficient dirty region updates
        """
        # Log current view state for debugging
        logger.debug(
            "Paint event - View state: Zoom=%.2f, OffsetX=%d, OffsetY=%d, ManualX=%d, ManualY=%d",
            curve_view.zoom_factor,
            curve_view.offset_x,
            curve_view.offset_y,
            curve_view.x_offset,
            curve_view.y_offset,
        )

        # Handle initial fit after widget is properly sized
        self._handle_initial_fit(curve_view)

        # Configure painter
        self._setup_painter(painter, curve_view)

        # Check if we need to show empty state - only show when no data of any kind is loaded
        has_curve_data = curve_view.points and len(curve_view.points) > 0
        has_image_data = curve_view.background_image is not None and not curve_view.background_image.isNull()

        if not has_curve_data and not has_image_data:
            # Draw empty state UI
            curve_view._draw_empty_state(painter)
            return

        # Create stable transform for consistent coordinate mapping
        transform = TransformationService.from_curve_view(curve_view)

        # Log transform parameters for debugging
        self._log_transform_parameters(transform)

        # Render all components in order
        self.background_renderer.render_background(painter, transform, curve_view)
        self.point_renderer.render_points(painter, transform, curve_view)
        self.info_renderer.render_info(painter, curve_view)

    def _handle_initial_fit(self, curve_view: "CurveView") -> None:
        """
        Handle initial fit to window after widget is properly sized.

        Args:
            curve_view: CurveView instance providing context
        """
        # Check if we need to do initial fit after widget is properly sized
        if curve_view._needs_initial_fit and curve_view.width() > 300 and curve_view.height() > 300:
            curve_view._needs_initial_fit = False
            curve_view._has_fitted = True
            # Use a timer to fit after this paint completes
            QTimer.singleShot(10, curve_view.fit_to_window)

    def _setup_painter(self, painter: QPainter, curve_view: "CurveView") -> None:
        """
        Configure painter settings and draw background.

        Args:
            painter: QPainter instance to configure
            curve_view: CurveView instance providing context
        """
        # Enable antialiasing for smooth rendering
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill background with theme-aware color
        bg_color = UIScaling.get_color("bg_primary")
        painter.fillRect(curve_view.rect(), QColor(bg_color))

        # Draw focus indicator if widget has focus
        if curve_view.hasFocus():
            focus_color = UIScaling.get_color("border_focus")
            painter.setPen(QPen(QColor(focus_color), 2))
            painter.drawRect(curve_view.rect().adjusted(1, 1, -1, -1))

    def _log_transform_parameters(self, transform: Any) -> None:
        """
        Log transform parameters for debugging.

        Args:
            transform: Transform object to log parameters for
        """
        transform_params = transform.get_parameters()
        logger.debug(
            f"Using stable transform: scale={transform_params['scale']:.4f}, "
            f"center=({transform_params['center_offset_x']:.1f}, {transform_params['center_offset_y']:.1f}), "
            f"pan=({transform_params['pan_offset_x']:.1f}, {transform_params['pan_offset_y']:.1f}), "
            f"manual=({transform_params['manual_offset_x']:.1f}, {transform_params['manual_offset_y']:.1f}), "
            f"flip_y={transform_params['flip_y']}"
        )
