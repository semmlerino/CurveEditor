#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main curve rendering orchestrator for CurveView.

This module contains the CurveRenderer class that orchestrates all rendering
components and replaces the monolithic paintEvent method.
"""

from typing import TYPE_CHECKING

from PySide6.QtGui import QPainter, QColor, QPen, QPaintEvent
from PySide6.QtCore import QTimer

from ui_scaling import UIScaling
from services.logging_service import LoggingService
from services.unified_transformation_service import UnifiedTransformationService

from .background_renderer import BackgroundRenderer
from .point_renderer import PointRenderer
from .info_renderer import InfoRenderer

if TYPE_CHECKING:
    from curve_view import CurveView

logger = LoggingService.get_logger("curve_renderer")


class CurveRenderer:
    """
    Main rendering orchestrator for CurveView.
    
    This class coordinates all specialized rendering components and replaces
    the monolithic paintEvent method with a clean, composable rendering pipeline.
    """
    
    def __init__(self) -> None:
        """Initialize the renderer with all specialized rendering components."""
        self.background_renderer = BackgroundRenderer()
        self.point_renderer = PointRenderer()
        self.info_renderer = InfoRenderer()
    
    def render(self, painter: QPainter, event: QPaintEvent, curve_view: 'CurveView') -> None:
        """
        Main rendering method that orchestrates all rendering components.
        
        Args:
            painter: QPainter instance for drawing
            event: Paint event that triggered the rendering
            curve_view: CurveView instance providing context and data
        """
        # Log current view state for debugging
        logger.debug("Paint event - View state: Zoom=%.2f, OffsetX=%d, OffsetY=%d, ManualX=%d, ManualY=%d",
                    curve_view.zoom_factor, curve_view.offset_x, curve_view.offset_y, 
                    curve_view.x_offset, curve_view.y_offset)
        
        # Handle initial fit after widget is properly sized
        self._handle_initial_fit(curve_view)
        
        # Configure painter
        self._setup_painter(painter, curve_view)
        
        # Check if we need to show empty state
        if not curve_view.points and not curve_view.background_image:
            # Draw empty state UI
            curve_view._draw_empty_state(painter)
            return
        
        # Create stable transform for consistent coordinate mapping
        transform = UnifiedTransformationService.from_curve_view(curve_view)
        
        # Log transform parameters for debugging
        self._log_transform_parameters(transform)
        
        # Render all components in order
        self.background_renderer.render_background(painter, transform, curve_view)
        self.point_renderer.render_points(painter, transform, curve_view)
        self.info_renderer.render_info(painter, curve_view)
    
    def _handle_initial_fit(self, curve_view: 'CurveView') -> None:
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
    
    def _setup_painter(self, painter: QPainter, curve_view: 'CurveView') -> None:
        """
        Configure painter settings and draw background.
        
        Args:
            painter: QPainter instance to configure
            curve_view: CurveView instance providing context
        """
        # Enable antialiasing for smooth rendering
        painter.setRenderHint(QPainter.Antialiasing)  # type: ignore[attr-defined]

        # Fill background with theme-aware color
        bg_color = UIScaling.get_color('bg_primary')
        painter.fillRect(curve_view.rect(), QColor(bg_color))
        
        # Draw focus indicator if widget has focus
        if curve_view.hasFocus():
            focus_color = UIScaling.get_color('border_focus')
            painter.setPen(QPen(QColor(focus_color), 2))
            painter.drawRect(curve_view.rect().adjusted(1, 1, -1, -1))
    
    def _log_transform_parameters(self, transform) -> None:
        """
        Log transform parameters for debugging.
        
        Args:
            transform: Transform object to log parameters for
        """
        transform_params = transform.get_parameters()
        logger.debug(f"Using stable transform: scale={transform_params['scale']:.4f}, "
                    f"center=({transform_params['center_offset_x']:.1f}, {transform_params['center_offset_y']:.1f}), "
                    f"pan=({transform_params['pan_offset_x']:.1f}, {transform_params['pan_offset_y']:.1f}), "
                    f"manual=({transform_params['manual_offset_x']:.1f}, {transform_params['manual_offset_y']:.1f}), "
                    f"flip_y={transform_params['flip_y']}")