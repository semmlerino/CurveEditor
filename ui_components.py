#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QSlider, QLineEdit, 
                              QGroupBox, QSplitter)
from PyQt5.QtCore import Qt


class UIComponents:
    """UI component creation for the 3DE4 Curve Editor."""
    
    @staticmethod
    def create_toolbar(main_window):
        """Create the toolbar with action buttons."""
        toolbar_layout = QHBoxLayout()
        
        # File operations
        main_window.load_button = QPushButton("Load 2D Track")
        main_window.load_button.clicked.connect(main_window.load_track_data)
        
        main_window.add_point_button = QPushButton("Add 2D Track")
        main_window.add_point_button.clicked.connect(main_window.add_track_data)
        main_window.add_point_button.setEnabled(False)
        
        main_window.save_button = QPushButton("Save 2D Track")
        main_window.save_button.clicked.connect(main_window.save_track_data)
        main_window.save_button.setEnabled(False)
        
        main_window.reset_view_button = QPushButton("Reset View")
        main_window.reset_view_button.clicked.connect(main_window.reset_view)
        
        # Image sequence buttons
        main_window.load_images_button = QPushButton("Load Images")
        main_window.load_images_button.clicked.connect(main_window.load_image_sequence)
        
        main_window.toggle_bg_button = QPushButton("Toggle Background")
        main_window.toggle_bg_button.clicked.connect(main_window.toggle_background)
        main_window.toggle_bg_button.setEnabled(False)
        
        # Curve operation buttons
        main_window.smooth_button = QPushButton("Smooth Curve")
        main_window.smooth_button.clicked.connect(main_window.show_smooth_dialog)
        main_window.smooth_button.setEnabled(False)
        
        main_window.fill_gaps_button = QPushButton("Fill Gaps")
        main_window.fill_gaps_button.clicked.connect(main_window.show_fill_gaps_dialog)
        main_window.fill_gaps_button.setEnabled(False)
        
        main_window.filter_button = QPushButton("Apply Filter")
        main_window.filter_button.clicked.connect(main_window.show_filter_dialog)
        main_window.filter_button.setEnabled(False)
        
        main_window.extrapolate_button = QPushButton("Extrapolate")
        main_window.extrapolate_button.clicked.connect(main_window.show_extrapolate_dialog)
        main_window.extrapolate_button.setEnabled(False)
        
        # Analysis buttons
        main_window.detect_problems_button = QPushButton("Detect Problems")
        main_window.detect_problems_button.clicked.connect(main_window.detect_problems)
        main_window.detect_problems_button.setEnabled(False)
        
        # Undo/redo buttons
        main_window.undo_button = QPushButton("Undo")
        main_window.undo_button.clicked.connect(main_window.undo_action)
        main_window.undo_button.setEnabled(False)
        
        main_window.redo_button = QPushButton("Redo")
        main_window.redo_button.clicked.connect(main_window.redo_action)
        main_window.redo_button.setEnabled(False)
        
        # Add buttons to toolbar
        toolbar_layout.addWidget(main_window.load_button)
        toolbar_layout.addWidget(main_window.add_point_button)
        toolbar_layout.addWidget(main_window.save_button)
        toolbar_layout.addWidget(main_window.reset_view_button)
        toolbar_layout.addWidget(main_window.load_images_button)
        toolbar_layout.addWidget(main_window.toggle_bg_button)
        toolbar_layout.addWidget(main_window.smooth_button)
        toolbar_layout.addWidget(main_window.fill_gaps_button)
        toolbar_layout.addWidget(main_window.filter_button)
        toolbar_layout.addWidget(main_window.extrapolate_button)
        toolbar_layout.addWidget(main_window.detect_problems_button)
        toolbar_layout.addWidget(main_window.undo_button)
        toolbar_layout.addWidget(main_window.redo_button)
        toolbar_layout.addStretch()
        
        # Add info label
        main_window.info_label = QLabel("No data loaded")
        toolbar_layout.addWidget(main_window.info_label)
        
        return toolbar_layout
        
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
        main_window.x_edit.returnPressed.connect(main_window.update_point_from_edit)
        
        main_window.y_label = QLabel("Y:")
        main_window.y_edit = QLineEdit()
        main_window.y_edit.setMaximumWidth(100)
        main_window.y_edit.returnPressed.connect(main_window.update_point_from_edit)
        
        main_window.update_point_button = QPushButton("Update")
        main_window.update_point_button.clicked.connect(main_window.update_point_from_edit)
        
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