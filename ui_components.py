#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI Components for 3DE4 Curve Editor.

This module contains the UIComponents class which centralizes all UI-related functionality
for the Curve Editor application. It handles the creation, arrangement, and signal connections
for all user interface elements in a consistent and maintainable way.

The module follows these key principles:
1. All UI component creation is centralized in static methods
2. All signal connections are managed through the connect_all_signals method
3. Proper error handling and defensive programming techniques are used
4. Clear separation between UI creation and application logic

This architecture ensures that:
- UI components are created consistently
- Signal connections are managed in a single location
- The code is more maintainable and easier to extend
- Components are properly checked before signals are connected
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QSlider, QLineEdit, 
                              QGroupBox, QSplitter, QToolBar, QFrame, 
                              QGridLayout, QTabWidget, QSpacerItem, 
                              QSizePolicy, QComboBox, QStatusBar, QSpinBox)
from PySide6.QtCore import Signal, Qt, QSize, QTimer, QEvent
from PySide6.QtGui import QIcon, QFont, QAction, QKeySequence

from curve_view_operations import CurveViewOperations
from visualization_operations import VisualizationOperations
from image_operations import ImageOperations
from dialog_operations import DialogOperations
from curve_operations import CurveOperations
from enhanced_curve_view import EnhancedCurveView
import os
import re


class UIComponents:
    """Centralized management of all UI components for the Curve Editor application.
    
    This class follows a utility pattern with static methods for creating, arranging,
    and connecting UI components. It serves as a single point of control for all
    UI-related operations, improving code organization and maintainability.
    
    Key responsibilities:
    - Creating and arranging UI widgets and layouts
    - Centralizing signal connections through connect_all_signals
    - Providing utility methods for UI operations
    - Ensuring proper error handling for UI components
    
    Note:
    All methods are static and take a MainWindow instance as the first parameter.
    This design allows for separation of UI component management from application logic.
    """
    
    @staticmethod
    def create_toolbar(main_window):
        """Create a more organized toolbar with action buttons grouped by function."""
        
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        
        # File operations group
        file_group = QWidget()
        file_layout = QVBoxLayout(file_group)
        file_layout.setContentsMargins(5, 2, 5, 2)
        file_layout.setSpacing(2)
        
        file_label = QLabel("File")
        file_label.setAlignment(Qt.AlignCenter)
        file_label.setFont(QFont("Arial", 8, QFont.Bold))
        file_layout.addWidget(file_label)
        
        file_buttons = QHBoxLayout()
        
        main_window.load_button = QPushButton("Load")
        main_window.load_button.setToolTip("Load 2D Track Data")
        main_window.load_button.clicked.connect(main_window.load_track_data)
        
        main_window.add_point_button = QPushButton("Add")
        main_window.add_point_button.setToolTip("Add 2D Track Data")
        main_window.add_point_button.clicked.connect(main_window.add_track_data)
        main_window.add_point_button.setEnabled(False)
        
        main_window.save_button = QPushButton("Save")
        main_window.save_button.setToolTip("Save 2D Track Data")
        main_window.save_button.clicked.connect(main_window.save_track_data)
        main_window.save_button.setEnabled(False)
        
        file_buttons.addWidget(main_window.load_button)
        file_buttons.addWidget(main_window.add_point_button)
        file_buttons.addWidget(main_window.save_button)
        file_layout.addLayout(file_buttons)
        
        # View operations group
        view_group = QWidget()
        view_layout = QVBoxLayout(view_group)
        view_layout.setContentsMargins(5, 2, 5, 2)
        view_layout.setSpacing(2)
        
        view_label = QLabel("View")
        view_label.setAlignment(Qt.AlignCenter)
        view_label.setFont(QFont("Arial", 8, QFont.Bold))
        view_layout.addWidget(view_label)
        
        view_buttons = QHBoxLayout()
        
        main_window.reset_view_button = QPushButton("Reset")
        main_window.reset_view_button.setToolTip("Reset View")
        main_window.reset_view_button.clicked.connect(lambda: CurveViewOperations.reset_view(main_window))
        
        main_window.load_images_button = QPushButton("Images")
        main_window.load_images_button.setToolTip("Load Image Sequence")
        main_window.load_images_button.clicked.connect(lambda: ImageOperations.load_image_sequence(main_window))
        
        main_window.toggle_bg_button = QPushButton("Toggle BG")
        main_window.toggle_bg_button.setToolTip("Toggle Background Visibility")
        main_window.toggle_bg_button.clicked.connect(lambda: ImageOperations.toggle_background(main_window))
        main_window.toggle_bg_button.setEnabled(False)
        
        view_buttons.addWidget(main_window.reset_view_button)
        view_buttons.addWidget(main_window.load_images_button)
        view_buttons.addWidget(main_window.toggle_bg_button)
        view_layout.addLayout(view_buttons)
        
        # Curve operations group
        curve_group = QWidget()
        curve_layout = QVBoxLayout(curve_group)
        curve_layout.setContentsMargins(5, 2, 5, 2)
        curve_layout.setSpacing(2)
        
        curve_label = QLabel("Curve Tools")
        curve_label.setAlignment(Qt.AlignCenter)
        curve_label.setFont(QFont("Arial", 8, QFont.Bold))
        curve_layout.addWidget(curve_label)
        
        curve_buttons = QGridLayout()
        curve_buttons.setSpacing(2)
        
        main_window.smooth_button = QPushButton("Smooth")
        main_window.smooth_button.setToolTip("Smooth Selected Curve")
        main_window.smooth_button.clicked.connect(lambda: DialogOperations.show_smooth_dialog(main_window))
        main_window.smooth_button.setEnabled(False)
        
        main_window.fill_gaps_button = QPushButton("Fill Gaps")
        main_window.fill_gaps_button.setToolTip("Fill Gaps in Tracking Data")
        main_window.fill_gaps_button.clicked.connect(lambda: DialogOperations.show_fill_gaps_dialog(main_window))
        main_window.fill_gaps_button.setEnabled(False)
        
        main_window.filter_button = QPushButton("Filter")
        main_window.filter_button.setToolTip("Apply Filter to Curve")
        main_window.filter_button.clicked.connect(lambda: DialogOperations.show_filter_dialog(main_window))
        main_window.filter_button.setEnabled(False)
        
        main_window.extrapolate_button = QPushButton("Extrapolate")
        main_window.extrapolate_button.setToolTip("Extrapolate Curve")
        main_window.extrapolate_button.clicked.connect(lambda: DialogOperations.show_extrapolate_dialog(main_window))
        main_window.extrapolate_button.setEnabled(False)
        
        curve_buttons.addWidget(main_window.smooth_button, 0, 0)
        curve_buttons.addWidget(main_window.fill_gaps_button, 0, 1)
        curve_buttons.addWidget(main_window.filter_button, 1, 0)
        curve_buttons.addWidget(main_window.extrapolate_button, 1, 1)
        
        curve_layout.addLayout(curve_buttons)
        
        # History and Analysis group
        history_group = QWidget()
        history_layout = QVBoxLayout(history_group)
        history_layout.setContentsMargins(5, 2, 5, 2)
        history_layout.setSpacing(2)
        
        history_label = QLabel("History & Analysis")
        history_label.setAlignment(Qt.AlignCenter)
        history_label.setFont(QFont("Arial", 8, QFont.Bold))
        history_layout.addWidget(history_label)
        
        history_buttons = QHBoxLayout()
        
        main_window.undo_button = QPushButton("Undo")
        main_window.undo_button.setToolTip("Undo Last Action")
        main_window.undo_button.clicked.connect(lambda: CurveOperations.undo(main_window))
        main_window.undo_button.setEnabled(False)
        
        main_window.redo_button = QPushButton("Redo")
        main_window.redo_button.setToolTip("Redo Last Action")
        main_window.redo_button.clicked.connect(lambda: CurveOperations.redo(main_window))
        main_window.redo_button.setEnabled(False)
        
        main_window.detect_problems_button = QPushButton("Detect")
        main_window.detect_problems_button.setToolTip("Detect Problems in Track Data")
        main_window.detect_problems_button.clicked.connect(lambda: DialogOperations.show_problem_detection_dialog(main_window, CurveOperations.detect_problems(main_window)))
        main_window.detect_problems_button.setEnabled(False)
        
        history_buttons.addWidget(main_window.undo_button)
        history_buttons.addWidget(main_window.redo_button)
        history_buttons.addWidget(main_window.detect_problems_button)
        history_layout.addLayout(history_buttons)
        
        # Add vertical separator lines between groups
        def create_vertical_line():
            line = QFrame()
            line.setFrameShape(QFrame.VLine)
            line.setFrameShadow(QFrame.Sunken)
            return line
        
        # Create the main toolbar layout
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(5, 0, 5, 0)
        toolbar_layout.setSpacing(10)
        
        # Add all groups to toolbar with separators
        toolbar_layout.addWidget(file_group)
        toolbar_layout.addWidget(create_vertical_line())
        toolbar_layout.addWidget(view_group)
        toolbar_layout.addWidget(create_vertical_line())
        toolbar_layout.addWidget(curve_group)
        toolbar_layout.addWidget(create_vertical_line())
        toolbar_layout.addWidget(history_group)
        toolbar_layout.addStretch()
        
        # Add info label
        main_window.info_label = QLabel("No data loaded")
        toolbar_layout.addWidget(main_window.info_label)
        
        # Create a container widget for the toolbar
        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar_layout)
        
        return toolbar_widget
        
    @staticmethod
    def create_view_and_timeline(main_window):
        """Create the curve view widget and timeline controls."""
        # Container for view and timeline
        view_container = QWidget()
        view_layout = QVBoxLayout(view_container)
        view_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create curve view container
        main_window.curve_view_container = QWidget()
        curve_view_layout = QVBoxLayout(main_window.curve_view_container)
        curve_view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.addWidget(main_window.curve_view_container)
        
        # Create curve view
        if hasattr(main_window, 'curve_view_class') and issubclass(main_window.curve_view_class, EnhancedCurveView):
            main_window.curve_view = main_window.curve_view_class()
            main_window.original_curve_view = main_window.curve_view  # Store reference to original view
        else:
            main_window.curve_view = EnhancedCurveView()
            main_window.original_curve_view = main_window.curve_view  # Store reference to original view
        
        curve_view_layout.addWidget(main_window.curve_view)
        
        # Timeline widget
        timeline_widget = QWidget()
        timeline_layout = QVBoxLayout(timeline_widget)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        
        # Image sequence controls
        image_controls = QHBoxLayout()
        main_window.prev_image_button = QPushButton("Previous")
        main_window.prev_image_button.clicked.connect(lambda: ImageOperations.previous_image(main_window))
        main_window.prev_image_button.setEnabled(False)
        
        main_window.next_image_button = QPushButton("Next")
        main_window.next_image_button.clicked.connect(lambda: ImageOperations.next_image(main_window))
        main_window.next_image_button.setEnabled(False)
        
        main_window.image_label = QLabel("No images loaded")
        
        # Opacity slider
        main_window.opacity_slider = QSlider(Qt.Horizontal)
        main_window.opacity_slider.setMinimum(0)
        main_window.opacity_slider.setMaximum(100)
        main_window.opacity_slider.setValue(70)  # Default 70% opacity
        main_window.opacity_slider.setEnabled(False)
        main_window.opacity_slider.valueChanged.connect(lambda value: ImageOperations.opacity_changed(main_window, value))
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity:"))
        opacity_layout.addWidget(main_window.opacity_slider)
        
        image_controls.addWidget(main_window.prev_image_button)
        image_controls.addWidget(main_window.image_label)
        image_controls.addWidget(main_window.next_image_button)
        image_controls.addStretch()
        image_controls.addLayout(opacity_layout)
        
        timeline_layout.addLayout(image_controls)
        
        # Timeline controls
        timeline_controls = QHBoxLayout()
        
        # Add playback controls
        main_window.play_button = QPushButton("Play")
        main_window.play_button.setCheckable(True)
        main_window.play_button.clicked.connect(lambda: UIComponents.toggle_playback(main_window))
        main_window.play_button.setToolTip("Play/Pause (Space)")
        main_window.play_button.setEnabled(False)
        
        main_window.prev_frame_button = QPushButton("<")
        main_window.prev_frame_button.clicked.connect(lambda: UIComponents.prev_frame(main_window))
        main_window.prev_frame_button.setToolTip("Previous Frame (,)")
        main_window.prev_frame_button.setEnabled(False)
        
        main_window.next_frame_button = QPushButton(">")
        main_window.next_frame_button.clicked.connect(lambda: UIComponents.next_frame(main_window))
        main_window.next_frame_button.setToolTip("Next Frame (.)")
        main_window.next_frame_button.setEnabled(False)
        
        timeline_controls.addWidget(main_window.prev_frame_button)
        timeline_controls.addWidget(main_window.play_button)
        timeline_controls.addWidget(main_window.next_frame_button)
        
        # Frame controls
        main_window.frame_label = QLabel("Frame: N/A")
        main_window.frame_edit = QLineEdit()
        main_window.frame_edit.setMaximumWidth(60)
        main_window.frame_edit.returnPressed.connect(lambda: UIComponents.on_frame_edit_changed(main_window))
        main_window.go_button = QPushButton("Go")
        main_window.go_button.clicked.connect(lambda: UIComponents.on_frame_edit_changed(main_window))
        main_window.go_button.setMaximumWidth(50)
        
        timeline_controls.addWidget(main_window.frame_label)
        timeline_controls.addWidget(main_window.frame_edit)
        timeline_controls.addWidget(main_window.go_button)
        timeline_controls.addStretch()
        
        timeline_layout.addLayout(timeline_controls)
        
        # Timeline slider
        main_window.timeline_slider = QSlider(Qt.Horizontal)
        main_window.timeline_slider.setMinimum(0)
        main_window.timeline_slider.setMaximum(100)  # Will be updated when data is loaded
        main_window.timeline_slider.valueChanged.connect(lambda value: UIComponents.on_timeline_changed(main_window, value))
        timeline_layout.addWidget(main_window.timeline_slider)
        
        view_layout.addWidget(timeline_widget)
        
        return view_container

    @staticmethod
    def create_enhanced_curve_view(main_window):
        """Create and set up the enhanced curve view.
        
        Args:
            main_window: The main application window instance
            
        Returns:
            bool: True if the enhanced view was successfully set up, False otherwise
        """
        try:
            # Create the enhanced curve view
            enhanced_view = EnhancedCurveView(main_window)
            
            # Replace standard view with enhanced view
            if hasattr(main_window, 'curve_view_container') and hasattr(main_window, 'curve_view'):
                main_window.curve_view_container.layout().removeWidget(main_window.curve_view)
                main_window.curve_view.deleteLater()
                
                # Set the new enhanced view
                main_window.curve_view = enhanced_view
                main_window.curve_view_container.layout().addWidget(main_window.curve_view)
                
                # Explicitly connect signals here to ensure proper connections
                main_window.curve_view.point_selected.connect(lambda idx: CurveViewOperations.on_point_selected(main_window, idx))
                main_window.curve_view.point_moved.connect(lambda idx, x, y: CurveViewOperations.on_point_moved(main_window, idx, x, y))
                main_window.curve_view.image_changed.connect(main_window.on_image_changed)
                print("UIComponents: Enhanced curve view signal connections established")
                
                # Add a direct update method to the view for direct timeline updates
                def update_timeline_for_image(index):
                    """Direct method to update the timeline for the current image."""
                    try:
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
                        
                        # Update label
                        if hasattr(main_window, 'range_slider_value_label'):
                            main_window.range_slider_value_label.setText(f"Frame: {frame_num}")
                            
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
                
                # Attach the method to the curve view
                main_window.curve_view.update_timeline_for_image = update_timeline_for_image
                
                # Create enhanced controls
                UIComponents.setup_enhanced_controls(main_window)
                
                return True
            else:
                return False
        except Exception as e:
            print(f"Error setting up enhanced curve view: {str(e)}")
            return False

    @staticmethod
    def create_control_panel(main_window):
        """Create the control panel for point editing."""
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # Point edit controls group
        point_group = QGroupBox("Point Editing")
        point_layout = QHBoxLayout(point_group)
        
        main_window.point_idx_label = QLabel("Point:")
        main_window.point_frame_label = QLabel("Frame: N/A")
        
        main_window.x_label = QLabel("X:")
        main_window.x_edit = QLineEdit()
        main_window.x_edit.setMaximumWidth(100)
        
        main_window.y_label = QLabel("Y:")
        main_window.y_edit = QLineEdit()
        main_window.y_edit.setMaximumWidth(100)
        
        main_window.update_point_button = QPushButton("Update")
        
        point_layout.addWidget(main_window.point_idx_label)
        point_layout.addWidget(main_window.point_frame_label)
        point_layout.addWidget(main_window.x_label)
        point_layout.addWidget(main_window.x_edit)
        point_layout.addWidget(main_window.y_label)
        point_layout.addWidget(main_window.y_edit)
        point_layout.addWidget(main_window.update_point_button)
        point_layout.addStretch()
        
        # Add controls to panel
        controls_layout.addWidget(point_group)
        
        # Create point editing container for batch operations and tools
        point_edit_container = QWidget()
        main_window.point_edit_layout = QVBoxLayout(point_edit_container)
        main_window.point_edit_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.addWidget(point_edit_container)
        
        # Create view controls section for enhanced controls
        view_group = QGroupBox("View Controls")
        main_window.view_controls_layout = QVBoxLayout(view_group)
        controls_layout.addWidget(view_group)
        
        return controls_widget

    @staticmethod
    def setup_enhanced_curve_view(main_window):
        """Create and setup the EnhancedCurveView.
        
        Replaces the standard curve view with the enhanced version if it exists
        and creates the necessary UI controls for the enhanced visualization features.
        This method follows proper error handling practices to ensure the application
        can continue running even if the enhanced view cannot be loaded.
        
        The method performs these steps:
        1. Create an instance of EnhancedCurveView
        2. Replace the standard curve view in the container
        3. Set up the enhanced controls through setup_enhanced_controls
        4. Return success/failure status
        
        Args:
            main_window: The main application window instance
            
        Returns:
            bool: True if the enhanced view was successfully set up, False otherwise
        """
        try:
            # Create the enhanced curve view
            enhanced_view = EnhancedCurveView(main_window)
            
            # Replace standard view with enhanced view
            if hasattr(main_window, 'curve_view_container') and hasattr(main_window, 'curve_view'):
                main_window.curve_view_container.layout().removeWidget(main_window.curve_view)
                main_window.curve_view.deleteLater()
                
                # Set the new enhanced view
                main_window.curve_view = enhanced_view
                main_window.curve_view_container.layout().addWidget(main_window.curve_view)
                
                # Explicitly connect signals here to ensure proper connections
                main_window.curve_view.point_selected.connect(lambda idx: CurveViewOperations.on_point_selected(main_window, idx))
                main_window.curve_view.point_moved.connect(lambda idx, x, y: CurveViewOperations.on_point_moved(main_window, idx, x, y))
                main_window.curve_view.image_changed.connect(main_window.on_image_changed)
                print("UIComponents: Enhanced curve view signal connections established")
                
                # Add a direct update method to the view for direct timeline updates
                def update_timeline_for_image(index):
                    """Direct method to update the timeline for the current image."""
                    try:
                        if index < 0 or index >= len(main_window.image_filenames):
                            print(f"update_timeline_for_image: Invalid index {index}")
                            return
                    
                        # Extract frame number
                        filename = os.path.basename(main_window.image_filenames[index])
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
                        
                        # Update label
                        if hasattr(main_window, 'range_slider_value_label'):
                            main_window.range_slider_value_label.setText(f"Frame: {frame_num}")
                            
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
                
                # Attach the method to the curve view
                main_window.curve_view.update_timeline_for_image = update_timeline_for_image
                
                # Create enhanced controls
                UIComponents.setup_enhanced_controls(main_window)
                
                return True
            else:
                return False
        except Exception as e:
            print(f"Error setting up enhanced curve view: {str(e)}")
            return False

    @staticmethod
    def setup_timeline(main_window):
        """Setup timeline slider based on frame range."""
        if not main_window.curve_data:
            return
            
        # Get frame range
        frames = [frame for frame, _, _ in main_window.curve_data]
        min_frame = min(frames)
        max_frame = max(frames)
        
        # Set slider range
        main_window.timeline_slider.setMinimum(min_frame)
        main_window.timeline_slider.setMaximum(max_frame)
        
        # Enable controls
        main_window.next_frame_button.setEnabled(True)
        main_window.prev_frame_button.setEnabled(True)
        main_window.play_button.setEnabled(True)
        
        # Set to first frame
        if main_window.current_frame < min_frame or main_window.current_frame > max_frame:
            main_window.current_frame = min_frame
            
        # Update slider and label
        main_window.timeline_slider.setValue(main_window.current_frame)
        main_window.frame_label.setText(f"Frame: {main_window.current_frame}")
        main_window.frame_edit.setText(str(main_window.current_frame))
        
        print("UIComponents: Timeline setup complete with slider connected to valueChanged signal")

    @staticmethod
    def on_timeline_changed(main_window, value):
        """Handle timeline slider value changed."""
        main_window.current_frame = value
        
        # Update frame edit and label
        main_window.frame_edit.setText(str(value))
        main_window.frame_label.setText(f"Frame: {value}")
        
        # Load the corresponding image if we have an image sequence
        if main_window.image_filenames:
            # Update the image by frame
            main_window.curve_view.setCurrentImageByFrame(value)
            main_window.update_image_label()
                    
        # Update view with current frame
        main_window.curve_view.update()
            
    @staticmethod
    def on_frame_edit_changed(main_window):
        """Handle frame edit text changed."""
        try:
            value = int(main_window.frame_edit.text())
            min_val = main_window.timeline_slider.minimum()
            max_val = main_window.timeline_slider.maximum()
            
            if min_val <= value <= max_val:
                main_window.timeline_slider.setValue(value)
            else:
                main_window.frame_edit.setText(str(main_window.current_frame))
                main_window.statusBar().showMessage(f"Frame must be between {min_val} and {max_val}", 2000)
        except ValueError:
            main_window.frame_edit.setText(str(main_window.current_frame))
            main_window.statusBar().showMessage("Please enter a valid frame number", 2000)
            
    @staticmethod
    def toggle_playback(main_window):
        """Toggle timeline playback on/off."""
        # If playback is already active, stop it
        if hasattr(main_window, 'playback_timer') and main_window.playback_timer.isActive():
            main_window.playback_timer.stop()
            main_window.play_button.setChecked(False)
            main_window.statusBar().showMessage("Playback stopped", 2000)
            return
            
        # Create timer if it doesn't exist
        if not hasattr(main_window, 'playback_timer'):
            main_window.playback_timer = QTimer(main_window)
            main_window.playback_timer.timeout.connect(lambda: UIComponents.advance_playback(main_window))
            
        # Set playback speed (frames per second)
        fps = 24  # Default to 24 fps
        interval = int(1000 / fps)  # Convert to milliseconds
        main_window.playback_timer.setInterval(interval)
        
        # Start playback
        main_window.playback_timer.start()
        main_window.play_button.setChecked(True)
        main_window.statusBar().showMessage(f"Playback started at {fps} fps", 2000)
    
    @staticmethod
    def advance_playback(main_window):
        """Advance to the next frame during playback."""
        if not main_window.curve_data:
            return
            
        # Get current frame and frame range
        current_frame = main_window.timeline_slider.value()
        min_frame = main_window.timeline_slider.minimum()
        max_frame = main_window.timeline_slider.maximum()
        
        # Calculate next frame (loop back to start if at end)
        next_frame = current_frame + 1
        if next_frame > max_frame:
            next_frame = min_frame
            
        # Update timeline position
        main_window.timeline_slider.setValue(next_frame)
    
    @staticmethod
    def next_frame(main_window):
        """Go to the next frame in the timeline."""
        if not main_window.curve_data:
            return
            
        current_frame = main_window.timeline_slider.value()
        max_frame = main_window.timeline_slider.maximum()
        
        if current_frame < max_frame:
            main_window.timeline_slider.setValue(current_frame + 1)
    
    @staticmethod
    def prev_frame(main_window):
        """Go to the previous frame in the timeline."""
        if not main_window.curve_data:
            return
            
        current_frame = main_window.timeline_slider.value()
        min_frame = main_window.timeline_slider.minimum()
        
        if current_frame > min_frame:
            main_window.timeline_slider.setValue(current_frame - 1)
            
    @staticmethod
    def go_to_frame(main_window, frame):
        """Go to a specific frame."""
        if not main_window.curve_data:
            return
            
        min_frame = main_window.timeline_slider.minimum()
        max_frame = main_window.timeline_slider.maximum()
        
        if min_frame <= frame <= max_frame:
            main_window.timeline_slider.setValue(frame)
            # Update will happen automatically via the slider's valueChanged signal
        else:
            main_window.statusBar().showMessage(f"Frame {frame} is out of range ({min_frame}-{max_frame})", 2000)

    @staticmethod
    def go_to_first_frame(main_window):
        """Go to the first frame in the timeline."""
        if not main_window.curve_data:
            return
            
        min_frame = main_window.timeline_slider.minimum()
        main_window.timeline_slider.setValue(min_frame)
        main_window.statusBar().showMessage(f"Moved to first frame ({min_frame})", 2000)
    
    @staticmethod
    def go_to_last_frame(main_window):
        """Go to the last frame in the timeline."""
        if not main_window.curve_data:
            return
            
        max_frame = main_window.timeline_slider.maximum()
        main_window.timeline_slider.setValue(max_frame)
        main_window.statusBar().showMessage(f"Moved to last frame ({max_frame})", 2000)

    @staticmethod
    def setup_enhanced_controls(main_window):
        """Set up enhanced visualization controls.
        
        Creates UI buttons for visualization features available in the EnhancedCurveView:
        - Grid toggle (using QPushButton from PySide6.QtWidgets)
        - Velocity vectors toggle (using QPushButton from PySide6.QtWidgets)
        - Frame numbers toggle (using QPushButton from PySide6.QtWidgets)
        - Crosshair toggle (using QPushButton from PySide6.QtWidgets)
        - View centering (using QPushButton from PySide6.QtWidgets)
        - Point size control (using QSpinBox from PySide6.QtWidgets)
        
        All buttons are initialized with proper tooltips and checkable states.
        Buttons are added to a QGroupBox (from PySide6.QtWidgets) with appropriate layout.
        Signal connections are handled in the connect_all_signals method, not here.
        
        Args:
            main_window: The main application window instance
        """
        main_window.enhanced_controls_group = QGroupBox("Enhanced Visualization")
        enhanced_layout = QHBoxLayout(main_window.enhanced_controls_group)
        
        main_window.toggle_grid_button = QPushButton("Grid")
        main_window.toggle_grid_button.setCheckable(True)
        main_window.toggle_grid_button.setChecked(False)
        main_window.toggle_grid_button.setToolTip("Toggle grid (G)")
        
        main_window.toggle_vectors_button = QPushButton("Vectors")
        main_window.toggle_vectors_button.setCheckable(True)
        main_window.toggle_vectors_button.setChecked(False)
        main_window.toggle_vectors_button.setToolTip("Toggle velocity vectors (V)")
        
        main_window.toggle_frame_numbers_button = QPushButton("Frame Numbers")
        main_window.toggle_frame_numbers_button.setCheckable(True)
        main_window.toggle_frame_numbers_button.setChecked(False)
        main_window.toggle_frame_numbers_button.setToolTip("Toggle all frame numbers (F)")
        
        main_window.toggle_crosshair_button = QPushButton("Crosshair")
        main_window.toggle_crosshair_button.setCheckable(True)
        main_window.toggle_crosshair_button.setChecked(True)
        main_window.toggle_crosshair_button.setToolTip("Toggle crosshair display (X)")
        
        main_window.center_on_point_button = QPushButton("Center")
        main_window.center_on_point_button.setToolTip("Center view on selected point (C)")
        
        # Add point size control
        point_size_layout = QHBoxLayout()
        point_size_layout.addWidget(QLabel("Point Size:"))
        main_window.point_size_spin = QSpinBox()
        main_window.point_size_spin.setMinimum(1)
        main_window.point_size_spin.setMaximum(10)
        main_window.point_size_spin.setValue(2)  # Default matches EnhancedCurveView's default
        main_window.point_size_spin.setToolTip("Change the size of points in the curve view")
        point_size_layout.addWidget(main_window.point_size_spin)
        
        enhanced_layout.addWidget(main_window.toggle_grid_button)
        enhanced_layout.addWidget(main_window.toggle_vectors_button)
        enhanced_layout.addWidget(main_window.toggle_frame_numbers_button)
        enhanced_layout.addWidget(main_window.toggle_crosshair_button)
        enhanced_layout.addWidget(main_window.center_on_point_button)
        enhanced_layout.addLayout(point_size_layout)
        
        # Add to view controls section
        if hasattr(main_window, 'view_controls_layout'):
            main_window.view_controls_layout.addWidget(main_window.enhanced_controls_group)
            
    @staticmethod
    def connect_all_signals(main_window):
        """Connect all signals to their respective slots."""
        
        print("\n" + "="*80)
        print("CONNECTING ALL SIGNALS:")
        
        # Check if image_operations exists before connecting signals
        if hasattr(main_window, 'image_operations'):
            print("Connecting image_operations signals...")
            # Connect controls to actions
            main_window.action_open.triggered.connect(lambda: ImageOperations.load_images(main_window))
            main_window.action_open_directory.triggered.connect(lambda: ImageOperations.open_directory(main_window))
            main_window.action_save.triggered.connect(lambda: CurveOperations.save_curve_data(main_window))
            main_window.action_exit.triggered.connect(main_window.close)
        else:
            print("WARNING: image_operations not found, some signals not connected")
            
        # Connect slider signals - timeline slider already connected in setup_timeline
        if hasattr(main_window, 'point_size_spin'):
            print("Connecting point_size_spin signal...")
            main_window.point_size_spin.valueChanged.connect(
                lambda value: CurveViewOperations.set_point_size(main_window, value)
            )
            
        # Connect enhanced curve view signals if they exist
        if hasattr(main_window, 'curve_view'):
            try:
                # Properly identify the class to ensure we're checking the right type
                from enhanced_curve_view import EnhancedCurveView
                
                if isinstance(main_window.curve_view, EnhancedCurveView):
                    print("Connecting EnhancedCurveView signals...")
                    print("Signals available in curve_view:", [
                        signal for signal in dir(main_window.curve_view) 
                        if isinstance(getattr(main_window.curve_view, signal), Signal)
                    ])
                    
                    # Connect enhanced curve view signals
                    if hasattr(main_window.curve_view, 'point_selected'):
                        main_window.curve_view.point_selected.connect(
                            lambda idx: CurveViewOperations.on_point_selected(main_window, idx)
                        )
                        print("Connected: curve_view.point_selected -> CurveViewOperations.on_point_selected")
                        
                    if hasattr(main_window.curve_view, 'point_moved'):
                        main_window.curve_view.point_moved.connect(
                            lambda idx, x, y: CurveViewOperations.on_point_moved(main_window, idx, x, y)
                        )
                        print("Connected: curve_view.point_moved -> CurveViewOperations.on_point_moved")
                        
                    if hasattr(main_window.curve_view, 'image_changed'):
                        main_window.curve_view.image_changed.connect(main_window.on_image_changed)
                        print("Connected: curve_view.image_changed -> main_window.on_image_changed")
                        
                        # Test the signal connection with a direct emit
                        if hasattr(main_window.curve_view, 'current_image_idx') and main_window.curve_view.current_image_idx >= 0:
                            print(f"Testing image_changed signal with index {main_window.curve_view.current_image_idx}")
                            main_window.curve_view.image_changed.emit(main_window.curve_view.current_image_idx)
                else:
                    print("curve_view is not an instance of EnhancedCurveView, it's:", type(main_window.curve_view))
            except Exception as e:
                print(f"Error connecting enhanced curve view signals: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print("WARNING: curve_view not found, curve view signals not connected")
            
        print("="*80 + "\n")