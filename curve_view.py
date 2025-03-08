#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPointF, pyqtSignal as Signal, pyqtSlot as Slot
from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath, QFont, QImage, QPixmap


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
        # Assuming filenames can be mapped to frame numbers
        
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
            else:
                self.background_image = None
        except Exception as e:
            print(f"Error loading image: {str(e)}")
            self.background_image = None
            
    def resetView(self):
        """Reset view to show all points."""
        self.zoom_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.update()
        
    def paintEvent(self, event):
        """Draw the curve and points."""
        if not self.points and not self.background_image:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        
        # Calculate transform from image coordinates to widget coordinates
        widget_width = self.width()
        widget_height = self.height()
        
        # Scale to fit in view and apply zoom
        scale_x = widget_width / self.image_width * self.zoom_factor
        scale_y = widget_height / self.image_height * self.zoom_factor
        
        # Function to convert image coordinates to widget coordinates
        def transform(x, y):
            # Calculate the centered position in widget space
            # First scale the coordinates
            scaled_x = x * scale_x
            scaled_y = y * scale_y
            
            print(f"Original coordinates: ({x:.2f}, {y:.2f})")
            print(f"Scaling factors: X={scale_x:.4f}, Y={scale_y:.4f}")
            print(f"Scaled coordinates: ({scaled_x:.2f}, {scaled_y:.2f})")
            print(f"Widget dimensions: {widget_width}x{widget_height}")
            print(f"Current offsets: X={self.offset_x}, Y={self.offset_y}")
            
            tx = widget_width - scaled_x - self.offset_x  # Flip X axis to match 3DE4
            ty = scaled_y + self.offset_y
            
            print(f"Transformed coordinates: ({tx:.2f}, {ty:.2f})\n")
            
            return tx, ty
            
        # Draw background image if available
        if self.show_background and self.background_image:
            # Calculate scaled image size
            img_width = self.image_width
            img_height = self.image_height
            
            # Calculate aspect ratio of the image
            img_aspect_ratio = img_width / img_height
            
            # Determine the appropriate scaling to preserve aspect ratio
            # while fitting within the tracking data coordinates
            if img_aspect_ratio > (self.image_width / self.image_height):
                # Image is wider than tracking area - scale by width
                scaled_width = self.image_width * scale_x
                scaled_height = scaled_width / img_aspect_ratio
            else:
                # Image is taller than tracking area - scale by height
                scaled_height = self.image_height * scale_y
                scaled_width = scaled_height * img_aspect_ratio
            
            # Calculate the center of the tracking data area in widget coordinates
            center_x, center_y = transform(self.image_width / 2, self.image_height / 2)
            
            # Position the image centered on the tracking data area
            img_x = center_x - scaled_width / 2
            img_y = center_y - scaled_height / 2
            
            # Create a transparent version of the image for overlay
            pixmap = QPixmap.fromImage(self.background_image)
            
            # Set opacity for the image
            painter.setOpacity(self.background_opacity)
            
            # Draw the image
            painter.drawPixmap(int(img_x), int(img_y), int(scaled_width), int(scaled_height), pixmap)
            
            # Reset opacity for other elements
            painter.setOpacity(1.0)
        
        # Draw the main curve if available
        if self.points:
            path = QPainterPath()
            first_point = True
            
            for frame, x, y in self.points:
                tx, ty = transform(x, y)
                
                if first_point:
                    path.moveTo(tx, ty)
                    first_point = False
                else:
                    path.lineTo(tx, ty)
            
            # Draw curve
            curve_pen = QPen(QColor(0, 160, 230), 2)
            painter.setPen(curve_pen)
            painter.drawPath(path)
            
            # Draw points
            for i, (frame, x, y) in enumerate(self.points):
                tx, ty = transform(x, y)
                
                # Highlight selected point
                if i == self.selected_point_idx:
                    painter.setPen(QPen(QColor(255, 80, 80), 2))
                    painter.setBrush(QColor(255, 80, 80, 150))
                    point_radius = self.point_radius + 2
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
            
    def mousePressEvent(self, event):
        """Handle mouse press to select or move points."""
        if not self.points:
            return
            
        if event.button() == Qt.LeftButton:
            self.drag_active = False
            self.selected_point_idx = -1
            
            # Calculate transform from image coordinates to widget coordinates
            widget_width = self.width()
            widget_height = self.height()
            scale_x = widget_width / self.image_width * self.zoom_factor
            scale_y = widget_height / self.image_height * self.zoom_factor
            
            # Find if we clicked on a point
            for i, (frame, x, y) in enumerate(self.points):
                # Convert image coordinates to widget coordinates
                scaled_x = x * scale_x
                scaled_y = y * scale_y
                tx = widget_width - scaled_x - self.offset_x
                ty = scaled_y + self.offset_y
                
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
        elif event.button() == Qt.RightButton:
            # Right click for panning
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
            
            # Calculate transform from widget coordinates to image coordinates
            widget_width = self.width()
            widget_height = self.height()
            scale_x = widget_width / self.image_width * self.zoom_factor
            scale_y = widget_height / self.image_height * self.zoom_factor
            
            # Convert mouse position to image coordinates
            # First, we need to convert from widget coordinates to the same space as our transform function
            # Then invert the transform to get back to image coordinates
            new_x = (widget_width - event.x() - self.offset_x) / scale_x
            new_y = (event.y() - self.offset_y) / scale_y
            
            # Update point
            self.points[self.selected_point_idx] = (frame, new_x, new_y)
            
            # Emit signal
            self.point_moved.emit(self.selected_point_idx, new_x, new_y)
            
            self.update()
        elif event.buttons() & Qt.RightButton:
            # Panning the view
            dx = event.x() - self.pan_start_x
            dy = event.y() - self.pan_start_y
            
            self.offset_x = self.initial_offset_x + dx
            self.offset_y = self.initial_offset_y + dy
            
            self.update()
            
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self.drag_active = False
        
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        # Calculate zoom factor change
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        
        # Calculate zoom center in widget coordinates
        center_x = event.x()
        center_y = event.y()
        
        # Calculate zoom center in image coordinates before zoom
        widget_width = self.width()
        widget_height = self.height()
        old_zoom = self.zoom_factor
        old_scale_x = widget_width / self.image_width * old_zoom
        old_scale_y = widget_height / self.image_height * old_zoom
        
        # Convert widget coordinates to image coordinates using the same logic as in mouseMoveEvent
        adjusted_x = widget_width - center_x - self.offset_x
        adjusted_y = center_y - self.offset_y
        
        img_center_x = adjusted_x / old_scale_x
        img_center_y = adjusted_y / old_scale_y
        
        # Apply zoom
        self.zoom_factor *= factor
        
        # Constrain zoom level
        self.zoom_factor = max(0.1, min(10.0, self.zoom_factor))
        
        # Calculate new scale factors
        new_scale_x = widget_width / self.image_width * self.zoom_factor
        new_scale_y = widget_height / self.image_height * self.zoom_factor
        
        # Adjust offset to keep the point under cursor fixed using the same transform logic
        self.offset_x = widget_width - center_x - img_center_x * new_scale_x
        self.offset_y = center_y - img_center_y * new_scale_y
        
        self.update()
        
    def keyPressEvent(self, event):
        """Handle key events."""
        if event.key() == Qt.Key_R:
            # Reset view
            self.resetView()
        elif event.key() == Qt.Key_Delete and self.selected_point_idx >= 0:
            # Allow deleting selected point (for UI only, actual deletion would be handled elsewhere)
            pass
        elif event.key() == Qt.Key_Left:
            # Move to previous image with left arrow
            if self.current_image_idx > 0:
                self.setCurrentImageByIndex(self.current_image_idx - 1)
                # Emit signal to update UI
                self.image_changed.emit(self.current_image_idx)
        elif event.key() == Qt.Key_Right:
            # Move to next image with right arrow
            if self.current_image_idx < len(self.image_filenames) - 1:
                self.setCurrentImageByIndex(self.current_image_idx + 1)
                # Emit signal to update UI
                self.image_changed.emit(self.current_image_idx)
