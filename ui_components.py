#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QSlider, QLineEdit, 
                              QGroupBox, QSplitter, QToolBar, QAction, QFrame, 
                              QGridLayout, QTabWidget, QSpacerItem, 
                              QSizePolicy, QComboBox, QStatusBar)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QFont


class UIComponents:
    """UI component creation for the 3DE4 Curve Editor."""
    
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
        main_window.reset_view_button.clicked.connect(main_window.reset_view)
        
        main_window.load_images_button = QPushButton("Images")
        main_window.load_images_button.setToolTip("Load Image Sequence")
        main_window.load_images_button.clicked.connect(main_window.load_image_sequence)
        
        main_window.toggle_bg_button = QPushButton("Toggle BG")
        main_window.toggle_bg_button.setToolTip("Toggle Background Visibility")
        main_window.toggle_bg_button.clicked.connect(main_window.toggle_background)
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
        main_window.smooth_button.clicked.connect(main_window.show_smooth_dialog)
        main_window.smooth_button.setEnabled(False)
        
        main_window.fill_gaps_button = QPushButton("Fill Gaps")
        main_window.fill_gaps_button.setToolTip("Fill Gaps in Tracking Data")
        main_window.fill_gaps_button.clicked.connect(main_window.show_fill_gaps_dialog)
        main_window.fill_gaps_button.setEnabled(False)
        
        main_window.filter_button = QPushButton("Filter")
        main_window.filter_button.setToolTip("Apply Filter to Curve")
        main_window.filter_button.clicked.connect(main_window.show_filter_dialog)
        main_window.filter_button.setEnabled(False)
        
        main_window.extrapolate_button = QPushButton("Extrapolate")
        main_window.extrapolate_button.setToolTip("Extrapolate Curve")
        main_window.extrapolate_button.clicked.connect(main_window.show_extrapolate_dialog)
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
        main_window.undo_button.clicked.connect(main_window.undo_action)
        main_window.undo_button.setEnabled(False)
        
        main_window.redo_button = QPushButton("Redo")
        main_window.redo_button.setToolTip("Redo Last Action")
        main_window.redo_button.clicked.connect(main_window.redo_action)
        main_window.redo_button.setEnabled(False)
        
        main_window.detect_problems_button = QPushButton("Detect")
        main_window.detect_problems_button.setToolTip("Detect Problems in Track Data")
        main_window.detect_problems_button.clicked.connect(main_window.detect_problems)
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
        
        # Create curve view
        main_window.curve_view = main_window.curve_view_class()
        main_window.curve_view.point_moved.connect(main_window.on_point_moved)
        main_window.curve_view.point_selected.connect(main_window.on_point_selected)
        main_window.curve_view.image_changed.connect(main_window.on_image_changed)
        
        view_layout.addWidget(main_window.curve_view)
        
        # Timeline widget
        timeline_widget = QWidget()
        timeline_layout = QVBoxLayout(timeline_widget)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        
        # Image sequence controls
        image_controls = QHBoxLayout()
        main_window.prev_image_button = QPushButton("Previous")
        main_window.prev_image_button.clicked.connect(main_window.previous_image)
        main_window.prev_image_button.setEnabled(False)
        
        main_window.next_image_button = QPushButton("Next")
        main_window.next_image_button.clicked.connect(main_window.next_image)
        main_window.next_image_button.setEnabled(False)
        
        main_window.image_label = QLabel("No images loaded")
        
        # Opacity slider
        main_window.opacity_slider = QSlider(Qt.Horizontal)
        main_window.opacity_slider.setMinimum(0)
        main_window.opacity_slider.setMaximum(100)
        main_window.opacity_slider.setValue(70)  # Default 70% opacity
        main_window.opacity_slider.setEnabled(False)
        main_window.opacity_slider.valueChanged.connect(main_window.opacity_changed)
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity:"))
        opacity_layout.addWidget(main_window.opacity_slider)
        
        image_controls.addWidget(main_window.prev_image_button)
        image_controls.addWidget(main_window.image_label)
        image_controls.addWidget(main_window.next_image_button)
        image_controls.addStretch()
        image_controls.addLayout(opacity_layout)
        
        timeline_layout.addLayout(image_controls)
        
        # Timeline slider
        main_window.timeline_slider = QSlider(Qt.Horizontal)
        main_window.timeline_slider.setMinimum(0)
        main_window.timeline_slider.setMaximum(100)  # Will be updated when data is loaded
        main_window.timeline_slider.valueChanged.connect(main_window.on_timeline_changed)
        
        # Frame controls
        timeline_info_layout = QHBoxLayout()
        main_window.frame_label = QLabel("Frame: N/A")
        main_window.frame_edit = QLineEdit()
        main_window.frame_edit.setMaximumWidth(60)
        main_window.frame_edit.returnPressed.connect(main_window.on_frame_edit_changed)
        main_window.go_button = QPushButton("Go")
        main_window.go_button.clicked.connect(main_window.on_frame_edit_changed)
        main_window.go_button.setMaximumWidth(50)
        
        timeline_info_layout.addWidget(main_window.frame_label)
        timeline_info_layout.addWidget(main_window.frame_edit)
        timeline_info_layout.addWidget(main_window.go_button)
        timeline_info_layout.addStretch()
        
        timeline_layout.addLayout(timeline_info_layout)
        timeline_layout.addWidget(main_window.timeline_slider)
        
        view_layout.addWidget(timeline_widget)
        
        return view_container

    @staticmethod
    def create_control_panel(main_window):
        """Create the control panel for point editing."""
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # Point edit controls
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
        
        return controls_widget