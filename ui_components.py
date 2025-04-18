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

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QLineEdit,
    QGroupBox, QSplitter, QToolBar, QFrame,
    QGridLayout, QTabWidget, QSpacerItem,
    QSizePolicy, QComboBox, QStatusBar, QSpinBox
)
from PySide6.QtCore import Signal, Qt, QSize, QTimer, QEvent
from PySide6.QtGui import (
    QIcon, QFont, QAction, QKeySequence,
    QPainter, QPainterPath, QColor, QShortcut
)

from curve_view_operations import CurveViewOperations
from visualization_operations import VisualizationOperations
from image_operations import ImageOperations
from dialog_operations import DialogOperations
# from curve_operations import CurveOperations # Removed, logic moved
from history_operations import HistoryOperations # For undo/redo
from centering_zoom_operations import ZoomOperations # Added Import

from enhanced_curve_view import EnhancedCurveView
import os
import re


class TimelineFrameMarker(QWidget):
    """Custom widget to show the current frame position marker in the timeline."""
    
    def __init__(self, parent=None):
        super(TimelineFrameMarker, self).__init__(parent)
        self.position = 0
        self.setFixedHeight(10)
        self.setMinimumWidth(100)
        
    def setPosition(self, position):
        """Set the relative position of the marker (0.0 to 1.0)."""
        self.position = max(0.0, min(1.0, position))
        self.update()
        
    def paintEvent(self, event):
        """Draw the frame marker."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate marker position
        width = self.width()
        x_pos = int(width * self.position)
        
        # Draw the triangle marker
        path = QPainterPath()
        path.moveTo(x_pos, 0)
        path.lineTo(x_pos - 5, 10)
        path.lineTo(x_pos + 5, 10)
        path.closeSubpath()
        
        painter.fillPath(path, QColor(255, 0, 0))


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
        main_window.smooth_button.setEnabled(True)
        
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
        # main_window.undo_button.clicked.connect(lambda: CurveOperations.undo(main_window)) # Original call removed
        main_window.undo_button.clicked.connect(lambda: HistoryOperations.undo_action(main_window)) # Use HistoryOperations
        main_window.undo_button.setEnabled(False)
        
        main_window.redo_button = QPushButton("Redo")
        main_window.redo_button.setToolTip("Redo Last Action")
        # main_window.redo_button.clicked.connect(lambda: CurveOperations.redo(main_window)) # Original call removed
        main_window.redo_button.clicked.connect(lambda: HistoryOperations.redo_action(main_window)) # Use HistoryOperations
        main_window.redo_button.setEnabled(False)
        
        main_window.detect_problems_button = QPushButton("Detect")
        main_window.detect_problems_button.setToolTip("Detect Problems in Track Data")
        # main_window.detect_problems_button.clicked.connect(lambda: DialogOperations.show_problem_detection_dialog(main_window, CurveOperations.detect_problems(main_window))) # TODO: Refactor detect_problems
        # Temporarily disable until detect_problems is refactored
        main_window.detect_problems_button.setEnabled(False)
        main_window.detect_problems_button.setToolTip("Problem detection temporarily disabled during refactoring.")
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
        
        # Add frame jump buttons
        main_window.first_frame_button = QPushButton("<<")
        main_window.first_frame_button.clicked.connect(lambda: UIComponents.go_to_first_frame(main_window))
        main_window.first_frame_button.setToolTip("Go to First Frame (Home)")
        main_window.first_frame_button.setEnabled(False)
        
        main_window.last_frame_button = QPushButton(">>")
        main_window.last_frame_button.clicked.connect(lambda: UIComponents.go_to_last_frame(main_window))
        main_window.last_frame_button.setToolTip("Go to Last Frame (End)")
        main_window.last_frame_button.setEnabled(False)
        
        timeline_controls.addWidget(main_window.first_frame_button)
        
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
        timeline_controls.addWidget(main_window.last_frame_button)
        timeline_controls.addStretch()
        
        timeline_layout.addLayout(timeline_controls)
        
        # Enhanced Timeline slider with individual frame ticks
        main_window.timeline_slider = QSlider(Qt.Horizontal)
        main_window.timeline_slider.setMinimum(0)
        main_window.timeline_slider.setMaximum(100)  # Will be updated when data is loaded
        
        # Configure slider to show individual frames
        main_window.timeline_slider.setTickPosition(QSlider.TicksBelow)
        main_window.timeline_slider.setSingleStep(1)    # Move by 1 frame at a time
        main_window.timeline_slider.setPageStep(1)      # Page step is also 1 frame
        
        # Determine a reasonable tick interval based on frame count
        frame_count = 100  # Default to 100 frames
        tick_interval = max(1, frame_count // 100)  # Prevent too many ticks on large frame ranges
        main_window.timeline_slider.setTickInterval(tick_interval)
        
        # Add frame tracking tooltip
        main_window.timeline_slider.setToolTip("Frame: 0")
        
        # Connect signals
        main_window.timeline_slider.valueChanged.connect(lambda value: UIComponents.on_timeline_changed(main_window, value))
        
        # Create frame marker for better visual indication
        main_window.frame_marker = TimelineFrameMarker()
        
        # Create a layout for the slider with the marker
        slider_layout = QVBoxLayout()
        slider_layout.addWidget(main_window.frame_marker)
        slider_layout.addWidget(main_window.timeline_slider)
        slider_layout.setSpacing(0)
        
        timeline_layout.addLayout(slider_layout)
        
        # Add mouse event handler for frame scrubbing
        def on_timeline_press(event):
            """Handle mouse press on timeline for direct frame selection."""
            if event.button() == Qt.LeftButton:
                # Calculate the frame based on click position
                slider = main_window.timeline_slider
                width = slider.width()
                pos = event.pos().x()
                
                # Get the frame range
                min_frame = slider.minimum()
                max_frame = slider.maximum()
                frame_range = max_frame - min_frame
                
                # Calculate the frame based on position
                if width > 0 and frame_range > 0:
                    frame = min_frame + int((pos / width) * frame_range + 0.5)
                    frame = max(min_frame, min(max_frame, frame))
                    
                    # Update the slider
                    slider.setValue(frame)
                    
                    # Update status message
                    main_window.statusBar().showMessage(f"Jumped to frame {frame}", 2000)
        
        # Store original event handler
        original_press_event = main_window.timeline_slider.mousePressEvent
        
        # Override mouse press event
        def custom_press_event(event):
            on_timeline_press(event)
            # Call original handler if needed
            if original_press_event:
                original_press_event(event)
                
        main_window.timeline_slider.mousePressEvent = custom_press_event
        
        view_layout.addWidget(timeline_widget)
        
        return view_container

    @staticmethod
    def create_enhanced_curve_view(main_window):
        """Create and set up the enhanced curve view."""
        # ... (Code as before) ...
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
                
                # Add a reference to the visualization operations method for timeline updates
                from visualization_operations import VisualizationOperations
                
                # Create a wrapper method that calls the visualization operations method
                def update_timeline_for_image(index):
                    """Wrapper method to update the timeline for the current image."""
                    VisualizationOperations.update_timeline_for_image(main_window, index)
                
                # Attach the wrapper method to the curve view for backward compatibility
                main_window.curve_view.updateTimelineForImage = update_timeline_for_image
                
                return True
        except Exception as e:
            print(f"Error creating enhanced curve view: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def create_control_panel(main_window):
        """Create the control panel for point editing and view controls."""
        # ... (Code as before) ...
        # Main container for controls
        controls_container = QWidget()
        controls_layout = QHBoxLayout(controls_container)
        
        # Left side: Point Info and Editing
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Point Info Group
        point_info_group = QGroupBox("Point Info")
        point_info_layout = QGridLayout(point_info_group)
        
        main_window.frame_info_label = QLabel("Frame: N/A")
        main_window.x_label = QLabel("X:")
        main_window.x_edit = QLineEdit()
        main_window.y_label = QLabel("Y:")
        main_window.y_edit = QLineEdit()
        main_window.update_point_button = QPushButton("Update Point")
        
        point_info_layout.addWidget(main_window.frame_info_label, 0, 0, 1, 2)
        point_info_layout.addWidget(main_window.x_label, 1, 0)
        point_info_layout.addWidget(main_window.x_edit, 1, 1)
        point_info_layout.addWidget(main_window.y_label, 2, 0)
        point_info_layout.addWidget(main_window.y_edit, 2, 1)
        point_info_layout.addWidget(main_window.update_point_button, 3, 0, 1, 2)
        
        left_layout.addWidget(point_info_group)
        
        # Selection Controls Group
        selection_group = QGroupBox("Selection")
        selection_layout = QHBoxLayout(selection_group)
        main_window.select_all_button = QPushButton("Select All")
        main_window.deselect_all_button = QPushButton("Deselect All")
        selection_layout.addWidget(main_window.select_all_button)
        selection_layout.addWidget(main_window.deselect_all_button)
        left_layout.addWidget(selection_group)
        
        left_layout.addStretch() # Push controls to the top
        
        # Center: Visualization Controls
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        
        vis_group = QGroupBox("Visualization")
        vis_layout = QGridLayout(vis_group)
        
        main_window.toggle_grid_button = QPushButton("Grid")
        main_window.toggle_grid_button.setCheckable(True)
        main_window.toggle_grid_button.setToolTip("Toggle Grid Visibility (G)")
        
        main_window.toggle_vectors_button = QPushButton("Vectors")
        main_window.toggle_vectors_button.setCheckable(True)
        main_window.toggle_vectors_button.setToolTip("Toggle Velocity Vectors (V)")
        
        main_window.toggle_frame_numbers_button = QPushButton("Numbers")
        main_window.toggle_frame_numbers_button.setCheckable(True)
        main_window.toggle_frame_numbers_button.setToolTip("Toggle Frame Numbers (F)")
        
        main_window.toggle_crosshair_button = QPushButton("Crosshair")
        main_window.toggle_crosshair_button.setCheckable(True)
        main_window.toggle_crosshair_button.setToolTip("Toggle Crosshair (X)")
        
        main_window.center_on_point_button = QPushButton("Center")
        main_window.center_on_point_button.setToolTip("Center View on Selected Point (C)")
        
        main_window.point_size_label = QLabel("Point Size:")
        main_window.point_size_spin = QSpinBox()
        main_window.point_size_spin.setRange(1, 20)
        main_window.point_size_spin.setValue(5) # Default size
        main_window.point_size_spin.setToolTip("Adjust Point Size")
        
        vis_layout.addWidget(main_window.toggle_grid_button, 0, 0)
        vis_layout.addWidget(main_window.toggle_vectors_button, 0, 1)
        vis_layout.addWidget(main_window.toggle_frame_numbers_button, 1, 0)
        vis_layout.addWidget(main_window.toggle_crosshair_button, 1, 1)
        vis_layout.addWidget(main_window.center_on_point_button, 2, 0, 1, 2)
        vis_layout.addWidget(main_window.point_size_label, 3, 0)
        vis_layout.addWidget(main_window.point_size_spin, 3, 1)
        
        center_layout.addWidget(vis_group)
        center_layout.addStretch()
        
        # Right side: Track Quality and Presets
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Track Quality Group
        quality_group = QGroupBox("Track Quality")
        quality_layout = QGridLayout(quality_group) # Use GridLayout for better alignment

        # Create labels for metrics
        quality_layout.addWidget(QLabel("Overall Score:"), 0, 0)
        main_window.quality_score_label = QLabel("N/A")
        main_window.quality_score_label.setFont(QFont("Arial", 10, QFont.Bold))
        quality_layout.addWidget(main_window.quality_score_label, 0, 1)

        quality_layout.addWidget(QLabel("Smoothness:"), 1, 0)
        main_window.smoothness_label = QLabel("N/A")
        quality_layout.addWidget(main_window.smoothness_label, 1, 1)

        quality_layout.addWidget(QLabel("Consistency:"), 2, 0)
        main_window.consistency_label = QLabel("N/A")
        quality_layout.addWidget(main_window.consistency_label, 2, 1)

        quality_layout.addWidget(QLabel("Coverage:"), 3, 0)
        main_window.coverage_label = QLabel("N/A")
        quality_layout.addWidget(main_window.coverage_label, 3, 1)

        # Add Analyze button (assuming it should trigger the analysis)
        main_window.analyze_button = QPushButton("Analyze Quality")
        main_window.analyze_button.setToolTip("Analyze the quality of the current track data")
        # Connection should be handled by SignalRegistry or MainWindow setup
        # main_window.analyze_button.clicked.connect(lambda: main_window.quality_ui.analyze_and_update_ui(main_window.curve_data))
        quality_layout.addWidget(main_window.analyze_button, 4, 0, 1, 2)

        right_layout.addWidget(quality_group)
        
        # Quick Filter Presets Group
        presets_group = QGroupBox("Quick Filters")
        presets_layout = QVBoxLayout(presets_group)
        main_window.presets_combo = QComboBox()
        main_window.presets_combo.addItems(["Select Preset...", "Smooth Light", "Smooth Medium", "Smooth Heavy", "Filter Jitter"])
        main_window.apply_preset_button = QPushButton("Apply Preset")
        presets_layout.addWidget(main_window.presets_combo)
        presets_layout.addWidget(main_window.apply_preset_button)
        right_layout.addWidget(presets_group)
        
        right_layout.addStretch()
        
        # Add panels to main controls layout
        controls_layout.addWidget(left_panel)
        controls_layout.addWidget(center_panel)
        controls_layout.addWidget(right_panel)
        
        # Disable controls initially
        main_window.enable_point_controls(False)
        
        return controls_container

    @staticmethod
    def setup_timeline(main_window):
        """Setup timeline slider based on frame range."""
        # ... (Code as before) ...
        if not main_window.curve_data:
            main_window.timeline_slider.setEnabled(False)
            main_window.frame_edit.setEnabled(False)
            main_window.go_button.setEnabled(False)
            main_window.play_button.setEnabled(False)
            main_window.prev_frame_button.setEnabled(False)
            main_window.next_frame_button.setEnabled(False)
            main_window.first_frame_button.setEnabled(False)
            main_window.last_frame_button.setEnabled(False)
            return
            
        # Get frame range from data
        frames = [p[0] for p in main_window.curve_data]
        min_frame = min(frames) if frames else 0
        max_frame = max(frames) if frames else 0
        frame_count = max_frame - min_frame + 1
        
        # Update slider range
        main_window.timeline_slider.setMinimum(min_frame)
        main_window.timeline_slider.setMaximum(max_frame)
        
        # Update tick interval based on new range
        tick_interval = max(1, frame_count // 100)
        main_window.timeline_slider.setTickInterval(tick_interval)
        
        # Set current frame if not already set or out of range
        if main_window.current_frame < min_frame or main_window.current_frame > max_frame:
            main_window.current_frame = min_frame
            
        # Update slider value without triggering signals initially
        main_window.timeline_slider.blockSignals(True)
        main_window.timeline_slider.setValue(main_window.current_frame)
        main_window.timeline_slider.blockSignals(False)
        
        # Update labels and edit fields
        main_window.frame_label.setText(f"Frame: {main_window.current_frame}")
        main_window.frame_edit.setText(str(main_window.current_frame))
        
        # Update frame marker position
        if hasattr(main_window, 'frame_marker'):
            main_window.frame_marker.setPosition(0)  # Start at beginning
        
        print(f"UIComponents: Timeline setup complete with {frame_count} discrete frames from {min_frame} to {max_frame}")

    @staticmethod
    def on_timeline_changed(main_window, value):
        """Handle timeline slider value changed with enhanced feedback."""
        main_window.current_frame = value
        
        # Update frame edit and label
        main_window.frame_edit.setText(str(value))
        main_window.frame_label.setText(f"Frame: {value}")
        
        # Update tooltip to show current frame
        main_window.timeline_slider.setToolTip(f"Frame: {value}")
        
        # Update the frame marker position
        if hasattr(main_window, 'frame_marker'):
            # Calculate position based on slider value
            slider_min = main_window.timeline_slider.minimum()
            slider_max = main_window.timeline_slider.maximum()
            
            # Only update if we have a valid range
            if slider_max > slider_min:
                frame_range = slider_max - slider_min
                position_ratio = (value - slider_min) / frame_range
                main_window.frame_marker.setPosition(position_ratio)
                main_window.frame_marker.update()
        
        # Load the corresponding image if we have an image sequence
        if main_window.image_filenames:
            # Update the image by frame
            main_window.curve_view.setCurrentImageByFrame(value)
            main_window.update_image_label()
                    
        # Auto-center if enabled
        if getattr(main_window, 'auto_center_enabled', False) and hasattr(main_window, 'curve_view'):
            try:
                ZoomOperations.center_on_selected_point(main_window.curve_view, preserve_zoom=True)
            except Exception as e:
                print(f"Error during auto-centering: {e}")
        
        # Update view AFTER potential centering
        main_window.curve_view.update()
    
    @staticmethod
    def on_frame_edit_changed(main_window):
        """Handle frame edit text changed."""
        try:
            value = int(main_window.frame_edit.text())
            min_val = main_window.timeline_slider.minimum()
            max_val = main_window.timeline_slider.maximum()
            
            if min_val <= value <= max_val:
                # Directly call go_to_frame to ensure consistent handling including centering
                UIComponents.go_to_frame(main_window, value)
            else:
                main_window.statusBar().showMessage(f"Frame {value} out of range ({min_val}-{max_val})", 2000)
        except ValueError:
            main_window.statusBar().showMessage("Invalid frame number entered", 2000)
            
    @staticmethod
    def toggle_playback(main_window):
        """Toggle timeline playback on/off."""
        # ... (Code as before) ...
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
            
        # Start playback
        # TODO: Add FPS setting
        fps = 24 # Default FPS
        main_window.playback_timer.start(1000 // fps)
        main_window.play_button.setChecked(True)
        main_window.statusBar().showMessage("Playback started", 2000)

    @staticmethod
    def advance_playback(main_window):
        """Advance timeline by one frame during playback."""
        # ... (Code as before) ...
        current_frame = main_window.timeline_slider.value()
        max_frame = main_window.timeline_slider.maximum()
        
        if current_frame < max_frame:
            main_window.timeline_slider.setValue(current_frame + 1)
        else:
            # Stop playback at the end
            main_window.playback_timer.stop()
            main_window.play_button.setChecked(False)
            main_window.statusBar().showMessage("Playback finished", 2000)

    @staticmethod
    def next_frame(main_window):
        """Go to the next frame in the timeline."""
        if not main_window.curve_data:
            return
            
        current_frame = main_window.timeline_slider.value()
        max_frame = main_window.timeline_slider.maximum()
        
        if current_frame < max_frame:
            new_frame = current_frame + 1
            main_window.timeline_slider.setValue(new_frame)
            # Explicitly call centering logic here as well
            if getattr(main_window, 'auto_center_enabled', False) and hasattr(main_window, 'curve_view'):
                try:
                    ZoomOperations.center_on_selected_point(main_window.curve_view, preserve_zoom=True)
                except Exception as e:
                    print(f"Error during auto-centering in next_frame: {e}")
            main_window.curve_view.update() # Ensure view updates

    @staticmethod
    def prev_frame(main_window):
        """Go to the previous frame in the timeline."""
        if not main_window.curve_data:
            return
            
        current_frame = main_window.timeline_slider.value()
        min_frame = main_window.timeline_slider.minimum()
        
        if current_frame > min_frame:
            new_frame = current_frame - 1
            main_window.timeline_slider.setValue(new_frame)
             # Explicitly call centering logic here as well
            if getattr(main_window, 'auto_center_enabled', False) and hasattr(main_window, 'curve_view'):
                try:
                    ZoomOperations.center_on_selected_point(main_window.curve_view, preserve_zoom=True)
                except Exception as e:
                    print(f"Error during auto-centering in prev_frame: {e}")
            main_window.curve_view.update() # Ensure view updates

    @staticmethod
    def advance_frames(main_window, count):
        """Advance timeline by specified number of frames (positive or negative)."""
        if not main_window.curve_data:
            return
            
        current_frame = main_window.timeline_slider.value()
        min_frame = main_window.timeline_slider.minimum()
        max_frame = main_window.timeline_slider.maximum()
        
        new_frame = current_frame + count
        new_frame = max(min_frame, min(max_frame, new_frame))
        
        main_window.timeline_slider.setValue(new_frame)
        # Explicitly call centering logic here as well
        if getattr(main_window, 'auto_center_enabled', False) and hasattr(main_window, 'curve_view'):
            try:
                ZoomOperations.center_on_selected_point(main_window.curve_view, preserve_zoom=True)
            except Exception as e:
                print(f"Error during auto-centering in advance_frames: {e}")
        main_window.curve_view.update() # Ensure view updates
        main_window.statusBar().showMessage(f"Advanced {count} frames to frame {new_frame}", 2000)
            
    @staticmethod
    def go_to_frame(main_window, frame):
        """Go to a specific frame."""
        if not main_window.curve_data:
            return
            
        min_frame = main_window.timeline_slider.minimum()
        max_frame = main_window.timeline_slider.maximum()
        
        if min_frame <= frame <= max_frame:
            main_window.timeline_slider.setValue(frame)
             # Explicitly call centering logic here as well
            if getattr(main_window, 'auto_center_enabled', False) and hasattr(main_window, 'curve_view'):
                try:
                    ZoomOperations.center_on_selected_point(main_window.curve_view, preserve_zoom=True)
                except Exception as e:
                    print(f"Error during auto-centering in go_to_frame: {e}")
            main_window.curve_view.update() # Ensure view updates
        else:
            main_window.statusBar().showMessage(f"Frame {frame} is out of range ({min_frame}-{max_frame})", 2000)

    @staticmethod
    def go_to_first_frame(main_window):
        """Go to the first frame in the timeline."""
        if not main_window.curve_data:
            return
            
        min_frame = main_window.timeline_slider.minimum()
        main_window.timeline_slider.setValue(min_frame)
        # Explicitly call centering logic here as well
        if getattr(main_window, 'auto_center_enabled', False) and hasattr(main_window, 'curve_view'):
            try:
                ZoomOperations.center_on_selected_point(main_window.curve_view, preserve_zoom=True)
            except Exception as e:
                print(f"Error during auto-centering in go_to_first_frame: {e}")
        main_window.curve_view.update() # Ensure view updates
        main_window.statusBar().showMessage(f"Moved to first frame ({min_frame})", 2000)
    
    @staticmethod
    def go_to_last_frame(main_window):
        """Go to the last frame in the timeline."""
        if not main_window.curve_data:
            return
            
        max_frame = main_window.timeline_slider.maximum()
        main_window.timeline_slider.setValue(max_frame)
        # Explicitly call centering logic here as well
        if getattr(main_window, 'auto_center_enabled', False) and hasattr(main_window, 'curve_view'):
            try:
                ZoomOperations.center_on_selected_point(main_window.curve_view, preserve_zoom=True)
            except Exception as e:
                print(f"Error during auto-centering in go_to_last_frame: {e}")
        main_window.curve_view.update() # Ensure view updates
        main_window.statusBar().showMessage(f"Moved to last frame ({max_frame})", 2000)

    @staticmethod
    def update_frame_marker(main_window):
        """Update the position of the frame marker based on current frame."""
        # ... (Code as before) ...
        if hasattr(main_window, 'frame_marker') and hasattr(main_window, 'timeline_slider'):
            slider = main_window.timeline_slider
            min_frame = slider.minimum()
            max_frame = slider.maximum()
            current_frame = slider.value()
            
            # Calculate relative position in the slider
            if max_frame > min_frame:
                position = (current_frame - min_frame) / (max_frame - min_frame)
                main_window.frame_marker.setPosition(position)
                main_window.frame_marker.update()

    @staticmethod
    def setup_enhanced_curve_view(main_window):
        """Set up enhanced visualization controls."""
        # ... (Code as before) ...
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
                
                # Add a reference to the visualization operations method for timeline updates
                from visualization_operations import VisualizationOperations
                
                # Create a wrapper method that calls the visualization operations method
                def update_timeline_for_image(index):
                    """Wrapper method to update the timeline for the current image."""
                    VisualizationOperations.update_timeline_for_image(main_window, index)
                
                # Attach the wrapper method to the curve view for backward compatibility
                main_window.curve_view.updateTimelineForImage = update_timeline_for_image
                
                return True
        except Exception as e:
            print(f"Error creating enhanced curve view: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def setup_enhanced_controls(main_window):
        """Set up enhanced visualization controls in the control panel."""
        # ... (Code as before) ...
        # Find the existing visualization group box or create it if needed
        vis_group = None
        if hasattr(main_window, 'controls_container'):
            # Search for the QGroupBox named "Visualization"
            for child in main_window.controls_container.findChildren(QGroupBox):
                if child.title() == "Visualization":
                    vis_group = child
                    break
                    
        if vis_group is None:
            # If not found, create it (this might indicate a UI structure issue)
            vis_group = QGroupBox("Visualization")
            # Add it to an appropriate layout (assuming center_layout exists)
            if hasattr(main_window, 'center_layout'):
                main_window.center_layout.addWidget(vis_group)
            else:
                print("Warning: Could not find layout to add Visualization group box.")
                return # Cannot proceed without a layout
                
        # Ensure the group box has a layout
        if vis_group.layout() is None:
            vis_layout = QGridLayout(vis_group)
        else:
            vis_layout = vis_group.layout()
            # Clear existing widgets if necessary (or adjust logic as needed)
            # while vis_layout.count():
            #     child = vis_layout.takeAt(0)
            #     if child.widget():
            #         child.widget().deleteLater()
                    
        # Create and add enhanced controls
        main_window.toggle_grid_button = QPushButton("Grid")
        main_window.toggle_grid_button.setCheckable(True)
        main_window.toggle_grid_button.setToolTip("Toggle Grid Visibility (G)")
        
        main_window.toggle_vectors_button = QPushButton("Vectors")
        main_window.toggle_vectors_button.setCheckable(True)
        main_window.toggle_vectors_button.setToolTip("Toggle Velocity Vectors (V)")
        
        main_window.toggle_frame_numbers_button = QPushButton("Numbers")
        main_window.toggle_frame_numbers_button.setCheckable(True)
        main_window.toggle_frame_numbers_button.setToolTip("Toggle Frame Numbers (F)")
        
        main_window.toggle_crosshair_button = QPushButton("Crosshair")
        main_window.toggle_crosshair_button.setCheckable(True)
        main_window.toggle_crosshair_button.setToolTip("Toggle Crosshair (X)")
        
        main_window.center_on_point_button = QPushButton("Center")
        main_window.center_on_point_button.setToolTip("Center View on Selected Point (C)")
        
        main_window.point_size_label = QLabel("Point Size:")
        main_window.point_size_spin = QSpinBox()
        main_window.point_size_spin.setRange(1, 20)
        main_window.point_size_spin.setValue(5) # Default size
        main_window.point_size_spin.setToolTip("Adjust Point Size")
        
        # Add widgets to layout
        vis_layout.addWidget(main_window.toggle_grid_button, 0, 0)
        vis_layout.addWidget(main_window.toggle_vectors_button, 0, 1)
        vis_layout.addWidget(main_window.toggle_frame_numbers_button, 1, 0)
        vis_layout.addWidget(main_window.toggle_crosshair_button, 1, 1)
        vis_layout.addWidget(main_window.center_on_point_button, 2, 0, 1, 2)
        vis_layout.addWidget(main_window.point_size_label, 3, 0)
        vis_layout.addWidget(main_window.point_size_spin, 3, 1)
        
        # Connect signals (moved to SignalRegistry)
        # SignalRegistry.connect_all_signals(main_window) # Ensure signals are connected

    @staticmethod
    def connect_all_signals(main_window):
        """Connect all UI signals to their respective slots.
        
        This method centralizes signal connections for better maintainability.
        It ensures that signals are connected only once and provides error handling.
        
        Args:
            main_window: The main application window instance
        """
        # Use the SignalRegistry to handle connections
        from signal_registry import SignalRegistry
        SignalRegistry.connect_all_signals(main_window)

# ... (rest of file, if any) ...
