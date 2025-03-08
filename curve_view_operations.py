#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Curve view operations for 3DE4 Curve Editor.
Provides functions for manipulating the curve view and handling point updates.
"""

from PySide6.QtWidgets import QMessageBox


class CurveViewOperations:
    """Curve view operations for the 3DE4 Curve Editor."""
    
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
