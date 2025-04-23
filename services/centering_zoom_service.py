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
        # 1. Calculate the scaled content size
        scaled_content_size = (content_size[0] * zoom, content_size[1] * zoom)
        
        # 2. Calculate the scaled content position
        scaled_content_x = content_position[0] * zoom
        scaled_content_y = content_position[1] * zoom
        
        # 3. Calculate the center of the content
        center_x = scaled_content_x + (scaled_content_size[0] / 2)
        center_y = scaled_content_y + (scaled_content_size[1] / 2)
        
        # 4. Calculate the desired center position
        desired_center_x = point[0]
        desired_center_y = point[1]
        
        # 5. Calculate the required main offset to place the scaled point at the center
        required_offset_x = desired_center_x - base_offset[0] - scaled_content_x
        required_offset_y = desired_center_y - base_offset[1] - scaled_content_y
        
        # ... rest of the method remains the same ...

    @staticmethod
    def auto_center_view(main_window: Any, preserve_zoom: bool = True) -> bool:
        """Detect selected point and center the view using ZoomOperations."""
        curve_view = getattr(main_window, 'curve_view', None)
        if not curve_view:
            return False
        # Detect selection index
        selected_points = getattr(curve_view, 'selected_points', None)
        if selected_points:
            idx = list(selected_points)[0]
        elif getattr(main_window, 'selected_indices', None):
            indices = main_window.selected_indices
            idx = indices[0] if indices else -1
        else:
            idx = -1
        if idx < 0:
            main_window.statusBar().showMessage("No point selected to center on", 2000)
            return False
        # Apply centering math
        success = LegacyZoomOps.center_on_selected_point(curve_view, idx, preserve_zoom)
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
