#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Info rendering component for CurveView.

This module contains the InfoRenderer class responsible for rendering
information overlays including view stats, image info, and debug information.
"""

import os
from typing import Set, TYPE_CHECKING

from PySide6.QtGui import QPainter, QColor, QPen

from ui_scaling import UIScaling
from services.logging_service import LoggingService
from services.image_service import ImageService

if TYPE_CHECKING:
    from core.protocols import PointsList

logger = LoggingService.get_logger("info_renderer")


class InfoRenderer:
    """
    Handles information overlay rendering for CurveView.
    
    This class is responsible for rendering text overlays including view statistics,
    image information, and debug information. Maintains identical functionality
    to the original paintEvent info rendering logic.
    """
    
    def render_info(self, painter: QPainter, curve_view: 'CurveViewProtocol') -> None:
        """
        Render all information overlays.
        
        Args:
            painter: QPainter instance for drawing
            curve_view: CurveView instance providing context and data
        """
        # Set up font and color for info text
        info_font = UIScaling.get_font("small", "regular", "monospace")
        painter.setFont(info_font)
        info_color = UIScaling.get_color('text_secondary')
        painter.setPen(QPen(QColor(info_color), 1))
        
        # Render view information
        self._render_view_info(painter, curve_view)
        
        # Render image information if available
        if curve_view.background_image:
            self._render_image_info(painter, curve_view)
            
        # Render debug information if in debug mode
        if curve_view.debug_mode:
            self._render_debug_info(painter, curve_view)
    
    def _render_view_info(self, painter: QPainter, curve_view: 'CurveViewProtocol') -> None:
        """
        Render view statistics and selected point information.
        
        Args:
            painter: QPainter instance for drawing
            curve_view: CurveView instance providing context and data
        """
        # Show current view info
        info_text = f"Zoom: {curve_view.zoom_factor:.2f}x | Points: {len(curve_view.points)}"
        
        # Add selected point type information
        if hasattr(curve_view, 'selected_points') and curve_view.selected_points:
            # Gather types of all selected points
            selected_types: Set[str] = set()
            for i in curve_view.selected_points:
                if 0 <= i < len(curve_view.points):
                    pt = curve_view.points[i]
                    if len(pt) >= 4:
                        selected_types.add(str(pt[3]))
                    else:
                        pass  # No type info for this point
            if selected_types:
                types_str = ', '.join(sorted(selected_types))
                info_text += f" | Type(s): {types_str}"
                
        painter.drawText(10, 20, info_text)
    
    def _render_image_info(self, painter: QPainter, curve_view: 'CurveViewProtocol') -> None:
        """
        Render image sequence information.
        
        Args:
            painter: QPainter instance for drawing
            curve_view: CurveView instance providing context and data
        """
        img_info = f"Image: {ImageService.get_current_image_index(curve_view) + 1}/{ImageService.get_image_count(curve_view)}"
        
        # Add filename if available
        if (ImageService.get_image_filenames(curve_view) and 
            ImageService.get_current_image_index(curve_view) >= 0):
            filename = os.path.basename(
                ImageService.get_image_filenames(curve_view)[ImageService.get_current_image_index(curve_view)]
            )
            img_info += f" - {filename}"
            
        painter.drawText(10, 40, img_info)
    
    def _render_debug_info(self, painter: QPainter, curve_view: 'CurveViewProtocol') -> None:
        """
        Render debug information and keyboard shortcuts.
        
        Args:
            painter: QPainter instance for drawing
            curve_view: CurveView instance providing context and data
        """
        # Main debug info line
        debug_info = f"Debug Mode: ON | Y-Flip: {'ON' if curve_view.flip_y_axis else 'OFF'} | Scale to Image: {'ON' if curve_view.scale_to_image else 'OFF'}"
        debug_info += f" | Track Dims: {curve_view.image_width}x{curve_view.image_height}"

        # Add image dimensions if available
        if curve_view.background_image:
            debug_info += f" | Image: {curve_view.background_image.width()}x{curve_view.background_image.height()}"

        painter.drawText(10, 60, debug_info)

        # Display keyboard shortcuts
        shortcuts = "Shortcuts: [R] Reset View, [Y] Toggle Y-Flip, [S] Toggle Scale-to-Image"
        shortcuts += " | Arrow keys + Shift: Adjust alignment"
        painter.drawText(10, 80, shortcuts)


# Protocol for type checking
try:
    from typing import Protocol
    from PySide6.QtGui import QPixmap
    
    class CurveViewProtocol(Protocol):
        points: 'PointsList'
        selected_points: Set[int]
        zoom_factor: float
        background_image: QPixmap
        debug_mode: bool
        flip_y_axis: bool
        scale_to_image: bool
        image_width: int
        image_height: int
        
except ImportError:
    # Fallback for older Python versions
    CurveViewProtocol = object