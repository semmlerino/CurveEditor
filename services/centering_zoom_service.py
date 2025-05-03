#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CenteringZoomService: Manages view centering and zoom operations.
Provides methods for zooming, centering, and handling view transformations.
"""

from typing import Tuple, Optional, TYPE_CHECKING, Any

import sys  # For sys.stderr in exception handling

if TYPE_CHECKING:
    from curve_view import CurveView
    from PySide6.QtGui import QWheelEvent

class CenteringZoomService:
    """Service for managing centering and zoom operations."""

    @staticmethod
    def calculate_centering_offsets(
        widget_width: float,
        widget_height: float,
        display_width: float,
        display_height: float,
        offset_x: float = 0,
        offset_y: float = 0
    ) -> Tuple[float, float]:
        """Calculate centering offsets for a view.

        Args:
            widget_width: Width of the widget
            widget_height: Height of the widget
            display_width: Width of the content/image
            display_height: Height of the content/image
            offset_x: Additional X offset (default 0)
            offset_y: Additional Y offset (default 0)

        Returns:
            Tuple[float, float]: Centering offsets to apply (offset_x, offset_y)
        """
        # Make sure we're dealing with non-zero dimensions to avoid division errors
        if widget_width <= 0 or widget_height <= 0 or display_width <= 0 or display_height <= 0:
            return offset_x, offset_y

        # Center the content within the widget, respecting aspect ratio
        cx = (widget_width - display_width) / 2 + offset_x
        cy = (widget_height - display_height) / 2 + offset_y
        return cx, cy

    @staticmethod
    def center_on_selected_point(curve_view: 'CurveView', point_idx: int = -1, preserve_zoom: bool = True) -> bool:
        """Center the view on the specified point index.

        If no index is provided, uses the currently selected point.

        Args:
            curve_view: The curve view instance
            point_idx: Index of point to center on. Default -1 uses selected point.
            preserve_zoom: If True, maintain current zoom level. If False, reset view.

        Returns:
            bool: True if centering was successful, False otherwise
        """
        # Get the target point index
        idx: int = point_idx if point_idx >= 0 else getattr(curve_view, "selected_point_idx", -1)

        # The following attributes are accessed dynamically on curve_view. For type checking:
        # curve_view: CurveView
        # curve_view.main_window: MainWindow
        # curve_view.main_window.curve_data: list[tuple[int, float, float]] or similar
        if idx < 0 or not hasattr(curve_view, 'main_window') or not getattr(curve_view.main_window, "curve_data", None):
            return False

        try:
            if idx < len(curve_view.main_window.curve_data):
                # Get the point coordinates
                curve_data: list[Any] = curve_view.main_window.curve_data  # type: ignore[attr-defined]
                point: Any = curve_data[idx]
                _, x, y = point[:3]  # type: ignore
                curve_view.selected_point_idx = idx

                # Set zoom level - either preserve current or reset
                current_zoom = curve_view.zoom_factor if preserve_zoom else 1.0
                if not preserve_zoom:
                    CenteringZoomService.reset_view(curve_view)

                # Current view and content dimensions
                widget_width = curve_view.width()
                widget_height = curve_view.height()

                # Get original content size
                img_width: int = getattr(curve_view, "image_width", widget_width)
                img_height: int = getattr(curve_view, "image_height", widget_height)

                # If there's a background image, use its dimensions
                display_width: int
                display_height: int
                if getattr(curve_view, "background_image", None):
                    display_width = curve_view.background_image.width()
                    display_height = curve_view.background_image.height()
                else:
                    display_width = img_width
                    display_height = img_height

                # Apply proper zoom level
                scale_x: float = widget_width / display_width
                scale_y: float = widget_height / display_height
                scale: float = min(scale_x, scale_y) * current_zoom
                curve_view.zoom_factor = current_zoom  # Ensure zoom factor is consistent

                # Calculate the screen transformation for the selected point
                # This is the crucial part for proper centering

                # 1. Reset manual offset - we'll recalculate it
                # x_offset_old = getattr(curve_view, "x_offset", 0)
                # y_offset_old = getattr(curve_view, "y_offset", 0)  # Unused, remove for linting

                # 2. Correctly transform point coordinates to screen space
                point_x: float
                point_y: float
                if getattr(curve_view, "scale_to_image", False):
                    # Scale to image space first
                    img_scale_x: float = display_width / img_width
                    img_scale_y: float = display_height / img_height

                    point_x = x * img_scale_x
                    point_y = y * img_scale_y

                    # Check Y-axis flip
                    if getattr(curve_view, "flip_y_axis", False):
                        point_y = display_height - point_y
                else:
                    # Direct coordinate use
                    point_x = x
                    point_y = y

                    # Check Y-axis flip
                    if getattr(curve_view, "flip_y_axis", False):
                        point_y = img_height - point_y

                # 3. Scale point to widget space
                scaled_x: float = point_x * scale
                scaled_y: float = point_y * scale

                # 4. Calculate base content centering (centers entire content in view)
                total_width: float = display_width * scale
                total_height: float = display_height * scale
                base_x: float = (widget_width - total_width) / 2
                base_y: float = (widget_height - total_height) / 2

                # 5. Calculate offset needed to center selected point
                # Target is the center of the widget
                target_x: float = widget_width / 2
                target_y: float = widget_height / 2

                # Calculate how much we need to shift the view to center the point
                dx: float = target_x - (base_x + scaled_x)
                dy: float = target_y - (base_y + scaled_y)

                # 6. Apply the calculated offset directly
                # This ensures precise centering in all window states
                # CurveView expects int for offset_x/y, so cast as needed
                curve_view.offset_x = int(dx)  # type: ignore[attr-defined]
                curve_view.offset_y = int(dy)  # type: ignore[attr-defined]

                # 7. Clear any unneeded manual offsets since we've recalculated perfectly
                curve_view.x_offset = 0  # type: ignore[attr-defined]  # type: ignore[attr-defined]
                curve_view.y_offset = 0  # type: ignore[attr-defined]  # type: ignore[attr-defined]

                # Debug information
                if getattr(curve_view, "debug_mode", False):
                    print(f"Centering on point ({x}, {y}) with zoom {scale:.2f}")
                    print(f"Widget size: {widget_width}x{widget_height}")
                    print(f"Content size: {display_width}x{display_height} → {total_width:.1f}x{total_height:.1f}")
                    print(f"Base offset: ({base_x:.1f}, {base_y:.1f})")
                    print(f"Applied offset: ({curve_view.offset_x}, {curve_view.offset_y})")

                # Force a redraw with the new configuration
                curve_view.update()
                return True
            else:
                return False
        except Exception as e:
            print(f"Error in center_on_selected_point: {e}", file=sys.stderr)
            return False

    @staticmethod
    def fit_selection(curve_view: 'CurveView') -> bool:
        """Fit the view to the bounding box of all selected points."""
        selected_points = getattr(curve_view, "selected_points", None)
        points = getattr(curve_view, "points", None)

        if (
            selected_points is not None
            and points is not None
            and len(selected_points) > 1
        ):
            xs = []
            ys = []
            for idx in selected_points:
                if 0 <= idx < len(points):
                    pt = points[idx]
                    x = pt[1]
                    y = pt[2]
                    xs.append(x)
                    ys.append(y)

            if xs and ys:
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                bbox_width = max_x - min_x
                bbox_height = max_y - min_y

                # Add margins (25% of bbox size)
                margin_x = bbox_width * 0.25 if bbox_width > 0 else 10.0
                margin_y = bbox_height * 0.25 if bbox_height > 0 else 10.0
                min_x -= margin_x
                max_x += margin_x
                min_y -= margin_y
                max_y += margin_y

                bbox_width = max_x - min_x
                bbox_height = max_y - min_y

                widget_width = curve_view.width()
                widget_height = curve_view.height()
                display_width = getattr(curve_view, "image_width", widget_width)
                display_height = getattr(curve_view, "image_height", widget_height)

                # Calculate scale to fit bbox
                scale_x = widget_width / bbox_width if bbox_width > 0 else 1.0
                scale_y = widget_height / bbox_height if bbox_height > 0 else 1.0
                scale = min(scale_x, scale_y)
                scale = max(0.1, min(50.0, scale))  # Clamp scale

                # Calculate center point
                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2

                # Set new zoom level
                curve_view.zoom_factor = scale

                # Calculate centering offsets
                widget_cx = widget_width / 2
                widget_cy = widget_height / 2

                # Handle coordinate transforms
                if getattr(curve_view, "background_image", None) and getattr(curve_view, "scale_to_image", False):
                    img_x = center_x + getattr(curve_view, "x_offset", 0)
                    img_y = center_y + getattr(curve_view, "y_offset", 0)
                    tx = 0 + img_x * scale

                    if getattr(curve_view, "flip_y_axis", False):
                        ty = 0 + (display_height - img_y) * scale
                    else:
                        ty = 0 + img_y * scale
                else:
                    tx = 0 + center_x * scale

                    if getattr(curve_view, "flip_y_axis", False):
                        ty = 0 + (display_height - center_y) * scale
                    else:
                        ty = 0 + center_y * scale

                # Set final offset
                curve_view.offset_x = int(widget_cx - tx)  # type: ignore[attr-defined]
                curve_view.offset_y = int(widget_cy - ty)  # type: ignore[attr-defined]

                # Mark as a fit operation
                curve_view.last_action_was_fit = True  # type: ignore[attr-defined]
                curve_view.update()
                return True
        return False

    @staticmethod
    def handle_wheel_event(curve_view: 'CurveView', event: 'QWheelEvent') -> None:
        """Handle mouse wheel events for zooming."""
        # Prevent jumpy zoom immediately after fit_selection
        if hasattr(curve_view, 'last_action_was_fit') and getattr(curve_view, 'last_action_was_fit', False):
            curve_view.last_action_was_fit = False  # type: ignore[attr-defined]
            return

        # Determine zoom factor from wheel delta
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9

        # Get mouse position for zoom centering
        position = event.position() if hasattr(event, 'position') else event.pos()
        mouse_x = position.x()
        mouse_y = position.y()

        # Temporarily clear multi-selection to avoid special case handling
        temp_selected = None
        if hasattr(curve_view, 'selected_points') and len(curve_view.selected_points) > 1:
            temp_selected = curve_view.selected_points.copy()
            curve_view.selected_points = {curve_view.selected_point_idx} if getattr(curve_view, 'selected_point_idx', -1) >= 0 else set()

        # Perform zoom via centralized method, respecting auto-center setting
        if hasattr(curve_view, 'main_window') and getattr(curve_view.main_window, 'auto_center_enabled', False):
            # Auto-centering on: zoom relative to selected point
            CenteringZoomService.zoom_view(curve_view, factor)
        else:
            # Default: zoom relative to mouse position
            CenteringZoomService.zoom_view(curve_view, factor, mouse_x, mouse_y)

        # Restore multi-selection state if needed
        if temp_selected is not None:
            curve_view.selected_points = temp_selected
            curve_view.update()

    @staticmethod
    def reset_view(curve_view: 'CurveView') -> None:
        """Reset view to default state (zoom and position)."""
        curve_view.zoom_factor = 1.0

        # Reset all offset attributes
        for attr in ['x_offset', 'y_offset', 'offset_x', 'offset_y']:
            if hasattr(curve_view, attr):
                setattr(curve_view, attr, 0)

        curve_view.update()

    @staticmethod
    def zoom_view(curve_view: 'CurveView', factor: float, mouse_x: Optional[float] = None, mouse_y: Optional[float] = None) -> None:
        """Zoom the view while keeping the mouse position fixed.

        Args:
            curve_view: The curve view instance
            factor: Zoom factor (> 1 to zoom in, < 1 to zoom out)
            mouse_x: X-coordinate to zoom around, if None uses center
            mouse_y: Y-coordinate to zoom around, if None uses center
        """
        old_zoom = curve_view.zoom_factor

        # Check if we should skip multi-selection handling
        skip_multi_selection = hasattr(curve_view, "last_action_was_fit") and getattr(curve_view, "last_action_was_fit", False)
        selected_points = getattr(curve_view, "selected_points", None)
        points = getattr(curve_view, "points", None)

        # Apply new zoom factor with limits
        curve_view.zoom_factor = max(0.1, min(50.0, curve_view.zoom_factor * factor))

        # Store current widget dimensions for proper scaling calculations
        widget_width = curve_view.width()
        widget_height = curve_view.height()

        # Handle mouse-centered zooming
        if mouse_x is not None and mouse_y is not None:
            # Calculate zoom adjustments relative to mouse position
            zoom_ratio = factor - 1.0
            center_x = widget_width / 2
            center_y = widget_height / 2
            dx = mouse_x - center_x
            dy = mouse_y - center_y

            # Apply offset adjustments based on zoom center
            curve_view.offset_x -= dx * zoom_ratio
            curve_view.offset_y -= dy * zoom_ratio
        # If no mouse position and auto-center is enabled, recenter on selected point
        elif getattr(curve_view, 'main_window', None) and getattr(curve_view.main_window, 'auto_center_enabled', False) \
             and hasattr(curve_view, 'selected_point_idx') and curve_view.selected_point_idx >= 0:
            # Re-center on the selected point after zooming
            # This is critical for maintaining centering during resize/fullscreen
            CenteringZoomService.center_on_selected_point(curve_view, curve_view.selected_point_idx, preserve_zoom=True)

        # Reset the fit flag if it exists
        if hasattr(curve_view, "last_action_was_fit"):
            curve_view.last_action_was_fit = False  # type: ignore[attr-defined]

        # Force a redraw with the new configuration
        curve_view.update()

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
        idx: int
        if selected_points:
            # Use first selected point from set if available
            idx = int(list(selected_points)[0])
        elif getattr(main_window, 'selected_indices', None):
            # Fallback to main window's selection indices
            indices = main_window.selected_indices
            idx = int(indices[0]) if indices else -1
        else:
            # No selection found
            idx = -1

        # Always attempt to center via CenteringZoomService; let it handle invalid idx
        success: bool = CenteringZoomService.center_on_selected_point(curve_view, idx, preserve_zoom)

        # Show status message based on result
        if success:
            main_window.statusBar().showMessage(f"Centered view on point {idx}", 2000)
        else:
            main_window.statusBar().showMessage("Centering failed", 2000)
        return success
