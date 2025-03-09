#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Curve view operations for 3DE4 Curve Editor.
Provides functions for manipulating the curve view and handling point updates.
"""

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt, QRect
import math


class CurveViewOperations:
    """Curve view operations for the 3DE4 Curve Editor."""
    
    @staticmethod
    def transform_point(curve_view, x, y, display_width, display_height, offset_x, offset_y, scale):
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
    def reset_view(main_window):
        """Reset the curve view to default zoom and position.
        
        Args:
            main_window: The main window that contains the curve_view
        """
        if hasattr(main_window, 'curve_view') and hasattr(main_window.curve_view, 'resetView'):
            main_window.curve_view.resetView()
    
    @staticmethod
    def on_point_selected(main_window, idx):
        """Handle point selected event.
        
        Args:
            main_window: The main window containing the curve data
            idx: Index of the selected point
        """
        # Store selected indices in main_window
        if hasattr(main_window, 'selected_indices'):
            main_window.selected_indices = [idx] if idx >= 0 else []
        
        # Ensure the curve_view's selection is in sync
        if hasattr(main_window, 'curve_view') and hasattr(main_window.curve_view, 'selected_points'):
            # Clear existing selection
            main_window.curve_view.selected_points.clear()
            
            # Add the newly selected point if valid
            if idx >= 0:
                main_window.curve_view.selected_points.add(idx)
                # Also update the primary selection index
                if hasattr(main_window.curve_view, 'selected_point_idx'):
                    main_window.curve_view.selected_point_idx = idx
        
        if idx >= 0 and idx < len(main_window.curve_data):
            x = main_window.curve_data[idx][1]
            y = main_window.curve_data[idx][2]
            CurveViewOperations.update_point_info(main_window, idx, x, y)
            
            # Update timeline if available
            if hasattr(main_window, 'timeline_slider'):
                frame = main_window.curve_data[idx][0]
                main_window.timeline_slider.setValue(frame)
        else:
            CurveViewOperations.update_point_info(main_window, -1, 0, 0)
    
    @staticmethod
    def update_point_info(main_window, idx, x, y):
        """Update the point information panel with selected point data.
        
        Args:
            main_window: The main window containing point info controls
            idx: Index of the selected point
            x: X-coordinate of the point
            y: Y-coordinate of the point
        """
        # Update point info display
        if idx >= 0 and idx < len(main_window.curve_data):
            frame = main_window.curve_data[idx][0]
            
            # Handle old-style controls
            if hasattr(main_window, 'point_idx_label'):
                main_window.point_idx_label.setText(f"Point: {idx}")
            if hasattr(main_window, 'point_frame_label'):
                main_window.point_frame_label.setText(f"Frame: {frame}")
            if hasattr(main_window, 'x_edit'):
                main_window.x_edit.setText(f"{x:.3f}")
            if hasattr(main_window, 'y_edit'):
                main_window.y_edit.setText(f"{y:.3f}")
            
            # Handle newer style controls
            if hasattr(main_window, 'point_id_edit'):
                main_window.point_id_edit.setText(str(idx))
            if hasattr(main_window, 'point_x_edit'):
                main_window.point_x_edit.setText(f"{x:.6f}")
            if hasattr(main_window, 'point_y_edit'):
                main_window.point_y_edit.setText(f"{y:.6f}")
            
            # Enable edit controls
            if hasattr(main_window, 'enable_point_controls'):
                main_window.enable_point_controls(True)
            
            # Update status bar if available
            if hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(f"Selected point {idx} at frame {frame}: ({x:.2f}, {y:.2f})", 3000)
            elif hasattr(main_window, 'status_bar'):
                main_window.status_bar.showMessage(f"Selected point {idx} at frame {frame}: ({x:.2f}, {y:.2f})", 3000)
        else:
            # Clear and disable edit fields if no valid point selected
            if hasattr(main_window, 'point_idx_label'):
                main_window.point_idx_label.setText("Point:")
            if hasattr(main_window, 'point_frame_label'):
                main_window.point_frame_label.setText("Frame: N/A")
            if hasattr(main_window, 'x_edit'):
                main_window.x_edit.clear()
            if hasattr(main_window, 'y_edit'):
                main_window.y_edit.clear()
                
            # Handle newer style controls
            if hasattr(main_window, 'point_id_edit'):
                main_window.point_id_edit.setText("")
            if hasattr(main_window, 'point_x_edit'):
                main_window.point_x_edit.setText("")
            if hasattr(main_window, 'point_y_edit'):
                main_window.point_y_edit.setText("")
            
            # Disable edit controls
            if hasattr(main_window, 'enable_point_controls'):
                main_window.enable_point_controls(False)
    
    @staticmethod
    def update_point_from_edit(main_window):
        """Update the selected point from edit field values.
        
        Args:
            main_window: The main window containing point edit controls
        """
        try:
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
                return
                
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
                return
            
            # Update the point in curve data
            frame = main_window.curve_data[idx][0]
            main_window.curve_data[idx] = (frame, x, y)
            
            # Update the view
            if hasattr(main_window.curve_view, 'setPoints'):
                main_window.curve_view.setPoints(
                    main_window.curve_data, 
                    main_window.image_width, 
                    main_window.image_height
                )
            elif hasattr(main_window.curve_view, 'set_curve_data'):
                main_window.curve_view.set_curve_data(main_window.curve_data)
            else:
                main_window.curve_view.update()
                
            # Add to history if available
            if hasattr(main_window, 'add_to_history'):
                main_window.add_to_history()
                
        except ValueError:
            QMessageBox.warning(main_window, "Invalid Input", "Please enter valid numeric values.")
        except Exception as e:
            QMessageBox.critical(main_window, "Error", f"Failed to update point: {str(e)}")
    
    @staticmethod
    def on_point_moved(main_window, idx, x, y):
        """Handle point moved event from the curve view.
        
        Args:
            main_window: The main window containing the curve data
            idx: Index of the moved point
            x: New X-coordinate
            y: New Y-coordinate
        """
        if 0 <= idx < len(main_window.curve_data):
            # Update curve data
            frame = main_window.curve_data[idx][0]
            main_window.curve_data[idx] = (frame, x, y)
            
            # Update point info display
            CurveViewOperations.update_point_info(main_window, idx, x, y)
            
            # Add to history if available
            if hasattr(main_window, 'add_to_history'):
                main_window.add_to_history()
                
    @staticmethod
    def handle_mouse_release(curve_view, event):
        """Handle mouse release event for curve views.
        
        Args:
            curve_view: The curve view instance
            event: The mouse event
        """
        if event.button() == Qt.LeftButton:
            curve_view.drag_active = False
            
            # Handle selection rectangle if it exists (for enhanced curve view)
            if hasattr(curve_view, 'selection_start') and curve_view.selection_start is not None:
                if hasattr(curve_view, 'finalize_selection'):
                    curve_view.finalize_selection()
                curve_view.selection_start = None
                curve_view.selection_rect = None
                curve_view.update()

    @staticmethod
    def select_all_points(curve_view):
        """Select all points in the curve.
        
        Args:
            curve_view: The curve view instance
        """
        if not curve_view.points:
            return
            
        curve_view.selected_points = set(range(len(curve_view.points)))
        if curve_view.points:
            curve_view.selected_point_idx = 0
            
        curve_view.update()
    
    @staticmethod
    def clear_selection(curve_view):
        """Clear all point selections.
        
        Args:
            curve_view: The curve view instance
        """
        curve_view.selected_points.clear()
        curve_view.selected_point_idx = -1
        curve_view.update()
    
    @staticmethod
    def select_point_by_index(curve_view, index):
        """Select a point by its index.
        
        Args:
            curve_view: The curve view instance
            index: The index of the point to select
        
        Returns:
            bool: True if selection was successful, False otherwise
        """
        if not curve_view.points or index < 0 or index >= len(curve_view.points):
            return False
            
        curve_view.selected_point_idx = index
        curve_view.selected_points = {index}
        curve_view.point_selected.emit(index)
        curve_view.update()
        return True
        
    @staticmethod
    def select_all_points(main_window):
        """Select all points in the view.
        
        Args:
            main_window: The main window containing the curve view
        """
        if hasattr(main_window.curve_view, 'selectAllPoints'):
            main_window.curve_view.selectAllPoints()
            main_window.statusBar().showMessage(f"Selected all {len(main_window.curve_data)} points", 3000)
    
    @staticmethod
    def deselect_all_points(main_window):
        """Deselect all points.
        
        Args:
            main_window: The main window containing the curve view
        """
        if hasattr(main_window.curve_view, 'clearSelection'):
            main_window.curve_view.clearSelection()
            main_window.statusBar().showMessage("Cleared selection", 2000)
    
    @staticmethod
    def delete_selected_points(main_window, show_confirmation=False):
        """Delete selected points from the curve.
        
        Args:
            main_window: The main window containing the curve data and view
            show_confirmation: Whether to show a confirmation dialog
        """
        # Get selected points
        if not hasattr(main_window.curve_view, 'selected_points') or not main_window.curve_view.selected_points:
            return
            
        # Save the view state before any changes
        view = main_window.curve_view
        view_state = {
            'zoom_factor': view.zoom_factor,
            'offset_x': view.offset_x,
            'offset_y': view.offset_y,
            'x_offset': view.x_offset,
            'y_offset': view.y_offset
        }
            
        selected_indices = sorted(main_window.curve_view.selected_points, reverse=True)
        
        # Confirm deletion if requested
        if show_confirmation:
            num_points = len(selected_indices)
            response = QMessageBox.question(
                main_window, 
                "Confirm Delete", 
                f"Delete {num_points} selected point{'s' if num_points > 1 else ''}?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if response != QMessageBox.Yes:
                return
        
        # Delete points, working backwards to maintain valid indices
        for idx in selected_indices:
            if 0 <= idx < len(main_window.curve_data):
                # Instead of deleting, mark the point as interpolated
                # Get the current point data
                if len(main_window.curve_data[idx]) == 3:  # If it's a standard (frame, x, y) tuple
                    frame, x, y = main_window.curve_data[idx]
                    # Replace with an extended tuple that includes 'interpolated' status
                    main_window.curve_data[idx] = (frame, x, y, 'interpolated')
                # We don't delete points anymore, just mark them as interpolated
                # del main_window.curve_data[idx]
        
        # Clear selection
        main_window.curve_view.clearSelection()
        
        # Preserve view state by manually assigning values after points update
        # First update the points without view reset
        if hasattr(main_window.curve_view, 'setPoints'):
            # Update points but don't reset the view
            main_window.curve_view.points = main_window.curve_data
            
            # Manually restore all view state variables
            view = main_window.curve_view
            view.zoom_factor = view_state['zoom_factor']
            view.offset_x = view_state['offset_x']
            view.offset_y = view_state['offset_y']
            view.x_offset = view_state['x_offset']
            view.y_offset = view_state['y_offset']
            
            # Select a new point if any points remain, focusing on the one after the deleted point
            if main_window.curve_data:
                # Use the first index that was deleted as an approximate position
                if selected_indices:
                    new_idx = min(selected_indices[0], len(main_window.curve_data) - 1)
                    if hasattr(main_window.curve_view, 'selectPointByIndex'):
                        main_window.curve_view.selectPointByIndex(new_idx)
                    else:
                        # Fallback if the method doesn't exist
                        main_window.curve_view.selected_point_idx = new_idx
                        main_window.curve_view.selected_points = {new_idx}
                        main_window.curve_view.point_selected.emit(new_idx)
            
            # Force update without resetting view
            view.update()
        else:
            main_window.curve_view.update()
        
        # Add to history
        if hasattr(main_window, 'add_to_history'):
            main_window.add_to_history()
            
        # Update status
        main_window.statusBar().showMessage(f"Deleted {len(selected_indices)} points", 3000)

    @staticmethod
    def zoom_in(main_window):
        """Zoom in on the curve view.
        
        Args:
            main_window: The main window containing the curve view
        """
        if hasattr(main_window, 'curve_view') and hasattr(main_window.curve_view, 'zoomIn'):
            main_window.curve_view.zoomIn()
            main_window.statusBar().showMessage("Zoomed in", 1000)
    
    @staticmethod
    def zoom_out(main_window):
        """Zoom out on the curve view.
        
        Args:
            main_window: The main window containing the curve view
        """
        if hasattr(main_window, 'curve_view') and hasattr(main_window.curve_view, 'zoomOut'):
            main_window.curve_view.zoomOut()
            main_window.statusBar().showMessage("Zoomed out", 1000)

    @staticmethod
    def set_point_size(main_window, size):
        """Set the point display size.
        
        Args:
            main_window: The main window that contains the curve_view
            size: Integer representing the point radius
        """
        if hasattr(main_window, 'curve_view') and main_window.curve_view:
            main_window.curve_view.set_point_radius(size)
            
    @staticmethod
    def set_point_radius(curve_view, radius):
        """Set the point display radius.
        
        Args:
            curve_view: The curve view instance
            radius: Integer representing the point radius (1-10)
        """
        curve_view.point_radius = max(1, min(10, radius))  # Ensure size is between 1 and 10
        curve_view.update()  # Redraw with new point size

    @staticmethod
    def toggle_point_interpolation(curve_view, idx):
        """Toggle the interpolated status of a point.
        
        Args:
            curve_view: The curve view instance
            idx: The index of the point to toggle
            
        Returns:
            bool: True if the operation was successful, False otherwise
        """
        if idx < 0 or idx >= len(curve_view.points):
            return False
        
        point = curve_view.points[idx]
        if len(point) == 3:  # Standard (frame, x, y) tuple
            frame, x, y = point
            # Mark as interpolated
            curve_view.points[idx] = (frame, x, y, 'interpolated')
        elif len(point) > 3:
            frame, x, y, status = point
            # If already interpolated, restore to normal
            if status == 'interpolated':
                curve_view.points[idx] = (frame, x, y)
            else:
                # Set status to interpolated
                curve_view.points[idx] = (frame, x, y, 'interpolated')
        
        curve_view.update()
        return True

    @staticmethod
    def restore_interpolated_point(curve_view, idx):
        """Restore an interpolated point to normal status.
        
        Args:
            curve_view: The curve view instance
            idx: The index of the point to restore
            
        Returns:
            bool: True if the operation was successful, False otherwise
        """
        if not CurveViewOperations.is_point_interpolated(curve_view, idx):
            return False
            
        point = curve_view.points[idx]
        if len(point) > 3:
            frame, x, y, _ = point
            curve_view.points[idx] = (frame, x, y)
            curve_view.update()
            return True
            
        return False

    @staticmethod
    def is_point_interpolated(curve_view, idx):
        """Check if a point has interpolated status.
        
        Args:
            curve_view: The curve view instance
            idx: The index of the point to check
            
        Returns:
            bool: True if the point is interpolated, False otherwise
        """
        point_data = CurveViewOperations.get_point_data(curve_view, idx)
        if point_data and len(point_data) > 3:
            return point_data[3] == 'interpolated'
        return False

    @staticmethod
    def get_point_data(curve_view, idx):
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
    def finalize_selection(curve_view):
        """Select all points inside the selection rectangle.
        
        Args:
            curve_view: The curve view instance
        """
        if not curve_view.selection_rect or not curve_view.points:
            return
            
        # Calculate transform parameters
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
        offset_x = (widget_width - (display_width * scale)) / 2 + curve_view.offset_x
        offset_y = (widget_height - (display_height * scale)) / 2 + curve_view.offset_y
        
        # Find all points within the selection rectangle
        selected = set()
        for i, (frame, x, y) in enumerate(curve_view.points):
            tx, ty = CurveViewOperations.transform_point(
                curve_view, x, y, display_width, display_height, offset_x, offset_y, scale
            )
            
            # Check if the point is within the selection rectangle
            if curve_view.selection_rect.contains(int(tx), int(ty)):
                selected.add(i)
                
        # If Ctrl is pressed, toggle selection for these points
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            for idx in selected:
                if idx in curve_view.selected_points:
                    curve_view.selected_points.remove(idx)
                else:
                    curve_view.selected_points.add(idx)
        else:
            # Otherwise replace current selection
            curve_view.selected_points = selected
            
        # Update primary selection if we have selected points
        if curve_view.selected_points:
            curve_view.selected_point_idx = next(iter(curve_view.selected_points))
            curve_view.point_selected.emit(curve_view.selected_point_idx)

    @staticmethod
    def update_point_position(curve_view, index, x, y):
        """Update a point's position while preserving its status.
        
        Args:
            curve_view: The curve view instance
            index: Index of the point to update
            x: New x-coordinate
            y: New y-coordinate
            
        Returns:
            bool: True if the operation was successful, False otherwise
        """
        if 0 <= index < len(curve_view.points):
            point = curve_view.points[index]
            frame = point[0]
            
            # Preserve status if it exists
            if len(point) > 3:
                status = point[3]
                curve_view.points[index] = (frame, x, y, status)
            else:
                curve_view.points[index] = (frame, x, y)
            
            return True
        
        return False

    @staticmethod
    def find_point_at(curve_view, pos):
        """Find point at the given position.
        
        Args:
            curve_view: The curve view instance
            pos: QPoint position to check
            
        Returns:
            int: Index of the point, or -1 if no point found
        """
        if not curve_view.points:
            return -1
            
        # Calculate transform parameters (same as in paintEvent)
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
        
        # Calculate centering offsets
        offset_x = (widget_width - (display_width * scale)) / 2 + curve_view.offset_x
        offset_y = (widget_height - (display_height * scale)) / 2 + curve_view.offset_y
        
        # Check distance to each point
        closest_idx = -1
        min_distance = float('inf')
        
        for i, point in enumerate(curve_view.points):
            frame, x, y = point[:3]  # Handle both regular and interpolated points
            tx, ty = CurveViewOperations.transform_point(
                curve_view, x, y, display_width, display_height, offset_x, offset_y, scale
            )
            
            # Calculate distance to mouse position
            distance = ((pos.x() - tx) ** 2 + (pos.y() - ty) ** 2) ** 0.5
            
            # Use a detection radius based on point_radius
            detection_radius = curve_view.point_radius * 2
            
            if distance <= detection_radius and distance < min_distance:
                min_distance = distance
                closest_idx = i
                
        return closest_idx

    @staticmethod
    def set_curve_data(curve_view, curve_data):
        """Set curve data for the view.
        
        Args:
            curve_view: The curve view instance
            curve_data: List of points in format [(frame, x, y), ...] or [(frame, x, y, status), ...]
        """
        curve_view.points = curve_data
        curve_view.update()
    
    @staticmethod
    def set_selected_indices(curve_view, indices):
        """Set selected point indices.
        
        Args:
            curve_view: The curve view instance
            indices: List of indices to select
        """
        curve_view.selected_points = set(indices)
        if indices:
            curve_view.selected_point_idx = indices[0]  # Set first selected as current
        else:
            curve_view.selected_point_idx = -1
        curve_view.update()
    
    @staticmethod
    def change_nudge_increment(curve_view, increase=True):
        """Change the nudge increment for point movement.
        
        Args:
            curve_view: The curve view instance
            increase: If True, increase the increment, otherwise decrease it
            
        Returns:
            float: The new nudge increment value
        """
        if not hasattr(curve_view, 'available_increments') or not hasattr(curve_view, 'current_increment_index'):
            return 1.0
            
        # Get the current index and available increments
        current_idx = curve_view.current_increment_index
        increments = curve_view.available_increments
        
        # Calculate new index with bounds checking
        if increase:
            new_idx = min(current_idx + 1, len(increments) - 1)
        else:
            new_idx = max(current_idx - 1, 0)
            
        # Update the index and increment value
        curve_view.current_increment_index = new_idx
        curve_view.nudge_increment = increments[new_idx]
        
        return curve_view.nudge_increment
    
    @staticmethod
    def nudge_selected_points(curve_view, dx=0, dy=0):
        """Nudge selected points by the specified delta.
        
        Args:
            curve_view: The curve view instance
            dx: Delta x to apply
            dy: Delta y to apply
            
        Returns:
            bool: True if any points were nudged, False otherwise
        """
        if not hasattr(curve_view, 'selected_points') or not curve_view.selected_points:
            return False
            
        # Apply the nudge increment
        actual_dx = dx * curve_view.nudge_increment
        actual_dy = dy * curve_view.nudge_increment
        
        # Track if any points were modified
        modified = False
        
        # Update each selected point
        for idx in curve_view.selected_points:
            if 0 <= idx < len(curve_view.points):
                point = curve_view.points[idx]
                frame, x, y = point[:3]  # Handle both regular and interpolated points
                
                # Calculate new position
                new_x = x + actual_dx
                new_y = y + actual_dy
                
                # Update the point
                modified = CurveViewOperations.update_point_position(curve_view, idx, new_x, new_y) or modified
                
                # Emit signal for the primary selected point
                if idx == curve_view.selected_point_idx:
                    curve_view.point_moved.emit(idx, new_x, new_y)
        
        # Update the view if any points were modified
        if modified:
            curve_view.update()
            
        return modified

    @staticmethod
    def extract_frame_number(curve_view, img_idx):
        """Extract frame number from the current image index.
        
        Args:
            curve_view: The curve view instance
            img_idx: The image index to extract frame number from
            
        Returns:
            int: The frame number, or img_idx if extraction fails
        """
        if img_idx < 0 or img_idx >= len(curve_view.image_filenames):
            return 0
            
        # Try to extract frame number from filename
        try:
            # Assume filename format includes frame number
            filename = curve_view.image_filenames[img_idx]
            # Extract numeric part - this is a simple implementation
            # that assumes frame numbers are digits in the filename
            import re
            matches = re.findall(r'\d+', filename)
            if matches:
                return int(matches[-1])  # Use the last number in the filename
        except Exception as e:
            print(f"Error extracting frame number: {str(e)}")
            
        # Fallback to using the image index itself
        return img_idx
    
    @staticmethod
    def find_closest_point_by_frame(curve_view, frame_num):
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
    def handle_key_press(curve_view, event):
        """Handle curve view operation key press events.
        
        Args:
            curve_view: The curve view instance
            event: The key event
            
        Returns:
            bool: True if the event was handled, False otherwise
        """
        from PySide6.QtCore import Qt
        import math
        
        handled = True
        
        # Get nudge increment and adjust based on modifiers
        step = curve_view.nudge_increment
        
        # Larger step if Shift is pressed
        if event.modifiers() & Qt.ShiftModifier:
            step = curve_view.available_increments[curve_view.current_increment_index + 1] if curve_view.current_increment_index < len(curve_view.available_increments) - 1 else curve_view.available_increments[-1]
        
        # Smaller step if Ctrl is pressed
        if event.modifiers() & Qt.ControlModifier:
            step = curve_view.available_increments[curve_view.current_increment_index - 1] if curve_view.current_increment_index > 0 else curve_view.available_increments[0]
        
        if event.key() == Qt.Key_R:
            # Reset view
            curve_view.resetView()
            # Also reset manual offsets
            curve_view.x_offset = 0
            curve_view.y_offset = 0
            curve_view.update()
        elif event.key() == Qt.Key_A:
            # Select all points
            curve_view.selectAllPoints()
            curve_view.update()
        elif event.key() == Qt.Key_Escape:
            # Clear selection
            curve_view.clearSelection()
            curve_view.update()
        elif event.key() == Qt.Key_Delete:
            # Delete selected points (mark as interpolated)
            if curve_view.selected_points or curve_view.selected_point_idx >= 0:
                # Get all selected points
                selected_indices = sorted(curve_view.selected_points, reverse=True)
                
                # Mark each point as interpolated
                for idx in selected_indices:
                    if 0 <= idx < len(curve_view.points):
                        CurveViewOperations.toggle_point_interpolation(curve_view, idx)
                
                # Clear selection
                curve_view.clearSelection()
                curve_view.update()
        elif event.key() == Qt.Key_Left or event.key() == Qt.Key_4:
            # Adjust x-offset with arrow keys + modifiers
            if event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier):
                curve_view.x_offset -= step
                curve_view.update()
            elif curve_view.selected_point_idx >= 0:
                # Nudge selected point left
                CurveViewOperations.nudge_selected_points(curve_view, dx=-1, dy=0)
        elif event.key() == Qt.Key_Right or event.key() == Qt.Key_6:
            # Adjust x-offset with arrow keys + modifiers
            if event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier):
                curve_view.x_offset += step
                curve_view.update()
            elif curve_view.selected_point_idx >= 0:
                # Nudge selected point right
                CurveViewOperations.nudge_selected_points(curve_view, dx=1, dy=0)
        elif event.key() == Qt.Key_Up or event.key() == Qt.Key_8:
            if event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier):
                # Adjust y-offset with arrow keys + modifiers
                curve_view.y_offset -= step
                curve_view.update()
            elif curve_view.selected_point_idx >= 0:
                # Nudge selected point up
                CurveViewOperations.nudge_selected_points(curve_view, dx=0, dy=-1)
            else:
                # Increase nudge increment
                CurveViewOperations.change_nudge_increment(curve_view, increase=True)
        elif event.key() == Qt.Key_Down or event.key() == Qt.Key_2:
            if event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier):
                # Adjust y-offset with arrow keys + modifiers
                curve_view.y_offset += step
                curve_view.update()
            elif curve_view.selected_point_idx >= 0:
                # Nudge selected point down
                CurveViewOperations.nudge_selected_points(curve_view, dx=0, dy=1)
            else:
                # Decrease nudge increment
                CurveViewOperations.change_nudge_increment(curve_view, increase=False)
        else:
            handled = False
            
        return handled

    @staticmethod
    def handle_mouse_press(curve_view, event):
        """Handle mouse press event for curve views.
        
        Args:
            curve_view: The curve view instance
            event: The mouse event
        """
        if event.button() == Qt.LeftButton:
            # Check if Shift is pressed for multi-selection rectangle
            if event.modifiers() & Qt.ShiftModifier:
                curve_view.selection_start = event.pos()
                curve_view.selection_rect = QRect(curve_view.selection_start, curve_view.selection_start)
                curve_view.update()
                return
                
            # Calculate transform parameters
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
            offset_x = (widget_width - (display_width * scale)) / 2 + curve_view.offset_x
            offset_y = (widget_height - (display_height * scale)) / 2 + curve_view.offset_y

            curve_view.drag_active = False
            
            # Check if Ctrl is pressed for multi-selection
            ctrl_pressed = event.modifiers() & Qt.ControlModifier
            
            # Find if we clicked on a point
            clicked_on_point = False
            for i, point in enumerate(curve_view.points):
                frame, x, y = point[:3]  # Extract only frame, x, y even if there's a status
                tx, ty = CurveViewOperations.transform_point(curve_view, x, y, display_width, display_height, offset_x, offset_y, scale)
                
                # Check if within radius
                dx = event.x() - tx
                dy = event.y() - ty
                dist = math.sqrt(dx * dx + dy * dy)
                
                if dist <= curve_view.point_radius + 2:  # +2 for better selection
                    clicked_on_point = True
                    
                    if ctrl_pressed:
                        # Add/remove from multi-selection
                        if i in curve_view.selected_points:
                            curve_view.selected_points.remove(i)
                        else:
                            curve_view.selected_points.add(i)
                            curve_view.selected_point_idx = i  # Also make it primary selection
                    else:
                        # If Ctrl is not pressed, clear selection before selecting this point
                        if not ctrl_pressed:
                            curve_view.selected_points.clear()
                        
                        curve_view.selected_point_idx = i
                        curve_view.selected_points.add(i)
                        curve_view.drag_active = True
                        
                    curve_view.point_selected.emit(i)
                    break
            
            # If clicked on empty space and not using Ctrl for multi-select, clear selection
            if not clicked_on_point and not ctrl_pressed:
                curve_view.selected_points.clear()
                curve_view.selected_point_idx = -1
                
            curve_view.update()
                
        elif event.button() == Qt.MiddleButton:
            # Middle click for panning
            curve_view.pan_start_x = event.x()
            curve_view.pan_start_y = event.y()
            curve_view.initial_offset_x = curve_view.offset_x
            curve_view.initial_offset_y = curve_view.offset_y

    @staticmethod
    def handle_mouse_move(curve_view, event):
        """Handle mouse movement for dragging points or panning.
        
        Args:
            curve_view: The curve view instance
            event: The mouse event
        """
        # Handle selection rectangle
        if curve_view.selection_start is not None:
            curve_view.selection_rect = QRect(curve_view.selection_start, event.pos()).normalized()
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
        offset_x = (widget_width - (display_width * scale)) / 2 + curve_view.offset_x
        offset_y = (widget_height - (display_height * scale)) / 2 + curve_view.offset_y
        
        if curve_view.drag_active and curve_view.selected_point_idx >= 0:
            # Get the point we're dragging
            point_data = CurveViewOperations.get_point_data(curve_view, curve_view.selected_point_idx)
            if not point_data:
                return
                
            frame, x, y, status = point_data
            
            # Convert from widget coordinates back to track coordinates
            if curve_view.background_image and curve_view.scale_to_image:
                # First convert to image coordinates
                img_x_with_scale = (event.x() - offset_x) / scale
                
                if curve_view.flip_y_axis:
                    img_y_with_scale = display_height - ((event.y() - offset_y) / scale)
                else:
                    img_y_with_scale = (event.y() - offset_y) / scale
                
                # Remove manual offset
                img_x = img_x_with_scale - curve_view.x_offset
                img_y = img_y_with_scale - curve_view.y_offset
                
                # Convert from image coordinates to track coordinates
                new_x = img_x / (display_width / curve_view.image_width)
                new_y = img_y / (display_height / curve_view.image_height)
            else:
                # Direct conversion from widget to track coordinates
                new_x = (event.x() - offset_x) / scale
                
                if curve_view.flip_y_axis:
                    new_y = curve_view.image_height - ((event.y() - offset_y) / scale)
                else:
                    new_y = (event.y() - offset_y) / scale
            
            # Update point, preserving interpolated status
            CurveViewOperations.update_point_position(curve_view, curve_view.selected_point_idx, new_x, new_y)
            
            # Emit signal
            curve_view.point_moved.emit(curve_view.selected_point_idx, new_x, new_y)
            
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
    def handle_mouse_release(curve_view, event):
        """Handle mouse release event for curve views.
        
        Args:
            curve_view: The curve view instance
            event: The mouse event
        """
        if event.button() == Qt.LeftButton:
            curve_view.drag_active = False
            
            # Handle selection rectangle if it exists (for enhanced curve view)
            if hasattr(curve_view, 'selection_start') and curve_view.selection_start is not None:
                if hasattr(curve_view, 'finalize_selection'):
                    curve_view.finalize_selection()
                curve_view.selection_start = None
                curve_view.selection_rect = None
                curve_view.update()

    @staticmethod
    def select_all_points(curve_view):
        """Select all points in the curve.
        
        Args:
            curve_view: The curve view instance
        """
        if not curve_view.points:
            return
            
        curve_view.selected_points = set(range(len(curve_view.points)))
        if curve_view.points:
            curve_view.selected_point_idx = 0
            
        curve_view.update()
    
    @staticmethod
    def clear_selection(curve_view):
        """Clear all point selections.
        
        Args:
            curve_view: The curve view instance
        """
        curve_view.selected_points.clear()
        curve_view.selected_point_idx = -1
        curve_view.update()
    
    @staticmethod
    def select_point_by_index(curve_view, index):
        """Select a point by its index.
        
        Args:
            curve_view: The curve view instance
            index: The index of the point to select
        
        Returns:
            bool: True if selection was successful, False otherwise
        """
        if not curve_view.points or index < 0 or index >= len(curve_view.points):
            return False
            
        curve_view.selected_point_idx = index
        curve_view.selected_points = {index}
        curve_view.point_selected.emit(index)
        curve_view.update()
        return True
        
    @staticmethod
    def select_all_points(main_window):
        """Select all points in the view.
        
        Args:
            main_window: The main window containing the curve view
        """
        if hasattr(main_window.curve_view, 'selectAllPoints'):
            main_window.curve_view.selectAllPoints()
            main_window.statusBar().showMessage(f"Selected all {len(main_window.curve_data)} points", 3000)
    
    @staticmethod
    def deselect_all_points(main_window):
        """Deselect all points.
        
        Args:
            main_window: The main window containing the curve view
        """
        if hasattr(main_window.curve_view, 'clearSelection'):
            main_window.curve_view.clearSelection()
            main_window.statusBar().showMessage("Cleared selection", 2000)
    
    @staticmethod
    def delete_selected_points(main_window, show_confirmation=False):
        """Delete selected points from the curve.
        
        Args:
            main_window: The main window containing the curve data and view
            show_confirmation: Whether to show a confirmation dialog
        """
        # Get selected points
        if not hasattr(main_window.curve_view, 'selected_points') or not main_window.curve_view.selected_points:
            return
            
        # Save the view state before any changes
        view = main_window.curve_view
        view_state = {
            'zoom_factor': view.zoom_factor,
            'offset_x': view.offset_x,
            'offset_y': view.offset_y,
            'x_offset': view.x_offset,
            'y_offset': view.y_offset
        }
            
        selected_indices = sorted(main_window.curve_view.selected_points, reverse=True)
        
        # Confirm deletion if requested
        if show_confirmation:
            num_points = len(selected_indices)
            response = QMessageBox.question(
                main_window, 
                "Confirm Delete", 
                f"Delete {num_points} selected point{'s' if num_points > 1 else ''}?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if response != QMessageBox.Yes:
                return
        
        # Delete points, working backwards to maintain valid indices
        for idx in selected_indices:
            if 0 <= idx < len(main_window.curve_data):
                # Instead of deleting, mark the point as interpolated
                # Get the current point data
                if len(main_window.curve_data[idx]) == 3:  # If it's a standard (frame, x, y) tuple
                    frame, x, y = main_window.curve_data[idx]
                    # Replace with an extended tuple that includes 'interpolated' status
                    main_window.curve_data[idx] = (frame, x, y, 'interpolated')
                # We don't delete points anymore, just mark them as interpolated
                # del main_window.curve_data[idx]
        
        # Clear selection
        main_window.curve_view.clearSelection()
        
        # Preserve view state by manually assigning values after points update
        # First update the points without view reset
        if hasattr(main_window.curve_view, 'setPoints'):
            # Update points but don't reset the view
            main_window.curve_view.points = main_window.curve_data
            
            # Manually restore all view state variables
            view = main_window.curve_view
            view.zoom_factor = view_state['zoom_factor']
            view.offset_x = view_state['offset_x']
            view.offset_y = view_state['offset_y']
            view.x_offset = view_state['x_offset']
            view.y_offset = view_state['y_offset']
            
            # Select a new point if any points remain, focusing on the one after the deleted point
            if main_window.curve_data:
                # Use the first index that was deleted as an approximate position
                if selected_indices:
                    new_idx = min(selected_indices[0], len(main_window.curve_data) - 1)
                    if hasattr(main_window.curve_view, 'selectPointByIndex'):
                        main_window.curve_view.selectPointByIndex(new_idx)
                    else:
                        # Fallback if the method doesn't exist
                        main_window.curve_view.selected_point_idx = new_idx
                        main_window.curve_view.selected_points = {new_idx}
                        main_window.curve_view.point_selected.emit(new_idx)
            
            # Force update without resetting view
            view.update()
        else:
            main_window.curve_view.update()
        
        # Add to history
        if hasattr(main_window, 'add_to_history'):
            main_window.add_to_history()
            
        # Update status
        main_window.statusBar().showMessage(f"Deleted {len(selected_indices)} points", 3000)

    @staticmethod
    def zoom_in(main_window):
        """Zoom in on the curve view.
        
        Args:
            main_window: The main window containing the curve view
        """
        if hasattr(main_window, 'curve_view') and hasattr(main_window.curve_view, 'zoomIn'):
            main_window.curve_view.zoomIn()
            main_window.statusBar().showMessage("Zoomed in", 1000)
    
    @staticmethod
    def zoom_out(main_window):
        """Zoom out on the curve view.
        
        Args:
            main_window: The main window containing the curve view
        """
        if hasattr(main_window, 'curve_view') and hasattr(main_window.curve_view, 'zoomOut'):
            main_window.curve_view.zoomOut()
            main_window.statusBar().showMessage("Zoomed out", 1000)

    @staticmethod
    def set_point_size(main_window, size):
        """Set the point display size.
        
        Args:
            main_window: The main window that contains the curve_view
            size: Integer representing the point radius
        """
        if hasattr(main_window, 'curve_view') and main_window.curve_view:
            main_window.curve_view.set_point_radius(size)
            
    @staticmethod
    def set_point_radius(curve_view, radius):
        """Set the point display radius.
        
        Args:
            curve_view: The curve view instance
            radius: Integer representing the point radius (1-10)
        """
        curve_view.point_radius = max(1, min(10, radius))  # Ensure size is between 1 and 10
        curve_view.update()  # Redraw with new point size

    @staticmethod
    def toggle_point_interpolation(curve_view, idx):
        """Toggle the interpolated status of a point.
        
        Args:
            curve_view: The curve view instance
            idx: The index of the point to toggle
            
        Returns:
            bool: True if the operation was successful, False otherwise
        """
        if idx < 0 or idx >= len(curve_view.points):
            return False
        
        point = curve_view.points[idx]
        if len(point) == 3:  # Standard (frame, x, y) tuple
            frame, x, y = point
            # Mark as interpolated
            curve_view.points[idx] = (frame, x, y, 'interpolated')
        elif len(point) > 3:
            frame, x, y, status = point
            # If already interpolated, restore to normal
            if status == 'interpolated':
                curve_view.points[idx] = (frame, x, y)
            else:
                # Set status to interpolated
                curve_view.points[idx] = (frame, x, y, 'interpolated')
        
        curve_view.update()
        return True

    @staticmethod
    def restore_interpolated_point(curve_view, idx):
        """Restore an interpolated point to normal status.
        
        Args:
            curve_view: The curve view instance
            idx: The index of the point to restore
            
        Returns:
            bool: True if the operation was successful, False otherwise
        """
        if not CurveViewOperations.is_point_interpolated(curve_view, idx):
            return False
            
        point = curve_view.points[idx]
        if len(point) > 3:
            frame, x, y, _ = point
            curve_view.points[idx] = (frame, x, y)
            curve_view.update()
            return True
            
        return False

    @staticmethod
    def is_point_interpolated(curve_view, idx):
        """Check if a point has interpolated status.
        
        Args:
            curve_view: The curve view instance
            idx: The index of the point to check
            
        Returns:
            bool: True if the point is interpolated, False otherwise
        """
        point_data = CurveViewOperations.get_point_data(curve_view, idx)
        if point_data and len(point_data) > 3:
            return point_data[3] == 'interpolated'
        return False

    @staticmethod
    def get_point_data(curve_view, idx):
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
    def finalize_selection(curve_view):
        """Select all points inside the selection rectangle.
        
        Args:
            curve_view: The curve view instance
        """
        if not curve_view.selection_rect or not curve_view.points:
            return
            
        # Calculate transform parameters
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
        offset_x = (widget_width - (display_width * scale)) / 2 + curve_view.offset_x
        offset_y = (widget_height - (display_height * scale)) / 2 + curve_view.offset_y
        
        # Find all points within the selection rectangle
        selected = set()
        for i, (frame, x, y) in enumerate(curve_view.points):
            tx, ty = CurveViewOperations.transform_point(
                curve_view, x, y, display_width, display_height, offset_x, offset_y, scale
            )
            
            # Check if the point is within the selection rectangle
            if curve_view.selection_rect.contains(int(tx), int(ty)):
                selected.add(i)
                
        # If Ctrl is pressed, toggle selection for these points
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            for idx in selected:
                if idx in curve_view.selected_points:
                    curve_view.selected_points.remove(idx)
                else:
                    curve_view.selected_points.add(idx)
        else:
            # Otherwise replace current selection
            curve_view.selected_points = selected
            
        # Update primary selection if we have selected points
        if curve_view.selected_points:
            curve_view.selected_point_idx = next(iter(curve_view.selected_points))
            curve_view.point_selected.emit(curve_view.selected_point_idx)

    @staticmethod
    def update_point_position(curve_view, index, x, y):
        """Update a point's position while preserving its status.
        
        Args:
            curve_view: The curve view instance
            index: Index of the point to update
            x: New x-coordinate
            y: New y-coordinate
            
        Returns:
            bool: True if the operation was successful, False otherwise
        """
        if 0 <= index < len(curve_view.points):
            point = curve_view.points[index]
            frame = point[0]
            
            # Preserve status if it exists
            if len(point) > 3:
                status = point[3]
                curve_view.points[index] = (frame, x, y, status)
            else:
                curve_view.points[index] = (frame, x, y)
            
            return True
        
        return False

    @staticmethod
    def find_point_at(curve_view, pos):
        """Find point at the given position.
        
        Args:
            curve_view: The curve view instance
            pos: QPoint position to check
            
        Returns:
            int: Index of the point, or -1 if no point found
        """
        if not curve_view.points:
            return -1
            
        # Calculate transform parameters (same as in paintEvent)
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
        
        # Calculate centering offsets
        offset_x = (widget_width - (display_width * scale)) / 2 + curve_view.offset_x
        offset_y = (widget_height - (display_height * scale)) / 2 + curve_view.offset_y
        
        # Check distance to each point
        closest_idx = -1
        min_distance = float('inf')
        
        for i, point in enumerate(curve_view.points):
            frame, x, y = point[:3]  # Handle both regular and interpolated points
            tx, ty = CurveViewOperations.transform_point(
                curve_view, x, y, display_width, display_height, offset_x, offset_y, scale
            )
            
            # Calculate distance to mouse position
            distance = ((pos.x() - tx) ** 2 + (pos.y() - ty) ** 2) ** 0.5
            
            # Use a detection radius based on point_radius
            detection_radius = curve_view.point_radius * 2
            
            if distance <= detection_radius and distance < min_distance:
                min_distance = distance
                closest_idx = i
                
        return closest_idx

    @staticmethod
    def set_curve_data(curve_view, curve_data):
        """Set curve data for the view.
        
        Args:
            curve_view: The curve view instance
            curve_data: List of points in format [(frame, x, y), ...] or [(frame, x, y, status), ...]
        """
        curve_view.points = curve_data
        curve_view.update()
    
    @staticmethod
    def set_selected_indices(curve_view, indices):
        """Set selected point indices.
        
        Args:
            curve_view: The curve view instance
            indices: List of indices to select
        """
        curve_view.selected_points = set(indices)
        if indices:
            curve_view.selected_point_idx = indices[0]  # Set first selected as current
        else:
            curve_view.selected_point_idx = -1
        curve_view.update()
    
    @staticmethod
    def change_nudge_increment(curve_view, increase=True):
        """Change the nudge increment for point movement.
        
        Args:
            curve_view: The curve view instance
            increase: If True, increase the increment, otherwise decrease it
            
        Returns:
            float: The new nudge increment value
        """
        if not hasattr(curve_view, 'available_increments') or not hasattr(curve_view, 'current_increment_index'):
            return 1.0
            
        # Get the current index and available increments
        current_idx = curve_view.current_increment_index
        increments = curve_view.available_increments
        
        # Calculate new index with bounds checking
        if increase:
            new_idx = min(current_idx + 1, len(increments) - 1)
        else:
            new_idx = max(current_idx - 1, 0)
            
        # Update the index and increment value
        curve_view.current_increment_index = new_idx
        curve_view.nudge_increment = increments[new_idx]
        
        return curve_view.nudge_increment
    
    @staticmethod
    def nudge_selected_points(curve_view, dx=0, dy=0):
        """Nudge selected points by the specified delta.
        
        Args:
            curve_view: The curve view instance
            dx: Delta x to apply
            dy: Delta y to apply
            
        Returns:
            bool: True if any points were nudged, False otherwise
        """
        if not hasattr(curve_view, 'selected_points') or not curve_view.selected_points:
            return False
            
        # Apply the nudge increment
        actual_dx = dx * curve_view.nudge_increment
        actual_dy = dy * curve_view.nudge_increment
        
        # Track if any points were modified
        modified = False
        
        # Update each selected point
        for idx in curve_view.selected_points:
            if 0 <= idx < len(curve_view.points):
                point = curve_view.points[idx]
                frame, x, y = point[:3]  # Handle both regular and interpolated points
                
                # Calculate new position
                new_x = x + actual_dx
                new_y = y + actual_dy
                
                # Update the point
                modified = CurveViewOperations.update_point_position(curve_view, idx, new_x, new_y) or modified
                
                # Emit signal for the primary selected point
                if idx == curve_view.selected_point_idx:
                    curve_view.point_moved.emit(idx, new_x, new_y)
        
        # Update the view if any points were modified
        if modified:
            curve_view.update()
            
        return modified

    @staticmethod
    def extract_frame_number(curve_view, img_idx):
        """Extract frame number from the current image index.
        
        Args:
            curve_view: The curve view instance
            img_idx: The image index to extract frame number from
            
        Returns:
            int: The frame number, or img_idx if extraction fails
        """
        if img_idx < 0 or img_idx >= len(curve_view.image_filenames):
            return 0
            
        # Try to extract frame number from filename
        try:
            # Assume filename format includes frame number
            filename = curve_view.image_filenames[img_idx]
            # Extract numeric part - this is a simple implementation
            # that assumes frame numbers are digits in the filename
            import re
            matches = re.findall(r'\d+', filename)
            if matches:
                return int(matches[-1])  # Use the last number in the filename
        except Exception as e:
            print(f"Error extracting frame number: {str(e)}")
            
        # Fallback to using the image index itself
        return img_idx
    
    @staticmethod
    def find_closest_point_by_frame(curve_view, frame_num):
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
    def handle_mouse_press(curve_view, event):
        """Handle mouse press event for curve views.
        
        Args:
            curve_view: The curve view instance
            event: The mouse event
        """
        if event.button() == Qt.LeftButton:
            # Check if Shift is pressed for multi-selection rectangle
            if event.modifiers() & Qt.ShiftModifier:
                curve_view.selection_start = event.pos()
                curve_view.selection_rect = QRect(curve_view.selection_start, curve_view.selection_start)
                curve_view.update()
                return
                
            # Calculate transform parameters
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
            offset_x = (widget_width - (display_width * scale)) / 2 + curve_view.offset_x
            offset_y = (widget_height - (display_height * scale)) / 2 + curve_view.offset_y

            curve_view.drag_active = False
            
            # Check if Ctrl is pressed for multi-selection
            ctrl_pressed = event.modifiers() & Qt.ControlModifier
            
            # Find if we clicked on a point
            clicked_on_point = False
            for i, point in enumerate(curve_view.points):
                frame, x, y = point[:3]  # Extract only frame, x, y even if there's a status
                tx, ty = CurveViewOperations.transform_point(curve_view, x, y, display_width, display_height, offset_x, offset_y, scale)
                
                # Check if within radius
                dx = event.x() - tx
                dy = event.y() - ty
                dist = math.sqrt(dx * dx + dy * dy)
                
                if dist <= curve_view.point_radius + 2:  # +2 for better selection
                    clicked_on_point = True
                    
                    if ctrl_pressed:
                        # Add/remove from multi-selection
                        if i in curve_view.selected_points:
                            curve_view.selected_points.remove(i)
                        else:
                            curve_view.selected_points.add(i)
                            curve_view.selected_point_idx = i  # Also make it primary selection
                    else:
                        # If Ctrl is not pressed, clear selection before selecting this point
                        if not ctrl_pressed:
                            curve_view.selected_points.clear()
                        
                        curve_view.selected_point_idx = i
                        curve_view.selected_points.add(i)
                        curve_view.drag_active = True
                        
                    curve_view.point_selected.emit(i)
                    break
            
            # If clicked on empty space and not using Ctrl for multi-select, clear selection
            if not clicked_on_point and not ctrl_pressed:
                curve_view.selected_points.clear()
                curve_view.selected_point_idx = -1
                
            curve_view.update()
                
        elif event.button() == Qt.MiddleButton:
            # Middle click for panning
            curve_view.pan_start_x = event.x()
            curve_view.pan_start_y = event.y()
            curve_view.initial_offset_x = curve_view.offset_x
            curve_view.initial_offset_y = curve_view.offset_y

    @staticmethod
    def handle_mouse_move(curve_view, event):
        """Handle mouse movement for dragging points or panning.
        
        Args:
            curve_view: The curve view instance
            event: The mouse event
        """
        # Handle selection rectangle
        if curve_view.selection_start is not None:
            curve_view.selection_rect = QRect(curve_view.selection_start, event.pos()).normalized()
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
        offset_x = (widget_width - (display_width * scale)) / 2 + curve_view.offset_x
        offset_y = (widget_height - (display_height * scale)) / 2 + curve_view.offset_y
        
        if curve_view.drag_active and curve_view.selected_point_idx >= 0:
            # Get the point we're dragging
            point_data = CurveViewOperations.get_point_data(curve_view, curve_view.selected_point_idx)
            if not point_data:
                return
                
            frame, x, y, status = point_data
            
            # Convert from widget coordinates back to track coordinates
            if curve_view.background_image and curve_view.scale_to_image:
                # First convert to image coordinates
                img_x_with_scale = (event.x() - offset_x) / scale
                
                if curve_view.flip_y_axis:
                    img_y_with_scale = display_height - ((event.y() - offset_y) / scale)
                else:
                    img_y_with_scale = (event.y() - offset_y) / scale
                
                # Remove manual offset
                img_x = img_x_with_scale - curve_view.x_offset
                img_y = img_y_with_scale - curve_view.y_offset
                
                # Convert from image coordinates to track coordinates
                new_x = img_x / (display_width / curve_view.image_width)
                new_y = img_y / (display_height / curve_view.image_height)
            else:
                # Direct conversion from widget to track coordinates
                new_x = (event.x() - offset_x) / scale
                
                if curve_view.flip_y_axis:
                    new_y = curve_view.image_height - ((event.y() - offset_y) / scale)
                else:
                    new_y = (event.y() - offset_y) / scale
            
            # Update point, preserving interpolated status
            CurveViewOperations.update_point_position(curve_view, curve_view.selected_point_idx, new_x, new_y)
            
            # Emit signal
            curve_view.point_moved.emit(curve_view.selected_point_idx, new_x, new_y)
            
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
    def handle_mouse_release(curve_view, event):
        """Handle mouse release event for curve views.
        
        Args:
            curve_view: The curve view instance
            event: The mouse event
        """
        if event.button() == Qt.LeftButton:
            curve_view.drag_active = False
            
            # Handle selection rectangle if it exists (for enhanced curve view)
            if hasattr(curve_view, 'selection_start') and curve_view.selection_start is not None:
                if hasattr(curve_view, 'finalize_selection'):
                    curve_view.finalize_selection()
                curve_view.selection_start = None
                curve_view.selection_rect = None
                curve_view.update()

    @staticmethod
    def select_all_points(curve_view):
        """Select all points in the curve.
        
        Args:
            curve_view: The curve view instance
        """
        if not curve_view.points:
            return
            
        curve_view.selected_points = set(range(len(curve_view.points)))
        if curve_view.points:
            curve_view.selected_point_idx = 0
            
        curve_view.update()
    
    @staticmethod
    def clear_selection(curve_view):
        """Clear all point selections.
        
        Args:
            curve_view: The curve view instance
        """
        curve_view.selected_points.clear()
        curve_view.selected_point_idx = -1
        curve_view.update()
    
    @staticmethod
    def select_point_by_index(curve_view, index):
        """Select a point by its index.
        
        Args:
            curve_view: The curve view instance
            index: The index of the point to select
        
        Returns:
            bool: True if selection was successful, False otherwise
        """
        if not curve_view.points or index < 0 or index >= len(curve_view.points):
            return False
            
        curve_view.selected_point_idx = index
        curve_view.selected_points = {index}
        curve_view.point_selected.emit(index)
        curve_view.update()
        return True
        
    @staticmethod
    def select_all_points(main_window):
        """Select all points in the view.
        
        Args:
            main_window: The main window containing the curve view
        """
        if hasattr(main_window.curve_view, 'selectAllPoints'):
            main_window.curve_view.selectAllPoints()
            main_window.statusBar().showMessage(f"Selected all {len(main_window.curve_data)} points", 3000)
    
    @staticmethod
    def deselect_all_points(main_window):
        """Deselect all points.
        
        Args:
            main_window: The main window containing the curve view
        """
        if hasattr(main_window.curve_view, 'clearSelection'):
            main_window.curve_view.clearSelection()
            main_window.statusBar().showMessage("Cleared selection", 2000)
    
    @staticmethod
    def delete_selected_points(main_window, show_confirmation=False):
        """Delete selected points from the curve.
        
        Args:
            main_window: The main window containing the curve data and view
            show_confirmation: Whether to show a confirmation dialog
        """
        # Get selected points
        if not hasattr(main_window.curve_view, 'selected_points') or not main_window.curve_view.selected_points:
            return
            
        # Save the view state before any changes
        view = main_window.curve_view
        view_state = {
            'zoom_factor': view.zoom_factor,
            'offset_x': view.offset_x,
            'offset_y': view.offset_y,
            'x_offset': view.x_offset,
            'y_offset': view.y_offset
        }
