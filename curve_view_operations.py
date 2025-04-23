#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Curve view operations for 3DE4 Curve Editor.
Provides functions for manipulating the curve view and handling point updates.

REFACTORED VERSION - Consolidated duplicate methods, improved error handling,
and added helper methods for common operations.
"""

from PySide6.QtCore import Qt as _Qt, QRect as _QRect
from typing import Any, cast, Tuple, Optional, Union, Dict, TYPE_CHECKING
Qt = cast(Any, _Qt)
QRect = cast(Any, _QRect)
from centering_zoom_operations import ZoomOperations
from error_handling import safe_operation
from curve_data_utils import compute_interpolated_curve_data
from curve_view_plumbing import operation, confirm_delete, normalize_point, set_point_status
if TYPE_CHECKING:
    from curve_view import CurveView
else:
    CurveView = Any

class CurveViewOperations:
    """Curve view operations for the 3DE4 Curve Editor."""
    
    # Alias for confirmation dialog
    _confirm_delete = confirm_delete
    
    @staticmethod
    def _get_curve_view(target: Any) -> CurveView:
        """Get CurveView instance from main window or direct."""
        return target.curve_view if hasattr(target, 'curve_view') else target

    @staticmethod
    def transform_point(curve_view: Any, x: float, y: float, display_width: float, display_height: float, offset_x: float, offset_y: float, scale: float) -> Tuple[float, float]:
        """Transform from track coordinates to widget coordinates.
        
        Args:
            curve_view: The curve view instance
            x: X-coordinate in track space
            y: Y-coordinate in track space
            display_width: Width of the display area
            display_height: Height of the display area
            offset_x: X offset for positioning
            offset_y: Y offset for positioning
            scale: Scale factor for the transformation
            
        Returns:
            tuple: (tx, ty) transformed coordinates in widget space
        """
        if curve_view.background_image and curve_view.scale_to_image:
            # Scale the tracking coordinates to match the image size
            img_x = x * (display_width / curve_view.image_width) + curve_view.x_offset
            img_y = y * (display_height / curve_view.image_height) + curve_view.y_offset
            
            # Scale to widget space
            tx = offset_x + img_x * scale
            
            # Apply Y-flip if enabled
            if curve_view.flip_y_axis:
                ty = offset_y + (display_height - img_y) * scale
            else:
                ty = offset_y + img_y * scale
        else:
            # Direct scaling with no image-based transformation
            tx = offset_x + x * scale
            
            # Apply Y-flip if enabled
            if curve_view.flip_y_axis:
                ty = offset_y + (curve_view.image_height - y) * scale
            else:
                ty = offset_y + y * scale
                
        return tx, ty
    
    @staticmethod
    def inverse_transform_point(curve_view: Any, tx: float, ty: float, display_width: float, display_height: float, offset_x: float, offset_y: float, scale: float) -> Tuple[float, float]:
        """Transform from widget coordinates back to track coordinates.
        
        Args:
            curve_view: The curve view instance
            tx: X-coordinate in widget space
            ty: Y-coordinate in widget space
            display_width: Width of the display area
            display_height: Height of the display area
            offset_x: X offset for positioning
            offset_y: Y offset for positioning
            scale: Scale factor for the transformation
            
        Returns:
            tuple: (x, y) transformed coordinates in track space
        """
        if curve_view.background_image and curve_view.scale_to_image:
            # Convert from widget to image space
            img_x = (tx - offset_x) / scale
            
            if curve_view.flip_y_axis:
                img_y = display_height - ((ty - offset_y) / scale)
            else:
                img_y = (ty - offset_y) / scale
            
            # Remove manual offset
            img_x = img_x - curve_view.x_offset
            img_y = img_y - curve_view.y_offset
            
            # Convert from image coordinates to track coordinates
            x = img_x / (display_width / curve_view.image_width)
            y = img_y / (display_height / curve_view.image_height)
        else:
            # Direct conversion from widget to track coordinates
            x = (tx - offset_x) / scale
            
            if curve_view.flip_y_axis:
                y = curve_view.image_height - ((ty - offset_y) / scale)
            else:
                y = (ty - offset_y) / scale
                
        return x, y
    
    @safe_operation("Reset View")
    @staticmethod
    def reset_view(target: Any) -> None:
        """Reset the curve view to default zoom and position.

        Args:
            target: The main window or curve view to reset
        """
        curve_view = CurveViewOperations._get_curve_view(target)
        ZoomOperations.reset_view(curve_view)
        # Update status bar if target is main window
        if hasattr(target, 'statusBar'):
            target.statusBar().showMessage("View reset to default", 2000)
    
    @safe_operation("Update Point")
    @staticmethod
    def update_point_from_edit(main_window: Any) -> bool:
        """Update the selected point from edit field values.
        
        Args:
            main_window: The main window containing point edit controls
        """
        # Get the selected point index
        idx = -1
        
        # Try to get index from curve view first
        if hasattr(main_window, 'curve_view') and hasattr(main_window.curve_view, 'selected_point_idx'):
            idx = main_window.curve_view.selected_point_idx
        
        # If not available or invalid, try to get from edit field
        if idx < 0 and hasattr(main_window, 'point_id_edit'):
            idx_text = main_window.point_id_edit.text()
            if idx_text:
                idx = int(idx_text)
        
        if idx < 0 or idx >= len(main_window.curve_data):
            raise ValueError("No valid point selected")
            
        # Get the new coordinates
        x = None
        y = None
        
        # Try new style edit fields first
        if hasattr(main_window, 'point_x_edit') and hasattr(main_window, 'point_y_edit'):
            x = float(main_window.point_x_edit.text())
            y = float(main_window.point_y_edit.text())
        # Fall back to old style edit fields
        elif hasattr(main_window, 'x_edit') and hasattr(main_window, 'y_edit'):
            x = float(main_window.x_edit.text())
            y = float(main_window.y_edit.text())
        
        if x is None or y is None:
            raise ValueError("Missing coordinate values")
        
        # Update the point in curve data
        frame = main_window.curve_data[idx][0]
        
        # Preserve status if the point has more than 3 elements
        if len(main_window.curve_data[idx]) > 3:
            status = main_window.curve_data[idx][3]
            main_window.curve_data[idx] = (frame, x, y, status)
        else:
            main_window.curve_data[idx] = (frame, x, y)
        
        # Update the view
        if hasattr(main_window.curve_view, 'setPoints'):
            main_window.curve_view.setPoints(
                main_window.curve_data, 
                main_window.image_width, 
                main_window.image_height,
                preserve_view=True  # Preserve view state when updating
            )
        elif hasattr(main_window.curve_view, 'set_curve_data'):
            main_window.curve_view.set_curve_data(main_window.curve_data)
        else:
            main_window.curve_view.update()
            
        # Add to history if available
        if hasattr(main_window, 'add_to_history'):
            main_window.add_to_history()
        
        return True
    
    @safe_operation("Point Moved")
    @staticmethod
    def on_point_moved(main_window: Any, idx: int, x: float, y: float) -> None:
        """Handle point moved event from the curve view.
        
        Args:
            main_window: The main window containing the curve data
            idx: Index of the moved point
            x: New X-coordinate
            y: New Y-coordinate
        """
        if 0 <= idx < len(main_window.curve_data):
            # Get current point data
            current_point = main_window.curve_data[idx]
            frame = current_point[0]
            
            # Update curve data and set status to keyframe
            main_window.curve_data[idx] = (frame, x, y, 'keyframe')
            
            # Update point info display
            CurveViewOperations.update_point_info(main_window, idx, x, y)
            
            # Add to history if available
            if hasattr(main_window, 'add_to_history'):
                main_window.add_to_history()
    
    @safe_operation("Mouse Release")
    @staticmethod
    def handle_mouse_release(curve_view: Any, event: Any) -> None:
        """Handle mouse release event for curve views.
        
        Args:
            curve_view: The curve view instance
            event: The mouse event
        """
        if event.button() == Qt.LeftButton:
            curve_view.drag_active = False
            
            # Handle selection rectangle if it exists
            if hasattr(curve_view, 'selection_start') and curve_view.selection_start is not None:
                # Try rectangle selection: returns False if no drag
                got = False
                if hasattr(curve_view, 'finalize_selection'):
                    got = curve_view.finalize_selection()
                if not got:
                    # No rectangle drag: fallback to section select
                    idx = CurveViewOperations.find_point_at(curve_view, event.x(), event.y())
                    CurveViewOperations.select_section(curve_view, idx)
                curve_view.selection_start = None
                curve_view.selection_rect = None
                curve_view.update()
            else:
                # Simple click: select a single point
                idx = CurveViewOperations.find_point_at(curve_view, event.x(), event.y())
                main_window = getattr(curve_view, 'main_window', None)
                CurveViewOperations.select_point_by_index(curve_view, main_window, idx)
                curve_view.update()
    
    @safe_operation("Mouse Press")
    @staticmethod
    def handle_mouse_press(curve_view: Any, event: Any) -> None:
        """Handle mouse press event for curve views."""
        # Initiate drag or pan based on button
        if event.button() == Qt.LeftButton:
            if event.modifiers() & Qt.AltModifier:
                # Alt+click or Alt+click-drag: start rectangle selection
                curve_view.selection_start = event.pos()
                curve_view.selection_rect = None
                return
            else:
                # Clear selection on single click
                main_window = getattr(curve_view, 'main_window', None)
                CurveViewOperations.clear_selection(curve_view, main_window)
                # Normal drag for moving a single point
                curve_view.drag_active = True
                curve_view.start_drag_x = event.x()
                curve_view.start_drag_y = event.y()
        elif event.button() == Qt.MiddleButton:
            curve_view.pan_start_x = event.x()
            curve_view.pan_start_y = event.y()
            curve_view.initial_offset_x = curve_view.offset_x
            curve_view.initial_offset_y = curve_view.offset_y
    
    @safe_operation("Mouse Move")
    @staticmethod
    def handle_mouse_move(curve_view: Any, event: Any) -> None:
        """Handle mouse movement for dragging points or panning.
        
        Args:
            curve_view: The curve view instance
            event: The mouse event
        """
        # Handle selection rectangle
        if hasattr(curve_view, 'selection_start') and curve_view.selection_start is not None:
            curve_view.selection_rect = QRect(curve_view.selection_start, event.pos()).normalized()
            # Live update: highlight points inside the rectangle as you drag
            widget_width = curve_view.width()
            widget_height = curve_view.height()
            display_width = curve_view.image_width
            display_height = curve_view.image_height
            if curve_view.background_image:
                display_width = curve_view.background_image.width()
                display_height = curve_view.background_image.height()
            scale_x = widget_width / display_width 
            scale_y = widget_height / display_height
            scale = min(scale_x, scale_y) * curve_view.zoom_factor
            offset_x, offset_y = ZoomOperations.calculate_centering_offsets(widget_width, widget_height, display_width * scale, display_height * scale, curve_view.offset_x, curve_view.offset_y)
        # offset_y is set below
            # offset_y is now set by calculate_centering_offsets above
            selected: set[int] = set()
            for i, point in enumerate(curve_view.points):
                _, x, y = point[:3]  # Handle both regular and interpolated points
                tx, ty = CurveViewOperations.transform_point(
                    curve_view, x, y, display_width, display_height, offset_x, offset_y, scale
                )
                if curve_view.selection_rect.contains(int(tx), int(ty)):
                    selected.add(i)
            curve_view.selected_points = selected
            # Optionally, set selected_point_idx to one of them for consistent highlighting
            if selected:
                curve_view.selected_point_idx = next(iter(selected))
            else:
                curve_view.selected_point_idx = -1
            # Debug log for validation
            if getattr(curve_view, "debug_mode", False):
                print(f"[DEBUG] Live selection: {len(selected)} points highlighted")
            curve_view.update()
            return
            
        # Calculate transform parameters for point dragging
        widget_width = curve_view.width()
        widget_height = curve_view.height()
        
        # Use the background image dimensions if available, otherwise use track dimensions
        display_width = curve_view.image_width
        display_height = curve_view.image_height
        
        if curve_view.background_image:
            display_width = curve_view.background_image.width()
            display_height = curve_view.background_image.height()
        
        # Calculate the scale factor to fit in the widget
        scale_x = widget_width / display_width 
        scale_y = widget_height / display_height
        
        # Use uniform scaling to maintain aspect ratio
        scale = min(scale_x, scale_y) * curve_view.zoom_factor
        
        # Calculate centering offsets
        offset_x, offset_y = ZoomOperations.calculate_centering_offsets(widget_width, widget_height, display_width * scale, display_height * scale, curve_view.offset_x, curve_view.offset_y)
        # offset_y is set below
        # offset_y is now set by calculate_centering_offsets above
        
        if curve_view.drag_active and curve_view.selected_point_idx >= 0:
            # Get the point we're dragging
            point_data = CurveViewOperations.get_point_data(curve_view, curve_view.selected_point_idx)
            if not point_data:
                return
                
            _, x, y, _ = point_data
            
            # Convert from widget coordinates back to track coordinates
            x, y = CurveViewOperations.inverse_transform_point(
                curve_view, event.x(), event.y(), 
                display_width, display_height, 
                offset_x, offset_y, scale
            )
            
            # Update point, setting moved point to keyframe
            main_window = getattr(curve_view, 'main_window', None)
            if main_window:
                CurveViewOperations.update_point_position(curve_view, main_window, curve_view.selected_point_idx, x, y)
            
            # Emit signal
            if hasattr(curve_view, 'point_moved'):
                curve_view.point_moved.emit(curve_view.selected_point_idx, x, y)
            
            curve_view.update()
        elif event.buttons() & Qt.MiddleButton:
            # Panning the view with middle mouse button
            dx = event.x() - curve_view.pan_start_x
            dy = event.y() - curve_view.pan_start_y
            
            curve_view.offset_x = curve_view.initial_offset_x + dx
            curve_view.offset_y = curve_view.initial_offset_y + dy
            
            curve_view.update()
        else:
            # Update for crosshair on mouse move
            curve_view.update()
    
    @staticmethod
    @operation("Select All Points", record_history=False)
    def select_all_points(curve_view: Any, main_window: Any) -> int:
        """Select all points in the curve."""
        if not curve_view.points:
            return 0
        curve_view.selected_points = set(range(len(curve_view.points)))
        curve_view.selected_point_idx = 0
        curve_view.update()
        if main_window and hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage(f"Selected all {len(curve_view.points)} points", 3000)
        return len(curve_view.points)
    
    @staticmethod
    @operation("Clear Selection", record_history=False)
    def clear_selection(curve_view: Any, main_window: Any) -> None:
        """Clear all point selections."""
        curve_view.selected_points = set()
        curve_view.selected_point_idx = -1
        curve_view.update()
        if main_window and hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage("Selection cleared", 2000)
    
    @staticmethod
    @operation("Select Point", record_history=False)
    def select_point_by_index(curve_view: Any, main_window: Any, index: int) -> bool:
        """Select a point by its index."""
        # Normalize index to int, fallback on selected_point_idx on failure
        try:
            index = int(index)
        except Exception:
            index = getattr(curve_view, 'selected_point_idx', -1)
        if not curve_view.points or index < 0 or index >= len(curve_view.points):
            return False
        curve_view.selected_point_idx = index
        curve_view.selected_points = {index}
        if hasattr(curve_view, 'point_selected'):
            curve_view.point_selected.emit(index)
        curve_view.update()
        if main_window:
            CurveViewOperations.on_point_selected(curve_view, main_window, index)
        return True
    
    @staticmethod
    @operation("Set Point Size", record_history=False)
    def set_point_size(curve_view: Any, main_window: Any, size: float) -> None:
        """Set the point display size."""
        curve_view.point_radius = max(1, min(10, size))
        curve_view.update()
        if main_window and hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage(f"Point size set to {size}", 2000)
    
    @staticmethod
    def get_point_data(curve_view: Any, idx: int) -> Optional[Tuple[int, float, float, str]]:
        """Get point data in a consistent format, handling both standard and interpolated points.
        
        Args:
            curve_view: The curve view instance
            idx: The index of the point to retrieve
            
        Returns:
            tuple: (frame, x, y, status) where status is 'normal' or 'interpolated'
        """
        if idx < 0 or idx >= len(curve_view.points):
            return None
            
        point = curve_view.points[idx]
        if len(point) == 3:  # Standard (frame, x, y) tuple
            return (point[0], point[1], point[2], 'normal')
        elif len(point) > 3:  # Extended tuple with status
            return point
        
        # Fallback for unexpected format
        return None
    
    @staticmethod
    def find_point_at(curve_view: Any, event_x: float, event_y: float) -> int:
        # DEBUG: trace input mouse coordinates
        print(f"[DEBUG] find_point_at called with event_x={event_x}, event_y={event_y}")
        """Find a point at the given position.
        
        Args:
            curve_view: The curve view instance
            event_x: X-coordinate of the mouse event
            event_y: Y-coordinate of the mouse event
            
        Returns:
            int: Index of the found point or -1 if no point was found
        """
        if not curve_view.points:
            return -1
            
        # Calculate transform parameters
        widget_width = curve_view.width()
        widget_height = curve_view.height()
        
        # Use the background image dimensions if available, otherwise use track dimensions
        display_width = curve_view.image_width
        display_height = curve_view.image_height
        
        if curve_view.background_image:
            display_width = curve_view.background_image.width()
            display_height = curve_view.background_image.height()
        
        # Calculate the scale factor
        scale_x = widget_width / display_width 
        scale_y = widget_height / display_height
        
        # Use uniform scaling to maintain aspect ratio
        scale = min(scale_x, scale_y) * curve_view.zoom_factor
        # DEBUG: show scale and dimensions
        print(f"[DEBUG] find_point_at: scale={scale:.3f}, widget=({widget_width},{widget_height}), display=({display_width},{display_height})")
        # Calculate centering offsets
        offset_x, offset_y = ZoomOperations.calculate_centering_offsets(
            widget_width, widget_height,
            display_width * scale, display_height * scale,
            curve_view.offset_x, curve_view.offset_y
        )
        # DEBUG: show computed offsets
        print(f"[DEBUG] find_point_at: offset_x={offset_x:.1f}, offset_y={offset_y:.1f}")
        # Check distance to each point
        closest_idx = -1
        min_distance = float('inf')
        
        for i, point in enumerate(curve_view.points):
            # Unpack and transform each point
            _, x, y = point[:3]
            tx, ty = CurveViewOperations.transform_point(
                curve_view, x, y,
                display_width, display_height,
                offset_x, offset_y, scale
            )
            # DEBUG: compute distance for point
            distance = ((event_x - tx) ** 2 + (event_y - ty) ** 2) ** 0.5
            detection_radius = curve_view.point_radius * 2
            print(f"[DEBUG] point {i}: tx={tx:.1f}, ty={ty:.1f}, distance={distance:.1f}, radius={detection_radius}")
            if distance <= detection_radius and distance < min_distance:
                min_distance = distance
                closest_idx = i
                
        # DEBUG: final selected index
        print(f"[DEBUG] find_point_at returning idx={closest_idx}")
        return closest_idx
    
    @staticmethod
    def find_closest_point_by_frame(curve_view: Any, frame_num: Union[int, float]) -> int:
        """Find the index of the point closest to the given frame number.
        
        Args:
            curve_view: The curve view instance
            frame_num: Target frame number
            
        Returns:
            int: Index of the closest point, or -1 if no points exist
        """
        if not curve_view.points:
            return -1
            
        closest_idx = -1
        min_distance = float('inf')
        
        for i, point in enumerate(curve_view.points):
            point_frame = point[0]
            distance = abs(point_frame - frame_num)
            
            if distance < min_distance:
                min_distance = distance
                closest_idx = i
                
        return closest_idx
    
    @staticmethod
    def _toggle_point_status(curve_view: Any, idx: int) -> Tuple[bool, Optional[str]]:
        """Toggle interpolation status of a single point."""
        try:
            point = curve_view.points[idx]
        except IndexError:
            return False, None
        _, _, _, status = normalize_point(point)
        new_status = 'normal' if status == 'interpolated' else 'interpolated'
        curve_view.points[idx] = set_point_status(point, new_status)
        return True, new_status

    @staticmethod
    @operation("Toggle Interpolation")
    def toggle_point_interpolation(curve_view: Any, idx: int) -> Union[bool, Tuple[bool, str]]:
        """Toggle the interpolated status of a point."""
        success, new_status = CurveViewOperations._toggle_point_status(curve_view, idx)
        if not success:
            return False
        # Update selection to toggled point
        curve_view.selected_points = {idx}
        curve_view.selected_point_idx = idx
        msg = f"Point {idx} {'interpolated' if new_status == 'interpolated' else 'normal'}"
        return True, msg

    @staticmethod
    @operation("Delete Points")
    def delete_selected_points(curve_view: Any, main_window: Any, show_confirmation: bool = False) -> Union[int, Tuple[int, str]]:
        """Delete or mark as interpolated the selected points."""
        selected_indices = sorted(getattr(curve_view, 'selected_points', []))
        if not selected_indices:
            return 0
        if show_confirmation and main_window:
            if not CurveViewOperations._confirm_delete(main_window, len(selected_indices)):
                return 0
        # Update the model instead of view.points
        new_data = compute_interpolated_curve_data(main_window.curve_data, selected_indices)
        main_window.curve_data = new_data
        curve_view.set_curve_data(main_window.curve_data)
        count = len(selected_indices)
        msg = f"Marked {count} point{'s' if count > 1 else ''} as interpolated"
        return (count, msg)
    
    @staticmethod
    def _move_point(curve_view: Any, index: int, x: float, y: float) -> bool:
        """Internal: update model only, setting moved point to keyframe."""
        main_window = getattr(curve_view, 'main_window', None)
        if main_window and 0 <= index < len(main_window.curve_data):
            frame, _, _, _ = normalize_point(main_window.curve_data[index])
            main_window.curve_data[index] = (frame, x, y, 'keyframe')
        return True
    
    @staticmethod
    @operation("Move Point")
    def update_point_position(curve_view: Any, main_window: Any, index: int, x: float, y: float) -> bool:
        """Wrap model move and finalize UI."""
        CurveViewOperations._move_point(curve_view, index, x, y)
        curve_view.set_curve_data(main_window.curve_data)
        return True
    
    @staticmethod
    @operation("Nudge Points")
    def nudge_selected_points(curve_view: Any, dx: Optional[int] = None, dy: Optional[int] = None) -> bool:
        """Nudge selected points by the specified delta."""
        # Coerce None arguments to zero (kwargs via decorator may pass None)
        if dx is None:
            dx = 0
        if dy is None:
            dy = 0
        main_window = getattr(curve_view, 'main_window', None)
        if not main_window:
            return False
        selected: set[int] = getattr(curve_view, 'selected_points', set())
        if not selected:
            return False
        incr = getattr(curve_view, 'nudge_increment', 1)
        actual_dx = dx * incr
        actual_dy = dy * incr
        # Update model
        for idx in selected:
            if 0 <= idx < len(main_window.curve_data):
                frame, x0, y0, status = normalize_point(main_window.curve_data[idx])
                main_window.curve_data[idx] = (frame, x0 + actual_dx, y0 + actual_dy, status)
        # Update view
        curve_view.set_curve_data(main_window.curve_data)
        # Emit move signal for primary selection
        if hasattr(curve_view, 'point_moved') and curve_view.selected_point_idx in selected:
            _, x1, y1, _ = normalize_point(main_window.curve_data[curve_view.selected_point_idx])
            curve_view.point_moved.emit(curve_view.selected_point_idx, x1, y1)
        return True
    
    @staticmethod
    @operation("Point Selected", record_history=False)
    def on_point_selected(curve_view: Any, main_window: Any, idx: int) -> None:
        """Handle point selected event.
        
        Args:
            curve_view: The curve view instance
            main_window: The main window containing the curve data
            idx: Index of the selected point
        """
        # Store selected indices in main_window
        sel_idx = curve_view.selected_point_idx if hasattr(curve_view, 'selected_point_idx') else idx
        # Override idx to ensure subsequent comparisons use an int
        idx = sel_idx if isinstance(sel_idx, int) else -1
        main_window.selected_indices = [idx] if idx >= 0 else []
        
        # Ensure the curve_view's selection is in sync
        if hasattr(main_window.curve_view, 'selected_points'):
            # Clear existing selection
            main_window.curve_view.selected_points.clear()
            
            # Add the newly selected point if valid
            if idx >= 0:
                main_window.curve_view.selected_points.add(idx)
                # Also update the primary selection index
                main_window.curve_view.selected_point_idx = idx
        
        if idx >= 0 and idx < len(main_window.curve_data):
            # Extract point data handling both regular (frame, x, y) and
            # extended (frame, x, y, status) formats
            point_data = main_window.curve_data[idx]
            frame, x, y = point_data[:3]  # Get first 3 elements regardless of length
            
            CurveViewOperations.update_point_info(main_window, idx, x, y)
            
            # Update timeline if available
            if hasattr(main_window, 'timeline_slider'):
                main_window.timeline_slider.setValue(frame)
        else:
            CurveViewOperations.update_point_info(main_window, -1, 0, 0)
    
    @staticmethod
    def _apply_text_mapping(main_window: Any, mapping: Dict[str, str]) -> None:
        """Set text on multiple UI controls based on a {attr: text} mapping."""
        for attr, text in mapping.items():
            if hasattr(main_window, attr):
                getattr(main_window, attr).setText(text)
    
    @staticmethod
    @operation("Update Info", record_history=False)
    def update_point_info(main_window: Any, idx: int, x: float, y: float) -> None:
        """Update the point information panel with selected point types for all selected points on the active frame.
        
        Args:
            main_window: The main window containing point info controls
            idx: Index of the selected point
            x: X-coordinate of the point
            y: Y-coordinate of the point
        """
        # If there are selected points, collect their types for the current frame
        selected_types: set[str] = set()
        frame = None
        if hasattr(main_window, 'curve_view') and hasattr(main_window.curve_view, 'get_selected_indices'):
            selected_indices = main_window.curve_view.get_selected_indices()
            if selected_indices:
                # Use the frame of the first selected point as the active frame
                first_idx = selected_indices[0]
                if first_idx >= 0 and first_idx < len(main_window.curve_data):
                    frame = main_window.curve_data[first_idx][0]
                    # Collect types for all selected points on this frame
                    for idx_ in selected_indices:
                        if idx_ >= 0 and idx_ < len(main_window.curve_data):
                            pt = main_window.curve_data[idx_]
                            if pt[0] == frame:
                                _, _, _, status = normalize_point(pt)
                                selected_types.add(status)
        # Fallback if no selection API or no selected points
        if not selected_types and idx >= 0 and idx < len(main_window.curve_data):
            frame = main_window.curve_data[idx][0]
            _, _, _, status = normalize_point(main_window.curve_data[idx])
            selected_types.add(status)
        # Update UI text fields
        fields = {
            'type_edit': ', '.join(sorted(selected_types)) if selected_types else '',
            'point_idx_label': f"Point: {idx}" if idx >= 0 else '',
            'point_frame_label': f"Frame: {frame}" if frame is not None else '',
            'point_id_edit': str(idx) if idx >= 0 else '',
            'point_x_edit': f"{x:.6f}" if idx >= 0 else '',
            'point_y_edit': f"{y:.6f}" if idx >= 0 else '',
        }
        CurveViewOperations._apply_text_mapping(main_window, fields)
        # Enable or disable edit controls
        if hasattr(main_window, 'enable_point_controls'):
            main_window.enable_point_controls(True if selected_types else False)
        # Update status bar to show point types
        if hasattr(main_window, 'statusBar'):
            if selected_types and frame is not None:
                main_window.statusBar().showMessage(f"Selected point(s) at frame {frame}: {', '.join(sorted(selected_types))}", 3000)
            else:
                main_window.statusBar().clearMessage()
    
    @staticmethod
    @operation("Finalize Selection", record_history=False)
    def finalize_selection(curve_view: Any, main_window: Any) -> bool:
        """Select all points inside the selection rectangle."""
        rect = getattr(curve_view, 'selection_rect', None)
        if rect is None or not curve_view.points:
            return False
        w, h = curve_view.width(), curve_view.height()
        dw, dh = curve_view.image_width, curve_view.image_height
        if curve_view.background_image:
            dw, dh = curve_view.background_image.width(), curve_view.background_image.height()
        sx, sy = w / dw, h / dh
        scale = min(sx, sy) * curve_view.zoom_factor
        ox, oy = ZoomOperations.calculate_centering_offsets(w, h, dw * scale, dh * scale, curve_view.offset_x, curve_view.offset_y)
        sel: set[int] = set()
        for i, pt in enumerate(curve_view.points):
            _, x, y = pt[:3]
            tx, ty = CurveViewOperations.transform_point(curve_view, x, y, dw, dh, ox, oy, scale)
            if rect.contains(int(tx), int(ty)):
                sel.add(i)
        curve_view.selected_points = sel
        curve_view.selected_point_idx = next(iter(sel)) if sel else -1
        return True
    
    @staticmethod
    @operation("Select Section", record_history=False)
    def select_section(curve_view: Any, idx: int) -> bool:
        # DEBUG: log invocation and data status
        print(f"[DEBUG] select_section called with idx={idx}")
        main_window = getattr(curve_view, 'main_window', None)
        if main_window is None or not hasattr(main_window, 'curve_data') or idx < 0 or idx >= len(main_window.curve_data):
            print(f"[DEBUG] select_section aborted: invalid main_window or idx out of range (idx={idx})")
            return False
        data = main_window.curve_data
        # DEBUG: show first/last point statuses
        first_status = normalize_point(data[0])[3] if data else None
        last_status = normalize_point(data[-1])[3] if data else None
        print(f"[DEBUG] curve_data length={len(data)}, first_status={first_status}, last_status={last_status}")
        # Find previous keyframe
        prev_idx = idx
        print(f"[DEBUG] starting prev_idx search from {prev_idx}")
        while prev_idx > 0:
            if normalize_point(data[prev_idx])[3] == 'keyframe':
                print(f"[DEBUG] found keyframe at prev_idx={prev_idx}")
                break
            prev_idx -= 1
        # Find next keyframe
        next_idx = idx
        print(f"[DEBUG] starting next_idx search from {next_idx}")
        while next_idx < len(data) - 1:
            if normalize_point(data[next_idx])[3] == 'keyframe':
                print(f"[DEBUG] found keyframe at next_idx={next_idx}")
                break
            next_idx += 1
        # Select indices range
        indices = list(range(prev_idx, next_idx + 1))
        print(f"[DEBUG] selecting indices {indices}")
        curve_view.selected_points = set(indices)
        curve_view.selected_point_idx = idx
        curve_view.update()
        # Update info panel
        _, x, y, _ = normalize_point(data[idx])
        CurveViewOperations.update_point_info(main_window, idx, x, y)
        return True