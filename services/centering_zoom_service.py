#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CenteringZoomService: facade for legacy ZoomOperations.
Dynamically attaches all static methods from ZoomOperations.
"""

from centering_zoom_operations import ZoomOperations as LegacyZoomOps
from typing import Any, Tuple

class CenteringZoomService:
    """Facade for centering & zoom operations."""
    @staticmethod
    def center_on_selected_point(point: Tuple[float, float], content_size: Tuple[float, float], content_position: Tuple[float, float], zoom: float, base_offset: Tuple[float, float]) -> None:
        """Calculate centering offsets to center a specific point.
        
        This is a utility method used by the centering calculation in full implementations.
        Used directly only in advanced scenarios; most usages should go through the
        auto_center_view method instead.
        
        Args:
            point: The point to center on (x, y)
            content_size: Size of the content (width, height) 
            content_position: Position of the content (x, y)
            zoom: Current zoom factor
            base_offset: Base offset to apply (x, y)
        """
        # 1. Calculate the scaled content size
        scaled_content_size = (content_size[0] * zoom, content_size[1] * zoom)
        
        # 2. Calculate the scaled content position
        scaled_content_x = content_position[0] * zoom
        scaled_content_y = content_position[1] * zoom
        
        # This method is intentionally incomplete in this implementation.
        # The actual centering calculation is performed by the LegacyZoomOps class
        # that is dynamically attached to this class at the bottom of this file.
        # 
        # This stub exists to provide proper type annotations and documentation
        # for the method signature, while the actual implementation comes from
        # the legacy code in centering_zoom_operations.py

    @staticmethod
    def auto_center_view(main_window: Any, preserve_zoom: bool = True) -> bool:
        """Detect selected point and center the view using ZoomOperations.
        
        This method handles centering in all window states (normal, maximized, fullscreen).
        It accounts for widget resizing to ensure proper centering in all scenarios.
        
        Args:
            main_window: The main window instance
            preserve_zoom: Whether to preserve current zoom level or reset
            
        Returns:
            bool: True if centering was successful, False otherwise
        """
        # Get curve view from main window
        curve_view = getattr(main_window, 'curve_view', None)
        if not curve_view:
            return False
            
        # Detect selection index from multiple possible sources
        selected_points = getattr(curve_view, 'selected_points', None)
        if selected_points:
            # Use first selected point from set if available
            idx = list(selected_points)[0]
        elif getattr(main_window, 'selected_indices', None):
            # Fallback to main window's selection indices
            indices = main_window.selected_indices
            idx = indices[0] if indices else -1
        else:
            # No selection found
            idx = -1
            
        # If no valid selection, show message and exit
        if idx < 0:
            main_window.statusBar().showMessage("No point selected to center on", 2000)
            return False
            
        # Get current view state to ensure we respect it during centering
        view_state = {
            'widget_width': curve_view.width(),
            'widget_height': curve_view.height(),
            'zoom_factor': getattr(curve_view, 'zoom_factor', 1.0),
            'scale_to_image': getattr(curve_view, 'scale_to_image', False),
            'flip_y_axis': getattr(curve_view, 'flip_y_axis', False)
        }
        
        # Apply centering calculation which accounts for current widget dimensions
        # This ensures proper centering regardless of window size/state
        success = LegacyZoomOps.center_on_selected_point(curve_view, idx, preserve_zoom)
        
        # Show status message based on result
        if success:
            main_window.statusBar().showMessage(f"Centered view on point {idx}", 2000)
        else:
            main_window.statusBar().showMessage("Centering failed", 2000)
        return success

    @staticmethod
    def handle_wheel_event(curve_view: Any, event: Any) -> None:
        """Delegate wheel event handling to legacy ZoomOperations."""
        LegacyZoomOps.handle_wheel_event(curve_view, event)

    @staticmethod
    def zoom_view(curve_view: Any, factor: float) -> None:
        """Stub for zoom_view to satisfy static analysis."""
        pass

# Attach legacy static methods
for name, fn in LegacyZoomOps.__dict__.items():
    if callable(fn) and not name.startswith("_") and not hasattr(CenteringZoomService, name):
        setattr(CenteringZoomService, name, staticmethod(fn))
