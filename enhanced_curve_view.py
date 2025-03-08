#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math
from PySide6.QtWidgets import QWidget, QApplication, QGridLayout
from PySide6.QtCore import Qt, QPointF, Signal, Slot, QRect
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QFont, QImage, QPixmap, QBrush
import re


class EnhancedCurveView(QWidget):
    """Enhanced widget for displaying and editing the 2D tracking curve with 
    added visualization options like grid, vectors, and all frame numbers."""
    
    point_moved = Signal(int, float, float)  # Signal emitted when a point is moved
    point_selected = Signal(int)  # Signal emitted when a point is selected
    image_changed = Signal(int)  # Signal emitted when image changes via keyboard
    
    def __init__(self, parent=None):
        super(EnhancedCurveView, self).__init__(parent)
        self.setMinimumSize(800, 600)
        self.points = []
        self.selected_point_idx = -1
        self.selected_points = set()  # Track selected points for multi-select
        self.drag_active = False
        self.zoom_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.x_offset = 0  # Manual offset for view panning
        self.y_offset = 0  # Manual offset for view panning
        self.image_width = 1920  # Default, will be updated when data is loaded
        self.image_height = 1080  # Default, will be updated when data is loaded
        self.setMouseTracking(True)
        self.point_radius = 5
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Enhanced visual options
        self.show_grid = True
        self.grid_spacing = 100
        self.show_all_frame_numbers = False  # Option to show all frame numbers
        self.show_velocity_vectors = False
        self.velocity_vector_scale = 10  # Scale factor for velocity vectors
        self.show_crosshair = True
        self.display_precision = 3  # Decimal places for coordinate display
        
        # Image background properties
        self.scale_to_image = True  # Automatically scale to fit image dimensions
        self.flip_y_axis = True  # Flip Y axis (0 at bottom instead of top)
        self.show_background = True  # Show background image
        self.background_opacity = 0.5  # Background image opacity
        self.image_sequence_path = ""  # Path to image sequence directory
        self.image_filenames = []  # List of image filenames
        self.current_image_idx = -1  # Current image index in sequence
        self.background_image = None  # Current background image
        
        # Selection properties
        self.multi_select_active = False
        self.selection_start = None
        self.selection_rect = None  # Selection rectangle for multi-select
        
        # Store reference to main window for direct updates
        self.main_window = parent
        
        # Debug options
        self.debug_mode = True  # Enable debug visuals
        
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
        
    def toggleGrid(self, enabled):
        """Toggle grid visibility."""
        self.show_grid = enabled
        self.update()
        
    def toggleVelocityVectors(self, enabled):
        """Toggle velocity vector display."""
        self.show_velocity_vectors = enabled
        self.update()
        
    def toggleAllFrameNumbers(self, enabled):
        """Toggle display of all frame numbers."""
        self.show_all_frame_numbers = enabled
        self.update()
        
    def toggleCrosshair(self, enabled):
        """Toggle crosshair visibility."""
        self.show_crosshair = enabled
        self.update()
    
    def centerOnSelectedPoint(self, point_idx=-1, preserve_zoom=True):
        """Center the view on the specified point index.
        
        If no index is provided, uses the currently selected point.
        
        Args:
            point_idx: Index of point to center on. Default -1 uses selected point.
            preserve_zoom: If True, maintain current zoom level. If False, reset view.
        """
        # Use provided index or current selection
        idx = point_idx if point_idx >= 0 else self.selected_point_idx
        
        if idx < 0 or not hasattr(self, 'main_window') or not self.main_window.curve_data:
            return False
            
        try:
            # Get the point to center on
            if idx < len(self.main_window.curve_data):
                # Extract point coordinates
                _, x, y = self.main_window.curve_data[idx]
                print(f"EnhancedCurveView: Centering on point {idx} at ({x}, {y})")
                
                # Set this as the selected point
                self.selected_point_idx = idx
                
                # Store current zoom factor if we're preserving zoom
                current_zoom = self.zoom_factor if preserve_zoom else 1.0
                
                # Reset zoom and positioning to default if not preserving zoom
                if not preserve_zoom:
                    self.resetView()
                
                # Get the point coordinates in widget space after reset
                widget_width = self.width()
                widget_height = self.height()
                
                # Calculate the transform that would be applied in paintEvent
                display_width = self.image_width
                display_height = self.image_height
                if self.background_image:
                    display_width = self.background_image.width()
                    display_height = self.background_image.height()
                
                # Calculate scale to fit in the widget
                scale_x = widget_width / display_width
                scale_y = widget_height / display_height
                
                # Apply the preserved zoom if requested
                if preserve_zoom:
                    scale = min(scale_x, scale_y) * current_zoom
                else:
                    scale = min(scale_x, scale_y) * self.zoom_factor
                
                # Calculate centering offsets for the image
                offset_x = (widget_width - (display_width * scale)) / 2
                offset_y = (widget_height - (display_height * scale)) / 2
                
                # Transform the point using the same logic as in paintEvent
                if self.scale_to_image:
                    # Scale the tracking coordinates to match the image size
                    img_x = x * (display_width / self.image_width)
                    img_y = y * (display_height / self.image_height)
                    
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
                
                # Calculate the offset needed to center this point
                center_x = widget_width / 2
                center_y = widget_height / 2
                
                # The offset needed is the difference between where the point is
                # and where we want it to be (at the center)
                delta_x = center_x - tx
                delta_y = center_y - ty
                
                # Apply the offset
                self.offset_x = delta_x
                self.offset_y = delta_y
                
                print(f"EnhancedCurveView: Point transforms to ({tx}, {ty})")
                print(f"EnhancedCurveView: Center is at ({center_x}, {center_y})")
                print(f"EnhancedCurveView: Applied offset of ({delta_x}, {delta_y})")
                
                # Update the view to apply new transforms
                self.update()
                return True
            else:
                print(f"EnhancedCurveView: Point index {idx} out of range")
                return False
        except Exception as e:
            print(f"EnhancedCurveView: Error centering on point: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
    def setCoordinatePrecision(self, precision):
        """Set decimal precision for coordinate display."""
        self.display_precision = max(1, min(precision, 6))
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
            
    def setCurrentImageByIndex(self, idx):
        """Set current image by index and update the view."""
        if idx < 0 or idx >= len(self.image_filenames):
            print(f"EnhancedCurveView: Invalid image index: {idx}")
            return
            
        # Store current zoom factor and view offsets
        current_zoom = self.zoom_factor
        current_offset_x = self.offset_x
        current_offset_y = self.offset_y
        
        # Store current center position before changing the image
        center_pos = None
        if self.selected_point_idx >= 0 and hasattr(self, 'main_window') and self.main_window.curve_data:
            # Remember center point if we have a selected point
            try:
                point = self.main_window.curve_data[self.selected_point_idx]
                center_pos = (point[1], point[2])  # x, y coordinates
                print(f"EnhancedCurveView: Storing center position at {center_pos}")
            except (IndexError, AttributeError) as e:
                print(f"EnhancedCurveView: Could not store center position: {str(e)}")
        
        # Update image index and load the image
        self.current_image_idx = idx
        self.loadCurrentImage()
        
        # Restore the zoom factor that was in effect before switching images
        print(f"EnhancedCurveView: Preserving zoom factor of {current_zoom}")
        self.zoom_factor = current_zoom
        
        # After changing the image, center on the selected point using our improved function
        if self.selected_point_idx >= 0:
            success = self.centerOnSelectedPoint(preserve_zoom=True)
            if success:
                print(f"EnhancedCurveView: Successfully centered on point {self.selected_point_idx}")
            else:
                print(f"EnhancedCurveView: Could not center on point {self.selected_point_idx}")
                # If centering fails, restore previous view position
                self.offset_x = current_offset_x
                self.offset_y = current_offset_y
        else:
            # If no point is selected, at least maintain the zoom level
            self.offset_x = current_offset_x
            self.offset_y = current_offset_y
        
        self.update()
        self.setFocus()
        
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
            # Get path to current image
            image_path = os.path.join(self.image_sequence_path, self.image_filenames[self.current_image_idx])
            print(f"EnhancedCurveView: Loading image: {image_path}")
            
            # Load image using PySide6.QtGui.QImage
            image = QImage(image_path)
            
            # Make sure we have focus to receive keyboard events
            self.setFocus()
            
            if image.isNull():
                print(f"EnhancedCurveView: Failed to load image: {image_path}")
                self.background_image = None
            else:
                print(f"EnhancedCurveView: Successfully loaded image from: {image_path}")
                self.background_image = image
                
                # Update track dimensions to match image dimensions
                if self.scale_to_image:
                    self.image_width = image.width()
                    self.image_height = image.height()
                    
                # Emit the image_changed signal
                print(f"EnhancedCurveView.loadCurrentImage: Emitting image_changed signal for idx={self.current_image_idx}")
                self.image_changed.emit(self.current_image_idx)
        except Exception as e:
            print(f"EnhancedCurveView: Error loading image: {str(e)}")
            self.background_image = None
            
    def resetView(self):
        """Reset view to show all points."""
        self.zoom_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.update()
        
    def paintEvent(self, event):
        """Draw the curve and points with enhanced visualization."""
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
        
        # Coordinate transformation functions
        def transform_point(x, y):
            """Transform from track coordinates to widget coordinates."""
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
        
        def inverse_transform(tx, ty):
            """Transform from widget coordinates to track coordinates."""
            if self.background_image and self.scale_to_image:
                # Convert from widget to image space
                img_x = (tx - offset_x) / scale
                
                if self.flip_y_axis:
                    img_y = display_height - ((ty - offset_y) / scale)
                else:
                    img_y = (ty - offset_y) / scale
                
                # Remove manual offset
                img_x = img_x - self.x_offset
                img_y = img_y - self.y_offset
                
                # Convert from image to track coordinates
                x = img_x / (display_width / self.image_width)
                y = img_y / (display_height / self.image_height)
            else:
                # Direct conversion
                x = (tx - offset_x) / scale
                
                if self.flip_y_axis:
                    y = self.image_height - ((ty - offset_y) / scale)
                else:
                    y = (ty - offset_y) / scale
                    
            return x, y
        
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
            
        # Draw grid if enabled
        if self.show_grid:
            painter.setPen(QPen(QColor(80, 80, 80, 120), 1, Qt.DotLine))
            
            # Calculate the range of grid lines to draw
            grid_min_x = 0
            grid_max_x = display_width
            grid_min_y = 0
            grid_max_y = display_height
            
            # Draw horizontal grid lines
            y = grid_min_y
            while y <= grid_max_y:
                tx1, ty = transform_point(grid_min_x, y)
                tx2, _ = transform_point(grid_max_x, y)
                painter.drawLine(int(tx1), int(ty), int(tx2), int(ty))
                y += self.grid_spacing
                
            # Draw vertical grid lines
            x = grid_min_x
            while x <= grid_max_x:
                tx, ty1 = transform_point(x, grid_min_y)
                _, ty2 = transform_point(x, grid_max_y)
                painter.drawLine(int(tx), int(ty1), int(tx), int(ty2))
                x += self.grid_spacing
                
            # Add coordinate labels at grid intersections
            painter.setPen(QPen(QColor(150, 150, 150, 180)))
            font = painter.font()
            font.setPointSize(7)
            painter.setFont(font)
            
            # Draw labels at some grid intersections (not all to avoid clutter)
            for x in range(0, int(grid_max_x) + 1, self.grid_spacing * 5):
                for y in range(0, int(grid_max_y) + 1, self.grid_spacing * 5):
                    tx, ty = transform_point(x, y)
                    painter.drawText(int(tx) + 2, int(ty) - 2, f"{x},{y}")
            
        # Draw the main curve if available
        if self.points:
            # Prepare to draw velocity vectors if enabled
            if self.show_velocity_vectors and len(self.points) > 1:
                # Sort points by frame for correct velocity calculation
                sorted_points = sorted(self.points, key=lambda p: p[0])
                
                for i in range(1, len(sorted_points)):
                    prev_frame, prev_x, prev_y = sorted_points[i-1]
                    curr_frame, curr_x, curr_y = sorted_points[i]
                    
                    # Calculate velocity components
                    frame_diff = curr_frame - prev_frame
                    if frame_diff > 0:
                        vx = (curr_x - prev_x) / frame_diff
                        vy = (curr_y - prev_y) / frame_diff
                        
                        # Scale velocity for better visualization
                        scaled_vx = vx * self.velocity_vector_scale
                        scaled_vy = vy * self.velocity_vector_scale
                        
                        # Draw velocity vector
                        tx, ty = transform_point(curr_x, curr_y)
                        end_x, end_y = transform_point(curr_x + scaled_vx, curr_y + scaled_vy)
                        
                        # Set pen based on velocity magnitude
                        vel_magnitude = math.sqrt(vx*vx + vy*vy)
                        
                        # Color based on magnitude (slow=green, medium=yellow, fast=red)
                        if vel_magnitude < 2:
                            color = QColor(0, 200, 0, 180)  # Green for slow
                        elif vel_magnitude < 10:
                            color = QColor(200, 200, 0, 180)  # Yellow for medium
                        else:
                            color = QColor(200, 0, 0, 180)  # Red for fast
                            
                        painter.setPen(QPen(color, 1))
                        painter.drawLine(int(tx), int(ty), int(end_x), int(end_y))
                        
                        # Draw arrow head
                        if vel_magnitude > 0.5:  # Only draw arrowhead if velocity is significant
                            # Calculate arrow angle
                            angle = math.atan2(end_y - ty, end_x - tx)
                            arrow_size = 6
                            
                            # Calculate arrow points
                            arrow_p1_x = end_x - arrow_size * math.cos(angle - math.pi/6)
                            arrow_p1_y = end_y - arrow_size * math.sin(angle - math.pi/6)
                            arrow_p2_x = end_x - arrow_size * math.cos(angle + math.pi/6)
                            arrow_p2_y = end_y - arrow_size * math.sin(angle + math.pi/6)
                            
                            # Draw arrow
                            points = [QPointF(end_x, end_y), QPointF(arrow_p1_x, arrow_p1_y), 
                                      QPointF(arrow_p2_x, arrow_p2_y)]
                            painter.setBrush(color)
                            painter.drawPolygon(points)
            
            # Set pen for the main curve
            curve_pen = QPen(QColor(0, 160, 230), 2)
            painter.setPen(curve_pen)
            
            # Create path for the curve
            path = QPainterPath()
            first_point = True
            
            for frame, x, y in sorted(self.points, key=lambda p: p[0]):
                tx, ty = transform_point(x, y)
                
                if first_point:
                    path.moveTo(tx, ty)
                    first_point = False
                else:
                    path.lineTo(tx, ty)
            
            # Draw the curve
            painter.drawPath(path)
            
            # Draw points
            for i, (frame, x, y) in enumerate(self.points):
                tx, ty = transform_point(x, y)
                
                # Determine if point is selected (either primary selection or in multi-selection)
                is_selected = (i == self.selected_point_idx) or (i in self.selected_points)
                
                if is_selected:
                    painter.setPen(QPen(QColor(255, 80, 80), 2))
                    painter.setBrush(QColor(255, 80, 80, 150))
                    point_radius = self.point_radius + 2
                else:
                    painter.setPen(QPen(QColor(200, 200, 200), 1))
                    painter.setBrush(QColor(220, 220, 220, 200))
                    point_radius = self.point_radius
                    
                painter.drawEllipse(QPointF(tx, ty), point_radius, point_radius)
                
                # Draw frame number - either for all frames or selected frames
                if self.show_all_frame_numbers or is_selected or frame % 10 == 0:
                    painter.setPen(QPen(QColor(200, 200, 100), 1))
                    font = painter.font()
                    font.setPointSize(8)
                    painter.setFont(font)
                    painter.drawText(int(tx) + 10, int(ty) - 10, str(frame))
                    
                    # Show coordinates for selected points with higher precision
                    if is_selected:
                        coord_format = f"{{:.{self.display_precision}f}}"
                        coord_text = f"X: {coord_format.format(x)}, Y: {coord_format.format(y)}"
                        painter.drawText(int(tx) + 10, int(ty) + 15, coord_text)
        
        # Draw crosshair at mouse position if enabled
        if self.show_crosshair and self.underMouse():
            mouse_pos = self.mapFromGlobal(self.cursor().pos())
            
            # Get coordinates in track space
            track_x, track_y = inverse_transform(mouse_pos.x(), mouse_pos.y())
            
            # Draw crosshair lines
            painter.setPen(QPen(QColor(255, 200, 0, 120), 1, Qt.DashLine))
            painter.drawLine(0, mouse_pos.y(), widget_width, mouse_pos.y())
            painter.drawLine(mouse_pos.x(), 0, mouse_pos.x(), widget_height)
            
            # Draw coordinate info
            painter.setPen(QPen(QColor(255, 200, 0)))
            coord_format = f"{{:.{self.display_precision}f}}"
            coord_text = f"X: {coord_format.format(track_x)}, Y: {coord_format.format(track_y)}"
            
            # Create background rect for text
            font_metrics = painter.fontMetrics()
            text_rect = font_metrics.boundingRect(coord_text)
            text_rect.moveCenter(QPointF(mouse_pos.x(), mouse_pos.y() - 20).toPoint())
            text_rect.adjust(-5, -2, 5, 2)
            
            painter.fillRect(text_rect, QColor(0, 0, 0, 180))
            painter.drawText(text_rect, Qt.AlignCenter, coord_text)
            
        # Draw selection rectangle if active
        if self.selection_rect:
            painter.setPen(QPen(QColor(100, 180, 255), 1, Qt.DashLine))
            painter.setBrush(QColor(100, 180, 255, 30))
            painter.drawRect(self.selection_rect)
        
        # Display info
        info_font = QFont("Monospace", 9)
        painter.setFont(info_font)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        
        # Show current view info
        info_text = f"Zoom: {self.zoom_factor:.2f}x | Points: {len(self.points)}"
        if self.selected_point_idx >= 0:
            frame, x, y = self.points[self.selected_point_idx]
            coord_format = f"{{:.{self.display_precision}f}}"
            info_text += f" | Selected: Frame {frame}, X: {coord_format.format(x)}, Y: {coord_format.format(y)}"
        elif self.selected_points:
            info_text += f" | Selected: {len(self.selected_points)} points"
            
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
            shortcuts += " | [G] Toggle Grid, [V] Toggle Vectors, [F] Toggle All Frame Numbers"
            shortcuts += " | Shift+Drag: Select multiple points"
            painter.drawText(10, 80, shortcuts)
            
    def mousePressEvent(self, event):
        """Handle mouse press to select or move points."""
        if event.button() == Qt.LeftButton:
            # Check if Shift is pressed for multi-selection rectangle
            if event.modifiers() & Qt.ShiftModifier:
                self.selection_start = event.pos()
                self.selection_rect = QRect(self.selection_start, self.selection_start)
                self.update()
                return
                
            # Calculate transform parameters
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

            # Transform function
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
            
            self.drag_active = False
            
            # Check if Ctrl is pressed for multi-selection
            ctrl_pressed = event.modifiers() & Qt.ControlModifier
            
            # Find if we clicked on a point
            clicked_on_point = False
            for i, (frame, x, y) in enumerate(self.points):
                tx, ty = transform_point(x, y)
                
                # Check if within radius
                dx = event.x() - tx
                dy = event.y() - ty
                dist = math.sqrt(dx * dx + dy * dy)
                
                if dist <= self.point_radius + 2:  # +2 for better selection
                    clicked_on_point = True
                    
                    if ctrl_pressed:
                        # Add/remove from multi-selection
                        if i in self.selected_points:
                            self.selected_points.remove(i)
                        else:
                            self.selected_points.add(i)
                            self.selected_point_idx = i  # Also make it primary selection
                    else:
                        # If not using multi-select, just select this point
                        if not i in self.selected_points:
                            self.selected_points.clear()
                        
                        self.selected_point_idx = i
                        self.selected_points.add(i)
                        self.drag_active = True
                        
                    self.point_selected.emit(i)
                    break
            
            # If clicked on empty space and not using Ctrl for multi-select, clear selection
            if not clicked_on_point and not ctrl_pressed:
                self.selected_points.clear()
                self.selected_point_idx = -1
                
            self.update()
                
        elif event.button() == Qt.MiddleButton:
            # Middle click for panning
            self.pan_start_x = event.x()
            self.pan_start_y = event.y()
            self.initial_offset_x = self.offset_x
            self.initial_offset_y = self.offset_y
            
    def mouseMoveEvent(self, event):
        """Handle mouse movement for dragging points or panning."""
        # Handle selection rectangle
        if self.selection_start is not None:
            self.selection_rect = QRect(self.selection_start, event.pos()).normalized()
            self.update()
            return
            
        # Calculate transform parameters for point dragging
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
        
        if self.drag_active and self.selected_point_idx >= 0:
            # Get the point we're dragging
            frame, x, y = self.points[self.selected_point_idx]
            
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
        else:
            # Update for crosshair on mouse move
            self.update()
            
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self.drag_active = False
            
            # Finalize selection rectangle if active
            if self.selection_start is not None:
                self.finalize_selection()
                self.selection_start = None
                self.selection_rect = None
                self.update()
        
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        
        # Store the old zoom factor
        old_zoom = self.zoom_factor
        
        # Apply zoom
        self.zoom_factor *= factor
        
        # Constrain zoom level
        self.zoom_factor = max(0.1, min(10.0, self.zoom_factor))
        
        # If we have a selected point, zoom on it
        if self.selected_point_idx >= 0 and self.selected_point_idx < len(self.points):
            # Get the coordinates of the selected point
            _, x, y = self.points[self.selected_point_idx]
            print(f"EnhancedCurveView: Zooming centered on point {self.selected_point_idx} at ({x}, {y})")
            
            # Calculate widget dimensions
            widget_width = self.width()
            widget_height = self.height()
            
            # Calculate display dimensions (image or track)
            display_width = self.image_width
            display_height = self.image_height
            if self.background_image:
                display_width = self.background_image.width()
                display_height = self.background_image.height()
            
            # Calculate scale to fit in the widget
            scale_x = widget_width / display_width
            scale_y = widget_height / display_height
            scale = min(scale_x, scale_y) * self.zoom_factor
            
            # Calculate centering offsets for the image
            offset_x = (widget_width - (display_width * scale)) / 2
            offset_y = (widget_height - (display_height * scale)) / 2
            
            # Transform the point using the same logic as in paintEvent
            if self.scale_to_image:
                # Scale the tracking coordinates to match the image size
                img_x = x * (display_width / self.image_width)
                img_y = y * (display_height / self.image_height)
                
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
            
            # Calculate the offset needed to center this point
            center_x = widget_width / 2
            center_y = widget_height / 2
            
            # The offset needed is the difference between where the point is
            # and where we want it to be (at the center)
            delta_x = center_x - tx
            delta_y = center_y - ty
            
            # Apply the offset
            self.offset_x = delta_x
            self.offset_y = delta_y
            
            print(f"EnhancedCurveView: Point transforms to ({tx}, {ty})")
            print(f"EnhancedCurveView: Center is at ({center_x}, {center_y})")
            print(f"EnhancedCurveView: Applied zoom offset of ({delta_x}, {delta_y})")
        else:
            # If no selected point, use standard zoom behavior (zoom at cursor)
            # Calculate zoom center in widget coordinates
            position = event.position()
            center_x = position.x()
            center_y = position.y()
            
            # Calculate widget dimensions
            widget_width = self.width()
            widget_height = self.height()
            
            # Calculate display dimensions (image or track)
            display_width = self.image_width
            display_height = self.image_height
            if self.background_image:
                display_width = self.background_image.width()
                display_height = self.background_image.height()
            
            # Calculate the scale factor
            scale_x = widget_width / display_width
            scale_y = widget_height / display_height
            base_scale = min(scale_x, scale_y)
            old_scale = base_scale * old_zoom
            new_scale = base_scale * self.zoom_factor
            
            # Calculate the point position relative to the image
            rel_x = (center_x - self.offset_x) / old_scale
            rel_y = (center_y - self.offset_y) / old_scale
            
            # Calculate how much the point moves due to zoom
            new_x = rel_x * new_scale
            new_y = rel_y * new_scale
            
            # Adjust the offset to keep the cursor point fixed
            delta_x = new_x - (center_x - self.offset_x)
            delta_y = new_y - (center_y - self.offset_y)
            
            # Update the offsets
            self.offset_x -= delta_x
            self.offset_y -= delta_y
            
            print(f"EnhancedCurveView: Standard zoom at cursor ({center_x}, {center_y})")
        
        # Update the view
        self.update()
        
    def keyPressEvent(self, event):
        """Handle key press events.
        
        Implements keyboard navigation and shortcuts.
        """
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
        elif event.key() == Qt.Key_G:
            # Toggle grid
            self.show_grid = not self.show_grid
            self.update()
        elif event.key() == Qt.Key_V:
            # Toggle velocity vectors
            self.show_velocity_vectors = not self.show_velocity_vectors
            self.update()
        elif event.key() == Qt.Key_F:
            # Toggle all frame numbers
            self.show_all_frame_numbers = not self.show_all_frame_numbers
            self.update()
        elif event.key() == Qt.Key_Escape:
            # Clear selection with Escape key
            self.selected_points.clear()
            self.selected_point_idx = -1
            self.update()
        elif event.key() == Qt.Key_Delete:
            # Delete selected points
            if self.selected_points or self.selected_point_idx >= 0:
                # This is just UI feedback - actual deletion is handled in higher-level component
                pass
        elif event.key() == Qt.Key_Left:
            print("EnhancedCurveView: Left key pressed")
            if event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier):
                # Adjust x-offset with arrow keys + modifiers
                self.x_offset -= step
                self.update()
            else:
                # Move to previous image with left arrow
                if self.current_image_idx > 0:
                    print(f"EnhancedCurveView: Moving to previous image, index={self.current_image_idx-1}")
                    self.setCurrentImageByIndex(self.current_image_idx - 1)
                    
                    # Use the direct update method if available
                    if hasattr(self, 'update_timeline_for_image'):
                        print(f"EnhancedCurveView: Using direct update method for index {self.current_image_idx}")
                        self.update_timeline_for_image(self.current_image_idx)
                    else:
                        print("EnhancedCurveView: Direct update method not available")
                        # Fall back to signal emission
                        print(f"EnhancedCurveView: Emitting image_changed signal with index={self.current_image_idx}")
                        self.image_changed.emit(self.current_image_idx)
                        
        elif event.key() == Qt.Key_Right:
            print("EnhancedCurveView: Right key pressed")
            if event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier):
                # Adjust x-offset with arrow keys + modifiers
                self.x_offset += step
                self.update()
            else:
                # Move to next image with right arrow
                if self.current_image_idx < len(self.image_filenames) - 1:
                    print(f"EnhancedCurveView: Moving to next image, index={self.current_image_idx+1}")
                    self.setCurrentImageByIndex(self.current_image_idx + 1)
                    
                    # Use the direct update method if available
                    if hasattr(self, 'update_timeline_for_image'):
                        print(f"EnhancedCurveView: Using direct update method for index {self.current_image_idx}")
                        self.update_timeline_for_image(self.current_image_idx)
                    else:
                        print("EnhancedCurveView: Direct update method not available")
                        # Fall back to signal emission
                        print(f"EnhancedCurveView: Emitting image_changed signal with index={self.current_image_idx}")
                        self.image_changed.emit(self.current_image_idx)
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
                
    def selectAllPoints(self):
        """Select all points in the curve."""
        if not self.points:
            return
            
        self.selected_points = set(range(len(self.points)))
        if self.points:
            self.selected_point_idx = 0
            
        self.update()
        
    def clearSelection(self):
        """Clear all point selections."""
        self.selected_points.clear()
        self.selected_point_idx = -1
        self.update()
        
    def set_curve_data(self, curve_data):
        """Compatibility method for curve_data from main_window."""
        self.points = curve_data
        # Don't need to reset view here as it might disrupt user's current view
        self.update()
        
    def set_selected_indices(self, indices):
        """Compatibility method for setting selected indices."""
        self.selected_points = set(indices)
        if indices:
            self.selected_point_idx = indices[0]  # Set first selected as current
        else:
            self.selected_point_idx = -1
        self.update()
        
    def get_selected_indices(self):
        """Return list of currently selected indices."""
        return list(self.selected_points)
        
    def finalize_selection(self):
        """Select all points inside the selection rectangle."""
        if not self.selection_rect or not self.points:
            return
            
        # Calculate transform parameters
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
        
        # Transform function for point coordinates
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
        
        # Find all points within the selection rectangle
        selected = set()
        for i, (frame, x, y) in enumerate(self.points):
            tx, ty = transform_point(x, y)
            
            # Check if the point is within the selection rectangle
            if self.selection_rect.contains(int(tx), int(ty)):
                selected.add(i)
                
        # If Ctrl is pressed, toggle selection for these points
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            for idx in selected:
                if idx in self.selected_points:
                    self.selected_points.remove(idx)
                else:
                    self.selected_points.add(idx)
        else:
            # Otherwise replace current selection
            self.selected_points = selected
            
        # Update primary selection if we have selected points
        if self.selected_points:
            self.selected_point_idx = next(iter(self.selected_points))
            self.point_selected.emit(self.selected_point_idx)