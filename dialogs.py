#!/usr/bin/env python
# -*- coding: utf-8 -*-
# mypy: disable-error-code=annotation-unchecked
from PySide6.QtCore import Qt  # type: ignore
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
                               QCheckBox, QGroupBox, QWidget, QSlider)  # type: ignore
from typing import Optional
from typing import Any


class SmoothingDialog(QDialog):
    """Dialog for curve smoothing options."""
    
    def __init__(self, parent: Optional[QWidget] = None, min_frame: int = 0, max_frame: int = 100, current_frame: int = 0) -> None:
        super(SmoothingDialog, self).__init__(parent)
        self.setWindowTitle("Smooth Curve")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Smoothing method
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Method:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Moving Average", "Gaussian", "Savitzky-Golay"])
        method_layout.addWidget(self.method_combo)
        layout.addLayout(method_layout)
        
        # Window size
        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel("Window Size:"))
        self.window_spin = QSpinBox()
        self.window_size_spin = self.window_spin
        self.window_spin.setMinimum(3)
        self.window_spin.setMaximum(25)
        self.window_spin.setSingleStep(2)  # Make it odd numbers only
        self.window_spin.setValue(5)
        window_layout.addWidget(self.window_spin)
        layout.addLayout(window_layout)
        
        # Sigma (for Gaussian)
        sigma_layout = QHBoxLayout()
        sigma_layout.addWidget(QLabel("Sigma:"))
        self.sigma_spin: QDoubleSpinBox = QDoubleSpinBox()
        self.cutoff_spin: Optional[QDoubleSpinBox] = None
        self.order_spin: Optional[QSpinBox] = None
        self.sigma_spin.setMinimum(0.5)
        self.sigma_spin.setMaximum(10.0)
        self.sigma_spin.setSingleStep(0.1)
        self.sigma_spin.setValue(1.0)
        sigma_layout.addWidget(self.sigma_spin)
        layout.addLayout(sigma_layout)
        
        # Frame range
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Apply to:"))
        self.range_combo = QComboBox()
        self.range_combo.addItems(["Entire Curve", "Selected Range", "Current Point Only", "Selected Points"])
        range_layout.addWidget(self.range_combo)
        layout.addLayout(range_layout)
        
        # Range selection
        self.range_group = QGroupBox("Frame Range")
        range_group_layout = QHBoxLayout(self.range_group)
        range_group_layout.addWidget(QLabel("Start:"))
        self.start_frame = QSpinBox()
        self.start_frame.setMinimum(min_frame)
        self.start_frame.setMaximum(max_frame)
        self.start_frame.setValue(min_frame)
        range_group_layout.addWidget(self.start_frame)
        range_group_layout.addWidget(QLabel("End:"))
        self.end_frame = QSpinBox()
        self.end_frame.setMinimum(min_frame)
        self.end_frame.setMaximum(max_frame)
        self.end_frame.setValue(max_frame)
        range_group_layout.addWidget(self.end_frame)
        layout.addWidget(self.range_group)
        
        # Preserve keyframes option
        self.preserve_keyframes = QCheckBox("Preserve Key Points")
        self.preserve_keyframes.setChecked(True)
        layout.addWidget(self.preserve_keyframes)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.range_combo.currentIndexChanged.connect(self.on_range_changed)
        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        
        # Set current frame if using "Current Point Only"
        self.current_frame = current_frame
        
        # Initial state
        self.on_range_changed(0)
        self.on_method_changed(0)
        
    def on_range_changed(self, index: int) -> None:
        """Handle range selection change."""
        # Enable frame range only for "Selected Range" (index 1)
        # Disable for "Entire Curve" (0), "Current Point Only" (2), and "Selected Points" (3)
        self.range_group.setEnabled(index == 1)
        
    def on_method_changed(self, index: int) -> None:
        """Handle method selection change."""
        # Show sigma only for Gaussian (which is at index 1)
        self.sigma_spin.setEnabled(index == 1)


class FilterDialog(QDialog):
    """Dialog for applying different filters to the curve data."""
    
    def __init__(self, parent: Optional[QWidget] = None, min_frame: int = 0, max_frame: int = 100, current_frame: int = 0) -> None:
        super(FilterDialog, self).__init__(parent)
        self.setWindowTitle("Apply Filter")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Filter type selection
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Median", "Gaussian", "Average", "Butterworth"])
        filter_layout.addWidget(self.filter_combo)
        layout.addLayout(filter_layout)
        
        # Frame range selection
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Apply to:"))
        self.range_combo = QComboBox()
        self.range_combo.addItems(["Entire Curve", "Selected Range", "Current Point"])
        range_layout.addWidget(self.range_combo)
        layout.addLayout(range_layout)
        
        # Range selection
        self.range_group = QGroupBox("Frame Range")
        range_group_layout = QHBoxLayout(self.range_group)
        range_group_layout.addWidget(QLabel("Start:"))
        self.start_frame = QSpinBox()
        self.start_frame.setMinimum(min_frame)
        self.start_frame.setMaximum(max_frame)
        self.start_frame.setValue(min_frame)
        range_group_layout.addWidget(self.start_frame)
        range_group_layout.addWidget(QLabel("End:"))
        self.end_frame = QSpinBox()
        self.end_frame.setMinimum(min_frame)
        self.end_frame.setMaximum(max_frame)
        self.end_frame.setValue(max_frame)
        range_group_layout.addWidget(self.end_frame)
        layout.addWidget(self.range_group)
        
        # Filter parameters
        self.param_group = QGroupBox("Filter Parameters")
        self.param_layout = QVBoxLayout(self.param_group)
        # Parameter UI elements will be added dynamically based on filter selection
        layout.addWidget(self.param_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)
        self.range_combo.currentIndexChanged.connect(self.on_range_changed)
        
        # Initialize UI
        self.create_param_widgets()
        self.on_filter_changed(0)
        self.on_range_changed(0)
        
        # Generic accessor for window size - adds compatibility with existing code
        self.window_size_spin: Optional[QSpinBox] = self.median_size
        self.sigma_spin: Optional[QDoubleSpinBox] = None
        self.cutoff_spin: Optional[QDoubleSpinBox] = None
        self.order_spin: Optional[QSpinBox] = None
        
    def create_param_widgets(self):
        """Create all parameter widgets for different filters."""
        # Median filter parameters
        self.median_widgets: list[tuple[QHBoxLayout, str]] = []
        median_layout = QHBoxLayout()
        median_layout.addWidget(QLabel("Window Size:"))
        self.median_size = QSpinBox()
        self.median_size.setMinimum(3)
        self.median_size.setMaximum(21)
        self.median_size.setSingleStep(2)  # Ensure odd values
        self.median_size.setValue(5)
        median_layout.addWidget(self.median_size)
        self.median_widgets.append((median_layout, "median_layout"))
        
        # Gaussian filter parameters
        self.gaussian_widgets: list[tuple[QHBoxLayout, str]] = []
        gaussian_layout = QHBoxLayout()
        gaussian_layout.addWidget(QLabel("Sigma:"))
        self.gaussian_sigma = QDoubleSpinBox()
        self.gaussian_sigma.setMinimum(0.1)
        self.gaussian_sigma.setMaximum(10.0)
        self.gaussian_sigma.setSingleStep(0.1)
        self.gaussian_sigma.setValue(1.0)
        gaussian_layout.addWidget(self.gaussian_sigma)
        self.gaussian_widgets.append((gaussian_layout, "gaussian_layout"))
        gaussian_layout2 = QHBoxLayout()
        gaussian_layout2.addWidget(QLabel("Window Size:"))
        self.gaussian_size = QSpinBox()
        self.gaussian_size.setMinimum(3)
        self.gaussian_size.setMaximum(21)
        self.gaussian_size.setSingleStep(2)
        self.gaussian_size.setValue(5)
        gaussian_layout2.addWidget(self.gaussian_size)
        self.gaussian_widgets.append((gaussian_layout2, "gaussian_layout2"))
        
        # Average filter parameters
        self.average_widgets: list[tuple[QHBoxLayout, str]] = []
        average_layout = QHBoxLayout()
        average_layout.addWidget(QLabel("Window Size:"))
        self.average_size = QSpinBox()
        self.average_size.setMinimum(3)
        self.average_size.setMaximum(21)
        self.average_size.setSingleStep(2)
        self.average_size.setValue(5)
        average_layout.addWidget(self.average_size)
        self.average_widgets.append((average_layout, "average_layout"))
        
        # Butterworth filter parameters
        self.butterworth_widgets: list[tuple[QHBoxLayout, str]] = []
        butterworth_layout1 = QHBoxLayout()
        butterworth_layout1.addWidget(QLabel("Cutoff Frequency:"))
        self.butterworth_cutoff = QDoubleSpinBox()
        self.butterworth_cutoff.setMinimum(0.01)
        self.butterworth_cutoff.setMaximum(1.0)
        self.butterworth_cutoff.setSingleStep(0.01)
        self.butterworth_cutoff.setValue(0.1)
        butterworth_layout1.addWidget(self.butterworth_cutoff)
        self.butterworth_widgets.append((butterworth_layout1, "butterworth_layout1"))
        butterworth_layout2 = QHBoxLayout()
        butterworth_layout2.addWidget(QLabel("Order:"))
        self.butterworth_order = QSpinBox()
        self.butterworth_order.setMinimum(1)
        self.butterworth_order.setMaximum(8)
        self.butterworth_order.setValue(2)
        butterworth_layout2.addWidget(self.butterworth_order)
        self.butterworth_widgets.append((butterworth_layout2, "butterworth_layout2"))
        
    def on_filter_changed(self, index: int) -> None:
        """Update parameter widgets based on selected filter."""
        # Clear existing parameter widgets
        while self.param_layout.count():
            item = self.param_layout.takeAt(0)
            if item.layout():
                # Remove items from the layout
                while item.layout().count():
                    item_widget = item.layout().takeAt(0)
                    if item_widget.widget():
                        item_widget.widget().setParent(None)
        
        # Add new parameter widgets based on filter type
        if index == 0:  # Median
            for layout, _ in self.median_widgets:
                self.param_layout.addLayout(layout)
            # Update generic accessors
            self.window_size_spin = self.median_size
            self.sigma_spin = None
            self.cutoff_spin = None
            self.order_spin = None
        elif index == 1:  # Gaussian
            for layout, _ in self.gaussian_widgets:
                self.param_layout.addLayout(layout)
            # Update generic accessors
            self.window_size_spin = self.gaussian_size
            self.sigma_spin = self.gaussian_sigma
            self.cutoff_spin = None
            self.order_spin = None
        elif index == 2:  # Average
            for layout, _ in self.average_widgets:
                self.param_layout.addLayout(layout)
            # Update generic accessors
            self.window_size_spin = self.average_size
            self.sigma_spin = None
            self.cutoff_spin = None
            self.order_spin = None
        elif index == 3:  # Butterworth
            for layout, _ in self.butterworth_widgets:
                self.param_layout.addLayout(layout)
            # Update generic accessors
            self.window_size_spin = None
            self.sigma_spin = None
            self.cutoff_spin = self.butterworth_cutoff
            self.order_spin = self.butterworth_order
                
    def on_range_changed(self, index: int) -> None:
        """Handle range selection change."""
        self.range_group.setEnabled(index == 1)  # Enable range only for "Selected Range"


class FillGapsDialog(QDialog):
    """Dialog for filling gaps in the tracking data."""
    
    def __init__(self, parent: Optional[QWidget] = None, min_frame: int = 0, max_frame: int = 100):
        super(FillGapsDialog, self).__init__(parent)
        self.setWindowTitle("Fill Gaps")
        self.resize(450, 300)
        
        layout = QVBoxLayout(self)
        
        # Gap selection
        gap_group = QGroupBox("Gap Range")
        gap_layout = QVBoxLayout(gap_group)
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Start Frame:"))
        self.start_frame = QSpinBox()
        self.start_frame.setMinimum(min_frame)
        self.start_frame.setMaximum(max_frame)
        self.start_frame.setValue(min_frame)
        range_layout.addWidget(self.start_frame)
        range_layout.addWidget(QLabel("End Frame:"))
        self.end_frame = QSpinBox()
        self.end_frame.setMinimum(min_frame)
        self.end_frame.setMaximum(max_frame)
        self.end_frame.setValue(max_frame)
        range_layout.addWidget(self.end_frame)
        gap_layout.addLayout(range_layout)
        
        # Auto-detect gaps checkbox
        self.auto_detect = QCheckBox("Auto-detect gaps")
        self.auto_detect.setChecked(True)
        self.auto_detect.stateChanged.connect(self.on_auto_detect_changed)
        gap_layout.addWidget(self.auto_detect)
        
        # Preserve endpoints checkbox
        self.preserve_endpoints = QCheckBox("Preserve original points at gap boundaries")
        self.preserve_endpoints.setChecked(True)
        gap_layout.addWidget(self.preserve_endpoints)
        
        layout.addWidget(gap_group)
        
        # Method selection
        method_group = QGroupBox("Fill Method")
        method_layout = QVBoxLayout(method_group)
        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "Linear Interpolation", 
            "Cubic Spline",
            "Constant Velocity",
            "Accelerated Motion",
            "Neighboring Frames Average"
        ])
        method_layout.addWidget(self.method_combo)
        
        # Parameter UI based on method
        self.param_widget = QWidget()
        self.param_layout = QVBoxLayout(self.param_widget)
        method_layout.addWidget(self.param_widget)
        layout.addWidget(method_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        
        # Initialize parameter widgets
        self.create_param_widgets()
        self.on_method_changed(0)
        self.on_auto_detect_changed(self.auto_detect.checkState().value)
        
    def create_param_widgets(self):
        """Create parameter widgets for different fill methods."""
        # Linear interpolation parameters
        self.linear_widgets: list[tuple[QHBoxLayout, str]] = []
        
        # Cubic spline parameters
        self.cubic_widgets: list[tuple[QHBoxLayout, str]] = []
        tension_layout = QHBoxLayout()
        tension_layout.addWidget(QLabel("Tension:"))
        self.cubic_tension = QDoubleSpinBox()
        self.cubic_tension.setMinimum(0.0)
        self.cubic_tension.setMaximum(1.0)
        self.cubic_tension.setSingleStep(0.1)
        self.cubic_tension.setValue(0.5)
        tension_layout.addWidget(self.cubic_tension)
        self.cubic_widgets.append((tension_layout, "tension_layout"))
        
        # Constant velocity parameters
        self.velocity_widgets: list[tuple[QHBoxLayout, str]] = []
        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel("Frames to analyze:"))
        self.velocity_window = QSpinBox()
        self.velocity_window.setMinimum(2)
        self.velocity_window.setMaximum(10)
        self.velocity_window.setValue(3)
        window_layout.addWidget(self.velocity_window)
        self.velocity_widgets.append((window_layout, "window_layout"))
        
        # Accelerated motion parameters
        self.accel_widgets: list[tuple[QHBoxLayout, str]] = []
        accel_window_layout = QHBoxLayout()
        accel_window_layout.addWidget(QLabel("Frames to analyze:"))
        self.accel_window = QSpinBox()
        self.accel_window.setMinimum(3)
        self.accel_window.setMaximum(15)
        self.accel_window.setValue(5)
        accel_window_layout.addWidget(self.accel_window)
        self.accel_widgets.append((accel_window_layout, "accel_window_layout"))
        accel_weight_layout = QHBoxLayout()
        accel_weight_layout.addWidget(QLabel("Acceleration weight:"))
        self.accel_weight = QDoubleSpinBox()
        self.accel_weight.setMinimum(0.0)
        self.accel_weight.setMaximum(1.0)
        self.accel_weight.setSingleStep(0.1)
        self.accel_weight.setValue(0.5)
        accel_weight_layout.addWidget(self.accel_weight)
        self.accel_widgets.append((accel_weight_layout, "accel_weight_layout"))
        
        # Neighboring frames average parameters
        self.average_widgets: list[tuple[QHBoxLayout, str]] = []
        avg_window_layout = QHBoxLayout()
        avg_window_layout.addWidget(QLabel("Window size:"))
        self.avg_window = QSpinBox()
        self.avg_window.setMinimum(2)
        self.avg_window.setMaximum(10)
        self.avg_window.setValue(3)
        avg_window_layout.addWidget(self.avg_window)
        self.average_widgets.append((avg_window_layout, "avg_window_layout"))
    
    def on_method_changed(self, index: int) -> None:
        """Update parameter widgets based on selected method."""
        # Clear current widgets
        for i in reversed(range(self.param_layout.count())):
            item = self.param_layout.itemAt(i)
            if item.layout():
                while item.layout().count():
                    widget_item = item.layout().takeAt(0)
                    widget = widget_item.widget()
                    if widget:
                        widget.setParent(None)
                self.param_layout.removeItem(item)
            elif item.widget():
                widget = item.widget()
                widget.setParent(None)
                self.param_layout.removeWidget(widget)
                
        # Add appropriate widgets for selected method
        if index == 0:  # Linear Interpolation
            for layout, _ in self.linear_widgets:
                self.param_layout.addLayout(layout)
        elif index == 1:  # Cubic Spline
            for layout, _ in self.cubic_widgets:
                self.param_layout.addLayout(layout)
        elif index == 2:  # Constant Velocity
            for layout, _ in self.velocity_widgets:
                self.param_layout.addLayout(layout)
        elif index == 3:  # Accelerated Motion
            for layout, _ in self.accel_widgets:
                self.param_layout.addLayout(layout)
        elif index == 4:  # Neighboring Frames Average
            for layout, _ in self.average_widgets:
                self.param_layout.addLayout(layout)
                
    def on_auto_detect_changed(self, state: Qt.CheckState) -> None:
        """Enable/disable manual frame range selection based on auto-detect setting."""
        enabled = state != Qt.Checked
        self.start_frame.setEnabled(enabled)
        self.end_frame.setEnabled(enabled)


class ExtrapolateDialog(QDialog):
    """Dialog for extrapolating curve data beyond the existing frames."""
    
    def __init__(self, parent: Optional[QWidget] = None, min_frame: int = 0, max_frame: int = 100):
        super(ExtrapolateDialog, self).__init__(parent)
        self.setWindowTitle("Extrapolate Curve")
        self.resize(450, 300)
        
        layout = QVBoxLayout(self)
        
        # Direction selection
        direction_layout = QHBoxLayout()
        direction_layout.addWidget(QLabel("Direction:"))
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Extrapolate Forward", "Extrapolate Backward", "Both Directions"])
        direction_layout.addWidget(self.direction_combo)
        layout.addLayout(direction_layout)
        
        # Frame range
        range_group = QGroupBox("Frame Range")
        range_layout = QVBoxLayout(range_group)
        forward_layout = QHBoxLayout()
        forward_layout.addWidget(QLabel("Forward frames:"))
        self.forward_frames = QSpinBox()
        self.forward_frames.setMinimum(0)
        self.forward_frames.setMaximum(100)
        self.forward_frames.setValue(10)
        forward_layout.addWidget(self.forward_frames)
        range_layout.addLayout(forward_layout)
        backward_layout = QHBoxLayout()
        backward_layout.addWidget(QLabel("Backward frames:"))
        self.backward_frames = QSpinBox()
        self.backward_frames.setMinimum(0)
        self.backward_frames.setMaximum(100)
        self.backward_frames.setValue(10)
        backward_layout.addWidget(self.backward_frames)
        range_layout.addLayout(backward_layout)
        layout.addWidget(range_group)
        
        # Method selection
        method_group = QGroupBox("Extrapolation Method")
        method_layout = QVBoxLayout(method_group)
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Linear", "Last Velocity", "Quadratic"])
        method_layout.addWidget(self.method_combo)
        
        # Advanced options for quadratic
        self.advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QVBoxLayout(self.advanced_group)
        fit_layout = QHBoxLayout()
        fit_layout.addWidget(QLabel("Points to use for fit:"))
        self.fit_points = QSpinBox()
        self.fit_points.setMinimum(3)
        self.fit_points.setMaximum(20)
        self.fit_points.setValue(5)
        fit_layout.addWidget(self.fit_points)
        advanced_layout.addLayout(fit_layout)
        method_layout.addWidget(self.advanced_group)
        layout.addWidget(method_group)
        
        # Display preview option
        self.preview_checkbox = QCheckBox("Show preview")
        self.preview_checkbox.setChecked(True)
        layout.addWidget(self.preview_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        self.direction_combo.currentIndexChanged.connect(self.on_direction_changed)
        
        # Initial state updates
        self.on_method_changed(0)
        self.on_direction_changed(0)
        
    def on_method_changed(self, index: int) -> None:
        """Handle method selection change."""
        # Show advanced options only for quadratic (index 2)
        self.advanced_group.setVisible(index == 2)
        
    def on_direction_changed(self, index: int) -> None:
        """Handle direction selection change."""
        # Enable/disable appropriate frame inputs based on selected direction
        if index == 0:  # Forward only
            self.forward_frames.setEnabled(True)
            self.backward_frames.setEnabled(False)
        elif index == 1:  # Backward only
            self.forward_frames.setEnabled(False)
            self.backward_frames.setEnabled(True)
        else:  # Both
            self.forward_frames.setEnabled(True)
            self.backward_frames.setEnabled(True)


class ProblemDetectionDialog(QDialog):
    """Dialog for detecting and navigating to problematic areas in the curve."""
    
    def __init__(self, parent: Optional[QWidget] = None, problems: Optional[list[dict[str, Any]]] = None):
        super(ProblemDetectionDialog, self).__init__(parent)
        self.setWindowTitle("Problem Detection")
        self.resize(500, 400)
        self.selected_problem: Optional[dict[str, Any]] = None
        
        if problems is None:
            problems = []
            
        # Store problems data first to avoid attribute error
        self.problems = problems
            
        layout = QVBoxLayout(self)
        
        # Problems list header
        layout.addWidget(QLabel("Detected problems in tracking curve:"))
        
        # Problems list
        self.problems_list = QComboBox()
        for problem in problems:
            frame, problem_type, severity, description = problem
            try:
                sev = float(severity)
            except (ValueError, TypeError):
                sev = 0.0
            severity_text = "High" if sev > 0.7 else "Medium" if sev > 0.3 else "Low"
            self.problems_list.addItem(f"Frame {frame}: {problem_type} - {severity_text} - {description}")
        layout.addWidget(self.problems_list)
        
        # Information area
        info_group = QGroupBox("Problem Details")
        info_layout = QVBoxLayout(info_group)
        self.info_frame = QLabel()
        self.info_type = QLabel()
        self.info_severity = QLabel()
        self.info_description = QLabel()
        self.info_description.setWordWrap(True)
        info_layout.addWidget(self.info_frame)
        info_layout.addWidget(self.info_type)
        info_layout.addWidget(self.info_severity)
        info_layout.addWidget(self.info_description)
        layout.addWidget(info_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.jump_button = QPushButton("Jump to Problem")
        self.jump_button.clicked.connect(self.jump_to_problem)
        self.next_button = QPushButton("Next Problem")
        self.next_button.clicked.connect(self.next_problem)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.jump_button)
        button_layout.addWidget(self.next_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.problems_list.currentIndexChanged.connect(self.update_problem_info)
        
        # Initial update
        if problems:
            self.update_problem_info(0)
        
    def update_problem_info(self, index: int) -> None:
        """Update the problem information display."""
        if index < 0 or index >= len(self.problems):
            return
        frame, problem_type, severity, description = self.problems[index]
        try:
            sev = float(severity)
        except (ValueError, TypeError):
            sev = 0.0
        severity_text = "High" if sev > 0.7 else "Medium" if sev > 0.3 else "Low"
        self.info_frame.setText(f"Frame: {frame}")
        self.info_type.setText(f"Type: {problem_type}")
        self.info_severity.setText(f"Severity: {severity_text} ({sev:.2f})")
        self.info_description.setText(f"Description: {description}")
        
    def jump_to_problem(self):
        """Signal to jump to the selected problem."""
        index = self.problems_list.currentIndex()
        if 0 <= index < len(self.problems):
            self.selected_problem = self.problems[index]
            self.accept()
            
    def next_problem(self):
        """Move to the next problem in the list."""
        index = self.problems_list.currentIndex()
        if index < self.problems_list.count() - 1:
            self.problems_list.setCurrentIndex(index + 1)
        else:
            self.problems_list.setCurrentIndex(0)  # Wrap around


class ShortcutsDialog(QDialog):
    """Dialog displaying keyboard shortcuts."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super(ShortcutsDialog, self).__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        shortcuts_label = QLabel("""
        <h3>Keyboard Shortcuts</h3>
        <table>
            <tr><td><b>Ctrl+O</b></td><td>Open file</td></tr>
            <tr><td><b>Ctrl+S</b></td><td>Save file</td></tr>
            <tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>
            <tr><td><b>Ctrl+Y</b></td><td>Redo</td></tr>
            <tr><td><b>Space</b></td><td>Play/Pause animation</td></tr>
            <tr><td><b>Left Arrow</b></td><td>Previous frame</td></tr>
            <tr><td><b>Right Arrow</b></td><td>Next frame</td></tr>
            <tr><td><b>Delete</b></td><td>Delete selected points</td></tr>
            <tr><td><b>Ctrl+A</b></td><td>Select all points</td></tr>
            <tr><td><b>Escape</b></td><td>Clear selection</td></tr>
            <tr><td><b>F</b></td><td>Frame view to show all points</td></tr>
            <tr><td><b>Ctrl+E</b></td><td>Export data</td></tr>
        </table>
        """)
        shortcuts_label.setTextFormat(Qt.RichText)
        layout.addWidget(shortcuts_label)
        
        # Close button
        button = QPushButton("Close")
        button.clicked.connect(self.accept)
        layout.addWidget(button)


class ScaleDialog(QDialog):
    """Dialog for scaling points."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Scale Points")

        layout = QVBoxLayout(self)

        # Scale factors
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("Scale X:"))
        self.scale_x_spin = QDoubleSpinBox()
        self.scale_x_spin.setRange(0.01, 10.0)
        self.scale_x_spin.setSingleStep(0.1)
        self.scale_x_spin.setValue(1.0)
        x_layout.addWidget(self.scale_x_spin)
        layout.addLayout(x_layout)

        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Scale Y:"))
        self.scale_y_spin = QDoubleSpinBox()
        self.scale_y_spin.setRange(0.01, 10.0)
        self.scale_y_spin.setSingleStep(0.1)
        self.scale_y_spin.setValue(1.0)
        y_layout.addWidget(self.scale_y_spin)
        layout.addLayout(y_layout)

        # Use centroid as scaling center
        self.use_centroid_check = QCheckBox("Scale around selection centroid")
        self.use_centroid_check.setChecked(True)
        layout.addWidget(self.use_centroid_check)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Apply")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        self.setWindowTitle("Scale Points")
        
        layout = QVBoxLayout(self)
        
        # Scale factors
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("Scale X:"))
        self.scale_x_spin = QDoubleSpinBox()
        self.scale_x_spin.setRange(0.01, 10.0)
        self.scale_x_spin.setSingleStep(0.1)
        self.scale_x_spin.setValue(1.0)
        x_layout.addWidget(self.scale_x_spin)
        layout.addLayout(x_layout)
        
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Scale Y:"))
        self.scale_y_spin = QDoubleSpinBox()
        self.scale_y_spin.setRange(0.01, 10.0)
        self.scale_y_spin.setSingleStep(0.1)
        self.scale_y_spin.setValue(1.0)
        y_layout.addWidget(self.scale_y_spin)
        layout.addLayout(y_layout)
        
        # Use centroid as scaling center
        self.use_centroid_check = QCheckBox("Scale around selection centroid")
        self.use_centroid_check.setChecked(True)
        layout.addWidget(self.use_centroid_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Apply")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
    
    @property
    def scale_x(self) -> float:
        return self.scale_x_spin.value()

    @property
    def scale_y(self) -> float:
        return self.scale_y_spin.value()

    @property
    def use_centroid(self) -> bool:
        return self.use_centroid_check.isChecked()


class OffsetDialog(QDialog):
    """Dialog for offsetting points."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Offset Points")

        layout = QVBoxLayout(self)

        # Offset values
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("Offset X:"))
        self.offset_x_spin = QDoubleSpinBox()
        self.offset_x_spin.setRange(-1000.0, 1000.0)
        self.offset_x_spin.setSingleStep(1.0)
        self.offset_x_spin.setValue(0.0)
        x_layout.addWidget(self.offset_x_spin)
        layout.addLayout(x_layout)

        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Offset Y:"))
        self.offset_y_spin = QDoubleSpinBox()
        self.offset_y_spin.setRange(-1000.0, 1000.0)
        self.offset_y_spin.setSingleStep(1.0)
        self.offset_y_spin.setValue(0.0)
        y_layout.addWidget(self.offset_y_spin)
        layout.addLayout(y_layout)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Apply")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        self.setWindowTitle("Offset Points")
        
        layout = QVBoxLayout(self)
        
        # Offset values
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("Offset X:"))
        self.offset_x_spin = QDoubleSpinBox()
        self.offset_x_spin.setRange(-1000.0, 1000.0)
        self.offset_x_spin.setSingleStep(1.0)
        self.offset_x_spin.setValue(0.0)
        x_layout.addWidget(self.offset_x_spin)
        layout.addLayout(x_layout)
        
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Offset Y:"))
        self.offset_y_spin = QDoubleSpinBox()
        self.offset_y_spin.setRange(-1000.0, 1000.0)
        self.offset_y_spin.setSingleStep(1.0)
        self.offset_y_spin.setValue(0.0)
        y_layout.addWidget(self.offset_y_spin)
        layout.addLayout(y_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Apply")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
    
    @property
    def offset_x(self):
        return self.offset_x_spin.value()
    
    @property
    def offset_y(self):
        return self.offset_y_spin.value()


class RotationDialog(QDialog):
    """Dialog for rotating points."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Rotate Points")

        layout = QVBoxLayout(self)

        # Rotation angle
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(QLabel("Angle (degrees):"))
        self.angle_spin = QDoubleSpinBox()
        self.angle_spin.setRange(-360.0, 360.0)
        self.angle_spin.setSingleStep(5.0)
        self.angle_spin.setValue(0.0)
        angle_layout.addWidget(self.angle_spin)
        layout.addLayout(angle_layout)

        # Use centroid as rotation center
        self.use_centroid_check = QCheckBox("Rotate around selection centroid")
        self.use_centroid_check.setChecked(True)
        layout.addWidget(self.use_centroid_check)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Apply")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        self.setWindowTitle("Rotate Points")
        
        layout = QVBoxLayout(self)
        
        # Rotation angle
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(QLabel("Angle (degrees):"))
        self.angle_spin = QDoubleSpinBox()
        self.angle_spin.setRange(-360.0, 360.0)
        self.angle_spin.setSingleStep(5.0)
        self.angle_spin.setValue(0.0)
        angle_layout.addWidget(self.angle_spin)
        layout.addLayout(angle_layout)
        
        # Use centroid as rotation center
        self.use_centroid_check = QCheckBox("Rotate around selection centroid")
        self.use_centroid_check.setChecked(True)
        layout.addWidget(self.use_centroid_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Apply")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
    
    @property
    def angle(self) -> float:
        return self.angle_spin.value()

    @property
    def use_centroid(self) -> bool:
        return self.use_centroid_check.isChecked()


class SmoothFactorDialog(QDialog):
    """Dialog for selecting smoothness factor."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Smooth Points")

        layout = QVBoxLayout(self)

        # Smoothness factor
        layout.addWidget(QLabel("Smoothness Factor:"))

        slider_layout = QHBoxLayout()
        self.factor_slider = QSlider(Qt.Horizontal)
        self.factor_slider.setRange(0, 100)
        self.factor_slider.setValue(50)
        slider_layout.addWidget(self.factor_slider)

        self.factor_spin = QDoubleSpinBox()
        self.factor_spin.setRange(0.0, 1.0)
        self.factor_spin.setSingleStep(0.05)
        self.factor_spin.setValue(0.5)
        slider_layout.addWidget(self.factor_spin)
        layout.addLayout(slider_layout)

        # Connect slider and spin box
        self.factor_slider.valueChanged.connect(self.update_spin_from_slider)
        self.factor_spin.valueChanged.connect(self.update_slider_from_spin)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Apply")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        self.setWindowTitle("Smooth Points")
        
        layout = QVBoxLayout(self)
        
        # Smoothness factor
        layout.addWidget(QLabel("Smoothness Factor:"))
        
        slider_layout = QHBoxLayout()
        self.factor_slider = QSlider(Qt.Horizontal)
        self.factor_slider.setRange(0, 100)
        self.factor_slider.setValue(50)
        slider_layout.addWidget(self.factor_slider)
        
        self.factor_spin = QDoubleSpinBox()
        self.factor_spin.setRange(0.0, 1.0)
        self.factor_spin.setSingleStep(0.05)
        self.factor_spin.setValue(0.5)
        slider_layout.addWidget(self.factor_spin)
        layout.addLayout(slider_layout)
        
        # Connect slider and spin box
        self.factor_slider.valueChanged.connect(self.update_spin_from_slider)
        self.factor_spin.valueChanged.connect(self.update_slider_from_spin)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Apply")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
    
    def update_spin_from_slider(self, value: int) -> None:
        """Update spin box value when slider changes."""
        self.factor_spin.setValue(value / 100.0)
    
    def update_slider_from_spin(self, value: float) -> None:
        """Update slider value when spin box changes."""
        self.factor_slider.setValue(int(value * 100))
    
    @property
    def smoothness_factor(self):
        return self.factor_spin.value()
