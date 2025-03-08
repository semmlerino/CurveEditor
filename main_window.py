#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import math
import copy

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QFileDialog, QMessageBox, QSlider, QLineEdit, 
                              QGroupBox, QSplitter, QDialog)
from PyQt5.QtCore import Qt, pyqtSlot as Slot

from curve_view import CurveView
from dialogs import (SmoothingDialog, FilterDialog, FillGapsDialog, 
                     ExtrapolateDialog, ProblemDetectionDialog)
import curve_operations as ops
import utils
import config

# Import the separated modules
from ui_components import UIComponents
from file_operations import FileOperations
from image_operations import ImageOperations
from timeline_operations import TimelineOperations
from history_operations import HistoryOperations


class MainWindow(QMainWindow):
    """Main application window for 3DE4 Curve Editor."""
    
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
        
        # Set the curve view class
        self.curve_view_class = CurveView
        
        # Default directory for 3DE points
        self.default_directory = "/home/gabriel-ha/3DEpoints"
        if not os.path.exists(self.default_directory):
            # Fallback to home directory if the specified path doesn't exist
            self.default_directory = os.path.expanduser("~")
            
        # Image sequence
        self.image_sequence_path = ""
        self.image_filenames = []
            
        # Undo/redo history
        self.history = []
        self.history_index = -1
        self.max_history = 20  # Maximum number of history states to keep
        
        # Create widgets
        self.setup_ui()
        
        # Install event filter for key navigation
        self.installEventFilter(self)
        
        # Load previously used file if it exists
        self.load_previous_file()
        
    def setup_ui(self):
        """Create and arrange UI elements."""
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Create toolbar
        toolbar_layout = self.create_toolbar()
        main_layout.addLayout(toolbar_layout)
        
        # Create splitter for main view and controls
        splitter = QSplitter(Qt.Vertical)
        
        # Create curve view and timeline
        view_container = self.create_view_and_timeline()
        splitter.addWidget(view_container)
        
        # Create control panel
        controls_widget = self.create_control_panel()
        splitter.addWidget(controls_widget)
        
        # Set relative sizes
        splitter.setSizes([600, 200])
        
        main_layout.addWidget(splitter)
        
        self.setCentralWidget(main_widget)
        
    def create_toolbar(self):
        """Create the toolbar with action buttons."""
        return UIComponents.create_toolbar(self)
        
    def create_view_and_timeline(self):
        """Create the curve view widget and timeline controls."""
        # Create the view container using UIComponents
        view_container = UIComponents.create_view_and_timeline(self)
        
        # Connect signals
        self.curve_view.point_moved.connect(self.on_point_moved)
        self.curve_view.point_selected.connect(self.on_point_selected)
        self.curve_view.image_changed.connect(self.on_image_changed)
        self.timeline_slider.valueChanged.connect(self.on_timeline_changed)
        self.frame_edit.returnPressed.connect(self.on_frame_edit_changed)
        self.go_button.clicked.connect(self.on_frame_edit_changed)
        self.prev_image_button.clicked.connect(self.previous_image)
        self.next_image_button.clicked.connect(self.next_image)
        self.opacity_slider.valueChanged.connect(self.opacity_changed)
        
        return view_container

    def create_control_panel(self):
        """Create the control panel for point editing."""
        controls_widget = UIComponents.create_control_panel(self)
        
        # Connect signals
        self.x_edit.returnPressed.connect(self.update_point_from_edit)
        self.y_edit.returnPressed.connect(self.update_point_from_edit)
        self.update_point_button.clicked.connect(self.update_point_from_edit)
        
        # Disable controls initially
        self.enable_point_controls(False)
        
        return controls_widget

    def enable_point_controls(self, enabled):
        """Enable or disable point editing controls."""
        self.x_edit.setEnabled(enabled)
        self.y_edit.setEnabled(enabled)
        self.update_point_button.setEnabled(enabled)

    def eventFilter(self, obj, event):
        """Global event filter for keyboard navigation."""
        if event.type() == event.KeyPress:
            if event.key() == Qt.Key_Left:
                # Previous image
                self.previous_image()
                return True
            elif event.key() == Qt.Key_Right:
                # Next image
                self.next_image()
                return True
                
        return super(MainWindow, self).eventFilter(obj, event)
    
    # File Operations
    def load_track_data(self):
        """Load 2D track data from a file."""
        FileOperations.load_track_data(self)

    def add_track_data(self):
        """Add an additional 2D track to the current data."""
        FileOperations.add_track_data(self)

    def save_track_data(self):
        """Save modified 2D track data to a file."""
        FileOperations.save_track_data(self)
    
    # Image Sequence Operations
    def load_image_sequence(self):
        """Load an image sequence to use as background."""
        ImageOperations.load_image_sequence(self)

    def previous_image(self):
        """Show the previous image in the sequence."""
        ImageOperations.previous_image(self)

    def next_image(self):
        """Show the next image in the sequence."""
        ImageOperations.next_image(self)

    def update_image_label(self):
        """Update the image label with current image info."""
        ImageOperations.update_image_label(self)

    def toggle_background(self):
        """Toggle background image visibility."""
        ImageOperations.toggle_background(self)

    def opacity_changed(self, value):
        """Handle opacity slider value changed."""
        opacity = value / 100.0  # Convert from 0-100 to 0.0-1.0
        self.curve_view.setBackgroundOpacity(opacity)

    def on_image_changed(self, index):
        """Handle image changed via keyboard navigation."""
        self.update_image_label()
        
    def load_previous_file(self):
        """Load the previously used file and folder if they exist."""
        # Check for last folder path and update default directory
        folder_path = config.get_last_folder_path()
        if folder_path and os.path.exists(folder_path):
            self.default_directory = folder_path
            
        # Load last file if it exists
        file_path = config.get_last_file_path()
        if file_path and os.path.exists(file_path):
            # Load track data from file
            point_name, point_color, num_frames, curve_data = utils.load_3de_track(file_path)
            
            if curve_data:
                # Set the data
                self.point_name = point_name
                self.point_color = point_color
                self.curve_data = curve_data
                
                # Determine image dimensions from the data
                self.image_width, self.image_height = utils.estimate_image_dimensions(curve_data)
                
                # Update view
                self.curve_view.setPoints(self.curve_data, self.image_width, self.image_height)
                
                # Enable controls
                self.save_button.setEnabled(True)
                self.add_point_button.setEnabled(True)
                self.smooth_button.setEnabled(True)
                self.fill_gaps_button.setEnabled(True)
                self.filter_button.setEnabled(True)
                self.detect_problems_button.setEnabled(True)
                self.extrapolate_button.setEnabled(True)
                
                # Update info
                self.info_label.setText(f"Loaded: {self.point_name} ({len(self.curve_data)} frames)")
                
                # Setup timeline
                self.setup_timeline()
                
                # Enable timeline controls
                self.timeline_slider.setEnabled(True)
                self.frame_edit.setEnabled(True)
                self.go_button.setEnabled(True)
                
                # Add to history
                self.add_to_history()
        
        # Load last image sequence if it exists
        self.load_previous_image_sequence()
    
    def load_previous_image_sequence(self):
        """Load the previously used image sequence if it exists."""
        # Check for last image sequence path
        sequence_path = config.get_last_image_sequence_path()
        if sequence_path and os.path.exists(sequence_path):
            # Find all image files in the directory
            image_files = utils.get_image_files(sequence_path)
            
            if image_files:
                # Set the image sequence
                self.image_sequence_path = sequence_path
                self.image_filenames = image_files
                
                # Setup the curve view with images
                self.curve_view.setImageSequence(sequence_path, image_files)
                
                # Update the UI
                self.update_image_label()
                self.toggle_bg_button.setEnabled(True)
                self.opacity_slider.setEnabled(True)

    # Timeline Operations
    def setup_timeline(self):
        """Setup timeline slider based on frame range."""
        TimelineOperations.setup_timeline(self)

    def on_timeline_changed(self, value):
        """Handle timeline slider value changed."""
        TimelineOperations.on_timeline_changed(self, value)

    def on_frame_edit_changed(self):
        """Handle frame edit text changed."""
        TimelineOperations.on_frame_edit_changed(self)

    # Point Editing Operations
    def on_point_selected(self, idx):
        """Handle point selection in the view."""
        if 0 <= idx < len(self.curve_data):
            frame, x, y = self.curve_data[idx]
            self.update_point_info(idx, x, y)
            
            # Update timeline
            self.timeline_slider.setValue(frame)

    def on_point_moved(self, idx, x, y):
        """Handle point moved in the view."""
        if 0 <= idx < len(self.curve_data):
            frame = self.curve_data[idx][0]
            self.curve_data[idx] = (frame, x, y)
            self.update_point_info(idx, x, y)
            
            # Add to history
            self.add_to_history()

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
            
            # Add to history
            self.add_to_history()
            
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid coordinate values.")

    # View Operations
    def reset_view(self):
        """Reset the curve view."""
        self.curve_view.resetView()

    # History Operations
    def add_to_history(self):
        """Add current state to history."""
        HistoryOperations.add_to_history(self)

    def update_history_buttons(self):
        """Update the state of undo/redo buttons."""
        HistoryOperations.update_history_buttons(self)

    def undo_action(self):
        """Undo the last action."""
        HistoryOperations.undo_action(self)

    def redo_action(self):
        """Redo the previously undone action."""
        HistoryOperations.redo_action(self)

    def restore_state(self, state):
        """Restore application state from history."""
        HistoryOperations.restore_state(self, state)

    # Dialog Operations
    def show_smooth_dialog(self):
        """Show dialog for curve smoothing."""
        if not self.curve_data or len(self.curve_data) < 3:
            QMessageBox.information(self, "Info", "Not enough points to smooth curve.")
            return
            
        frames = [frame for frame, _, _ in self.curve_data]
        min_frame = min(frames)
        max_frame = max(frames)
        
        current_frame = min_frame
        if self.curve_view.selected_point_idx >= 0:
            current_frame = self.curve_data[self.curve_view.selected_point_idx][0]
        
        dialog = SmoothingDialog(self, min_frame, max_frame, current_frame)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        # Get smoothing parameters
        method = dialog.method_combo.currentIndex()
        range_type = dialog.range_combo.currentIndex()
        
        # Determine points to smooth
        points_to_smooth = []
        
        if range_type == 0:  # Entire curve
            points_to_smooth = list(range(len(self.curve_data)))
        elif range_type == 1:  # Selected range
            start_frame = dialog.start_frame.value()
            end_frame = dialog.end_frame.value()
            
            for i, (frame, _, _) in enumerate(self.curve_data):
                if start_frame <= frame <= end_frame:
                    points_to_smooth.append(i)
        elif range_type == 2:  # Current point only
            if self.curve_view.selected_point_idx >= 0:
                # Include a window around the current point
                window = dialog.window_spin.value() // 2
                center = self.curve_view.selected_point_idx
                
                for i in range(max(0, center - window), min(len(self.curve_data), center + window + 1)):
                    points_to_smooth.append(i)
        
        if not points_to_smooth:
            QMessageBox.warning(self, "Warning", "No points to smooth.")
            return
            
        # Apply the selected smoothing method
        if method == 0:  # Moving Average
            window_size = dialog.window_spin.value()
            self.curve_data = ops.smooth_moving_average(self.curve_data, points_to_smooth, window_size)
        elif method == 1:  # Gaussian
            window_size = dialog.window_spin.value()
            sigma = dialog.sigma_spin.value()
            self.curve_data = ops.smooth_gaussian(self.curve_data, points_to_smooth, window_size, sigma)
        elif method == 2:  # Savitzky-Golay
            window_size = dialog.window_spin.value()
            self.curve_data = ops.smooth_savitzky_golay(self.curve_data, points_to_smooth, window_size)
        
        # Update view
        self.curve_view.setPoints(self.curve_data, self.image_width, self.image_height)
        
        # Add to history
        self.add_to_history()

    def show_filter_dialog(self):
        """Show dialog for applying filters to the curve."""
        if not self.curve_data or len(self.curve_data) < 3:
            QMessageBox.information(self, "Info", "Not enough points to apply filter.")
            return
            
        frames = [frame for frame, _, _ in self.curve_data]
        min_frame = min(frames)
        max_frame = max(frames)
        
        current_frame = min_frame
        if self.curve_view.selected_point_idx >= 0:
            current_frame = self.curve_data[self.curve_view.selected_point_idx][0]
        
        dialog = FilterDialog(self, min_frame, max_frame, current_frame)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        # Get filter parameters
        filter_type = dialog.filter_combo.currentIndex()
        range_type = dialog.range_combo.currentIndex()
        
        # Determine points to filter
        points_to_filter = []
        
        if range_type == 0:  # Entire curve
            points_to_filter = list(range(len(self.curve_data)))
        elif range_type == 1:  # Selected range
            start_frame = dialog.start_frame.value()
            end_frame = dialog.end_frame.value()
            
            for i, (frame, _, _) in enumerate(self.curve_data):
                if start_frame <= frame <= end_frame:
                    points_to_filter.append(i)
        elif range_type == 2:  # Current point
            if self.curve_view.selected_point_idx >= 0:
                # Include a window around the current point
                window = 5  # Default window
                if filter_type == 0:  # Median
                    window = dialog.median_size.value()
                elif filter_type == 1:  # Gaussian
                    window = dialog.gaussian_size.value()
                elif filter_type == 2:  # Average
                    window = dialog.average_size.value()
                elif filter_type == 3:  # Butterworth
                    window = 11  # Default for Butterworth
                    
                half_window = window // 2
                
                center = self.curve_view.selected_point_idx
                for i in range(max(0, center - half_window), min(len(self.curve_data), center + half_window + 1)):
                    points_to_filter.append(i)
        
        if not points_to_filter:
            QMessageBox.warning(self, "Warning", "No points to filter.")
            return
            
        # Apply the selected filter
        if filter_type == 0:  # Median
            window_size = dialog.median_size.value()
            self.curve_data = ops.filter_median(self.curve_data, points_to_filter, window_size)
        elif filter_type == 1:  # Gaussian
            sigma = dialog.gaussian_sigma.value()
            window_size = dialog.gaussian_size.value()
            self.curve_data = ops.filter_gaussian(self.curve_data, points_to_filter, window_size, sigma)
        elif filter_type == 2:  # Average
            window_size = dialog.average_size.value()
            self.curve_data = ops.filter_average(self.curve_data, points_to_filter, window_size)
        elif filter_type == 3:  # Butterworth
            cutoff = dialog.butterworth_cutoff.value()
            order = dialog.butterworth_order.value()
            self.curve_data = ops.filter_butterworth(self.curve_data, points_to_filter, cutoff, order)
        
        # Update view
        self.curve_view.setPoints(self.curve_data, self.image_width, self.image_height)
        
        # Add to history
        self.add_to_history()

    def show_fill_gaps_dialog(self):
        """Show dialog for filling gaps in the tracking data."""
        if not self.curve_data or len(self.curve_data) < 2:
            QMessageBox.information(self, "Info", "Not enough tracking data to fill gaps.")
            return
            
        frames = [frame for frame, _, _ in self.curve_data]
        min_frame = min(frames)
        max_frame = max(frames)
        
        dialog = FillGapsDialog(self, min_frame, max_frame)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        # Get fill parameters
        method = dialog.method_combo.currentIndex()
        auto_detect = dialog.auto_detect.isChecked()
        preserve_endpoints = dialog.preserve_endpoints.isChecked()
        
        # Determine frame range to fill
        if auto_detect:
            # Find gaps in the data
            gaps = self.detect_gaps()
            if not gaps:
                QMessageBox.information(self, "Info", "No gaps detected in the tracking data.")
                return
                
            # Fill all detected gaps
            for start_frame, end_frame in gaps:
                self.fill_gap(start_frame, end_frame, method, dialog, preserve_endpoints)
        else:
            # Use user-specified range
            start_frame = dialog.start_frame.value()
            end_frame = dialog.end_frame.value()
            
            # Verify range
            if start_frame >= end_frame:
                QMessageBox.warning(self, "Warning", "End frame must be greater than start frame.")
                return
                
            # Fill the specified gap
            self.fill_gap(start_frame, end_frame, method, dialog, preserve_endpoints)
            
        # Update view
        self.curve_view.setPoints(self.curve_data, self.image_width, self.image_height)
        
        # Update timeline
        self.setup_timeline()
        
        # Add to history
        self.add_to_history()
    
    def detect_gaps(self):
        """Detect gaps in the tracking data."""
        if not self.curve_data or len(self.curve_data) < 2:
            return []
            
        # Sort by frame
        sorted_data = sorted(self.curve_data, key=lambda x: x[0])
        
        # Find gaps
        gaps = []
        for i in range(1, len(sorted_data)):
            prev_frame = sorted_data[i-1][0]
            curr_frame = sorted_data[i][0]
            
            if curr_frame - prev_frame > 1:
                # Found a gap
                gaps.append((prev_frame + 1, curr_frame - 1))
                
        return gaps
    
    def fill_gap(self, start_frame, end_frame, method, dialog, preserve_endpoints):
        """Fill a gap in the tracking data using the specified method."""
        if method == 0:  # Linear Interpolation
            self.curve_data = ops.fill_linear(self.curve_data, start_frame, end_frame, preserve_endpoints)
        elif method == 1:  # Cubic Spline
            tension = dialog.cubic_tension.value()
            self.curve_data = ops.fill_cubic_spline(self.curve_data, start_frame, end_frame, tension, preserve_endpoints)
        elif method == 2:  # Constant Velocity
            window_size = dialog.velocity_window.value()
            self.curve_data = ops.fill_constant_velocity(self.curve_data, start_frame, end_frame, window_size, preserve_endpoints)
        elif method == 3:  # Accelerated Motion
            window_size = dialog.accel_window.value()
            accel_weight = dialog.accel_weight.value()
            self.curve_data = ops.fill_accelerated_motion(self.curve_data, start_frame, end_frame, window_size, accel_weight, preserve_endpoints)
        elif method == 4:  # Neighboring Frames Average
            window_size = dialog.avg_window.value()
            self.curve_data = ops.fill_average(self.curve_data, start_frame, end_frame, window_size, preserve_endpoints)

    def show_extrapolate_dialog(self):
        """Show dialog for extrapolating curve data."""
        if not self.curve_data or len(self.curve_data) < 3:
            QMessageBox.information(self, "Info", "Not enough points to extrapolate curve.")
            return
            
        frames = [frame for frame, _, _ in self.curve_data]
        min_frame = min(frames)
        max_frame = max(frames)
        
        dialog = ExtrapolateDialog(self, min_frame, max_frame)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        # Get extrapolation parameters
        direction = dialog.direction_combo.currentIndex()
        forward_frames = dialog.forward_frames.value()
        backward_frames = dialog.backward_frames.value()
        method = dialog.method_combo.currentIndex()
        
        # Make a copy of the curve data
        original_data = copy.deepcopy(self.curve_data)
        
        # If quadratic, get number of points to fit
        fit_points = 5
        if method == 2:  # Quadratic
            fit_points = dialog.fit_points.value()
            
        # Extrapolate forward
        if direction == 0 or direction == 2:  # Forward or Both
            self.curve_data = ops.extrapolate_forward(self.curve_data, forward_frames, method, fit_points)
            
        # Extrapolate backward
        if direction == 1 or direction == 2:  # Backward or Both
            # We need a separate function for backward extrapolation
            # For now, we'll just indicate this would be implemented
            QMessageBox.information(self, "Info", "Backward extrapolation would be implemented here.")
            
        # Update view
        self.curve_view.setPoints(self.curve_data, self.image_width, self.image_height)
        
        # Update timeline
        self.setup_timeline()
        
        # Add to history
        self.add_to_history()

    def detect_problems(self):
        """Detect potential problems in the tracking data."""
        if not self.curve_data or len(self.curve_data) < 5:
            QMessageBox.information(self, "Info", "Not enough tracking data to detect problems.")
            return
            
        # Use the curve_operations function to detect problems
        problems = ops.detect_problems(self.curve_data)
        
        if not problems:
            QMessageBox.information(self, "Results", "No problems detected in the tracking data.")
            return
            
        # Show dialog with problems
        dialog = ProblemDetectionDialog(self, problems)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_problem:
            # Jump to the selected problem frame
            problem_frame = dialog.selected_problem[0]
            self.timeline_slider.setValue(problem_frame)


if __name__ == '__main__':
    # Using PyQt5 for consistency with the rest of the codebase
# Removed: from PySide2.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

