# -*- coding: utf-8 -*-

import os
import math
from PySide6.QtWidgets import QWidget, QApplication, QGridLayout, QMenu
from PySide6.QtCore import Qt, QPointF, Signal, Slot, QRect
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QFont, QImage, QPixmap, QBrush, QAction
import re


class EnhancedCurveView(QWidget):
    """Enhanced widget for displaying and editing the 2D tracking curve with 
    added visualization options like grid, vectors, and all frame numbers."""
    
    point_moved = Signal(int, float, float)  # Signal emitted when a point is moved
    point_selected = Signal(int)  # Signal emitted when a point is selected
    image_changed = Signal(int)  # Signal emitted when image changes via keyboard
    
    def __init__(self, parent=None):
        """Initialize the view."""
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
        self.point_radius = 2  # Default point radius (smaller)
        self.setFocusPolicy(Qt.StrongFocus)
        self.display_precision = 2  # Default precision for coordinate display
        
        # Enhanced visual options
        self.show_grid = True
        self.grid_spacing = 100
        self.grid_line_width = 1
        self.grid_color = QColor(100, 100, 120, 150)  # Default grid color (semi-transparent gray-blue)
        self.show_velocity_vectors = False
        self.velocity_vector_scale = 5.0  # Default scale for velocity vectors
        self.show_all_frame_numbers = False
        self.scale_to_image = True
        self.flip_y_axis = True
        self.show_background = True
        
        # Point status colors
        self.normal_point_color = QColor(220, 220, 220, 200)
        self.normal_point_border = QColor(200, 200, 200)
        self.selected_point_color = QColor(255, 80, 80, 150)
        self.selected_point_border = QColor(255, 80, 80)
        self.interpolated_point_color = QColor(100, 180, 255, 150)
        self.interpolated_point_border = QColor(80, 160, 240)
        
        # Image background properties
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
        
        # Nudging increments
        self.nudge_increment = 1.0
        self.available_increments = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        self.current_increment_index = 2  # Default to 1.0
        
        # For panning
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.initial_offset_x = 0
        self.initial_offset_y = 0
        
    def setPoints(self, points, image_width, image_height, preserve_view=False):
        """Set the points to display and adjust view accordingly.
        
        Args:
            points: List of points in format [(frame, x, y), ...] or [(frame, x, y, status), ...]
            image_width: Width of the image/workspace
            image_height: Height of the image/workspace
            preserve_view: If True, maintain current view position
        """
        from visualization_operations import VisualizationOperations
        VisualizationOperations.set_points(self, points, image_width, image_height, preserve_view)
        
    def setImageSequence(self, path, filenames):
        """Set the image sequence to display as background."""
        from image_operations import ImageOperations
        ImageOperations.set_image_sequence(self, path, filenames)
        
    def toggleGrid(self, enabled=None):
        """Toggle grid visibility."""
        from visualization_operations import VisualizationOperations
        VisualizationOperations.toggle_grid_internal(self, enabled)
        
    def toggleVelocityVectors(self, enabled=None):
        """Toggle velocity vector display."""
        from visualization_operations import VisualizationOperations
        VisualizationOperations.toggle_velocity_vectors_internal(self, enabled)
        
    def toggleAllFrameNumbers(self, enabled=None):
        """Toggle display of all frame numbers."""
        from visualization_operations import VisualizationOperations
        VisualizationOperations.toggle_all_frame_numbers_internal(self, enabled)
        
    
    def centerOnSelectedPoint(self, point_idx=-1, preserve_zoom=True):
        """Center the view on the specified point index.
        
        If no index is provided, uses the currently selected point.
        
        Args:
            point_idx: Index of point to center on. Default -1 uses selected point.
            preserve_zoom: If True, maintain current zoom level. If False, reset view.
        """
        from visualization_operations import VisualizationOperations
        return VisualizationOperations.center_on_selected_point(self, point_idx, preserve_zoom)
        
    def setCoordinatePrecision(self, precision):
        """Set decimal precision for coordinate display."""
        self.display_precision = max(1, min(precision, 6))
        self.update()
        
    def setCurrentImageByFrame(self, frame):
        """Set the current background image based on frame number."""
        from image_operations import ImageOperations
        ImageOperations.set_current_image_by_frame(self, frame)
            
    def setCurrentImageByIndex(self, idx):
        """Set current image by index and update the view."""
        from image_operations import ImageOperations
        ImageOperations.set_current_image_by_index(self, idx)
        
    def toggleBackgroundVisible(self, visible=None):
        """Toggle visibility of background image."""
        from visualization_operations import VisualizationOperations
        VisualizationOperations.toggle_background_visible_internal(self, visible)
        
    def setBackgroundOpacity(self, opacity):
        """Set the opacity of the background image."""
        from visualization_operations import VisualizationOperations
        VisualizationOperations.set_background_opacity(self, opacity)
        
    def loadCurrentImage(self):
        """Load the current image in the sequence."""
        from image_operations import ImageOperations
        ImageOperations.load_current_image(self)
            
    def resetView(self):
        """Reset view to default state (zoom and position)."""
        from visualization_operations import VisualizationOperations
        VisualizationOperations.reset_view(self)
        
    def set_point_radius(self, radius):
        """Set the point display radius.
        
        Args:
            radius: Integer representing the point radius (1-10)
        """
        from curve_view_operations import CurveViewOperations
        CurveViewOperations.set_point_radius(self, radius)
        
    def get_point_data(self, index):
        """Get point data as a tuple (frame, x, y, status).
        
        Args:
            index: Index of the point to get data for
            
        Returns:
            Tuple of (frame, x, y, status) or None if index is invalid
        """
        from curve_view_operations import CurveViewOperations
        return CurveViewOperations.get_point_data(self, index)
        
    def findPointAt(self, pos):
        """Find a point at the given position.
        
        Args:
            pos: QPoint with screen coordinates
            
        Returns:
            Index of the found point or -1 if no point was found
        """
        from curve_view_operations import CurveViewOperations
        return CurveViewOperations.find_point_at(self, pos.x(), pos.y())
    
    def findClosestPointByFrame(self, frame_num):
        """Find the point closest to the given frame number.
        
        Args:
            frame_num: The frame number to find the closest point to
            
        Returns:
            Index of the closest point or -1 if no points are available
        """
        from curve_view_operations import CurveViewOperations
        return CurveViewOperations.find_closest_point_by_frame(self, frame_num)
        
    def toggle_point_interpolation(self, index):
        """Toggle the interpolation status of a point.
        
        Args:
            index: Index of the point to toggle
            
        Returns:
            bool: True if the toggle was successful, False otherwise
        """
        from curve_view_operations import CurveViewOperations
        return CurveViewOperations.toggle_point_interpolation(self, index)
        
    def finalize_selection(self):
        """Select all points inside the selection rectangle."""
        from curve_view_operations import CurveViewOperations
        CurveViewOperations.finalize_selection(self)
        
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
            from curve_view_operations import CurveViewOperations
            return CurveViewOperations.transform_point(self, x, y, display_width, display_height, offset_x, offset_y, scale)
        
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
                
                # Convert from image coordinates to track coordinates
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
            painter.setPen(QPen(self.grid_color, self.grid_line_width, Qt.DotLine))
            
            # Calculate the range of grid lines to draw
            grid_min_x = 0
            grid_max_x = display_width
            grid_min_y = 0
            grid_max_y = display_height
            
            # Center grid on selected point if available
            grid_center_x = 0
            grid_center_y = 0
            
            if self.selected_point_idx >= 0 and self.selected_point_idx < len(self.points):
                # Use get_point_data to safely handle points with different structures
                point_data = self.get_point_data(self.selected_point_idx)
                if point_data:
                    frame, center_x, center_y, _ = point_data
                    grid_center_x = center_x
                    grid_center_y = center_y
                
                if self.debug_mode:
                    print(f"EnhancedCurveView: Centering grid on point at ({grid_center_x}, {grid_center_y})")
            
            # Calculate grid line positions centered on the selected point
            # Draw horizontal grid lines
            # Start from the center and go in both directions
            y = grid_center_y - (int(grid_center_y / self.grid_spacing) * self.grid_spacing)
            while y <= grid_max_y:
                tx1, ty = transform_point(grid_min_x, y)
                tx2, _ = transform_point(grid_max_x, y)
                painter.drawLine(int(tx1), int(ty), int(tx2), int(ty))
                y += self.grid_spacing
                
            y = grid_center_y - self.grid_spacing
            while y >= grid_min_y:
                tx1, ty = transform_point(grid_min_x, y)
                tx2, _ = transform_point(grid_max_x, y)
                painter.drawLine(int(tx1), int(ty), int(tx2), int(ty))
                y -= self.grid_spacing
                
            # Draw vertical grid lines
            # Start from the center and go in both directions
            x = grid_center_x - (int(grid_center_x / self.grid_spacing) * self.grid_spacing)
            while x <= grid_max_x:
                tx, ty1 = transform_point(x, grid_min_y)
                _, ty2 = transform_point(x, grid_max_y)
                painter.drawLine(int(tx), int(ty1), int(tx), int(ty2))
                x += self.grid_spacing
                
            x = grid_center_x - self.grid_spacing
            while x >= grid_min_x:
                tx, ty1 = transform_point(x, grid_min_y)
                _, ty2 = transform_point(x, grid_max_y)
                painter.drawLine(int(tx), int(ty1), int(tx), int(ty2))
                x -= self.grid_spacing
                
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
                    # Extract only frame, x, y even if there's a status
                    prev_point = sorted_points[i-1]
                    prev_frame, prev_x, prev_y = prev_point[:3]
                    
                    curr_point = sorted_points[i]
                    curr_frame, curr_x, curr_y = curr_point[:3]
                    
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
            
            if self.points:
                # Start with the first point
                point = self.points[0]
                frame, x, y = point[:3]  # Extract only frame, x, y even if there's a status
                tx, ty = transform_point(x, y)
                path.moveTo(tx, ty)
                
                # Connect subsequent points
                for i in range(1, len(self.points)):
                    point = self.points[i]
                    frame, x, y = point[:3]  # Extract only frame, x, y even if there's a status
                    tx, ty = transform_point(x, y)
                    path.lineTo(tx, ty)
            
            # Draw the curve
            painter.drawPath(path)
            
            # Draw points
            for i in range(len(self.points)):
                point = self.points[i]
                frame, x, y = point[:3]  # Extract only frame, x, y even if there's a status
                tx, ty = transform_point(x, y)
                
                # Determine if point is selected (either primary selection or in multi-selection)
                is_selected = (i == self.selected_point_idx) or (i in self.selected_points)
                
                # Check if point has interpolated status (4th tuple element)
                is_interpolated = False
                if len(point) > 3 and point[3] == 'interpolated':
                    is_interpolated = True
                
                if is_selected:
                    painter.setPen(QPen(self.selected_point_border, 2))
                    painter.setBrush(self.selected_point_color)
                    point_radius = self.point_radius + 2
                elif is_interpolated:
                    painter.setPen(QPen(self.interpolated_point_border, 1))
                    painter.setBrush(self.interpolated_point_color)
                    point_radius = self.point_radius
                else:
                    painter.setPen(QPen(self.normal_point_border, 1))
                    painter.setBrush(self.normal_point_color)
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
            point = self.points[self.selected_point_idx]
            frame, x, y = point[:3]  # Extract only frame, x, y even if there's a status
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
            shortcuts += " | Alt+Drag: Select multiple points"
            painter.drawText(10, 80, shortcuts)
            
            # Display nudge increment value with visual indicator
            nudge_info = f"Nudge Increment: {self.nudge_increment:.1f}"
            
            # Create a visual indicator showing the current increment position
            indicator_width = 200
            indicator_height = 20
            indicator_x = 10
            indicator_y = 100
            
            # Draw background bar
            painter.setBrush(QColor(50, 50, 50, 180))
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.drawRect(indicator_x, indicator_y, indicator_width, indicator_height)
            
            # Draw increment markers and labels
            for i, increment in enumerate(self.available_increments):
                # Calculate position for this increment
                pos_x = indicator_x + (i / (len(self.available_increments) - 1)) * indicator_width
                
                # Draw tick mark
                painter.setPen(QPen(QColor(150, 150, 150), 1))
                painter.drawLine(int(pos_x), indicator_y, int(pos_x), indicator_y + indicator_height)
                
                # Draw value label
                painter.setPen(QPen(QColor(200, 200, 200), 1))
                painter.drawText(int(pos_x - 10), indicator_y + indicator_height + 15, f"{increment:.1f}")
            
            # Draw cursor position for current increment
            current_pos_x = indicator_x + (self.current_increment_index / (len(self.available_increments) - 1)) * indicator_width
            
            # Draw triangle cursor
            cursor_size = 8
            painter.setBrush(QColor(255, 200, 0))
            painter.setPen(Qt.NoPen)
            cursor_points = [
                QPointF(current_pos_x, indicator_y - cursor_size),
                QPointF(current_pos_x - cursor_size, indicator_y - cursor_size * 2),
                QPointF(current_pos_x + cursor_size, indicator_y - cursor_size * 2)
            ]
            painter.drawPolygon(cursor_points)
            
            # Draw increment value
            painter.setPen(QPen(QColor(255, 200, 0), 1))
            painter.drawText(indicator_x + indicator_width + 10, indicator_y + indicator_height // 2 + 5, 
                           f"Current: {self.nudge_increment:.1f}")
            
            # Draw up/down arrow instructions
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawText(indicator_x, indicator_y + indicator_height + 35, 
                           "Use ↑/↓ keys to change nudge increment")
            
    def mousePressEvent(self, event):
        """Handle mouse press to select or move points."""
        from curve_view_operations import CurveViewOperations
        CurveViewOperations.handle_mouse_press(self, event)
            
    def mouseMoveEvent(self, event):
        """Handle mouse movement for dragging points or panning."""
        from curve_view_operations import CurveViewOperations
        CurveViewOperations.handle_mouse_move(self, event)
            
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        from curve_view_operations import CurveViewOperations
        CurveViewOperations.handle_mouse_release(self, event)
        
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        
        # Get mouse position for zoom centering
        position = event.position()
        mouse_x = position.x()
        mouse_y = position.y()
        
        # Use centralized zoom method from visualization_operations
        from visualization_operations import VisualizationOperations
        VisualizationOperations.zoom_view(self, factor, mouse_x, mouse_y)
        
    def keyPressEvent(self, event):
        """Handle key press events for navigation and shortcuts."""
        from visualization_operations import VisualizationOperations
        from curve_view_operations import CurveViewOperations
        
        # Try visualization operations first
        if VisualizationOperations.handle_key_press(self, event):
            return
            
        # Then try curve view operations
        if CurveViewOperations.handle_key_press(self, event):
            return
            
        # If no handler processed the key, call the parent implementation
        super().keyPressEvent(event)
        
    def selectAllPoints(self):
        """Select all points in the curve."""
        from curve_view_operations import CurveViewOperations
        CurveViewOperations.select_all_points(self)
        
    def clearSelection(self):
        """Clear all point selections."""
        from curve_view_operations import CurveViewOperations
        CurveViewOperations.clear_selection(self)
        
    def selectPointByIndex(self, index):
        """Select a point by its index."""
        from curve_view_operations import CurveViewOperations
        return CurveViewOperations.select_point_by_index(self, index)
        
    def set_curve_data(self, curve_data):
        """Compatibility method for curve_data from main_window."""
        from curve_view_operations import CurveViewOperations
        CurveViewOperations.set_curve_data(self, curve_data)
        
    def set_selected_indices(self, indices):
        """Compatibility method for setting selected indices."""
        from curve_view_operations import CurveViewOperations
        CurveViewOperations.set_selected_indices(self, indices)
        
    def change_nudge_increment(self, increase=True):
        """Change the nudge increment for point movement."""
        from curve_view_operations import CurveViewOperations
        return CurveViewOperations.change_nudge_increment(self, increase)
    
    def nudge_selected_points(self, dx=0, dy=0):
        """Nudge selected points by the specified delta."""
        from curve_view_operations import CurveViewOperations
        return CurveViewOperations.nudge_selected_points(self, dx, dy)
    
    def update_point_position(self, index, x, y):
        """Update a point's position while preserving its status."""
        from curve_view_operations import CurveViewOperations
        return CurveViewOperations.update_point_position(self, index, x, y)
        
    def contextMenuEvent(self, event):
        """Show context menu with point options."""
        menu = QMenu(self)
        
        # Get clicked point (if any)
        mouse_pos = event.pos()
        selected_point_index = self.findPointAt(mouse_pos)
        
        if selected_point_index >= 0:
            # If a point was clicked, add point-specific actions
            point_info = self.get_point_data(selected_point_index)
            if point_info:
                frame, x, y, status = point_info
                
                # Add point information header
                menu.addSection(f"Point {selected_point_index}: Frame {frame}, ({x:.2f}, {y:.2f})")
                
                # Add select point action
                if selected_point_index != self.selected_point_idx:
                    select_action = QAction("Select this point", self)
                    select_action.triggered.connect(lambda: self.selectPointByIndex(selected_point_index))
                    menu.addAction(select_action)
                
                # Add interpolation toggle based on current status
                is_interpolated = status == 'interpolated'
                toggle_text = "Restore to normal point" if is_interpolated else "Mark as interpolated"
                toggle_action = QAction(toggle_text, self)
                toggle_action.triggered.connect(lambda: self.toggle_point_interpolation(selected_point_index))
                menu.addAction(toggle_action)
                
                menu.addSeparator()
                
        # Add view options
        grid_action = QAction("Hide Grid" if self.show_grid else "Show Grid", self)
        grid_action.triggered.connect(self.toggleGrid)
        menu.addAction(grid_action)
        
        # Execute the menu
        menu.exec_(event.globalPos())
    
    def extractFrameNumber(self, img_idx):
        """Extract frame number from the current image index."""
        from curve_view_operations import CurveViewOperations
        return CurveViewOperations.extract_frame_number(self, img_idx)