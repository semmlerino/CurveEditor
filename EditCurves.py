#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                              QMessageBox, QSlider, QLineEdit, QGroupBox, QSplitter)
from PyQt5.QtCore import Qt, QPointF, pyqtSignal as Signal, pyqtSlot as Slot
from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath, QFont

class CurveView(QWidget):
    """Widget for displaying and editing the 2D tracking curve."""
    
    point_moved = Signal(int, float, float)  # Signal emitted when a point is moved
    
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
        
    def setPoints(self, points, image_width, image_height):
        """Set the points to display and adjust view accordingly."""
        self.points = points
        self.image_width = image_width
        self.image_height = image_height
        self.resetView()
        self.update()
        
    def resetView(self):
        """Reset view to show all points."""
        self.zoom_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.update()
        
    def paintEvent(self, event):
        """Draw the curve and points."""
        if not self.points:
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
            tx = widget_width - (x * scale_x + self.offset_x)  # Flip X axis to match 3DE4
            ty = y * scale_y + self.offset_y  # Match 3DE4 orientation (Y increases downward)
            return tx, ty
        
        # Draw the curve
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
                tx = widget_width - (x * scale_x + self.offset_x)  # Flip X axis to match 3DE4
                ty = y * scale_y + self.offset_y  # Match 3DE4 orientation
                
                # Check if within radius
                dx = event.x() - tx
                dy = event.y() - ty
                dist = math.sqrt(dx * dx + dy * dy)
                
                if dist <= self.point_radius + 2:  # +2 for better selection
                    self.selected_point_idx = i
                    self.drag_active = True
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
            new_x = (widget_width - event.x() - self.offset_x) / scale_x  # Flip X axis to match 3DE4
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
        
        img_center_x = (widget_width - center_x - self.offset_x) / old_scale_x  # Flip X axis to match 3DE4
        img_center_y = (center_y - self.offset_y) / old_scale_y
        
        # Apply zoom
        self.zoom_factor *= factor
        
        # Constrain zoom level
        self.zoom_factor = max(0.1, min(10.0, self.zoom_factor))
        
        # Calculate new scale factors
        new_scale_x = widget_width / self.image_width * self.zoom_factor
        new_scale_y = widget_height / self.image_height * self.zoom_factor
        
        # Adjust offset to keep the point under cursor fixed
        self.offset_x = widget_width - center_x - img_center_x * new_scale_x  # Flip X axis to match 3DE4
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

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self.setWindowTitle("3DE4 2D Curve Editor")
        self.resize(1200, 800)
        
        # Data storage
        self.curve_data = []
        self.point_name = ""
        self.point_color = 0
        self.image_width = 1920
        self.image_height = 1080
        
        # Create widgets
        self.setup_ui()
        
    def setup_ui(self):
        """Create and arrange UI elements."""
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.load_button = QPushButton("Load 2D Track")
        self.load_button.clicked.connect(self.load_track_data)
        
        self.save_button = QPushButton("Save 2D Track")
        self.save_button.clicked.connect(self.save_track_data)
        self.save_button.setEnabled(False)
        
        self.reset_view_button = QPushButton("Reset View")
        self.reset_view_button.clicked.connect(self.reset_view)
        
        toolbar_layout.addWidget(self.load_button)
        toolbar_layout.addWidget(self.save_button)
        toolbar_layout.addWidget(self.reset_view_button)
        toolbar_layout.addStretch()
        
        # Add info label
        self.info_label = QLabel("No data loaded")
        toolbar_layout.addWidget(self.info_label)
        
        main_layout.addLayout(toolbar_layout)
        
        # Splitter for main view and controls
        splitter = QSplitter(Qt.Vertical)
        
        # Curve view
        self.curve_view = CurveView()
        self.curve_view.point_moved.connect(self.on_point_moved)
        splitter.addWidget(self.curve_view)
        
        # Controls panel
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # Point edit controls
        point_group = QGroupBox("Point Editing")
        point_layout = QHBoxLayout(point_group)
        
        self.point_idx_label = QLabel("Point:")
        self.point_frame_label = QLabel("Frame: N/A")
        
        self.x_label = QLabel("X:")
        self.x_edit = QLineEdit()
        self.x_edit.setMaximumWidth(100)
        self.x_edit.returnPressed.connect(self.update_point_from_edit)
        
        self.y_label = QLabel("Y:")
        self.y_edit = QLineEdit()
        self.y_edit.setMaximumWidth(100)
        self.y_edit.returnPressed.connect(self.update_point_from_edit)
        
        self.update_point_button = QPushButton("Update")
        self.update_point_button.clicked.connect(self.update_point_from_edit)
        
        point_layout.addWidget(self.point_idx_label)
        point_layout.addWidget(self.point_frame_label)
        point_layout.addWidget(self.x_label)
        point_layout.addWidget(self.x_edit)
        point_layout.addWidget(self.y_label)
        point_layout.addWidget(self.y_edit)
        point_layout.addWidget(self.update_point_button)
        point_layout.addStretch()
        
        # Add controls to panel
        controls_layout.addWidget(point_group)
        
        # Add controls widget to splitter
        splitter.addWidget(controls_widget)
        
        # Set relative sizes
        splitter.setSizes([600, 200])
        
        main_layout.addWidget(splitter)
        
        self.setCentralWidget(main_widget)
        
        # Disable controls initially
        self.enable_point_controls(False)
        
    def enable_point_controls(self, enabled):
        """Enable or disable point editing controls."""
        self.x_edit.setEnabled(enabled)
        self.y_edit.setEnabled(enabled)
        self.update_point_button.setEnabled(enabled)
        
    def load_track_data(self):
        """Load 2D track data from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load 2D Track Data", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                
            if len(lines) < 4:
                QMessageBox.warning(self, "Error", "Invalid file format.")
                return
                
            # Parse header
            num_points = int(lines[0].strip())
            
            # We expect a single point
            if num_points != 1:
                QMessageBox.warning(self, "Warning", 
                                   f"File contains {num_points} points. Only the first point will be loaded.")
            
            line_idx = 1
            
            # Point name
            self.point_name = lines[line_idx].strip()
            line_idx += 1
            
            # Point color
            self.point_color = int(lines[line_idx].strip())
            line_idx += 1
            
            # Number of frames
            num_frames = int(lines[line_idx].strip())
            line_idx += 1
            
            # Read points
            self.curve_data = []
            
            for i in range(num_frames):
                if line_idx >= len(lines):
                    break
                    
                parts = lines[line_idx].strip().split()
                if len(parts) >= 3:
                    frame = int(parts[0])
                    x = float(parts[1])
                    y = float(parts[2])
                    self.curve_data.append((frame, x, y))
                    
                line_idx += 1
                
            # Determine image dimensions from the data
            if self.curve_data:
                max_x = max(x for _, x, _ in self.curve_data)
                max_y = max(y for _, _, y in self.curve_data)
                self.image_width = max(1920, int(max_x * 1.1))
                self.image_height = max(1080, int(max_y * 1.1))
            
            # Update view
            self.curve_view.setPoints(self.curve_data, self.image_width, self.image_height)
            self.save_button.setEnabled(True)
            
            # Update info
            self.info_label.setText(f"Loaded: {self.point_name} ({len(self.curve_data)} frames)")
            
            # Connect selection change
            self.curve_view.point_moved.connect(self.update_point_info)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
            
    def save_track_data(self):
        """Save modified 2D track data to a file."""
        if not self.curve_data:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save 2D Track Data", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w') as f:
                # Write header
                f.write("1\n")  # Number of points
                f.write(f"{self.point_name}\n")
                f.write(f"{self.point_color}\n")
                f.write(f"{len(self.curve_data)}\n")
                
                # Write points
                for frame, x, y in self.curve_data:
                    f.write(f"{frame} {x:.15f} {y:.15f}\n")
                    
            QMessageBox.information(self, "Success", "Track data saved successfully.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
            
    def reset_view(self):
        """Reset the curve view."""
        self.curve_view.resetView()
        
    def on_point_moved(self, idx, x, y):
        """Handle point moved in the view."""
        if 0 <= idx < len(self.curve_data):
            frame = self.curve_data[idx][0]
            self.curve_data[idx] = (frame, x, y)
            self.update_point_info(idx, x, y)
            
    def update_point_info(self, idx, x, y):
        """Update the point information panel."""
        if 0 <= idx < len(self.curve_data):
            frame = self.curve_data[idx][0]
            self.point_idx_label.setText(f"Point: {idx}")
            self.point_frame_label.setText(f"Frame: {frame}")
            self.x_edit.setText(f"{x:.3f}")
            self.y_edit.setText(f"{y:.3f}")
            self.enable_point_controls(True)
        else:
            self.point_idx_label.setText("Point:")
            self.point_frame_label.setText("Frame: N/A")
            self.x_edit.clear()
            self.y_edit.clear()
            self.enable_point_controls(False)
            
    def update_point_from_edit(self):
        """Update point from edit fields."""
        idx = self.curve_view.selected_point_idx
        if idx < 0 or idx >= len(self.curve_data):
            return
            
        try:
            x = float(self.x_edit.text())
            y = float(self.y_edit.text())
            
            frame = self.curve_data[idx][0]
            self.curve_data[idx] = (frame, x, y)
            
            self.curve_view.update()
            
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid coordinate values.")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()