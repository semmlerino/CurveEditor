#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, Signal, Slot
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QFont, QImage, QPixmap, QBrush


class CurveView(QWidget):
    """Widget for displaying and editing the 2D tracking curve."""
    
    point_moved = Signal(int, float, float)  # Signal emitted when a point is moved
    point_selected = Signal(int)  # Signal emitted when a point is selected
    image_changed = Signal(int)  # Signal emitted when image changes via keyboard
    
    def __init__(self, parent=None):
        super(CurveView, self).__init__(parent)
        self.setMinimumSize(800, 600)
        self.points = []
        self.selected_point_idx = -1
        self.drag_active = False
        self.zoom_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.image_width = 1920  # Default, will be updated when data is loaded
        self.image_height = 1080  # Default, will be updated when data is loaded
        self.setMouseTracking(True)
        self.point_radius = 5
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Image sequence support
        self.background_image = None
        self.image_sequence_path = ""
        self.image_filenames = []
        self.current_image_idx = -1
        self.show_background = True
        self.background_opacity = 0.7  # 0.0 to 1.0
        
        # Debug options
        self.debug_mode = True  # Enable debug visuals
        self.flip_y_axis = True  # Toggle Y-axis flip
        self.scale_to_image = True  # Automatically scale track data to match image dimensions
        self.x_offset = 0  # Manual X offset for fine-tuning alignment
        self.y_offset = 0  # Manual Y offset for fine-tuning alignment
        
    def setPoints(self, points, image_width, image_height):
        """Set the points to display and adjust view accordingly."""
        self.points = points
        self.image_width = image_width
        self.image_height = image_height
        self.resetView()
        self.update()
        
    def setImageSequence(self, path, filenames):
        """Set the image sequence to display as background."""
        self.image_sequence_path = path
        self.image_filenames = filenames
        self.current_image_idx = 0 if filenames else -1
        self.loadCurrentImage()
        self.update()
        
    def setCurrentImageByFrame(self, frame):
        """Set the current background image based on frame number."""
        if not self.image_filenames:
            return
            
        # Find the closest image index to the requested frame
        closest_idx = -1
        min_diff = float('inf')
        
        for i, filename in enumerate(self.image_filenames):
            # Try to extract frame number from filename
            try:
                # Common formats: name.####.ext or name_####.ext
                parts = os.path.basename(filename).split('.')
                if len(parts) >= 2 and parts[-2].isdigit():
                    img_frame = int(parts[-2])
                else:
                    # Try underscore format
                    name_parts = parts[0].split('_')
                    if name_parts[-1].isdigit():
                        img_frame = int(name_parts[-1])
                    else:
                        # Just use sequential index if can't parse frame
                        img_frame = i
            except:
                img_frame = i
                
            diff = abs(img_frame - frame)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
                
        if closest_idx >= 0 and closest_idx < len(self.image_filenames):
            self.current_image_idx = closest_idx
            self.loadCurrentImage()
            self.update()
            
    def setCurrentImageByIndex(self, index):
        """Set the current background image by sequence index."""
        if not self.image_filenames or index < 0 or index >= len(self.image_filenames):
            return
            
        self.current_image_idx = index
        self.loadCurrentImage()
        self.update()
        
    def toggleBackgroundVisible(self, visible):
        """Toggle visibility of background image."""
        self.show_background = visible
        self.update()
        
    def setBackgroundOpacity(self, opacity):
        """Set the opacity of the background image."""
        self.background_opacity = max(0.0, min(1.0, opacity))
        self.update()
        
    def loadCurrentImage(self):
        """Load the current image in the sequence."""
        if self.current_image_idx < 0 or not self.image_filenames:
            self.background_image = None
            return
            
        try:
            filename = os.path.join(self.image_sequence_path, self.image_filenames[self.current_image_idx])
            image = QImage(filename)
            if not image.isNull():
                self.background_image = image
                # Update track dimensions to match image dimensions
                if self.scale_to_image:
                    self.image_width = image.width()
                    self.image_height = image.height()
            else:
                self.background_image = None
        except Exception as e:
            print(f"Error loading image: {str(e)}")
            self.background_image = None
            
    def resetView(self):
        """Reset view to show all points."""
        from visualization_operations import VisualizationOperations
        VisualizationOperations.reset_view(self)
        
    def paintEvent(self, event):
        """Draw the curve and points."""
        if not self.points and not self.background_image:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        
        # Get widget dimensions
        widget_width = self.width()
        widget_height = self.height()
        
        # Use the background image dimensions if available, otherwise use track dimensions
        display_width = self.image_width
        display_height = self.image_height
        
        if self.background_image:
            display_width = self.background_image.width()
            display_height = self.background_image.height()
        
        # Calculate the scale factor to fit in the widget
        scale_x = widget_width / display_width 
        scale_y = widget_height / display_height
        
        # Use uniform scaling to maintain aspect ratio
        scale = min(scale_x, scale_y) * self.zoom_factor
        
        # Calculate centering offsets
        offset_x = (widget_width - (display_width * scale)) / 2 + self.offset_x
        offset_y = (widget_height - (display_height * scale)) / 2 + self.offset_y

        # CRITICAL FIX - Simple direct transformation that doesn't try to normalize
        def transform_point(x, y):
            # Scale directly from track coordinates to image space
            # This works when both are the same aspect ratio but different resolution
            if self.background_image and self.scale_to_image:
                # Scale the tracking coordinates to match the image size
                img_x = x * (display_width / self.image_width) + self.x_offset
                img_y = y * (display_height / self.image_height) + self.y_offset
                
                # Scale to widget space
                tx = offset_x + img_x * scale
                
                # Apply Y-flip if enabled
                if self.flip_y_axis:
                    ty = offset_y + (display_height - img_y) * scale
                else:
                    ty = offset_y + img_y * scale
            else:
                # Direct scaling with no image-based transformation
                tx = offset_x + x * scale
                
                # Apply Y-flip if enabled
                if self.flip_y_axis:
                    ty = offset_y + (self.image_height - y) * scale
                else:
                    ty = offset_y + y * scale
                    
            return tx, ty
            
        # Draw background image if available
        if self.show_background and self.background_image:
            # Calculate scaled dimensions
            scaled_width = display_width * scale
            scaled_height = display_height * scale
            
            # Position image
            img_x = offset_x
            img_y = offset_y
            
            # Draw the image
            pixmap = QPixmap.fromImage(self.background_image)
            painter.setOpacity(self.background_opacity)
            painter.drawPixmap(int(img_x), int(img_y), int(scaled_width), int(scaled_height), pixmap)
            painter.setOpacity(1.0)
            
            # Debugging visuals
            if self.debug_mode:
                # Show alignment info
                painter.setPen(QPen(QColor(255, 100, 100), 1))
                painter.drawText(10, 100, f"Manual Alignment: X-offset: {self.x_offset}, Y-offset: {self.y_offset}")
                painter.drawText(10, 120, f"Adjust with arrow keys + Shift/Ctrl")
        
        # Draw the main curve if available
        if self.points:
            # Set pen for the curve
            curve_pen = QPen(QColor(0, 160, 230), 2)
            painter.setPen(curve_pen)
            
            # Create path for the curve
            path = QPainterPath()
            first_point = True
            
            for frame, x, y in self.points:
                tx, ty = transform_point(x, y)
                
                if first_point:
                    path.moveTo(tx, ty)
                    first_point = False
                else:
                    path.lineTo(tx, ty)
            
            # Draw the curve
            painter.drawPath(path)
            
            # Draw points
            for i, pt in enumerate(self.points):
                # Support both (frame, x, y) and (frame, x, y, status)
                if len(pt) == 4 and pt[3] == 'interpolated':
                    frame, x, y, _ = pt
                    is_interpolated = True
                else:
                    frame, x, y = pt[:3]
                    is_interpolated = False

                tx, ty = transform_point(x, y)

                # Highlight selected point
                if i == self.selected_point_idx:
                    painter.setPen(QPen(QColor(255, 80, 80), 2))
                    painter.setBrush(QColor(255, 80, 80, 150))
                    point_radius = self.point_radius + 2
                elif is_interpolated:
                    # Lighter, more transparent colour for interpolated points
                    painter.setPen(QPen(QColor(180, 220, 255), 1))
                    painter.setBrush(QColor(200, 230, 255, 120))
                    point_radius = self.point_radius
                else:
                    painter.setPen(QPen(QColor(200, 200, 200), 1))
                    painter.setBrush(QColor(220, 220, 220, 200))
                    point_radius = self.point_radius

                painter.drawEllipse(QPointF(tx, ty), point_radius, point_radius)
                
                # Draw frame number
                if i == self.selected_point_idx or i % 10 == 0:  # Only show some frame numbers for clarity
                    painter.setPen(QPen(QColor(200, 200, 100), 1))
                    font = painter.font()
                    font.setPointSize(8)
                    painter.setFont(font)
                    painter.drawText(int(tx) + 10, int(ty) - 10, str(frame))
        
        # Display info
        info_font = QFont("Monospace", 9)
        painter.setFont(info_font)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        
        # Show current view info
        info_text = f"Zoom: {self.zoom_factor:.2f}x | Points: {len(self.points)}"
        if self.selected_point_idx >= 0:
            frame, x, y = self.points[self.selected_point_idx]
            info_text += f" | Selected: Frame {frame}, X: {x:.2f}, Y: {y:.2f}"
            
        painter.drawText(10, 20, info_text)
        
        # Show image info if available
        if self.background_image:
            img_info = f"Image: {self.current_image_idx + 1}/{len(self.image_filenames)}"
            if self.image_filenames and self.current_image_idx >= 0:
                img_info += f" - {os.path.basename(self.image_filenames[self.current_image_idx])}"
            painter.drawText(10, 40, img_info)
            
        # Debug info
        if self.debug_mode:
            debug_info = f"Debug Mode: ON | Y-Flip: {'ON' if self.flip_y_axis else 'OFF'} | Scale to Image: {'ON' if self.scale_to_image else 'OFF'}"
            debug_info += f" | Track Dims: {self.image_width}x{self.image_height}"
            
            if self.background_image:
                debug_info += f" | Image: {self.background_image.width()}x{self.background_image.height()}"
                
            painter.drawText(10, 60, debug_info)
            
            # Display keyboard shortcuts
            shortcuts = "Shortcuts: [R] Reset View, [Y] Toggle Y-Flip, [S] Toggle Scale-to-Image"
            shortcuts += " | Arrow keys + Shift: Adjust alignment"
            painter.drawText(10, 80, shortcuts)
            
    def mousePressEvent(self, event):
        """Handle mouse press to select or move points."""
        self.setFocus()
        if not self.points:
            return
            
        if event.button() == Qt.LeftButton:
            self.drag_active = False
            self.selected_point_idx = -1
            
            # Calculate transform parameters using the same logic as in paintEvent
            widget_width = self.width()
            widget_height = self.height()
            
            # Use the background image dimensions if available, otherwise use track dimensions
            display_width = self.image_width
            display_height = self.image_height
            
            if self.background_image:
                display_width = self.background_image.width()
                display_height = self.background_image.height()
            
            # Calculate the scale factor to fit in the widget
            scale_x = widget_width / display_width
            scale_y = widget_height / display_height
            
            # Use uniform scaling to maintain aspect ratio
            scale = min(scale_x, scale_y) * self.zoom_factor
            
            # Calculate centering offsets
            offset_x = (widget_width - (display_width * scale)) / 2 + self.offset_x
            offset_y = (widget_height - (display_height * scale)) / 2 + self.offset_y

            # Use same transform function as in paintEvent
            def transform_point(x, y):
                if self.background_image and self.scale_to_image:
                    # Scale the tracking coordinates to match the image size
                    img_x = x * (display_width / self.image_width) + self.x_offset
                    img_y = y * (display_height / self.image_height) + self.y_offset
                    
                    # Scale to widget space
                    tx = offset_x + img_x * scale
                    
                    # Apply Y-flip if enabled
                    if self.flip_y_axis:
                        ty = offset_y + (display_height - img_y) * scale
                    else:
                        ty = offset_y + img_y * scale
                else:
                    # Direct scaling with no image-based transformation
                    tx = offset_x + x * scale
                    
                    # Apply Y-flip if enabled
                    if self.flip_y_axis:
                        ty = offset_y + (self.image_height - y) * scale
                    else:
                        ty = offset_y + y * scale
                        
                return tx, ty
            
            # Find if we clicked on a point
            for i, (frame, x, y) in enumerate(self.points):
                tx, ty = transform_point(x, y)
                
                # Check if within radius
                dx = event.x() - tx
                dy = event.y() - ty
                dist = math.sqrt(dx * dx + dy * dy)
                
                if dist <= self.point_radius + 2:  # +2 for better selection
                    self.selected_point_idx = i
                    self.drag_active = True
                    self.point_selected.emit(i)
                    break
            
            self.update()
        elif event.button() == Qt.MiddleButton:
            # Middle click for panning
            self.pan_start_x = event.x()
            self.pan_start_y = event.y()
            self.initial_offset_x = self.offset_x
            self.initial_offset_y = self.offset_y
            
    def mouseMoveEvent(self, event):
        """Handle mouse movement for dragging points or panning."""
        if not self.points:
            return
            
        if self.drag_active and self.selected_point_idx >= 0:
            # Get the point we're dragging
            frame, x, y = self.points[self.selected_point_idx]
            
            # Calculate transform parameters using the same logic as in paintEvent
            widget_width = self.width()
            widget_height = self.height()
            
            # Use the background image dimensions if available, otherwise use track dimensions
            display_width = self.image_width
            display_height = self.image_height
            
            if self.background_image:
                display_width = self.background_image.width()
                display_height = self.background_image.height()
            
            # Calculate the scale factor to fit in the widget
            scale_x = widget_width / display_width
            scale_y = widget_height / display_height
            
            # Use uniform scaling to maintain aspect ratio
            scale = min(scale_x, scale_y) * self.zoom_factor
            
            # Calculate centering offsets
            offset_x = (widget_width - (display_width * scale)) / 2 + self.offset_x
            offset_y = (widget_height - (display_height * scale)) / 2 + self.offset_y
            
            # Convert from widget coordinates back to track coordinates
            if self.background_image and self.scale_to_image:
                # First convert to image coordinates
                img_x_with_scale = (event.x() - offset_x) / scale
                
                if self.flip_y_axis:
                    img_y_with_scale = display_height - ((event.y() - offset_y) / scale)
                else:
                    img_y_with_scale = (event.y() - offset_y) / scale
                
                # Remove manual offset
                img_x = img_x_with_scale - self.x_offset
                img_y = img_y_with_scale - self.y_offset
                
                # Convert from image coordinates to track coordinates
                new_x = img_x / (display_width / self.image_width)
                new_y = img_y / (display_height / self.image_height)
            else:
                # Direct conversion from widget to track coordinates
                new_x = (event.x() - offset_x) / scale
                
                if self.flip_y_axis:
                    new_y = self.image_height - ((event.y() - offset_y) / scale)
                else:
                    new_y = (event.y() - offset_y) / scale
            
            # Update point
            self.points[self.selected_point_idx] = (frame, new_x, new_y)
            
            # Emit signal
            self.point_moved.emit(self.selected_point_idx, new_x, new_y)
            
            self.update()
        elif event.buttons() & Qt.MiddleButton:
            # Panning the view with middle mouse button
            dx = event.x() - self.pan_start_x
            dy = event.y() - self.pan_start_y
            
            self.offset_x = self.initial_offset_x + dx
            self.offset_y = self.initial_offset_y + dy
            
            self.update()
            
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        from curve_view_operations import CurveViewOperations
        CurveViewOperations.handle_mouse_release(self, event)
        
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        # Prevent jumpy zoom immediately after fit_selection
        if hasattr(self, "last_action_was_fit") and getattr(self, "last_action_was_fit", False):
            self.last_action_was_fit = False
            return

        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9

        # Get mouse position for zoom centering
        position = event.position()
        mouse_x = position.x()
        mouse_y = position.y()

        # BUGFIX: Temporarily clear multiple selection to avoid
        # special case handling in zoom_view that recalculates bbox
        temp_selected = None
        if hasattr(self, "selected_points") and len(self.selected_points) > 1:
            temp_selected = self.selected_points.copy()  # Save a copy
            self.selected_points = set([self.selected_point_idx]) if self.selected_point_idx >= 0 else set()

        # Use centralized zoom method from visualization_operations
        from visualization_operations import VisualizationOperations
        VisualizationOperations.zoom_view(self, factor, mouse_x, mouse_y)
        
        # Restore selected points
        if temp_selected is not None:
            self.selected_points = temp_selected
            self.update()  # Ensure selection is correctly displayed
        
    def keyPressEvent(self, event):
        """Handle key events."""
        step = 1
        
        # Larger step if Shift is pressed
        if event.modifiers() & Qt.ShiftModifier:
            step = 10
        
        # Smaller step if Ctrl is pressed
        if event.modifiers() & Qt.ControlModifier:
            step = 0.1
        
        if event.key() == Qt.Key_R:
            # Reset view
            self.resetView()
            # Also reset manual offsets
            self.x_offset = 0
            self.y_offset = 0
            self.update()
        elif event.key() == Qt.Key_Y:
            # Toggle Y-flip for debugging
            self.flip_y_axis = not self.flip_y_axis
            self.update()
        elif event.key() == Qt.Key_S:
            # Toggle scaling to image dimensions
            self.scale_to_image = not self.scale_to_image
            self.update()
        elif event.key() == Qt.Key_D:
            # Toggle debug mode
            self.debug_mode = not self.debug_mode
            self.update()
        
        # Handle arrow keys for navigation only
        elif event.key() == Qt.Key_Up:
            if event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier):
                # Adjust y-offset with arrow keys + modifiers
                self.y_offset -= step
                self.update()
        elif event.key() == Qt.Key_Down:
            if event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier):
                # Adjust y-offset with arrow keys + modifiers
                self.y_offset += step
                self.update()
        elif event.key() == Qt.Key_Delete and self.selected_point_idx >= 0:
            # Allow deleting selected point (for UI only, actual deletion would be handled elsewhere)
            pass

    # Compatibility methods to ensure consistent interface with EnhancedCurveView
    
    def set_curve_data(self, curve_data):
        """Compatibility method for main_window.py curve_data."""
        self.points = curve_data
        self.update()
        
    def set_selected_indices(self, indices):
        """Set selected point indices."""
        if indices:
            self.selected_point_idx = indices[0]  # Use the first selected point
        else:
            self.selected_point_idx = -1
        self.update()
        
    def get_selected_indices(self):
        """Return list of selected indices (singleton list or empty)."""
        if self.selected_point_idx >= 0:
            return [self.selected_point_idx]
        return []
        
    def toggleGrid(self, enabled):
        """Stub for grid toggling (not implemented in basic view)."""
        # Basic view doesn't support grid
        pass
        
    def toggleVelocityVectors(self, enabled):
        """Stub for velocity vector toggling (not implemented in basic view)."""
        # Basic view doesn't support velocity vectors
        pass
        
    def toggleAllFrameNumbers(self, enabled):
        """Stub for frame numbers toggling (not implemented in basic view)."""
        # Basic view doesn't support frame numbers
        pass
        
    def toggleCrosshair(self, enabled):
        """Stub for crosshair toggling (not implemented in basic view)."""
        # Basic view doesn't support crosshair
        pass
        
    def centerOnSelectedPoint(self, point_idx):
        """Stub for centering on point (not implemented in basic view)."""
        # Basic view doesn't support centering on points
        pass