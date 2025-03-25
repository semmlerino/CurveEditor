#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Visualization operations for 3DE4 Curve Editor.
Provides functionality for curve visualization features like grid, vectors, and crosshair display.
"""

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt
import os

class VisualizationOperations:
    """Static utility methods for visualization operations in the curve editor."""
    
    @staticmethod
    def toggle_grid(main_window, checked):
        """Toggle grid visibility.
        
        Args:
            main_window: The main application window
            checked: Boolean indicating if grid should be shown
        """
        if hasattr(main_window.curve_view, 'toggleGrid'):
            main_window.curve_view.toggleGrid(checked)
            main_window.toggle_grid_button.setChecked(checked)
    
    @staticmethod
    def toggle_velocity_vectors(main_window, checked):
        """Toggle velocity vector display.
        
        Args:
            main_window: The main application window
            checked: Boolean indicating if vectors should be shown
        """
        if hasattr(main_window.curve_view, 'toggleVelocityVectors'):
            main_window.curve_view.toggleVelocityVectors(checked)
            main_window.toggle_vectors_button.setChecked(checked)
    
    @staticmethod
    def toggle_all_frame_numbers(main_window, checked):
        """Toggle display of all frame numbers.
        
        Args:
            main_window: The main application window
            checked: Boolean indicating if frame numbers should be shown
        """
        if hasattr(main_window.curve_view, 'toggleAllFrameNumbers'):
            main_window.curve_view.toggleAllFrameNumbers(checked)
            main_window.toggle_frame_numbers_button.setChecked(checked)
    
    @staticmethod
    def toggle_crosshair(main_window, checked):
        """Toggle crosshair visibility.
        
        Args:
            main_window: The main application window
            checked: Boolean indicating if crosshair should be shown
        """
        if hasattr(main_window.curve_view, 'toggleCrosshair'):
            main_window.curve_view.toggleCrosshair(checked)
            if hasattr(main_window, 'toggle_crosshair_button'):
                main_window.toggle_crosshair_button.setChecked(checked)
                
    @staticmethod
    def toggle_background_visible(main_window, visible):
        """Toggle visibility of background image.
        
        Args:
            main_window: The main application window
            visible: Boolean indicating if background should be shown
        """
        if hasattr(main_window.curve_view, 'toggleBackgroundVisible'):
            main_window.curve_view.toggleBackgroundVisible(visible)
            
    @staticmethod
    def toggle_background_visible_internal(curve_view, visible):
        """Toggle visibility of background image (internal implementation).
        
        Args:
            curve_view: The curve view instance
            visible: Boolean indicating if background should be shown
        """
        curve_view.show_background = visible
        curve_view.update()
        
    @staticmethod
    def set_background_opacity(curve_view, opacity):
        """Set the opacity of the background image.
        
        Args:
            curve_view: The curve view instance
            opacity: Opacity value between 0.0 and 1.0
        """
        curve_view.background_opacity = max(0.0, min(1.0, opacity))
        curve_view.update()
    
    @staticmethod
    def toggle_fullscreen(main_window):
        """Toggle fullscreen mode for the main window.
        
        Args:
            main_window: The main application window
        """
        if main_window.isFullScreen():
            main_window.showNormal()
            if hasattr(main_window, 'status_bar'):
                main_window.status_bar.showMessage("Exited fullscreen mode", 2000)
            elif hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage("Exited fullscreen mode", 2000)
        else:
            main_window.showFullScreen()
            if hasattr(main_window, 'status_bar'):
                main_window.status_bar.showMessage("Entered fullscreen mode (press F11 to exit)", 3000)
            elif hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage("Entered fullscreen mode (press F11 to exit)", 3000)
    
    @staticmethod
    def center_on_selected_point(curve_view, point_idx=-1, preserve_zoom=True):
        """Center the view on the specified point index.
        
        If no index is provided, uses the currently selected point.
        
        Args:
            curve_view: The curve view instance
            point_idx: Index of point to center on. Default -1 uses selected point.
            preserve_zoom: If True, maintain current zoom level. If False, reset view.
            
        Returns:
            bool: True if centering was successful, False otherwise
        """
        # Use provided index or current selection
        idx = point_idx if point_idx >= 0 else curve_view.selected_point_idx
        
        if idx < 0 or not hasattr(curve_view, 'main_window') or not curve_view.main_window.curve_data:
            return False
            
        try:
            # Get the point to center on
            if idx < len(curve_view.main_window.curve_data):
                # Extract point coordinates
                point = curve_view.main_window.curve_data[idx]
                _, x, y = point[:3]  # Extract only frame, x, y even if there's a status
                print(f"VisualizationOperations: Centering on point {idx} at ({x}, {y})")
                
                # Set this as the selected point
                curve_view.selected_point_idx = idx
                
                # Store current zoom factor if we're preserving zoom
                current_zoom = curve_view.zoom_factor if preserve_zoom else 1.0
                
                # Reset zoom and positioning to default if not preserving zoom
                if not preserve_zoom:
                    VisualizationOperations.reset_view(curve_view)
                
                # Get the point coordinates in widget space after reset
                widget_width = curve_view.width()
                widget_height = curve_view.height()
                
                # Calculate the transform that would be applied in paintEvent
                display_width = curve_view.image_width
                display_height = curve_view.image_height
                if curve_view.background_image:
                    display_width = curve_view.background_image.width()
                    display_height = curve_view.background_image.height()
                
                # Calculate scale to fit in the widget
                scale_x = widget_width / display_width
                scale_y = widget_height / display_height
                
                # Apply the preserved zoom if requested
                if preserve_zoom:
                    scale = min(scale_x, scale_y) * current_zoom
                else:
                    scale = min(scale_x, scale_y) * curve_view.zoom_factor
                
                # Calculate centering offsets for the image
                offset_x = (widget_width - (display_width * scale)) / 2
                offset_y = (widget_height - (display_height * scale)) / 2
                
                # Transform the point using the same logic as in paintEvent
                if curve_view.scale_to_image:
                    # Scale the tracking coordinates to match the image size
                    img_x = x * (display_width / curve_view.image_width)
                    img_y = y * (display_height / curve_view.image_height)
                    
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
                
                # Calculate the offset needed to center this point
                center_x = widget_width / 2
                center_y = widget_height / 2
                
                # The offset needed is the difference between where the point is
                # and where we want it to be (at the center)
                delta_x = center_x - tx
                delta_y = center_y - ty
                
                # Apply the offset
                curve_view.offset_x = delta_x
                curve_view.offset_y = delta_y
                
                print(f"VisualizationOperations: Point transforms to ({tx}, {ty})")
                print(f"VisualizationOperations: Center is at ({center_x}, {center_y})")
                print(f"VisualizationOperations: Applied offset of ({delta_x}, {delta_y})")
                
                # Update the view to apply new transforms
                curve_view.update()
                return True
            else:
                print(f"VisualizationOperations: Point index {idx} out of range")
                return False
        except Exception as e:
            print(f"VisualizationOperations: Error centering on point: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    @staticmethod
    def center_on_selected_point_from_main_window(main_window):
        """Center the view on the currently selected point from the main window context.
        
        Args:
            main_window: The main application window
        """
        if not hasattr(main_window.curve_view, 'centerOnSelectedPoint'):
            main_window.statusBar().showMessage("Center on point not supported in basic view mode", 2000)
            return
        
        # Check first if we have selected points in the curve view
        if hasattr(main_window.curve_view, 'selected_points') and main_window.curve_view.selected_points:
            # Use the first selected point from the curve view's selection
            point_idx = list(main_window.curve_view.selected_points)[0]
            main_window.curve_view.centerOnSelectedPoint(point_idx)
            main_window.statusBar().showMessage(f"Centered view on point {point_idx}", 2000)
            return
            
        # Fallback to main_window.selected_indices
        if hasattr(main_window, 'selected_indices') and main_window.selected_indices:
            # Use the first selected point if multiple are selected
            point_idx = main_window.selected_indices[0]
            main_window.curve_view.centerOnSelectedPoint(point_idx)
            main_window.statusBar().showMessage(f"Centered view on point {point_idx}", 2000)
            return
            
        # If we get here, no point is selected
        main_window.statusBar().showMessage("No point selected to center on", 2000)
        
    @staticmethod
    def reset_view(curve_view):
        """Reset view to default state (zoom and position).
        
        Args:
            curve_view: The curve view instance to reset
        """
        # Reset zoom factor
        curve_view.zoom_factor = 1.0
        
        # Reset offsets
        if hasattr(curve_view, 'x_offset'):
            curve_view.x_offset = 0
        if hasattr(curve_view, 'y_offset'):
            curve_view.y_offset = 0
        if hasattr(curve_view, 'offset_x'):
            curve_view.offset_x = 0
        if hasattr(curve_view, 'offset_y'):
            curve_view.offset_y = 0
            
        # Update the view
        curve_view.update()
        
    @staticmethod
    def zoom_view(curve_view, factor, mouse_x=None, mouse_y=None):
        """Zoom the view while keeping the selected point centered.
        
        Args:
            curve_view: The curve view instance
            factor: Zoom factor (> 1 to zoom in, < 1 to zoom out)
            mouse_x: X-coordinate to zoom around, if None uses center
            mouse_y: Y-coordinate to zoom around, if None uses center
        """
        # Store previous zoom to check if centering is needed
        old_zoom = curve_view.zoom_factor
        
        # Apply new zoom factor with limits
        curve_view.zoom_factor = max(0.1, min(50.0, curve_view.zoom_factor * factor))
        
        # If mouse coordinates are provided, zoom around that point
        if mouse_x is not None and mouse_y is not None:
            widget_width = curve_view.width()
            widget_height = curve_view.height()
            
            # Calculate how much the coordinates will change due to zoom
            zoom_ratio = factor - 1.0
            
            # Calculate distance from mouse to center
            center_x = widget_width / 2
            center_y = widget_height / 2
            dx = mouse_x - center_x
            dy = mouse_y - center_y
            
            # Adjust offset to keep mouse position fixed
            curve_view.offset_x -= dx * zoom_ratio
            curve_view.offset_y -= dy * zoom_ratio
        # If no mouse coordinates, but we have a selected point, center on it
        elif hasattr(curve_view, 'selected_point_idx') and curve_view.selected_point_idx >= 0:
            # Use the existing method which already handles transformations correctly
            VisualizationOperations.center_on_selected_point(curve_view, curve_view.selected_point_idx, preserve_zoom=True)
        
        # Update the view
        curve_view.update()
        
    @staticmethod
    def pan_view(curve_view, dx, dy):
        """Pan the view by the specified delta.
        
        Args:
            curve_view: The curve view instance
            dx: Change in x position
            dy: Change in y position
        """
        # Apply the pan offset
        curve_view.offset_x += dx
        curve_view.offset_y += dy
        
        # Update the view
        curve_view.update()
    
    @staticmethod
    def toggle_grid_internal(curve_view, enabled=None):
        """Toggle grid visibility with optional explicit state.
        
        Args:
            curve_view: The curve view instance
            enabled: Boolean to explicitly set state, or None to toggle
        """
        if enabled is None:
            curve_view.show_grid = not curve_view.show_grid
        else:
            curve_view.show_grid = enabled
        curve_view.update()
        
    @staticmethod
    def toggle_velocity_vectors_internal(curve_view, enabled):
        """Toggle velocity vector display (internal implementation).
        
        Args:
            curve_view: The curve view instance
            enabled: Boolean indicating if vectors should be shown
        """
        curve_view.show_velocity_vectors = enabled
        curve_view.update()
        
    @staticmethod
    def toggle_all_frame_numbers_internal(curve_view, enabled):
        """Toggle display of all frame numbers (internal implementation).
        
        Args:
            curve_view: The curve view instance
            enabled: Boolean indicating if frame numbers should be shown
        """
        curve_view.show_all_frame_numbers = enabled
        curve_view.update()
        
    @staticmethod
    def toggle_crosshair_internal(curve_view, enabled):
        """Toggle crosshair visibility (internal implementation).
        
        Args:
            curve_view: The curve view instance
            enabled: Boolean indicating if crosshair should be shown
        """
        curve_view.show_crosshair = enabled
        curve_view.update()
    
    @staticmethod
    def set_point_radius(curve_view, radius):
        """Set the radius for points in the curve view.
        
        Args:
            curve_view: The curve view instance
            radius: Point radius in pixels
        """
        curve_view.point_radius = max(1, radius)  # Ensure minimum size of 1
        curve_view.update()
        
    @staticmethod
    def set_grid_color(curve_view, color):
        """Set the color of the grid lines.
        
        Args:
            curve_view: The curve view instance
            color: QColor for the grid lines
        """
        from PySide6.QtGui import QColor
        
        if isinstance(color, QColor):
            curve_view.grid_color = color
            curve_view.update()
        else:
            print("Error: Grid color must be a QColor instance")
            
    @staticmethod
    def set_grid_line_width(curve_view, width):
        """Set the width of grid lines.
        
        Args:
            curve_view: The curve view instance
            width: Width in pixels
        """
        curve_view.grid_line_width = max(1, width)  # Ensure minimum width of 1
        curve_view.update()
        
    @staticmethod
    def update_timeline_for_image(main_window, index):
        """Update the timeline for the current image.
        
        This method extracts the frame number from an image filename and updates
        the timeline slider and related UI elements to match the current image.
        It also selects the point in the curve data that corresponds to the frame.
        
        Args:
            main_window: The main application window
            index: Index of the current image in the image_filenames list
        """
        try:
            if not hasattr(main_window, 'image_filenames') or not main_window.image_filenames:
                print("update_timeline_for_image: No image filenames available")
                return
                
            if index < 0 or index >= len(main_window.image_filenames):
                print(f"update_timeline_for_image: Invalid index {index}")
                return
        
            # Extract frame number
            filename = os.path.basename(main_window.image_filenames[index])
            import re
            frame_match = re.search(r'(\d+)', filename)
            if not frame_match:
                print(f"update_timeline_for_image: Could not extract frame from {filename}")
                return
                
            frame_num = int(frame_match.group(1))
            print(f"update_timeline_for_image: Extracted frame {frame_num} from {filename}")
            
            # Update timeline directly
            if hasattr(main_window, 'timeline_slider'):
                main_window.timeline_slider.blockSignals(True)
                main_window.timeline_slider.setValue(frame_num)
                main_window.timeline_slider.blockSignals(False)
                print(f"update_timeline_for_image: Updated timeline to frame {frame_num}")
            
            # Update frame marker position if it exists
            VisualizationOperations.update_frame_marker_position(main_window, frame_num)
            
            # Find and update selected point
            if hasattr(main_window, 'curve_data') and main_window.curve_data:
                closest_frame = min(main_window.curve_data, key=lambda point: abs(point[0] - frame_num))[0]
                
                for i, point in enumerate(main_window.curve_data):
                    if point[0] == closest_frame:
                        # Update selection
                        if hasattr(main_window.curve_view, 'selected_point_idx'):
                            main_window.curve_view.selected_point_idx = i
                            main_window.curve_view.update()
                            print(f"update_timeline_for_image: Updated selected point to {i}")
                        break
        except Exception as e:
            print(f"update_timeline_for_image: Error updating timeline: {str(e)}")

    @staticmethod
    def update_frame_marker_position(main_window, frame):
        """Update the position of the frame marker based on current frame.
        
        Args:
            main_window: The main window instance
            frame: The current frame number
        """
        # Update the marker position if it exists
        if hasattr(main_window, 'frame_marker_label'):
            # Calculate position based on frame
            if hasattr(main_window, 'timeline_slider'):
                slider = main_window.timeline_slider
                min_frame = slider.minimum()
                max_frame = slider.maximum()
                
                # Only update if we have a valid range
                if max_frame > min_frame:
                    frame_range = max_frame - min_frame
                    # Ensure the frame is within valid range
                    current_frame = max(min_frame, min(max_frame, frame))
                    # Update the tooltip to show the current frame
                    main_window.frame_marker_label.setToolTip(f"Frame: {current_frame}")

    @staticmethod
    def set_points(curve_view, points, image_width, image_height, preserve_view=False):
        """Set the points to display and adjust view accordingly.
        
        Args:
            curve_view: The curve view instance
            points: List of points in format [(frame, x, y), ...] or [(frame, x, y, status), ...]
            image_width: Width of the image/workspace
            image_height: Height of the image/workspace
            preserve_view: If True, maintain current view position
        """
        # Store current view state if preserving view
        view_state = None
        if preserve_view:
            view_state = {
                'zoom_factor': curve_view.zoom_factor,
                'offset_x': curve_view.offset_x,
                'offset_y': curve_view.offset_y,
                'x_offset': curve_view.x_offset if hasattr(curve_view, 'x_offset') else 0,
                'y_offset': curve_view.y_offset if hasattr(curve_view, 'y_offset') else 0
            }
            
        # Update data
        curve_view.points = points
        curve_view.image_width = image_width
        curve_view.image_height = image_height
        
        # Reset view if not preserving
        if not preserve_view:
            VisualizationOperations.reset_view(curve_view)
        else:
            # Restore view state
            if view_state:
                curve_view.zoom_factor = view_state['zoom_factor']
                curve_view.offset_x = view_state['offset_x']
                curve_view.offset_y = view_state['offset_y']
                if hasattr(curve_view, 'x_offset'):
                    curve_view.x_offset = view_state['x_offset']
                if hasattr(curve_view, 'y_offset'):
                    curve_view.y_offset = view_state['y_offset']
            
        curve_view.update()
    
    @staticmethod
    def handle_key_press(curve_view, event):
        """Handle key press events for visualization controls.
        
        Args:
            curve_view: The curve view instance
            event: The key press event
            
        Returns:
            bool: True if the event was handled, False otherwise
        """
        # Handle visualization toggle keys
        handled = True
        
        if event.key() == Qt.Key_G:
            curve_view.show_grid = not curve_view.show_grid
            curve_view.update()
        elif event.key() == Qt.Key_V:
            curve_view.show_velocity_vectors = not curve_view.show_velocity_vectors
            curve_view.update()
        elif event.key() == Qt.Key_F:
            curve_view.show_all_frame_numbers = not curve_view.show_all_frame_numbers
            curve_view.update()
        elif event.key() == Qt.Key_X:
            curve_view.show_crosshair = not curve_view.show_crosshair
            curve_view.update()
        elif event.key() == Qt.Key_B:
            curve_view.show_background = not curve_view.show_background
            curve_view.update()
        elif event.key() == Qt.Key_Y:
            curve_view.flip_y_axis = not curve_view.flip_y_axis
            curve_view.update()
        elif event.key() == Qt.Key_S:
            curve_view.scale_to_image = not curve_view.scale_to_image
            curve_view.update()
        elif event.key() == Qt.Key_R:
            curve_view.resetView()
            curve_view.x_offset = 0
            curve_view.y_offset = 0
            curve_view.update()
        # Handle new frame navigation key presses
        elif event.key() == Qt.Key_Period:  # Next frame
            if hasattr(curve_view, 'main_window'):
                from ui_components import UIComponents
                UIComponents.next_frame(curve_view.main_window)
            else:
                handled = False
        elif event.key() == Qt.Key_Comma:  # Previous frame
            if hasattr(curve_view, 'main_window'):
                from ui_components import UIComponents
                UIComponents.prev_frame(curve_view.main_window)
            else:
                handled = False
        elif event.key() == Qt.Key_Home:  # First frame
            if hasattr(curve_view, 'main_window'):
                from ui_components import UIComponents
                UIComponents.go_to_first_frame(curve_view.main_window)
            else:
                handled = False
        elif event.key() == Qt.Key_End:  # Last frame
            if hasattr(curve_view, 'main_window'):
                from ui_components import UIComponents
                UIComponents.go_to_last_frame(curve_view.main_window)
            else:
                handled = False
        else:
            handled = False
            
        return handled

    @staticmethod
    def jump_to_frame_by_click(main_window, position):
        """Jump to a specific frame based on click position on timeline.
        
        Args:
            main_window: The main application window
            position: Click position (QPoint)
            
        Returns:
            bool: True if successfully jumped to frame, False otherwise
        """
        if not hasattr(main_window, 'timeline_slider'):
            return False
            
        slider = main_window.timeline_slider
        min_frame = slider.minimum()
        max_frame = slider.maximum()
        
        # Calculate the frame based on position
        slider_width = slider.width()
        if slider_width <= 0:
            return False
            
        # Calculate the frame corresponding to the click position
        relative_pos = max(0, min(position.x(), slider_width)) / slider_width
        frame = int(min_frame + (max_frame - min_frame) * relative_pos)
        
        # Set the slider value
        slider.setValue(frame)
        
        # Update the frame marker position
        VisualizationOperations.update_frame_marker_position(main_window, frame)
        
        # Update status bar
        if hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage(f"Jumped to frame {frame}", 2000)
            
        return True