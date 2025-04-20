#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, Signal, Slot
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QFont, QImage, QPixmap, QBrush
from services.input_service import InputService
from keyboard_shortcuts import ShortcutManager
from services.image_service import ImageService


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
        self.selected_points = set()
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
        self.show_background = True
        self.background_opacity = 0.7  # 0.0 to 1.0

        # Register shortcuts via ShortcutManager
        self._register_shortcuts()

    def _register_shortcuts(self):
        # Register CurveView-specific shortcuts
        ShortcutManager.connect_shortcut(self, "reset_view", self.reset_view_slot)
        ShortcutManager.connect_shortcut(self, "toggle_y_flip", self.toggle_y_flip)
        ShortcutManager.connect_shortcut(self, "toggle_scale_to_image", self.toggle_scale_to_image)
        ShortcutManager.connect_shortcut(self, "toggle_debug_mode", self.toggle_debug_mode)

    def reset_view_slot(self):
        self.resetView()
        self.x_offset = 0
        self.y_offset = 0
        self.update()

    def toggle_y_flip(self):
        self.flip_y_axis = not getattr(self, "flip_y_axis", False)
        self.update()

    def toggle_scale_to_image(self):
        self.scale_to_image = not getattr(self, "scale_to_image", False)
        self.update()

    def toggle_debug_mode(self):
        self.debug_mode = not getattr(self, "debug_mode", False)
        self.update()
        
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
        ImageService.set_image_sequence(self, path, filenames)
        self.update()
        
    def setCurrentImageByFrame(self, frame):
        """Set the current background image based on frame number."""
        ImageService.set_current_image_by_frame(self, frame)
        
    def setCurrentImageByIndex(self, idx):
        """Set current image by index and update the view."""
        ImageService.set_current_image_by_index(self, idx)
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
        ImageService.load_current_image(self)
        
    def resetView(self):
        """Reset view to show all points."""
        from centering_zoom_operations import ZoomOperations
        ZoomOperations.reset_view(self)
        
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
        offset_x, offset_y = ZoomOperations.calculate_centering_offsets(widget_width, widget_height, display_width * scale, display_height * scale, self.offset_x, self.offset_y)
        # offset_y is set below
        # offset_y is now set by calculate_centering_offsets above

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
            painter.setOpacity(self.background_opacity)
            painter.drawPixmap(int(img_x), int(img_y), int(scaled_width), int(scaled_height), self.background_image)
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

                # Highlight selected points
                if i in self.selected_points:
                    painter.setPen(QPen(QColor(255, 80, 80), 2))
                    painter.setBrush(QColor(255, 80, 80, 150))
                    # primary index gets larger radius
                    point_radius = self.point_radius + 2 if i == self.selected_point_idx else self.point_radius
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
        if hasattr(self, 'selected_points') and self.selected_points:
            # Gather types of all selected points
            selected_types = set()
            for i in self.selected_points:
                if 0 <= i < len(self.points):
                    pt = self.points[i]
                    if len(pt) >= 4:
                        selected_types.add(str(pt[3]))
                    else:
                        selected_types.add('normal')
            types_str = ', '.join(sorted(selected_types))
            info_text += f" | Type(s): {types_str}"
        painter.drawText(10, 20, info_text)
        
        # Show image info if available
        if self.background_image:
            img_info = f"Image: {ImageService.get_current_image_index(self) + 1}/{ImageService.get_image_count(self)}"
            if ImageService.get_image_filenames(self) and ImageService.get_current_image_index(self) >= 0:
                img_info += f" - {os.path.basename(ImageService.get_image_filenames(self)[ImageService.get_current_image_index(self)])}"
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
        InputService.handle_mouse_press(self, event)
        
    def mouseMoveEvent(self, event):
        """Handle mouse movement for dragging points or panning."""
        InputService.handle_mouse_move(self, event)
        
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        InputService.handle_mouse_release(self, event)
        
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming via central service."""
        InputService.handle_wheel_event(self, event)
        
    def keyPressEvent(self, event):
        """Handle key events for navigation (arrow keys, etc)."""
        InputService.handle_key_event(self, event)

    # Compatibility methods to ensure consistent interface with EnhancedCurveView
    
    def set_curve_data(self, curve_data):
        """Compatibility method for main_window.py curve_data."""
        self.points = curve_data
        self.update()
        
    def set_selected_indices(self, indices):
        """Set selected point indices."""
        self.selected_points = set(indices)
        if indices:
            self.selected_point_idx = indices[0]
        else:
            self.selected_point_idx = -1
        self.update()

    def get_selected_indices(self):
        """Return list of selected indices (singleton list or empty)."""
        return list(self.selected_points)
        
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